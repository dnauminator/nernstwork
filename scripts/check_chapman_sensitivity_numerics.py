#!/usr/bin/env python3
"""Rescore saved Chapman fits; optionally run isolated, original-seed controls.

No main result or official fit cache is changed. Default scoring uses the exact
solver defaults of the original final parameter-transfer evaluation. Failed integrations
may use a separately verified fallback, explicitly marked in the score record.
Optimizer repeats require --run-repeat and execute serially in a separate tree.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import replace
import json
import math
import os
from pathlib import Path
import signal
import sys
import time

# This script never starts a process pool; restrict numerical libraries as well.
for _key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_key] = "1"

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nernstwork.canonical import canonical_param_keys
from nernstwork.data import joint_observation_set, load_dataset, observation_set, sha256_bytes, sha256_file, sha256_json
from nernstwork.evaluate import code_identity, translate_fit, validate_submission
from nernstwork.fit import Problem, fit, seed_from
from nernstwork.model import compile_mechanism
from nernstwork.store import atomic_write_json, now

OUT = ROOT / "data/derived/chapman_li_sensitivity"
PROTOCOL_PATH = ROOT / "configs/protocols/synthesis-mle-v1.json"
PRIMARY = dict(method="LSODA", rtol=1e-8, atol=1e-10, max_rhs=None)
FALLBACKS = [dict(method="LSODA", rtol=1e-9, atol=1e-11, max_rhs=None),
             dict(method="Radau", rtol=1e-9, atol=1e-11, max_rhs=None),
             dict(method="Radau", rtol=1e-10, atol=1e-12, max_rhs=None)]
VERIFY_ATOL, VERIFY_RTOL = 2e-6, 2e-5
ATTEMPT_WALL_LIMIT_S = 30


def read(path):
    return json.loads(Path(path).read_text())


def relative(path):
    return str(Path(path).resolve().relative_to(ROOT))


def observations(paths, protocol):
    loaded = [load_dataset(ROOT / p) for p in paths]
    exclude = protocol.get("exclude_t0", True)
    return (joint_observation_set(loaded[:2], exclude), observation_set(*loaded[2], exclude),
            dict(zip(paths, [sha for _, sha in loaded])))


def score_prediction(comp, validation, fitted, hold, common, trajectory):
    positions = {float(t): i for i, t in enumerate(hold.t_union)}
    channels, score, nll, total_sse, count = {}, 0., 0., 0., 0
    for channel in hold.channels:
        ids = [comp.species.index(s) for s in validation["observation_map"][channel.name]]
        predicted = trajectory[ids][:, [positions[float(t)] for t in channel.t]].sum(axis=0)
        residual = predicted - channel.y
        sse = float(residual @ residual)
        sigma, fixed_sigma = fitted["sigma"][channel.name], common[channel.name]
        if not sigma > 0 or not fixed_sigma > 0:
            raise ValueError("noise scales must be positive")
        score += sse / fixed_sigma ** 2
        nll += len(residual) * .5 * math.log(2 * math.pi * sigma ** 2) + sse / (2 * sigma ** 2)
        total_sse += sse
        count += len(residual)
        channels[channel.name] = {"time_min": channel.t.tolist(), "observed": channel.y.tolist(),
                                  "predicted": predicted.tolist(), "rmse": math.sqrt(sse / len(residual)),
                                  "sse": sse, "n_obs": len(residual)}
    # Official final scoring averages channel MSEs. These campaign grids have the
    # same sample count per channel, so this also equals pooled-observation RMSE.
    rmse = math.sqrt(np.mean([x["rmse"] ** 2 for x in channels.values()]))
    c0 = comp.resolved_c0(np.array(fitted["theta"]), hold.c0, hold.conditions) if hasattr(comp, "resolved_c0") else hold.c0
    return {"heldout_score": score, "rmse_all": rmse, "rmse_per_observation": math.sqrt(total_sse / count),
            "predictive_nll": nll, "channels": channels, "common_sigma": common, "n_obs": count,
            "initial_carbonate_input": hold.c0["Li2CO3"], "initial_carbonate_used": c0["Li2CO3"]}


def predict_with_verification(comp, validation, fitted, hold, common):
    attempts = []

    def attempt(settings):
        start = time.perf_counter()
        item = {"settings": settings, "wall_limit_s": ATTEMPT_WALL_LIMIT_S}
        def time_limit(signum, frame):
            raise TimeoutError(f"prediction exceeded {ATTEMPT_WALL_LIMIT_S} wall seconds")
        old_handler = signal.signal(signal.SIGALRM, time_limit)
        signal.setitimer(signal.ITIMER_REAL, ATTEMPT_WALL_LIMIT_S)
        try:
            y = comp.simulate(np.array(fitted["theta"]), hold.t_union, hold.c0,
                              conditions=hold.conditions, **settings)
            if y.shape != (len(comp.species), len(hold.t_union)) or not np.all(np.isfinite(y)):
                raise ValueError("prediction is nonfinite or has the wrong shape")
            score = score_prediction(comp, validation, fitted, hold, common, y)
            item.update(status="predicted", heldout_score=score["heldout_score"], rmse_all=score["rmse_all"])
        except Exception as error:
            item.update(status="prediction_failed", error=f"{type(error).__name__}: {error}")
            y, score = None, None
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old_handler)
        item["wall_s"] = time.perf_counter() - start
        attempts.append(item)
        return y, score

    y, prediction = attempt(PRIMARY)
    numerics = {"primary_settings": PRIMARY, "attempts": attempts,
                "verification_tolerance": {"atol": VERIFY_ATOL, "rtol": VERIFY_RTOL}}
    if y is not None:
        return dict(prediction_status="predicted", prediction=prediction, numerics=numerics)
    successful = []
    for settings in FALLBACKS:
        y, prediction = attempt(settings)
        if y is None:
            continue
        successful.append((len(attempts) - 1, y, prediction))
        if len(successful) < 2:
            continue
        bi, b, second = successful[-1]
        for ai, a, first in successful[:-1]:
            verified = bool(np.allclose(a, b, atol=VERIFY_ATOL, rtol=VERIFY_RTOL))
            comparison = {"attempt_indices": [ai, bi], "agreed": verified,
                          "max_abs_trajectory_difference": float(np.max(np.abs(a - b))),
                          "heldout_score_difference": second["heldout_score"] - first["heldout_score"]}
            numerics.setdefault("verification_comparisons", []).append(comparison)
            if verified:
                numerics["verification"] = comparison
                numerics["accepted_attempt_index"] = bi
                return dict(prediction_status="predicted_verified_fallback", prediction=second, numerics=numerics)
    status = "numerical_disagreement" if len(successful) >= 2 else "prediction_failed"
    return dict(prediction_status=status, numerics=numerics,
                error="No pair of fallback integrations produced verified agreeing predictions")


def rescore(path, out=OUT):
    raw = path.read_bytes()
    result = json.loads(raw)
    source_hash, engine = sha256_file(__file__), code_identity()["sha256"]
    signature = {"input_result_sha256": sha256_bytes(raw), "score_code_sha256": source_hash,
                 "engine_sha256": engine, "protocol_sha256": sha256_json(read(PROTOCOL_PATH)),
                 "dataset_file_sha256": {p: sha256_file(ROOT / p) for p in result["paths"]}}
    if result["mode"] != "fixed":
        signature["adapter_source_sha256"] = sha256_file(ROOT / "scripts/chapman_initial_amount_adapter.py")
    identity = sha256_json(signature)
    dest = out / "scores" / f"{result['scenario']}__{result['mode']}" / path.name
    if dest.exists() and read(dest).get("identity") == identity:
        return read(dest), True
    record = {"identity": identity, **signature, "created_at": now(), "input_result_path": relative(path),
              "dynamics_hash": result["dynamics_hash"], "scenario": result["scenario"], "mode": result["mode"],
              "candidate_name": result.get("candidate_name"), "root_status": result.get("status"),
              "fit_status": result.get("fit", {}).get("status", "missing"),
              "prediction_status": "not_attempted_fit_failed"}
    if record["fit_status"] == "fitted":
        try:
            protocol = read(PROTOCOL_PATH)
            dev, hold, files = observations(result["paths"], protocol)
            record["dataset_file_sha256"] = files
            expected = {"engine_sha256": engine, "protocol_sha256": sha256_json(protocol),
                        "data_sha256": dev.sha256, "heldout_sha256": hold.sha256}
            if any(result.get(key) != value for key, value in expected.items()):
                raise ValueError("saved fit inputs, protocol or engine no longer match current files")
            validation = validate_submission(result["submission"], dev, protocol)
            if validation["status"] != "valid" or validation["dynamics_hash"] != result["dynamics_hash"]:
                raise ValueError("candidate validation or dynamics identity changed")
            if result["mode"] == "fixed":
                comp = compile_mechanism(result["submission"]["mechanism"], dev.conditions, protocol["bounds"])
            else:
                from chapman_initial_amount_adapter import compile_with_initial_amount
                if result.get("adapter_sha256") != signature["adapter_source_sha256"]:
                    raise ValueError("initial-amount adapter changed since fitting")
                comp = compile_with_initial_amount(result["submission"]["mechanism"], dev.conditions,
                                                   protocol["bounds"], mode=result["mode"])
            if comp.free_names() != result["fit"]["free_parameter_names"]:
                raise ValueError("parameter order no longer matches the stored fit")
        except Exception as error:
            record.update(prediction_status="input_identity_mismatch", error=f"{type(error).__name__}: {error}")
        else:
            record.update(predict_with_verification(comp, validation, result["fit"], hold, result["common_sigma"]))
            if result["mode"] == "shared":
                ordinary = compile_mechanism(result["submission"]["mechanism"], dev.conditions, protocol["bounds"])
                kinetics = dict(result["fit"], theta=result["fit"]["theta"][:comp.kinetic_n_free])
                conditional_hold = replace(hold, c0=dict(hold.c0, Li2CO3=0.36))
                conditional = predict_with_verification(ordinary, validation, kinetics, conditional_hold, result["common_sigma"])
                conditional.update(policy="frozen_shared_fit_kinetics_with_external_heldout_c0",
                                   external_initial_carbonate=0.36,
                                   note="Secondary conditional prediction: fitted kinetics are unchanged; externally specified 750 C initial carbonate replaces the shared fitted amount. No refitting.")
                record["conditional_external_initial_carbonate"] = conditional
            if "prediction" in record and "prediction" in result:
                record["difference_from_root_prediction"] = {
                    k: record["prediction"][k] - result["prediction"][k]
                    for k in ("heldout_score", "rmse_all", "predictive_nll")}
    atomic_write_json(dest, record)
    return record, False


def repeat_plan(out=OUT):
    protocol = read(PROTOCOL_PATH)
    manifest = read(out / "input_manifest.json")
    inventory = {r["dynamics_hash"]: r for r in read(out / "repaired_records.json")}
    jobs = []
    for label, run in (("baseline_selected", "chapman750-enumeration"),
                       ("opus1_selected", "chapman750-propose_space-opus1")):
        runpath = ROOT / "investigations/runs" / run
        candidate_id = read(runpath / "frozen.json")["top1"]
        candidate_path = runpath / "candidates" / f"{candidate_id}.json"
        candidate = read(candidate_path)
        dynamics = candidate["validation"]["dynamics_hash"]
        cache_path = ROOT / inventory[dynamics]["old_data_cache_path"]
        cached = read(cache_path)["result"]
        paths = manifest["inputs"]["fig2_lower"]
        dev, _, _ = observations(paths, protocol)
        jobs.append({"label": label, "scenario": "fig2_lower", "mode": "fixed", "candidate_id": candidate_id,
                     "dynamics_hash": dynamics, "submission": candidate["submission"], "paths": paths,
                     "original_candidate_path": relative(candidate_path), "original_candidate_sha256": sha256_file(candidate_path),
                     "original_cache_path": relative(cache_path), "original_cache_sha256": sha256_file(cache_path),
                     "original_seed": cached["multistart"]["seed"],
                     "ordinary_changed_data_seed": seed_from(f"{protocol['optimizer']['seed']}:{dynamics}:{dev.sha256}"),
                     "original_canonical_parameter_order": cached["canonical_param_keys"],
                     "reason": "Change only initial Li2CO3; keep the original multistart seed and canonical parameter order."})
    result = {"created_at": now(), "jobs": jobs, "notes": [
        "These are numerical controls, excluded from the primary ranking and official fit cache.",
        "Each job uses the unchanged core fitting protocol and original canonical parameter order.",
        "A fixed seed alone is insufficient when equivalent candidates reorder optimizer coordinates.",
        "Run serially with --run-repeat LABEL; no optimizer repeats execute during scoring."]}
    atomic_write_json(out / "numerics/optimizer_repeat_plan.json", result)
    return result


def run_repeat(job, out=OUT):
    protocol, engine = read(PROTOCOL_PATH), code_identity()["sha256"]
    dev, hold, files = observations(job["paths"], protocol)
    signature = {"job_sha256": sha256_json(job), "data_sha256": dev.sha256,
                 "heldout_sha256": hold.sha256, "protocol_sha256": sha256_json(protocol),
                 "engine_sha256": engine, "score_code_sha256": sha256_file(__file__)}
    identity = sha256_json(signature)
    destination = out / "numerics/optimizer_repeats" / job["label"] / f"{identity}.json"
    if destination.exists():
        return read(destination)
    start = time.perf_counter()
    sub = job["submission"]
    validation = validate_submission(sub, dev, protocol)
    if validation["status"] != "valid" or validation["dynamics_hash"] != job["dynamics_hash"]:
        raise ValueError("repeat candidate validation changed")
    if sha256_file(ROOT / job["original_cache_path"]) != job["original_cache_sha256"]:
        raise ValueError("original cache changed since the repeat plan was made")
    comp = compile_mechanism(sub["mechanism"], dev.conditions, protocol["bounds"])
    keys = canonical_param_keys(comp, validation["canonical_map"])
    original_keys = job["original_canonical_parameter_order"]
    if sorted(keys) != sorted(original_keys):
        raise ValueError("cannot reproduce original optimizer parameter coordinates")
    comp.free = [comp.free[keys.index(key)] for key in original_keys]
    fitted = fit(Problem(comp, dev, validation["observation_map"], protocol), protocol, job["original_seed"])
    fitted.update(free_parameter_names=comp.free_names(), canonical_param_keys=original_keys,
                  canonical_species=validation["canonical_map"]["labels"], observation_notes=dev.notes)
    result = {"identity": identity, **signature, "created_at": now(), "job": job,
              "dataset_file_sha256": files, "fit_status": fitted["status"], "fit": fitted,
              "primary_ranking_eligible": False}
    if fitted["status"] == "fitted":
        reference = read(ROOT / job["original_cache_path"])["result"]
        reference = translate_fit(reference, validation, comp)
        result["difference_from_original_fit"] = {"nll": fitted["nll"] - reference["nll"],
                                                   "aicc": fitted["aicc"] - reference["aicc"],
                                                   "max_abs_theta": float(np.max(np.abs(np.array(fitted["theta"]) - reference["theta"])))}
        sigma = read(ROOT / "investigations/runs/chapman750-propose_space-opus1/final/chapman2023_fig2_750C/predictions.json")["common_sigma"]
        result.update(predict_with_verification(comp, validation, fitted, hold, sigma))
    result["wall_s"] = time.perf_counter() - start
    atomic_write_json(destination, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--scenario", choices=["fig2_nominal", "fig2_lower", "s1_nominal", "s1_lower"])
    parser.add_argument("--mode", choices=["fixed", "shared", "per_temperature"])
    parser.add_argument("--ids", help="comma-separated dynamics hashes")
    parser.add_argument("--plan-repeats", action="store_true")
    parser.add_argument("--run-repeat", choices=["baseline_selected", "opus1_selected"])
    args = parser.parse_args()
    if args.plan_repeats or args.run_repeat:
        plan = repeat_plan(args.out)
        if args.run_repeat:
            job = next(j for j in plan["jobs"] if j["label"] == args.run_repeat)
            result = run_repeat(job, args.out)
            print(json.dumps({"label": job["label"], "fit_status": result["fit_status"],
                              "difference_from_original_fit": result.get("difference_from_original_fit"),
                              "wall_s": result["wall_s"]}), flush=True)
        else:
            print(json.dumps({"repeat_jobs_planned": len(plan["jobs"])}), flush=True)
        return
    selected = set(args.ids.split(",")) if args.ids else None
    paths = sorted((args.out / "results").glob(f"{args.scenario or '*'}__{args.mode or '*'}/*.json"))
    counts, reused, processed = Counter(), 0, 0
    for path in paths:
        if selected and path.stem not in selected:
            continue
        record, cached = rescore(path, args.out)
        counts[record["prediction_status"]] += 1
        reused += int(cached)
        processed += 1
        if not cached and (processed % 50 == 0 or record["prediction_status"] not in ("predicted", "not_attempted_fit_failed")):
            print(json.dumps({"completed": processed, "scenario": record["scenario"],
                              "dynamics_hash": record["dynamics_hash"], "prediction_status": record["prediction_status"]}), flush=True)
    print(json.dumps({"finished": now(), "snapshot_inputs": len(paths), "processed": processed,
                      "reused_scores": reused, "prediction_statuses": counts}), flush=True)


if __name__ == "__main__":
    main()
