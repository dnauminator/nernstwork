#!/usr/bin/env python3
"""Bounded serial optimizer diagnostics; primary fits/cache/ranks are untouched.

Default is coordinate preflight only. --execute runs at most four planner
priorities, at most three starts each, on one numerical thread. Only optimizer
budgets change: 40 IRLS outer iterations, 1000 nfev, 500000 fit ODE solves/start.
"""
from __future__ import annotations

import os
for _name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_name] = "1"

import argparse
import copy
import json
import math
from pathlib import Path
import sys
import time

import numpy as np
from scipy.stats import qmc

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nernstwork.canonical import canonical_param_keys
from nernstwork.data import sha256_file, sha256_json
from nernstwork.evaluate import code_identity, fit_key, translate_fit, validate_submission
from nernstwork.fit import FitBudgetExceeded, Problem, _solve, local_uncertainty, residual_diagnostics
from nernstwork.model import compile_mechanism
from nernstwork.store import atomic_write_json, now
from check_chapman_sensitivity_numerics import observations, predict_with_verification
from plan_chapman_li_followups import independent, versions

OUT = ROOT / "data/derived/chapman_li_sensitivity"
MAX_CANDIDATES = 4
EXTENDED_BUDGET = {"max_outer": 40, "max_nfev": 1000, "max_ode_solves_per_fit": 500000}
REPLICATION_TOLERANCE = .01


def read(path):
    return json.loads(Path(path).read_text())


def relative(path):
    return str(Path(path).resolve().relative_to(ROOT))


def finite(value):
    return isinstance(value, (int, float)) and math.isfinite(value)


def mapped_theta(raw_fit, compiled, validation):
    current_keys = canonical_param_keys(compiled, validation["canonical_map"])
    original_keys = raw_fit["canonical_param_keys"]
    if len(set(current_keys)) != len(current_keys) or len(set(original_keys)) != len(original_keys) or sorted(current_keys) != sorted(original_keys):
        raise ValueError("Canonical parameter keys are not a one-to-one match")
    return np.array(raw_fit["theta"], dtype=float)[[original_keys.index(k) for k in current_keys]]


def regenerate_starts(raw_fit, compiled, validation, protocol):
    """Generate in original raw-cache coordinates, then permute to this compiler.

    Campaign theta has already been translated and must never be translated again.
    The raw cache is the authority for original RNG coordinate order and seed.
    """
    current_keys = canonical_param_keys(compiled, validation["canonical_map"])
    original_keys = raw_fit["canonical_param_keys"]
    if len(set(current_keys)) != len(current_keys) or sorted(current_keys) != sorted(original_keys):
        raise ValueError("Cannot reconstruct original LHS coordinates")
    original_from_current = [current_keys.index(k) for k in original_keys]
    current_from_original = [original_keys.index(k) for k in current_keys]
    lo, hi = compiled.tbounds()
    original_lo, original_hi = lo[original_from_current], hi[original_from_current]
    seed = int(raw_fit["multistart"]["seed"])
    draws = qmc.LatinHypercube(d=compiled.n_free, seed=np.random.default_rng(seed)).random(protocol["optimizer"]["n_starts"])
    original_starts = qmc.scale(draws, original_lo, original_hi)
    original_starts = np.clip(original_starts, original_lo + 1e-9*(original_hi-original_lo), original_hi - 1e-9*(original_hi-original_lo))
    starts = original_starts[:, current_from_original]
    # Independently follow the existing numerical-repeat helper: reorder the
    # compiled free slots first, then draw against that compiler's bounds.
    helper = copy.copy(compiled)
    helper.free = [compiled.free[i] for i in original_from_current]
    helper_lo, helper_hi = helper.tbounds()
    helper_draws = qmc.LatinHypercube(d=helper.n_free, seed=np.random.default_rng(seed)).random(protocol["optimizer"]["n_starts"])
    helper_starts = qmc.scale(helper_draws, helper_lo, helper_hi)
    helper_starts = np.clip(helper_starts, helper_lo + 1e-9*(helper_hi-helper_lo), helper_hi - 1e-9*(helper_hi-helper_lo))
    if canonical_param_keys(helper, validation["canonical_map"]) != original_keys or not np.array_equal(helper_starts, original_starts):
        raise ValueError("LHS reconstruction differs from existing numerical-repeat helper")
    return starts, {"original_seed": seed, "original_canonical_parameter_order": original_keys,
                    "original_free_parameter_names": raw_fit["free_parameter_names"],
                    "current_canonical_parameter_order": current_keys, "current_free_parameter_names": compiled.free_names(),
                    "current_from_original_indices": current_from_original,
                    "original_bounds": [original_lo.tolist(), original_hi.tolist()],
                    "original_lhs_sha256": sha256_json(original_starts.tolist()),
                    "current_lhs_sha256": sha256_json(starts.tolist()), "matches_existing_repeat_helper": True}


def raw_cache_for(source, dev, protocol, engine):
    key = fit_key(source["dynamics_hash"], dev.sha256, protocol, engine)
    path = ROOT / "investigations/cache/fits" / key / "result.json"
    body = read(path)
    if body["fit_key"] != key or body["result"].get("status") != "fitted":
        raise ValueError("Expected an existing fitted official cache with matching identity")
    return path, body["result"]


def prepare(source_path, protocol):
    source = read(source_path)
    if source["mode"] != "fixed":
        raise ValueError("This bounded rescue supports fixed-initial-state fits only")
    engine = code_identity()["sha256"]
    dev, hold, files = observations(source["paths"], protocol)
    expected = {"engine_sha256": engine, "protocol_sha256": sha256_json(protocol),
                "data_sha256": dev.sha256, "heldout_sha256": hold.sha256}
    if any(source.get(k) != v for k, v in expected.items()):
        raise ValueError("Source result no longer matches current inputs/protocol/engine")
    validation = validate_submission(source["submission"], dev, protocol)
    if validation["status"] != "valid" or validation["dynamics_hash"] != source["dynamics_hash"]:
        raise ValueError("Source dynamics no longer validate")
    compiled = compile_mechanism(source["submission"]["mechanism"], dev.conditions, protocol["bounds"])
    cache_path, raw_fit = raw_cache_for(source, dev, protocol, engine)
    starts, coordinate = regenerate_starts(raw_fit, compiled, validation, protocol)
    theta = mapped_theta(raw_fit, compiled, validation)
    once_translated = translate_fit(raw_fit, validation, compiled)
    if not np.array_equal(theta, np.array(once_translated["theta"])):
        raise ValueError("Manual canonical mapping differs from a single raw-cache translation")
    if compiled.free_names() != source["fit"]["free_parameter_names"] or not np.array_equal(theta, np.array(source["fit"]["theta"])):
        raise ValueError("Campaign parameter vector does not match the raw-cache canonical mapping")
    if raw_fit["multistart"] != source["fit"]["multistart"]:
        raise ValueError("Campaign multistart record differs from original cache")
    problem = Problem(compiled, dev, validation["observation_map"], protocol)
    raw = problem.raw_residuals(theta)
    sig = np.array([raw_fit["sigma"][g] for g in problem.groups])
    checked_nll = float(problem.nll(raw, sig))
    if abs(checked_nll-raw_fit["nll"]) > 1e-4 + 1e-8*abs(raw_fit["nll"]):
        raise ValueError("Mapped fitted theta does not reproduce its source NLL")
    coordinate.update(raw_cache_path=relative(cache_path), raw_cache_sha256=sha256_file(cache_path),
                      source_nll=raw_fit["nll"], recomputed_nll=checked_nll,
                      source_mle_mapping_matches_campaign=True,
                      warning="Only the raw official cache was translated; campaign canonical_param_keys metadata was not used to remap its theta")
    return {"source": source, "source_path": source_path, "dev": dev, "hold": hold, "files": files,
            "validation": validation, "compiled": compiled, "raw_fit": raw_fit, "starts": starts,
            "coordinate_preflight": coordinate, "engine": engine, "mapped_source_theta": theta}


def known_case_check(campaign, protocol):
    path = campaign / "numerics/optimizer_repeat_plan.json"
    plan = read(path)
    job = next(j for j in plan["jobs"] if j["label"] == "baseline_selected")
    source_path = campaign / "results/fig2_nominal__fixed" / f"{job['dynamics_hash']}.json"
    checked = prepare(source_path, protocol)
    coordinate = checked["coordinate_preflight"]
    if coordinate["original_seed"] != job["original_seed"] or coordinate["original_canonical_parameter_order"] != job["original_canonical_parameter_order"]:
        raise ValueError("Known baseline does not match the established numerical-repeat plan")
    # Exercise a genuinely different free-slot order even when this representative
    # happens to use the original order, proving the permutation is not a no-op.
    reversed_compiled = copy.copy(checked["compiled"])
    reversed_compiled.free = list(reversed(reversed_compiled.free))
    reversed_starts, _ = regenerate_starts(checked["raw_fit"], reversed_compiled, checked["validation"], protocol)
    if not np.array_equal(reversed_starts[:, ::-1], checked["starts"]):
        raise ValueError("Known-case reversed-coordinate control failed")
    return {"status": "passed", "case": job["label"], "repeat_plan_path": relative(path),
            "repeat_plan_sha256": sha256_file(path), "coordinate_preflight": coordinate,
            "reversed_coordinate_control_passed": True}


def plan_starts(prepared, campaign, protocol):
    raw_fit = prepared["raw_fit"]
    multi = raw_fit["multistart"]
    flags = multi["converged_by_start"]
    unfinished = [(value, i) for i, value in enumerate(multi["nll_by_start"])
                  if finite(value) and not flags[i]]
    if len(unfinished) < 2:
        raise ValueError("This policy requires two finite unfinished original starts")
    jobs = [{"label": f"primary_lhs_{i}", "kind": "regenerated_original_lhs", "source_start_index": i,
             "source_unfinished_nll": value, "initial_theta": prepared["starts"][i].tolist()}
            for value, i in sorted(unfinished)[:2]]
    source = prepared["source"]
    nominal_path = campaign / "results/fig2_nominal__fixed" / f"{source['dynamics_hash']}.json"
    nominal = read(nominal_path)
    if source["scenario"] == "fig2_lower":
        nominal_dev, _hold, _files = observations(nominal["paths"], protocol)
        path, fit = raw_cache_for(nominal, nominal_dev, protocol, prepared["engine"])
        third_theta = mapped_theta(fit, prepared["compiled"], prepared["validation"])
        label, rule = "nominal_mle", "If the two unfinished LHS starts do not yield agreeing formal optima, initialize the third start from the nominal-input raw-cache MLE"
    else:
        third_theta = prepared["mapped_source_theta"]
        path = ROOT / prepared["coordinate_preflight"]["raw_cache_path"]
        label, rule = "source_mle", "If the two unfinished LHS starts do not yield agreeing formal optima, initialize the third start from this nominal-input raw-cache MLE"
    jobs.append({"label": label, "kind": "raw_cache_mle", "rule": rule, "raw_cache_path": relative(path),
                 "raw_cache_sha256": sha256_file(path), "initial_theta": third_theta.tolist()})
    return jobs, nominal_path


def update_quality(result):
    stages = result["stages"]
    converged = [(name, stage) for name, stage in stages.items() if stage.get("status") == "converged" and finite(stage.get("nll"))]
    warnings = []
    if converged:
        label, best = min(converged, key=lambda item: item[1]["nll"])
        result["best_converged_stage"] = label
        result["converged_replicates"] = [name for name, stage in converged if abs(stage["nll"]-best["nll"]) < REPLICATION_TOLERANCE]
        result["lower_unconverged_stages"] = [name for name, stage in stages.items() if stage.get("status") != "converged"
                                              and finite(stage.get("nll")) and stage["nll"] < best["nll"]-REPLICATION_TOLERANCE]
        primary_finite = [v for v in result["original_multistart"]["nll_by_start"] if finite(v)]
        if primary_finite and min(primary_finite) < best["nll"]-REPLICATION_TOLERANCE:
            warnings.append("A primary start remains lower than the best formally converged rescue")
        if result["lower_unconverged_stages"]:
            warnings.append("A rescue start remains lower but unconverged")
    else:
        result["converged_replicates"] = []
        warnings.append("No formally converged rescue")
    if len(result["converged_replicates"]) < 2:
        warnings.append("Best rescue lacks two agreeing formally converged starts")
    result["remaining_optimizer_warnings"] = warnings


def run_candidate(prepared, jobs, nominal_path, protocol, plan_path, known_case, campaign):
    source, compiled, dev = prepared["source"], prepared["compiled"], prepared["dev"]
    extended = copy.deepcopy(protocol)
    extended["optimizer"].update(EXTENDED_BUDGET)
    assert all(extended[key] == value for key, value in protocol.items() if key != "optimizer")
    signature = {"input_result_sha256": sha256_file(prepared["source_path"]),
                 "nominal_result_sha256": sha256_file(nominal_path), "rescue_source_sha256": sha256_file(__file__),
                 "score_code_sha256": sha256_file(ROOT / "scripts/check_chapman_sensitivity_numerics.py"),
                 "engine_sha256": prepared["engine"], "original_protocol_sha256": sha256_json(protocol),
                 "extended_protocol_sha256": sha256_json(extended), "dataset_file_sha256": prepared["files"],
                 "coordinate_preflight": prepared["coordinate_preflight"], "planned_starts": jobs,
                 "maximum_starts": 3, "replication_tolerance_nll": REPLICATION_TOLERANCE}
    identity = sha256_json(signature)
    destination = campaign / "numerics/rescue" / f"{source['dynamics_hash']}__{identity[:12]}.json"
    if destination.exists():
        result = read(destination)
        if result["identity"] != identity:
            raise ValueError("Rescue output identity mismatch")
    else:
        result = {"identity": identity, **signature, "created_at": now(), "dynamics_hash": source["dynamics_hash"],
                  "scenario": source["scenario"], "mode": "fixed", "input_result_path": relative(prepared["source_path"]),
                  "original_protocol": protocol, "extended_protocol": extended, "primary_ranking_eligible": False,
                  "planner_path": relative(plan_path), "planner_sha256": sha256_file(plan_path),
                  "known_case_validation": known_case, "original_multistart": prepared["raw_fit"]["multistart"],
                  "carbonate_independent": source["carbonate_independent"],
                  "lower_input_transfer": "requires separate observed-trajectory invariance proof" if source["carbonate_independent"] else "not applicable",
                  "note": "Diagnostic optimizer rescue only. Data, noise, ODE settings, parameter bounds and objective unchanged. Higher optimizer budgets; no primary ranking eligibility.",
                  "stages": {}}
    atomic_write_json(destination, result)
    lo, hi = compiled.tbounds()
    for job in jobs:
        update_quality(result)
        if len(result["stages"]) >= 2 and len(result["converged_replicates"]) >= 2 and not result["remaining_optimizer_warnings"]:
            result["stop_reason"] = "two_formally_converged_starts_agree_within_0.01_nll"
            break
        label = job["label"]
        if label in result["stages"]:
            continue
        result["active_stage"] = {"label": label, "started_at": now()}
        atomic_write_json(destination, result)
        print(json.dumps({"started": source["dynamics_hash"], "scenario": source["scenario"], "stage": label}), flush=True)
        problem = Problem(compiled, dev, prepared["validation"]["observation_map"], extended)
        problem.enforce_budget = True
        started = time.monotonic()
        stage = dict(job)
        solved = None
        try:
            solved = _solve(problem, np.array(job["initial_theta"]), lo, hi, extended["optimizer"])
        except FitBudgetExceeded:
            stage.update(status="ode_budget_exhausted", error="500000 fitting ODE solves exhausted")
        except Exception as exc:
            stage.update(status="execution_error", error=f"{type(exc).__name__}: {exc}")
        if solved is not None:
            stage.update(status="converged" if solved["converged"] else "unconverged", theta=solved["x"].tolist(),
                         nll=solved["nll"] if math.isfinite(solved["nll"]) else None,
                         sigma={g: float(s) for g, s in zip(problem.groups, solved["sigma"])},
                         nfev=solved["nfev"], solver_failed=solved["solver_failed"])
            if solved["converged"]:
                k = compiled.n_free + problem.n_sigma_params
                fitted = {"status": "fitted", "theta": stage["theta"], "nll": solved["nll"], "sigma": stage["sigma"],
                          "free_parameter_names": compiled.free_names(),
                          "canonical_param_keys": canonical_param_keys(compiled, prepared["validation"]["canonical_map"]),
                          "k_kinetic": compiled.n_free, "k_noise": problem.n_sigma_params, "k_total": k,
                          "n_obs": dev.n_obs, "aicc": 2*k + 2*solved["nll"] + 2*k*(k+1)/(dev.n_obs-k-1)}
                try:
                    fitted["uncertainty"] = local_uncertainty(problem, solved["x"], solved["sigma"])
                    fitted["residuals"] = residual_diagnostics(problem, solved["x"], solved["sigma"])
                except Exception as exc:
                    stage["diagnostic_error"] = f"{type(exc).__name__}: {exc}"
                stage["fit"] = fitted
                stage.update(predict_with_verification(compiled, prepared["validation"], fitted, prepared["hold"], source["common_sigma"]))
        stage.update(wall_s=time.monotonic()-started, n_ode_solves=problem.n_ode, n_ode_failures=problem.n_ode_fail,
                     fit_diagnostic_ode_budget=problem.max_solves)
        if problem.n_ode > problem.max_solves:
            raise RuntimeError("Internal error: fitting/diagnostics exceeded the per-start ODE budget")
        result["stages"][label] = stage
        result.pop("active_stage", None)
        update_quality(result)
        result["updated_at"] = now()
        atomic_write_json(destination, result)
        print(json.dumps({"completed": source["dynamics_hash"], "stage": label, "status": stage["status"],
                          "nll": stage.get("nll"), "wall_s": stage["wall_s"], "converged_replicates": result["converged_replicates"]}), flush=True)
    update_quality(result)
    result.setdefault("stop_reason", "maximum_three_starts_completed")
    result["completed_at"] = now()
    atomic_write_json(destination, result)
    return {"path": relative(destination), "dynamics_hash": source["dynamics_hash"], "scenario": source["scenario"],
            "stop_reason": result["stop_reason"], "converged_replicates": result["converged_replicates"],
            "remaining_optimizer_warnings": result["remaining_optimizer_warnings"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", type=Path, default=OUT)
    parser.add_argument("--plan", type=Path, help="Default: latest existing versioned follow-up plan; fixed for this invocation")
    parser.add_argument("--execute", action="store_true", help="Run the bounded serial rescue after all coordinate checks pass")
    args = parser.parse_args()
    plan_path = args.plan or versions(args.campaign, "followup_plan")[-1][1]
    plan = read(plan_path)
    priorities = [r for r in plan["numerical_rescue_priorities"] if r["diagnostic_status"] == "pending_bounded_rescue_decision"]
    if len(priorities) > MAX_CANDIDATES:
        raise ValueError("This invocation is bounded to at most four declared planner priorities")
    protocol = read(ROOT / "configs/protocols/synthesis-mle-v1.json")
    known = known_case_check(args.campaign, protocol)
    prepared_jobs = []
    for priority in priorities:
        requested = read(ROOT / priority["result_path"])
        # One nominal rescue for an inert control; lower-input equivalence is
        # a later separately recorded proof, never a second optimization here.
        scenario = "fig2_nominal" if independent({"submission": requested["submission"]}) else priority["scenario"]
        path = args.campaign / "results" / f"{scenario}__fixed" / f"{priority['dynamics_hash']}.json"
        prepared = prepare(path, protocol)
        jobs, nominal = plan_starts(prepared, args.campaign, protocol)
        prepared_jobs.append((prepared, jobs, nominal))
    summary = {"created_at": now(), "planner_path": relative(plan_path), "planner_sha256": sha256_file(plan_path),
               "rescue_source_sha256": sha256_file(__file__), "workers": 1, "maximum_starts_per_candidate": 3,
               "extended_optimizer_budget_per_start": EXTENDED_BUDGET, "known_case_validation": known,
               "already_recognized_rescues": [r for r in plan["numerical_rescue_priorities"] if r["diagnostic_status"] == "replicated_rescue_exists"],
               "jobs": [{"dynamics_hash": p["source"]["dynamics_hash"], "scenario": p["source"]["scenario"],
                         "source_path": relative(p["source_path"]), "coordinate_preflight": p["coordinate_preflight"],
                         "planned_starts": jobs} for p, jobs, _ in prepared_jobs], "results": []}
    destination = args.campaign / "numerics/targeted_rescue_batches" / f"{sha256_json(summary)}.json"
    atomic_write_json(destination, summary)
    print(json.dumps({"coordinate_preflight": "passed", "known_case": "baseline_selected_and_reversed_coordinates",
                      "candidates": len(prepared_jobs), "execute": args.execute, "batch": relative(destination),
                      "already_recognized_rescues": len(summary["already_recognized_rescues"])}), flush=True)
    if not args.execute:
        return
    for prepared, jobs, nominal in prepared_jobs:
        summary["results"].append(run_candidate(prepared, jobs, nominal, protocol, plan_path, known, args.campaign))
        atomic_write_json(destination, summary)
    summary["completed_at"] = now()
    atomic_write_json(destination, summary)
    print(json.dumps({"completed_batch": relative(destination), "results": summary["results"]}), flush=True)


if __name__ == "__main__":
    main()
