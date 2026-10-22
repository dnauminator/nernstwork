#!/usr/bin/env python3
"""Read-only physical diagnostics for saved Chapman fits; never fit or rerank.

One process and one numerical thread. Each integration is limited to 20,000 RHS
evaluations and 30 seconds. Results are separate from fit/prediction artifacts.
"""
from __future__ import annotations

import os
for _variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_variable] = "1"

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import signal
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nernstwork.data import joint_observation_set, load_dataset, observation_set, sha256_json
from nernstwork.evaluate import code_identity, validate_submission
from nernstwork.model import compile_mechanism
from chapman_initial_amount_adapter import compile_with_initial_amount

CONFIG = {"grid_start_min": 0.0, "grid_end_min": 9.5, "grid_step_min": 0.01,
          "negative_threshold": -1e-6, "element_drift_threshold": 1e-6,
          "rtol": 1e-8, "atol": 1e-10, "method": "LSODA", "max_rhs": 20000,
          "integration_timeout_s": 30, "workers": 1}


def read(path):
    return json.loads(Path(path).read_text())


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rel(path):
    return str(Path(path).resolve().relative_to(ROOT))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
    tmp.replace(path)


def declaration(mechanism):
    elements = mechanism.get("conservation", {}).get("elements", [])
    group = "Li+Ti" if {"Li", "Ti"} <= set(elements) else "Ti-only" if elements == ["Ti"] else "+".join(sorted(elements))
    return elements, group


def static_check(compiled, theta=None):
    """A boundary risk is a net consumption whose rate need not vanish at zero.

    A catalyst appearing unchanged on both sides is not net consumption. Free
    orders whose allowed interval includes zero are potential risks, separately
    from an actual fitted/fixed nonpositive order. This is not a positivity proof.
    """
    risks, possible, fitted_free = [], [], []
    resolved = compiled._resolved(theta) if theta is not None else None
    for j, reaction in enumerate(compiled.mechanism["reactions"]):
        law = reaction["rate_law"]
        for i in np.flatnonzero(compiled.S[:, j] < 0):
            species = compiled.species[i]
            item = {"reaction": reaction["id"], "species": species,
                    "net_stoichiometry": float(compiled.S[i, j]), "family": law["family"]}
            if law["family"] == "power_law":
                order = law["orders"].get(species)
                if order is None:
                    risks.append(dict(item, reason="omitted_order"))
                elif order.get("fixed"):
                    if float(order["value"]) <= 0:
                        risks.append(dict(item, reason="fixed_nonpositive_order", order=order["value"]))
                elif resolved is not None:
                    value = float(resolved[j]["orders"][species])
                    fitted_free.append(dict(item, fitted_order=value))
                    if value <= 0:
                        risks.append(dict(item, reason="fitted_nonpositive_order", order=value))
                else:
                    parameter = next(p for p in compiled.free if (j, "order", species) in p.members)
                    if parameter.lo <= 0:
                        possible.append(dict(item, reason="free_order_allows_zero", bounds=[parameter.lo, parameter.hi]))
            elif law["family"] == "langmuir_saturation" and i != compiled.reactant_terms[j][0][0]:
                risks.append(dict(item, reason="not_the_saturating_reactant"))
    elements, group = declaration(compiled.mechanism)
    matrix = np.array([[s.get("composition", {}).get(el, 0.0) for s in compiled.mechanism["species"]]
                       for el in elements], dtype=float)
    residuals = matrix @ compiled.S
    return {"declared_elements": elements, "conservation_group": group,
            "unprotected_consumption": risks, "free_order_boundary_possibilities": possible,
            "fitted_free_orders": fitted_free,
            "declared_stoichiometry_max_abs_residual": {el: float(np.max(np.abs(row))) for el, row in zip(elements, residuals)}}


def timeout_handler(_signum, _frame):
    raise TimeoutError("physics audit integration exceeded 30 seconds")


def integration(compiled, theta, obs, role):
    grid = np.unique(np.concatenate([np.linspace(0, 9.5, 951), obs.t_union]))
    actual_c0 = compiled.resolved_c0(theta, obs.c0, obs.conditions) if hasattr(compiled, "resolved_c0") else dict(obs.c0)
    output = {"dataset_id": obs.dataset_id, "role": role, "temperature_C": obs.conditions.T_C,
              "input_c0": obs.c0, "actual_c0": actual_c0, "n_sample_times": len(grid),
              "grid_sha256": sha256_json(grid.tolist())}
    started = time.monotonic()
    try:
        signal.setitimer(signal.ITIMER_REAL, CONFIG["integration_timeout_s"])
        y = compiled.simulate(theta, grid, obs.c0, conditions=obs.conditions,
                              rtol=CONFIG["rtol"], atol=CONFIG["atol"], method=CONFIG["method"], max_rhs=CONFIG["max_rhs"])
        signal.setitimer(signal.ITIMER_REAL, 0)
        y0 = np.array([actual_c0.get(sp, 0.0) for sp in compiled.species], dtype=float)
        minima = {}
        for i, species in enumerate(compiled.species):
            at = int(np.argmin(y[i]))
            below = np.flatnonzero(y[i] < CONFIG["negative_threshold"])
            minima[species] = {"minimum": float(y[i, at]), "time_min": float(grid[at]),
                               "first_sample_below_threshold_min": float(grid[below[0]]) if len(below) else None}
        elements, _group = declaration(compiled.mechanism)
        drift = {}
        for element in elements:
            weights = np.array([s.get("composition", {}).get(element, 0.0) for s in compiled.mechanism["species"]])
            initial = float(weights @ y0)
            delta = weights @ y - initial
            at = int(np.argmax(np.abs(delta)))
            drift[element] = {"initial": initial, "max_abs_drift": float(abs(delta[at])),
                              "signed_drift_at_max": float(delta[at]), "time_min": float(grid[at]),
                              "relative_to_initial": float(abs(delta[at]) / abs(initial)) if initial else None}
        output.update(status="simulated", species_minima=minima, declared_element_drift=drift,
                      any_species_below_threshold=any(v["minimum"] < CONFIG["negative_threshold"] for v in minima.values()),
                      any_declared_element_drift_above_threshold=any(v["max_abs_drift"] > CONFIG["element_drift_threshold"] for v in drift.values()))
    except Exception as exc:
        output.update(status="simulation_failed", error=f"{type(exc).__name__}: {exc}")
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        output["wall_s"] = time.monotonic() - started
    return output


def audit_result(path, raw, context, protocol, engine, source_hash, campaign):
    result = json.loads(raw)
    scenario, mode = result["scenario"], result["mode"]
    dev, hold, input_hashes = context[scenario]
    identity_fields = {"result_sha256": hashlib.sha256(raw).hexdigest(), "input_sha256": input_hashes,
                       "protocol_sha256": sha256_json(protocol), "engine_sha256": engine,
                       "auditor_sha256": source_hash, "config": CONFIG,
                       "adapter_sha256": digest(ROOT / "scripts/chapman_initial_amount_adapter.py") if mode != "fixed" else None}
    identity = sha256_json(identity_fields)
    destination = campaign / "physics_audit" / "records" / f"{scenario}__{mode}" / path.name
    if destination.exists():
        cached = read(destination)
        if cached.get("audit_identity") == identity:
            return cached
    fit = result.get("fit", {})
    output = {"result_path": rel(path), "audit_identity": identity, "identity_fields": identity_fields,
              "scenario": scenario, "mode": mode, "dynamics_hash": result["dynamics_hash"],
              "candidate_name": result.get("candidate_name"), "fit_status": fit.get("status"),
              "runner_status": result.get("status"), "development_aicc": fit.get("aicc"),
              "integrations": [], "observation_map": result["validation"].get("observation_map")}
    try:
        if result["engine_sha256"] != engine or result["protocol_sha256"] != sha256_json(protocol):
            raise ValueError("fit engine/protocol differs from current audit engine/protocol")
        if result["data_sha256"] != dev.sha256 or result["heldout_sha256"] != hold.sha256:
            raise ValueError("saved fit/prediction input hashes differ from current observations")
        if mode != "fixed" and result.get("adapter_sha256") != identity_fields["adapter_sha256"]:
            raise ValueError("initial-amount adapter differs from fitted source")
        submission = result["submission"]
        validation = validate_submission(submission, dev, protocol)
        if validation["status"] != "valid" or validation["dynamics_hash"] != result["dynamics_hash"]:
            raise ValueError("submission no longer validates with the saved dynamics identity")
        compiled = (compile_mechanism(submission["mechanism"], dev.conditions, protocol.get("bounds")) if mode == "fixed"
                    else compile_with_initial_amount(submission["mechanism"], dev.conditions, protocol.get("bounds"), mode))
        output["static"] = static_check(compiled)
        if fit.get("status") != "fitted":
            output["audit_status"] = "not_fitted"
        else:
            if compiled.free_names() != fit["free_parameter_names"]:
                raise ValueError("saved/current parameter names or order differ")
            theta = np.array(fit["theta"], dtype=float)
            if theta.shape != (compiled.n_free,) or not np.isfinite(theta).all():
                raise ValueError("wrong parameter count or nonfinite frozen theta")
            output["static_at_fitted_parameters"] = static_check(compiled, theta)
            output["integrations"] = [integration(compiled, theta, obs, role) for obs, role in
                                      [(p, "development") for p in dev.parts] + [(hold, "held_out_750")]]
            output["audit_status"] = "all_simulated" if all(x["status"] == "simulated" for x in output["integrations"]) else "incomplete_simulation"
    except Exception as exc:
        output.update(audit_status="audit_error", error=f"{type(exc).__name__}: {exc}")
    write(destination, output)
    return output


def render(summary, path):
    lines = ["# Chapman physical diagnostics", "", f"Snapshot: {summary['generated_at_utc']}.", "",
             "This audit resimulates frozen fitted parameters. It does not change the engine, fit results, candidate selection or ranks. "
             "Missing files are unfinished coverage, not failed models. Negative amounts and declared-element drift are separate checks.", "",
             "The core evaluates rates with `max(amount, 0)` but does not clip the integrated state. A reaction that consumes "
             "a species with an omitted or zero rate order can therefore continue below zero. The static check examines net "
             "consumption, so unchanged catalysts are not counted as depleted reactants.", "",
             "| Candidate inventory | Dynamics representatives | Li + Ti declared | Ti only | Unprotected consumption | Free order can reach zero |",
             "|---|---:|---:|---:|---:|---:|"]
    for name, c in summary["static_inventory_counts"].items():
        lines.append(f"| {name} | {c['total']} | {c.get('Li+Ti',0)} | {c.get('Ti-only',0)} | {c['boundary_risk']} | {c['possible_free_order_boundary']} |")
    lines += ["", "Counts refer to the stored representative chemistry, not every chemistry alias sharing its dynamics. "
              "Historical and fresh sets overlap and must not be added as unique candidates.", "",
              "**Ti-only models deliberately do not impose a lithium balance.** They remain valid predictive baselines within "
              "that assumption, including models with an implicit unlimited lithium supply. Their fit cannot establish lithium "
              "conservation, lithium depletion or the intermediate's lithium stoichiometry. This audit never rejects them solely "
              "for lacking lithium conservation and does not infer missing Li compositions from species names.", "",
              "Each fitted result uses its current 700/725/750 °C observations and starting amounts, including fitted initial "
              "amounts through the unchanged adapter. Cached unobserved trajectories are not used. The grid covers 0–9.5 min "
              "every 0.01 min plus all observed times. LSODA uses rtol=1e-8, atol=1e-10, at most 20,000 RHS evaluations "
              "and a 30-second timeout per integration; the audit runs on one CPU. No alternate solver recovery is silently applied.", "",
              "| Result scenario / mode | Files in snapshot | Fitted | All 3 simulations completed | Any species < −1e−6 | Declared element drift > 1e−6 | Incomplete / error |",
              "|---|---:|---:|---:|---:|---:|---:|"]
    for name, c in summary["result_counts"].items():
        lines.append(f"| {name} | {c['files']} | {c['fitted']} | {c['all_simulated']} | {c['negative']} | {c['element_drift']} | {c['incomplete_or_error']} |")
    lines += ["", f"Saved result files at snapshot start: {summary['available_result_files']}; audited in this invocation: {summary['audited_result_files']}. "
              f"Successful integrations: {summary['successful_integrations']}; failed integrations: {summary['failed_integrations']}.", "",
              "Amount thresholds are formula units per mol Ti; elemental drift is atoms per mol Ti. "
              f"Largest sampled declared-element drift: {summary['maximum_declared_element_drift']}. "
              "The count of negative trajectories includes numerical overshoot; it is not by itself evidence that a rate law is structurally invalid.", "",
              "| Flagged result | Temperature | Diagnostic |",
              "|---|---:|---|"]
    for issue in summary["exceptions"]:
        lines.append(f"| `{issue['dynamics_hash'][:12]}` / {issue['scenario']} / {issue['mode']} | {issue.get('temperature_C', '—')} | {issue['detail']} |")
    if not summary["exceptions"]:
        lines.append("| None in completed checks | — | — |")
    if summary["fitted_free_orders"]:
        lines += ["", "The historical candidate with a free anatase order has these fitted values (zero is allowed by its bounds, not assumed): " +
                  "; ".join(f"`{r['dynamics_hash'][:12]}` / {r['scenario']} / {r['mode']}: {r['fitted_order']:.6g}" for r in summary["fitted_free_orders"]) + "."]
    lines += ["",
              "| Frozen selection / scenario / mode | Declared balance | Simulation status | Lowest sampled amount | Largest declared-element drift |",
              "|---|---|---|---:|---:|"]
    for r in summary["anchor_results"]:
        lines.append(f"| {r['anchor']} / {r['scenario']} / {r['mode']} | {r['conservation_group']} | {r['audit_status']} | {r['min_amount']} | {r['max_element_drift']} |")
    lines += ["", "The observation map still sums nominal phase amounts. The digitized weight fractions were converted with "
              "fixed nominal formula masses and normalized Ti closure. Changing Li content in a model does not recompute that "
              "conversion or account for amorphous material. A nonnegative, element-balanced trajectory therefore does not validate "
              "the assumed phase composition, observation mapping, thermal history, or reaction mechanism. Sampling cannot prove "
              "positivity between grid points or outside this time/temperature range. A solver failure leaves the physical check unresolved.", "",
              "Full result identities, per-species minima, current initial amounts, declared-element drift and failures are in "
              "[the local audit snapshot](../data/derived/chapman_li_sensitivity/physics_audit/summary.json). "
              "For the observation-map and lithium-budget limits, see [the literature review](LITERATURE_REVIEW_OCT22.md).", "",
              "Refresh without fitting:", "", "```bash", ".venv/bin/python scripts/audit_chapman_physics.py", "```", ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", type=Path, default=ROOT / "data/derived/chapman_li_sensitivity")
    parser.add_argument("--report", type=Path, default=ROOT / "docs/CHAPMAN_PHYSICS_AUDIT.md")
    parser.add_argument("--limit", type=int, help="Audit only the first N result files, prioritizing frozen selections and low development AICc")
    parser.add_argument("--static-only", action="store_true")
    args = parser.parse_args()
    signal.signal(signal.SIGALRM, timeout_handler)
    protocol = read(ROOT / "configs/protocols/synthesis-mle-v1.json")
    manifest = read(args.campaign / "input_manifest.json")
    engine = code_identity()["sha256"]
    source_hash = digest(__file__)
    context = {}
    for scenario, names in manifest["inputs"].items():
        paths = [ROOT / name for name in names]
        loaded = [load_dataset(p) for p in paths]
        context[scenario] = (joint_observation_set(loaded[:2]), observation_set(*loaded[2]), {rel(p): sha for p, (_, sha) in zip(paths, loaded)})
    static_rows, static_counts, inventory_hashes = [], {}, {}
    for name, filename in (("Historical union", "repaired_records.json"), ("Fresh proposals", "fresh_opus_records.json")):
        path = args.campaign / filename
        if not path.exists():
            continue
        inventory_hashes[rel(path)] = digest(path)
        counts = Counter(total=0, boundary_risk=0, possible_free_order_boundary=0)
        for record in read(path):
            compiled = compile_mechanism(record["submission"]["mechanism"], context["fig2_lower"][0].conditions, protocol.get("bounds"))
            check = static_check(compiled)
            static_rows.append({"inventory": name, "dynamics_hash": record["dynamics_hash"], **check})
            counts["total"] += 1
            counts[check["conservation_group"]] += 1
            counts["boundary_risk"] += bool(check["unprotected_consumption"])
            counts["possible_free_order_boundary"] += bool(check["free_order_boundary_possibilities"])
        static_counts[name] = dict(counts)
    write(args.campaign / "physics_audit/static_inventory.json", static_rows)
    anchors = {}
    for name, run in (("Original baseline", "chapman750-enumeration"), ("Original Opus1", "chapman750-propose_space-opus1"), ("Fresh Opus", "chapman-li-oct22-opus1")):
        directory = ROOT / "investigations/runs" / run
        if (directory / "frozen.json").exists():
            selected = read(directory / "candidates" / f"{read(directory/'frozen.json')['top1']}.json")
            anchors[name] = selected["validation"]["dynamics_hash"]
    paths = sorted((args.campaign / "results").glob("*/*.json"))
    saved = [(p, p.read_bytes()) for p in paths]
    def priority(item):
        result = json.loads(item[1])
        return (result["dynamics_hash"] not in anchors.values(), result.get("fit", {}).get("aicc", float("inf")), str(item[0]))
    saved.sort(key=priority)
    selected = [] if args.static_only else saved[:args.limit] if args.limit else saved
    rows = []
    for i, (path, raw) in enumerate(selected):
        rows.append(audit_result(path, raw, context, protocol, engine, source_hash, args.campaign))
        if (i + 1) % 50 == 0 or i + 1 == len(selected):
            print(json.dumps({"audited": i + 1, "snapshot_files": len(saved), "last_status": rows[-1]["audit_status"]}), flush=True)
    counts = defaultdict(lambda: Counter(files=0, fitted=0, all_simulated=0, negative=0, element_drift=0, incomplete_or_error=0))
    anchor_rows, exceptions, free_orders, element_drifts = [], [], [], []
    for row in rows:
        c = counts[f"{row['scenario']}__{row['mode']}"]
        c["files"] += 1
        c["fitted"] += row["fit_status"] == "fitted"
        c["all_simulated"] += row["audit_status"] == "all_simulated"
        c["negative"] += any(x.get("any_species_below_threshold", False) for x in row["integrations"])
        c["element_drift"] += any(x.get("any_declared_element_drift_above_threshold", False) for x in row["integrations"])
        c["incomplete_or_error"] += row["audit_status"] in ("incomplete_simulation", "audit_error")
        identifier = {key: row[key] for key in ("dynamics_hash", "scenario", "mode")}
        for order in row.get("static_at_fitted_parameters", {}).get("fitted_free_orders", []):
            free_orders.append({**identifier, **order})
        if row.get("error"):
            exceptions.append({**identifier, "detail": row["error"]})
        for integration_row in row["integrations"]:
            detail = {**identifier, "temperature_C": integration_row["temperature_C"]}
            if integration_row.get("error"):
                exceptions.append({**detail, "detail": integration_row["error"]})
            for species, minimum in integration_row.get("species_minima", {}).items():
                if minimum["minimum"] < CONFIG["negative_threshold"]:
                    exceptions.append({**detail, "detail": f"{species} minimum {minimum['minimum']:.6g} at {minimum['time_min']:.3g} min; sampled negative-amount flag"})
            for element, drift in integration_row.get("declared_element_drift", {}).items():
                element_drifts.append(drift["max_abs_drift"])
                if drift["max_abs_drift"] > CONFIG["element_drift_threshold"]:
                    exceptions.append({**detail, "detail": f"{element} drift {drift['max_abs_drift']:.6g}"})
        for label, dh in anchors.items():
            if row["dynamics_hash"] == dh:
                minima = [v["minimum"] for x in row["integrations"] for v in x.get("species_minima", {}).values()]
                drift = [v["max_abs_drift"] for x in row["integrations"] for v in x.get("declared_element_drift", {}).values()]
                anchor_rows.append({"anchor": label, "scenario": row["scenario"], "mode": row["mode"], "audit_status": row["audit_status"],
                                    "conservation_group": row.get("static", {}).get("conservation_group", "unknown"),
                                    "min_amount": min(minima) if minima else None, "max_element_drift": max(drift) if drift else None})
    summary = {"generated_at_utc": datetime.now(timezone.utc).isoformat(), "config": CONFIG,
               "auditor_sha256": source_hash, "engine_sha256": engine, "inventory_sha256": inventory_hashes,
               "static_inventory_counts": static_counts, "available_result_files": len(saved), "audited_result_files": len(rows),
               "result_counts": dict(sorted(counts.items())), "anchors": anchors, "anchor_results": anchor_rows,
               "exceptions": exceptions, "fitted_free_orders": free_orders,
               "maximum_declared_element_drift": max(element_drifts, default=None),
               "successful_integrations": sum(x["status"] == "simulated" for r in rows for x in r["integrations"]),
               "failed_integrations": sum(x["status"] != "simulated" for r in rows for x in r["integrations"]),
               "result_files_at_start": {rel(p): hashlib.sha256(raw).hexdigest() for p, raw in saved},
               "results": rows}
    write(args.campaign / "physics_audit/summary.json", summary)
    render(summary, args.report)
    print(json.dumps({"static": static_counts, "results": summary["result_counts"], "report": rel(args.report)}, indent=2))


if __name__ == "__main__":
    main()
