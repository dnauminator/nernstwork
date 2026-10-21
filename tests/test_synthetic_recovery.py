"""Synthetic known-mechanism checks of the evaluator and enumeration baseline.

These test correctness of the pipeline on data generated from a known network. They are not evidence of physical
discovery, and they do not require exact recovery where candidates are statistically equivalent.
"""
import json

import pytest

from nernstwork import investigation as inv
from nernstwork.enumerate import enumerate_space
from nernstwork.synthetic import synthetic_dataset

TIMES = [0, 10, 20, 30, 40, 50, 60, 80, 100, 120, 150, 180, 360, 720, 1080, 1440, 2160, 2880]
SP = [{"id": "NO3", "N_oxidation_state": 5}, {"id": "NO2", "N_oxidation_state": 3}, {"id": "NH3", "N_oxidation_state": -3},
      {"id": "SINK", "N_oxidation_state": 0, "observable": False, "role": "sink"}]


def rx(i, a, b, e, k, tau=400.0):
    return {"id": i, "reactants": [{"species": a, "coeff": 1}], "products": [{"species": b, "coeff": 1}], "electrons": e,
            "rate_law": {"family": "mass_action", "params": {"k": {"value": k}},
                         "time_modulation": {"kind": "deactivation", "tau_min": {"value": tau, "tie": "tau_cat"}}}}


def make_run(root, tmp_path, truth, name, seed=1, rel=0.03):
    ds = synthetic_dataset(truth, {"NO3": 100.0}, TIMES, ["NO3", "NO2", "NH3"], rel=rel, abs_mM=0.2, seed=seed, ds_id=name)
    dp = tmp_path / f"{name}.json"
    dp.write_text(json.dumps(ds))
    proto = json.loads((root / "configs/protocols/mle-profiled-v1.json").read_text())
    proto["optimizer"]["n_starts"] = 8
    pp = tmp_path / "proto.json"
    pp.write_text(json.dumps(proto))
    cfg = json.loads((root / "configs/investigations/liao50.json").read_text())
    cfg.update(investigation_id=name, protocol=str(pp), enumeration_spaces=["configs/spaces/liao_core.json"])
    cfg["datasets"] = {"development": [str(dp)], "final_holdout": [], "partition_policy": "synthetic"}
    cfg["evidence"]["documents"] = []
    cp = tmp_path / "cfg.json"
    cp.write_text(json.dumps(cfg))
    run = inv.init_run(cp, "enumeration", name, tmp_path / "nw")
    space = json.loads((root / "configs/spaces/liao_core.json").read_text())
    inv.submit(run, enumerate_space(space), {"source": "enumerator"})
    inv.evaluate(run, workers=8)
    truth_cand = {"name": "truth", "mechanism": truth}
    tid = inv.submit(run, [truth_cand], {"source": "human"})[0]["candidate_id"]  # duplicate of an enumerated member
    return run, tid


def ranked(run):
    return inv.compare(run)["ranking"]["groups"][0]["rows"]


def test_known_mechanism_is_recovered_within_indistinguishable_set(root, tmp_path):
    truth = {"id": "truth", "species": SP, "reactions": [rx("R1", "NO3", "NO2", 2, 2e-3), rx("R2", "NO2", "NH3", 6, 1e-2),
                                                         rx("R3", "NO2", "SINK", 3, 3e-3)]}
    run, tid = make_run(root, tmp_path, truth, "syn_known")
    rows = ranked(run)
    band = {r["candidate_id"]: r for r in rows}
    assert tid in band and band[tid]["delta_aicc"] <= 2.0, rows[:3]
    # the truth's parameters come back near their generating values
    s = next(x for x in inv.summaries(run) if x["candidate_id"] == tid)
    vals = {n: p["value"] for n, p in s["params"].items()}
    stored = run.candidate(tid)["submission"]["mechanism"]["reactions"]
    rid = {(r["reactants"][0]["species"], r["products"][0]["species"]): r["id"] for r in stored}
    assert vals[f"{rid['NO3', 'NO2']}.k"] == pytest.approx(2e-3, rel=0.25)
    assert vals[f"{rid['NO2', 'NH3']}.k"] == pytest.approx(1e-2, rel=0.35)
    assert vals[f"{rid['NO2', 'SINK']}.k"] == pytest.approx(3e-3, rel=0.35)
    assert vals["tie:tau_cat"] == pytest.approx(400, rel=0.3)


def test_missing_branch_is_detected(root, tmp_path):
    truth = {"id": "truth", "species": SP, "reactions": [rx("R1", "NO3", "NO2", 2, 1e-3), rx("R2", "NO2", "NH3", 6, 1e-2),
                                                         rx("R3", "NO3", "NH3", 8, 4e-3)]}
    run, _tid = make_run(root, tmp_path, truth, "syn_branch", seed=2)
    rows = ranked(run)
    cands = {c["candidate_id"]: c for c in run.candidates()}
    with_branch = [r for r in rows if "NO3>NH3" in cands[r["candidate_id"]]["submission"]["rationale"]]
    without = [r for r in rows if "NO3>NH3" not in cands[r["candidate_id"]]["submission"]["rationale"]]
    assert min(r["aicc"] for r in without) - min(r["aicc"] for r in with_branch) > 10
    assert rows[0]["candidate_id"] in {r["candidate_id"] for r in with_branch}


def test_weak_sink_is_reported_as_ambiguous_not_resolved(root, tmp_path):
    truth = {"id": "truth", "species": SP, "reactions": [rx("R1", "NO3", "NO2", 2, 2e-3), rx("R2", "NO2", "NH3", 6, 1e-2),
                                                         rx("R3", "NO2", "SINK", 3, 2e-5)]}
    run, tid = make_run(root, tmp_path, truth, "syn_weak", seed=3, rel=0.05)
    rows = {r["candidate_id"]: r for r in ranked(run)}
    cands = {c["candidate_id"]: c for c in run.candidates()}
    no_sink = [cid for cid, c in cands.items() if c["origin"]["source"] == "enumerator" and "SINK" not in c["submission"]["rationale"]
               and "NO2>NH3" in c["submission"]["rationale"] and "NO3>NH3" not in c["submission"]["rationale"]
               and "shared_deactivation" in c["submission"]["rationale"]]
    assert no_sink and rows[no_sink[0]]["delta_aicc"] <= 4.0 and rows[tid]["delta_aicc"] <= 4.0
