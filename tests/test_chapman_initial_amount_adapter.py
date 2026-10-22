"""Initial-amount recovery and transfer checks on a synthetic Li-balanced reaction."""
import copy
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

from nernstwork.data import joint_observation_set, sha256_json
from nernstwork.model import Conditions, compile_mechanism

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("chapman_initial_amount_adapter", ROOT / "scripts/chapman_initial_amount_adapter.py")
adapter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(adapter)


def mechanism(free_rate=True):
    return {"id": "Li_balanced_synthetic", "conservation": {"basis": "elements", "elements": ["Ti", "Li"]},
            "species": [{"id": "anatase", "composition": {"Ti": 1}},
                        {"id": "Li2CO3", "composition": {"Li": 2}, "observable": False},
                        {"id": "Li2TiO3", "composition": {"Ti": 1, "Li": 2}}],
            "reactions": [{"id": "R1", "reactants": [{"species": "anatase", "coeff": 1},
                                                        {"species": "Li2CO3", "coeff": 1}],
                           "products": [{"species": "Li2TiO3", "coeff": 1}],
                           "rate_law": {"family": "power_law", "params": {"k": {"value": 2.0, "fixed": not free_rate}},
                                        "orders": {"anatase": {"value": 1.0, "fixed": True},
                                                   "Li2CO3": {"value": 1.0, "fixed": True}},
                                        "temperature_dependence": {"T_ref_C": 712.5,
                                                                   "Ea_kJ_mol": {"value": 120.0, "fixed": True}}}}]}


def dataset(T, initial):
    # Closed-form solution of A+L->P, rather than the adapter itself, supplies truth.
    t = np.array([0.2, 0.4, 0.7, 1.0, 1.5, 2.0, 3.0, 5.0, 7.0, 10.0])
    rate = 2.0 * np.exp(-120000 / 8.314462618 * (1 / (T + 273.15) - 1 / (712.5 + 273.15)))
    difference = 1.0 - initial
    fraction = initial * np.exp(-difference * rate * t)
    lithium = difference * fraction / (1 - fraction)
    product = initial - lithium
    return {"id": f"synthetic_{T:g}", "provenance": {"source_type": "simulated"},
            "conditions": {"basis": "mol per mol Ti", "temperature_C": T,
                           "c0": {"anatase": 1.0, "Li2CO3": 0.4}},
            "series": [{"species": "anatase", "t_min": t.tolist(), "y": (1 - product).tolist()},
                       {"species": "Li2TiO3", "t_min": t.tolist(), "y": product.tolist()}]}


def observations(amounts):
    datasets = [dataset(t, a) for t, a in zip((700, 725), amounts)]
    return joint_observation_set([(d, sha256_json(d)) for d in datasets])


@pytest.fixture(scope="module")
def protocol():
    result = json.loads((ROOT / "configs/protocols/synthesis-mle-v1.json").read_text())
    result["optimizer"].update(n_starts=4, max_nfev=150)
    result["bounds"]["k_order2"] = [0.1, 10.0]
    return result


@pytest.fixture(scope="module")
def shared_fit(protocol):
    obs = observations((0.32, 0.32))
    sub = {"name": "initial_recovery", "mechanism": mechanism()}
    result = adapter.fit_with_initial_amount(sub, obs, protocol, "shared", seed=31415)
    return sub, obs, result


def test_recovers_shared_initial_amount_and_counts_it_in_aicc(shared_fit):
    _, _, result = shared_fit
    assert result["status"] == "fitted"
    assert result["fitted_initial_amounts"]["c0.Li2CO3"] == pytest.approx(0.32, abs=2e-5)
    assert result["k_kinetic"] == 1 and result["k_initial_amount"] == 1
    assert result["k_noise"] == 2 and result["k_total"] == 4
    n, k = result["n_obs"], result["k_total"]
    assert result["aicc"] == pytest.approx(2 * result["nll"] + 2 * k + 2 * k * (k + 1) / (n - k - 1))
    assert result["initial_amount_uncertainty"][0]["kind"] == "initial_amount"
    assert not result["initial_amount_uncertainty"][0]["at_bound"]


def test_shared_amount_transfers_without_refitting_and_conserves_lithium(shared_fit, protocol):
    sub, obs, result = shared_fit
    compiled = adapter.compile_with_initial_amount(sub["mechanism"], obs.conditions, protocol["bounds"], "shared")
    theta = np.array(result["theta"])
    supplied = {"anatase": 1.0, "Li2CO3": 0.4}
    T = Conditions(None, None, 750)
    times = np.linspace(0, 10, 20)
    predicted = compiled.simulate(theta, times, supplied, conditions=T)
    assert supplied["Li2CO3"] == 0.4  # input dictionaries and dataset truth remain untouched
    assert predicted[1, 0] == pytest.approx(0.32, abs=2e-5)
    np.testing.assert_allclose(2 * predicted[1] + 2 * predicted[2], 0.64, atol=4e-5)
    np.testing.assert_allclose(predicted[0] + predicted[2], 1.0, atol=1e-8)
    base = compile_mechanism(sub["mechanism"], obs.conditions, protocol["bounds"])
    expected = base.simulate(theta[:1], times, {"anatase": 1.0, "Li2CO3": theta[1]}, conditions=T)
    np.testing.assert_allclose(predicted, expected, atol=1e-10)


def test_per_temperature_recovers_two_amounts_and_requires_external_prediction_c0(protocol):
    sub = {"name": "two_amounts", "mechanism": mechanism()}
    obs = observations((0.28, 0.36))
    result = adapter.fit_with_initial_amount(sub, obs, protocol, "per_temperature", seed=42)
    assert result["status"] == "fitted"
    assert result["k_total"] == 5 and result["k_initial_amount"] == 2
    assert result["fitted_initial_amounts"] == pytest.approx({"c0.Li2CO3.700C": 0.28, "c0.Li2CO3.725C": 0.36}, abs=2e-5)
    compiled = adapter.compile_with_initial_amount(sub["mechanism"], obs.conditions, protocol["bounds"], "per_temperature")
    theta = result["theta"]
    with pytest.raises(ValueError, match="explicit external"):
        compiled.simulate(theta, [0, 1], {"anatase": 1}, conditions=Conditions(None, None, 750))
    first = compiled.simulate(theta, [0, 1], {"anatase": 1, "Li2CO3": 0.30}, conditions=Conditions(None, None, 750))
    second = compiled.simulate(theta, [0, 1], {"anatase": 1, "Li2CO3": 0.40}, conditions=Conditions(None, None, 750))
    assert first[1, 0] == pytest.approx(0.30) and second[1, 0] == pytest.approx(0.40)
    assert first[2, 1] < second[2, 1]


def test_bounds_parameter_names_and_identity(protocol):
    conditions = Conditions(None, None, 700, n_temperatures=2)
    shared = adapter.compile_with_initial_amount(mechanism(), conditions, protocol["bounds"], "shared")
    separate = adapter.compile_with_initial_amount(mechanism(), conditions, protocol["bounds"], "per_temperature")
    assert shared.free_names() == ["R1.k", "c0.Li2CO3"]
    assert separate.free_names() == ["R1.k", "c0.Li2CO3.700C", "c0.Li2CO3.725C"]
    assert shared.free[-1].tbounds == (0.25, 0.4) and shared.free[-1].members == []
    with pytest.raises(ValueError, match="outside"):
        shared.simulate([0, 0.41], [0, 1], {"anatase": 1})
    with pytest.raises(ValueError, match="within"):
        adapter.compile_with_initial_amount(mechanism(), conditions, {"initial_amount": [0.2, 0.4]})
    assert adapter.adapter_identity("shared")["sha256"] != adapter.adapter_identity("per_temperature")["sha256"]
    assert adapter.adapter_identity("shared")["sha256"] != adapter.adapter_identity("shared", {"initial_amount": [0.27, 0.4]})["sha256"]


def test_initial_amount_bound_is_reported(protocol):
    sub = {"name": "outside_range", "mechanism": mechanism(free_rate=False)}
    result = adapter.fit_with_initial_amount(sub, observations((0.45, 0.45)), protocol, seed=5)
    assert result["status"] == "fitted"
    assert result["fitted_initial_amounts"]["c0.Li2CO3"] == pytest.approx(0.4, abs=1e-5)
    assert "c0.Li2CO3: at fit bound" in result["initial_amount_flags"]


def test_profile_uses_same_fitted_initial_parameter(shared_fit, protocol):
    sub, obs, fitted = shared_fit
    result = adapter.profile_with_initial_amount(sub, obs, protocol, fitted)
    profile = result["params"]["c0.Li2CO3"]
    assert profile["mle"] == pytest.approx(0.32, abs=2e-5)
    assert profile["classification"] == "identifiable"
    assert profile["ci95"][0] < 0.32 < profile["ci95"][1]
    stale = copy.deepcopy(fitted)
    stale["adapter"]["sha256"] = "stale"
    with pytest.raises(ValueError, match="changed"):
        adapter.profile_with_initial_amount(sub, obs, protocol, stale)
    with pytest.raises(ValueError, match="changed"):
        adapter.profile_with_initial_amount(sub, observations((0.31, 0.31)), protocol, fitted)
