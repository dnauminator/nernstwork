#!/usr/bin/env python3
"""Turn a WebPlotDigitizer export into a nernstwork dataset JSON.

Usage:
    python scripts/digitized_to_dataset.py data/digitized_inputs/katsounaros2012_fig1 data/real

Input folder:
    meta.json          id, provenance, conditions, unit factor, optional time grid (template: katsounaros2012_fig1)
    wpd_datasets.csv   the unified WebPlotDigitizer export (preferred), OR one <species>.csv per species

Unified WPD CSV structure (what "Export all datasets" produces):
    row 1: dataset name in the first column of each X/Y pair, the second column blank
           NO3,,NO2,,N2,,N2O,,NH3,
    row 2: X,Y headers repeated per pair
    rows 3+: x,y pairs per dataset, datasets may have different lengths (shorter ones leave blanks)
Dataset names must equal species ids (NO3, NO2, N2, N2O, NH3, ...) or be mapped in meta["name_map"].
Name each WPD dataset by species id when you digitize; that is the whole convention.

meta.json options beyond the dataset schema:
    "to_mM_N":      {"default": 1000.0}  multiply digitized y by this (1000 for mol/L); per-species overrides allowed
    "t_grid_min":   [0, 30, ...]        snap digitized times to the nominal sampling times
    "snap_tol_min": 5                   snapping tolerance (default 5)
    "pin_t0_to_c0": true                at t=0 set y to conditions.c0_mM_N[species] (0 if absent); removes click noise
    "sigma":        {"NO3": 0.05}       optional relative 1-sigma per species
    "sigma_abs":    {"NO3": {"30": 4.46}}  optional absolute 1-sigma per point in plotted units, keyed by nominal time
                    (for example error-bar half-lengths read off the figure); converted with to_mM_N, null where absent
    "name_map":     {"Nitrate": "NO3"}  map WPD dataset names to species ids
    "derived_series": {"Ag/AgCl": "reported_n_loss"}  datasets that are not species (here: the authors' plotted
                    loss of mass balance); stored under quality.reported_n_loss, never as a series
    "n_basis_note": "..."               how per-molecule vs per-N-atom units were established
Negative digitized times or concentrations are clamped to 0 (axis-click noise near the origin).
Output is never marked verified: set provenance.verified_against_figure by hand after overlaying the fit.
"""
import csv
import json
import sys
from pathlib import Path


def read_unified(path):
    rows = list(csv.reader(open(path, newline="")))
    names = rows[0]
    out = {}
    for c in range(0, len(names), 2):
        name = names[c].strip()
        if not name:
            continue
        pts = []
        for r in rows[2:]:
            if c + 1 >= len(r) or not r[c].strip() or not r[c + 1].strip():
                continue
            try:
                pts.append((float(r[c]), float(r[c + 1])))
            except ValueError:
                continue
        out[name] = sorted(pts)
    return out


def read_pair(path):
    pts = []
    for row in csv.reader(open(path)):
        try:
            pts.append((float(row[0]), float(row[1])))
        except (ValueError, IndexError):
            continue
    return sorted(pts)


def load_points(folder, meta):
    unified = folder / "wpd_datasets.csv"
    nm = meta.get("name_map", {})
    if unified.exists():
        raw = read_unified(unified)
        return {nm.get(k, k): v for k, v in raw.items()}
    return {sp: read_pair(folder / f"{sp}.csv") for sp in meta["species"]}


def build(folder):
    folder = Path(folder)
    meta = json.loads((folder / "meta.json").read_text())
    pts_by_sp = load_points(folder, meta)
    derived = meta.get("derived_series", {})
    species = meta.get("species") or [k for k in pts_by_sp if k not in derived]
    missing = [s for s in species if not pts_by_sp.get(s)]
    if missing:
        raise SystemExit(f"no digitized points for: {missing}. Found datasets: {list(pts_by_sp)}")
    factors = meta.get("to_mM_N", {"default": 1000.0})
    grid, tol = meta.get("t_grid_min"), meta.get("snap_tol_min", 5.0)
    c0 = meta["conditions"]["c0_mM_N"]
    series = []
    for sp in species:
        f = factors.get(sp, factors["default"])
        t, y = [], []
        for x, v in pts_by_sp[sp]:
            if grid:
                g = min(grid, key=lambda q: abs(q - x))
                x = g if abs(g - x) <= tol else x
            x = round(max(x, 0.0), 3)
            val = round(max(v * f, 0.0), 3)
            if meta.get("pin_t0_to_c0") and x == 0:
                val = float(c0.get(sp, 0.0))
            t.append(x)
            y.append(val)
        s = {"species": sp, "t_min": t, "y": y, "reported_unit": meta.get("reported_unit", "mol L-1"),
             "conversion": f"mM-N = digitized y * {f}"}
        rel = meta.get("sigma", {}).get(sp)
        ab = meta.get("sigma_abs", {}).get(sp)
        if rel is not None and ab is not None:
            raise SystemExit(f"{sp}: give sigma (relative) or sigma_abs (per point), not both")
        if rel is not None:
            s["sigma"] = [round(rel * v, 3) for v in y]
        elif ab is not None:
            s["sigma"] = [round(ab[f"{tt:g}"] * f, 4) if f"{tt:g}" in ab else None for tt in t]
        series.append(s)
    quality_extra = {}
    for name, kind in derived.items():
        if kind != "reported_n_loss":
            raise SystemExit(f"unknown derived series kind {kind}")
        f = factors.get(name, factors["default"])
        tl, yl = [], []
        for x, v in pts_by_sp[name]:
            if grid:
                g = min(grid, key=lambda q: abs(q - x))
                x = g if abs(g - x) <= tol else x
            tl.append(round(max(x, 0.0), 3))
            yl.append(round(max(v * f, 0.0), 3))
        quality_extra["reported_n_loss"] = {"t_min": tl, "y": yl}
    if meta.get("n_basis_note"):
        quality_extra["n_basis_note"] = meta["n_basis_note"]
    common = sorted(set.intersection(*[set(s["t_min"]) for s in series]))
    total0 = sum(c0.values())
    frac = [round(sum(s["y"][s["t_min"].index(tt)] for s in series) / total0, 4) for tt in common]
    # meta["extraction_method"] records how the points were obtained when that was not WebPlotDigitizer
    method = meta.get("extraction_method")
    prov = dict(meta["provenance"], source_type="digitized",
                extraction=(f"{method} Converted with scripts/digitized_to_dataset.py." if method
                            else "scripts/digitized_to_dataset.py (WebPlotDigitizer unified CSV)"))
    prov.setdefault("verified_against_figure", False)
    return {"id": meta["id"], "provenance": prov, "conditions": meta["conditions"], "series": series,
            "quality": dict({"n_closure": {"t_min": common, "fraction": frac}, "flags": meta.get("flags", [])}, **quality_extra)}


if __name__ == "__main__":
    folder, out = Path(sys.argv[1]), Path(sys.argv[2])
    ds = build(folder)
    out.mkdir(parents=True, exist_ok=True)
    p = out / f"{ds['id']}.json"
    p.write_text(json.dumps(ds, indent=2) + "\n")
    cl = ds["quality"]["n_closure"]["fraction"]
    print(f"wrote {p} ({len(ds['series'])} species, closure {min(cl):.2f}-{max(cl):.2f} on {len(cl)} shared times)")
