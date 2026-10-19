import json

import numpy as np

from nernstwork import simulate, total_N


def _load(root, rel):
    return json.loads((root / rel).read_text())


def test_all_worlds_conserve_nitrogen(root):
    for p in sorted(root.glob("worlds/W*.json")):
        w = _load(root, p.relative_to(root))
        t = np.array(w["observation"]["sampling_times_min"], float)
        E = w["design_space"]["potential_V_vs_RHE"][0]
        c0 = w["design_space"]["c0_mM_N"][-1]
        traj = simulate(w["ground_truth"], {"NO3": c0}, t, E_V=E, pH=7.0)
        tot = total_N(traj)
        assert np.allclose(tot, c0, rtol=1e-5), p.name
        assert all((v > -1e-8).all() for v in traj.values()), p.name


def test_series_nitrite_peaks_then_falls(root):
    w = _load(root, "worlds/W1_series_closed.json")
    t = np.linspace(0, 400, 401)
    tr = simulate(w["ground_truth"], {"NO3": 100.0}, t, E_V=-0.6)
    i = tr["NO2"].argmax()
    assert 0 < i < len(t) - 1
    assert tr["NH3"][-1] > 95.0


def test_calibrated_world_reproduces_real_curve_shape(root):
    """W2 is calibrated to Liao Supp. Fig. 50b: N closure should sit near 0.75 at 48 h, NH3 near 65 mM-N."""
    w = _load(root, "worlds/W2_liao_sink_deactivation.json")
    d = _load(root, "data/real/liao2025_mos2_suppfig50b.json")
    t = np.array(d["series"][0]["t_min"])
    tr = simulate(w["ground_truth"], {"NO3": 100.0}, t, E_V=-0.6)
    real = {s["species"]: np.array(s["y"]) for s in d["series"]}
    for sp in ("NO3", "NH3"):
        rmse = np.sqrt(np.mean((tr[sp] - real[sp]) ** 2))
        assert rmse < 8.0, (sp, rmse)
    observed = tr["NO3"] + tr["NO2"] + tr["NH3"]
    assert 0.6 < observed[-1] / 100.0 < 0.85


def test_potential_dependence_shifts_branching(root):
    w = _load(root, "worlds/W5_potential_dependent.json")
    t = np.array([0.0, 180.0])
    lo = simulate(w["ground_truth"], {"NO3": 100.0}, t, E_V=-0.4)
    hi = simulate(w["ground_truth"], {"NO3": 100.0}, t, E_V=-0.8)
    # more negative E speeds R1 and R3 more than R2 (alpha 0.35, 0.55 vs 0.15): more sink fraction
    assert hi["NO3"][-1] < lo["NO3"][-1]
    assert hi["SINK"][-1] / max(hi["NH3"][-1] + hi["SINK"][-1], 1e-9) > lo["SINK"][-1] / max(lo["NH3"][-1] + lo["SINK"][-1], 1e-9)


def test_katsounaros_model_b_matches_eyeballed_fig1(root):
    """Coarse check against values read by eye from Katsounaros 2012 Fig. 1 (mol/L). Replace with digitized points."""
    w = _load(root, "worlds/W3_katsounaros_hidden_intermediate.json")
    t = np.array([0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0])
    tr = simulate(w["ground_truth"], {"NO3": 500.0}, t, E_V=-1.2, pH=14.0)
    eye = {  # species: {t_min: approx mM-N read from the figure}
        "NO3": {30: 250, 60: 125, 90: 85, 180: 12},
        "N2": {90: 165, 120: 248, 180: 310},
        "N2O": {120: 55, 180: 62},
        "NH3": {180: 27},
    }
    idx = {float(x): i for i, x in enumerate(t)}
    for sp, pts in eye.items():
        for tt, val in pts.items():
            assert abs(tr[sp][idx[float(tt)]] - val) < 40, (sp, tt, tr[sp][idx[float(tt)]], val)
    assert 0.2 < tr["X"].max() / 500.0 < 0.3  # hidden pool about 24% of total N
