#!/usr/bin/env python3
"""Snapshot and revalidate fresh Chapman proposals without fitting or changing a run.

The fresh set remains separate from the frozen 904-member historical inventory.
Rerun after the investigator submits more candidates or freezes its selection.
Only development observations are loaded; no held-out predictions are evaluated.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nernstwork.data import joint_observation_set, load_dataset, sha256_file, sha256_json
from nernstwork.evaluate import code_identity, fit_key, validate_submission


def read(path):
    return json.loads(Path(path).read_text())


def relative(path):
    return str(Path(path).resolve().relative_to(ROOT))


def write(path, value):
    raw = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(raw)
    tmp.replace(path)
    return hashlib.sha256(raw.encode()).hexdigest()


def export(run, out):
    run = run.resolve()
    # Sources must resolve inside this repository, not to stale paths on another device.
    relative(run)
    manifest = read(run / "manifest.json")
    protocol = read(run / "protocol.json")
    if sha256_json(protocol) != manifest["protocol"]["sha256"]:
        raise ValueError("Run protocol differs from its manifest")
    code = code_identity()
    if code["sha256"] != manifest["code"]["sha256"]:
        raise ValueError("Current validation/fit engine differs from the run manifest")
    paths = []
    for entry in manifest["datasets"]:
        if entry["role"] != "development":
            continue
        path = (ROOT / entry["path"]).resolve()
        relative(path)
        if sha256_file(path) != entry["sha256"]:
            raise ValueError(f"Development input differs from manifest: {path}")
        paths.append(path)
    if len(paths) != 2:
        raise ValueError("Expected exactly two Chapman development inputs")
    obs = joint_observation_set([load_dataset(path) for path in paths], protocol.get("exclude_t0", True))
    candidate_paths = sorted((run / "candidates").glob("*.json"))
    if not candidate_paths:
        raise ValueError("Fresh run has no saved candidates yet")
    collection, excluded, source_hashes = {}, [], {}
    source_statuses, conservation_counts = Counter(), Counter()
    for path in candidate_paths:
        raw = path.read_bytes()
        stored = json.loads(raw)
        if path.stem != stored["candidate_id"]:
            raise ValueError(f"Candidate ID/path mismatch: {path}")
        source_hashes[relative(path)] = hashlib.sha256(raw).hexdigest()
        sub = stored["submission"]
        validation = validate_submission(sub, obs, protocol)
        source_statuses[validation["status"]] += 1
        previous = stored["validation"]
        if validation["status"] != previous["status"]:
            raise ValueError(f"Validation status changed: {path}")
        if validation["status"] != "valid":
            excluded.append({"path":relative(path),"candidate_id":stored["candidate_id"],"validation":validation})
            continue
        if any(validation[key] != previous[key] for key in ("dynamics_hash", "chem_hash")):
            raise ValueError(f"Stored/current canonical identity differs: {path}")
        dh = validation["dynamics_hash"]
        source = {"kind":"fresh_candidate", "run_id":run.name, "path":relative(path),
                  "candidate_id":stored["candidate_id"],"source_sha256":source_hashes[relative(path)],
                  "submission_sha256":sha256_json(sub),"chem_hash":validation["chem_hash"],
                  "declared_conserved_elements":sub["mechanism"].get("conservation",{}).get("elements",[]),
                  "origin":stored.get("origin",{})}
        carbonate_used = any(t["species"] == "Li2CO3" for r in sub["mechanism"]["reactions"] for t in r["reactants"])
        carbonate_observed = any("Li2CO3" in v for v in sub.get("observation_map",{}).values())
        elements = sub["mechanism"].get("conservation",{}).get("elements",[])
        key = fit_key(dh, obs.sha256, protocol, code["sha256"])
        record = collection.setdefault(dh, {"submission":sub,"validation":validation,"dynamics_hash":dh,
            "sources":[],"carbonate_independent":not carbonate_used and not carbonate_observed,
            "declared_conserved_elements":elements,"declares_lithium_conservation":"Li" in elements,
            "development_fit_key":key,
            "development_cache_path":relative(ROOT / "investigations/cache/fits" / key / "result.json")})
        record["sources"].append(source)
        conservation_counts["+".join(sorted(elements)) or "other_basis"] += 1
    records = [collection[key] for key in sorted(collection)]
    for record in records:
        record["chemistry_hashes"] = sorted({source["chem_hash"] for source in record["sources"]})
        record["conservation_declarations"] = sorted({tuple(source["declared_conserved_elements"]) for source in record["sources"]})
    frozen_path = run / "frozen.json"
    frozen = None
    if frozen_path.is_file():
        saved = read(frozen_path)
        selected = read(run / "candidates" / f"{saved['top1']}.json")
        dh = selected["validation"]["dynamics_hash"]
        if dh not in collection:
            raise ValueError("Frozen top1 absent from the exported validated candidates")
        frozen = {"candidate_id":saved["top1"],"dynamics_hash":dh,"frozen_at":saved.get("frozen_at"),
                  "rule":saved.get("rule"),"path":relative(frozen_path),"sha256":sha256_file(frozen_path)}
    state_path = run / "pi/host_state.json"
    state = read(state_path) if state_path.is_file() else {}
    old = read(out / "repaired_aliases.json") if (out / "repaired_aliases.json").is_file() else []
    old_ids = {r["dynamics_hash"] for r in old}
    overlap = set(collection) & old_ids
    out.mkdir(parents=True, exist_ok=True)
    (out / ".gitignore").write_text("*\n")
    records_hash = write(out / "fresh_opus_records.json", records)
    inventory = {"generated_at_utc":datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "run_id":run.name,"run_path":relative(run),"scenario":"fig2_lower","mode":"fixed",
        "scope":"Saved candidates at export time; separate from historical inventory; no fits performed",
        "candidate_files":len(candidate_paths),"validation_statuses":dict(source_statuses),
        "unique_valid_dynamics":len(records),"duplicate_dynamics_candidates":sum(len(r["sources"])-1 for r in records),
        "declared_element_counts_by_valid_source":dict(conservation_counts),
        "overlap_with_old_904":len(overlap),"new_relative_to_old_904":len(set(collection)-old_ids),
        "old_inventory_available":bool(old),"excluded_candidates":excluded,"frozen_selection":frozen,
        "host_state":{key:state.get(key) for key in ("phase","round","submissionsOpen","concluded","updatedAt")},
        "frozen_at_export":frozen is not None,"records_path":relative(out/"fresh_opus_records.json"),
        "records_sha256":records_hash,"source_sha256":source_hashes,
        "manifest_sha256":sha256_file(run/"manifest.json"),"protocol_sha256":sha256_json(protocol),
        "engine_sha256":code["sha256"],"development_data_sha256":obs.sha256,
        "development_input_sha256":{relative(path):sha256_file(path) for path in paths},
        "exporter_sha256":sha256_file(Path(__file__))}
    write(out / "fresh_opus_inventory.json", inventory)
    return inventory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run",type=Path,default=ROOT/"investigations/runs/chapman-li-oct22-opus1")
    parser.add_argument("--out",type=Path,default=ROOT/"data/derived/chapman_li_sensitivity")
    args = parser.parse_args()
    inventory = export(args.run,args.out)
    print(json.dumps({key:inventory[key] for key in ("run_id","candidate_files","validation_statuses",
        "unique_valid_dynamics","overlap_with_old_904","new_relative_to_old_904","frozen_selection","host_state")},indent=2))


if __name__ == "__main__":
    main()
