"""Maximum-likelihood fitting: deterministic multistart, explicit noise models, local and profile identifiability.

Noise models (protocol["noise"]["model"]):
  profiled_gaussian  independent Gaussian errors with one unknown sigma per measured channel, maximized out
                     (iteratively reweighted least squares). Sigma has a floor, max(abs_floor, rel_floor * channel max),
                     so a channel that is fitted almost exactly cannot drive the likelihood to infinity. Default.
  fixed_gaussian     sigma_i = sqrt(abs^2 + (rel * y_i)^2) per channel, taken from the protocol (no sigma parameters).
  legacy_scaled      residuals divided by each channel's maximum, one shared sigma. This is the objective of
                     scripts/calibrate_liao.py; kept only to reproduce the earlier calibration inside this evaluator.

A joint fit (several experiments, e.g. temperatures, one parameter vector) simulates each experiment under its own
conditions; profiled_gaussian then has one sigma per measured species, shared across experiments.

All three treat points as independent. With 7-18 points per channel from one trajectory, residuals of a misspecified
model are serially correlated, so information-criterion differences overstate the evidence; adequacy diagnostics
(runs test, lag-1 autocorrelation) are reported next to every fit for that reason.
"""
from __future__ import annotations

import math
import time

import numpy as np
from scipy.optimize import least_squares
from scipy.stats import norm, qmc

from .data import parts_of
from .model import FITTED, NONCONVERGENCE, SOLVER_FAILURE, Compiled, SolverFailure

PENALTY = 1e4
DEFAULT_MAX_RHS_EVALS = 20_000  # per ODE solve
DEFAULT_MAX_ODE_SOLVES = 60_000  # per fit (all starts); about 4x the largest fit observed on the Liao data


class FitBudgetExceeded(Exception):
    pass


class Problem:
    def __init__(self, compiled: Compiled, obs, mapping: dict, protocol: dict):
        self.c = compiled
        self.obs = obs
        self.protocol = protocol
        ode = protocol.get("ode", {})
        self.rtol, self.atol, self.method = ode.get("rtol", 1e-8), ode.get("atol", 1e-10), ode.get("method", "LSODA")
        self.max_rhs = int(ode.get("max_rhs_evals", DEFAULT_MAX_RHS_EVALS))
        self.max_solves = int(protocol.get("optimizer", {}).get("max_ode_solves_per_fit", DEFAULT_MAX_ODE_SOLVES))
        self.enforce_budget = False
        self.parts = parts_of(obs)
        self.joint = len(self.parts) > 1
        sp_idx = {s: i for i, s in enumerate(compiled.species)}
        self.chan = []  # (channel, positions in its experiment's time grid, species indices)
        self.chan_part, self.chan_label, self.part_t = [], [], []
        for pi, part in enumerate(self.parts):
            pos = {float(v): i for i, v in enumerate(part.t_union)}
            self.part_t.append(part.t_union)
            for ch in part.channels:
                self.chan.append((ch, np.array([pos[float(v)] for v in ch.t], int),
                                  np.array([sp_idx[s] for s in mapping[ch.name]], int)))
                self.chan_part.append(pi)
                self.chan_label.append(f"{part.dataset_id}:{ch.name}" if self.joint else ch.name)
        self.t = self.part_t[0]
        # noise groups: one per measured species (shared by the experiments of a joint fit; one per channel otherwise)
        self.groups = []
        for ch, _, _ in self.chan:
            if ch.name not in self.groups:
                self.groups.append(ch.name)
        self.chan_group = [self.groups.index(ch.name) for ch, _, _ in self.chan]
        self.n = obs.n_obs
        self.n_ch = len(self.chan)
        noise = protocol.get("noise", {})
        self.noise_model = noise.get("model", "profiled_gaussian")
        floor_ch = [max(noise.get("abs_floor_mM", 0.05), noise.get("rel_floor", 0.01) * ch.scale) for ch, _, _ in self.chan]
        self.floor = np.array([max(f for f, g in zip(floor_ch, self.chan_group) if g == k) for k in range(len(self.groups))])
        self.group_scale = [max(ch.scale for (ch, _, _), g in zip(self.chan, self.chan_group) if g == k)
                            for k in range(len(self.groups))]
        if self.noise_model == "fixed_gaussian":
            spec = noise.get("channels", {})
            self.fixed_sigma = []
            for ch, _, _ in self.chan:
                s = spec.get(ch.name, spec.get("*"))
                if s is None:
                    raise ValueError(f"fixed_gaussian noise has no entry for channel {ch.name}")
                self.fixed_sigma.append(np.sqrt(s["abs"] ** 2 + (s["rel"] * ch.y) ** 2))
        self.n_ode = 0
        self.n_ode_fail = 0

    @property
    def n_sigma_params(self) -> int:
        return {"profiled_gaussian": len(self.groups), "legacy_scaled": 1, "fixed_gaussian": 0}[self.noise_model]

    # ------------------------------------------------------------------ predictions
    def trajectories(self, theta, t=None, part: int = 0):
        if self.enforce_budget and self.n_ode >= self.max_solves:
            raise FitBudgetExceeded()
        self.n_ode += 1
        p = self.parts[part]
        try:
            return self.c.simulate(theta, self.part_t[part] if t is None else t, p.c0, self.rtol, self.atol, self.method,
                                   max_rhs=self.max_rhs, conditions=p.conditions if self.joint else None)
        except SolverFailure:
            self.n_ode_fail += 1
            raise

    def raw_residuals(self, theta):
        Ys = [self.trajectories(theta, part=i) for i in range(len(self.parts))]
        return [Ys[pi][sidx][:, tpos].sum(axis=0) - ch.y for (ch, tpos, sidx), pi in zip(self.chan, self.chan_part)]

    def weights(self, sig):
        if self.noise_model == "profiled_gaussian":
            return [np.full(len(ch.y), sig[g]) for (ch, _, _), g in zip(self.chan, self.chan_group)]
        if self.noise_model == "fixed_gaussian":
            return self.fixed_sigma
        return [np.full(len(ch.y), ch.scale * sig[0]) for ch, _, _ in self.chan]

    def weighted(self, theta, wts):
        try:
            return np.concatenate([r / w for r, w in zip(self.raw_residuals(theta), wts)])
        except SolverFailure:
            return np.full(self.n, PENALTY)

    def nll(self, raw, sig) -> float:
        if self.noise_model == "profiled_gaussian":
            tot = 0.0
            for r, g in zip(raw, self.chan_group):
                s = sig[g]
                tot += len(r) * 0.5 * math.log(2 * math.pi * s * s) + float(r @ r) / (2 * s * s)
            return tot
        if self.noise_model == "fixed_gaussian":
            tot = 0.0
            for r, w in zip(raw, self.fixed_sigma):
                tot += float(np.sum(np.log(w)) + 0.5 * len(r) * math.log(2 * math.pi) + np.sum((r / w) ** 2) / 2)
            return tot
        s2 = sig[0] ** 2
        rw = np.concatenate([r / ch.scale for r, (ch, _, _) in zip(raw, self.chan)])
        return self.n * 0.5 * math.log(2 * math.pi * s2) + float(rw @ rw) / (2 * s2)

    def sigma_hat(self, raw):
        if self.noise_model == "profiled_gaussian":
            ss, nn = np.zeros(len(self.groups)), np.zeros(len(self.groups))
            for r, g in zip(raw, self.chan_group):
                ss[g] += float(r @ r)
                nn[g] += len(r)
            return np.array([max(math.sqrt(s / n), f) for s, n, f in zip(ss, nn, self.floor)])
        if self.noise_model == "fixed_gaussian":
            return np.array([])
        rw = np.concatenate([r / ch.scale for r, (ch, _, _) in zip(raw, self.chan)])
        return np.array([max(math.sqrt(float(rw @ rw) / self.n), 1e-12)])

    def initial_sigma(self):
        if self.noise_model == "profiled_gaussian":
            return np.array([max(f, 0.05 * sc) for sc, f in zip(self.group_scale, self.floor)])
        return np.array([0.05]) if self.noise_model == "legacy_scaled" else np.array([])


def _solve(prob: Problem, x0, lo, hi, opt: dict, fixed: dict | None = None):
    """IRLS maximum likelihood from x0. `fixed` maps parameter index -> transformed value (profiles)."""
    fixed = fixed or {}
    free_i = [i for i in range(len(x0)) if i not in fixed]
    x = np.array(x0, float)
    for i, v in fixed.items():
        x[i] = v
    sig = prob.initial_sigma()
    max_outer = opt.get("max_outer", 10) if prob.noise_model != "fixed_gaussian" else 1
    inner_ok, sig_ok, nfev = False, False, 0

    def full(z):
        xx = x.copy()
        xx[free_i] = z
        return xx

    for _ in range(max_outer):
        wts = prob.weights(sig)
        if free_i:
            res = least_squares(lambda z, w=wts: prob.weighted(full(z), w), x[free_i], bounds=(lo[free_i], hi[free_i]),
                                method="trf", x_scale=1.0, ftol=opt.get("ftol", 1e-10), xtol=opt.get("xtol", 1e-10),
                                gtol=opt.get("gtol", 1e-10), max_nfev=opt.get("max_nfev", 400))
            x = full(res.x)
            nfev += res.nfev
            inner_ok = res.status > 0
        else:
            inner_ok = True
        try:
            raw = prob.raw_residuals(x)
        except SolverFailure:
            return {"x": x, "nll": math.inf, "converged": False, "sigma": sig, "nfev": nfev, "solver_failed": True}
        new = prob.sigma_hat(raw)
        sig_ok = prob.noise_model == "fixed_gaussian" or bool(np.all(np.abs(np.log(new / sig)) < 1e-4))
        sig = new
        if sig_ok:
            break
    nll = prob.nll(raw, sig)
    return {"x": x, "nll": nll, "converged": bool(inner_ok and sig_ok), "sigma": sig, "nfev": nfev, "solver_failed": False}


def seed_from(material: str) -> int:
    import hashlib

    return int(hashlib.sha256(material.encode()).hexdigest()[:15], 16)


def multistart(prob: Problem, protocol: dict, seed: int) -> dict:
    opt = protocol.get("optimizer", {})
    n_starts = int(opt.get("n_starts", 12))
    tol = float(opt.get("replicate_tol_nll", 0.01))
    lo, hi = prob.c.tbounds()
    d = prob.c.n_free
    if d:
        sampler = qmc.LatinHypercube(d=d, seed=np.random.default_rng(seed))
        starts = qmc.scale(sampler.random(n_starts), lo, hi)
        starts = np.clip(starts, lo + 1e-9 * (hi - lo), hi - 1e-9 * (hi - lo))
    else:
        starts = np.zeros((1, 0))
    runs = []
    budget_hit = False
    prob.enforce_budget = True
    try:
        for i, x0 in enumerate(starts):
            try:
                r = _solve(prob, x0, lo, hi, opt)
            except FitBudgetExceeded:
                budget_hit = True  # remaining starts are skipped; recorded below
                break
            r["start"] = i
            runs.append(r)
    finally:
        prob.enforce_budget = False
    finite = [r for r in runs if math.isfinite(r["nll"])]
    summary = {"n_starts": len(runs), "n_starts_planned": len(starts), "n_finite": len(finite), "seed": seed,
               "budget_exhausted": budget_hit, "max_ode_solves_per_fit": prob.max_solves, "max_rhs_evals": prob.max_rhs,
               "nll_by_start": [None if not math.isfinite(r["nll"]) else round(r["nll"], 6) for r in runs],
               "converged_by_start": [r["converged"] for r in runs]}
    if budget_hit:
        summary["note"] = (f"compute budget exhausted after {len(runs)} of {len(starts)} starts "
                           f"({prob.max_solves} ODE solves); a numerical limit, not evidence against the chemistry")
    if not finite:
        return {"status": NONCONVERGENCE if budget_hit else SOLVER_FAILURE, "summary": summary, "best": None}
    conv = [r for r in finite if r["converged"]]
    best_any = min(finite, key=lambda r: r["nll"])
    at_best = [r for r in finite if r["nll"] - best_any["nll"] <= tol + 1e-9 * abs(best_any["nll"])]
    # The optimum is the lowest NLL reached, provided it is trustworthy: met the formal criteria (least-squares
    # termination and stable sigma), or was reached independently by at least two starts. Replication is direct
    # evidence of a minimum; preferring a formally converged but clearly worse start would report a wrong optimum.
    if best_any["converged"] or len(at_best) >= 2:
        best = min(at_best, key=lambda r: (not r["converged"], r["nll"]))
        summary["replicates"] = len(at_best)
        summary["replicates_formally_converged"] = sum(1 for r in at_best if r["converged"])
        summary["best_start"] = best["start"]
        if not best["converged"]:
            summary["formally_converged"] = False
            summary["note"] = summary.get("note", "") + ("; " if summary.get("note") else "") + \
                (f"optimum reached by {len(at_best)} starts that stopped on the evaluation budget or sigma tolerance; "
                 "accepted because replicated")
        return {"status": FITTED, "summary": summary, "best": best}
    if not conv:
        summary["note"] = summary.get("note", "") + ("; " if summary.get("note") else "") + \
            "no start met the convergence criteria and the lowest NLL was not replicated"
        return {"status": NONCONVERGENCE, "summary": summary, "best": best_any}
    best = min(conv, key=lambda r: r["nll"])
    summary["replicates"] = int(sum(1 for r in finite if r["nll"] - best["nll"] <= tol + 1e-9 * abs(best["nll"])))
    summary["best_start"] = best["start"]
    summary["warning"] = (f"a single unconverged start reached lower NLL ({best_any['nll']:.4f} vs {best['nll']:.4f}) "
                          "without replication; reported optimum may not be global")
    return {"status": FITTED, "summary": summary, "best": best}


# ------------------------------------------------------------------ diagnostics
def jacobian(prob: Problem, x, sig, h=1e-4):
    lo, hi = prob.c.tbounds()
    wts = prob.weights(sig)
    J = np.zeros((prob.n, len(x)))
    for i in range(len(x)):
        a, b = x.copy(), x.copy()
        up, dn = min(h, hi[i] - x[i]), min(h, x[i] - lo[i])
        if up <= 0 and dn <= 0:
            continue
        a[i] += up
        b[i] -= dn
        J[:, i] = (prob.weighted(a, wts) - prob.weighted(b, wts)) / (up + dn)
    return J


def local_uncertainty(prob: Problem, x, sig) -> dict:
    """Linearized (Fisher) uncertainty in transformed coordinates, sigma treated as known."""
    c = prob.c
    lo, hi = c.tbounds()
    if c.n_free == 0:
        return {"method": "none (no free parameters)", "params": [], "fim_condition_number": None,
                "fim_eigenvalues_rel": [], "sloppy_directions": [], "high_correlations": []}
    J = jacobian(prob, x, sig)
    fim = J.T @ J
    w, V = np.linalg.eigh(fim)
    wmax = max(float(w.max()), 1e-300)
    cov = np.linalg.pinv(fim, rcond=1e-12)
    se = np.sqrt(np.clip(np.diag(cov), 0, None))
    sens = np.linalg.norm(J, axis=0)
    params = []
    for i, p in enumerate(c.free):
        span = hi[i] - lo[i]
        at_bound = (x[i] - lo[i] < 1e-3 * span) or (hi[i] - x[i] < 1e-3 * span)
        s = float(se[i])
        scale = 1.0 if p.transform == "log10" else span / 3.0
        rel = s / scale
        if sens[i] < 1e-10:
            det = "no_sensitivity"
        elif rel < 0.15:
            det = "well_determined"
        elif rel < 0.5:
            det = "moderately_determined"
        elif rel < 1.0:
            det = "poorly_determined"
        else:
            det = "not_determined_locally"
        lo95, hi95 = x[i] - 1.96 * s, x[i] + 1.96 * s
        params.append({"name": p.name, "kind": p.kind, "transform": p.transform, "value": float(p.from_t(x[i])),
                       "theta": float(x[i]), "se_theta": s,
                       "wald_ci95": [float(p.from_t(max(lo95, lo[i]))), float(p.from_t(min(hi95, hi[i])))],
                       "wald_ci95_clipped_at_bounds": bool(lo95 < lo[i] or hi95 > hi[i]),
                       "at_bound": bool(at_bound), "determinacy": det})
    sloppy = []
    for k in range(len(w)):
        if w[k] < 1e-6 * wmax:
            load = {c.free[i].name: round(float(V[i, k]), 3) for i in range(len(x)) if abs(V[i, k]) > 0.3}
            sloppy.append({"eigenvalue_rel": float(w[k] / wmax), "combination": load})
    corr = []
    d = np.sqrt(np.clip(np.diag(cov), 1e-300, None))
    C = cov / np.outer(d, d)
    for i in range(len(x)):
        for j in range(i + 1, len(x)):
            if abs(C[i, j]) > 0.95:
                corr.append({"pair": [c.free[i].name, c.free[j].name], "r": round(float(C[i, j]), 3)})
    wmin = float(w.min())
    return {"method": "local Fisher information at the MLE (linearized, sigma fixed at its estimate); "
                      "a screening diagnostic, not a guarantee",
            "params": params, "fim_condition_number": float(wmax / wmin) if wmin > 0 and math.isfinite(wmax / wmin) else None,
            "fim_singular": not (wmin > 0),
            "fim_eigenvalues_rel": [float(v / wmax) for v in w], "sloppy_directions": sloppy, "high_correlations": corr}


def _runs_test(r):
    s = np.sign(r)
    s = s[s != 0]
    n = len(s)
    if n < 5:
        return None
    n1, n2 = int((s > 0).sum()), int((s < 0).sum())
    if n1 == 0 or n2 == 0:
        return 0.0
    runs = 1 + int(np.sum(s[1:] != s[:-1]))
    mu = 2 * n1 * n2 / n + 1
    var = 2 * n1 * n2 * (2 * n1 * n2 - n) / (n * n * (n - 1))
    if var <= 0:
        return None
    z = (runs - mu) / math.sqrt(var)
    return float(2 * norm.cdf(-abs(z)))


def residual_diagnostics(prob: Problem, x, sig) -> dict:
    raw = prob.raw_residuals(x)
    wts = prob.weights(sig)
    out, reasons = {}, []
    for (ch, _, _), label, r, w in zip(prob.chan, prob.chan_label, raw, wts):
        z = r / w
        lag1 = float(np.corrcoef(z[:-1], z[1:])[0, 1]) if len(z) > 3 and np.std(z[:-1]) > 0 and np.std(z[1:]) > 0 else None
        p = _runs_test(r)
        out[label] = {"t_min": ch.t.tolist(), "observed": ch.y.tolist(), "predicted": (ch.y + r).tolist(),
                        "residual": r.tolist(), "standardized": z.tolist(), "rmse": float(np.sqrt(np.mean(r ** 2))),
                        "max_abs_standardized": float(np.max(np.abs(z))), "runs_test_p": p, "lag1_autocorr": lag1}
        if p is not None and p < 0.05:
            reasons.append(f"{label}: residual signs cluster (runs test p={p:.3f})")
        if lag1 is not None and len(z) >= 8 and lag1 > 0.5:
            reasons.append(f"{label}: residuals are serially correlated (lag-1 r={lag1:.2f})")
    return {"channels": out, "adequacy": "poor" if reasons else "no_systematic_misfit_detected", "adequacy_reasons": reasons,
            "adequacy_rule": "poor if any channel has runs-test p < 0.05, or lag-1 autocorrelation > 0.5 with >= 8 points "
                             "(heuristics with low power at 7-18 points per channel; with a profiled sigma, standardized "
                             "residuals are bounded by sqrt(n), so their size is not used)"}


def profile_likelihood(prob: Problem, x_hat, nll_hat, protocol: dict, names: list[str] | None = None) -> dict:
    """Profile each named parameter: refit the others on a grid, report the 95% interval (delta NLL = 1.92).

    Steps grow geometrically from a small first step, so sharp and flat profiles are both resolved; interval ends are
    linearly interpolated between the last grid point inside and the first outside the threshold.
    """
    opt = dict(protocol.get("optimizer", {}))
    popt = protocol.get("profile", {})
    step0 = popt.get("first_step_log10", 0.02)
    growth = popt.get("growth", 1.6)
    max_steps = popt.get("max_steps", 16)
    thr = 0.5 * 3.841458820694124
    lo, hi = prob.c.tbounds()
    out = {}
    for i, p in enumerate(prob.c.free):
        if names is not None and p.name not in names:
            continue
        st0 = step0 if p.transform == "log10" else popt.get("first_step_linear_frac", 0.005) * (hi[i] - lo[i])
        pts = [(float(x_hat[i]), 0.0)]
        ends, ci, unreliable = {}, {}, {}
        for direction in (+1, -1):
            x = x_hat.copy()
            crossed = False
            prev = (float(x_hat[i]), 0.0)
            st = st0
            for _ in range(max_steps):
                v = x[i] + direction * st
                at_edge = v >= hi[i] or v <= lo[i]
                v = min(max(v, lo[i]), hi[i])
                r = _solve(prob, x, lo, hi, opt, fixed={i: v})
                if not r["converged"] or not math.isfinite(r["nll"]):
                    # an unreliable inner fit must not masquerade as a likelihood rise
                    unreliable[direction] = float(v)
                    break
                d = r["nll"] - nll_hat
                pts.append((float(v), float(d)))
                if d > thr:
                    crossed = True
                    if math.isfinite(d) and d != prev[1]:
                        ci[direction] = prev[0] + (thr - prev[1]) * (v - prev[0]) / (d - prev[1])
                    else:
                        ci[direction] = v
                    break
                x = r["x"]
                prev = (float(v), float(d))
                st *= growth
                if at_edge:
                    break
            ends[direction] = crossed
            if not crossed:
                ci[direction] = prev[0]
        pts.sort()
        both = ends[1] and ends[-1]
        cls = "identifiable" if both else ("one_sided" if (ends[1] or ends[-1]) else "flat_within_bounds")
        if unreliable and not both:
            cls = "inconclusive_numerics"
        lo_t, hi_t = min(ci[-1], ci[1]), max(ci[-1], ci[1])
        out[p.name] = {"transform": p.transform, "mle": float(p.from_t(x_hat[i])), "grid_theta": [v for v, _ in pts],
                       "delta_nll": [d for _, d in pts], "classification": cls,
                       "ci95_theta": [lo_t, hi_t], "ci95": [float(p.from_t(lo_t)), float(p.from_t(hi_t))],
                       "ci95_note": "an end that is not bounded stops at the protocol bound or the last grid point",
                       "upper_bounded": ends[1], "lower_bounded": ends[-1],
                       "min_delta_nll": float(min(d for _, d in pts)),
                       "better_optimum_found": bool(min(d for _, d in pts) < -0.01),
                       "stopped_by_unconverged_refit_at_theta": unreliable or None}
    return {"method": "profile likelihood (other parameters and sigma re-optimized at each grid point; threshold delta "
                      "NLL = 1.92, chi-square(1) 95%)", "params": out}


def dense_grid(tmax: float, data_t) -> np.ndarray:
    lin = np.linspace(0, tmax, 120)
    geo = np.geomspace(max(tmax / 1e3, 0.1), tmax, 120)
    return np.unique(np.concatenate([[0.0], lin, geo, np.asarray(data_t, float)]))


def fit(prob: Problem, protocol: dict, seed: int) -> dict:
    t0, c0 = time.process_time(), time.perf_counter()
    ms = multistart(prob, protocol, seed)
    out = {"status": ms["status"], "multistart": ms["summary"]}
    best = ms["best"]
    if ms["status"] != FITTED:
        if best is not None:
            out["best_unconverged"] = {"nll": best["nll"], "theta": best["x"].tolist()}
        out["timing"] = {"cpu_s": time.process_time() - t0, "wall_s": time.perf_counter() - c0,
                         "n_ode_solves": prob.n_ode, "n_ode_failures": prob.n_ode_fail}
        return out
    x, sig, nll = best["x"], best["sigma"], best["nll"]
    k = prob.c.n_free + prob.n_sigma_params
    n = prob.n
    aicc = 2 * k + 2 * nll + (2 * k * (k + 1) / (n - k - 1) if n - k - 1 > 0 else math.inf)
    out.update({
        "theta": x.tolist(), "nll": nll, "n_obs": n, "k_kinetic": prob.c.n_free, "k_noise": prob.n_sigma_params, "k_total": k,
        "aic": 2 * k + 2 * nll, "aicc": aicc, "bic": k * math.log(n) + 2 * nll,
        "noise_model": prob.noise_model,
        "sigma": ({g: float(s) for g, s in zip(prob.groups, sig)} if prob.noise_model == "profiled_gaussian"
                  else ({"shared_scaled": float(sig[0])} if prob.noise_model == "legacy_scaled" else {})),
        "sigma_at_floor": ([g for g, s, f in zip(prob.groups, sig, prob.floor) if s <= f * (1 + 1e-9)]
                           if prob.noise_model == "profiled_gaussian" else []),
    })
    out["uncertainty"] = local_uncertainty(prob, x, sig)
    out["residuals"] = residual_diagnostics(prob, x, sig)
    trajs = {}
    for pi, part in enumerate(prob.parts):
        tg = dense_grid(float(prob.part_t[pi].max()), prob.part_t[pi])
        Y = prob.trajectories(x, tg, part=pi)
        trajs[part.dataset_id] = {"t_min": tg.tolist(), "species": {s: Y[i].tolist() for i, s in enumerate(prob.c.species)},
                                  "T_C": part.conditions.T_C}
    first = trajs[prob.parts[0].dataset_id]
    out["trajectory"] = {"t_min": first["t_min"], "species": first["species"]}
    if prob.joint:
        out["trajectories"] = trajs
    out["timing"] = {"cpu_s": time.process_time() - t0, "wall_s": time.perf_counter() - c0,
                     "n_ode_solves": prob.n_ode, "n_ode_failures": prob.n_ode_fail}
    return out
