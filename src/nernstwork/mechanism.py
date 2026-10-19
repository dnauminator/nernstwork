"""Reference implementation of the mechanism schema: validation and ODE simulation.

This is intentionally small. It exists to prove the schema is executable and to give the
benchmark worlds ground-truth trajectories. It is not the inference engine.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp

F = 96485.33212  # C/mol
R = 8.314462618  # J/(mol K)


def load_json(path):
    return json.loads(Path(path).read_text())


# ---------------------------------------------------------------- validation
def validate_mechanism(m: dict) -> list[str]:
    """Semantic checks the JSON schema cannot express. Returns a list of problems (empty = ok)."""
    problems = []
    ids = {s["id"] for s in m["species"]}
    ox = {s["id"]: s.get("N_oxidation_state") for s in m["species"]}
    for rxn in m["reactions"]:
        rid = rxn["id"]
        for term in rxn["reactants"] + rxn["products"]:
            if term["species"] not in ids:
                problems.append(f"{rid}: unknown species {term['species']}")
        n_in = sum(t["coeff"] for t in rxn["reactants"])
        n_out = sum(t["coeff"] for t in rxn["products"])
        if not math.isclose(n_in, n_out, rel_tol=1e-9):
            problems.append(f"{rid}: N-equivalents not conserved ({n_in} in, {n_out} out)")
        e = rxn.get("electrons")
        states = [ox.get(t["species"]) for t in rxn["reactants"] + rxn["products"]]
        if e is not None and all(s is not None for s in states):
            calc = sum(t["coeff"] * ox[t["species"]] for t in rxn["reactants"]) - sum(
                t["coeff"] * ox[t["species"]] for t in rxn["products"]
            )
            if not math.isclose(calc, e, abs_tol=1e-9):
                problems.append(f"{rid}: electrons={e} but oxidation states imply {calc}")
        rl = rxn["rate_law"]
        if rl["family"] == "langmuir_saturation":
            if "K" not in rl["params"]:
                problems.append(f"{rid}: langmuir_saturation needs params.K")
            if len(rxn["reactants"]) != 1:
                problems.append(f"{rid}: langmuir_saturation needs exactly one reactant")
        if rl["family"] == "power_law" and "orders" not in rl:
            problems.append(f"{rid}: power_law needs 'orders'")
    return problems


# ---------------------------------------------------------------- kinetics
def effective_k(rxn: dict, E_V: float, pH: float, T_C: float = 25.0) -> float:
    rl = rxn["rate_law"]
    k = rl["params"]["k"]["value"]
    T = T_C + 273.15
    pdp = rl.get("potential_dependence")
    if pdp:
        k *= math.exp(pdp["alpha"]["value"] * F * (pdp["E_ref_V"] - E_V) / (R * T))
    phd = rl.get("ph_dependence")
    if phd:
        k *= 10 ** (-phd["order"]["value"] * (pH - phd["pH_ref"]))
    kmt = rl["params"].get("k_mt")
    if kmt:
        k = 1.0 / (1.0 / k + 1.0 / kmt["value"])
    return k


def time_factor(rxn: dict, t_min: float) -> float:
    """Catalyst-state modulation g(t); 1.0 when the reaction has none."""
    tm = rxn["rate_law"].get("time_modulation")
    if not tm:
        return 1.0
    tau = tm["tau_min"]["value"]
    if tm["kind"] == "activation":
        return 1.0 - math.exp(-t_min / tau)
    return math.exp(-t_min / tau)


def rate(rxn: dict, c: dict, k: float) -> float:
    rl = rxn["rate_law"]
    fam = rl["family"]
    if fam == "mass_action":
        r = k
        for t in rxn["reactants"]:
            r *= max(c[t["species"]], 0.0) ** t["coeff"]
        return r
    if fam == "power_law":
        r = k
        for sp, order in rl["orders"].items():
            r *= max(c[sp], 0.0) ** order["value"]
        return r
    if fam == "langmuir_saturation":
        sp = rxn["reactants"][0]["species"]
        K = rl["params"]["K"]["value"]
        x = max(c[sp], 0.0)
        return k * x / (1.0 + x / K)
    raise ValueError(f"unknown rate-law family {fam}")


def simulate(m: dict, c0: dict, t_min, E_V: float, pH: float = 7.0, T_C: float = 25.0, rtol=1e-8, atol=1e-10):
    """Integrate the mechanism. Concentrations in mM-N, time in minutes. Returns {species: array}."""
    names = [s["id"] for s in m["species"]]
    idx = {n: i for i, n in enumerate(names)}
    ks = [effective_k(r, E_V, pH, T_C) for r in m["reactions"]]

    def rhs(_t, y):
        c = {n: y[idx[n]] for n in names}
        dy = np.zeros_like(y)
        for rxn, k in zip(m["reactions"], ks):
            r = rate(rxn, c, k) * time_factor(rxn, _t)
            for t in rxn["reactants"]:
                dy[idx[t["species"]]] -= t["coeff"] * r
            for t in rxn["products"]:
                dy[idx[t["species"]]] += t["coeff"] * r
        return dy

    y0 = np.array([c0.get(n, 0.0) for n in names], dtype=float)
    t_min = np.asarray(t_min, dtype=float)
    sol = solve_ivp(rhs, (t_min.min(), t_min.max()), y0, t_eval=t_min, method="LSODA", rtol=rtol, atol=atol)
    if not sol.success:
        raise RuntimeError(sol.message)
    return {n: sol.y[idx[n]] for n in names}


def total_N(traj: dict) -> np.ndarray:
    return sum(traj.values())
