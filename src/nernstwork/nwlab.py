"""Exploratory toolkit for the investigator's sandbox.

A read-only snapshot of the model, validator and fitter is placed next to each run's evidence pack, so the investigator
can check, simulate and roughly fit candidates in seconds instead of writing its own ODE code. Results here are
EXPLORATORY: fewer starts and looser tolerances than the official protocol, no caching, nothing stored. Official
numbers come only from the nw_evaluate tool. The toolkit sees the development evidence and nothing else.

    import nwlab
    ds, obs = nwlab.dataset()                 # the development dataset(s) in the evidence pack (several: fitted jointly)
    nwlab.check(candidate)                    # schema, N/electron bookkeeping, unsupported features
    y = nwlab.simulate(candidate)             # trajectories at the candidate's own parameter values
    r = nwlab.quick_fit(candidate)            # exploratory maximum-likelihood fit
    nwlab.plot(candidate, r, "plots/x.png")   # overlay on the data
"""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path

import numpy as np

from nernstwork.data import joint_observation_set, load_dataset
from nernstwork.evaluate import run_fit, translate_fit, validate_submission
from nernstwork.model import FITTED, compile_mechanism

LABEL = "EXPLORATORY (sandbox toolkit; not the official evaluation)"


def _evidence() -> Path:
    env = os.environ.get("NW_EVIDENCE")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2] / "evidence"


def protocol(exploratory: bool = True) -> dict:
    p = json.loads((_evidence() / "evidence_summary.json").read_text())["protocol"]
    if exploratory:
        p = copy.deepcopy(p)
        p["optimizer"].update(n_starts=4, max_nfev=150, max_outer=6, max_ode_solves_per_fit=8000)
        p["ode"].update(rtol=1e-6, atol=1e-8)
    return p


def dataset(path: str | None = None):
    """(dataset dict, observation set). With several development datasets (e.g. temperatures) the first value is the
    list of dataset dicts and the observation set is the joint one the official evaluator fits."""
    files = [Path(path)] if path else sorted((_evidence() / "datasets").glob("*.json"))
    items = [load_dataset(f) for f in files]
    obs = joint_observation_set(items)
    return (items[0][0] if len(items) == 1 else [ds for ds, _ in items]), obs


def _as_candidate(c: dict) -> dict:
    return c if "mechanism" in c else {"name": c.get("id", "mechanism"), "mechanism": c}


def check(candidate: dict) -> dict:
    """The official validator's report (status, errors, warnings, free parameters)."""
    _, obs = dataset()
    v = validate_submission(_as_candidate(candidate), obs, protocol(False))
    return {k: v.get(k) for k in ("status", "errors", "warnings", "free_parameters", "k_kinetic", "k_noise", "n_obs",
                                  "observation_map")}


def simulate(candidate: dict, params: dict | None = None, t=None, c0: dict | None = None) -> dict:
    """Trajectories at the candidate's stated parameter values, optionally overridden by {free-parameter name: value}.
    With several development datasets the result is {dataset id: trajectories}, one per experiment's conditions."""
    cand = _as_candidate(candidate)
    _, obs = dataset()
    comp = compile_mechanism(cand["mechanism"], obs.conditions, protocol(False).get("bounds"))
    vals = []
    for p in comp.free:
        j, slot, sp = p.members[0]
        rl = cand["mechanism"]["reactions"][j]["rate_law"]
        prm = {"k": rl["params"].get("k"), "K": rl["params"].get("K"), "k_mt": rl["params"].get("k_mt"),
               "tau_min": (rl.get("time_modulation") or {}).get("tau_min"),
               "alpha": (rl.get("potential_dependence") or {}).get("alpha"),
               "ph_order": (rl.get("ph_dependence") or {}).get("order"),
               "order": (rl.get("orders") or {}).get(sp),
               "Ea": (rl.get("temperature_dependence") or {}).get("Ea_kJ_mol"),
               "n_avrami": (rl.get("time_modulation") or {}).get("n")}[slot]
        v = (params or {}).get(p.name, prm["value"])
        vals.append(p.to_t(float(v)))
    tt = np.asarray(t if t is not None else np.linspace(0, float(obs.t_union.max()), 200), float)
    out = {}
    parts = getattr(obs, "parts", [obs])
    for part in parts:
        Y = comp.simulate(np.array(vals), tt, c0 or part.c0, conditions=part.conditions)
        out[part.dataset_id] = {"t_min": tt, **{s: Y[i] for i, s in enumerate(comp.species)}}
    return out[parts[0].dataset_id] if len(parts) == 1 else out


def quick_fit(candidate: dict, n_starts: int = 4) -> dict:
    """Exploratory fit (same likelihood as the protocol, fewer starts, looser tolerances). Seconds, not minutes."""
    cand = _as_candidate(candidate)
    _, obs = dataset()
    p = protocol(True)
    p["optimizer"]["n_starts"] = int(n_starts)
    v = validate_submission(cand, obs, p)
    if v["status"] != "valid":
        return {"label": LABEL, "status": v["status"], "errors": v["errors"]}
    r = run_fit(cand, v, obs, p)
    out = {"label": LABEL, "status": r["status"], "multistart": r["multistart"]}
    if r["status"] != FITTED:
        return out
    r = translate_fit(r, v, compile_mechanism(cand["mechanism"], obs.conditions, p.get("bounds")))
    out.update({
        "aicc_exploratory": r["aicc"], "nll": r["nll"], "k_total": r["k_total"], "n_obs": r["n_obs"], "sigma": r["sigma"],
        "rmse": {ch: d["rmse"] for ch, d in r["residuals"]["channels"].items()},
        "adequacy": r["residuals"]["adequacy"], "adequacy_reasons": r["residuals"]["adequacy_reasons"],
        "params": {q["name"]: q["value"] for q in r["uncertainty"]["params"]},
        "trajectory": r["trajectory"], "observation_map": v["observation_map"],
    })
    if "trajectories" in r:
        out["trajectories"] = r["trajectories"]
    return out


def plot(candidate: dict, fit: dict, path: str):
    """Overlay an exploratory fit on the data (channels and unmeasured N)."""
    from nernstwork import plots

    _, obs = dataset()
    plots.plot_fits(obs, [(_as_candidate(candidate)["name"], dict(fit, _mapping=fit["observation_map"]))], Path(path),
                    title=f"{LABEL}: {_as_candidate(candidate)['name']}")
    return path
