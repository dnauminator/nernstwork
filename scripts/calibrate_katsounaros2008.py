#!/usr/bin/env python3
"""Fit three candidate structures to the digitized Katsounaros 2008 Fig. 2 data (1 M nitrate, Sn, -2.8 V vs Ag/AgCl).

Usage: python scripts/calibrate_katsounaros2008.py data/real
  A: NO3 -> NO2; NO2 -> NH3, N2O, N2 directly (no hidden species)
  B: as A but NO2 -> X (hidden) -> N2 (Katsounaros 2012 model-B structure)
  B+L: B with a Langmuir-saturating nitrate step, r1 = k1 c / (1 + c/K)
Point estimates from multi-start least squares, no uncertainty; Gaussian AIC/BIC from the residual sum of squares.
Results quoted in docs/SPEC.md section 7c. N2 and N2O interpolated onto the nitrate time grid (195 min point dropped).
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import least_squares

d = json.load(open(Path(sys.argv[1]) / "katsounaros2008_fig2_sn_nacl_1M.json"))
S = {s["species"]: (np.array(s["t_min"]), np.array(s["y"])) for s in d["series"]}
grid, c0 = S["NO3"][0], 1000.0
obs = np.vstack([S["NO3"][1], S["NO2"][1], S["NH3"][1], np.interp(grid, *S["N2O"]), np.interp(grid, *S["N2"])])


def run(f, y0):
    return solve_ivp(f, (0, 210), y0, t_eval=grid, rtol=1e-9, atol=1e-9, method="LSODA").y


def sim_A(p):
    k1, k3, k4, k5 = np.exp(p)
    return run(lambda _t, y: [-k1 * y[0], k1 * y[0] - (k3 + k4 + k5) * y[1], k4 * y[1], k5 * y[1], k3 * y[1]], [c0, 0, 0, 0, 0])


def sim_B(p, lang=False):
    k1, k2, k3, k4, k5 = np.exp(p[:5])
    K = np.exp(p[5]) if lang else None

    def f(_t, y):
        r1 = k1 * y[0] / (1 + y[0] / K) if lang else k1 * y[0]
        return [-r1, r1 - (k2 + k4 + k5) * y[1], k2 * y[1] - k3 * y[2], k4 * y[1], k5 * y[1], k3 * y[2]]

    s = run(f, [c0, 0, 0, 0, 0, 0])
    return s[[0, 1, 3, 4, 5]], s[2]


def fit(sim, starts, nparams):
    best = None
    for x0 in starts:
        r = least_squares(lambda p: (sim(p) - obs).ravel(), x0, bounds=(-12, 9))
        if best is None or r.cost < best.cost:
            best = r
    n, rss = obs.size, 2 * best.cost
    print(f"{nparams} params  RMSE {np.sqrt(rss / n):5.1f} mM-N  AIC {n * np.log(rss / n) + 2 * nparams:6.1f}  "
          f"BIC {n * np.log(rss / n) + nparams * np.log(n):6.1f}  k = {np.exp(best.x).round(4)}")
    return best


print("A (no hidden species)")
fit(sim_A, [np.log([a, b, .002, .005]) for a in (.01, .02) for b in (.02, .05)], 4)
print("B (hidden X)")
rB = fit(lambda p: sim_B(p)[0], [np.log([a, b, c, .002, .005]) for a in (.01, .02) for b in (.02, .05) for c in (.01, .03)], 5)
print(f"  hidden X peak {sim_B(rB.x)[1].max():.0f} mM-N; authors' plotted loss peaks at 261 mM-N")
print("B + Langmuir nitrate step (last number is K in mM)")
fit(lambda p: sim_B(p, True)[0], [np.log([a, .05, .03, .003, .003, K]) for a in (.02, .05, .1) for K in (100, 300, 1000)], 6)
