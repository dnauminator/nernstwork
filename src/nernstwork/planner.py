"""Experiment planner: which feasible measurement best separates the surviving models.

For every candidate design (temperature, initial amounts, sampling times, measured phases) each surviving model predicts
the measured channels with its development MLE. Designs are scored by the pairwise discrimination criterion of
Buzzi-Ferraris and Forzatti (1983), weighted by the models' Akaike weights:

    U(x) = sum_{i<j} w_i w_j  D_ij(x),   D_ij = d_ij^T (2 S_eps + G_i V_i G_i^T + G_j V_j G_j^T)^-1 d_ij

d_ij is the difference of the two models' predictions, S_eps the measurement noise (each phase's profiled development
sigma), G_i the sensitivity of model i's predictions to its parameters and V_i its Fisher covariance at the MLE. Because
parameter uncertainty sits in the denominator, a disagreement that only reflects poorly determined parameters (for
example an Arrhenius extrapolation) is discounted rather than rewarded; rewarding parameter spread was reported to be
unstable (Murphy et al. 2026). A pair counts as separable on a design when D_ij exceeds the number of predicted points
(the Buzzi-Ferraris convention). The bounded score 0.5 log det(I + S_eps^-1 S_mu) (S_mu: Akaike-weighted spread of the
model means) is reported next to U because the pairwise sum is unbounded.

All of this is local (linearized) and uses development data only; it is a ranking of designs, not a guarantee.
"""
from __future__ import annotations

import itertools
import math

import numpy as np

from .data import parts_of
from .fit import Problem, jacobian
from .model import FITTED, SolverFailure, compile_mechanism


def default_designs(obs) -> list[dict]:
    """A finite menu for phase-fraction time courses: other temperatures, dense early sampling, a rutile precursor."""
    parts = parts_of(obs)
    c0 = dict(parts[0].c0)
    temps = sorted({p.conditions.T_C for p in parts})
    t_std = sorted({float(t) for p in parts for t in p.t_union if t > 0})
    t_end = max(t_std)
    early = [round(x, 3) for x in np.geomspace(0.05, 2.0, 12)]
    out = []
    for T in sorted({temps[0] - 50, temps[0] - 25, temps[-1] + 25, temps[-1] + 50, temps[-1] + 75}):
        out.append({"name": f"T{T:g}C_standard", "temperature_C": T, "c0": c0, "t_sample_min": t_std})
    for T in temps:
        out.append({"name": f"T{T:g}C_dense_early", "temperature_C": T, "c0": c0, "t_sample_min": early})
    if "anatase" in c0:
        rut = {("rutile" if k == "anatase" else k): v for k, v in c0.items()}
        out.append({"name": f"rutile_precursor_T{temps[-1]:g}C", "temperature_C": temps[-1], "c0": rut, "t_sample_min": t_std})
    for f in (0.5, 1.5):
        if "Li2CO3" in c0:
            out.append({"name": f"Li2CO3_x{f:g}_T{temps[-1]:g}C", "temperature_C": temps[-1],
                        "c0": dict(c0, Li2CO3=round(c0["Li2CO3"] * f, 4)), "t_sample_min": t_std})
    for d in out:
        d["t_sample_min"] = [t for t in d["t_sample_min"] if t <= t_end]
    return out


def _model_state(run, cid, rec, inv):
    """(candidate, compiled, theta, sigma by channel, Fisher covariance in transformed coordinates, observation map)."""
    obs = inv._dev_obs(run)
    protocol = run.protocol()
    c, v, _, fr, _ = inv.fit_view(run, cid, rec)
    comp = compile_mechanism(c["submission"]["mechanism"], obs.conditions, protocol.get("bounds"))
    prob = Problem(comp, obs, v["observation_map"], protocol)
    x = np.array(fr["theta"], float)
    sig = np.array([fr["sigma"][g] for g in prob.groups], float)
    J = jacobian(prob, x, sig)
    V = np.linalg.pinv(J.T @ J, rcond=1e-10)  # pseudo-inverse: unidentified directions do not blow up the score
    return c, comp, x, dict(fr["sigma"]), V, v["observation_map"]


def _predict(comp, theta, om, design, channels, cond):
    t = np.asarray(design["t_sample_min"], float)
    tt = np.unique(np.concatenate([[0.0], t]))
    Y = comp.simulate(theta, tt, design["c0"], conditions=cond)
    pos = [int(np.searchsorted(tt, x)) for x in t]
    return np.concatenate([Y[[comp.species.index(s) for s in om[ch]]][:, pos].sum(0) for ch in channels])


def _sensitivity(comp, theta, om, design, channels, cond, h=1e-4):
    lo, hi = comp.tbounds()
    base = _predict(comp, theta, om, design, channels, cond)
    G = np.zeros((len(base), len(theta)))
    for i in range(len(theta)):
        up, dn = min(h, hi[i] - theta[i]), min(h, theta[i] - lo[i])
        if up <= 0 and dn <= 0:
            continue
        a, b = theta.copy(), theta.copy()
        a[i] += up
        b[i] -= dn
        G[:, i] = (_predict(comp, a, om, design, channels, cond) - _predict(comp, b, om, design, channels, cond)) / (up + dn)
    return base, G


def plan(run, designs: list[dict] | None = None, cids: list[str] | None = None, max_models: int = 6,
         delta: float | None = None) -> dict:
    from . import investigation as inv  # lazy: investigation is the store-facing layer

    obs = inv._dev_obs(run)
    protocol = run.protocol()
    delta = protocol.get("ranking", {}).get("considerable_delta", 4.0) if delta is None else delta
    recs = inv.current_records(run)
    fitted = [(cid, r) for cid, r in recs.items() if r["summary"]["status"] == FITTED]
    if cids:
        fitted = [(cid, r) for cid, r in fitted if cid in cids]
    # one representative per distinct dynamics, lowest development AICc first
    seen, models = set(), []
    for cid, r in sorted(fitted, key=lambda x: x[1]["summary"]["aicc"]):
        h = r["summary"].get("dynamics_hash") or cid
        if h not in seen:
            seen.add(h)
            models.append((cid, r))
    if not cids:
        best = models[0][1]["summary"]["aicc"] if models else math.nan
        models = [m for m in models if m[1]["summary"]["aicc"] - best <= delta]
    dropped = models[max_models:]
    models = models[:max_models]
    if len(models) < 2:
        return {"error": f"need at least two fitted models with distinct dynamics within delta AICc {delta} "
                         f"(found {len(models)}); pass candidate_ids to choose them"}
    aicc = np.array([m[1]["summary"]["aicc"] for m in models])
    # Akaike weights over the survivors; models chosen by hand are hypotheses to separate and count equally
    w = np.ones(len(models)) if cids else np.exp(-0.5 * (aicc - aicc.min()))
    w = w / w.sum()
    states = [_model_state(run, cid, r, inv) for cid, r in models]
    channels = obs.channel_names()
    designs = designs or default_designs(obs)
    base_cond = parts_of(obs)[0].conditions
    rows = []
    for d in designs:
        d = dict(d)
        d.setdefault("c0", dict(parts_of(obs)[0].c0))
        if "t_sample_min" not in d:
            t_end = float(d.get("t_end_min", obs.t_union.max()))
            d["t_sample_min"] = [float(t) for t in obs.t_union if 0 < t <= t_end]
        observe = [ch for ch in d.get("observe", channels) if ch in channels]
        cond = base_cond if d.get("temperature_C") is None else type(base_cond)(
            E_V=base_cond.E_V, pH=base_cond.pH, T_C=float(d["temperature_C"]))
        mus, covs, fail = [], [], None
        for (cid, _), (c, comp, x, sig, V, om) in zip(models, states):
            try:
                mu, G = _sensitivity(comp, x, om, d, observe, cond)
            except SolverFailure as e:
                fail = f"{cid}: {e}"
                break
            mus.append(mu)
            covs.append(G @ V @ G.T)
        if fail:
            rows.append({"design": d, "error": f"prediction failed ({fail})"})
            continue
        nt = len(d["t_sample_min"])
        s_eps = np.concatenate([np.full(nt, float(np.average([st[3][ch] for st in states], weights=w)) ** 2)
                                for ch in observe])
        S_eps = np.diag(s_eps)
        pairs, U = [], 0.0
        for i, j in itertools.combinations(range(len(models)), 2):
            dlt = mus[i] - mus[j]
            D = float(dlt @ np.linalg.solve(2 * S_eps + covs[i] + covs[j], dlt))
            U += w[i] * w[j] * D
            k = int(np.argmax(np.abs(dlt) / np.sqrt(s_eps)))
            pairs.append({"pair": [models[i][0], models[j][0]], "D": D, "separable": D > len(dlt),
                          "largest_gap": {"channel": observe[k // nt], "t_min": d["t_sample_min"][k % nt],
                                          "difference": float(dlt[k]), "in_noise_sigma": float(abs(dlt[k]) / math.sqrt(s_eps[k]))}})
        mbar = np.average(np.array(mus), axis=0, weights=w)
        S_mu = sum(wi * np.outer(m - mbar, m - mbar) for wi, m in zip(w, mus))
        sign, logdet = np.linalg.slogdet(np.eye(len(mbar)) + S_mu / s_eps[:, None])
        pairs.sort(key=lambda p: -p["D"])
        rows.append({"design": d, "U": U, "bounded_score": 0.5 * float(logdet), "n_points": int(len(mbar)),
                     "n_separable_pairs": sum(p["separable"] for p in pairs), "n_pairs": len(pairs), "pairs": pairs[:6],
                     "predictions": {models[i][0]: {ch: mus[i][k * nt:(k + 1) * nt].round(5).tolist()
                                                    for k, ch in enumerate(observe)} for i in range(len(models))}})
    ok = sorted([r for r in rows if "U" in r], key=lambda r: -r["U"])
    out = {"method": __doc__.split("\n\n")[1].strip().replace("\n", " "),
           "weights": "equal (models chosen by hand)" if cids else "Akaike weights over the survivors",
           "models": [{"candidate_id": cid, "name": st[0]["name"], "aicc": float(a), "weight": float(wi)}
                      for (cid, _), st, a, wi in zip(models, states, aicc, w)],
           "models_not_considered": [cid for cid, _ in dropped],
           "ranking": [{"design": r["design"]["name"], "U": r["U"], "bounded_score": r["bounded_score"],
                        "separable_pairs": f"{r['n_separable_pairs']}/{r['n_pairs']}"} for r in ok],
           "designs": ok + [r for r in rows if "U" not in r],
           "note": ("No design on this menu separates the surviving models beyond noise plus parameter uncertainty."
                    if ok and not any(r["n_separable_pairs"] for r in ok) else None)}
    n = inv._next_free(run.dir / "analyses", "plan-{}.json", lambda k: dict(out, created_at=inv.now()))
    run.event("plan_computed", n=n, models=[m[0] for m in models], top=ok[0]["design"]["name"] if ok else None)
    return out
