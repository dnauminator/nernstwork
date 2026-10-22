#!/usr/bin/env python3
"""Read-only audit and snapshot report for the finite Chapman lithium campaign.

Does not fit models, change jobs, or infer completion from a quiet result directory.
Candidate-level exports remain local in the ignored campaign directory. Tracked
outputs are a concise aggregate report and figures. Safe to rerun as jobs finish.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CAMPAIGN = ROOT / "data/derived/chapman_li_sensitivity"
SCENARIOS = ("fig2_nominal", "fig2_lower", "s1_nominal", "s1_lower")
LABELS = {"fig2_nominal": "Fig. 2 nominal", "fig2_lower": "Fig. 2 lower Li",
          "s1_nominal": "S1 nominal", "s1_lower": "S1 lower Li"}
GROUP_LABELS = {"comparable": "Originally valid union", "repaired": "Union including repairs",
                "repaired_only": "Added by representation repair", "baseline": "Fixed baseline",
                "prior_opus1": "Saved Opus1, originally valid", "prior_opus1_repaired": "Saved Opus1 including repairs",
                "fresh_opus": "Fresh lower-Li Opus run"}


def read(path):
    return json.loads(Path(path).read_text())


def finite(value):
    return isinstance(value, (int, float)) and math.isfinite(value)


def clean(value):
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    # Summary files are separate from runner files; replace only our own output.
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(clean(value), indent=2, allow_nan=False) + "\n")
    tmp.replace(path)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rel(path):
    try:
        return str(Path(path).resolve().relative_to(ROOT))
    except ValueError:
        return str(Path(path).resolve())


def source_groups(campaign):
    records = read(campaign / "source_records.json")
    aliases = {kind: read(campaign / f"{kind}_aliases.json") for kind in ("comparable", "repaired")}
    groups = {kind: {a["dynamics_hash"] for a in items} for kind, items in aliases.items()}
    groups["repaired_only"] = groups["repaired"] - groups["comparable"]
    for group, run, field in (("baseline", "chapman750-enumeration", "original_dynamics_hash"),
                              ("prior_opus1", "chapman750-propose_space-opus1", "original_dynamics_hash"),
                              ("prior_opus1_repaired", "chapman750-propose_space-opus1", "repaired_dynamics_hash")):
        groups[group] = {r[field] for r in records if r["source"]["run_id"] == run and field in r}
    # Cross-check membership against every alias link, not only a representative name.
    for kind, items in aliases.items():
        field = "original_dynamics_hash" if kind == "comparable" else "repaired_dynamics_hash"
        for item in items:
            if any(records[i].get(field) != item["dynamics_hash"] for i in item["source_record_indices"]):
                raise ValueError(f"Broken {kind} source-record alias: {item['dynamics_hash']}")
    expected = read(campaign / "inventory.json")["counts"]
    if len(groups["comparable"]) != expected["comparable_dynamics"] or len(groups["repaired"]) != expected["repaired_dynamics"]:
        raise ValueError("Inventory and alias counts differ")
    if len(groups["baseline"]) != 154:
        raise ValueError("Declared baseline is no longer the fixed 154-member baseline")
    anchors = {}
    for name, run in (("original_baseline_top1", "chapman750-enumeration"),
                      ("original_opus1_top1", "chapman750-propose_space-opus1"),
                      ("original_opus2_top1", "chapman750-propose_space-opus2"),
                      ("original_gemini1_top1", "chapman750-propose_space-gemini1"),
                      ("original_gemini2_top1", "chapman750-propose_space-gemini2")):
        runpath = ROOT / "investigations/runs" / run
        cid = read(runpath / "frozen.json")["top1"]
        candidate = read(runpath / "candidates" / f"{cid}.json")
        frozen = read(runpath / "frozen.json")
        anchors[name] = {"candidate_id": cid, "dynamics_hash": candidate["validation"]["dynamics_hash"],
                         "path":rel(runpath/"frozen.json"),"frozen_at":frozen.get("frozen_at"),"rule":frozen.get("rule")}
    fresh_path = campaign / "fresh_opus_inventory.json"
    if fresh_path.is_file():
        fresh = read(fresh_path)
        records_path = campaign / "fresh_opus_records.json"
        if digest(records_path) != fresh["records_sha256"]:
            raise ValueError("Fresh Opus inventory/records hashes differ; rerun exporter")
        fresh_records = read(records_path)
        groups["fresh_opus"] = {r["dynamics_hash"] for r in fresh_records}
        if len(groups["fresh_opus"]) != len(fresh_records) or len(fresh_records) != fresh["unique_valid_dynamics"]:
            raise ValueError("Fresh Opus export is not the declared unique dynamics set")
        for record in fresh_records:
            if record["validation"]["status"] != "valid" or record["validation"]["dynamics_hash"] != record["dynamics_hash"]:
                raise ValueError("Fresh Opus record lacks matching validated dynamics")
        if fresh.get("frozen_selection"):
            anchors["fresh_opus_top1"] = fresh["frozen_selection"]
    return groups, anchors


def topology(submission):
    mechanism = submission.get("mechanism", {})
    steps = []
    for reaction in mechanism.get("reactions", []):
        def side(terms):
            return " + ".join((f"{t['coeff']:g} " if t["coeff"] != 1 else "") + t["species"] for t in terms)
        law = reaction["rate_law"]
        suffix = law["family"]
        if law.get("time_modulation"):
            suffix += ", " + law["time_modulation"]["kind"]
        steps.append(f"{reaction['id']}: {side(reaction['reactants'])} → {side(reaction['products'])} [{suffix}]")
    elements = mechanism.get("conservation", {}).get("elements", ["N-equivalents"])
    bypass = [r["id"] for r in mechanism.get("reactions", [])
              if any(t["species"] == "Li2TiO3" for t in r["products"])
              and not any(t["species"] == "Li2CO3" for t in r["reactants"])
              and "Li2CO3" not in r["rate_law"].get("orders", {})]
    return {"conserved_elements": elements, "declares_lithium_conservation":"Li" in elements,
            "carbonate_free_intermediate_routes":bypass,
            "steps": steps, "n_steps": len(steps), "n_species": len(mechanism.get("species", []))}


def optimizer_quality(fit, tolerance=.01):
    """Check starts near the RETURNED NLL; better unfinished starts are not replicas."""
    multi = fit.get("multistart", {})
    returned = fit.get("nll")
    values = multi.get("nll_by_start", [])
    flags = multi.get("converged_by_start", [])
    epsilon = tolerance + 1e-9 * abs(returned) if finite(returned) else tolerance
    near = [i for i,nll in enumerate(values) if finite(returned) and finite(nll) and abs(nll-returned) <= epsilon]
    lower = [nll for nll in values if finite(returned) and finite(nll) and nll < returned-epsilon]
    return {"warning":multi.get("warning"),"budget_exhausted":multi.get("budget_exhausted"),
            "nll_by_start":values,"converged_by_start":flags,"replicate_tolerance_nll":tolerance,
            "reported_replicates":multi.get("replicates"),"starts_near_returned_nll":len(near) if values else None,
            "converged_starts_near_returned_nll":sum(i < len(flags) and bool(flags[i]) for i in near) if values else None,
            "accepted_by_replication_without_formal_convergence":fit.get("status") == "fitted" and multi.get("formally_converged") is False,
            "starts_better_than_returned":len(lower),"best_available_start_nll":min((x for x in values if finite(x)),default=None),
            "interpretation_unreliable":bool(multi.get("warning")) or bool(lower)}


def expected_observations(campaign):
    result = {}
    for scenario, paths in read(campaign / "input_manifest.json")["inputs"].items():
        ds = read(ROOT / paths[2])
        channels = {}
        for channel in ds["series"]:
            points = [(float(t), float(y)) for t, y in zip(channel["t_min"], channel["y"]) if t > 0 and y is not None]
            channels[channel["species"]] = (np.array([p[0] for p in points]), np.array([p[1] for p in points]))
        result[scenario] = channels
    return result


def audit_prediction(result, expected, reference_sigma):
    prediction = result.get("prediction")
    if not prediction:
        return [], None
    errors, sse, weighted, count = [], 0.0, 0.0, 0
    sigma = prediction.get("common_sigma", {})
    if sigma != reference_sigma or result.get("common_sigma") != reference_sigma:
        errors.append("common_sigma differs from frozen reference")
    channels = prediction.get("channels", {})
    if set(channels) != set(expected):
        errors.append("held-out channel set differs from input")
    for name, channel in channels.items():
        try:
            t, y, pred = (np.array(channel[key], dtype=float) for key in ("time_min", "observed", "predicted"))
            et, ey = expected[name]
            if not (t.shape == y.shape == pred.shape == et.shape == ey.shape):
                errors.append(f"{name}: inconsistent array lengths")
                continue
            if not np.array_equal(t, et) or not np.allclose(y, ey, atol=1e-12, rtol=0):
                errors.append(f"{name}: observations differ from scenario input")
            if not np.all(np.isfinite(pred)):
                errors.append(f"{name}: nonfinite prediction")
                continue
            ss = float(np.sum((pred - y) ** 2))
            sse += ss
            weighted += ss / reference_sigma[name] ** 2
            count += len(y)
            if not math.isclose(channel["rmse"], math.sqrt(ss / len(y)), rel_tol=1e-8, abs_tol=1e-10):
                errors.append(f"{name}: saved RMSE does not match prediction")
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"{name}: {type(exc).__name__}: {exc}")
    if not count:
        return errors + ["no usable prediction points"], None
    rmse = math.sqrt(sse / count)
    for key, actual in (("heldout_score", weighted), ("rmse_all", rmse), ("n_obs", count)):
        if not finite(prediction.get(key)) or not math.isclose(prediction[key], actual, rel_tol=1e-8, abs_tol=1e-9):
            errors.append(f"saved {key} does not match recomputation")
    return errors, {"heldout_score": weighted, "rmse_all": rmse, "n_obs": count}


def collect(campaign):
    expected = expected_observations(campaign)
    expected_hashes = {}
    for scenario, paths in read(campaign / "input_manifest.json")["inputs"].items():
        dev_hashes = [digest(ROOT / path) for path in paths[:2]]
        joint_hash = hashlib.sha256(json.dumps(dev_hashes,separators=(",", ":")).encode()).hexdigest()
        expected_hashes[scenario] = {"data_sha256":joint_hash,"heldout_sha256":digest(ROOT / paths[2])}
    protocol_hash = read(campaign / "inventory.json")["protocol_sha256"]
    reference = ROOT / "investigations/runs/chapman750-propose_space-opus1/final/chapman2023_fig2_750C/predictions.json"
    sigma = read(reference)["common_sigma"]
    rows, problems, hashes = [], [], {}
    paths = sorted((campaign / "results").glob("*/*.json"))  # freeze the file list for this snapshot
    for path in paths:
        raw = path.read_bytes()
        hashes[rel(path)] = hashlib.sha256(raw).hexdigest()
        try:
            result = json.loads(raw)
            scenario, mode = result["scenario"], result["mode"]
            if path.parent.name != f"{scenario}__{mode}" or path.stem != result["dynamics_hash"]:
                raise ValueError("file path does not match result scenario/mode/dynamics")
            if scenario not in expected:
                raise ValueError(f"unknown scenario {scenario}")
            score_path = campaign / "scores" / path.parent.name / path.name
            score_status, score_numerics, prediction_source = None, None, "runner"
            score_identity_errors = []
            conditional_external = None
            if score_path.is_file():
                score_raw = score_path.read_bytes()
                hashes[rel(score_path)] = hashlib.sha256(score_raw).hexdigest()
                score = json.loads(score_raw)
                score_status, score_numerics = score.get("prediction_status"), score.get("numerics")
                prediction_source = rel(score_path)
                result["prediction"] = None
                if score.get("input_result_sha256") != hashlib.sha256(raw).hexdigest():
                    score_identity_errors.append("independent score does not match source result hash")
                if any(score.get(k) != result[k] for k in ("dynamics_hash", "scenario", "mode")):
                    score_identity_errors.append("independent score identifiers differ from source result")
                if score.get("fit_status") != result.get("fit", {}).get("status"):
                    score_identity_errors.append("independent score fit_status differs from source result")
                if not score_identity_errors and score_status in {"predicted", "predicted_verified_fallback"}:
                    result["prediction"] = score.get("prediction")
                conditional = score.get("conditional_external_initial_carbonate")
                if not score_identity_errors and conditional:
                    accepted = conditional.get("prediction_status") in {"predicted", "predicted_verified_fallback"}
                    cerr, cpred = (audit_prediction({**result,"prediction":conditional.get("prediction")},expected[scenario],sigma)
                                  if accepted else ([],None))
                    conditional_external = {"status":conditional.get("prediction_status"),"prediction":cpred,
                                            "audit_errors":cerr,"policy":conditional.get("policy"),
                                            "external_initial_carbonate":conditional.get("external_initial_carbonate")}
                    if cerr:
                        problems.append({"path":rel(score_path),"conditional_external_prediction_errors":cerr})
            errors, recomputed = audit_prediction(result, expected[scenario], sigma)
            errors += score_identity_errors
            fit_identity_valid = result.get("data_sha256") == expected_hashes[scenario]["data_sha256"] and result.get("protocol_sha256") == protocol_hash
            if not fit_identity_valid:
                errors.append("development input or protocol hash differs from frozen campaign inputs")
            if result.get("heldout_sha256") != expected_hashes[scenario]["heldout_sha256"]:
                errors.append("held-out input hash differs from scenario input")
            fit = result.get("fit", {})
            uncertainty = fit.get("uncertainty", {})
            parameters = uncertainty.get("params", [])
            multistart = fit.get("multistart", {})
            quality = optimizer_quality(fit)
            residuals = fit.get("residuals", {})
            rows.append({"path": rel(path), "scenario": scenario, "mode": mode,
                         "dynamics_hash": result["dynamics_hash"], "name": result.get("candidate_name"),
                         "status": result.get("status"), "fit_status": fit.get("status"),
                         "fit_identity_valid":fit_identity_valid,
                         "error": result.get("error"), "prediction_audit_errors": errors,
                         "prediction_source": prediction_source, "independent_prediction_status": score_status,
                         "prediction_numerics": score_numerics,
                         "conditional_external_initial_carbonate": conditional_external,
                         "prediction_valid": fit.get("status") == "fitted" and bool(result.get("prediction")) and not errors,
                         "aicc": fit.get("aicc"), "nll": fit.get("nll"), "k_total": fit.get("k_total"),
                         "k_kinetic_reported": fit.get("k_kinetic"), "k_noise": fit.get("k_noise"),
                         "k_initial_amount": fit.get("k_initial_amount", sum(p.get("kind") == "initial_amount" for p in parameters)),
                         "n_obs_dev": fit.get("n_obs"), "prediction": recomputed,
                         "own_noise_predictive_nll": (result.get("prediction") or {}).get("predictive_nll"),
                         "initial_carbonate_input": (result.get("prediction") or {}).get("initial_carbonate_input"),
                         "initial_carbonate_used": (result.get("prediction") or {}).get("initial_carbonate_used"),
                         "fitted_initial_amounts": fit.get("fitted_initial_amounts", {p["name"]: p["value"] for p in parameters if p.get("kind") == "initial_amount"}),
                         "initial_amount_flags": fit.get("initial_amount_flags", []),
                         "adequacy": residuals.get("adequacy"), "adequacy_reasons": residuals.get("adequacy_reasons", []),
                         "at_bound": [p["name"] for p in parameters if p.get("at_bound")],
                         "weak_parameters": [p["name"] for p in parameters if p.get("determinacy") in
                                             {"no_sensitivity", "poorly_determined", "not_determined_locally"}],
                         "parameters": parameters, "profile": fit.get("profile_likelihood", fit.get("profile")),
                         "n_optimum_replicates": quality["starts_near_returned_nll"],
                         "optimizer_quality":quality,"optimizer_warning":multistart.get("warning"),
                         "optimizer_budget_exhausted": multistart.get("budget_exhausted"),
                         "optimizer_formally_converged": multistart.get("formally_converged"),
                         "optimizer_note": multistart.get("note"), "fit_origin": result.get("fit_origin"),
                         "carbonate_independent": result.get("carbonate_independent"),
                         "topology": topology(result.get("submission", {})),
                         "signature": {k: result.get(k) for k in ("data_sha256", "heldout_sha256", "protocol_sha256", "engine_sha256", "adapter_sha256")}})
            if errors:
                problems.append({"path": rel(path), "errors": errors})
        except (ValueError, KeyError, TypeError) as exc:
            problems.append({"path": rel(path), "errors": [f"{type(exc).__name__}: {exc}"]})
    # Never compare a directory containing incompatible evaluator or input identities.
    for key in sorted({(r["scenario"], r["mode"]) for r in rows}):
        members = [r for r in rows if (r["scenario"], r["mode"]) == key]
        signatures = {json.dumps(r["signature"], sort_keys=True) for r in members}
        if len(signatures) != 1:
            problem = "mixed input/protocol/engine/adapter identities within one scenario and mode"
            problems.append({"scenario_mode": key, "errors": [problem]})
            for row in members:
                row["prediction_valid"] = False
                row["fit_identity_valid"] = False
                row["prediction_audit_errors"].append(problem)
    return rows, problems, hashes, sigma, len(paths)


def collect_rescues(campaign, sigma):
    """Audit separately budgeted numerical recovery; never insert it into main rows."""
    expected = expected_observations(campaign)
    rescues, hashes, problems = [], {}, []
    accepted_predictions = {"predicted", "predicted_verified_fallback"}
    for path in sorted((campaign/"numerics/rescue").glob("*.json")):
        raw = path.read_bytes()
        hashes[rel(path)] = hashlib.sha256(raw).hexdigest()
        rescue = json.loads(raw)
        errors = []
        primary_path = ROOT/rescue["input_result_path"]
        primary = read(primary_path)
        if digest(primary_path) != rescue["input_result_sha256"]:
            errors.append("rescue source primary hash mismatch")
        if rescue.get("primary_ranking_eligible") is not False:
            errors.append("rescue is not explicitly excluded from primary ranking")
        for key in ("scenario","mode","dynamics_hash","engine_sha256"):
            if rescue.get(key) != primary.get(key):
                errors.append(f"rescue/primary {key} mismatch")
        for filename, saved_hash in rescue["dataset_file_sha256"].items():
            if digest(ROOT/filename) != saved_hash:
                errors.append(f"rescue input hash mismatch: {filename}")
        nominal_path = campaign/"results/fig2_nominal__fixed"/f"{rescue['dynamics_hash']}.json"
        if rescue.get("nominal_result_sha256") != digest(nominal_path):
            errors.append("rescue nominal-source hash mismatch")
        original, extended = rescue["original_protocol"],rescue["extended_protocol"]
        for label, protocol in (("original",original),("extended",extended)):
            h = hashlib.sha256(json.dumps(protocol,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
            if h != rescue[f"{label}_protocol_sha256"]:
                errors.append(f"rescue {label} protocol hash mismatch")
        if rescue["original_protocol_sha256"] != primary["protocol_sha256"]:
            errors.append("rescue original protocol differs from primary")
        changes = {key:{name:[original[key].get(name),value] for name,value in extended[key].items()
                        if original[key].get(name)!=value} for key in extended
                   if isinstance(extended[key],dict) and extended[key] != original.get(key)}
        allowed = {"max_nfev","max_outer","max_ode_solves_per_fit"}
        if any(original.get(key)!=value for key,value in extended.items() if key != "optimizer") or any(
                key not in allowed for key in changes.get("optimizer",{})):
            errors.append("rescue changes more than documented optimizer budgets")
        stages = {}
        for label, stage in rescue["stages"].items():
            fit = stage.get("fit",{})
            converged = stage.get("status") == "converged" and fit.get("status") == "fitted" and finite(fit.get("nll"))
            accepted = stage.get("prediction_status") in accepted_predictions
            p_errors,p_summary = (audit_prediction({"prediction":stage.get("prediction"),"common_sigma":sigma},
                                                   expected[rescue["scenario"]],sigma) if accepted else ([],None))
            stages[label] = {"status":stage.get("status"),"converged":converged,"nll":fit.get("nll"),
                "aicc":fit.get("aicc"),"adequacy":fit.get("residuals",{}).get("adequacy"),
                "parameters":fit.get("uncertainty",{}).get("params",[]),"prediction":p_summary,
                "prediction_valid":converged and accepted and not p_errors,
                "channels":stage.get("prediction",{}).get("channels",{}) if accepted and not p_errors else {},
                "prediction_status":stage.get("prediction_status"),"audit_errors":p_errors,
                "initial_theta":stage.get("initial_theta"),"initial_carbonate_used":stage.get("prediction",{}).get("initial_carbonate_used"),
                "n_ode_solves":stage.get("n_ode_solves"),"wall_s":stage.get("wall_s")}
            errors += [f"{label}: {message}" for message in p_errors]
        converged = [name for name,stage in stages.items() if stage["converged"]]
        best = min(converged,key=lambda name:stages[name]["nll"]) if converged else None
        if best != rescue.get("best_converged_stage"):
            errors.append("saved best rescue stage differs from minimum converged development NLL")
        replicas = [name for name in converged if abs(stages[name]["nll"]-stages[best]["nll"]) <= .01] if best else []
        max_trajectory_difference, max_parameter_difference = None,None
        if best:
            differences=[]
            parameter_differences=[]
            reference=stages[best]
            ref_parameters={p["name"]:p["value"] for p in reference["parameters"]}
            for name in replicas:
                other=stages[name]
                if reference["prediction_valid"] and other["prediction_valid"]:
                    differences += [float(np.max(np.abs(np.array(reference["channels"][channel]["predicted"])-
                                                         np.array(other["channels"][channel]["predicted"]))))
                                    for channel in reference["channels"]]
                parameter_differences += [abs(p["value"]-ref_parameters[p["name"]]) for p in other["parameters"]
                                          if p["name"] in ref_parameters and p["kind"] == "Ea"]
            max_trajectory_difference=max(differences,default=None)
            max_parameter_difference=max(parameter_differences,default=None)
        entry={"path":rel(path),"sha256":hashes[rel(path)],"identity":rescue["identity"],
            "dynamics_hash":rescue["dynamics_hash"],"scenario":rescue["scenario"],"mode":rescue["mode"],
            "primary_path":rel(primary_path),"primary_ranking_eligible":False,"note":rescue.get("note"),
            "protocol_changes":changes,"audit_errors":errors,"stages":stages,"best_stage":best,
            "replicated_converged_stages":replicas,"independent_initial_states":len({tuple(stages[name]["initial_theta"]) for name in replicas}),
            "max_replica_prediction_difference":max_trajectory_difference,"max_replica_Ea_difference":max_parameter_difference,
            "remaining_optimizer_warnings":rescue.get("remaining_optimizer_warnings",[]),
            "lower_input_transfer":rescue.get("lower_input_transfer"),
            "active_stage":rescue.get("active_stage"),"updated_at":rescue.get("updated_at")}
        entry["replicated_best"]=len(replicas)>=2 and entry["independent_initial_states"]>=2
        if errors:
            problems.append({"path":rel(path),"errors":errors})
        rescues.append(entry)
    return rescues,hashes,problems


def collect_profiles(campaign):
    """Keep timed-out pilots visible; use only validated numerical intervals."""
    entries,hashes,problems=[],{},[]
    for path in sorted((campaign/"profiles").glob("*/*.json")):
        raw=path.read_bytes();body=json.loads(raw);hashes[rel(path)]=hashlib.sha256(raw).hexdigest()
        source_path=ROOT/body["input_result_path"]
        source=read(source_path)
        errors=[]
        if digest(source_path)!=body["input_result_sha256"]:
            errors.append("profile source-result hash mismatch")
        if any(body.get(key)!=source.get(key) for key in ("scenario","dynamics_hash")):
            errors.append("profile/source scenario or dynamics mismatch")
        if body["mode"]=="fixed_rescue":
            fit=source["stages"][body["fit_stage"]]["fit"]
            if body.get("rescue_identity")!=source["identity"] or body.get("protocol_sha256")!=source["extended_protocol_sha256"]:
                errors.append("profile rescue/protocol identity mismatch")
            if body.get("primary_result_sha256")!=digest(ROOT/source["input_result_path"]):
                errors.append("profile underlying primary-result hash mismatch")
            if body.get("engine_sha256")!=source["engine_sha256"]:
                errors.append("profile engine mismatch")
        else:
            fit=source["fit"]
            if body.get("fit_identity")!=fit.get("result_identity") or body.get("data_sha256")!=source["data_sha256"]:
                errors.append("profile adapter-fit/data identity mismatch")
        for filename,saved_hash in body.get("dataset_file_sha256",{}).items():
            if digest(ROOT/filename)!=saved_hash:
                errors.append(f"profile dataset hash mismatch: {filename}")
        fitted={p["name"]:p["value"] for p in fit.get("uncertainty",{}).get("params",[])}
        for name in body["parameters"]:
            saved=body.get("profiles",{}).get(name,{})
            parameter=saved.get("result",{}).get("params",{}).get(name,{})
            p_errors=errors.copy()
            if parameter and (name not in fitted or not math.isclose(parameter["mle"],fitted[name],rel_tol=1e-7,abs_tol=1e-8)):
                p_errors.append("profile MLE differs from source fit")
            if saved.get("result",{}).get("fit_identity") not in (None,body.get("fit_identity")):
                p_errors.append("parameter-level fit identity mismatch")
            attempts=saved.get("point_attempts",[])
            numerical_failure=parameter.get("classification")=="inconclusive_numerics" or bool(parameter.get("stopped_by_unconverged_refit_at_theta"))
            if attempts and not numerical_failure:
                for theta,delta in zip(parameter.get("grid_theta",[]),parameter.get("delta_nll",[])):
                    if math.isclose(theta,parameter["mle"],rel_tol=1e-12,abs_tol=1e-12):
                        continue
                    matches=[a for a in attempts if a.get("converged") and a.get("validation",{}).get("fixed_coordinates_exact")
                             and finite(a.get("validation",{}).get("nll_abs_difference"))
                             and a["validation"]["nll_abs_difference"]<=1e-6
                             and math.isclose(a.get("fixed",{}).get(name,math.inf),theta,rel_tol=1e-12,abs_tol=1e-12)]
                    if not any(math.isclose(a["nll"]-fit["nll"],delta,rel_tol=1e-7,abs_tol=1e-6) for a in matches):
                        p_errors.append(f"profile grid point lacks independently validated converged refit: {theta}")
            grid=parameter.get("grid_theta",[])
            usable=(saved.get("status")=="profiled" and parameter.get("classification") in {"identifiable","one_sided"}
                    and not parameter.get("better_optimum_found") and not numerical_failure and not p_errors and len(grid)>1)
            entry={"path":rel(path),"sha256":hashes[rel(path)],"identity":body["identity"],
                "scenario":body["scenario"],"mode":body["mode"],"dynamics_hash":body["dynamics_hash"],"parameter":name,
                "status":saved.get("status","pending"),"classification":parameter.get("classification"),"usable_interval":usable,
                "mle":parameter.get("mle"),"ci95":parameter.get("ci95") if usable else None,
                "lower_bounded":parameter.get("lower_bounded"),"upper_bounded":parameter.get("upper_bounded"),
                "better_optimum_found":parameter.get("better_optimum_found"),"numerical_failure":numerical_failure,
                "grid_theta":grid,"delta_nll":parameter.get("delta_nll",[]),"audit_errors":p_errors,
                "initial_sigma_policy":body.get("initial_sigma_policy"),"source_result":body["input_result_path"],
                "profile_job_sha256":body.get("profile_job_sha256"),"point_attempts":len(attempts),
                "updated_at":body.get("updated_at",body["created_at"])}
            if p_errors:
                problems.append({"path":rel(path),"parameter":name,"errors":p_errors})
            entries.append(entry)
    chosen={}
    for entry in entries:
        key=(entry["scenario"],entry["mode"],entry["dynamics_hash"],entry["parameter"])
        current=chosen.get(key)
        # Prefer a usable interval, then the latest checkpoint; never choose by interval width.
        if current is None or (entry["usable_interval"],entry["updated_at"])>(current["usable_interval"],current["updated_at"]):
            chosen[key]=entry
    return {"all_attempts":entries,"selected":list(chosen.values()),
            "selection_policy":"usable interval first, then latest checkpoint; no prediction-based selection"},hashes,problems


def collect_feasibility(campaign):
    path=campaign/"numerics/opus1_carbonate_feasibility.json"
    if not path.is_file():
        return None,{},[]
    raw=path.read_bytes();body=json.loads(raw);errors=[]
    candidate=read(ROOT/body["candidate_path"])
    if digest(ROOT/body["candidate_path"])!=body["candidate_sha256"]:
        errors.append("feasibility candidate hash mismatch")
    mechanism=candidate["mechanism"]
    species=body["species_order"]
    reactions=mechanism["reactions"]
    if body["reaction_order"] != [r["id"] for r in reactions]:
        errors.append("feasibility reaction order mismatch")
    matrix=np.zeros((len(species),len(reactions)))
    for j,reaction in enumerate(reactions):
        for side,sign in (("products",1),("reactants",-1)):
            for term in reaction[side]:
                matrix[species.index(term["species"]),j]+=sign*term["coeff"]
    weights=body["nonincreasing_certificate"]["weights"]
    vector=np.array([weights[name] for name in species])
    change=vector@matrix
    if not np.allclose(matrix,body["net_stoichiometric_matrix"],atol=1e-12,rtol=0) or np.any(change>1e-12):
        errors.append("feasibility nonincreasing certificate fails direct stoichiometric check")
    if weights.get("Li2CO3")!=1 or weights.get("Li2TiO3")!=.8 or any(v!=0 for k,v in weights.items() if k not in {"Li2CO3","Li2TiO3"}):
        errors.append("feasibility certificate is not the stated carbonate/intermediate supply rule")
    for row in body["rows"]:
        ds_path=ROOT/row["dataset_path"]
        if digest(ds_path)!=row["dataset_sha256"] or digest(ds_path)!=body["dataset_file_sha256"][row["dataset_path"]]:
            errors.append(f"feasibility dataset hash mismatch: {row['dataset_path']}")
        ds=read(ds_path)
        initial=ds["conditions"]["c0"]
        cap=initial.get("Li2TiO3",0)+initial["Li2CO3"]/.8
        observed=next(s for s in ds["series"] if s["species"]=="Li2TiO3")
        values=[y for t,y in zip(observed["t_min"],observed["y"]) if t>0 and y is not None]
        if not math.isclose(cap,row["intermediate_upper_bound"],abs_tol=1e-12) or not math.isclose(max(values),row["observed_intermediate_max"],abs_tol=1e-12):
            errors.append("feasibility cap or observed maximum differs from input")
        if sum(y>cap+1e-12 for y in values)!=row["n_points_above_bound"]:
            errors.append("feasibility exceedance count differs from input")
    if body["declared_conservation"]!=mechanism.get("conservation"):
        errors.append("feasibility declared conservation mismatch")
    body.update({"path":rel(path),"sha256":hashlib.sha256(raw).hexdigest(),"audit_errors":errors})
    return body,{rel(path):body["sha256"]},([{"path":rel(path),"errors":errors}] if errors else [])


def coverage(rows, members):
    selected = [r for r in rows if r["dynamics_hash"] in members]
    ids = {r["dynamics_hash"] for r in selected}
    if len(ids) != len(selected):
        raise ValueError("Duplicate dynamics in a scenario/mode snapshot")
    fit = [r for r in selected if r["fit_status"] == "fitted"]
    return {"declared": len(members), "recorded": len(ids), "missing": len(members - ids),
            "all_declared_recorded": ids == members, "fitted": len(fit),
            "prediction_valid": sum(r["prediction_valid"] for r in selected),
            "independent_prediction_statuses": dict(Counter(r["independent_prediction_status"] or "not_rescored" for r in selected)),
            "statuses": dict(Counter(r["status"] for r in selected)),
            "fit_origins": dict(Counter((r["fit_origin"] or {}).get("kind", "not_recorded") for r in selected)),
            "poor_adequacy": sum(r["adequacy"] == "poor" for r in fit),
            "fits_with_any_bound": sum(bool(r["at_bound"]) for r in fit),
            "fits_with_weak_parameters": sum(bool(r["weak_parameters"]) for r in fit),
            "fit_budget_exhausted": sum(bool(r["optimizer_budget_exhausted"]) for r in selected),
            "fits_with_optimizer_warning":sum(r["optimizer_quality"]["interpretation_unreliable"] for r in fit),
            "fits_accepted_by_replication_without_formal_convergence":sum(r["optimizer_quality"]["accepted_by_replication_without_formal_convergence"] for r in fit),
            "audit_failed": sum(bool(r["prediction_audit_errors"]) for r in selected)}


def baseline_rank(candidate, baseline, declared):
    cov = coverage(baseline, declared)
    if not candidate or not candidate["prediction_valid"] or not cov["all_declared_recorded"] or cov["audit_failed"]:
        return {"available": False, "baseline_recorded": cov["recorded"], "baseline_declared": len(declared),
                "reason": "baseline outcomes incomplete, prediction unavailable, or audit failure"}
    scored = [r for r in baseline if r["prediction_valid"]]
    value = candidate["prediction"]["heldout_score"]
    better = sum(r["prediction"]["heldout_score"] < value - 1e-9 * max(1, abs(value)) for r in scored)
    return {"available": True, "insertion_rank": better + 1, "baseline_better": better,
            "baseline_scored": len(scored), "baseline_declared": len(declared),
            "note": "1 + better baseline models; outsider may rank 154 against 153 scored baselines"}


def selection(rows, members, baseline, baseline_members):
    subset = [r for r in rows if r["dynamics_hash"] in members]
    # Prediction failure must not change which candidate development AICc selected.
    eligible = [r for r in subset if r["fit_status"] == "fitted" and finite(r["aicc"]) and r["fit_identity_valid"]]
    predicted = [r for r in eligible if r["prediction_valid"]]
    dev = min(eligible, key=lambda r: (r["aicc"], r["dynamics_hash"])) if eligible else None
    retro = min(predicted, key=lambda r: (r["prediction"]["heldout_score"], r["dynamics_hash"])) if predicted else None
    return {"coverage": coverage(rows, members), "development_selected": dev, "retrospective_best_prediction": retro,
            "development_selected_baseline_rank": baseline_rank(dev, baseline, baseline_members),
            "retrospective_best_baseline_rank": baseline_rank(retro, baseline, baseline_members)}


def declaration_analysis(campaign, rows, groups):
    """Partition the saved representative submissions, preserving the old denominator."""
    path=campaign/"repaired_records.json"
    records=read(path)
    if {r["dynamics_hash"] for r in records}!=groups["repaired"] or len(records)!=len(groups["repaired"]):
        raise ValueError("Declaration analysis records do not match the old repaired union")
    families=defaultdict(set)
    for record in records:
        mechanism=record["submission"]["mechanism"]
        elements=set(mechanism["conservation"]["elements"])
        declaration="Ti+Li" if {"Ti","Li"}<=elements else "Ti-only" if elements=={"Ti"} else "+".join(sorted(elements))
        independent=all(not any(t["species"]=="Li2CO3" for t in r["reactants"])
                        and "Li2CO3" not in r["rate_law"].get("orders",{}) for r in mechanism["reactions"])
        if independent!=record["carbonate_independent"]:
            raise ValueError(f"Carbonate classification differs from runner inventory: {record['dynamics_hash']}")
        families[(declaration,"independent" if independent else "dependent")].add(record["dynamics_hash"])
    result=[]
    for (declaration,dependence),members in sorted(families.items()):
        scenarios={}
        for scenario in ("fig2_nominal","fig2_lower"):
            selected=[r for r in rows if r["scenario"]==scenario and r["mode"]=="fixed"]
            baseline=[r for r in selected if r["dynamics_hash"] in groups["baseline"]]
            scenarios[scenario]=selection(selected,members,baseline,groups["baseline"])
        result.append({"declared_elements":declaration,"carbonate_classification":dependence,
                       "declared_dynamics":len(members),"dynamics_hashes":sorted(members),"scenarios":scenarios})
    return {"source_path":rel(path),"source_sha256":digest(path),"families":result,
            "unit":"one saved representative submission per old-union dynamics hash; not unique physical mechanisms",
            "carbonate_rule":"independent only when carbonate is absent from every reactant list and rate-order map; dependent is the conservative complement"}


def declaration_report(snapshot):
    analysis=snapshot["declaration_analysis"]
    lines=["", "## Declared conservation and carbonate dependence", "",
           "These are separate properties. A Ti-only model can use carbonate in some reactions while allowing other routes "
           "to make the same intermediate without it. The table partitions the old 904 representative submissions used by "
           "the campaign; it does not count unique physical mechanisms or resolve chemistry aliases that share dynamics. "
           "Carbonate-independent means carbonate is absent from every reactant list and rate-order map. The dependent "
           "category is the conservative complement, not proof that every fitted pathway depends on carbonate.", "",
           "| Declaration / carbonate use | Input | Recorded / declared | Valid predictions | Optimizer warnings | Current development selection | AICc | Common score |",
           "|---|---|---:|---:|---:|---|---:|---:|"]
    for family in analysis["families"]:
        for scenario,entry in family["scenarios"].items():
            cov=entry["coverage"];row=entry["development_selected"]
            label=f"{family['declared_elements']} / {family['carbonate_classification']}"
            choice=result_link(row) if row else "none fitted"
            if not cov["all_declared_recorded"]:
                choice += " (partial set)"
            if row and row["optimizer_quality"]["interpretation_unreliable"]:
                choice += " (optimizer warning)"
            pred=row["prediction"] if row and row["prediction_valid"] else {}
            lines.append(f"| {label} | {scenario} | {cov['recorded']} / {cov['declared']} | {cov['prediction_valid']} | "
                         f"{cov['fits_with_optimizer_warning']} | {choice} | {aicc_number(row['aicc']) if row else '—'} | "
                         f"{number(pred.get('heldout_score'),5)} |")
    leader=snapshot["summaries"]["fig2_lower__fixed"]["repaired"]["development_selected"]
    if leader and not leader["topology"]["declares_lithium_conservation"] and leader["topology"]["carbonate_free_intermediate_routes"]:
        routes=", ".join(leader["topology"]["carbonate_free_intermediate_routes"])
        lines += ["", f"The current lower-input development leader {result_link(leader)} declares Ti-only conservation and "
                  f"includes carbonate-free intermediate production in {routes}. That route avoids the original Opus model's "
                  "specific carbonate supply ceiling. Selecting this model family would not establish a lithium-conserving physical mechanism."]
    complete=snapshot["summaries"]["fig2_lower__fixed"]["repaired"]["coverage"]["all_declared_recorded"]
    lines += ["", ("All lower-input outcomes are recorded; failures and optimizer warnings remain visible. " if complete else
                    "The lower-input set remains incomplete, and optimizer warnings stay visible. ")+
              "These are model-family comparisons, not established physical mechanisms. "
              "[Declaration and rate-law source](../"+analysis["source_path"]+")."]
    return lines


def pairs(rows, anchors, summaries):
    lookup = {(r["scenario"], r["mode"], r["dynamics_hash"]): r for r in rows}
    known = {name: v["dynamics_hash"] for name, v in anchors.items()}
    for scenario in ("fig2_nominal", "fig2_lower"):
        for group in ("comparable", "repaired"):
            row = summaries.get(f"{scenario}__fixed", {}).get(group, {}).get("development_selected")
            if row:
                known[f"{scenario}_{group}_current_development_selected"] = row["dynamics_hash"]
    definitions = [("primary_Li", "fig2_nominal", "fig2_lower", "fixed", "fixed"),
                   ("S1_Li", "s1_nominal", "s1_lower", "fixed", "fixed"),
                   ("extraction_nominal", "fig2_nominal", "s1_nominal", "fixed", "fixed"),
                   ("extraction_lower", "fig2_lower", "s1_lower", "fixed", "fixed"),
                   ("fig2_shared_initial_vs_original", "fig2_nominal", "fig2_lower", "fixed", "shared"),
                   ("fig2_per_temperature_initial_vs_original", "fig2_nominal", "fig2_lower", "fixed", "per_temperature")]
    for scenario in SCENARIOS:
        for mode in ("shared", "per_temperature"):
            definitions.append((f"initial_amount_{mode}_{scenario}", scenario, scenario, "fixed", mode))
    all_pairs, known_pairs = [], []
    dynamics = {r["dynamics_hash"] for r in rows}
    for comparison, left, right, lm, rm in definitions:
        for dh in sorted(dynamics):
            a, b = lookup.get((left, lm, dh)), lookup.get((right, rm, dh))
            if not a or not b or a["fit_status"] != "fitted" or b["fit_status"] != "fitted":
                continue
            ap, bp = ({p["name"]: p for p in row["parameters"]} for row in (a, b))
            changes = []
            for name in sorted(ap.keys() & bp.keys()):
                x, y = ap[name], bp[name]
                changes.append({"name": name, "kind": x["kind"], "before": x["value"], "after": y["value"],
                                "delta": y["value"] - x["value"],
                                "ratio": y["value"] / x["value"] if x["value"] != 0 else None,
                                "before_at_bound": x.get("at_bound"), "after_at_bound": y.get("at_bound"),
                                "before_determinacy": x.get("determinacy"), "after_determinacy": y.get("determinacy")})
            valid = a["prediction_valid"] and b["prediction_valid"]
            pair = {"comparison": comparison, "dynamics_hash": dh, "before_path": a["path"], "after_path": b["path"],
                    "before_scenario_mode": f"{left}__{lm}", "after_scenario_mode": f"{right}__{rm}",
                    "prediction_pair_valid": valid, "before_aicc": a["aicc"], "after_aicc": b["aicc"],
                    "before_rmse": a["prediction"]["rmse_all"] if valid else None,
                    "after_rmse": b["prediction"]["rmse_all"] if valid else None,
                    "before_score": a["prediction"]["heldout_score"] if valid else None,
                    "after_score": b["prediction"]["heldout_score"] if valid else None,
                    "before_adequacy": a["adequacy"], "after_adequacy": b["adequacy"],
                    "before_prediction_source":a["prediction_source"],"after_prediction_source":b["prediction_source"],
                    "carbonate_independent": a["carbonate_independent"], "parameter_changes": changes,
                    "optimizer_quality_before":a["optimizer_quality"],"optimizer_quality_after":b["optimizer_quality"],
                    "optimizer_warning_on_either_side":a["optimizer_quality"]["interpretation_unreliable"] or b["optimizer_quality"]["interpretation_unreliable"],
                    "initial_amount_before": a["fitted_initial_amounts"], "initial_amount_after": b["fitted_initial_amounts"],
                    "known_labels": [name for name, value in known.items() if value == dh]}
            all_pairs.append(pair)
            if pair["known_labels"]:
                known_pairs.append(pair)
    return all_pairs, known_pairs, known


def number(value, digits=3):
    return f"{value:.{digits}g}" if finite(value) else "—"


def aicc_number(value):
    return f"{value:.1f}" if finite(value) else "—"


def result_link(row):
    if not row:
        return "not yet available"
    return f"[`{row['dynamics_hash'][:10]}`](../{row['path']})"


def control_checks(all_pairs, groups):
    results = {}
    for name, keep in (("baseline", groups["baseline"]), ("all_carbonate_independent", groups["repaired"])):
        matched = [p for p in all_pairs if p["comparison"] == "primary_Li" and p["dynamics_hash"] in keep
                   and p["carbonate_independent"] and p["prediction_pair_valid"]]
        results[name] = {"paired_audited_predictions": len(matched),
                         "mixed_runner_and_independent_prediction_sources":sum((p["before_prediction_source"]=="runner") !=
                                                                                (p["after_prediction_source"]=="runner") for p in matched),
                         "max_abs_AICc_change": max((abs(p["after_aicc"]-p["before_aicc"]) for p in matched),default=None),
                         "max_abs_common_score_change": max((abs(p["after_score"]-p["before_score"]) for p in matched),default=None),
                         "max_relative_common_score_change": max((abs(p["after_score"]-p["before_score"])/max(1.,abs(p["before_score"])) for p in matched),default=None),
                         "max_abs_RMSE_change": max((abs(p["after_rmse"]-p["before_rmse"]) for p in matched),default=None),
                         "max_abs_parameter_change": max((abs(c["delta"]) for p in matched for c in p["parameter_changes"]),default=None)}
    return results


def overlay_data(snapshot, campaign, hashes):
    """Use frozen choices, never select these illustrative curves by 750 C error."""
    expected=expected_observations(campaign)
    curves,errors=[],[]
    definitions=[("original_baseline_top1","fig2_nominal__fixed","Frozen baseline", "#777777","--"),
                 ("original_opus1_top1","fig2_nominal__fixed","Original Opus choice · nominal Li", "#0072B2","-"),
                 ("fresh_opus_top1","fig2_lower__fixed","Fresh frozen Opus choice · lower Li", "#009E73","-.")]
    for anchor,key,label,color,style in definitions:
        row=snapshot["frozen_choice_results"].get(anchor,{}).get(key)
        if not row or not row["prediction_valid"]:
            continue
        path=ROOT/(row["path"] if row["prediction_source"] == "runner" else row["prediction_source"])
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != hashes[rel(path)]:
            errors.append(f"Overlay source changed after snapshot: {rel(path)}")
            continue
        prediction=json.loads(raw).get("prediction")
        issues,recomputed=audit_prediction({"prediction":prediction,"common_sigma":snapshot["common_sigma"]},
                                           expected[row["scenario"]],snapshot["common_sigma"])
        if issues or not recomputed:
            errors += [f"Overlay {label}: {message}" for message in issues or ["missing prediction"]]
            continue
        curves.append({"label":label,"anchor":anchor,"source":rel(path),"source_sha256":hashes[rel(path)],
                       "dynamics_hash":row["dynamics_hash"],"scenario":row["scenario"],"mode":row["mode"],
                       "color":color,"linestyle":style,"prediction":recomputed,"channels":prediction["channels"],
                       "initial_carbonate_used":prediction.get("initial_carbonate_used"),
                       "optimizer_warning":row["optimizer_quality"]["interpretation_unreliable"]})
    original=snapshot["anchors"]["original_opus1_top1"]["dynamics_hash"]
    candidates=[r for r in snapshot["numerical_rescues"] if r["dynamics_hash"] == original
                and r["scenario"] == "fig2_lower" and not r["audit_errors"] and r["best_stage"]]
    # If future rescue protocols differ, do not pick one retrospectively without an explicit choice.
    if len(candidates)>1:
        errors.append("Multiple lower-Li rescue protocols exist; overlay needs an explicit rescue choice")
    elif candidates:
        rescue=candidates[0]
        best=rescue["stages"][rescue["best_stage"]]
        if best["prediction_valid"]:
            curves.insert(2,{"label":"Same Opus choice · lower Li, recovered","anchor":"original_opus1_lower_rescue",
                "source":rescue["path"],"source_sha256":rescue["sha256"],"rescue_stage":rescue["best_stage"],
                "dynamics_hash":original,"scenario":"fig2_lower","mode":"fixed, extended optimizer budget",
                "color":"#D55E00","linestyle":"-","prediction":best["prediction"],"channels":best["channels"],
                "initial_carbonate_used":best["initial_carbonate_used"],"optimizer_warning":False})
    for curve in curves:
        for channel,(t,y) in expected["fig2_nominal"].items():
            saved=curve["channels"][channel]
            if not np.array_equal(t,saved["time_min"]) or not np.array_equal(y,saved["observed"]):
                errors.append(f"Overlay {curve['label']} observations differ from shared Fig. 2 points")
    return {"selection_policy":"frozen baseline and AI development choices; rescue selected only by converged development NLL",
            "observations":{name:{"time_min":t.tolist(),"observed":y.tolist()} for name,(t,y) in expected["fig2_nominal"].items()},
            "curves":curves,"audit_errors":errors,"fresh_frozen":"fresh_opus_top1" in snapshot["anchors"],
            "fresh_curve_available":any(c["anchor"] == "fresh_opus_top1" for c in curves)}


def rescue_report(snapshot):
    lines=["", "## Numerical recovery — separate from the standard campaign", "",
           "These checks keep the same objective, observations, noise model, parameter bounds and integration settings, with larger "
           "optimizer budgets. They are excluded from standard campaign coverage, selections and ranks. A recovered prediction's "
           "diagnostic insertion rank compares its score with the saved baseline; it does not replace any primary result.", "",
           "| Candidate / purpose | Input | Standard → recovered NLL | Recovered AICc | Agreeing starts at best NLL | Common score | RMSE | Diagnostic baseline rank |",
           "|---|---|---:|---:|---:|---:|---:|---|"]
    if not snapshot["numerical_rescues"]:
        return []
    for rescue in snapshot["numerical_rescues"]:
        if rescue["audit_errors"]:
            lines += [f"Recovery artifact `{rescue['dynamics_hash'][:10]}` failed its source/prediction audit; excluded from interpretation: "
                      + "; ".join(rescue["audit_errors"]), ""]
            continue
        best=rescue["stages"].get(rescue["best_stage"])
        if not best:
            lines += [f"Recovery for `{rescue['dynamics_hash'][:10]}` has no formally converged start yet.", ""]
            continue
        n=len(rescue["replicated_converged_stages"])
        prediction=best["prediction"] if best["prediction_valid"] else {}
        primary=rescue.get("primary_summary") or {}
        purpose=", ".join(rescue["frozen_selection_labels"]) or "carbonate-independent numerical control"
        rank=rescue["diagnostic_baseline_rank"]
        ranktext=f"{rank['insertion_rank']} ({rank['baseline_scored']} baseline scored)" if rank["available"] else "pending"
        if not rescue["replicated_best"]:
            ranktext+="; unreplicated best"
        lines.append(f"| [`{rescue['dynamics_hash'][:10]}`](../{rescue['path']}); {purpose} | {rescue['scenario']} | "
                     f"{number(primary.get('nll'),7)} → {number(best['nll'],7)} | {aicc_number(best['aicc'])} | "
                     f"{n}{' (best not replicated)' if not rescue['replicated_best'] else ''} | "
                     f"{number(prediction.get('heldout_score'),6)} | {number(prediction.get('rmse_all'),6)} | {ranktext} |")
    lines += ["", "The three carbonate-independent checks are numerical controls, not AI-selected discoveries. "
              "Their nominal-data recoveries are not transferred to lower inputs without a separate invariance check. "
              "A formally converged best fit reached only once remains unreplicated. Poor residual adequacy and model uncertainty "
              "remain after numerical recovery."]
    original=snapshot["anchors"]["original_opus1_top1"]["dynamics_hash"]
    for rescue in snapshot["numerical_rescues"]:
        if rescue["dynamics_hash"]!=original or rescue["audit_errors"] or not rescue["best_stage"]:
            continue
        best=rescue["stages"][rescue["best_stage"]]
        changes=", ".join(f"`{name}` {before} → {after}" for name,(before,after) in rescue["protocol_changes"].get("optimizer",{}).items())
        lines += ["",f"**Original Opus selection:** {len(rescue['replicated_converged_stages'])} formally converged starts agree. "
                  f"Maximum trajectory disagreement is {number(rescue['max_replica_prediction_difference'],3)} formula units per mole Ti. "
                  f"Budget changes: {changes}. The recovered lower-Li RMSE is "
                  f"{number(best['prediction']['rmse_all'],6)}; the nominal result is "
                  f"{number(snapshot['frozen_choice_results']['original_opus1_top1']['fig2_nominal__fixed']['prediction']['rmse_all'],6)}. "
                  f"Residual adequacy remains **{best['adequacy']}**. This is conditional on the submitted network and assumed inputs.", ""]
        rows=snapshot["frozen_choice_results"].get("original_opus1_top1",{})
        nominal=rows.get("fig2_nominal__fixed")
        if nominal:
            before={p["name"]:p for p in nominal["parameters"]}
            lines += ["| Parameter | Nominal fit | Recovered lower-Li fit | Bound flag, recovered |", "|---|---:|---:|---|"]
            for parameter in best["parameters"]:
                if parameter["name"] in before and parameter["kind"] in {"Ea","n_avrami"}:
                    unit="kJ/mol" if parameter["kind"] == "Ea" else "dimensionless"
                    lines.append(f"| `{parameter['name']}` ({unit}) | {number(before[parameter['name']]['value'],5)} | "
                                 f"{number(parameter['value'],5)} | {parameter.get('at_bound')} |")
        active=rescue.get("active_stage")
        if active:
            lines += ["",f"An additional independent check, `{active['label']}`, was still active at the saved snapshot."]
    return lines


def profile_report(snapshot):
    selected=snapshot["profiles"]["selected"]
    if not selected:
        return []
    lines=["", "## Conditional uncertainty profiles", "",
           "Each range reoptimizes the other parameters and noise scales while fixing one parameter; the nominal 95% cutoff is "
           "ΔNLL = 1.92. These ranges condition on this network, extraction, noise model and initial-state policy. They do not measure "
           "physical starting composition or include model error. Residual adequacy is poor. A protocol-bound endpoint is not a likelihood-derived upper bound.", "",
           "| Fit | Parameter | Estimate | Approximate conditional 95% range | Interpretation |", "|---|---|---:|---|---|"]
    for row in selected:
        label={"fixed_rescue":"Lower Li, recovered fixed start","shared":"Shared fitted start","per_temperature":"Separate fitted starts"}.get(row["mode"],row["mode"])
        if row["usable_interval"]:
            lo,hi=row["ci95"]
            interval=f"{number(lo,6)} – {number(hi,6)}"
            note="both ends bounded by likelihood" if row["lower_bounded"] and row["upper_bounded"] else "one-sided; unbounded end stops at imposed parameter bound"
        else:
            interval="withheld"
            note="pending" if row["status"]=="pending" else "numerically inconclusive; placeholder endpoints are not confidence limits"
        lines.append(f"| [{label}](../{row['path']}) | `{row['parameter']}` | {number(row['mle'],6)} | {interval} | {note} |")
    failed=sum(row["numerical_failure"] for row in snapshot["profiles"]["all_attempts"])
    lines += ["",f"Earlier numerical failures remain in the local provenance export ({failed} parameter attempts); their equal-endpoint placeholders are suppressed. "
              "The validated lower-Li recovery profiles initialize noise scales from the recovered fit, then fully update them at every constrained fit. "
              "This is a convergence aid, not fixed-noise fitting. Activation energies are in kJ/mol; initial amounts are formula units per mole Ti. "
              "The recovered lower-Li and shared-start activation-energy ranges overlap."]
    return lines


def feasibility_report(snapshot):
    body=snapshot.get("carbonate_feasibility")
    if not body:
        return []
    if body["audit_errors"]:
        return ["", "Supply-rule diagnostic withheld: " + "; ".join(body["audit_errors"])]
    lines=["", "## Why the lower starting amounts strain the original Opus model", "",
           "This network consumes 0.8 Li2CO3 units for each unit of the Li2TiO3 channel it makes. Its equations require "
           "`Li2CO3 + 0.8 × Li2TiO3` to stay constant or decrease. With nonnegative amounts and no initial intermediate, "
           "the Li2TiO3 channel therefore cannot exceed `initial Li2CO3 / 0.8`, regardless of the fitted rate constants.", "",
           "| Temperature | Lower initial carbonate | Model's Li2TiO3 ceiling | Digitized maximum | Points above ceiling |",
           "|---|---:|---:|---:|---:|"]
    for row in body["rows"]:
        if row["scenario"]=="fig2_lower":
            lines.append(f"| {row['temperature_C']:g} °C | {number(row['initial_carbonate'],4)} | {number(row['intermediate_upper_bound'],4)} | "
                         f"{number(row['observed_intermediate_max'],6)} | {row['n_points_above_bound']} / {row['n_intermediate_points']} |")
    lines += ["", "The 700 and 725 °C development observations already exceed this ceiling. Changing activation energies cannot remove "
              "that incompatibility while retaining the same network and initial amounts. This is a property of the model's supply rule, "
              "**not elemental lithium conservation**: the model declares Ti-only conservation, and its nominal R1 formulas create "
              "0.4 Li atoms per reaction extent. The diagnostic does not establish which starting composition, extraction or physical "
              f"mechanism is correct. [Source and stoichiometric certificate](../{body['path']})."]
    return lines


def render_report(snapshot, output, figure_dir, campaign):
    summary, groups = snapshot["summaries"], snapshot["membership_counts"]
    stage = ("Both primary Fig. 2 × 904 outcome grids have been recorded; failures remain part of the result."
             if snapshot["primary_fixed_grid_all_outcomes_recorded"] else "This is an in-progress retrospective sensitivity analysis.")
    lines = ["# Chapman lithium sensitivity — results snapshot", "", f"Generated {snapshot['generated_at_utc']}.", "",
             f"**{stage}** Every count below comes from saved result files. "
             "A recorded outcome may be a failed fit; a missing outcome may be queued, running, or not scheduled. "
             "No full-campaign conclusion follows from a provisional winner.", "",
             "The primary comparison changes only the starting Li2CO3 assumption in the original Fig. 2 inputs. "
             "Fits use 700 + 725 °C; predictions use 750 °C with frozen kinetics. The lower initial amounts are hypotheses "
             "(0.28, 0.30, 0.36 formula units per mole Ti), not new measured starting compositions. "
             "The S1 comparison changes extraction on the same time grid and uses the same published experiments.", "",
             "## Coverage and failures", "",
             f"The declared union contains **{groups['comparable']} originally valid dynamics** and **{groups['repaired']} "
             f"including representation repairs** ({groups['repaired_only']} added dynamics). The fixed baseline has "
             f"{groups['baseline']} members; saved Opus1 has {groups['prior_opus1']} originally valid dynamics "
             f"({groups['prior_opus1_repaired']} with repairs). Membership is reconstructed from source-record and alias links.", "",
             "| Input / initial-state mode | Recorded / 904 | Comparable recorded / 860 | Valid 750 °C predictions | Failed outcomes | Missing |",
             "|---|---:|---:|---:|---|---:|"]
    for key, subsets in summary.items():
        c, original = subsets["repaired"]["coverage"], subsets["comparable"]["coverage"]
        failures = ", ".join(f"{status}: {n}" for status, n in c["statuses"].items() if status != "fitted") or "none recorded"
        lines.append(f"| {key} | {c['recorded']} / {c['declared']} | {original['recorded']} / {original['declared']} | "
                     f"{c['prediction_valid']} | {failures} | {c['missing']} |")
    lines += ["", "For S1 and optional fitted-initial-state modes, the 904 denominator above describes coverage of the old union. "
              "Their smaller declared target lists are tracked below; a target list alone does not establish that all its work has started.", "",
              "| Follow-up | Recorded / declared targets | Audited predictions | Missing |", "|---|---:|---:|---:|"]
    for key,entry in snapshot["declared_followup_targets"].items():
        c=entry["coverage"]
        lines.append(f"| [{key}](../{entry['path']}) | {c['recorded']} / {c['declared']} | {c['prediction_valid']} | {c['missing']} |")
    lines += ["", "![Recorded outcome coverage](examples/chapman_li_oct22/coverage.png)", "",
              "| Input / mode | Baseline outcomes / 154 | Baseline predictions | Saved Opus1 outcomes / 208 | Saved Opus1 predictions |",
              "|---|---:|---:|---:|---:|"]
    for key, subsets in summary.items():
        b, o = subsets["baseline"]["coverage"], subsets["prior_opus1"]["coverage"]
        lines.append(f"| {key} | {b['recorded']} / {b['declared']} | {b['prediction_valid']} | {o['recorded']} / {o['declared']} | {o['prediction_valid']} |")
    fresh = snapshot.get("fresh_opus")
    if fresh:
        lines += ["", "### Fresh lower-lithium proposals — separate set", "",
                  f"Exported {fresh['generated_at_utc']}: {fresh['candidate_files']} saved candidates, "
                  f"**{fresh['unique_valid_dynamics']} unique valid dynamics**; {fresh['overlap_with_old_904']} overlap the old 904 "
                  f"and {fresh['new_relative_to_old_904']} are additional dynamics. The old 860/904 denominators are unchanged. "
                  "Membership uses the fresh dynamics set, even when a reused result retains an older source label. "
                  "This is a snapshot of proposals submitted so far, not a claim that proposal or fitting work is complete.", "",
                  "| Input / mode | Fresh outcomes / exported dynamics | Valid predictions | Missing |", "|---|---:|---:|---:|"]
        for key, subsets in summary.items():
            c = subsets["fresh_opus"]["coverage"]
            lines.append(f"| {key} | {c['recorded']} / {c['declared']} | {c['prediction_valid']} | {c['missing']} |")
        frozen = fresh.get("frozen_selection")
        lines += ["", (f"The fresh run froze `{frozen['candidate_id']}` / `{frozen['dynamics_hash'][:10]}` at {frozen['frozen_at']}."
                        if frozen else "**The fresh run has not frozen a selection in this export.** A current best completed fit is not its final selected model."), ""]
    rescored = [(key, sub["repaired"]["coverage"]["independent_prediction_statuses"]) for key,sub in summary.items()
                if any(s != "not_rescored" for s in sub["repaired"]["coverage"]["independent_prediction_statuses"])]
    if rescored:
        lines += ["", "Independent prediction checks are recorded separately from the original runner outcome:", "",
                  "| Input / mode | Independent prediction statuses |", "|---|---|"]
        for key, statuses in rescored:
            lines.append(f"| {key} | " + ", ".join(f"{name}: {count}" for name,count in statuses.items()) + " |")
    lines += ["", "## Selection and prediction are separate", "",
              "Development selection minimizes AICc on 700 + 725 °C. Retrospective best prediction minimizes the common weighted "
              "750 °C squared error after looking at that temperature. The latter is not a prospectively selected model. "
              "All selections are provisional until their declared set has outcomes recorded; numerical failures remain part of coverage.", "",
              "The common score is `sum((prediction − observation)^2 / reference_sigma[channel]^2)`, using the original frozen reference "
              "scales for every candidate and condition. RMSE is unweighted, in formula units per mole Ti. A model's own predictive "
              "noise does not determine the rank. AICc across different extractions is not evidence for which extraction is correct.", "",
              "| Input / mode; candidate set | Choice | Candidate | AICc | Common prediction score ↓ | RMSE ↓ | Baseline insertion rank |",
              "|---|---|---|---:|---:|---:|---|"]
    for key, subsets in summary.items():
        for group in ("baseline", "prior_opus1", "comparable", "repaired", "fresh_opus"):
            if group not in subsets:
                continue
            data = subsets[group]
            if not data["coverage"]["recorded"]:
                continue
            for which, label, rankkey in (("development_selected", "development-selected", "development_selected_baseline_rank"),
                                          ("retrospective_best_prediction", "retrospective best", "retrospective_best_baseline_rank")):
                row = data[which]
                if row is None:
                    continue
                pred, rank = (row["prediction"] or {}) if row["prediction_valid"] else {}, data[rankkey]
                ranktxt = (f"{rank['insertion_rank']} ({rank['baseline_scored']}/{rank['baseline_declared']} baseline scored)"
                           if rank["available"] else "pending baseline / prediction")
                provisional = "" if data["coverage"]["all_declared_recorded"] and (group != "fresh_opus" or fresh.get("frozen_selection")) else " (provisional)"
                if row["optimizer_quality"]["interpretation_unreliable"]:
                    provisional += "; optimizer warning"
                lines.append(f"| {key}; {GROUP_LABELS[group]} | {label}{provisional} | {result_link(row)} | "
                             f"{aicc_number(row['aicc'])} | {number(pred.get('heldout_score'), 4)} | {number(pred.get('rmse_all'), 4)} | {ranktxt} |")
    lines += ["", "Baseline insertion rank is one plus the number of better-scoring baseline members under the **same extraction and lithium scenario**, "
              "using fixed initial-state baseline fits even for adapter comparisons. It is withheld until all 154 baseline outcomes are recorded. "
              "The original baseline had 153 fitted outcomes; a failed fit is not assigned an artificial worst score. "
              "An outside candidate can rank 154 against 153 scored baseline candidates. Rank alone does not establish predictive accuracy.", ""]
    if fresh:
        lines += ["## Frozen AI choices", "",
                  "The original run selected on nominal lithium. The fresh run selects on the lower-lithium development inputs. "
                  "These choices are fixed by each run's saved selection file, not replaced by the best 750 °C predictor. "
                  "Both can be evaluated under the same scenario once their result files are available.", "",
                  "| Frozen choice | Selection status | Fig. 2 nominal RMSE | Fig. 2 lower-Li RMSE |", "|---|---|---:|---:|"]
        for name,label in (("original_opus1_top1","Original Opus1"),("fresh_opus_top1","Fresh lower-Li Opus")):
            anchor = snapshot["anchors"].get(name)
            if not anchor:
                lines.append(f"| {label} | Not frozen at export | — | — |")
                continue
            values=[]
            for scenario in ("fig2_nominal","fig2_lower"):
                row = snapshot["frozen_choice_results"].get(name,{}).get(f"{scenario}__fixed")
                value = number(row["prediction"]["rmse_all"],4) if row and row["prediction_valid"] else "pending"
                if row and row["optimizer_quality"]["interpretation_unreliable"]:
                    value += " (optimizer warning)"
                values.append(value)
            lines.append(f"| {label} `{anchor['dynamics_hash'][:10]}` | [{anchor['candidate_id']}](../{anchor['path']}) | {' | '.join(values)} |")
    lines += ["", "The original Opus1 choice `b9b64bc542` declares **Ti-only conservation**. Its carbonate-reactant coefficient "
              "creates carbonate dependence but does not impose lithium balance. Neither that coefficient nor its fitted trajectory "
              "proves a Li1.6 phase composition. Declared element conservation and rate-law dependence are separate properties.", "",
              "## Same-candidate sensitivity", "",
              "![Paired prediction errors](examples/chapman_li_oct22/paired_rmse.png)", "",
              "Each point compares the same validated dynamics under nominal and lower lithium. Only pairs with audited predictions appear. "
              "Below the diagonal means smaller error under lower lithium; it does not establish the correct starting composition. "
              "Crosses mark optimizer warnings, including a returned fit worse than an unfinished start; those changes cannot support a physical interpretation. "
              "The Ti-only baseline is a control because carbonate is absent from its rate equations.", "",
              "| Comparison | Known candidate | RMSE before → after | Common score before → after | AICc before → after | Optimizer quality |",
              "|---|---|---:|---:|---:|---|"]
    shown = [p for p in snapshot["known_pairs"] if p["comparison"] in ("primary_Li", "S1_Li")]
    for pair in shown:
        label = ", ".join(pair["known_labels"])
        lines.append(f"| {pair['comparison']} | `{pair['dynamics_hash'][:10]}` ({label}) | "
                     f"{number(pair['before_rmse'],4)} → {number(pair['after_rmse'],4)} | "
                     f"{number(pair['before_score'],4)} → {number(pair['after_score'],4)} | "
                     f"{aicc_number(pair['before_aicc'])} → {aicc_number(pair['after_aicc'])} | "
                     f"{'Warning; do not interpret physical parameter shifts' if pair['optimizer_warning_on_either_side'] else 'No lower-start warning recorded'} |")
    if not shown:
        lines.append("| — | No anchor candidate has completed both sides yet | — | — | — | — |")
    control = snapshot["control_checks"]["baseline"]
    lines += ["", f"**Baseline invariance check:** {control['paired_audited_predictions']} matched, audited baseline predictions. "
              f"Maximum absolute changes: AICc {number(control['max_abs_AICc_change'],6)}, "
              f"common score {number(control['max_abs_common_score_change'],6)}, "
              f"RMSE {number(control['max_abs_RMSE_change'],6)}. "
              f"{control['mixed_runner_and_independent_prediction_sources']} pairs currently mix runner and independent prediction sources. "
              "Different integration tolerances can cause small prediction-score differences even when the carbonate-independent "
              "rate equations and fitted parameters are unchanged. This checks paired completed baseline fits; it does not imply "
              "that unpaired numerical failures are equivalent."]
    lines += ["", "### Parameter changes for the original Opus1 selection", "",
              "This tracks the same original candidate, not a switch between different winning mechanisms. Rate constants are at each step's "
              "declared reference condition. Bound or weakly determined estimates cannot establish a physical change in activation energy.", "",
              "| Comparison | Parameter | Before | After | Bound flag before / after | Local determinacy before / after |",
              "|---|---|---:|---:|---|---|"]
    parameter_rows = 0
    for pair in snapshot["known_pairs"]:
        if "original_opus1_top1" not in pair["known_labels"]:
            continue
        if pair["optimizer_warning_on_either_side"]:
            parameter_rows += 1
            lines.append(f"| {pair['comparison']} | Physical interpretation withheld: optimizer warning; raw values remain in paired JSON | — | — | — | — |")
            continue
        for change in pair["parameter_changes"]:
            if change["kind"] not in {"Ea", "n_avrami", "k", "initial_amount"}:
                continue
            parameter_rows += 1
            lines.append(f"| {pair['comparison']} | `{change['name']}` ({change['kind']}) | {number(change['before'],5)} | "
                         f"{number(change['after'],5)} | {change['before_at_bound']} / {change['after_at_bound']} | "
                         f"{change['before_determinacy']} / {change['after_determinacy']} |")
    if not parameter_rows:
        lines.append("| — | Paired anchor fits not yet available | — | — | — | — |")
    lines += ["", "Full same-candidate parameter changes, including rate constants, activation energies, Avrami exponents and fitted initial amounts, "
              f"are in the local [paired parameter export](../{rel(campaign / 'summary/paired_candidates.json')}). "
              "Wald intervals and local sensitivity labels are screening diagnostics, not profile-likelihood evidence.", "",
              "## Fit quality and represented networks", "",
              "| Input / mode | Fitted | Poor residual adequacy | Any parameter at bound | Weak parameters | Optimizer warnings | Prediction audit failures |",
              "|---|---:|---:|---:|---:|---:|---:|"]
    for key, subsets in summary.items():
        c = subsets["repaired"]["coverage"]
        lines.append(f"| {key} | {c['fitted']} | {c['poor_adequacy']} | {c['fits_with_any_bound']} | {c['fits_with_weak_parameters']} | {c['fits_with_optimizer_warning']} | {c['audit_failed']} |")
    lines += ["", "Residual adequacy is the existing heuristic for clustered signs or serial correlation. Passing it is not proof of the mechanism. "
              "Numerical failure, incomplete optimization and limited identifiability are reported separately from chemistry. "
              "Budget exhaustion alone is distinct from a lower-start warning: the existing fitter can accept a minimum replicated by "
              "independent starts even when its formal stopping criterion is unmet. Those counts remain separate in the snapshot JSON. "
              "Different chemistry/source aliases can share identical fitted dynamics, so a dynamics winner does not uniquely identify a physical mechanism."]
    warning_anchors = [(name,key,row) for name,items in snapshot["frozen_choice_results"].items() for key,row in items.items()
                       if row["optimizer_quality"]["interpretation_unreliable"]]
    for name,key,row in warning_anchors:
        quality = row["optimizer_quality"]
        lines += ["", f"**Optimizer warning — {name}, {key}:** returned NLL {number(row['nll'],7)}; "
                  f"best available start NLL {number(quality['best_available_start_nll'],7)}. "
                  f"Starts within 0.01 of the returned NLL: {quality['starts_near_returned_nll']} "
                  f"({quality['converged_starts_near_returned_nll']} formally converged); "
                  f"{quality['starts_better_than_returned']} starts reached a lower NLL. "
                  f"Stored warning: {quality['warning'] or 'better starts found by summary audit'}. "
                  "This result remains in coverage, but its parameter shifts and accuracy change are not reliable scientific evidence. "
                  "Any numerical rescue must be reported separately with its changed optimization budget."]
    topologies = {}
    for key, subsets in summary.items():
        for group in ("comparable", "repaired"):
            row = subsets[group]["development_selected"]
            if row:
                topologies.setdefault(row["dynamics_hash"], {"row": row, "labels": []})["labels"].append(f"{key}/{group}")
    for entry in topologies.values():
        row = entry["row"]
        lines += ["", f"**Representative `{row['dynamics_hash'][:10]}`** — {', '.join(entry['labels'])}.", "",
                  f"Conserved elements: {', '.join(row['topology']['conserved_elements'])}. {row['topology']['n_steps']} steps. "
                  f"Residual adequacy: {row['adequacy']}. Bound parameters: {', '.join(row['at_bound']) or 'none reported'}. "
                  f"Starts within 0.01 NLL of returned fit: {row['n_optimum_replicates']}. "
                  f"Optimizer warning: {row['optimizer_warning'] or 'none recorded'}. Raw result: {result_link(row)}.", ""]
        lines += [f"- `{step}`" for step in row["topology"]["steps"]]
    lines += declaration_report(snapshot)
    lines += feasibility_report(snapshot)
    lines += ["", "## Fitted initial amounts", "",
              "Shared mode adds one development-fitted initial Li2CO3 amount and transfers it unchanged to 750 °C. "
              "Per-temperature mode adds separate amounts at 700 and 725 °C; its 750 °C prediction uses the externally specified "
              "amount and does not infer that starting state. Added parameters must be included in AICc. Effective amounts are nuisance "
              "parameters, not measurements of weighed composition.", "",
              "| Input / mode; current repaired-union development selection | Fitted amounts | 750 °C input → used | Added initial parameters | Total parameters |",
              "|---|---|---|---:|---:|"]
    n_adapter = 0
    for key, subsets in summary.items():
        row = subsets["repaired"]["development_selected"]
        if row and row["mode"] != "fixed":
            n_adapter += 1
            amounts = ", ".join(f"{k}={number(v,4)}" for k,v in row["fitted_initial_amounts"].items()) or "not reported"
            lines.append(f"| {key}; {result_link(row)} | {amounts} | {number(row['initial_carbonate_input'])} → "
                         f"{number(row['initial_carbonate_used'])} | {row['k_initial_amount']} | {row['k_total']} |")
    if not n_adapter:
        lines.append("| No completed adapter selection in this snapshot | — | — | — | — |")
    original_amounts=snapshot["frozen_choice_results"]["original_opus1_top1"]
    lines += ["", "The following holds the original Opus candidate fixed and compares its two fitted-start policies. "
              "The shared primary prediction transfers its fitted amount to 750 °C; the per-temperature fit uses the externally "
              "specified 0.36 there. Their primary prediction errors therefore include different 750 °C starting states.", "",
              "| Original Opus fit / prediction policy | Fitted c0 at 700 °C | Fitted c0 at 725 °C | c0 used at 750 °C | Development AICc | Common score | RMSE |",
              "|---|---:|---:|---:|---:|---:|---:|"]
    for mode,label in (("shared","Shared start; transfer fitted amount"),("per_temperature","Separate starts; external 750 °C amount")):
        row=original_amounts.get(f"fig2_lower__{mode}")
        if not row:
            continue
        amounts=row["fitted_initial_amounts"]
        c700=amounts.get("c0.Li2CO3",amounts.get("c0.Li2CO3.700C"))
        c725=amounts.get("c0.Li2CO3",amounts.get("c0.Li2CO3.725C"))
        prediction=row["prediction"] if row["prediction_valid"] else {}
        lines.append(f"| {label} | {number(c700,6)} | {number(c725,6)} | {number(row['initial_carbonate_used'],6)} | "
                     f"{aicc_number(row['aicc'])} | {number(prediction.get('heldout_score'),6)} | {number(prediction.get('rmse_all'),6)} |")
        conditional=row.get("conditional_external_initial_carbonate")
        if conditional and conditional["prediction"] and not conditional["audit_errors"]:
            pred=conditional["prediction"]
            lines.append(f"| Shared kinetics unchanged; external 750 °C amount | {number(c700,6)} | {number(c725,6)} | "
                         f"{number(conditional['external_initial_carbonate'],6)} | same shared fit | "
                         f"{number(pred['heldout_score'],6)} | {number(pred['rmse_all'],6)} |")
    lines += ["", "The 0.4 estimates reach the imposed upper fit bound. They are effective fitting parameters, not measurements "
              "of lithium present in the sample. Use the external-0.36 row when comparing shared and separate-start predictions under that same 750 °C assumption."]
    conditional_rows = []
    for key,subsets in summary.items():
        row = subsets["repaired"]["development_selected"]
        if row and row.get("conditional_external_initial_carbonate") and not (
                key=="fig2_lower__shared" and row["dynamics_hash"]==snapshot["anchors"]["original_opus1_top1"]["dynamics_hash"]):
            conditional_rows.append((key,row,row["conditional_external_initial_carbonate"]))
    if conditional_rows:
        lines += ["", "The following secondary calculation freezes those same shared-fit kinetics and changes only the "
                  "750 °C initial amount to an external assumption. It is not the primary transferred-initial-state prediction "
                  "and is not used for the main ranking.", "",
                  "| Shared fit | External 750 °C initial carbonate | Conditional common score | Conditional RMSE | Status |",
                  "|---|---:|---:|---:|---|"]
        for key,row,conditional in conditional_rows:
            cp = conditional["prediction"] or {}
            lines.append(f"| {key}; {result_link(row)} | {number(conditional['external_initial_carbonate'])} | "
                         f"{number(cp.get('heldout_score'),4)} | {number(cp.get('rmse_all'),4)} | {conditional['status']} |")
    lines += profile_report(snapshot)
    lines += rescue_report(snapshot)
    overlay=snapshot["phase_overlay"]
    if overlay["curves"] and not overlay["audit_errors"]:
        lines += ["", "## 750 °C phase predictions", "",
                  "![Retrospective phase predictions against Fig. 2 observations](examples/chapman_li_oct22/phase_predictions_750C.png)", "",
                  "Points are the digitized Fig. 2 observations. Lines join saved predictions at those times; kinetics were fitted at 700 + 725 °C "
                  "and transferred without refitting to 750 °C. The baseline and AI candidates come from frozen development selections; "
                  "the lower-Li recovery is the same original AI candidate with a separate optimizer budget. "
                  "Phase amounts are formula units per mole Ti, **not weight fractions**. Li4Ti5O12 contains five Ti atoms per formula unit "
                  "and therefore has a different numerical scale from the other phases. This remains retrospective prediction, not new blind validation.", "",
                  "| Curve | Initial Li2CO3 at 750 °C | Common score | RMSE | Saved prediction |", "|---|---:|---:|---:|---|"]
        for curve in overlay["curves"]:
            lines.append(f"| {curve['label']} | {number(curve['initial_carbonate_used'])} | "
                         f"{number(curve['prediction']['heldout_score'],6)} | {number(curve['prediction']['rmse_all'],6)} | "
                         f"[source](../{curve['source']}) |")
        if not overlay["fresh_curve_available"]:
            lines += ["", "The fresh Opus curve will be added after its choice is frozen and its prediction passes the audit."]
    elif overlay["audit_errors"]:
        lines += ["", "Phase overlay withheld: " + "; ".join(overlay["audit_errors"])]
    lines += ["", "## Provenance and interpretation limits", "",
              f"Prediction checks: **{len(snapshot['audit_problems'])} problems** across {snapshot['result_file_count']} saved files. "
              "The summary independently recomputes weighted scores and RMSE, checks the expected 750 °C observations, and rejects mixed "
              "input/evaluator identities within a scenario. Prediction audit failures are excluded from prediction ranking, not silently repaired. "
              "They do not replace the model selected by development AICc; its missing prediction remains visible. "
              "Where a hash-matched independent score file exists, it takes precedence: only `predicted` or "
              "`predicted_verified_fallback` outcomes enter prediction rankings. Numerical disagreement or scoring failure is not "
              "replaced with an older prediction. Files not independently rescored still use audited runner predictions. "
              "A successful independent prediction can rescue a runner prediction error without converting a failed fit into a successful fit.", "",
              f"Separate checks: recovery {len(snapshot['rescue_audit_problems'])} problems; profiles {len(snapshot['profile_audit_problems'])}; "
              f"supply-rule evidence {len(snapshot['feasibility_audit_problems'])}. These do not change any primary result or ranking.", "",
              f"Read the local [snapshot JSON](../{rel(campaign / 'summary/campaign_summary.json')}), "
              f"[candidate summaries](../{rel(campaign / 'summary/candidate_summary.json')}) and "
              f"[source-file hashes](../{rel(campaign / 'summary/source_hashes.json')}) for all counts, failures, aliases and raw-result paths. "
              "Candidate-level files remain ignored; these aggregate figures and this report are review artifacts.", "",
              "The old finite candidate set was proposed on the original extraction; fresh lower-lithium proposals remain a separate set. S1 is an alternate extraction of the same experiment, "
              "not independent evidence. Starting composition, crystalline normalization, lithium deficiency, initial rutile and the heating "
              "ramp remain distinct uncertainties. A retrospective rank improvement cannot by itself identify a mechanism or validate an "
              "initial-state assumption. The fresh run is retrospective at team level even though its proposer does not receive 750 °C observations.", "",
              "## Context for the Daniel discussion", "",
              "The [October 21 catch-up](https://notes.granola.ai/d/eec92642-6e39-4305-b5c0-8d5b437c5deb) frames the comparisons as "
              "directional calibration with candid feedback, followed by visualization. The [October 12 discussion]"
              "(https://notes.granola.ai/d/dac924f7-c3f6-4ad2-995f-2e11f47ad6a4) emphasizes reducing redundant experiments and using "
              "virtual experiments to resolve competing pathways and guide physical measurements. The supported demonstration is: "
              "change an assumption, compare the resulting explanations, expose what remains uncertain, and identify the next useful measurement. "
              "These meeting notes explain the intended use; they are not evidence for the scientific results above.", "",
              "Regenerate this snapshot without launching any fits:", "", "```bash", ".venv/bin/python scripts/summarize_chapman_li_sensitivity.py", "```", ""]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines))


def plots(snapshot, all_pairs, figure_dir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "svg.fonttype": "none"})
    figure_dir.mkdir(parents=True, exist_ok=True)
    keys = list(snapshot["summaries"])
    def plotted_coverage(key):
        target=snapshot["declared_followup_targets"].get(key)
        return target["coverage"] if target else snapshot["summaries"][key]["repaired"]["coverage"]
    fig, ax = plt.subplots(figsize=(11, max(3.8, .5*len(keys)+1.6)), layout="constrained")
    y = np.arange(len(keys))
    left = np.zeros(len(keys))
    categories = [("prediction_valid", "Audited prediction", "#0072B2"),
                  ("other_recorded", "Other recorded outcome", "#E69F00"), ("missing", "No saved outcome", "#dce1e5")]
    for field, label, color in categories:
        values = []
        for key in keys:
            cov = plotted_coverage(key)
            values.append(cov["recorded"]-cov["prediction_valid"] if field == "other_recorded" else cov[field])
        ax.barh(y, values, left=left, label=label, color=color)
        left += values
    for i, key in enumerate(keys):
        cov = plotted_coverage(key)
        ax.text(910, i, f"{cov['recorded']}/{cov['declared']} recorded", va="center", fontsize=9)
    ax.set(yticks=y, yticklabels=keys, xlabel="Distinct model dynamics (declared set size shown for each row)", xlim=(0, 1120),
           title="Recorded outcomes against the primary and follow-up target sets")
    ax.invert_yaxis()
    ax.legend(loc="lower center", bbox_to_anchor=(.5,-.3), ncol=3, frameon=False, fontsize=9)
    fig.supxlabel("Primary comparison: original 904-model set • follow-ups: declared smaller lists • fresh proposals remain separate",fontsize=9)
    for ext in ("png", "svg"):
        fig.savefig(figure_dir/f"coverage.{ext}", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1,2,figsize=(10.5,4.9),layout="constrained")
    for ax, key, title in zip(axes, ("primary_Li", "S1_Li"), ("Original Fig. 2", "Alternate S1 extraction")):
        selected = [p for p in all_pairs if p["comparison"] == key and p["prediction_pair_valid"] and p["in_old_repaired_union"]]
        if selected:
            xy = np.array([[p["before_rmse"],p["after_rmse"]] for p in selected])
            lim = max(.02,float(xy.max())*1.06)
            for independent, color, label in ((True,"#0072B2","Carbonate-independent"),(False,"#D55E00","Carbonate-dependent")):
                subset = [p for p in selected if bool(p["carbonate_independent"]) == independent and not p["optimizer_warning_on_either_side"]]
                if subset:
                    ax.scatter([p["before_rmse"] for p in subset],[p["after_rmse"] for p in subset],
                               s=24,alpha=.5,color=color,label=f"{label} (n={len(subset)})")
            warned = [p for p in selected if p["optimizer_warning_on_either_side"]]
            if warned:
                ax.scatter([p["before_rmse"] for p in warned],[p["after_rmse"] for p in warned],
                           s=24,alpha=.65,color="#444",marker="x",label=f"Optimizer warning (n={len(warned)})")
            ax.plot([0,lim],[0,lim],"--",color="#555",lw=1)
            ax.set(xlim=(0,lim),ylim=(0,lim),aspect="equal")
            ax.legend(loc="upper left",fontsize=8,frameon=False)
        else:
            ax.text(.5,.5,"No completed prediction pairs yet",ha="center",va="center",transform=ax.transAxes)
            ax.set(xlim=(0,1),ylim=(0,1))
        ax.set(title=f"{title}: {len(selected)} same-candidate pairs",xlabel="750 °C RMSE, nominal lithium",ylabel="750 °C RMSE, lower lithium")
    fig.suptitle("Matched prediction errors — provisional, completed pairs only",fontsize=14)
    fig.supxlabel("Original 904-model set • RMSE in formula units per mole Ti • optimizer warnings limit interpretation",fontsize=9)
    for ext in ("png","svg"):
        fig.savefig(figure_dir/f"paired_rmse.{ext}",dpi=180)
    plt.close(fig)

    overlay=snapshot["phase_overlay"]
    if overlay["audit_errors"] or not overlay["curves"]:
        return
    fig,axes=plt.subplots(2,2,figsize=(10.8,7.8))
    has_fresh=overlay["fresh_curve_available"]
    fig.subplots_adjust(left=.09,right=.98,bottom=.13,top=.73 if has_fresh else .77,hspace=.3,wspace=.22)
    phases=[("anatase","Anatase TiO₂"),("rutile","Rutile TiO₂"),("Li2TiO3","Li₂TiO₃ channel"),("Li4Ti5O12","Li₄Ti₅O₁₂ channel")]
    for ax,(channel,label) in zip(axes.flat,phases):
        observed=overlay["observations"][channel]
        ax.scatter(observed["time_min"],observed["observed"],s=24,color="#222222",edgecolor="white",linewidth=.5,
                   label="Digitized Fig. 2 observations",zorder=4)
        for curve in overlay["curves"]:
            saved=curve["channels"][channel]
            ax.plot(saved["time_min"],saved["predicted"],color=curve["color"],ls=curve["linestyle"],lw=1.8,label=curve["label"])
        feasibility=snapshot.get("carbonate_feasibility")
        if channel=="Li2TiO3" and feasibility and not feasibility["audit_errors"]:
            cap=next(row["intermediate_upper_bound"] for row in feasibility["rows"] if row["scenario"]=="fig2_lower" and row["temperature_C"]==750)
            ax.axhline(cap,color="#D55E00",ls=":",lw=1,alpha=.7)
            ax.text(3.1,cap+.008,f"Lower-Li model supply ceiling: {cap:.2f}",color="#A64000",fontsize=8)
        ax.set(title=label,xlim=(0,9.7),ylim=(0,None))
        ax.grid(axis="y",color="#dddddd",lw=.5)
        ax.tick_params(labelsize=9)
    handles,labels=axes[0,0].get_legend_handles_labels()
    fig.legend(handles,labels,ncol=2,loc="upper center",bbox_to_anchor=(.53,.91),frameon=False,fontsize=9)
    fig.suptitle("750 °C retrospective prediction: observed and predicted phase amounts",fontsize=14,y=.99)
    fig.text(.53,.947,"Fit at 700 + 725 °C; transfer frozen kinetics to 750 °C",ha="center",fontsize=10)
    fig.supxlabel("Time after insertion (min)",y=.075,fontsize=11)
    fig.supylabel("Phase amount (formula units per mole Ti)",x=.015,fontsize=11)
    footer="Lower-Li recovery has a separate optimizer budget; it does not replace the standard result."
    if not has_fresh:
        footer += "\nFresh Opus selection/prediction pending."
    fig.text(.53,.025,footer,ha="center",va="center",fontsize=9)
    for ext in ("png","svg"):
        fig.savefig(figure_dir/f"phase_predictions_750C.{ext}",dpi=180)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign",type=Path,default=DEFAULT_CAMPAIGN)
    parser.add_argument("--report",type=Path,default=ROOT/"docs/CHAPMAN_LI_SENSITIVITY_RESULTS.md")
    parser.add_argument("--figures",type=Path,default=ROOT/"docs/examples/chapman_li_oct22")
    args = parser.parse_args()
    groups, anchors = source_groups(args.campaign)
    fresh = read(args.campaign/"fresh_opus_inventory.json") if "fresh_opus" in groups else None
    rows, problems, hashes, sigma, result_file_count = collect(args.campaign)
    rescues,rescue_hashes,rescue_problems=collect_rescues(args.campaign,sigma)
    profiles,profile_hashes,profile_problems=collect_profiles(args.campaign)
    feasibility,feasibility_hashes,feasibility_problems=collect_feasibility(args.campaign)
    declarations=declaration_analysis(args.campaign,rows,groups)
    summaries = {}
    available = {(r["scenario"],r["mode"]) for r in rows}
    available.update((s,"fixed") for s in SCENARIOS)
    for scenario, mode in sorted(available,key=lambda x:(SCENARIOS.index(x[0]),x[1])):
        selected = [r for r in rows if r["scenario"] == scenario and r["mode"] == mode]
        baseline = [r for r in rows if r["scenario"] == scenario and r["mode"] == "fixed" and r["dynamics_hash"] in groups["baseline"]]
        summaries[f"{scenario}__{mode}"] = {group: selection(selected,members,baseline,groups["baseline"]) for group,members in groups.items()}
    all_pairs, known_pairs, known = pairs(rows,anchors,summaries)
    for pair in all_pairs:
        pair["in_old_repaired_union"] = pair["dynamics_hash"] in groups["repaired"]
    frozen_choice_results = {name:{f"{r['scenario']}__{r['mode']}":r for r in rows if r["dynamics_hash"] == anchor["dynamics_hash"]}
                             for name,anchor in anchors.items()}
    bypath={r["path"]:r for r in rows}
    for rescue in rescues:
        rescue["primary_summary"]=bypath.get(rescue["primary_path"])
        rescue["frozen_selection_labels"]=[name for name,a in anchors.items() if a["dynamics_hash"]==rescue["dynamics_hash"]]
        best=rescue["stages"].get(rescue["best_stage"])
        proxy={"prediction_valid":not rescue["audit_errors"] and bool(best) and best["prediction_valid"],
               "prediction":best["prediction"] if best else None}
        baseline=[r for r in rows if r["scenario"]==rescue["scenario"] and r["mode"]=="fixed" and r["dynamics_hash"] in groups["baseline"]]
        rescue["diagnostic_baseline_rank"]=baseline_rank(proxy,baseline,groups["baseline"])
        original_baseline=[r for r in rows if r["scenario"]=="fig2_nominal" and r["mode"]=="fixed" and r["dynamics_hash"] in groups["baseline"]]
        rescue["diagnostic_original_nominal_baseline_rank"]=baseline_rank(proxy,original_baseline,groups["baseline"])
    targets={}
    for key,filename in (("s1_nominal__fixed","extraction_shortlist_v1.json"),("s1_lower__fixed","extraction_shortlist_v1.json"),
                         ("fig2_lower__shared","initial_amount_shortlist_v1.json"),("fig2_lower__per_temperature","per_temperature_shortlist_v1.json")):
        path=args.campaign/filename
        if path.is_file():
            records=read(path);members={r["dynamics_hash"] for r in records}
            if len(members)!=len(records):
                raise ValueError(f"Declared follow-up list has duplicate dynamics: {path}")
            scenario,mode=key.split("__")
            targets[key]={"path":rel(path),"sha256":digest(path),
                          "coverage":coverage([r for r in rows if r["scenario"]==scenario and r["mode"]==mode],members)}
    snapshot = {"generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "scope": "saved-result snapshot; retrospective; absence is not completion",
                "membership_counts": {k:len(v) for k,v in groups.items()}, "anchors": anchors,
                "fresh_opus":fresh,"frozen_choice_results":frozen_choice_results,
                "declared_followup_targets":targets,"profiles":profiles,"profile_audit_problems":profile_problems,
                "carbonate_feasibility":feasibility,"feasibility_audit_problems":feasibility_problems,
                "declaration_analysis":declarations,
                "known_candidates": known, "result_file_count": result_file_count, "audited_candidate_count": len(rows),
                "fixed_grid_all_outcomes_recorded": all(summaries[f"{s}__fixed"]["repaired"]["coverage"]["all_declared_recorded"] for s in SCENARIOS),
                "primary_fixed_grid_all_outcomes_recorded": all(summaries[f"{s}__fixed"]["repaired"]["coverage"]["all_declared_recorded"] for s in ("fig2_nominal","fig2_lower")),
                "common_sigma": sigma, "summaries": summaries, "known_pairs": known_pairs,
                "numerical_rescues":rescues,"rescue_audit_problems":rescue_problems,
                "control_checks": control_checks(all_pairs,groups),
                "audit_problems": problems, "unknown_dynamics": sorted({r["dynamics_hash"] for r in rows}-set.union(*groups.values()))}
    snapshot["phase_overlay"]=overlay_data(snapshot,args.campaign,hashes)
    out = args.campaign/"summary"
    write(out/"campaign_summary.json",snapshot)
    write(out/"candidate_summary.json",rows)
    write(out/"paired_candidates.json",all_pairs)
    write(out/"phase_overlay.json",snapshot["phase_overlay"])
    write(out/"profile_summary.json",profiles)
    write(out/"declaration_summary.json",declarations)
    input_manifest = read(args.campaign/"input_manifest.json")
    write(out/"source_hashes.json",{"result_and_score_files":hashes,"inventory_sha256":digest(args.campaign/"inventory.json"),
                                    "rescue_files":rescue_hashes,
                                    "profile_files":profile_hashes,"feasibility_files":feasibility_hashes,
                                    "declaration_records":{declarations["source_path"]:declarations["source_sha256"]},
                                    "followup_lists":{entry["path"]:entry["sha256"] for entry in targets.values()},
                                    "source_records_sha256":digest(args.campaign/"source_records.json"),
                                    "alias_sha256":{kind:digest(args.campaign/f"{kind}_aliases.json") for kind in ("comparable","repaired")},
                                    "input_manifest_sha256":digest(args.campaign/"input_manifest.json"),
                                    "input_data_sha256":{path:digest(ROOT/path) for paths in input_manifest["inputs"].values() for path in paths},
                                    "common_sigma_reference_sha256":digest(ROOT/"investigations/runs/chapman750-propose_space-opus1/final/chapman2023_fig2_750C/predictions.json"),
                                    "summary_script_sha256":digest(Path(__file__))})
    if fresh:
        source_hashes = read(out/"source_hashes.json")
        source_hashes["fresh_export_sha256"] = {name:digest(args.campaign/name) for name in ("fresh_opus_inventory.json","fresh_opus_records.json")}
        write(out/"source_hashes.json",source_hashes)
    plots(snapshot,all_pairs,args.figures)
    render_report(snapshot,args.report,args.figures,args.campaign)
    print(json.dumps({"report":rel(args.report),"result_files":result_file_count,"audit_problems":len(problems),
                      "rescue_audit_problems":len(rescue_problems),"profile_audit_problems":len(profile_problems),
                      "feasibility_audit_problems":len(feasibility_problems),
                      "coverage":{k:v["repaired"]["coverage"] for k,v in summaries.items()},
                      "paired_comparisons":dict(Counter(p["comparison"] for p in all_pairs))},indent=2))


if __name__ == "__main__":
    main()
