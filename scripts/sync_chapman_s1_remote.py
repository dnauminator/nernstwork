#!/usr/bin/env python3
"""Import committed remote S1 artifacts without overwriting any local file.

Read-only SSH snapshots only the 282 owned dynamics and their expected fit keys.
rsync --ignore-existing fetches into quarantine; hashes, ownership and identities
are verified before atomic create-only imports. Attempts and partial files stay
on the execution host. No deletion or workload control is performed.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from nernstwork.data import sha256_json
from nernstwork.evaluate import fit_key


def read(path):
    return json.loads(Path(path).read_text())


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_body(name,body,manifest,expected,sigma):
    info=expected[name]
    if info["kind"]=="cache":
        if body.get("fit_key")!=info["fit_key"] or not body.get("committed_by_attempt") or not body.get("committed_at") or "result" not in body:
            raise ValueError(f"Uncommitted or mismatched cache record: {name}")
        return
    scenario=info["scenario"]
    required={"dynamics_hash":info["dynamics_hash"],"scenario":scenario,"mode":"fixed",
        "engine_sha256":manifest["engine_sha256"],"protocol_sha256":info["protocol_sha256"],
        "data_sha256":manifest["scenario_hashes"][scenario]["development"],
        "heldout_sha256":manifest["scenario_hashes"][scenario]["heldout"],"common_sigma":sigma,"force_refit":False}
    if any(body.get(key)!=value for key,value in required.items()):
        raise ValueError(f"Remote result ownership/input/engine mismatch: {name}")
    signature={key:value for key,value in required.items() if key!="scenario"}
    if body.get("identity")!=sha256_json(signature):
        raise ValueError(f"Remote result identity mismatch: {name}")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest",type=Path,required=True)
    args=parser.parse_args()
    manifest_path=args.manifest.resolve()
    manifest=read(manifest_path)
    alias=manifest["ssh_alias"]
    stage=manifest["remote_stage"]
    if alias!="spark-f7e2-direct" or not re.fullmatch(r"/home/jarrodbarnes/nernstwork-staging/chapman-li-\d{8}-\d{8}T\d{6}Z",stage):
        raise ValueError("Unexpected remote alias or staging path")
    ids=manifest["remote_dynamics"]
    if len(ids)!=282 or len(set(ids))!=282 or set(ids)&set(manifest["local_dynamics"]):
        raise ValueError("Ownership manifest is not the disjoint 282-member remote set")
    if any(not re.fullmatch("[a-f0-9]{64}",dh) for dh in ids):
        raise ValueError("Invalid dynamics identifier")
    protocol_path=ROOT/"configs/protocols/synthesis-mle-v1.json"
    if digest(protocol_path)!=manifest["source_sha256"][str(protocol_path.relative_to(ROOT))]:
        raise ValueError("Local protocol changed since the remote launch")
    protocol=read(protocol_path)
    sigma=read(ROOT/"investigations/runs/chapman750-propose_space-opus1/final/chapman2023_fig2_750C/predictions.json")["common_sigma"]
    expected={}
    for scenario in ("s1_nominal","s1_lower"):
        for dh in ids:
            key=fit_key(dh,manifest["scenario_hashes"][scenario]["development"],protocol,manifest["engine_sha256"])
            expected[f"investigations/cache/fits/{key}/result.json"]={"kind":"cache","fit_key":key}
            expected[f"data/derived/chapman_li_sensitivity/results/{scenario}__fixed/{dh}.json"]={
                "kind":"result","dynamics_hash":dh,"scenario":scenario,"protocol_sha256":sha256_json(protocol)}
    config={"stage":stage,"host":manifest["remote_host"],"files":list(expected),
            "manifest":str(manifest_path.relative_to(ROOT)),"manifest_sha256":digest(manifest_path),
            "runtime":manifest["run_artifacts"]+"/runtime_manifest.json"}
    script="""import hashlib,json,socket
from pathlib import Path
config=json.loads(CONFIGURATION)
root=Path(config['stage'])
assert socket.gethostname()==config['host']
assert hashlib.sha256((root/config['manifest']).read_bytes()).hexdigest()==config['manifest_sha256']
files={}
for name in config['files']:
    path=root/name
    if path.is_file():
        raw=path.read_bytes()
        json.loads(raw)
        files[name]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
runtime=json.loads((root/config['runtime']).read_text())
print(json.dumps({'host':socket.gethostname(),'files':files,'runtime':runtime}))
""".replace("CONFIGURATION",repr(json.dumps(config)))
    raw=subprocess.check_output(["ssh","-o","BatchMode=yes","-o","StrictHostKeyChecking=yes",alias,"python3 -"],input=script,text=True)
    remote=json.loads(raw)
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"-"+uuid.uuid4().hex[:8]
    batch=manifest_path.parent/"imports"/stamp
    incoming=batch/"incoming"
    incoming.mkdir(parents=True)
    (batch/"remote_snapshot.json").write_text(json.dumps(remote,indent=2)+"\n")
    all_names=sorted(remote["files"])
    if any(name not in expected for name in all_names):
        raise ValueError("Unexpected path returned by remote snapshot")
    identical=[name for name in all_names if (ROOT/name).is_file() and digest(ROOT/name)==remote["files"][name]["sha256"]]
    for name in identical:
        validate_body(name,read(ROOT/name),manifest,expected,sigma)
    names=[name for name in all_names if name not in set(identical)]
    listing=batch/"files.txt"
    listing.write_text("\n".join(names)+("\n" if names else ""))
    if names:
        subprocess.run(["rsync","-a","--ignore-existing","--protect-args","--files-from",str(listing),
                        "-e","ssh -o BatchMode=yes -o StrictHostKeyChecking=yes",f"{alias}:{stage}/",str(incoming)+"/"],check=True)
    collisions=[]
    for name in names:
        path=incoming/name
        if digest(path)!=remote["files"][name]["sha256"]:
            raise ValueError(f"Transferred artifact hash mismatch: {name}")
        validate_body(name,read(path),manifest,expected,sigma)
        destination=ROOT/name
        if destination.exists() and digest(destination)!=digest(path):
            collisions.append(name)
    if collisions:
        (batch/"collisions.json").write_text(json.dumps(collisions,indent=2)+"\n")
        raise ValueError(f"{len(collisions)} existing local artifacts differ; entire batch remains in quarantine")
    created,existing=[],identical.copy()
    for name in names:
        source,destination=incoming/name,ROOT/name
        destination.parent.mkdir(parents=True,exist_ok=True)
        try:
            os.link(source,destination)  # atomic create-only; never replaces a destination
            created.append(name)
        except FileExistsError:
            if digest(destination)!=digest(source):
                raise ValueError(f"New local collision during create-only import: {name}")
            existing.append(name)
    result={"imported_at":datetime.now(timezone.utc).isoformat(),"manifest_sha256":digest(manifest_path),
        "remote_host":remote["host"],"created":created,"already_identical":existing,
        "committed_cache_records":sum(expected[name]["kind"]=="cache" for name in all_names),
        "result_records":sum(expected[name]["kind"]=="result" for name in all_names),
        "transferred_bytes":sum(remote["files"][name]["bytes"] for name in names),"batch":str(batch.relative_to(ROOT))}
    (batch/"import.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({key:value for key,value in result.items() if key not in ("created","already_identical")}|
                     {"created_count":len(created),"already_identical_count":len(existing)},indent=2))


if __name__=="__main__":
    main()
