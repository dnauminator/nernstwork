#!/usr/bin/env python3
"""Run only the frozen S1 carbonate-dependent subset in a dedicated CPU staging tree.

The launch manifest fixes source hashes, exact engine identity, input hashes, host,
and disjoint ownership. This script does not install software or contact APIs.
The caller must apply the documented systemd CPU/memory/priority limits.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def verify(manifest_path):
    manifest=json.loads(manifest_path.read_text())
    if str(ROOT)!=manifest["remote_stage"] or socket.gethostname()!=manifest["remote_host"]:
        raise ValueError("This manifest belongs to a different staging tree or host")
    for name,expected in manifest["source_sha256"].items():
        path=(ROOT/name).resolve()
        path.relative_to(ROOT)
        if digest(path)!=expected:
            raise ValueError(f"Staged source hash mismatch: {name}")
    for variable in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","NUMEXPR_NUM_THREADS"):
        if os.environ.get(variable)!="1":
            raise ValueError(f"{variable} must be 1 before importing the numerical engine")
    if os.environ.get("CUDA_VISIBLE_DEVICES")!="":
        raise ValueError("This launch must hide all CUDA devices")
    from run_chapman_li_sensitivity import CODE,PROTOCOL,inputs,no_carbonate_dependence
    from nernstwork.evaluate import code_identity,validate_submission
    if CODE!=manifest["engine_sha256"]:
        raise ValueError("Staged numerical code/version identity mismatch")
    versions=code_identity()["versions"]
    if versions!=manifest["versions"]:
        raise ValueError("Staged software versions differ from approved local versions")
    records_path=ROOT/manifest["records_path"]
    records=json.loads(records_path.read_text())
    ids={record["dynamics_hash"] for record in records}
    if len(records)!=282 or len(ids)!=282 or ids!=set(manifest["remote_dynamics"]):
        raise ValueError("The fixed remote subset must contain exactly 282 unique dynamics")
    if ids & set(manifest["local_dynamics"]):
        raise ValueError("Remote and local extraction ownership overlap")
    if any(no_carbonate_dependence(record["submission"]) for record in records):
        raise ValueError("An invariant baseline member appeared in the remote subset")
    for scenario in ("s1_nominal","s1_lower"):
        obs,hold,_=inputs(scenario)
        if obs.sha256!=manifest["scenario_hashes"][scenario]["development"] or hold.sha256!=manifest["scenario_hashes"][scenario]["heldout"]:
            raise ValueError(f"Staged dataset identity mismatch: {scenario}")
        for record in records:
            validation=validate_submission(record["submission"],obs,PROTOCOL)
            if validation["status"]!="valid" or validation["dynamics_hash"]!=record["dynamics_hash"]:
                raise ValueError(f"Staged candidate validation differs: {record['dynamics_hash']}")
    return manifest,{"verified_at":now(),"host":socket.gethostname(),"architecture":platform.machine(),
        "python_executable":sys.executable,"code_identity":code_identity(),"candidate_count":len(records),
        "manifest_sha256":digest(manifest_path),"worker_count":6,"gpu_use":False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest",type=Path,required=True)
    parser.add_argument("--verify-only",action="store_true")
    args=parser.parse_args()
    manifest,runtime=verify(args.manifest.resolve())
    print(json.dumps(runtime),flush=True)
    if args.verify_only:
        return
    out=ROOT/manifest["run_artifacts"]
    out.mkdir(parents=True,exist_ok=True)
    (out/"runtime_manifest.json").write_text(json.dumps(runtime,indent=2)+"\n")
    for scenario in ("s1_nominal","s1_lower"):
        command=[sys.executable,str(ROOT/"scripts/run_chapman_li_sensitivity.py"),"--records",str(ROOT/manifest["records_path"]),
                 "--scenario",scenario,"--mode","fixed","--workers","6"]
        print(json.dumps({"started_at":now(),"scenario":scenario,"command":command}),flush=True)
        with (out/f"{scenario}.log").open("a") as logfile:
            subprocess.run(command,cwd=ROOT,check=True,stdout=logfile,stderr=subprocess.STDOUT)
        print(json.dumps({"completed_at":now(),"scenario":scenario}),flush=True)
    (out/"completed.json").write_text(json.dumps({"completed_at":now(),"manifest_sha256":runtime["manifest_sha256"]},indent=2)+"\n")


if __name__=="__main__":
    main()
