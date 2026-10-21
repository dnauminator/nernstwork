"""Compile a mechanism (mechanism.schema.json dict) into a numerical model with an explicit free-parameter vector.

`mechanism.simulate` stays the reference definition of the kinetics. This module is an equivalent, faster
form for the fitter (tests check both agree) plus the bookkeeping fitting needs: which numbers are free,
their bounds and transforms, which are tied, and which features cannot be evaluated against a given dataset.
Anything the evaluator cannot represent raises `CompileError` with an explicit status instead of being
silently changed into a different mechanism.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy.integrate import solve_ivp

from .mechanism import F, R, T_EPS_MIN, validate_mechanism

# Outcome statuses shared by the evaluator, the store and the agent tools.
INVALID_SUBMISSION = "invalid_submission"  # schema or structural error in what was submitted
INVALID_CHEMISTRY = "invalid_chemistry"  # violates N or electron bookkeeping
UNSUPPORTED = "unsupported_representation"  # well-formed, but the evaluator cannot represent it
INCOMPATIBLE_OBSERVATION = "incompatible_observation"  # cannot predict a measured channel
INSUFFICIENT_DATA = "insufficient_data"  # representable, but these data cannot inform it
SOLVER_FAILURE = "solver_failure"
NONCONVERGENCE = "nonconvergence"
FITTED = "fitted"

LOG_KINDS = {"k", "K", "k_mt", "tau_min"}

DEFAULT_BOUNDS = {
    "k_order1": [1e-7, 10.0],  # min^-1
    "k_order2": [1e-10, 1.0],  # (mM-N)^-1 min^-1
    "k_other": [1e-10, 10.0],
    "K": [1e-2, 1e5],  # mM-N
    "k_mt": [1e-6, 1e2],  # min^-1
    "tau_min": [1.0, 1e6],  # min
    "alpha": [-1.0, 3.0],
    "order": [0.0, 3.0],
    "ph_order": [-2.0, 2.0],
    "Ea": [0.0, 600.0],  # kJ/mol (Arrhenius temperature dependence)
    "n_avrami": [0.3, 4.0],  # Avrami exponent
}


class CompileError(Exception):
    def __init__(self, status: str, messages: list[str]):
        super().__init__(f"{status}: " + "; ".join(messages))
        self.status = status
        self.messages = messages


class SolverFailure(Exception):
    pass


class _RHSBudget(Exception):
    pass


@dataclass
class FreeParam:
    name: str  # e.g. "R1.k", or "tie:tau_cat" for a tie group
    kind: str  # k, K, k_mt, tau_min, alpha, order, ph_order, Ea, n_avrami
    bounds_key: str  # key into the protocol bounds table
    lo: float
    hi: float
    members: list  # [(reaction index, slot, species-or-None)]

    @property
    def transform(self) -> str:
        return "log10" if self.kind in LOG_KINDS else "linear"

    def to_t(self, v: float) -> float:
        return math.log10(v) if self.transform == "log10" else v

    def from_t(self, x):
        return 10.0 ** x if self.transform == "log10" else x

    @property
    def tbounds(self):
        return self.to_t(self.lo), self.to_t(self.hi)


@dataclass
class Conditions:
    E_V: float | None
    pH: float | None
    T_C: float
    n_potentials: int = 1
    n_pH: int = 1
    n_temperatures: int = 1


@dataclass
class Compiled:
    mechanism: dict
    species: list[str]
    observable: dict
    S: np.ndarray  # (n_species, n_reactions) net stoichiometry
    slots: list[dict]  # per reaction: slot -> fixed natural value (free slots filled from theta)
    free: list[FreeParam]
    families: list[str]
    reactant_terms: list[list[tuple[int, float]]]
    tmod: list[str | None]
    warnings: list[str] = field(default_factory=list)
    conditions: Conditions | None = None

    @property
    def n_free(self) -> int:
        return len(self.free)

    def free_names(self) -> list[str]:
        return [p.name for p in self.free]

    def tbounds(self):
        lo = np.array([p.tbounds[0] for p in self.free], float)
        hi = np.array([p.tbounds[1] for p in self.free], float)
        return lo, hi

    def natural(self, theta) -> list[float]:
        return [float(p.from_t(x)) for p, x in zip(self.free, theta)]

    # ------------------------------------------------------------- numerics
    def _resolved(self, theta):
        vals = [dict(s) for s in self.slots]
        for p, x in zip(self.free, theta):
            v = float(p.from_t(x))
            for j, slot, sp in p.members:
                if slot == "order":
                    vals[j].setdefault("orders", {})[sp] = v
                else:
                    vals[j][slot] = v
        return vals

    def _rate_arrays(self, theta, cond: Conditions | None = None):
        cond = cond or self.conditions
        vals = self._resolved(theta)
        nr = len(vals)
        k = np.empty(nr)
        for j, v in enumerate(vals):
            kk = v["k"]
            if "alpha" in v:
                T = cond.T_C + 273.15
                kk *= math.exp(v["alpha"] * F * (v["E_ref_V"] - cond.E_V) / (R * T))
            if "ph_order" in v:
                kk *= 10 ** (-v["ph_order"] * (cond.pH - v["pH_ref"]))
            if "Ea" in v:
                kk *= math.exp(-v["Ea"] * 1e3 / R * (1.0 / (cond.T_C + 273.15) - 1.0 / v["T_ref_K"]))
            if "k_mt" in v:
                kk = 1.0 / (1.0 / kk + 1.0 / v["k_mt"])
            k[j] = kk
        return vals, k

    def make_rhs(self, theta, cond: Conditions | None = None):
        vals, kvec = self._rate_arrays(theta, cond)
        S = self.S
        uni_j, uni_s, lang_j, lang_s, lang_K, gen = [], [], [], [], [], []
        for j, (fam, terms) in enumerate(zip(self.families, self.reactant_terms)):
            if fam == "langmuir_saturation":
                lang_j.append(j)
                lang_s.append(terms[0][0])
                lang_K.append(vals[j]["K"])
            elif fam == "mass_action" and len(terms) == 1 and terms[0][1] == 1:
                uni_j.append(j)
                uni_s.append(terms[0][0])
            else:
                if fam == "power_law":
                    sp_ids = self.mechanism["reactions"][j]["rate_law"]["orders"].keys()
                    idx = [self.species.index(s) for s in sp_ids]
                    ex = [vals[j]["orders"][s] for s in sp_ids]
                else:
                    idx = [i for i, _ in terms]
                    ex = [c for _, c in terms]
                gen.append((j, np.array(idx, int), np.array(ex, float)))
        uni_j, uni_s = np.array(uni_j, int), np.array(uni_s, int)
        lang_j, lang_s, lang_K = np.array(lang_j, int), np.array(lang_s, int), np.array(lang_K, float)
        act = np.array([j for j, m in enumerate(self.tmod) if m == "activation"], int)
        deact = np.array([j for j, m in enumerate(self.tmod) if m == "deactivation"], int)
        tau_act = np.array([vals[j]["tau_min"] for j in act], float)
        tau_deact = np.array([vals[j]["tau_min"] for j in deact], float)
        avr = np.array([j for j, m in enumerate(self.tmod) if m == "avrami"], int)
        n_avr = np.array([vals[j]["n_avrami"] for j in avr], float)
        k_avr = kvec[avr] if len(avr) else np.zeros(0)
        has_t = len(act) + len(deact) + len(avr) > 0

        def rhs(t, y):
            c = np.maximum(y, 0.0)
            r = kvec.copy()
            if len(uni_j):
                r[uni_j] *= c[uni_s]
            if len(lang_j):
                x = c[lang_s]
                r[lang_j] *= x / (1.0 + x / lang_K)
            for j, idx, ex in gen:
                r[j] *= np.prod(c[idx] ** ex)
            if has_t:
                if len(act):
                    r[act] *= 1.0 - np.exp(-t / tau_act)
                if len(deact):
                    r[deact] *= np.exp(-t / tau_deact)
                if len(avr):
                    # JMAK: g = n (k t)^(n-1), with the step's effective k; common time origin t = 0
                    r[avr] *= n_avr * (k_avr * max(t, T_EPS_MIN)) ** (n_avr - 1.0)
            return S @ r

        return rhs

    def simulate(self, theta, t_eval, c0: dict, rtol=1e-8, atol=1e-10, method="LSODA", max_rhs: int | None = None,
                 conditions: Conditions | None = None) -> np.ndarray:
        """Amounts (n_species, len(t_eval)) on the dataset basis (mM-N for electrochemistry). Raises SolverFailure.

        max_rhs caps right-hand-side evaluations per solve (a deterministic compute budget): parameter sets that make the
        system pathologically stiff fail like any other solver failure instead of running for hours. `conditions`
        overrides the compiled conditions (one experiment of a multi-temperature fit, or a planned design).
        """
        t_eval = np.asarray(t_eval, float)
        y0 = np.array([float(c0.get(s, 0.0)) for s in self.species])
        rhs = self.make_rhs(theta, conditions)
        if max_rhs:
            inner, calls = rhs, [0]

            def rhs(t, y):
                calls[0] += 1
                if calls[0] > max_rhs:
                    raise _RHSBudget()
                return inner(t, y)
        try:
            with np.errstate(over="raise", invalid="raise"):
                sol = solve_ivp(rhs, (0.0, float(t_eval.max())), y0, t_eval=t_eval, method=method, rtol=rtol, atol=atol)
        except (FloatingPointError, ValueError, ZeroDivisionError, OverflowError) as e:
            raise SolverFailure(f"integration raised {type(e).__name__}: {e}") from e
        except _RHSBudget:
            raise SolverFailure(f"right-hand-side evaluation budget ({max_rhs}) exceeded") from None
        if not sol.success or sol.y.shape[1] != len(t_eval) or not np.all(np.isfinite(sol.y)):
            raise SolverFailure(f"integration failed: {sol.message}")
        return sol.y


# ------------------------------------------------------------------- compile
def _bounds_key(kind: str, rxn: dict) -> str:
    if kind != "k":
        return kind
    rl = rxn["rate_law"]
    if rl["family"] == "langmuir_saturation":
        return "k_order1"
    if rl["family"] == "power_law":
        orders = rl.get("orders", {}).values()
        if any(not o.get("fixed") for o in orders):
            return "k_other"  # free orders: the k scale must not depend on proposed starting values
        tot = sum(o["value"] for o in orders)
    else:
        tot = sum(t["coeff"] for t in rxn["reactants"])
    return {1.0: "k_order1", 2.0: "k_order2"}.get(float(tot), "k_other")


def _param_entries(rxn: dict):
    """Yield (slot, species, param dict, kind) for every numeric parameter of a reaction's rate law."""
    rl = rxn["rate_law"]
    yield "k", None, rl["params"]["k"], "k"
    if "K" in rl["params"]:
        yield "K", None, rl["params"]["K"], "K"
    if "k_mt" in rl["params"]:
        yield "k_mt", None, rl["params"]["k_mt"], "k_mt"
    if rl.get("potential_dependence"):
        yield "alpha", None, rl["potential_dependence"]["alpha"], "alpha"
    if rl.get("ph_dependence"):
        yield "ph_order", None, rl["ph_dependence"]["order"], "ph_order"
    if rl.get("temperature_dependence"):
        yield "Ea", None, rl["temperature_dependence"]["Ea_kJ_mol"], "Ea"
    tm = rl.get("time_modulation")
    if tm:
        if tm["kind"] == "avrami":
            yield "n_avrami", None, tm["n"], "n_avrami"
        else:
            yield "tau_min", None, tm["tau_min"], "tau_min"
    if rl["family"] == "power_law":
        for sp, o in rl.get("orders", {}).items():
            yield "order", sp, o, "order"


def compile_mechanism(mech: dict, conditions: Conditions, protocol_bounds: dict | None = None) -> Compiled:
    """Compile for a dataset's conditions. Raises CompileError with an explicit status."""
    bounds_table = dict(DEFAULT_BOUNDS, **(protocol_bounds or {}))
    problems = validate_mechanism(mech)
    if problems:
        structural = [p for p in problems if "unknown species" in p or "needs" in p]
        if structural:
            raise CompileError(INVALID_SUBMISSION, problems)
        raise CompileError(INVALID_CHEMISTRY, problems)

    warnings = []
    species = [s["id"] for s in mech["species"]]
    if len(set(species)) != len(species):
        raise CompileError(INVALID_SUBMISSION, ["duplicate species ids"])
    rids = [r["id"] for r in mech["reactions"]]
    if len(set(rids)) != len(rids):
        raise CompileError(INVALID_SUBMISSION, ["duplicate reaction ids"])
    idx = {s: i for i, s in enumerate(species)}
    ox = {s["id"]: s.get("N_oxidation_state") for s in mech["species"]}

    unsupported, insufficient = [], []
    for rxn in mech["reactions"]:
        rl = rxn["rate_law"]
        if rxn.get("reversible"):
            unsupported.append(f"{rxn['id']}: reversible=true has no reverse rate constant in the schema and the simulator "
                               "integrates every step forward only; submit the reverse step as its own reaction")
        for slot, _sp, prm, _kind in _param_entries(rxn):
            if "prior" in prm:
                warnings.append(f"{rxn['id']}.{slot}: prior is recorded but not used by the maximum-likelihood evaluator")
        if rl["family"] == "power_law":
            missing = set(rl.get("orders", {})) - {t["species"] for t in rxn["reactants"]}
            if missing:
                raise CompileError(INVALID_SUBMISSION, [f"{rxn['id']}: power_law orders for non-reactants {sorted(missing)}"])
        pdp = rl.get("potential_dependence")
        if pdp:
            if conditions.E_V is None:
                insufficient.append(f"{rxn['id']}: potential_dependence needs a potential on the RHE scale; the dataset has none")
            elif not pdp["alpha"].get("fixed") and conditions.n_potentials < 2:
                insufficient.append(f"{rxn['id']}: free alpha cannot be estimated from data at a single potential "
                                    "(it is confounded with k); fix alpha or drop the term")
        phd = rl.get("ph_dependence")
        if phd:
            if conditions.pH is None:
                insufficient.append(f"{rxn['id']}: ph_dependence needs a pH; the dataset reports none")
            elif not phd["order"].get("fixed") and conditions.n_pH < 2:
                insufficient.append(f"{rxn['id']}: free pH order cannot be estimated from data at a single pH")
        td = rl.get("temperature_dependence")
        if td and not td["Ea_kJ_mol"].get("fixed") and conditions.n_temperatures < 2:
            insufficient.append(f"{rxn['id']}: free Ea cannot be estimated from data at a single temperature (it is "
                                "confounded with k); fit several temperatures jointly, fix Ea, or drop the term")
        e = rxn.get("electrons")
        if rl.get("time_modulation") and rl["time_modulation"]["kind"] != "avrami" and e == 0:
            warnings.append(f"{rxn['id']}: catalyst-state time modulation on a non-electrochemical step (electrons = 0), "
                            "e.g. crossover or volatilization would not deactivate with the catalyst")
        states = [ox.get(t["species"]) for t in rxn["reactants"] + rxn["products"]]
        if e is not None and any(s is None for s in states):
            warnings.append(f"{rxn['id']}: electrons={e} cannot be checked (a species has unknown oxidation state)")
        if e is not None and e < 0:
            warnings.append(f"{rxn['id']}: electrons={e} < 0 is an oxidation at the cathode")
    if unsupported:
        raise CompileError(UNSUPPORTED, unsupported)
    if insufficient:
        raise CompileError(INSUFFICIENT_DATA, insufficient)

    # tie groups are checked as a whole, independent of reaction order
    tie_members: dict[str, list] = {}
    for rxn in mech["reactions"]:
        if "K" in rxn["rate_law"]["params"] and rxn["rate_law"]["family"] != "langmuir_saturation":
            raise CompileError(INVALID_SUBMISSION, [f"{rxn['id']}: params.K is only used by langmuir_saturation"])
        for slot, _sp, prm, kind in _param_entries(rxn):
            if prm.get("tie"):
                tie_members.setdefault(prm["tie"], []).append((rxn["id"], slot, kind, prm))
    for tie, mem in tie_members.items():
        kinds = {k for _, _, k, _ in mem}
        fixed = {bool(p.get("fixed")) for _, _, _, p in mem}
        if len(kinds) > 1:
            raise CompileError(INVALID_SUBMISSION, [f"tie '{tie}' joins parameters of different kinds {sorted(kinds)}"])
        if len(fixed) > 1:
            raise CompileError(INVALID_SUBMISSION, [f"tie '{tie}' mixes fixed and free parameters"])
        if fixed == {True} and len({float(p["value"]) for *_, p in mem}) > 1:
            raise CompileError(INVALID_SUBMISSION, [f"tie '{tie}' mixes different fixed values"])

    nr = len(mech["reactions"])
    S = np.zeros((len(species), nr))
    families, reactant_terms, tmod, slots = [], [], [], []
    groups: dict[str, FreeParam] = {}
    free: list[FreeParam] = []
    tie_fixed: dict[str, float] = {}
    for j, rxn in enumerate(mech["reactions"]):
        for t in rxn["reactants"]:
            S[idx[t["species"]], j] -= t["coeff"]
        for t in rxn["products"]:
            S[idx[t["species"]], j] += t["coeff"]
        rl = rxn["rate_law"]
        families.append(rl["family"])
        reactant_terms.append([(idx[t["species"]], float(t["coeff"])) for t in rxn["reactants"]])
        tm = rl.get("time_modulation")
        tmod.append(tm["kind"] if tm else None)
        slot_vals = {}
        if rl.get("potential_dependence"):
            slot_vals["E_ref_V"] = rl["potential_dependence"]["E_ref_V"]
        if rl.get("ph_dependence"):
            slot_vals["pH_ref"] = rl["ph_dependence"]["pH_ref"]
        if rl.get("temperature_dependence"):
            slot_vals["T_ref_K"] = rl["temperature_dependence"]["T_ref_C"] + 273.15
        for slot, sp, prm, kind in _param_entries(rxn):
            bkey = _bounds_key(kind, rxn)
            plo, phi = bounds_table[bkey]
            lo, hi = prm.get("bounds", [plo, phi])
            tie = prm.get("tie")
            if not prm.get("fixed"):
                tol = 1e-12 * max(abs(plo), abs(phi), 1.0)
                if lo < plo - tol or hi > phi + tol or lo >= hi:
                    raise CompileError(INVALID_SUBMISSION, [f"{rxn['id']}.{slot}: bounds {[lo, hi]} must be increasing and "
                                                            f"inside the protocol bounds {[plo, phi]} for {bkey}"])
                if kind in LOG_KINDS and lo <= 0:
                    raise CompileError(INVALID_SUBMISSION, [f"{rxn['id']}.{slot}: bounds must be positive"])
            elif not math.isfinite(float(prm["value"])) or (kind in LOG_KINDS and prm["value"] <= 0):
                raise CompileError(INVALID_SUBMISSION, [f"{rxn['id']}.{slot}: fixed value must be finite (and positive for {kind})"])
            if prm.get("fixed"):
                v = float(prm["value"])
                if tie:
                    if tie in tie_fixed and not math.isclose(tie_fixed[tie], v, rel_tol=1e-12):
                        raise CompileError(INVALID_SUBMISSION, [f"tie '{tie}' mixes different fixed values"])
                    tie_fixed[tie] = v
                if slot == "order":
                    slot_vals.setdefault("orders", {})[sp] = v
                else:
                    slot_vals[slot] = v
                continue
            member = (j, slot, sp)
            name = f"{rxn['id']}.{slot}" + (f".{sp}" if sp else "")
            if tie:
                if tie in tie_fixed:
                    raise CompileError(INVALID_SUBMISSION, [f"tie '{tie}' mixes fixed and free parameters"])
                g = groups.get(tie)
                if g is None:
                    g = FreeParam(f"tie:{tie}", kind, bkey, float(lo), float(hi), [member])
                    groups[tie] = g
                    free.append(g)
                else:
                    if g.kind != kind or not (math.isclose(g.lo, lo) and math.isclose(g.hi, hi)):
                        raise CompileError(INVALID_SUBMISSION, [f"tie '{tie}' joins parameters with different kinds or bounds "
                                                                f"({g.kind} {[g.lo, g.hi]} vs {kind} {[lo, hi]})"])
                    g.members.append(member)
            else:
                free.append(FreeParam(name, kind, bkey, float(lo), float(hi), [member]))
        slots.append(slot_vals)
    for tie, g in groups.items():
        if len(g.members) == 1:
            warnings.append(f"tie '{tie}' has a single member")

    observable = {s["id"]: s.get("observable", True) for s in mech["species"]}
    return Compiled(mech, species, observable, S, slots, free, families, reactant_terms, tmod, warnings, conditions)


def dead_reactions(mech: dict, c0: dict) -> list[str]:
    """Reactions whose reactants can never become nonzero from the initial state (their k is structurally unidentifiable)."""
    present = {s for s, v in c0.items() if v > 0}
    changed = True
    while changed:
        changed = False
        for r in mech["reactions"]:
            if all(t["species"] in present for t in r["reactants"]):
                for t in r["products"]:
                    if t["species"] not in present:
                        present.add(t["species"])
                        changed = True
    return [r["id"] for r in mech["reactions"] if not all(t["species"] in present for t in r["reactants"])]
