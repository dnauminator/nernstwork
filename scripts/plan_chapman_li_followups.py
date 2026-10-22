#!/usr/bin/env python3
"""Reconcile the finite Chapman campaign and publish append-only follow-up plans.

Reads existing artifacts only; never starts fits, rescoring, jobs, or messages.
The only writes are new versioned plans/lists. Existing v1 job inputs are preserved.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nernstwork.data import sha256_json
from nernstwork.evaluate import code_identity
from summarize_chapman_li_sensitivity import collect, optimizer_quality

OLD_AI = tuple(f"chapman750-propose_space-{name}" for name in ("opus1", "opus2", "gemini1", "gemini2"))
DELTA_AICC = 4.0


def finite(value):
    return isinstance(value, (int, float)) and math.isfinite(value)


def relative(path):
    try:
        return str(Path(path).resolve().relative_to(ROOT))
    except ValueError:
        return str(Path(path).resolve())


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


class Sources:
    def __init__(self):
        self.hashes = {}

    def read(self, path):
        path = Path(path)
        raw = path.read_bytes()
        value = hashlib.sha256(raw).hexdigest()
        key = relative(path)
        if key in self.hashes and self.hashes[key] != value:
            raise ValueError(f"Source changed within this planning snapshot: {key}; rerun")
        self.hashes[key] = value
        return json.loads(raw)

    def track(self, path):
        path = Path(path)
        self.hashes[relative(path)] = hashlib.sha256(path.read_bytes()).hexdigest()


def independent(record):
    submission = record["submission"]
    used = any(t["species"] == "Li2CO3" for r in submission["mechanism"]["reactions"] for t in r["reactants"])
    observed = any("Li2CO3" in species for species in submission.get("observation_map", {}).values())
    return not used and not observed


def index_records(records):
    result = {}
    for record in records:
        key = record["dynamics_hash"]
        if key in result:
            raise ValueError(f"Duplicate dynamics in a declared inventory: {key}")
        if record["validation"]["status"] != "valid" or record["validation"]["dynamics_hash"] != key:
            raise ValueError(f"Invalid exported candidate: {key}")
        if record.get("carbonate_independent") != independent(record):
            raise ValueError(f"Stale carbonate-independence annotation: {key}")
        result[key] = record
    return result


def versions(directory, stem):
    expression = re.compile(re.escape(stem) + r"_v(\d+)\.json$")
    found = []
    for path in directory.glob(f"{stem}_v*.json"):
        match = expression.fullmatch(path.name)
        if match:
            found.append((int(match.group(1)), path))
    return sorted(found)


def previous_members(directory, stem):
    found = versions(directory, stem)
    if not found:
        return set()
    return {r["dynamics_hash"] for r in json.loads(found[-1][1].read_text())}


def coverage(rows, members, scenario, mode):
    selected = {r["dynamics_hash"]: r for r in rows if r["scenario"] == scenario and r["mode"] == mode
                and r["dynamics_hash"] in members}
    missing = sorted(set(members) - set(selected))
    invalid = sorted(key for key, r in selected.items() if not r["fit_identity_valid"])
    fitted = [r for r in selected.values() if r["fit_status"] == "fitted" and r["fit_identity_valid"]]
    predictions = [r for r in fitted if r["prediction_valid"]]
    return {"target_count": len(members), "target_dynamics_hashes": sorted(members),
            "result_files": len(selected), "missing_count": len(missing), "missing_dynamics_hashes": missing,
            "fit_status_counts": dict(Counter(r["fit_status"] or "missing_fit" for r in selected.values())),
            "runner_status_counts": dict(Counter(r["status"] or "missing_status" for r in selected.values())),
            "identity_invalid_dynamics_hashes": invalid, "valid_fitted_results": len(fitted),
            "audited_predictions": len(predictions),
            "independent_prediction_status_counts": dict(Counter(r["independent_prediction_status"] or "not_independently_rescored" for r in selected.values())),
            "fitted_without_audited_prediction": sorted(r["dynamics_hash"] for r in fitted if not r["prediction_valid"]),
            "fit_failures": sorted(key for key, r in selected.items() if r["fit_status"] != "fitted"),
            "optimizer_warning_dynamics_hashes": sorted(r["dynamics_hash"] for r in fitted if r["optimizer_quality"]["interpretation_unreliable"]),
            "all_outcomes_recorded": not missing and not invalid,
            "all_fits_and_predictions_succeeded": len(predictions) == len(members) and not missing and not invalid}


def unfinished_start_aicc(result):
    """Diagnostic score only: unfinished starts never become fitted candidates."""
    fitted, validation = result.get("fit", {}), result["validation"]
    multi = fitted.get("multistart", {})
    statuses = multi.get("converged_by_start", [])
    starts = [(i, value) for i, value in enumerate(multi.get("nll_by_start", []))
              if finite(value) and (i >= len(statuses) or statuses[i] is not True)]
    if not starts:
        return None
    index, nll = min(starts, key=lambda item: item[1])
    returned = fitted.get("nll")
    if finite(returned) and nll >= returned - .01 - 1e-9 * abs(returned):
        return None
    k = fitted.get("k_total", validation["k_kinetic"] + validation["k_noise"])
    n = fitted.get("n_obs", validation["n_obs"])
    if n <= k + 1:
        return None
    return {"start_index": index, "unfinished_nll": nll,
            "diagnostic_aicc_at_unfinished_start": 2*nll + 2*k + 2*k*(k+1)/(n-k-1),
            "returned_nll": returned, "returned_aicc": fitted.get("aicc"),
            "nll_gap": returned - nll if finite(returned) else None,
            "ranking_eligible": False}


def build(campaign, output):
    sources, warnings = Sources(), []
    for path in (Path(__file__), ROOT / "scripts/summarize_chapman_li_sensitivity.py",
                 ROOT / "docs/CHAPMAN_LI_SENSITIVITY_PROTOCOL.md", ROOT / "configs/protocols/synthesis-mle-v1.json"):
        sources.track(path)
    for path in sorted(campaign.glob("queue_*.sh")):
        sources.track(path)
    manifest = sources.read(campaign / "input_manifest.json")
    for names in manifest["inputs"].values():
        for name in names:
            sources.track(ROOT / name)
    old = index_records(sources.read(campaign / "repaired_records.json"))
    comparable = index_records(sources.read(campaign / "comparable_records.json"))
    if len(old) != 904 or len(comparable) != 860 or not set(comparable) <= set(old):
        raise ValueError("Historical 904/860 inventory contract changed")
    source_records = sources.read(campaign / "source_records.json")
    sources.read(campaign / "inventory.json")
    fresh, fresh_inventory = {}, None
    fresh_path = campaign / "fresh_opus_inventory.json"
    fresh_state = {"export_available": fresh_path.exists(), "selection_frozen": False,
                   "provisional": True, "export_matches_live_candidates": False}
    if fresh_path.exists():
        fresh_inventory = sources.read(fresh_path)
        fresh = index_records(sources.read(campaign / "fresh_opus_records.json"))
        if sources.hashes[relative(campaign / "fresh_opus_records.json")] != fresh_inventory["records_sha256"]:
            raise ValueError("Fresh inventory/records hashes differ; refresh exporter")
        if len(fresh) != fresh_inventory["unique_valid_dynamics"]:
            raise ValueError("Fresh inventory count mismatch")
        run_dir = ROOT / fresh_inventory["run_path"]
        live_sources = {}
        for path in sorted((run_dir / "candidates").glob("*.json")):
            sources.track(path)
            live_sources[relative(path)] = sources.hashes[relative(path)]
        host = sources.read(run_dir / "pi/host_state.json") if (run_dir / "pi/host_state.json").exists() else {}
        matches = live_sources == fresh_inventory["source_sha256"]
        fresh_state.update(export_generated_at=fresh_inventory["generated_at_utc"], run_id=fresh_inventory["run_id"],
                           exported_dynamics=len(fresh), live_candidate_files=len(live_sources),
                           exported_validation_statuses=fresh_inventory["validation_statuses"],
                           export_matches_live_candidates=matches,
                           live_host_state={k: host.get(k) for k in ("phase", "round", "concluded", "submissionsOpen")})
        if not matches:
            warnings.append("Fresh export is stale: refresh it before closing candidate coverage")
    merged = dict(fresh)
    merged.update(old)  # preserve the historical representative for overlapping dynamics
    reasons = defaultdict(set)
    anchors, retrospective_predictors, original_best = {}, {}, []

    def add(dynamics, reason):
        if dynamics not in merged:
            raise ValueError(f"Follow-up candidate missing from validated inventories: {dynamics}")
        reasons[dynamics].add(reason)

    # Original means originally valid and the historical nominal-input cache,
    # never newly repaired candidates or lower-input results that arrived first.
    for dynamics, record in comparable.items():
        path = ROOT / record["old_data_cache_path"]
        if not path.exists():
            warnings.append(f"Missing original nominal fit cache: {dynamics}")
            continue
        body = sources.read(path)
        if body["fit_key"] != record["old_data_fit_key"]:
            raise ValueError(f"Original cache key mismatch: {dynamics}")
        fit = body["result"]
        if fit.get("status") == "fitted" and finite(fit.get("aicc")) and not independent(record):
            original_best.append({"dynamics_hash": dynamics, "aicc": fit["aicc"],
                                  "optimizer_quality": optimizer_quality(fit)})
    original_best.sort(key=lambda r: (r["aicc"], r["dynamics_hash"]))
    for i, item in enumerate(original_best[:10], 1):
        add(item["dynamics_hash"], f"original_nominal_dependent_top10_rank_{i}")
    if len(original_best) < 10:
        warnings.append("Fewer than ten original fitted carbonate-dependent candidates are available")

    for run in ("chapman750-enumeration", *OLD_AI):
        directory = ROOT / "investigations/runs" / run
        frozen = sources.read(directory / "frozen.json")
        candidate = sources.read(directory / "candidates" / f"{frozen['top1']}.json")
        dynamics = candidate["validation"]["dynamics_hash"]
        anchors[run] = {"candidate_id": frozen["top1"], "dynamics_hash": dynamics, "frozen": True}
        if run in OLD_AI:
            add(dynamics, f"original_development_selection:{run}")
            final = sources.read(directory / "final/chapman2023_fig2_750C/predictions.json")
            # R: denotes that AI run's candidates; S: is its shared reference set.
            eligible = [(key[2:], score) for key, score in final["scores"].items()
                        if key.startswith("R:") and score.get("status") == "fitted" and finite(score.get("heldout_score"))]
            if not eligible:
                raise ValueError(f"No original retrospective predictor for {run}")
            cid, score = min(eligible, key=lambda item: (item[1]["heldout_score"], item[0]))
            best = sources.read(directory / "candidates" / f"{cid}.json")
            dh = best["validation"]["dynamics_hash"]
            retrospective_predictors[run] = {"candidate_id": cid, "dynamics_hash": dh,
                                             "heldout_score": score["heldout_score"], "selection_is_retrospective": True}
            add(dh, f"original_best_retrospective_predictor:{run}")

    fresh_selected = set()
    if fresh_inventory:
        frozen_path = ROOT / fresh_inventory["run_path"] / "frozen.json"
        if frozen_path.exists():
            frozen = sources.read(frozen_path)
            candidate = sources.read(frozen_path.parent / "candidates" / f"{frozen['top1']}.json")
            dh = candidate["validation"]["dynamics_hash"]
            if dh not in fresh:
                warnings.append("Fresh frozen selection is absent from export; refresh exporter before scheduling it")
            else:
                fresh_selected.add(dh)
                add(dh, "fresh_frozen_development_selection")
                anchors[fresh_inventory["run_id"]] = {"candidate_id": frozen["top1"], "dynamics_hash": dh, "frozen": True}
                fresh_state["selection_frozen"] = True
        fresh_state["provisional"] = not (fresh_state["selection_frozen"] and fresh_state["export_matches_live_candidates"]
                                           and fresh_state["live_host_state"].get("concluded") is True)

    rows, problems, result_hashes, _sigma, file_count = collect(campaign)
    sources.hashes.update(result_hashes)
    unknown_results = sorted(r["path"] for r in rows if r["dynamics_hash"] not in merged)
    if unknown_results:
        warnings.append("Saved results exist outside the exported inventories; refresh/reconcile inventories before closure")
    engine = code_identity()["sha256"]
    for row in rows:
        if row["signature"].get("engine_sha256") != engine:
            row["fit_identity_valid"] = row["prediction_valid"] = False
            problems.append({"path": row["path"], "errors": ["fit engine differs from current evaluator"]})
    lower = [r for r in rows if r["scenario"] == "fig2_lower" and r["mode"] == "fixed"
             and r["dynamics_hash"] in merged and r["fit_status"] == "fitted" and r["fit_identity_valid"] and finite(r["aicc"])]
    dependent = [r for r in lower if not independent(merged[r["dynamics_hash"]])]
    best_dependent = min((r["aicc"] for r in dependent), default=None)
    competitive = []
    if best_dependent is not None:
        for row in dependent:
            if row["aicc"] <= best_dependent + DELTA_AICC:
                add(row["dynamics_hash"], "lower_fixed_development_within_4_aicc_of_best_dependent")
                competitive.append({"dynamics_hash": row["dynamics_hash"], "aicc": row["aicc"],
                                    "optimizer_warning": row["optimizer_quality"]["interpretation_unreliable"]})

    baseline = {r["original_dynamics_hash"] for r in source_records
                if r["source"]["run_id"] == "chapman750-enumeration" and "original_dynamics_hash" in r}
    opus1 = {r["repaired_dynamics_hash"] for r in source_records
             if r["source"]["run_id"] == "chapman750-propose_space-opus1" and "repaired_dynamics_hash" in r}
    if len(baseline) != 154:
        raise ValueError("Declared baseline must contain 154 dynamics")
    proposed = {
        "initial_amount_shortlist": {dh for dh in reasons if not independent(merged[dh])},
        "extraction_shortlist": baseline | opus1 | set(reasons) | fresh_selected,
        # Conditional interpretation/profile decisions are not invented by this planner.
        "per_temperature_shortlist": set(),
        "fresh_selected_nominal_shortlist": fresh_selected - set(old),
        "primary_lower_union_records": set(merged),
    }
    scheduled = {}
    for stem in proposed:
        seed = campaign / f"{stem}_v1.json"
        existing = set()
        if seed.exists():
            existing |= set(index_records(sources.read(seed)))
        existing |= previous_members(output, stem)
        if not existing <= set(merged):
            raise ValueError(f"Previously scheduled members disappeared from inventory: {stem}")
        scheduled[stem] = existing
        proposed[stem] |= existing  # never retract a previously scheduled comparison
    if any(independent(merged[dh]) for dh in proposed["initial_amount_shortlist"] | proposed["per_temperature_shortlist"]):
        raise ValueError("Initial-amount shortlist contains a carbonate-independent candidate")

    primary_targets = {"fig2_nominal__fixed": set(old), "fig2_lower__fixed": set(merged)}
    primary = {key: coverage(rows, ids, *key.split("__")) for key, ids in primary_targets.items()}
    followup_targets = {
        "fig2_lower__shared": proposed["initial_amount_shortlist"],
        "fig2_lower__per_temperature": proposed["per_temperature_shortlist"],
        "s1_nominal__fixed": proposed["extraction_shortlist"],
        "s1_lower__fixed": proposed["extraction_shortlist"],
        "fresh_selected_fig2_nominal__fixed": proposed["fresh_selected_nominal_shortlist"],
    }
    followup_coverage = {key: coverage(rows, ids, *key.removeprefix("fresh_selected_").split("__"))
                         for key, ids in followup_targets.items()}

    selected_ids = {anchor["dynamics_hash"] for anchor in anchors.values()}
    provisional_selections = {}
    for scenario, members in (("fig2_nominal", set(old)), ("fig2_lower", set(merged))):
        options = [r for r in rows if r["scenario"] == scenario and r["mode"] == "fixed" and r["dynamics_hash"] in members
                   and r["fit_identity_valid"] and r["fit_status"] == "fitted" and finite(r["aicc"])]
        if options:
            chosen = min(options, key=lambda r: (r["aicc"], r["dynamics_hash"]))
            selected_ids.add(chosen["dynamics_hash"])
            provisional_selections[scenario] = {"dynamics_hash": chosen["dynamics_hash"], "aicc": chosen["aicc"],
                                                "frozen": False, "coverage_incomplete": not primary[f"{scenario}__fixed"]["all_outcomes_recorded"]}
    trusted_best, trusted_overall = {}, {}
    for scenario in ("fig2_nominal", "fig2_lower"):
        trusted_rows = [r for r in rows if r["scenario"] == scenario and r["mode"] == "fixed"
                   and r["dynamics_hash"] in merged and r["fit_identity_valid"] and r["fit_status"] == "fitted"
                   and finite(r["aicc"])
                   and not r["optimizer_quality"]["interpretation_unreliable"]]
        trusted_best[scenario] = min((r["aicc"] for r in trusted_rows if not independent(merged[r["dynamics_hash"]])), default=None)
        trusted_overall[scenario] = min((r["aicc"] for r in trusted_rows), default=None)

    rescues = []
    for path in sorted((campaign / "numerics/rescue").glob("*.json")):
        rescue = sources.read(path)
        converged = [stage for stage in rescue.get("stages", {}).values()
                     if stage.get("status") == "converged" and finite(stage.get("nll"))]
        best = min((stage["nll"] for stage in converged), default=None)
        replicas = sum(abs(stage["nll"]-best) <= .01 for stage in converged) if best is not None else 0
        rescues.append({"path": relative(path), "dynamics_hash": rescue["dynamics_hash"], "scenario": rescue["scenario"],
                        "input_result_sha256": rescue["input_result_sha256"], "replicated_converged_starts": replicas,
                        "primary_ranking_eligible": rescue.get("primary_ranking_eligible")})
    rescue_priorities = []
    for row in rows:
        if row["mode"] != "fixed" or row["scenario"] not in trusted_best or not row["fit_identity_valid"] or row["dynamics_hash"] not in merged:
            continue
        raw = sources.read(ROOT / row["path"])
        unfinished = unfinished_start_aicc(raw)
        numerical_problem = row["fit_status"] != "fitted" or row["optimizer_quality"]["interpretation_unreliable"]
        inert = independent(merged[row["dynamics_hash"]])
        benchmark_kind = "overall" if inert else "carbonate_dependent"
        benchmark = (trusted_overall if inert else trusted_best)[row["scenario"]]
        close = unfinished is not None and benchmark is not None and unfinished["diagnostic_aicc_at_unfinished_start"] <= benchmark + DELTA_AICC
        selected_problem = row["dynamics_hash"] in selected_ids and numerical_problem
        if not close and not selected_problem:
            continue
        matching = [r for r in rescues if r["dynamics_hash"] == row["dynamics_hash"] and r["scenario"] == row["scenario"]
                    and r["input_result_sha256"] == sources.hashes[row["path"]]]
        resolved = any(r["replicated_converged_starts"] >= 2 and r["primary_ranking_eligible"] is False for r in matching)
        rescue_priorities.append({"dynamics_hash": row["dynamics_hash"], "scenario": row["scenario"], "result_path": row["path"],
                                  "reasons": ([f"unfinished_better_start_within_4_of_best_trusted_{benchmark_kind}"] if close else []) +
                                             (["selected_primary_candidate_has_optimizer_problem"] if selected_problem else []),
                                  "comparison_group": benchmark_kind, "comparison_benchmark_aicc": benchmark,
                                  "best_trusted_dependent_aicc": trusted_best[row["scenario"]],
                                  "best_trusted_overall_aicc": trusted_overall[row["scenario"]], "unfinished_start": unfinished,
                                  "diagnostic_status": "replicated_rescue_exists" if resolved else "pending_bounded_rescue_decision",
                                  "existing_rescues": matching, "primary_ranking_eligible": False})
    excluded_amount = sorted(dh for dh in reasons if independent(merged[dh]))
    primary_closed = all(c["all_outcomes_recorded"] for c in primary.values())
    extraction_independent = sum(independent(merged[dh]) for dh in proposed["extraction_shortlist"])
    plan = {
        "planner_version": 1, "purpose": "Read-only reconciliation; new append-only plan/list artifacts only; no jobs launched",
        "engine_sha256": engine, "protocol_rule_delta_aicc": DELTA_AICC,
        "selection_window_definition": "Reported fitted lower-Fig2 development AICc within 4 of the best dependent fit; optimizer warnings remain explicit. No unfinished start is eligible.",
        "trusted_definition": "Identity-valid fitted result without a lower-start/optimizer warning; this is not proof of a global optimum or physical validity",
        "fresh": fresh_state, "provisional": fresh_state["provisional"] or not primary_closed or bool(warnings) or bool(problems),
        "inventory_counts": {"historical": len(old), "originally_valid": len(comparable), "fresh": len(fresh),
                             "overlap": len(set(old) & set(fresh)), "lower_union": len(merged),
                             "distinct_primary_condition_outcomes": len(old) + len(merged)},
        "source_sha256": dict(sorted(sources.hashes.items())), "result_files_in_snapshot": file_count,
        "unclassified_result_paths": unknown_results,
        "list_status_note": "These are declared target lists, not evidence that a queue has started or completed. This planner launches nothing.",
        "primary_coverage": primary, "followup_coverage": followup_coverage,
        "original_best_ten_dependent": original_best[:10], "frozen_selections": anchors,
        "original_best_retrospective_predictors": retrospective_predictors,
        "current_primary_development_selections": provisional_selections,
        "lower_best_reported_dependent_aicc": best_dependent, "lower_newly_competitive": competitive,
        "best_trusted_dependent_aicc": trusted_best,
        "best_trusted_overall_aicc": trusted_overall,
        "rescue_triage_rule": "Unfinished inert-candidate scores are compared with the trusted overall leader; dependent candidates with the trusted dependent leader. Selected anchors retain priority regardless of score. Unfinished scores are never ranking eligible.",
        "followup_reasons": {key: sorted(value) for key, value in sorted(reasons.items())},
        "amount_fit_exclusions_carbonate_independent": excluded_amount,
        "planned_lists": {stem: {"target_count": len(ids), "retained_previously_scheduled_count": len(scheduled[stem]),
                                  "added_dynamics_hashes": sorted(ids-scheduled[stem]), "target_dynamics_hashes": sorted(ids)}
                          for stem, ids in proposed.items()},
        "extraction_optimization_accounting": {"condition_outcomes": 2*len(proposed["extraction_shortlist"]),
                                               "carbonate_independent_reuses_if_proven": extraction_independent,
                                               "optimizations_with_successful_invariance_reuse": 2*len(proposed["extraction_shortlist"])-extraction_independent},
        "numerical_rescue_priorities": rescue_priorities,
        "prediction_followup": [{"path": r["path"], "scenario": r["scenario"], "mode": r["mode"],
                                  "dynamics_hash": r["dynamics_hash"], "independent_status": r["independent_prediction_status"],
                                  "audit_errors": r["prediction_audit_errors"]}
                                 for r in rows if r["fit_status"] == "fitted" and (not r["prediction_valid"] or r["independent_prediction_status"] is None)],
        "pending_interpretation_decisions": [
            "Separate-amount and profile lists are not automatically expanded: review completed shared fits and consequential conclusions, then explicitly record additions.",
            "Refresh fresh export after candidate generation/freeze; then rerun this planner and schedule only missing listed results.",
            "Refresh independent scoring and physical diagnostics, including separately rescued parameter sets; preserve primary results and ranking eligibility.",
            "A process exiting successfully is not coverage. Missing/busy results and numerical failures require explicit reconciliation.",
            "Completion means every declared candidate has a recorded bounded-budget outcome, not a global-optimization or all-chemistry guarantee."],
        "audit_problems": problems, "warnings": warnings,
    }
    lists = {stem: [merged[dh] for dh in sorted(ids)] for stem, ids in proposed.items()}
    return plan, lists


def publish_list(directory, stem, records):
    wanted = {r["dynamics_hash"]: r for r in records}
    found = versions(directory, stem)
    if found:
        path = found[-1][1]
        saved = {r["dynamics_hash"]: r for r in json.loads(path.read_text())}
        if saved == wanted:
            return {"path": relative(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "created": False}
    version = max(2, found[-1][0]+1 if found else 2)
    path = directory / f"{stem}_v{version}.json"
    raw = encoded(records)
    with path.open("xb") as handle:
        handle.write(raw)
    return {"path": relative(path), "sha256": hashlib.sha256(raw).hexdigest(), "created": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", type=Path, default=ROOT / "data/derived/chapman_li_sensitivity")
    parser.add_argument("--output-dir", type=Path, help="Default: campaign directory; source artifacts are never overwritten")
    parser.add_argument("--dry-run", action="store_true", help="Compute the plan without writing any files")
    args = parser.parse_args()
    output = args.output_dir or args.campaign
    plan, lists = build(args.campaign, output)
    # Creation time and file-version allocation do not affect semantic identity.
    identity = sha256_json(plan)
    path, reused = None, False
    found = versions(output, "followup_plan")
    if found and json.loads(found[-1][1].read_text()).get("identity") == identity:
        path, reused = found[-1][1], True
    elif not args.dry_run:
        output.mkdir(parents=True, exist_ok=True)
        published = {stem: publish_list(output, stem, records) for stem, records in lists.items()}
        version = max(2, found[-1][0]+1 if found else 2)
        path = output / f"followup_plan_v{version}.json"
        body = dict(plan, identity=identity, generated_at_utc=datetime.now(timezone.utc).isoformat(), record_lists=published)
        with path.open("xb") as handle:
            handle.write(encoded(body))
    print(json.dumps({"plan": relative(path) if path else None, "dry_run": args.dry_run, "reused_plan": reused,
                      "provisional": plan["provisional"], "inventory": plan["inventory_counts"],
                      "primary": {key: {name: row[name] for name in ("target_count", "result_files", "missing_count", "valid_fitted_results", "audited_predictions")}
                                  for key, row in plan["primary_coverage"].items()},
                      "followup_targets": {key: row["target_count"] for key, row in plan["followup_coverage"].items()},
                      "rescue_priorities": dict(Counter(r["diagnostic_status"] for r in plan["numerical_rescue_priorities"])),
                      "warnings": plan["warnings"], "audit_problems": len(plan["audit_problems"])}, indent=2))


if __name__ == "__main__":
    main()
