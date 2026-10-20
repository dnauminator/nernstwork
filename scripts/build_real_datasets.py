#!/usr/bin/env python3
"""Convert time-course sheets from the Nat. Commun. 2025 MoS2 Source Data workbook
into nernstwork dataset JSON.

Usage:
    python scripts/build_real_datasets.py PATH/TO/41467_2025_60671_MOESM5_ESM.xlsx data/real

The workbook is NOT committed to the repo (size, licence). Download it from the paper's
Source Data link (doi:10.1038/s41467-025-60671-y) and pass the local path.

Conventions
-----------
* State variables are mM of nitrogen (mM-N). The paper reports ug mL-1 of N for NO3-, NO2-
  and NH4+ ("NO3--N", "NO2--N", "NH4+-N" in SI eqs 6-7; nitrate "1400 ug mL-1 NO3--N" = 100 mM).
* mM-N = (ug N / mL) / 14.007.
* NH4+/NH3 is stored under the id "NH3" (lumped).
"""
import json
import sys
from pathlib import Path

import openpyxl

N_MOLAR_MASS = 14.007  # g/mol

DOI = "10.1038/s41467-025-60671-y"
CITATION = (
    "Liao W., Wang J., et al. 'Near-Unity Nitrate to Ammonia conversion via reactant "
    "enrichment at the solid-liquid interface', Nat. Commun. (2025)"
)

RUNS = [
    {
        "sheet": "Supplementary Fig. 49",
        "id": "liao2025_agmos2_suppfig49",
        "catalyst": "Ag-MoS2",
        "time_unit_to_min": 1.0,
        "figure": "Supplementary Fig. 49",
        "extra_flags": [],
        "notes": (
            "Potential not stated in the Supp. Fig. 49 caption. Confirmed -0.6 V vs RHE by the dataset owner "
            "(Oct 19 2026): the values are identical to Supp. Fig. 48, which states the conditions explicitly."
        ),
        "potential_verified": True,
        "caption_catalyst_verified": True,
    },
    {
        "sheet": "Supplementary Fig. 50a",
        "id": "liao2025_wmos2_suppfig50a",
        "catalyst": "W-MoS2",
        "time_unit_to_min": 60.0,
        "figure": "Supplementary Fig. 50a",
        "extra_flags": ["unobserved_sink_suspected"],
        "notes": (
            "Catalyst assignment taken from the Supp. Fig. 50 caption ((a) W-MoS2, (b) MoS2); "
            "the sheet itself does not name the catalyst. Time column is in hours in the source."
        ),
        "potential_verified": True,
        "caption_catalyst_verified": False,
    },
    {
        "sheet": "Supplementary Fig. 50b",
        "id": "liao2025_mos2_suppfig50b",
        "catalyst": "MoS2",
        "time_unit_to_min": 60.0,
        "figure": "Supplementary Fig. 50b",
        "extra_flags": ["unobserved_sink_suspected"],
        "notes": (
            "Catalyst assignment taken from the Supp. Fig. 50 caption ((a) W-MoS2, (b) MoS2); "
            "the sheet itself does not name the catalyst. Time column is in hours in the source."
        ),
        "potential_verified": True,
        "caption_catalyst_verified": False,
    },
]

COLS = {"NO2": 1, "NO3": 2, "NH3": 3}  # column index in sheet (0 = time)


def to_mM_N(ug_per_mL):
    return None if ug_per_mL is None else ug_per_mL / N_MOLAR_MASS


def build(ws, run):
    rows = [r for r in ws.iter_rows(values_only=True)][2:]  # skip two header rows
    rows = [r for r in rows if r[0] is not None]
    t = [float(r[0]) * run["time_unit_to_min"] for r in rows]
    series = []
    for sp in ("NO3", "NO2", "NH3"):
        y = [to_mM_N(r[COLS[sp]]) for r in rows]
        series.append(
            {
                "species": sp,
                "t_min": [round(x, 4) for x in t],
                "y": [None if v is None else round(v, 4) for v in y],
                "reported_unit": "ug mL-1 as N",
                "conversion": "mM-N = ug N / mL / 14.007",
            }
        )
    totals = []
    for i in range(len(t)):
        vals = [s["y"][i] for s in series]
        totals.append(sum(v for v in vals if v is not None))
    c0 = totals[0] if totals[0] > 0 else None
    # c0 for nitrate comes from the first nitrate point
    c0_nitrate = series[0]["y"][0]
    closure = [round(x / c0_nitrate, 4) for x in totals]
    flags = list(run["extra_flags"])
    if not run["potential_verified"]:
        flags.append("potential_unverified")
    if run["extra_flags"] == [] and min(closure) < 0.97:
        flags.append("noisy")
    return {
        "id": run["id"],
        "provenance": {
            "source_type": "source_data",
            "doi": DOI,
            "citation": CITATION,
            "figure": run["figure"],
            "file": "41467_2025_60671_MOESM5_ESM.xlsx",
            "sheet": run["sheet"],
            "extraction": "scripts/build_real_datasets.py",
            "notes": run["notes"],
            "verified_against_figure": False,
        },
        "conditions": {
            "catalyst": run["catalyst"],
            "electrolyte": "0.5 M K2SO4 + 100 mM KNO3",
            "cell": "H_cell",
            "potential_V_vs_RHE": -0.6,
            "potential_as_reported": "-0.6 V vs RHE",
            "potential_mode": "potentiostatic",
            "pH": None,
            "temperature_C": None,
            "volume_mL": 60,
            "stirring": "not recorded here",
            "c0_mM_N": {"NO3": round(c0_nitrate, 4)},
            "notes": (
                "pH not reported for the electrolyte; unbuffered neutral salt, so local and bulk pH likely "
                "drift upward as hydroxide is produced. Treat pH as unknown."
            ),
        },
        "series": series,
        "quality": {
            "n_closure": {"t_min": [round(x, 4) for x in t], "fraction": closure},
            "flags": flags,
        },
    }


def main():
    xlsx, outdir = Path(sys.argv[1]), Path(sys.argv[2])
    outdir.mkdir(parents=True, exist_ok=True)
    wb = openpyxl.load_workbook(xlsx, read_only=True, data_only=True)
    for run in RUNS:
        ds = build(wb[run["sheet"]], run)
        path = outdir / f"{run['id']}.json"
        path.write_text(json.dumps(ds, indent=2) + "\n")
        cl = ds["quality"]["n_closure"]["fraction"]
        print(f"{path.name}: {len(ds['series'][0]['t_min'])} points, N closure min {min(cl):.2f} max {max(cl):.2f}")


if __name__ == "__main__":
    main()
