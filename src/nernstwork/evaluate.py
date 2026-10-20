"""The shared evaluator. Every candidate, whoever proposed it, goes through `validate_submission` and `run_fit`
with the same protocol; nothing here knows or reads who proposed a candidate.

Outcome statuses (model.py) keep apart: an invalid submission, invalid chemistry, a representation the evaluator
does not support, a candidate that cannot predict a measured channel, features the data cannot inform, a numerical
failure (solver_failure, nonconvergence), and a fitted model (whose adequacy is reported separately). A computation
failure is not evidence against the chemistry.
"""
from __future__ import annotations

import hashlib
import math
import platform
import sys
from pathlib import Path

import numpy as np

from . import schemas
from .canonical import canonical_forms, canonical_param_keys, default_observation_map
from .data import ObservationSet, sha256_json
from .fit import Problem, fit, profile_likelihood, seed_from
from .model import (FITTED, INCOMPATIBLE_OBSERVATION, INSUFFICIENT_DATA, INVALID_SUBMISSION, CompileError,
                    compile_mechanism, dead_reactions)

CODE_FILES = ("model.py", "fit.py", "data.py", "canonical.py", "evaluate.py", "mechanism.py")


def code_identity() -> dict:
    src = Path(__file__).resolve().parent
    h = hashlib.sha256()
    for f in CODE_FILES:
        h.update(f.encode())
        h.update((src / f).read_bytes())
    import scipy

    versions = {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__}
    h.update(repr(sorted(versions.items())).encode())
    return {"sha256": h.hexdigest(), "files": [f"src/nernstwork/{f}" for f in CODE_FILES], "versions": versions,
            "platform": f"{sys.platform}-{platform.machine()}"}


def protocol_hash(protocol: dict) -> str:
    return sha256_json(protocol)


def _support_summary(sub: dict) -> dict:
    counts = {"literature": 0, "data": 0, "speculative": 0}
    targets = set()
    for s in sub.get("support", []):
        counts[s["basis"]] += 1
        targets.add(s["target"].split(".")[0])
    rids = [r["id"] for r in sub["mechanism"]["reactions"]]
    lit_no_source = [s["target"] for s in sub.get("support", []) if s["basis"] == "literature" and not s.get("source")]
    return {"counts": counts, "reactions_without_support": [r for r in rids if r not in targets],
            "literature_claims_without_source": lit_no_source}


def validate_submission(sub: dict, obs: ObservationSet, protocol: dict) -> dict:
    """Structural, chemical and observational checks before any numerics. Pure function of its inputs."""
    rep = {"status": "valid", "errors": [], "warnings": []}
    errs = schemas.errors("candidate", sub)
    if errs:
        rep.update(status=INVALID_SUBMISSION, errors=errs)
        return rep
    mech = sub["mechanism"]
    channels = obs.channel_names()
    om = sub.get("observation_map") or default_observation_map(mech, channels)
    ids = {s["id"]: s for s in mech["species"]}
    missing = [ch for ch in channels if ch not in om]
    extra = [ch for ch in om if ch not in channels]
    unknown = sorted({x for v in om.values() for x in v if x not in ids})
    if unknown:
        rep.update(status=INVALID_SUBMISSION, errors=[f"observation_map refers to unknown species {unknown}"])
        return rep
    if missing:
        rep.update(status=INCOMPATIBLE_OBSERVATION,
                   errors=[f"measured channel(s) {missing} have no model species; add the species or map the channel "
                           f"in observation_map (channels: {channels})"])
        return rep
    if extra:
        rep["warnings"].append(f"observation_map entries {extra} are not measured in {obs.dataset_id}; ignored")
        om = {k: v for k, v in om.items() if k in channels}
    for ch, sps in om.items():
        for s in sps:
            if ids[s].get("observable") is False:
                rep.update(status=INVALID_SUBMISSION,
                           errors=[f"species {s} is declared observable=false but is mapped to measured channel {ch}"])
                return rep
    for s in mech["species"]:
        mapped = any(s["id"] in v for v in om.values())
        if s.get("observable", True) and not mapped:
            rep["warnings"].append(f"species {s['id']} is observable=true but not measured in {obs.dataset_id}")
    unknown_c0 = [s for s in obs.c0 if s not in ids]
    if unknown_c0:
        rep.update(status=INCOMPATIBLE_OBSERVATION,
                   errors=[f"dataset initial species {unknown_c0} are not in the mechanism"])
        return rep
    try:
        comp = compile_mechanism(mech, obs.conditions, protocol.get("bounds"))
    except CompileError as e:
        rep.update(status=e.status, errors=e.messages)
        return rep
    rep["warnings"] += comp.warnings
    dead = dead_reactions(mech, obs.c0)
    if dead:
        rep["warnings"].append(f"reactions {dead} can never run from this initial state (their parameters have no "
                               "information)")
    k_noise = {"profiled_gaussian": len(channels), "legacy_scaled": 1, "fixed_gaussian": 0}[protocol["noise"]["model"]]
    k_total = comp.n_free + k_noise
    if k_total >= obs.n_obs - 1:
        rep.update(status=INSUFFICIENT_DATA,
                   errors=[f"{comp.n_free} kinetic + {k_noise} noise parameters for {obs.n_obs} observations"])
        return rep
    forms = canonical_forms(mech, om, set(obs.c0), protocol.get("bounds"))
    rep.update({
        "observation_map": om, "free_parameters": [{"name": p.name, "kind": p.kind, "bounds": [p.lo, p.hi],
                                                     "transform": p.transform} for p in comp.free],
        "k_kinetic": comp.n_free, "k_noise": k_noise, "n_obs": obs.n_obs,
        "dynamics_hash": forms["dynamics"][1], "chem_hash": forms["chem"][1],
        "canonical_map": forms["dynamics"][2],
        "support": _support_summary(sub),
    })
    return rep


def fit_key(dynamics_hash: str, dataset_sha: str, protocol: dict, code_sha: str) -> str:
    return sha256_json({"dynamics": dynamics_hash, "data": dataset_sha, "protocol": protocol_hash(protocol), "code": code_sha})


def run_fit(sub: dict, validation: dict, obs: ObservationSet, protocol: dict) -> dict:
    """Numerical fit; depends only on the candidate's dynamics, the data and the protocol."""
    comp = compile_mechanism(sub["mechanism"], obs.conditions, protocol.get("bounds"))
    prob = Problem(comp, obs, validation["observation_map"], protocol)
    seed = seed_from(f"{protocol['optimizer']['seed']}:{validation['dynamics_hash']}:{obs.sha256}")
    res = fit(prob, protocol, seed)
    res["free_parameter_names"] = comp.free_names()
    # canonical coordinates, so every observationally equivalent candidate can read this fit in its own names
    res["canonical_param_keys"] = canonical_param_keys(comp, validation["canonical_map"])
    res["canonical_species"] = dict(validation["canonical_map"]["labels"])
    res["observation_notes"] = obs.notes
    return res


def translate_fit(fit_res: dict, validation: dict, compiled) -> dict:
    """Return a copy of a stored fit expressed in this candidate's parameter and species names.

    A stored fit is shared by every candidate with the same dynamics_hash, but it was computed in the names and parameter
    order of whichever candidate was fitted first. Everything name- or order-dependent is mapped through canonical keys.
    """
    if fit_res.get("status") != FITTED:
        return fit_res
    my_keys = canonical_param_keys(compiled, validation["canonical_map"])
    my_names = compiled.free_names()
    stored_keys = fit_res["canonical_param_keys"]
    if sorted(my_keys) != sorted(stored_keys):
        raise ValueError("stored fit does not match this candidate's parameters (canonical keys differ)")
    pos = [stored_keys.index(k) for k in my_keys]
    key_of_stored_name = dict(zip(fit_res["free_parameter_names"], stored_keys))
    my_name_of_key = dict(zip(my_keys, my_names))
    rename = lambda n: my_name_of_key[key_of_stored_name[n]]
    out = dict(fit_res)
    out["theta"] = [fit_res["theta"][i] for i in pos]
    out["free_parameter_names"] = my_names
    unc = dict(fit_res["uncertainty"])
    by_name = {p["name"]: p for p in unc.get("params", [])}
    unc["params"] = [dict(by_name[fit_res["free_parameter_names"][i]], name=my_names[k]) for k, i in enumerate(pos)]
    unc["sloppy_directions"] = [dict(d, combination={rename(n): v for n, v in d["combination"].items()})
                                for d in unc.get("sloppy_directions", [])]
    unc["high_correlations"] = [dict(c, pair=[rename(n) for n in c["pair"]]) for c in unc.get("high_correlations", [])]
    out["uncertainty"] = unc
    label_to_stored = {lab: sp for sp, lab in fit_res["canonical_species"].items()}
    mine = validation["canonical_map"]["labels"]
    tr = fit_res["trajectory"]
    out["trajectory"] = {"t_min": tr["t_min"], "species": {sp: tr["species"][label_to_stored[lab]] for sp, lab in mine.items()}}
    out["canonical_species"] = dict(mine)
    return out


def profile_to_canonical(profile: dict, fit_res: dict) -> dict:
    keys = dict(zip(fit_res["free_parameter_names"], fit_res["canonical_param_keys"]))
    return dict(profile, params={keys[n]: dict(d, computed_as=n) for n, d in profile["params"].items()})


def profile_from_canonical(profile: dict, validation: dict, compiled) -> dict:
    name_of = dict(zip(canonical_param_keys(compiled, validation["canonical_map"]), compiled.free_names()))
    return dict(profile, params={name_of[k]: d for k, d in profile["params"].items()})


def run_profiles(sub: dict, validation: dict, obs: ObservationSet, protocol: dict, fit_res: dict, names=None) -> dict:
    comp = compile_mechanism(sub["mechanism"], obs.conditions, protocol.get("bounds"))
    prob = Problem(comp, obs, validation["observation_map"], protocol)
    return profile_likelihood(prob, np.array(fit_res["theta"]), fit_res["nll"], protocol, names)


def annotate(sub: dict, validation: dict, fit_res: dict, obs: ObservationSet, protocol: dict) -> dict:
    """Chemistry-specific annotations of a fit (cheap; recomputed per candidate even when the fit is shared)."""
    if fit_res.get("status") != FITTED:
        return {}
    mech = sub["mechanism"]
    om = validation["observation_map"]
    observed = {x for v in om.values() for x in v}
    consumed = {t["species"] for r in mech["reactions"] for t in r["reactants"]}
    unobs = [s["id"] for s in mech["species"] if s["id"] not in observed]
    hidden = [s for s in unobs if s in consumed]
    terminal = [s for s in unobs if s not in consumed]
    tr = fit_res["trajectory"]
    t = np.array(tr["t_min"])
    Y = {s: np.array(v) for s, v in tr["species"].items()}
    total0 = sum(obs.c0.values())
    out = {"unobserved_species": unobs, "hidden_intermediates": hidden, "unobserved_terminal": terminal}
    flags = []
    if hidden:
        h = sum(Y[s] for s in hidden)
        i = int(np.argmax(h))
        frac = float(h[i] / total0)
        out["peak_hidden_fraction_of_total_N"] = frac
        out["peak_hidden_time_min"] = float(t[i])
        cap = protocol.get("plausibility", {}).get("max_hidden_fraction_of_total_N")
        if cap is not None and frac > cap:
            flags.append(f"hidden pool peaks at {frac:.2f} of total N (> {cap}; {protocol['plausibility'].get('max_hidden_fraction_source', '')})")
    if unobs:
        u = sum(Y[s] for s in unobs)
        out["unobserved_N_end_mM"] = float(u[-1])
        out["unobserved_N_max_mM"] = float(u.max())
    pred_closure = sum(Y[s] for s in observed) / total0
    out["predicted_observed_closure_end"] = float(pred_closure[-1])
    for p in fit_res["uncertainty"]["params"]:
        if p["at_bound"]:
            flags.append(f"{p['name']} at a protocol bound ({p['value']:.3g})")
    for w in validation.get("warnings", []):
        if "non-electrochemical" in w or "oxidation at the cathode" in w:
            flags.append(w)
    out["plausibility_flags"] = flags
    return out


def evaluation_summary(cid: str, validation: dict, fit_res: dict | None, notes: dict | None) -> dict:
    """Compact, code-computed summary used by rankings, tools and reviews."""
    s = {"candidate_id": cid, "status": validation["status"] if validation["status"] != "valid" else
         (fit_res or {}).get("status", "pending")}
    if validation["status"] != "valid":
        s["errors"] = validation["errors"]
        return s
    s["k_kinetic"] = validation["k_kinetic"]
    if not fit_res or fit_res.get("status") != FITTED:
        if fit_res:
            s["numerics"] = fit_res.get("multistart")
        return s
    s.update({k: fit_res[k] for k in ("nll", "aicc", "bic", "k_total", "n_obs")})
    s["dynamics_hash"] = validation.get("dynamics_hash")
    s["optimizer_warning"] = fit_res["multistart"].get("warning")
    s["rmse"] = {ch: v["rmse"] for ch, v in fit_res["residuals"]["channels"].items()}
    s["sigma"] = fit_res["sigma"]
    s["adequacy"] = fit_res["residuals"]["adequacy"]
    s["adequacy_reasons"] = fit_res["residuals"]["adequacy_reasons"]
    s["replicates"] = fit_res["multistart"].get("replicates")
    s["params"] = {p["name"]: {"value": p["value"], "wald_ci95": p["wald_ci95"], "determinacy": p["determinacy"],
                               "at_bound": p["at_bound"]} for p in fit_res["uncertainty"]["params"]}
    s["sloppy_directions"] = fit_res["uncertainty"]["sloppy_directions"]
    if notes:
        s.update({k: notes[k] for k in ("peak_hidden_fraction_of_total_N", "unobserved_N_end_mM", "plausibility_flags")
                  if k in notes})
    return s


def rank(summaries: list[dict], protocol: dict) -> dict:
    """Numerical ranking in code. Only fitted candidates on the same observations are comparable."""
    crit = protocol.get("ranking", {}).get("criterion", "aicc")
    d_ind = protocol.get("ranking", {}).get("indistinguishable_delta", 2.0)
    d_con = protocol.get("ranking", {}).get("considerable_delta", 4.0)
    fitted = [s for s in summaries if s["status"] == FITTED and math.isfinite(s.get(crit, math.inf))]
    groups: dict[tuple, list] = {}
    for s in fitted:
        groups.setdefault((s["n_obs"], tuple(sorted(s["rmse"]))), []).append(s)
    out = {"criterion": crit, "note": (f"Delta {crit} <= {d_ind}: not distinguished by these data; <= {d_con}: still "
                                       "supported. Akaike weights are relative support within this candidate set (one weight per distinct dynamics) under "
                                       "the stated noise model, not probabilities that a mechanism is true. Residual "
                                       "correlation from misspecification makes these differences optimistic."),
           "groups": []}
    for key, ss in groups.items():
        ss = sorted(ss, key=lambda s: s[crit])
        best = ss[0][crit]
        # Akaike weights over distinct dynamics: observationally equivalent candidates share one fit and one weight
        first: dict[str, str] = {}
        cls = []
        for s in ss:
            h = s.get("dynamics_hash") or s["candidate_id"]
            first.setdefault(h, s["candidate_id"])
            cls.append(h)
        uniq = list(first)
        wu = np.exp(-0.5 * (np.array([next(s[crit] for s in ss if (s.get("dynamics_hash") or s["candidate_id"]) == h)
                                      for h in uniq]) - best))
        wu = dict(zip(uniq, wu / wu.sum()))
        rows = []
        for s, h in zip(ss, cls):
            d = s[crit] - best
            rows.append({"candidate_id": s["candidate_id"], crit: s[crit], f"delta_{crit}": d, "weight": float(wu[h]),
                         "equivalent_to": None if first[h] == s["candidate_id"] else first[h],
                         "bic": s["bic"], "k_total": s["k_total"], "adequacy": s["adequacy"],
                         "replicates": s.get("replicates"), "optimizer_warning": s.get("optimizer_warning"),
                         "band": "indistinguishable_from_best" if d <= d_ind else ("supported" if d <= d_con else "less_supported"),
                         "plausibility_flags": s.get("plausibility_flags", [])})
        out["groups"].append({"n_obs": key[0], "channels": list(key[1]), "rows": rows})
    out["not_ranked"] = [{"candidate_id": s["candidate_id"], "status": s["status"]} for s in summaries
                         if s not in fitted]
    return out
