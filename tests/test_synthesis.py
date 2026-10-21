"""Synthesis domain: element balance, Arrhenius and Avrami rate laws, joint multi-temperature fits, hypothesis spaces,
the experiment planner and parameter-transfer held-out evaluation."""
import copy
import json
import math

import numpy as np
import pytest

from nernstwork import investigation as inv
from nernstwork.data import joint_observation_set, observation_set
from nernstwork.enumerate import enumerate_space, validate_synthesis_space
from nernstwork.evaluate import run_fit, validate_submission
from nernstwork.mechanism import R
from nernstwork.mechanism import simulate as ref_simulate
from nernstwork.model import INSUFFICIENT_DATA, INVALID_CHEMISTRY, INVALID_SUBMISSION, CompileError, Conditions, compile_mechanism

GRID = [0.3, 0.5, 0.8, 1.2, 2.0, 3.0, 4.5, 6.0, 8.0, 10.0]
TRUE = {"k1": 0.6, "Ea1": 200.0, "k2": 0.25, "Ea2": 260.0, "n2": 1.6, "T_ref": 712.5}


def _p(v, fixed=True):
    return {"value": v, "fixed": True} if fixed else {"value": v}


def _mech(fixed=True, avrami=True, Ea2=True):
    """X -> Y (first order, Arrhenius), Y -> Z (Avrami, Arrhenius); Ti conserved."""
    rl2 = {"family": "power_law", "params": {"k": _p(TRUE["k2"], fixed)}, "orders": {"Y": {"value": 1.0, "fixed": True}}}
    if Ea2:
        rl2["temperature_dependence"] = {"Ea_kJ_mol": _p(TRUE["Ea2"], fixed), "T_ref_C": TRUE["T_ref"]}
    if avrami:
        rl2["time_modulation"] = {"kind": "avrami", "n": _p(TRUE["n2"], fixed)}
    return {"id": "xyz", "conservation": {"basis": "elements", "elements": ["Ti"]},
            "species": [{"id": "X", "composition": {"Ti": 1}}, {"id": "Y", "composition": {"Ti": 1}},
                        {"id": "Z", "composition": {"Ti": 1}}],
            "reactions": [
                {"id": "R1", "reactants": [{"species": "X", "coeff": 1}], "products": [{"species": "Y", "coeff": 1}],
                 "rate_law": {"family": "power_law", "params": {"k": _p(TRUE["k1"], fixed)},
                              "orders": {"X": {"value": 1.0, "fixed": True}},
                              "temperature_dependence": {"Ea_kJ_mol": _p(TRUE["Ea1"], fixed), "T_ref_C": TRUE["T_ref"]}}},
                {"id": "R2", "reactants": [{"species": "Y", "coeff": 1}], "products": [{"species": "Z", "coeff": 1}],
                 "rate_law": rl2}]}


def _dataset(T, noise=0.004, seed=0):
    m = _mech()
    comp = compile_mechanism(m, Conditions(E_V=None, pH=None, T_C=T, n_temperatures=2))
    t = np.array([0.0] + GRID)
    Y = comp.simulate(np.zeros(0), t, {"X": 1.0}, conditions=Conditions(E_V=None, pH=None, T_C=T))
    rng = np.random.default_rng(seed + int(T))
    series = [{"species": s, "t_min": GRID, "y": [round(float(v + noise * rng.standard_normal()), 6) for v in Y[i][1:]],
               "reported_unit": "simulated"} for i, s in enumerate(["X", "Y", "Z"])]
    return {"id": f"synth_{T:g}C", "provenance": {"source_type": "simulated"},
            "conditions": {"basis": "mol per mol Ti", "c0": {"X": 1.0}, "temperature_C": T,
                           "potential_V_vs_RHE": None, "pH": None}, "series": series}


@pytest.fixture(scope="module")
def protocol(root):
    p = json.loads((root / "configs" / "protocols" / "synthesis-mle-v1.json").read_text())
    p["optimizer"]["n_starts"] = 6
    return p


def test_synthetic_dataset_validates(validator):
    errs = list(validator("dataset.schema.json").iter_errors(_dataset(700.0)))
    assert not errs, errs[0].message


def test_element_balance_replaces_the_n_rule():
    m = _mech()
    m["reactions"][0]["products"][0]["coeff"] = 2  # Ti 1 -> 2
    with pytest.raises(CompileError) as e:
        compile_mechanism(m, Conditions(None, None, 700.0, n_temperatures=2))
    assert e.value.status == INVALID_CHEMISTRY and "Ti not conserved" in e.value.messages[0]
    m = _mech()
    del m["species"][1]["composition"]
    with pytest.raises(CompileError) as e:
        compile_mechanism(m, Conditions(None, None, 700.0, n_temperatures=2))
    assert e.value.status == INVALID_SUBMISSION


def test_avrami_single_step_is_jmak_and_matches_reference_simulator():
    m = _mech()
    m["reactions"] = [m["reactions"][1]]
    m["reactions"][0]["reactants"][0]["species"] = "X"
    m["reactions"][0]["rate_law"]["orders"] = {"X": {"value": 1.0, "fixed": True}}
    t = np.linspace(0, 10, 41)
    T = 725.0
    cond = Conditions(None, None, T, n_temperatures=2)
    y = compile_mechanism(m, cond).simulate(np.zeros(0), t, {"X": 1.0}, conditions=cond)
    k = TRUE["k2"] * math.exp(-TRUE["Ea2"] * 1e3 / R * (1 / (T + 273.15) - 1 / (TRUE["T_ref"] + 273.15)))
    alpha = 1 - np.exp(-(k * t) ** TRUE["n2"])
    assert np.allclose(y[2], alpha, atol=2e-5)
    ref = ref_simulate(m, {"X": 1.0}, t, None, None, T)
    assert np.allclose(ref["Z"], y[2], atol=2e-5)


def test_free_activation_energy_needs_two_temperatures(protocol):
    single = observation_set(_dataset(700.0), "x")
    joint = joint_observation_set([(_dataset(700.0), "a"), (_dataset(725.0), "b")])
    sub = {"name": "free", "mechanism": _mech(fixed=False)}
    assert validate_submission(sub, single, protocol)["status"] == INSUFFICIENT_DATA
    assert validate_submission(sub, joint, protocol)["status"] == "valid"
    assert joint.conditions.n_temperatures == 2 and joint.channel_names() == ["X", "Y", "Z"]


def test_joint_fit_recovers_rate_constants_activation_energies_and_avrami_exponent(protocol):
    obs = joint_observation_set([(_dataset(700.0), "a"), (_dataset(725.0), "b")])
    sub = {"name": "free", "mechanism": _mech(fixed=False)}
    v = validate_submission(sub, obs, protocol)
    r = run_fit(sub, v, obs, protocol)
    assert r["status"] == "fitted"
    est = {p["name"]: p["value"] for p in r["uncertainty"]["params"]}
    assert est["R1.k"] == pytest.approx(TRUE["k1"], rel=0.05)
    assert est["R2.k"] == pytest.approx(TRUE["k2"], rel=0.05)
    assert est["R2.n_avrami"] == pytest.approx(TRUE["n2"], abs=0.1)
    assert est["R1.Ea"] == pytest.approx(TRUE["Ea1"], abs=60)
    assert est["R2.Ea"] == pytest.approx(TRUE["Ea2"], abs=60)
    assert set(r["sigma"]) == {"X", "Y", "Z"}  # one sigma per phase, shared across temperatures
    assert set(r["trajectories"]) == {"synth_700C", "synth_725C"}
    assert all(k.startswith("synth_7") for k in r["residuals"]["channels"])


def _space():
    return {"space_id": "xyz-space", "conservation": {"basis": "elements", "elements": ["Ti"]},
            "species": [{"id": "X", "composition": {"Ti": 1}}, {"id": "Y", "composition": {"Ti": 1}},
                        {"id": "Z", "composition": {"Ti": 1}}],
            "initial": ["X"],
            "steps": [{"id": "S1", "reactants": {"X": 1}, "products": {"Y": 1}},
                      {"id": "S2", "reactants": {"Y": 1}, "products": {"Z": 1}, "rate_laws": ["first_order", "avrami"],
                       "support": [{"basis": "data", "source": "synthetic: sigmoidal Z"}]},
                      {"id": "S3", "reactants": {"X": 1}, "products": {"Z": 1}}],
            "require": {"produced": ["Y", "Z"]},
            "temperature_dependence": {"Ea": "per_step", "T_ref_C": TRUE["T_ref"]}}


def test_synthesis_space_enumeration_and_plain_language_errors(root):
    members = enumerate_space(_space())
    # S1+S2 (two S2 forms), S1+S2+S3 (two S2 forms); S1+S3 never forms Z from Y but does produce Z, so it is allowed too
    assert len(members) == 5
    assert all(m["mechanism"]["conservation"]["elements"] == ["Ti"] for m in members)
    assert any(s["basis"] == "data" for m in members for s in m["support"])
    bad = copy.deepcopy(_space())
    bad["steps"][0]["products"] = {"Y": 2}
    del bad["temperature_dependence"]["T_ref_C"]
    errs = validate_synthesis_space(bad)
    assert any("Ti not conserved" in e for e in errs) and any("T_ref_C" in e for e in errs)
    capped = dict(_space(), max_members=2)
    with pytest.raises(ValueError, match="more than max_members"):
        enumerate_space(capped)
    core = json.loads((root / "configs" / "spaces" / "chapman_core.json").read_text())
    assert len(enumerate_space(core)) == 154


def test_propose_space_run_plans_and_predicts_held_out_temperature(root, tmp_path, protocol):
    paths = {}
    for T in (700.0, 725.0, 750.0):
        p = tmp_path / f"synth_{T:g}C.json"
        p.write_text(json.dumps(_dataset(T)))
        paths[T] = str(p)
    pp = tmp_path / "protocol.json"
    pp.write_text(json.dumps(protocol))
    ref = tmp_path / "ref_space.json"
    ref.write_text(json.dumps(dict(_space(), space_id="ref", steps=_space()["steps"][:2])))
    cfg = json.loads((root / "configs" / "investigations" / "chapman750.json").read_text())
    cfg.update(investigation_id="synth", protocol=str(pp), enumeration_spaces=[str(ref)],
               datasets={"development": [paths[700.0], paths[725.0]], "final_holdout": [paths[750.0]], "excluded": [],
                         "partition_policy": "synthetic"})
    cfg["evidence"]["documents"] = []
    cp = tmp_path / "cfg.json"
    cp.write_text(json.dumps(cfg))
    run = inv.init_run(cp, "propose_space", "ps", tmp_path / "nw")
    ev = run.dir / "evidence"
    assert sorted(f.name for f in (ev / "datasets").iterdir()) == ["synth_700C.json", "synth_725C.json"]
    assert "mol per mol Ti" in (ev / "evidence_summary.md").read_text()
    res = inv.submit_space(run, _space(), {"source": "agent_space"})
    assert res["accepted"] and res["n_members"] == 5
    assert inv.submit_space(run, {"space_id": "x"}, {})["accepted"] is False
    inv.evaluate(run, workers=2)
    ranking = inv.compare(run)["ranking"]["groups"][0]["rows"]
    best = ranking[0]["candidate_id"]
    assert run.candidate(best)["submission"]["rationale"].startswith("enumerated: S1:first_order,S2:avrami")
    from nernstwork.planner import plan
    others = [r["candidate_id"] for r in ranking if r["candidate_id"] != best]
    pl = plan(run, [{"name": "T650", "temperature_C": 650.0, "c0": {"X": 1.0}},
                    {"name": "T725_late_only", "temperature_C": 725.0, "c0": {"X": 1.0}, "t_sample_min": [8.0, 10.0]}],
              cids=[best, others[0]])
    assert pl["weights"].startswith("equal") and all(r["U"] >= 0 for r in pl["ranking"])
    assert pl["ranking"][0]["design"] == "T650"  # the late-only design carries less information
    inv.conclude(run, {"plausible": [best], "rejected": [], "ambiguities": [], "adequacy": "uncertain",
                       "recommended_experiments": [], "narrative": "test"})
    fz = inv.freeze(run)
    assert fz["top1"] == best
    out = inv.final_evaluate(run, workers=2)
    d = out["datasets"][0]
    assert d["mode"] == "predict" and d["dataset_id"] == "synth_750C"
    row = d["frozen_candidates"][0]
    assert row["rank_among_space"] == 1 and row["rmse_all"] < 0.02
    own = d["run_candidates"]
    assert own["n_scored"] == 5 and own["best_predicting"]["rank_among_space"] == 1
    from nernstwork.report import compare_arms, write_report
    rep = write_report(run, tmp_path / "report.md")
    text = (tmp_path / "report.md").read_text()
    assert "predicted without refitting" in text and "rank 1/2" in text and "Common noise scale" in text
    cmp = compare_arms([run], tmp_path / "arms.md")
    assert cmp["rows"][0]["heldout_top1"]["rank_among_space"] == 1
    assert "predict 750 C" in (tmp_path / "arms.md").read_text()
