#!/usr/bin/env python3
"""Turn the Chapman 2023 Fig. 2 colour-classification extraction into nernstwork synthesis datasets.

Usage:
    python scripts/chapman_to_dataset.py data/digitized_inputs/chapman2023_fig2 data/real

Input folder (written by scripts/extract_chapman_fig2.py, D. Naumov, commit f135e65):
    meta.json                       citation, caveats, verification_todo
    extracted_phase_fractions.csv   T_C,t_min,wt_*,tifrac_* on a 0.05 min grid, T in {700, 725, 750}
Output: one dataset per temperature, <out>/chapman2023_fig2_<T>C.json.

Basis: "mol per mol Ti", formula units per mole of total Ti. anatase, rutile and Li2TiO3 carry one Ti per formula
unit, so their amount equals their Ti fraction (tifrac_*); Li4Ti5O12 carries five, so its amount is tifrac / 5.
The extraction computed tifrac_* from the plotted weight % with nominal molar masses.

Resampling: each grid value is the mean of the extracted rows with |t - grid| <= 0.051 min (three pixel columns).
The 0.05 min columns are pixel samples of one drawn curve, not independent measurements, so using all ~200 per
panel would overstate the information in the figure. Columns before 0.3 min are unreliable (heating strip, axis
line and the vertical Li2CO3 label overlap the data, per meta.json), so the grid starts at 0.3 min and no column
with t < 0.3 min enters any grid value: the 0.3 min point is the mean of the 0.30 and 0.35 min columns only. It stops at
9.5 min for every temperature because the 750 C panel's last points are an edge artefact (at 9.75 min Li2CO3 jumps
from 0.7 to 21.9 wt % and Li4Ti5O12 jumps). There is no t = 0 point: t = 0 is the nominal initial condition
(conditions.c0), not a measurement.
Li2CO3 gets no series (its peaks vanish after about 30 s and the extraction shows only a ~1 wt % line-width strip);
it appears only in conditions.c0.
Output is never marked verified: set provenance.verified_against_figure by hand after the spot-check.
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

GRID = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0, 1.2, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 9.5]
WINDOW = 0.051  # min; three 0.05 min pixel columns centred on the grid time
T_MIN = 0.3  # min; columns before this are never used (heating strip, axis and label overlap)
COLUMNS_PER_POINT = 3
# species id -> (CSV column, Ti per formula unit, molar mass used by the extraction in g/mol)
SPECIES = {"anatase": ("tifrac_anatase", 1, 79.866), "rutile": ("tifrac_rutile", 1, 79.866),
           "Li2TiO3": ("tifrac_Li2TiO3", 1, 109.75), "Li4Ti5O12": ("tifrac_Li4Ti5O12", 5, 459.08)}
LI_PER_FU = {"Li2TiO3": 2, "Li4Ti5O12": 4}
C0 = {"anatase": 1.0, "Li2CO3": 0.4}  # 5:2 TiO2:Li2CO3 molar = 0.4 Li2CO3 per Ti
LI_SUPPLIED = 2 * C0["Li2CO3"]  # 0.8 Li per Ti
EXTRACTION_COMMIT = "f135e65"
REPORTED_UNIT = "weight % (normalised stack of Rietveld phase fractions)"


def read_rows(path):
    by_t = defaultdict(list)
    for r in csv.DictReader(open(path, newline="")):
        by_t[int(float(r["T_C"]))].append({k: float(v) for k, v in r.items()})
    return {T: sorted(rows, key=lambda r: r["t_min"]) for T, rows in sorted(by_t.items())}


def window(rows, g):
    sel = [r for r in rows if abs(r["t_min"] - g) <= WINDOW and r["t_min"] >= T_MIN - 1e-9]
    expected = COLUMNS_PER_POINT - (1 if g - WINDOW < T_MIN - 1e-9 else 0)  # 2 at the first grid time
    if len(sel) != expected:
        raise SystemExit(f"expected {expected} columns within {WINDOW} min of t = {g} (t >= {T_MIN}), "
                         f"found {[r['t_min'] for r in sel]}")
    return sel


def mean(sel, col):
    return sum(r[col] for r in sel) / len(sel)


def build_one(T, rows, meta):
    T_label = f"{T:g}"
    series = []
    for sp, (col, n_ti, M) in SPECIES.items():
        y = [round(mean(window(rows, g), col) / n_ti, 5) for g in GRID]
        conv = (f"mol per mol Ti = mean({col}) over 3 pixel columns (2 at {T_MIN} min)"
                + (f" / {n_ti}" if n_ti != 1 else ""))
        conv += f"; {col} from wt % with M = {M} g/mol, {n_ti} Ti per formula unit"
        series.append({"species": sp, "t_min": list(GRID), "y": y, "reported_unit": REPORTED_UNIT, "conversion": conv})
    y = {s["species"]: s["y"] for s in series}

    # diagnostics written into the notes (this panel only, so the 700 and 725 C files carry no 750 C numbers)
    i_pk = max(range(len(GRID)), key=lambda i: y["Li2TiO3"][i])
    used = [r for g in GRID for r in window(rows, g)]
    raw_pk = max(used, key=lambda r: r["tifrac_Li2TiO3"])
    wt_pk = max(used, key=lambda r: r["wt_Li2TiO3"])
    li = [sum(LI_PER_FU[sp] * y[sp][i] for sp in LI_PER_FU) for i in range(len(GRID))]
    i_li = max(range(len(GRID)), key=lambda i: li[i])

    prov_meta = meta["provenance"]
    citation = prov_meta["citation"].split(", doi ")[0]
    doi = prov_meta["citation"].split(", doi ")[1] if ", doi " in prov_meta["citation"] else "10.1021/jacs.3c10916"
    extraction = (
        f"Colour classification of the raster Fig. 2 image by scripts/extract_chapman_fig2.py (D. Naumov, commit "
        f"{EXTRACTION_COMMIT}; data/digitized_inputs/chapman2023_fig2/extracted_phase_fractions.csv, no manual clicking), "
        "then scripts/chapman_to_dataset.py: each grid value is the mean of the 3 extracted 0.05 min columns within "
        f"{WINDOW} min of the grid time, because the columns are pixel samples of one drawn curve and using all ~200 "
        "would overstate the information; columns before 0.3 min overlap the heating strip, axis line and Li2CO3 label, "
        "so the grid starts at 0.3 min and no column with t < 0.3 min is averaged into any value (the 0.3 min point is "
        "the mean of the 0.30 and 0.35 min columns only); the grid stops at 9.5 min for every temperature because the "
        "last columns of one panel are an edge artefact (details in the converter docstring, not repeated here so that "
        "no file carries another temperature's values); Ti fractions converted to formula units per mol Ti (Li4Ti5O12 divided by 5); no t = 0 point.")
    notes = (
        f"Not yet verified. To do (meta.json): {prov_meta['verification_todo']} "
        f"Known bias: this panel's extracted Li2TiO3 band reaches {wt_pk['wt_Li2TiO3']:.1f} wt % (at "
        f"{wt_pk['t_min']:g} min, in the columns used here) against the about 52 wt % maximum stated by the authors, a "
        "bias of about 2 wt % most likely from the 1-2 px boundary lines; treat every phase fraction as carrying about "
        "1-2 wt % systematic error. reconstruction.png in the input folder is our re-plot, not the published figure.")
    conditions = {
        "basis": "mol per mol Ti",
        "c0": dict(C0),
        "temperature_C": T,
        "potential_V_vs_RHE": None,
        "pH": None,
        "precursors": "5:2 TiO2 (anatase):Li2CO3 molar, pelletized, loaded in a capillary",
        "notes": ("Sample moved into a pre-heated hot zone; heating takes under 10 s (the 'Heating' strip in the paper's "
                  "Fig. 3, about the first 0.17 min), and t = 0 is insertion, so the sample is below temperature_C for "
                  "roughly the first 0.17 min. Atmosphere not stated. c0 is the nominal mix (0.4 Li2CO3 per Ti from the "
                  "5:2 molar ratio). Li2CO3 is not a series: the authors state its peaks are no longer distinguishable "
                  "after about 30 s, and the extraction shows only a ~1-2 wt % line-width strip to the end of the panel, "
                  "so it appears only in c0."),
    }
    basis_note = (
        "Amounts are formula units per mole of total Ti. The figure plots weight % as a normalised stack (anatase, "
        "rutile, Li4Ti5O12, Li2TiO3, Li2CO3 summing to 100); the extraction converted wt % to the fraction of Ti in "
        "each Ti-bearing phase with nominal molar masses (TiO2 79.866, Li2TiO3 109.75, Li4Ti5O12 459.08 g/mol; 1, 1, 5 "
        "Ti per formula unit), and this converter divides the Li4Ti5O12 Ti fraction by 5. Because the stack is "
        "normalised, anatase + rutile + Li2TiO3 + 5 x Li4Ti5O12 = 1 at every point by construction, so a Ti closure "
        "check cannot reveal unobserved or amorphous Ti-bearing material. Nominal molar masses were used although the "
        "authors report Li-deficient Li2-xTiO3, so the Li2TiO3 amount is approximate. In this panel the Li2TiO3 Ti "
        f"fraction peaks at {y['Li2TiO3'][i_pk]:.3f} at {GRID[i_pk]:g} min on this grid ({raw_pk['tifrac_Li2TiO3']:.3f} at "
        f"{raw_pk['t_min']:g} min in the 0.05 min columns), above the {LI_SUPPLIED / 2:.2f} that stoichiometric Li2TiO3 "
        f"allows with {LI_SUPPLIED:.1f} Li per Ti in the mix. With nominal stoichiometries (2 Li per Li2TiO3, 4 per "
        f"Li4Ti5O12) the observed phases would hold {li[i_li]:.2f} Li per Ti at {GRID[i_li]:g} min and {li[-1]:.2f} at "
        f"{GRID[-1]:g} min, against {LI_SUPPLIED:.1f} supplied: either Li2TiO3 is strongly Li-deficient, the extracted "
        "Li2TiO3 band is too wide, or the plotted fractions do not balance Li; this dataset cannot tell which.")
    return {
        "id": f"chapman2023_fig2_{T_label}C",
        "provenance": {
            "source_type": "digitized",
            "citation": citation,
            "doi": doi,
            "figure": f"Fig. 2, {T_label} C panel",
            "file": "ja3c10916.pdf (not redistributed)",
            "extraction": extraction,
            "verified_against_figure": False,
            "notes": notes,
        },
        "conditions": conditions,
        "series": series,
        "quality": {
            "flags": ["normalised_fractions", "extraction_unverified", "time_origin_uncertain"],
            "basis_note": basis_note,
        },
    }


def build(folder):
    folder = Path(folder)
    meta = json.loads((folder / "meta.json").read_text())
    by_T = read_rows(folder / "extracted_phase_fractions.csv")
    return [build_one(T, rows, meta) for T, rows in by_T.items()]


if __name__ == "__main__":
    folder, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    for ds in build(folder):
        p = out / f"{ds['id']}.json"
        p.write_text(json.dumps(ds, indent=2) + "\n")
        y = {s["species"]: s["y"] for s in ds["series"]}
        ti = [sum(y[sp][i] * SPECIES[sp][1] for sp in SPECIES) for i in range(len(GRID))]
        pk = max(y["Li2TiO3"])
        print(f"wrote {p} ({len(ds['series'])} species x {len(GRID)} times, {GRID[0]}-{GRID[-1]} min; "
              f"Li2TiO3 peak {pk:.3f} mol/mol Ti at {GRID[y['Li2TiO3'].index(pk)]} min; "
              f"Ti sum {min(ti):.4f}-{max(ti):.4f})")
