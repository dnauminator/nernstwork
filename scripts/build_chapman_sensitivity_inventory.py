#!/usr/bin/env python3
"""Export the finite Oct 21 Chapman hypothesis set without fitting or changing its sources.

Run from the repository with .venv/bin/python scripts/build_chapman_sensitivity_inventory.py.
The default output is local, ignored campaign input under data/derived/chapman_li_sensitivity/.
The comparable set preserves all originally valid dynamics. A separate repaired set adds
members omitted by two representation errors; it does not silently change the original set.
"""
from __future__ import annotations

import argparse
import copy
import json
from collections import Counter
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nernstwork.data import joint_observation_set, load_dataset, sha256_file, sha256_json
from nernstwork.enumerate import enumerate_space
from nernstwork.evaluate import code_identity, fit_key, validate_submission


def relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def repaired_submission(original: dict) -> tuple[dict, list[dict]]:
    """Repair representation only, retaining every reaction, coefficient and rate law."""
    sub = copy.deepcopy(original)
    repairs = []
    for i, species in enumerate(sub["mechanism"]["species"]):
        if species.get("phase") == "unobserved":
            repairs.append({"path": f"/mechanism/species/{i}/phase", "old": "unobserved",
                            "operation": "remove", "reason": "unobserved is not a physical phase; field is optional"})
            del species["phase"]
        if species.get("role") == "Li sink (volatilised or amorphous Li-O)":
            repairs.append({"path": f"/mechanism/species/{i}/role", "old": species["role"], "new": "sink",
                            "operation": "replace", "reason": "use the schema's sink role; chemistry is unchanged"})
            species["role"] = "sink"
    ids = {s["id"] for s in sub["mechanism"]["species"]}
    for channel, mapped in sub.get("observation_map", {}).items():
        present = [s for s in mapped if s in ids]
        if present != mapped:
            if not present:
                raise ValueError(f"repair would leave {channel} without any observed species")
            repairs.append({"path": f"/observation_map/{channel}", "old": mapped, "new": present,
                            "operation": "replace", "reason": "optional species absent from this enumerated member"})
            sub["observation_map"][channel] = present
    return sub, repairs


def build(out: Path, runs_root: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    # Keep local run artifacts out of git without editing the repository-wide ignore rules.
    (out / ".gitignore").write_text("*\n")
    protocol_path = ROOT / "configs/protocols/synthesis-mle-v1.json"
    protocol = json.loads(protocol_path.read_text())
    data_paths = [ROOT / f"data/real/chapman2023_fig2_{t}C.json" for t in (700, 725)]
    obs = joint_observation_set([load_dataset(p) for p in data_paths], protocol.get("exclude_t0", True))
    code = code_identity()
    inputs = {relative(p): sha256_file(p) for p in [protocol_path, *data_paths]}
    comparable, repaired = {}, {}
    comparable_chem, repaired_chem = set(), set()
    records, space_counts = [], []
    historical_by_run = {}

    def add(sub: dict, source: dict) -> None:
        original = validate_submission(sub, obs, protocol)
        fixed, changes = repaired_submission(sub)
        revised = validate_submission(fixed, obs, protocol)
        record = {"source": source, "submission_name": sub["name"],
                  "original_submission_sha256": sha256_json(sub), "original_status": original["status"],
                  "original_errors": original["errors"], "repairs": changes,
                  "repaired_submission_sha256": sha256_json(fixed), "repaired_status": revised["status"],
                  "repaired_errors": revised["errors"]}
        for label, candidate, validation, target, chemistry in (
            ("original", sub, original, comparable, comparable_chem),
            ("repaired", fixed, revised, repaired, repaired_chem),
        ):
            if validation["status"] != "valid":
                continue
            dynamic, chem = validation["dynamics_hash"], validation["chem_hash"]
            chemistry.add(chem)
            record[f"{label}_dynamics_hash"] = dynamic
            record[f"{label}_chem_hash"] = chem
            item = target.setdefault(dynamic, {"submission": candidate, "representative_source": source,
                                               "chemistry_hashes": set(), "source_record_indices": []})
            item["chemistry_hashes"].add(chem)
            item["source_record_indices"].append(len(records))
        records.append(record)

    reference = ROOT / "configs/spaces/chapman_core.json"
    inputs[relative(reference)] = sha256_file(reference)
    spaces = [(reference, json.loads(reference.read_text()), "chapman750-enumeration")]
    runs = [runs_root / f"chapman750-propose_space-{name}" for name in ("opus1", "opus2", "gemini1", "gemini2")]
    for run in runs:
        if not run.is_dir():
            raise FileNotFoundError(f"required historical run is missing: {run}")
        for path in sorted((run / "spaces").glob("space-*.json")):
            inputs[relative(path)] = sha256_file(path)
            spaces.append((path, json.loads(path.read_text())["space"], run.name))
    for path, space, run_id in spaces:
        start = len(records)
        for sub in enumerate_space(space):
            add(sub, {"kind": "enumerated_space", "path": relative(path), "run_id": run_id,
                      "space_id": space["space_id"], "space_sha256": sha256_json(space)})
        subset = records[start:]
        space_counts.append({"path": relative(path), "run_id": run_id, "space_id": space["space_id"],
                             "members": len(subset),
                             "original_statuses": dict(Counter(r["original_status"] for r in subset)),
                             "repaired_statuses": dict(Counter(r["repaired_status"] for r in subset))})
    for run in [runs_root / "chapman750-enumeration", *runs]:
        candidates = []
        for path in sorted((run / "candidates").glob("*.json")):
            stored = json.loads(path.read_text())
            candidates.append(stored)
            inputs[relative(path)] = sha256_file(path)
            if stored["origin"]["source"] == "agent":
                add(stored["submission"], {"kind": "standalone_candidate", "path": relative(path),
                                          "run_id": run.name, "candidate_id": stored["candidate_id"]})
        historical_by_run[run.name] = candidates

    expected = {"raw_members": 1108, "original_valid": 1016, "comparable_dynamics": 860,
                "comparable_chemistry": 940, "repaired_dynamics": 904, "repaired_chemistry": 993}
    actual = {"raw_members": len(records), "original_valid": sum(r["original_status"] == "valid" for r in records),
              "comparable_dynamics": len(comparable), "comparable_chemistry": len(comparable_chem),
              "repaired_dynamics": len(repaired), "repaired_chemistry": len(repaired_chem)}
    if actual != expected or any(r["repaired_status"] != "valid" for r in records):
        raise ValueError(f"historical inventory changed; review before using: expected {expected}, got {actual}")
    historical_dynamics = {c["validation"]["dynamics_hash"] for cs in historical_by_run.values() for c in cs
                           if c["validation"]["status"] == "valid"}
    if historical_dynamics != set(comparable):
        raise ValueError("re-enumeration does not reproduce every stored historical dynamic hypothesis")

    exports = {}
    cache_inventory = []
    for name, collection in (("comparable", comparable), ("repaired", repaired)):
        dynamics = sorted(collection)
        filename = f"{name}_candidates.json"
        write_json(out / filename, [collection[h]["submission"] for h in dynamics])
        aliases = []
        candidate_records = []
        for index, h in enumerate(dynamics):
            item = collection[h]
            key = fit_key(h, obs.sha256, protocol, code["sha256"])
            result_path = runs_root.parent / "cache/fits" / key / "result.json"
            alias = {"export_index": index, "dynamics_hash": h, "chemistry_hashes": sorted(item["chemistry_hashes"]),
                     "representative_source": item["representative_source"],
                     "source_record_indices": item["source_record_indices"], "old_data_fit_key": key,
                     "old_data_cache_path": relative(result_path), "old_data_cache_exists": result_path.is_file()}
            aliases.append(alias)
            sub = item["submission"]
            carbonate_used = any(t["species"] == "Li2CO3" for r in sub["mechanism"]["reactions"]
                                 for t in r["reactants"])
            carbonate_observed = any("Li2CO3" in v for v in sub.get("observation_map", {}).values())
            candidate_records.append({"submission": sub, "validation": validate_submission(sub, obs, protocol),
                                      "dynamics_hash": h,
                                      "sources": [records[i]["source"] for i in item["source_record_indices"]],
                                      "source_record_indices": item["source_record_indices"],
                                      "carbonate_independent": not carbonate_used and not carbonate_observed,
                                      "old_data_fit_key": key, "old_data_cache_path": relative(result_path)})
            if name == "comparable":
                status, timing = None, {}
                if result_path.is_file():
                    result = json.loads(result_path.read_text()).get("result", {})
                    status, timing = result.get("status"), result.get("timing", {})
                cache_inventory.append({"dynamics_hash": h, "fit_key": key, "status": status, "timing": timing,
                                        "carbonate_independent": not carbonate_used and not carbonate_observed})
        write_json(out / f"{name}_aliases.json", aliases)
        write_json(out / f"{name}_records.json", candidate_records)
        exports[name] = {"path": relative(out / filename), "n_dynamics": len(dynamics),
                         "sha256": sha256_file(out / filename), "aliases": relative(out / f"{name}_aliases.json"),
                         "records": relative(out / f"{name}_records.json")}

    for name, run_id in (("baseline", "chapman750-enumeration"), ("prior_opus1", "chapman750-propose_space-opus1")):
        candidates = historical_by_run[run_id]
        path = out / f"{name}_candidates.json"
        write_json(path, [c["submission"] for c in candidates])
        exports[name] = {"path": relative(path), "n_candidates": len(candidates), "sha256": sha256_file(path),
                         "candidate_ids": [c["candidate_id"] for c in candidates]}
    frozen_path = runs[0] / "frozen.json"
    inputs[relative(frozen_path)] = sha256_file(frozen_path)
    top1 = json.loads(frozen_path.read_text())["top1"]
    top1_sub = next(c["submission"] for c in historical_by_run[runs[0].name] if c["candidate_id"] == top1)
    write_json(out / "prior_opus1_top1_candidate.json", top1_sub)
    exports["prior_opus1_top1"] = {"path": relative(out / "prior_opus1_top1_candidate.json"), "candidate_id": top1}
    write_json(out / "source_records.json", records)
    repair_log = [dict(source=r["source"], submission_name=r["submission_name"],
                       original_errors=r["original_errors"], repairs=r["repairs"],
                       repaired_dynamics_hash=r.get("repaired_dynamics_hash")) for r in records if r["repairs"]]
    write_json(out / "repair_log.json", repair_log)
    write_json(out / "config_candidates.json", exports)
    timing_report = {}
    for name, selected in (("all", cache_inventory),
                           ("carbonate_independent", [r for r in cache_inventory if r["carbonate_independent"]]),
                           ("carbonate_dependent", [r for r in cache_inventory if not r["carbonate_independent"]])):
        values = sorted(r["timing"]["cpu_s"] for r in selected if "cpu_s" in r["timing"])
        if values:
            timing_report[name] = {"n": len(values), "cpu_hours": sum(values) / 3600,
                                   "median_cpu_s": statistics.median(values), "p90_cpu_s": values[int(.9 * (len(values) - 1))],
                                   "p95_cpu_s": values[int(.95 * (len(values) - 1))], "max_cpu_s": max(values)}
    write_json(out / "historical_runtime.json", timing_report)
    inventory = {"inventory_version": 1, "counts": actual, "spaces": space_counts, "exports": exports,
                 "input_sha256": inputs, "development_dataset_sha256": obs.sha256,
                 "protocol_sha256": sha256_json(protocol), "evaluator_code": code,
                 "repair_members": len(repair_log), "original_cache_statuses": dict(Counter(x["status"] for x in cache_inventory)),
                 "cache_inventory": cache_inventory,
                 "notes": ["No fitting or held-out scoring is performed by this script.",
                           "Comparable candidates are deduplicated by dynamics, retaining chemistry/source aliases.",
                           "Repaired candidates differ only in invalid optional metadata or an absent optional observation-map species.",
                           "Space IDs are not unique; use source paths and hashes.",
                           "Cache keys apply only to the exact original development files, protocol, and evaluator code.",
                           "The finite union reuses proposals made on the old extraction; it is not an exhaustive chemistry search."]}
    write_json(out / "inventory.json", inventory)
    return inventory


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "data/derived/chapman_li_sensitivity")
    parser.add_argument("--runs-root", type=Path, default=ROOT / "investigations/runs")
    args = parser.parse_args()
    result = build(args.out.resolve(), args.runs_root.resolve())
    print(json.dumps({"output": relative(args.out), "counts": result["counts"],
                      "repaired_members": result["repair_members"],
                      "old_cache_statuses": result["original_cache_statuses"]}, indent=2))
