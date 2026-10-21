"""Synthetic datasets from a known mechanism, for correctness tests of the pipeline (never evidence of discovery).

Noise follows SPEC section 6: observed = true * (1 + N(0, rel)) + N(0, abs), clipped at 0, seeded.
"""
from __future__ import annotations

import numpy as np

from .mechanism import simulate


def synthetic_dataset(mech: dict, c0: dict, times, observed: list[str], rel=0.03, abs_mM=0.2, seed=0,
                      E_V=-0.6, pH=7.0, ds_id="synthetic") -> dict:
    t = np.asarray(times, float)
    tr = simulate(mech, c0, t, E_V=E_V, pH=pH)
    rng = np.random.default_rng(seed)
    series = []
    for s in observed:
        y = tr[s] * (1 + rng.normal(0, rel, len(t))) + rng.normal(0, abs_mM, len(t))
        y = np.clip(y, 0, None)
        y[t == 0] = c0.get(s, 0.0)
        series.append({"species": s, "t_min": t.tolist(), "y": [round(float(v), 6) for v in y],
                       "reported_unit": "mM-N (simulated)", "conversion": "none"})
    total0 = sum(c0.values())
    frac = [round(float(sum(se["y"][i] for se in series) / total0), 4) for i in range(len(t))]
    return {"id": ds_id, "provenance": {"source_type": "simulated", "extraction": "nernstwork.synthetic",
                                        "notes": f"simulated from mechanism {mech['id']} (seed {seed}, rel {rel}, abs {abs_mM})"},
            "conditions": {"potential_V_vs_RHE": E_V, "pH": pH, "c0_mM_N": c0},
            "series": series, "quality": {"n_closure": {"t_min": t.tolist(), "fraction": frac}, "flags": []}}
