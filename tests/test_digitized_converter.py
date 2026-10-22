import json
import shutil
import sys

import numpy as np

from nernstwork import simulate


def test_converter_roundtrip(root, validator, tmp_path):
    sys.path.insert(0, str(root / "scripts"))
    import digitized_to_dataset as d

    src = root / "data/digitized_inputs/katsounaros2012_fig1"
    shutil.copy(src / "meta.json", tmp_path / "meta.json")
    w = json.loads((root / "worlds/W3_katsounaros_hidden_intermediate.json").read_text())
    t = np.array([0, 31, 59, 91, 120, 149, 180.0])  # jittered clicks, should snap
    tr = simulate(w["ground_truth"], {"NO3": 500.0}, np.array([0, 30, 60, 90, 120, 150, 180.0]), E_V=-1.2, pH=14.0)
    for sp in ("NO3", "NO2", "N2", "N2O", "NH3"):
        rows = "x,y\n" + "\n".join(f"{a},{b / 1000.0}" for a, b in zip(t, tr[sp]))
        (tmp_path / f"{sp}.csv").write_text(rows)
    ds = d.build(tmp_path)
    assert not list(validator("dataset.schema.json").iter_errors(ds))
    assert ds["series"][0]["t_min"] == [0, 30, 60, 90, 120, 150, 180]
    cl = ds["quality"]["n_closure"]["fraction"]
    assert min(cl) < 0.85 and max(cl) <= 1.001  # hidden X shows up as an N-closure deficit


def test_real_katsounaros_fig1_digitization(root, validator):
    """Daniel's WebPlotDigitizer export (unified CSV) converts cleanly and sits near published model B."""
    sys.path.insert(0, str(root / "scripts"))
    import digitized_to_dataset as d

    ds = d.build(root / "data/digitized_inputs/katsounaros2012_fig1")
    assert not list(validator("dataset.schema.json").iter_errors(ds))
    assert [s["species"] for s in ds["series"]] == ["NO3", "NO2", "N2", "N2O", "NH3"]
    assert all(s["t_min"] == [0, 30, 60, 90, 120, 150, 180] for s in ds["series"])
    assert ds["series"][0]["y"][0] == 500.0 and ds["series"][1]["y"][0] == 0.0
    w = json.loads((root / "worlds/W3_katsounaros_hidden_intermediate.json").read_text())
    tg = simulate(w["ground_truth"], {"NO3": 500.0}, np.array(ds["series"][0]["t_min"]), E_V=-1.2, pH=14.0)
    for s in ds["series"]:
        rmse = np.sqrt(np.mean((np.array(s["y"]) - tg[s["species"]]) ** 2))
        assert rmse < 25.0, (s["species"], rmse)  # about 5% of c0: model B was fit to these points
    assert 0.65 < min(ds["quality"]["n_closure"]["fraction"]) < 0.85  # hidden N shows as closure deficit


def _build(root, folder):
    sys.path.insert(0, str(root / "scripts"))
    import digitized_to_dataset as d

    return d.build(root / "data/digitized_inputs" / folder)


def test_katsounaros2008_fig2(root, validator):
    ds = _build(root, "katsounaros2008_fig2")
    assert not list(validator("dataset.schema.json").iter_errors(ds))
    assert [s["species"] for s in ds["series"]] == ["NO3", "NO2", "NH3", "N2O", "N2"]  # 'Ag/AgCl' is not a species
    q = ds["quality"]
    loss = dict(zip(q["reported_n_loss"]["t_min"], q["reported_n_loss"]["y"]))
    assert max(loss.values()) > 250 and loss[0] == 0.0 and loss[210] == 0.0  # negatives clamped to 0
    for s in ds["series"]:
        assert min(s["y"]) >= 0 and min(s["t_min"]) >= 0
    # our own closure deficit agrees with the authors' plotted loss of mass balance
    for t, f in zip(q["n_closure"]["t_min"], q["n_closure"]["fraction"]):
        assert abs((1 - f) * 1000.0 - loss[t]) < 30.0, (t, f, loss[t])
    n2 = ds["series"][4]
    assert abs(n2["y"][-1] - 835.3) < 1.0  # x2 per-molecule conversion applied


def test_polatides2005_fig3_and_published_scheme(root, validator):
    ds = _build(root, "polatides2005_fig3")
    assert not list(validator("dataset.schema.json").iter_errors(ds))
    assert {"noisy", "units_unverified"} <= set(ds["quality"]["flags"])
    assert 0.9 < min(ds["quality"]["n_closure"]["fraction"]) and max(ds["quality"]["n_closure"]["fraction"]) < 1.15
    from scipy.integrate import solve_ivp

    t = np.array(ds["series"][0]["t_min"])
    obs = {s["species"]: np.array(s["y"]) for s in ds["series"]}

    def nh3(k2_s):  # printed scheme: NO3->NO2 (k1), NO2->NH3 (k2), 2NO2->N2 (k3, L/mol/s); mM and min
        k1, k2, k3 = 4.9e-4 * 60, k2_s * 60, 7.66e-3 * 60 / 1000
        f = lambda _t, y: [-k1 * y[0], k1 * y[0] - k2 * y[1] - 2 * k3 * y[1] ** 2, k2 * y[1], k3 * y[1] ** 2]
        return solve_ivp(f, (0, 120), [50, 0, 0, 0], t_eval=t, rtol=1e-9, atol=1e-11).y[2]

    assert abs(nh3(1.76e-4)[-1] - obs["NH3"][-1]) < 5.0  # corrected exponent reproduces the figure
    assert nh3(1.76e-5)[-1] < 0.25 * obs["NH3"][-1]  # printed exponent does not


def test_wang2025_figS18_sigma_abs(root, validator):
    ds = _build(root, "wang2025_figS18_rtio2cu2o")
    assert not list(validator("dataset.schema.json").iter_errors(ds))
    by = {s["species"]: s for s in ds["series"]}
    assert by["NO3"]["y"][0] == 3.5697 and by["NH3"]["y"][0] == 0.0  # pinned c0, mg N/L -> mM-N
    assert abs(by["NH3"]["y"][-1] - 45.053 * 0.0713944) < 1e-3
    # per-point error bars carried in mM-N; null where the bar was not readable
    assert by["NO3"]["sigma"][0] is None and abs(by["NO3"]["sigma"][1] - 4.46 * 0.0713944) < 1e-4
    assert by["NH3"]["sigma"][-1] is None and len(by["NO2"]["sigma"]) == 7
    assert 0.88 < min(ds["quality"]["n_closure"]["fraction"]) < 0.92  # about 4.5 mg N/L unaccounted
