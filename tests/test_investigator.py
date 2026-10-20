"""Contract tests for the investigation backend: data provenance, candidate identity, explicit statuses, equal treatment
of proposers, numerical reproducibility, cache invalidation, reviews, revisions, recovery and holdout separation."""
import copy
import json
import os
import subprocess
import sys

import numpy as np
import pytest

from nernstwork import investigation as inv
from nernstwork import simulate
from nernstwork.data import load_dataset, observation_set, sha256_file
from nernstwork.evaluate import fit_key, protocol_hash, run_fit, validate_submission
from nernstwork.model import Conditions, compile_mechanism
from nernstwork.review import validate_review
from nernstwork.store import create_once_json

DEV = "data/real/liao2025_mos2_suppfig50b.json"
HOLD = "data/real/liao2025_wmos2_suppfig50a.json"


def _sp(i, ox, **kw):
    return dict(id=i, N_oxidation_state=ox, **kw)


def _rx(i, a, b, e, tie="tau_cat", mod="deactivation", k=1e-3, family="mass_action", **extra):
    rl = {"family": family, "params": {"k": {"value": k}}}
    if family == "langmuir_saturation":
        rl["params"]["K"] = {"value": 50.0}
    if mod:
        rl["time_modulation"] = {"kind": mod, "tau_min": {"value": 300.0, **({"tie": tie} if tie else {})}}
    r = {"id": i, "reactants": [{"species": a, "coeff": 1}], "products": [{"species": b, "coeff": 1}], "electrons": e, "rate_law": rl}
    r.update(extra)
    return r


SPECIES = [_sp("NO3", 5), _sp("NO2", 3), _sp("NH3", -3), _sp("SINK", 0, observable=False, role="sink")]


def cand(name="c", reactions=None, species=None, **kw):
    reactions = reactions or [_rx("R1", "NO3", "NO2", 2), _rx("R2", "NO2", "NH3", 6), _rx("R3", "NO3", "NH3", 8),
                              _rx("R4", "NO3", "SINK", 5)]
    return {"name": name, "mechanism": {"id": name, "species": copy.deepcopy(species or SPECIES), "reactions": reactions}, **kw}


@pytest.fixture(scope="module")
def protocol(root):
    p = json.loads((root / "configs/protocols/mle-profiled-v1.json").read_text())
    p["optimizer"]["n_starts"] = 6
    return p


@pytest.fixture(scope="module")
def dev_obs(root):
    ds, sha = load_dataset(root / DEV)
    return observation_set(ds, sha)


@pytest.fixture()
def config(root, tmp_path, protocol):
    pp = tmp_path / "protocol.json"
    pp.write_text(json.dumps(protocol))
    cfg = json.loads((root / "configs/investigations/liao50.json").read_text())
    cfg["protocol"] = str(pp)
    cfg["enumeration_spaces"] = ["configs/spaces/liao_core.json"]
    cfg["agent"]["arms"]["propose_only"]["candidate_budget"] = 3
    p = tmp_path / "cfg.json"
    p.write_text(json.dumps(cfg))
    return p


# ------------------------------------------------------------------ data, units, provenance
def test_observation_set_excludes_initial_condition_and_keeps_units(root, dev_obs):
    ds, _ = load_dataset(root / DEV)
    assert dev_obs.n_obs == 3 * (len(ds["series"][0]["t_min"]) - 1)
    for ch in dev_obs.channels:
        assert ch.t.min() > 0
        src = next(s for s in ds["series"] if s["species"] == ch.name)
        assert src["reported_unit"] == "ug mL-1 as N" and "14.007" in src["conversion"]
    assert dev_obs.c0 == {"NO3": 99.95} and dev_obs.conditions.E_V == -0.6 and dev_obs.conditions.pH is None


def test_compiled_model_matches_reference_simulator(root):
    for p in sorted((root / "worlds").glob("W*.json")):
        w = json.loads(p.read_text())
        m = copy.deepcopy(w["ground_truth"])
        for rxn in m["reactions"]:  # declared fit bounds do not affect simulation (W5's exceed the protocol's)
            rl = rxn["rate_law"]
            for prm in [*rl["params"].values(), *(rl.get("time_modulation") or {}).values(),
                        *(rl.get("potential_dependence") or {}).values()]:
                if isinstance(prm, dict):
                    prm.pop("bounds", None)
        E = w["design_space"]["potential_V_vs_RHE"][0]
        c = compile_mechanism(m, Conditions(E_V=E, pH=7.0, T_C=25.0, n_potentials=2, n_pH=2))
        theta = []
        for fp in c.free:
            j, slot, _ = fp.members[0]
            rl = m["reactions"][j]["rate_law"]
            prm = {"k": rl["params"].get("k"), "tau_min": (rl.get("time_modulation") or {}).get("tau_min"),
                   "alpha": (rl.get("potential_dependence") or {}).get("alpha")}[slot]
            theta.append(fp.to_t(prm["value"]))
        t = np.array(w["observation"]["sampling_times_min"], float)
        y = c.simulate(theta, t, {"NO3": 100.0})
        ref = simulate(m, {"NO3": 100.0}, t, E_V=E, pH=7.0)
        for i, s in enumerate(c.species):
            assert np.allclose(y[i], ref[s], rtol=1e-6, atol=1e-8), (p.name, s)


def test_run_never_modifies_raw_inputs_and_records_hashes(root, config, tmp_path):
    before = {p: sha256_file(root / p) for p in (DEV, HOLD)}
    run = inv.init_run(config, "propose_only", "r1", tmp_path / "nw")
    m = run.manifest()
    assert {d["dataset_id"]: d["sha256"] for d in m["datasets"]} == {
        "liao2025_mos2_suppfig50b": before[DEV], "liao2025_wmos2_suppfig50a": before[HOLD]}
    assert m["datasets"][0]["measurement"].startswith("measured")
    assert any(f["field"] == "quality.n_closure" and f["kind"] == "derived" for f in m["datasets"][0]["derived_fields"])
    inv.submit(run, [cand("a")], {"source": "agent", "round": 1})
    inv.evaluate(run, workers=1)
    assert {p: sha256_file(root / p) for p in (DEV, HOLD)} == before


# ------------------------------------------------------------------ candidate identity
def test_canonical_identity_is_invariant_to_labels_order_and_start_values(dev_obs, protocol):
    a = cand("a")
    b = copy.deepcopy(a)
    b["name"] = "b"
    b["mechanism"]["reactions"] = list(reversed(b["mechanism"]["reactions"]))
    for i, r in enumerate(b["mechanism"]["reactions"]):
        r["id"] = f"Q{i}"
        r["rate_law"]["params"]["k"]["value"] = 0.5
        r["rate_law"]["time_modulation"]["tau_min"]["tie"] = "other_name"
    b["mechanism"]["species"][3] = _sp("N2gas", 0, observable=False, role="sink")
    for r in b["mechanism"]["reactions"]:
        for t in r["products"]:
            if t["species"] == "SINK":
                t["species"] = "N2gas"
    va, vb = validate_submission(a, dev_obs, protocol), validate_submission(b, dev_obs, protocol)
    assert va["status"] == vb["status"] == "valid"
    assert va["dynamics_hash"] == vb["dynamics_hash"] and va["chem_hash"] == vb["chem_hash"]


def test_different_kinetic_laws_are_not_collapsed(dev_obs, protocol):
    a = cand("a")
    b = copy.deepcopy(a)
    b["mechanism"]["reactions"][0] = _rx("R1", "NO3", "NO2", 2, family="langmuir_saturation")
    c = copy.deepcopy(a)
    for r in c["mechanism"]["reactions"]:
        r["rate_law"]["time_modulation"]["tau_min"].pop("tie")  # four independent taus, not one shared
    h = {validate_submission(x, dev_obs, protocol)["dynamics_hash"] for x in (a, b, c)}
    assert len(h) == 3


def test_observationally_equivalent_chemistry_shares_dynamics_not_chemistry(dev_obs, protocol):
    a = cand("n2_sink")
    b = copy.deepcopy(a)  # nitrate crossover into the anolyte instead of reduction to N2: electrons 0, N(+5)
    b["mechanism"]["species"][3] = _sp("NO3_anolyte", 5, observable=False, role="sink")
    b["mechanism"]["reactions"][3] = _rx("R4", "NO3", "NO3_anolyte", 0, mod=None)
    a["mechanism"]["reactions"][3] = _rx("R4", "NO3", "SINK", 5, mod=None)
    va, vb = validate_submission(a, dev_obs, protocol), validate_submission(b, dev_obs, protocol)
    assert va["dynamics_hash"] == vb["dynamics_hash"] and va["chem_hash"] != vb["chem_hash"]


def test_candidate_round_trip_through_store(config, tmp_path):
    run = inv.init_run(config, "manual", "rt", tmp_path / "nw")
    sub = cand("rt", support=[{"target": "R1", "basis": "literature", "source": "doi:x Fig. 1"}], assumptions=["a"],
               predictions=["p"])
    res = inv.submit(run, [sub], {"source": "human"})
    stored = run.candidate(res[0]["candidate_id"])
    assert stored["submission"] == sub and stored["version"] == 1 and stored["parent_id"] is None
    again = inv.submit(run, [copy.deepcopy(sub)], {"source": "agent"})
    assert again[0]["duplicate_of"] == res[0]["candidate_id"] and len(run.candidates()) == 1


# ------------------------------------------------------------------ explicit statuses
@pytest.mark.parametrize("mutate,status", [
    (lambda c: c["mechanism"]["reactions"][0]["products"][0].update(coeff=2), "invalid_chemistry"),
    (lambda c: c["mechanism"]["reactions"][0].update(electrons=3), "invalid_chemistry"),
    (lambda c: c["mechanism"]["reactions"][0].update(reversible=True), "unsupported_representation"),
    (lambda c: c["mechanism"]["reactions"][0]["rate_law"].update(
        potential_dependence={"alpha": {"value": 0.5}, "E_ref_V": -0.6}), "insufficient_data"),
    (lambda c: c["mechanism"]["reactions"][0]["rate_law"].update(
        ph_dependence={"order": {"value": 0.5, "fixed": True}, "pH_ref": 7}), "insufficient_data"),
    (lambda c: c["mechanism"]["reactions"][0]["products"][0].update(species="NOPE"), "invalid_submission"),
    (lambda c: c["mechanism"]["reactions"][0]["rate_law"]["params"]["k"].update(bounds=[1e-12, 1e3]), "invalid_submission"),
    (lambda c: c["mechanism"]["reactions"][1]["rate_law"].update(
        time_modulation={"kind": "deactivation", "tau_min": {"value": 300, "tie": "tau_cat", "bounds": [2, 10]}}),
     "invalid_submission"),
    (lambda c: c["mechanism"].pop("species"), "invalid_submission"),
    (lambda c: c["mechanism"].update(species=[s for s in c["mechanism"]["species"] if s["id"] != "NO2"],
                                     reactions=[_rx("R1", "NO3", "NH3", 8)]), "incompatible_observation"),
    (lambda c: c["mechanism"]["species"][0].update(observable=False), "invalid_submission"),
])
def test_explicit_statuses_instead_of_coercion(dev_obs, protocol, mutate, status):
    c = cand("s")
    mutate(c)
    assert validate_submission(c, dev_obs, protocol)["status"] == status


def test_fixed_alpha_at_single_potential_is_allowed(dev_obs, protocol):
    c = cand("fa")
    c["mechanism"]["reactions"][0]["rate_law"]["potential_dependence"] = {"alpha": {"value": 0.5, "fixed": True}, "E_ref_V": -0.6}
    assert validate_submission(c, dev_obs, protocol)["status"] == "valid"


def test_potential_dependence_on_chemical_step_is_invalid(dev_obs, protocol):
    c = cand("chem")
    c["mechanism"]["species"][3] = _sp("NO3_anolyte", 5, observable=False, role="sink")
    c["mechanism"]["reactions"][3] = _rx("R4", "NO3", "NO3_anolyte", 0, mod=None)
    c["mechanism"]["reactions"][3]["rate_law"]["potential_dependence"] = {"alpha": {"value": 0.5, "fixed": True}, "E_ref_V": -0.6}
    assert validate_submission(c, dev_obs, protocol)["status"] == "invalid_chemistry"


def test_numerical_failures_are_statuses_not_chemistry(dev_obs, protocol, monkeypatch):
    c = cand("num")
    v = validate_submission(c, dev_obs, protocol)
    p = copy.deepcopy(protocol)
    p["optimizer"].update(max_nfev=1, max_outer=1, n_starts=2)
    assert run_fit(c, v, dev_obs, p)["status"] == "nonconvergence"
    from nernstwork import model

    def boom(*a, **k):
        raise model.SolverFailure("forced")

    monkeypatch.setattr(model.Compiled, "simulate", boom)
    assert run_fit(c, v, dev_obs, protocol)["status"] == "solver_failure"


# ------------------------------------------------------------------ equal treatment, reproducibility, caching
def test_enumerator_and_agent_candidates_get_identical_evaluations(config, tmp_path):
    run = inv.init_run(config, "manual", "eq", tmp_path / "nw")
    from nernstwork.enumerate import enumerate_space

    space = json.loads((inv.REPO / "configs/spaces/liao_core.json").read_text())
    enum = next(s for s in enumerate_space(space) if "NO3>NH3,NO3>NO2,NO3>SINK" in s["rationale"] and "deactivation" in s["rationale"]
                and "NO2>NH3" in s["rationale"] and "NO2>SINK" not in s["rationale"])
    agent = copy.deepcopy(enum)
    agent["name"] = "agent_version"
    agent["mechanism"]["reactions"] = list(reversed(agent["mechanism"]["reactions"]))
    for r in agent["mechanism"]["reactions"]:
        r["rate_law"]["params"]["k"]["value"] = 0.07
    r1 = inv.submit(run, [enum], {"source": "enumerator"})
    r2 = inv.submit(run, [agent], {"source": "agent"})
    assert r2[0]["duplicate_of"] == r1[0]["candidate_id"]
    # evaluated through the same path, the fit key ignores who proposed it and with which starting values
    obs = inv._dev_obs(run)
    pr = run.protocol()
    va = validate_submission(enum, obs, pr)
    vb = validate_submission(agent, obs, pr)
    from nernstwork.evaluate import code_identity

    code = code_identity()["sha256"]
    assert fit_key(va["dynamics_hash"], obs.sha256, pr, code) == fit_key(vb["dynamics_hash"], obs.sha256, pr, code)


def test_fit_is_reproducible_and_keys_change_with_protocol_code_and_data(dev_obs, protocol, root):
    c = cand("rep")
    v = validate_submission(c, dev_obs, protocol)
    a, b = run_fit(c, v, dev_obs, protocol), run_fit(c, v, dev_obs, protocol)
    assert a["nll"] == pytest.approx(b["nll"], abs=1e-9) and np.allclose(a["theta"], b["theta"], atol=1e-9)
    p2 = copy.deepcopy(protocol)
    p2["noise"]["rel_floor"] = 0.02
    k = fit_key(v["dynamics_hash"], dev_obs.sha256, protocol, "code")
    assert k != fit_key(v["dynamics_hash"], dev_obs.sha256, p2, "code")
    assert k != fit_key(v["dynamics_hash"], dev_obs.sha256, protocol, "code2")
    _ds, sha = load_dataset(root / HOLD)
    assert k != fit_key(v["dynamics_hash"], sha, protocol, "code")
    assert protocol_hash(protocol) != protocol_hash(p2)


def test_legacy_objective_reproduces_earlier_calibration(root, dev_obs):
    p = json.loads((root / "configs/protocols/legacy-scaled-v1.json").read_text())
    c = cand("w2")
    v = validate_submission(c, dev_obs, p)
    r = run_fit(c, v, dev_obs, p)
    k = dict(zip(r["free_parameter_names"], [10 ** x for x in r["theta"]]))
    # docs/SPEC.md section 7 / scripts/calibrate_liao.py: k1=4.0e-4 k2=2.7e-3 k3=3.7e-3 kl=1.5e-3 tau=368, sink 23.2
    assert k["R1.k"] == pytest.approx(4.0e-4, rel=0.03) and k["R2.k"] == pytest.approx(2.7e-3, rel=0.03)
    assert k["R3.k"] == pytest.approx(3.7e-3, rel=0.03) and k["R4.k"] == pytest.approx(1.5e-3, rel=0.03)
    assert k["tie:tau_cat"] == pytest.approx(368, rel=0.03)
    assert r["trajectory"]["species"]["SINK"][-1] == pytest.approx(23.2, abs=0.3)


def test_changed_dataset_bytes_are_refused(config, tmp_path, root):
    cfg = json.loads(config.read_text())
    dev_copy = tmp_path / "dev.json"
    dev_copy.write_bytes((root / DEV).read_bytes())
    cfg["datasets"]["development"] = [str(dev_copy)]
    p = tmp_path / "cfg2.json"
    p.write_text(json.dumps(cfg))
    run = inv.init_run(p, "manual", "chg", tmp_path / "nw")
    dev_copy.write_text(dev_copy.read_text().replace("99.95", "99.96", 1))
    with pytest.raises(inv.InvestigationError, match="changed since the run was created"):
        inv.submit(run, [cand("x")], {"source": "human"})


# ------------------------------------------------------------------ reviews and revisions
def test_review_must_cite_resolvable_artifacts_and_correct_numbers(config, tmp_path):
    run = inv.init_run(config, "critique_revise", "rv", tmp_path / "nw")
    cid = inv.submit(run, [cand("a")], {"source": "agent", "round": 1})[0]["candidate_id"]
    inv.evaluate(run, workers=1)
    b = inv.review_bundle(run)
    bundle = inv.load_bundle(run, b["bundle_id"])
    aicc = bundle["artifacts"][f"evaluation:{cid}"]["summary"]["aicc"]
    good = {"summary": "s", "findings": [{"id": "F1", "severity": "major", "category": "statistics", "claim": "c",
                                          "targets": [f"candidate:{cid}#/submission/mechanism/reactions/3"],
                                          "evidence": [{"ref": f"evaluation:{cid}#/summary/aicc", "value": aicc}],
                                          "check": {"type": "numerical", "description": "d"},
                                          "action": {"type": "additional_analysis", "description": "d"}}],
            "assessment": {"plausible_candidates": [cid], "not_supported": [], "ambiguities": [], "adequate_candidate_exists": "uncertain"}}
    assert validate_review(good, bundle) == []
    bad = copy.deepcopy(good)
    bad["findings"][0]["evidence"][0]["value"] = aicc + 5
    bad["findings"][0]["targets"] = ["candidate:Cnope#/x"]
    errs = validate_review(bad, bundle)
    assert any("quoted" in e for e in errs) and any("unknown artifact" in e for e in errs)
    assert inv.record_review(run, b["bundle_id"], bad, {})["accepted"] is False
    rid = inv.record_review(run, b["bundle_id"], good, {"model": "test"})["review_id"]
    # revision keeps the original and links the new version
    rev = cand("a_v2", reactions=[_rx("R1", "NO3", "NO2", 2), _rx("R2", "NO2", "NH3", 6), _rx("R3", "NO3", "NH3", 8),
                                   _rx("R4", "NO2", "SINK", 3)], parent=cid)
    r = inv.submit(run, [rev], {"source": "reviewer_revision", "round": 2})[0]
    assert r["version"] == 2 and r["parent_id"] == cid and run.candidate_path(cid).exists()
    assert inv.record_response(run, rid, {"responses": []})["accepted"] is False
    ok = inv.record_response(run, rid, {"responses": [{"finding_id": "F1", "action": "revised", "candidate_ids": [r["candidate_id"]], "note": "n"}]})
    assert ok["accepted"]
    # bundle is content-addressed and frozen: rebuilding with the same content gives the same id
    assert inv.review_bundle(run, [cid])["bundle_id"] == inv.review_bundle(run, [cid])["bundle_id"]


def test_conclusion_allows_ambiguity_and_rejects_unknown_ids(config, tmp_path):
    run = inv.init_run(config, "propose_only", "cc", tmp_path / "nw")
    cid = inv.submit(run, [cand("a")], {"source": "agent"})[0]["candidate_id"]
    ok = inv.conclude(run, {"plausible": [cid], "rejected": [], "ambiguities": ["sink placement"], "adequacy": "none_adequate",
                            "recommended_experiments": [], "narrative": "n"})
    assert ok["accepted"]
    assert not inv.conclude(run, {"plausible": ["Cxxx"], "rejected": [], "ambiguities": [], "adequacy": "uncertain",
                                  "narrative": "n"})["accepted"]


def test_budget_is_enforced_and_recorded(config, tmp_path):
    run = inv.init_run(config, "propose_only", "bud", tmp_path / "nw")
    subs = [cand("a"), cand("b", reactions=[_rx("R1", "NO3", "NO2", 2), _rx("R2", "NO2", "NH3", 6)]),
            cand("c", reactions=[_rx("R1", "NO3", "NO2", 2), _rx("R2", "NO2", "NH3", 6), _rx("R3", "NO2", "SINK", 3)]),
            cand("d", reactions=[_rx("R1", "NO3", "NO2", 2), _rx("R2", "NO3", "NH3", 8)])]
    res = inv.submit(run, subs, {"source": "agent", "round": 1})
    assert [r["status"] for r in res][-1] == "budget_exhausted"
    assert len(list((run.dir / "submissions").glob("*.json"))) == 4


# ------------------------------------------------------------------ recovery
def _cli(root, nwroot, *args, env=None, stdin=""):
    e = dict(os.environ, PYTHONPATH=str(root / "src"), NW_ROOT=str(nwroot), **(env or {}))
    return subprocess.run([sys.executable, "-m", "nernstwork.cli", *args], input=stdin, capture_output=True, text=True, env=e, cwd=root, check=False)


def test_interrupted_attempts_are_reconciled_without_duplicate_results(root, config, tmp_path):
    nw = tmp_path / "nw"
    run = inv.init_run(config, "manual", "crash", nw)
    cid = inv.submit(run, [cand("a")], {"source": "human"})[0]["candidate_id"]
    # 1) worker dies after fitting, before committing: no result, attempt left 'running' with a dead pid
    r = _cli(root, nw, "evaluate", "--run", "crash", "--workers", "1", env={"NW_FAULT": "crash_before_commit"})
    assert r.returncode != 0
    fdirs = list((nw / "cache" / "fits").glob("*"))
    assert len(fdirs) == 1 and not (fdirs[0] / "result.json").exists()
    st = inv.status(run)
    assert len(st["reconciled_attempts"]["abandoned"]) == 1
    # 2) worker dies right after committing the result, before the run's evaluation record is written
    r = _cli(root, nw, "evaluate", "--run", "crash", "--workers", "1", env={"NW_FAULT": "crash_after_commit"})
    assert r.returncode != 0 and (fdirs[0] / "result.json").exists() and not run.evaluations()
    # 3) resume: the committed result is reused, the record is written once, nothing is refit
    out = json.loads(_cli(root, nw, "evaluate", "--run", "crash").stdout)["result"]
    assert out["n_fits_run"] == 0 and out["summaries"][0]["status"] == "fitted"
    states = sorted(json.loads(p.read_text())["state"] for p in (fdirs[0] / "attempts").glob("*.json"))
    assert states == ["abandoned", "committed"]
    assert len(run.evaluations()) == 1 and run.evaluations()[0]["candidate_id"] == cid
    # a second, independent commit of the same key is refused and checked for reproducibility
    body = json.loads((fdirs[0] / "result.json").read_text())
    aid = run.cache.begin_attempt(fdirs[0].name, {})
    c = run.cache.commit(fdirs[0].name, aid, body["result"])
    assert c["committed"] is False and c["reproduced"] is True


def test_create_once_never_overwrites(tmp_path):
    p = tmp_path / "x.json"
    assert create_once_json(p, {"a": 1}) and not create_once_json(p, {"a": 2})
    assert json.loads(p.read_text()) == {"a": 1}


# ------------------------------------------------------------------ development vs final evaluation
def test_evidence_pack_contains_no_holdout_data(config, tmp_path, root):
    run = inv.init_run(config, "propose_only", "ho", tmp_path / "nw")
    ev = run.dir / "evidence"
    hold, _ = load_dataset(root / HOLD)
    marks = [hold["id"], "11.4743", "51.6296", "4.64 mM and 11.78 mM"]
    for p in ev.rglob("*"):
        if p.is_file() and p.suffix in (".json", ".md", ".py"):
            txt = p.read_text()
            for m in marks:
                assert m not in txt, (p.name, m)
    assert sorted(x.name for x in (ev / "datasets").iterdir()) == ["liao2025_mos2_suppfig50b.json"]


def test_final_evaluation_only_after_freeze_and_freeze_closes_submissions(config, tmp_path):
    run = inv.init_run(config, "propose_only", "fz", tmp_path / "nw")
    inv.submit(run, [cand("a")], {"source": "agent"})
    inv.evaluate(run, workers=1)
    with pytest.raises(inv.InvestigationError, match="frozen"):
        inv.final_evaluate(run)
    fz = inv.freeze(run)
    assert fz["selected_by_rule"] and run.state()["phase"] == "frozen"
    with pytest.raises(inv.InvestigationError, match="no new candidates after freeze"):
        inv.submit(run, [cand("b")], {"source": "agent"})
    events = [e["type"] for e in run.events()]
    assert events.index("frozen") > events.index("evaluation_recorded")


# ------------------------------------------------------------------ regressions from the code review
def _equivalent_pair():
    """Same dynamics, different chemistry, different reaction order and unobserved-species names."""
    a = cand("n2_sink", reactions=[_rx("R1", "NO3", "NO2", 2), _rx("R2", "NO2", "NH3", 6), _rx("R3", "NO3", "NH3", 8),
                                   _rx("R4", "NO3", "SINK", 5)])
    b = cand("crossover", species=[_sp("NO3", 5), _sp("NO2", 3), _sp("NH3", -3), _sp("NO3_anolyte", 5, observable=False, role="sink")],
             reactions=[_rx("Z1", "NO3", "NO3_anolyte", 0, tie="t"), _rx("Z2", "NO3", "NH3", 8, tie="t"),
                        _rx("Z3", "NO2", "NH3", 6, tie="t"), _rx("Z4", "NO3", "NO2", 2, tie="t")])
    return a, b


def test_shared_fit_is_read_in_each_candidates_own_names(config, tmp_path):
    run = inv.init_run(config, "manual", "share", tmp_path / "nw")
    a, b = _equivalent_pair()
    ra, rb = inv.submit(run, [a, b], {"source": "human"})
    assert rb.get("observationally_equivalent_to") == [ra["candidate_id"]]
    out = inv.evaluate(run, workers=1)
    assert out["n_fits_run"] == 1  # one fit serves both
    s = {x["candidate_id"]: x for x in inv.summaries(run)}
    pa, pb = s[ra["candidate_id"]]["params"], s[rb["candidate_id"]]["params"]
    pairs = {("NO3", "NO2"): ("R1.k", "Z4.k"), ("NO2", "NH3"): ("R2.k", "Z3.k"), ("NO3", "NH3"): ("R3.k", "Z2.k"),
             ("NO3", "sink"): ("R4.k", "Z1.k")}
    for ka, kb in pairs.values():
        assert pa[ka]["value"] == pytest.approx(pb[kb]["value"], rel=1e-9), (ka, kb)
    assert pa["tie:tau_cat"]["value"] == pytest.approx(pb["tie:t"]["value"], rel=1e-9)
    assert s[ra["candidate_id"]]["unobserved_N_end_mM"] == pytest.approx(s[rb["candidate_id"]]["unobserved_N_end_mM"])
    # a profile computed for one is read correctly by the other
    inv.profile(run, [ra["candidate_id"]])
    pb_view = inv.fit_view(run, rb["candidate_id"])[4]["params"]
    pa_view = inv.fit_view(run, ra["candidate_id"])[4]["params"]
    for ka, kb in pairs.values():
        assert pa_view[ka]["ci95"] == pytest.approx(pb_view[kb]["ci95"])
    d = inv.discriminate(run, [ra["candidate_id"], rb["candidate_id"]], [{"name": "nitrite_feed", "c0_mM_N": {"NO2": 100.0}}])
    assert all(r["max_spread_mM_N"] < 1e-6 for r in d["designs"][0]["comparisons"])  # identical dynamics, identical predictions
    rk = inv.compare(run)["ranking"]["groups"][0]["rows"]
    assert {r["equivalent_to"] for r in rk} == {None, ra["candidate_id"]} and rk[0]["weight"] == pytest.approx(1.0)


def test_candidate_without_free_parameters_is_evaluated(config, tmp_path):
    run = inv.init_run(config, "manual", "nofree", tmp_path / "nw")
    c = cand("fixed", reactions=[_rx("R1", "NO3", "NO2", 2, mod=None), _rx("R2", "NO2", "NH3", 6, mod=None)])
    for r, k in zip(c["mechanism"]["reactions"], (5e-3, 2e-2)):
        r["rate_law"]["params"]["k"] = {"value": k, "fixed": True}
    inv.submit(run, [c], {"source": "human"})
    out = inv.evaluate(run, workers=1)
    assert out["summaries"][0]["status"] == "fitted" and out["summaries"][0]["k_kinetic"] == 0


def test_canonical_identity_normalizes_numbers_and_explicit_defaults(dev_obs, protocol):
    a = cand("a")
    b = copy.deepcopy(a)
    a["mechanism"]["reactions"][0]["rate_law"]["params"]["k"]["bounds"] = [1e-6, 1]
    b["mechanism"]["reactions"][0]["rate_law"]["params"]["k"].update(bounds=[1e-6, 1.0], fixed=False)
    va, vb = validate_submission(a, dev_obs, protocol), validate_submission(b, dev_obs, protocol)
    assert va["chem_hash"] == vb["chem_hash"]


@pytest.mark.parametrize("fixed_first", [True, False])
def test_tie_mixing_fixed_and_free_is_rejected_in_any_order(dev_obs, protocol, fixed_first):
    c = cand("tie")
    taus = [r["rate_law"]["time_modulation"]["tau_min"] for r in c["mechanism"]["reactions"]]
    (taus[0] if fixed_first else taus[-1]).update(fixed=True)
    v = validate_submission(c, dev_obs, protocol)
    assert v["status"] == "invalid_submission" and "mixes fixed and free" in " ".join(v["errors"])


def test_unused_parameters_and_start_value_dependence_are_rejected(dev_obs, protocol):
    c = cand("k_on_mass_action")
    c["mechanism"]["reactions"][0]["rate_law"]["params"]["K"] = {"value": 10.0}
    assert validate_submission(c, dev_obs, protocol)["status"] == "invalid_submission"
    p1, p2 = cand("pl1"), cand("pl2")
    for c, start in ((p1, 1.0), (p2, 2.0)):
        r = c["mechanism"]["reactions"][0]
        r["rate_law"].update(family="power_law", orders={"NO3": {"value": start, "bounds": [0.0, 3.0]}})
    v1, v2 = validate_submission(p1, dev_obs, protocol), validate_submission(p2, dev_obs, protocol)
    assert v1["dynamics_hash"] == v2["dynamics_hash"]  # start value of a free order does not change the hypothesis


def test_freeze_requires_current_evaluations_and_repairs_interrupted_freeze(config, tmp_path):
    run = inv.init_run(config, "propose_only", "fz2", tmp_path / "nw")
    inv.submit(run, [cand("a")], {"source": "agent"})
    with pytest.raises(inv.InvestigationError, match="cannot freeze"):
        inv.freeze(run)
    inv.evaluate(run, workers=1)
    inv.freeze(run)
    run.set_state(phase="development")  # simulate a crash between frozen.json and the phase change
    inv.freeze(run)
    assert run.state()["phase"] == "frozen"


def test_profile_stops_on_unconverged_refits_instead_of_reporting_a_narrow_interval(dev_obs, protocol, monkeypatch):
    from nernstwork import fit as fitmod

    c = cand("pr")
    v = validate_submission(c, dev_obs, protocol)
    res = run_fit(c, v, dev_obs, protocol)
    real = fitmod._solve

    def flaky(prob, x0, lo, hi, opt, fixed=None):
        r = real(prob, x0, lo, hi, opt, fixed)
        if fixed:
            r = dict(r, converged=False)
        return r

    monkeypatch.setattr(fitmod, "_solve", flaky)
    from nernstwork.evaluate import run_profiles

    pr = run_profiles(c, v, dev_obs, protocol, res)
    assert {d["classification"] for d in pr["params"].values()} == {"inconclusive_numerics"}
    json.dumps(pr, allow_nan=False)


def test_compute_budgets_end_pathological_fits_with_explicit_status(dev_obs, protocol):
    c = cand("budget")
    v = validate_submission(c, dev_obs, protocol)
    p = copy.deepcopy(protocol)
    p["ode"]["max_rhs_evals"] = 20  # every solve exceeds this: all starts fail numerically
    r = run_fit(c, v, dev_obs, p)
    assert r["status"] == "solver_failure" and r["timing"]["n_ode_failures"] == r["timing"]["n_ode_solves"]
    p = copy.deepcopy(protocol)
    p["optimizer"]["max_ode_solves_per_fit"] = 50  # budget runs out during the first start
    r = run_fit(c, v, dev_obs, p)
    assert r["status"] == "nonconvergence" and r["multistart"]["budget_exhausted"] is True
    assert "not evidence against the chemistry" in r["multistart"]["note"]


def test_nonfinite_values_are_stored_explicitly(tmp_path):
    p = tmp_path / "x.json"
    assert create_once_json(p, {"cond": float("inf"), "v": [1.0, float("nan")]})
    assert json.loads(p.read_text()) == {"cond": "inf", "v": [1.0, "nan"]}


def test_replicated_unconverged_optimum_is_reported_not_a_worse_converged_one(dev_obs, protocol, monkeypatch):
    from nernstwork import fit as fitmod
    from nernstwork.fit import Problem, multistart

    c = cand("rep")
    v = validate_submission(c, dev_obs, protocol)
    prob = Problem(compile_mechanism(c["mechanism"], dev_obs.conditions, protocol["bounds"]), dev_obs, v["observation_map"], protocol)

    def scripted(seq):
        it = iter(seq)

        def fake(prob, x0, lo, hi, opt, fixed=None):
            nll, conv = next(it)
            return {"x": np.array(x0), "nll": nll, "converged": conv, "sigma": np.ones(3), "nfev": 1, "solver_failed": False}
        return fake

    p = copy.deepcopy(protocol)
    p["optimizer"]["n_starts"] = 6
    monkeypatch.setattr(fitmod, "_solve", scripted([(150.0, True), (85.0, False), (85.0, False), (85.0, False), (160.0, True), (150.0, True)]))
    ms = multistart(prob, p, seed=1)
    assert ms["status"] == "fitted" and ms["best"]["nll"] == 85.0
    assert ms["summary"]["replicates"] == 3 and ms["summary"]["formally_converged"] is False
    monkeypatch.setattr(fitmod, "_solve", scripted([(150.0, True), (85.0, False), (150.0, True), (160.0, True), (170.0, True), (150.0, True)]))
    ms = multistart(prob, p, seed=1)
    assert ms["best"]["nll"] == 150.0 and "without replication" in ms["summary"]["warning"]


def test_sandbox_toolkit_checks_simulates_and_fits_exploratorily(config, tmp_path):
    run = inv.init_run(config, "manual", "tk", tmp_path / "nw")
    tk = run.dir / "toolkit"
    assert (tk / "nwlab.py").exists() and not (tk / "nernstwork" / "store.py").exists()
    code = (
        "import json, nwlab\n"
        "c = json.load(open('cand.json'))\n"
        "ck = nwlab.check(c); y = nwlab.simulate(c); r = nwlab.quick_fit(c, n_starts=2)\n"
        "print(json.dumps({'check': ck['status'], 'ny': len(y['NO3']), 'status': r['status'], 'label': r['label'],"
        " 'aicc': r.get('aicc_exploratory')}))\n")
    (tmp_path / "cand.json").write_text(json.dumps(cand("tk")))
    env = {"PATH": os.environ["PATH"], "PYTHONPATH": str(tk), "NW_EVIDENCE": str(run.dir / "evidence")}
    out = subprocess.run([sys.executable, "-c", code], cwd=tmp_path, env=env, capture_output=True, text=True, timeout=600, check=False)
    assert out.returncode == 0, out.stderr[-2000:]
    d = json.loads(out.stdout.strip().splitlines()[-1])
    assert d["check"] == "valid" and d["ny"] == 200 and d["status"] == "fitted" and "EXPLORATORY" in d["label"]
    assert d["aicc"] > 0
