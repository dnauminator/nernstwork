"""Fit an effective initial Li2CO3 amount without changing the validated core engine.

``shared`` fits one initial amount and transfers it unchanged to a new temperature.
``per_temperature`` fits separate amounts at 700/725 C. At any other temperature
the caller must supply an external Li2CO3 initial amount; there is no interpolation
or refitting on the prediction data. All amounts are formula units per mol Ti.

This is an experimental nuisance-parameter adapter, not a measurement of the
weighed precursor composition. Its implementation hash belongs in every cache key.
"""
from __future__ import annotations

import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nernstwork.data import parts_of, sha256_file, sha256_json
from nernstwork.evaluate import code_identity, seed_from, validate_submission
from nernstwork.fit import Problem, fit, profile_likelihood
from nernstwork.model import Compiled, FreeParam, compile_mechanism

MODES = ("shared", "per_temperature")
INITIAL_BOUNDS = (0.25, 0.4)
DEVELOPMENT_TEMPERATURES = (700.0, 725.0)


def _amount_bounds(bounds: dict | None) -> tuple[float, float]:
    limits = (bounds or {}).get("initial_amount", INITIAL_BOUNDS)
    if len(limits) != 2:
        raise ValueError("initial_amount bounds must contain two numbers")
    lo, hi = map(float, limits)
    if not all(math.isfinite(x) for x in (lo, hi)) or not INITIAL_BOUNDS[0] <= lo < hi <= INITIAL_BOUNDS[1]:
        raise ValueError("initial_amount bounds must be increasing and within [0.25, 0.4]")
    return lo, hi


def adapter_identity(mode: str, bounds: dict | None = None) -> dict:
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    spec = {"adapter_version": 1, "source_sha256": sha256_file(__file__), "mode": mode,
            "initial_amount_bounds": list(_amount_bounds(bounds)),
            "development_temperatures_C": list(DEVELOPMENT_TEMPERATURES),
            "prediction_policy": "transfer_shared_fitted_c0" if mode == "shared" else "require_external_c0"}
    return dict(spec, sha256=sha256_json(spec))


class InitialAmountCompiled(Compiled):
    """The existing parameter vector with one or two linear initial-amount slots."""

    def resolved_c0(self, theta, c0: dict, conditions=None) -> dict:
        theta = np.asarray(theta, dtype=float)
        if theta.ndim != 1 or len(theta) != self.n_free or not np.all(np.isfinite(theta)):
            raise ValueError(f"expected {self.n_free} finite parameters, including fitted initial amounts")
        cond = conditions or self.conditions
        if cond is None or not math.isfinite(float(cond.T_C)):
            raise ValueError("a finite temperature is required to resolve initial amounts")
        chosen = None
        if self.initial_amount_mode == "shared":
            chosen = self.kinetic_n_free
        else:
            for i, temperature in enumerate(DEVELOPMENT_TEMPERATURES):
                if math.isclose(cond.T_C, temperature, rel_tol=0, abs_tol=1e-8):
                    chosen = self.kinetic_n_free + i
                    break
        resolved = dict(c0)
        if chosen is not None:
            parameter = self.free[chosen]
            amount = float(theta[chosen])
            if not parameter.lo - 1e-12 <= amount <= parameter.hi + 1e-12:
                raise ValueError(f"{parameter.name} is outside its declared bounds")
            resolved["Li2CO3"] = amount
        elif "Li2CO3" not in resolved:
            raise ValueError("per_temperature prediction requires an explicit external Li2CO3 c0")
        if not math.isfinite(float(resolved["Li2CO3"])) or float(resolved["Li2CO3"]) < 0:
            raise ValueError("external Li2CO3 c0 must be finite and nonnegative")
        return resolved

    def simulate(self, theta, t_eval, c0, rtol=1e-8, atol=1e-10, method="LSODA", max_rhs=None, conditions=None):
        resolved = self.resolved_c0(theta, c0, conditions)
        # Initial-amount parameters have members=[], so core rate resolution ignores
        # them while derivatives, uncertainty and profiling retain the whole vector.
        return super().simulate(theta, t_eval, resolved, rtol, atol, method, max_rhs, conditions)


def compile_with_initial_amount(mechanism, conditions, bounds=None, mode="shared") -> InitialAmountCompiled:
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    lo, hi = _amount_bounds(bounds)
    base = compile_mechanism(mechanism, conditions, bounds)
    if "Li2CO3" not in base.species:
        raise ValueError("fitted initial amount requires a Li2CO3 species")
    if mode == "per_temperature" and conditions.n_temperatures < 2:
        raise ValueError("per_temperature amounts require joint development temperatures")
    compiled = InitialAmountCompiled(**vars(base))
    compiled.free = list(base.free)
    compiled.warnings = list(base.warnings)
    compiled.kinetic_n_free = base.n_free
    compiled.initial_amount_mode = mode
    names = ["c0.Li2CO3"] if mode == "shared" else [f"c0.Li2CO3.{T:g}C" for T in DEVELOPMENT_TEMPERATURES]
    compiled.free.extend(FreeParam(name, "initial_amount", "initial_amount", lo, hi, []) for name in names)
    compiled.initial_amount_names = names
    if not any(t["species"] == "Li2CO3" for r in mechanism["reactions"] for t in r["reactants"]):
        compiled.warnings.append("Li2CO3 is not a reactant; its initial amount cannot affect other species")
    return compiled


def _problem(submission, obs, protocol, mode):
    validation = validate_submission(submission, obs, protocol)
    if validation["status"] != "valid":
        raise ValueError(f"invalid candidate for initial-amount fit: {validation['errors']}")
    temperatures = {p.conditions.T_C for p in parts_of(obs)}
    if mode == "per_temperature" and temperatures != set(DEVELOPMENT_TEMPERATURES):
        raise ValueError("per_temperature fitting uses exactly the 700 and 725 C development datasets")
    compiled = compile_with_initial_amount(submission["mechanism"], obs.conditions, protocol.get("bounds"), mode)
    problem = Problem(compiled, obs, validation["observation_map"], protocol)
    if compiled.n_free + problem.n_sigma_params >= obs.n_obs - 1:
        raise ValueError("insufficient observations after counting fitted initial amounts")
    return compiled, problem, validation


def fit_with_initial_amount(submission, obs, protocol, mode="shared", seed=None) -> dict:
    """Fit development observations only; cache ownership stays with the caller."""
    compiled, problem, validation = _problem(submission, obs, protocol, mode)
    identity = adapter_identity(mode, protocol.get("bounds"))
    engine = code_identity()["sha256"]
    result_identity = {"adapter_sha256": identity["sha256"], "engine_sha256": engine,
                       "dynamics_hash": validation["dynamics_hash"], "dataset_sha256": obs.sha256,
                       "protocol_sha256": sha256_json(protocol), "mode": mode}
    if seed is None:
        seed = seed_from(f"{protocol['optimizer']['seed']}:{sha256_json(result_identity)}")
    result_identity["seed"] = int(seed)
    result = fit(problem, protocol, int(seed))
    result.update(adapter=identity, result_identity=dict(result_identity, sha256=sha256_json(result_identity)),
                  free_parameter_names=compiled.free_names(), initial_amount_parameter_names=compiled.initial_amount_names,
                  k_initial_amount=len(compiled.initial_amount_names), adapter_warnings=compiled.warnings,
                  observation_notes=obs.notes)
    if result["status"] == "fitted":
        # The core counts every free slot correctly; distinguish kinetic and initial
        # parameters in this adapter's report without changing k_total or AICc.
        result["n_free_total"] = compiled.n_free
        result["k_kinetic"] = compiled.kinetic_n_free
        result["fitted_initial_amounts"] = {name: float(result["theta"][compiled.free_names().index(name)])
                                            for name in compiled.initial_amount_names}
        initial_uncertainty = [p for p in result["uncertainty"]["params"] if p["kind"] == "initial_amount"]
        result["initial_amount_uncertainty"] = initial_uncertainty
        result["initial_amount_flags"] = [f"{p['name']}: {message}" for p in initial_uncertainty
                                          for message in (["at fit bound"] if p["at_bound"] else [])
                                          + ([p["determinacy"]] if p["determinacy"] != "well_determined" else [])]
    return result


def profile_with_initial_amount(submission, obs, protocol, fitted, names=None) -> dict:
    """Profile c0 by default, refitting kinetic parameters using the existing engine."""
    mode = fitted["adapter"]["mode"]
    identity = adapter_identity(mode, protocol.get("bounds"))
    if fitted["adapter"]["sha256"] != identity["sha256"]:
        raise ValueError("adapter changed since this fit; do not profile a stale result")
    compiled, problem, validation = _problem(submission, obs, protocol, mode)
    expected = {"engine_sha256": code_identity()["sha256"], "dataset_sha256": obs.sha256,
                "protocol_sha256": sha256_json(protocol), "dynamics_hash": validation["dynamics_hash"]}
    if any(fitted["result_identity"].get(key) != value for key, value in expected.items()):
        raise ValueError("engine, candidate, data or protocol changed since this initial-amount fit")
    if fitted.get("free_parameter_names") != compiled.free_names():
        raise ValueError("parameter order differs from the fitted candidate")
    result = profile_likelihood(problem, np.array(fitted["theta"]), fitted["nll"], protocol,
                                compiled.initial_amount_names if names is None else names)
    return dict(result, adapter=identity, fit_identity=fitted["result_identity"])
