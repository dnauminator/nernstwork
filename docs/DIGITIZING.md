# Digitizing a figure: the convention

One folder per figure under `data/digitized_inputs/<authorYEAR_figN>/`:

- `wpd_datasets.csv`: the unified WebPlotDigitizer export, left exactly as exported.
- `meta.json`: copy `data/digitized_inputs/katsounaros2012_fig1/meta.json` and edit it.
- Output: `python scripts/digitized_to_dataset.py data/digitized_inputs/<folder> data/real` writes `data/real/<id>.json`.

## The CSV structure

Name each WebPlotDigitizer dataset by its species id (`NO3`, `NO2`, `NH3`, `N2`, `N2O`, ...). The export then looks like this:

    NO3,,NO2,,N2,,N2O,,NH3,
    X,Y,X,Y,X,Y,X,Y,X,Y
    0.46,0.5,0.30,0.0010,0.13,0.0010,...
    30.2,0.2508,30,0.1073,...

Row 1 holds one dataset name per X/Y pair (second cell of the pair blank). Row 2 is the X,Y header. Data start on row 3. Datasets may have different lengths; shorter ones leave blanks. If a dataset name is not a species id (for example "Nitrate"), map it in `meta.json` with `"name_map": {"Nitrate": "NO3"}`.

## Negative values and non-species datasets

The converter clamps any negative digitized time or concentration to 0 (click noise near the axes). A dataset in the export that is not a species, for example the authors' plotted loss of mass balance, is declared in `meta.json` with `"derived_series": {"<export name>": "reported_n_loss"}` and stored under `quality.reported_n_loss`, never as a series.

## What to set in meta.json

- `to_mM_N`: factor from the plotted unit to mM-N (1000 for mol/L). Override per species where the paper plots molecules rather than N atoms: N2 and N2O need 2.0 in both Katsounaros 2008 and Polatides 2005, but not in Katsounaros 2012, which plots N-equivalents.
- `n_basis_note`: say how you established the N basis (closure check, the paper's stated product distribution, or the text).
- `t_grid_min`: the nominal sampling times; clicks within `snap_tol_min` (default 5) snap to them.
- `pin_t0_to_c0`: true to set t = 0 points to the stated initial concentrations (removes click noise at the axis).
- `conditions` (catalyst, electrolyte, potential as reported, pH, `c0_mM_N`) and `provenance` (citation, figure). Leave `potential_V_vs_RHE` null unless you converted it.
- `sigma`: optional relative error per species if the figure has error bars you want to carry.
- `sigma_abs`: optional absolute error per point instead, in plotted units keyed by nominal time (`{"NO3": {"30": 4.46}}`), for error bars read point by point; times without an entry get `null`.

## Axis calibration checklist (the usual source of error)

Calibrate on tick marks at both ends of each axis. Check whether the y axis is in mol/L, mM, ug/mL or percent, and whether N2 and N2O are plotted per molecule or per N atom (the closure check at the end tells you: observed species should never sum to more than the initial N). Time may be in hours.

## Verification

Overlay the published fit or model on your points (see `data/digitized_inputs/katsounaros2012_fig1/overlay_vs_modelB.png`) and compare with the original figure. Set `provenance.verified_against_figure` to true only after that.
