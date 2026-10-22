#!/usr/bin/env python3
"""Raster extraction of Wang et al. 2025 (J. Hazard. Mater., doi 10.1016/j.jhazmat.2025.137174) SI Fig. S18.

Fig. S18: NO3--N, NO2--N and NH4+-N (mg L-1) against time (0-180 min) during nitrate reduction on R-TiO2/Cu2O,
filled up-triangle markers with error bars, Origin-style flat fills (no antialiasing).

Usage:
    python scripts/extract_wang2025_figS18.py <image18.tiff> data/digitized_inputs/wang2025_figS18_rtio2cu2o [--profiles]

<image18.tiff> is word/media/image18.tiff inside the SI file 1-s2.0-S030438942500086X-mmc1.docx (free download from
https://ars.els-cdn.com/content/image/1-s2.0-S030438942500086X-mmc1.docx; publisher copyright, not committed).

Method:
  1. Axes: linear fits to the outward tick-mark centres (y ticks 0..50 mg/L, x ticks 0..180 min), found as short dark
     runs beside the axis lines.
  2. Marker centre: occlusion-tolerant template match. The template is the legend's NO3 triangle (exact shape); its
     centre is the legend line's centre row, which sits at the triangle centroid (not the bounding-box centre).
     Score = template pixels of the series colour - 2 x template pixels that are white (other colours may occlude).
  3. Connecting lines: Origin draws straight segments through the data points, so a line fitted to each segment's
     pixels between markers gives an independent estimate of both end values.
  4. Value = mean of the template centre and the adjacent line-end estimates when the marker is at least 90% visible;
     otherwise (overlapped or clipped markers) the mean of the line-end estimates alone.
  5. Error bars: cap rows (17-19 px wide runs of the series colour, separated from the triangle by the 3 px bar line)
     were read by eye from the row-width profiles printed with --profiles, and are listed in CAPS below. Half-length =
     half the distance between the two cap centres, or the distance from the value to the one visible cap.
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

MARKER = {"NO3": (94, 151, 221), "NO2": (189, 212, 209), "NH3": (235, 187, 139)}
LINE = {"NO3": (169, 200, 237), "NO2": (211, 226, 224), "NH3": (232, 216, 176)}
T_MIN = [0, 30, 60, 90, 120, 150, 180]
# Cap centre rows read by eye from --profiles (top, bottom); None where the cap is hidden, clipped or inside the marker.
CAPS = {
    ("NO3", 30): (202.0, 276.0), ("NO3", 60): (325.0, 375.0), ("NO3", 90): (414.0, 435.0), ("NO3", 120): (441.0, None),
    ("NO2", 30): (433.0, 449.0), ("NO2", 60): (445.0, None), ("NO2", 90): (447.0, None),
    ("NH3", 30): (293.5, 346.5), ("NH3", 60): (181.0, 203.0), ("NH3", 90): (105.5, 146.0), ("NH3", 120): (85.5, 101.0),
    ("NH3", 150): (78.0, None),
}


def runs(idx):
    if len(idx) == 0:
        return []
    return np.split(idx, np.nonzero(np.diff(idx) > 1)[0] + 1)


def calibrate(img):
    dark = img.mean(axis=2) < 110
    ycol = int(np.argmax(dark[:, : img.shape[1] // 2].sum(axis=0)))      # left axis line column
    xrow = int(np.argmax(dark[img.shape[0] // 2:, :].sum(axis=1))) + img.shape[0] // 2  # bottom axis line row
    yt = [r.mean() for r in runs(np.nonzero(dark[:, ycol - 6:ycol - 2].all(axis=1))[0]) if len(r) <= 6]
    xt = [c.mean() for c in runs(np.nonzero(dark[xrow + 3:xrow + 7, :].all(axis=0))[0]) if len(c) <= 6]
    yt = sorted(yt)[-6:]
    xt = sorted(xt)[:7]
    if len(yt) != 6 or len(xt) != 7:
        raise SystemExit(f"tick detection failed: {len(yt)} y ticks, {len(xt)} x ticks")
    yv = np.array([50, 40, 30, 20, 10, 0.0])
    ay, by = np.polyfit(yt, yv, 1)
    ax, bx = np.polyfit(xt, np.array(T_MIN, float), 1)
    return {"y_tick_rows": yt, "x_tick_cols": xt, "mg_per_px": float(-ay), "y_of_row": (float(ay), float(by)),
            "y_tick_max_residual_mg": float(np.abs(np.polyval([ay, by], yt) - yv).max()),
            "x_tick_max_residual_min": float(np.abs(np.polyval([ax, bx], xt) - np.array(T_MIN)).max())}


def template(img, mask):
    leg = mask["NO3"][19:40, 186:213]
    tr, tc = np.nonzero(leg)
    tr, tc = tr + 19, tc + 186
    line_rows = [r for r in range(26, 38) if (img[r, 176:185].min(axis=1) < 235).sum() >= 8]
    return np.stack([tr - (min(line_rows) + max(line_rows)) / 2, tc - (tc.min() + tc.max()) / 2], axis=1)


def main():
    img = np.asarray(Image.open(sys.argv[1]).convert("RGB")).astype(float)
    outdir = Path(sys.argv[2])
    H, W, _ = img.shape
    cal = calibrate(img)
    ay, by = cal["y_of_row"]
    y_of = lambda r: ay * r + by
    row_of = lambda y: (y - by) / ay
    xt = cal["x_tick_cols"]
    white = img.min(axis=2) > 240
    mask = {k: np.linalg.norm(img - np.array(v), axis=2) < 15 for k, v in MARKER.items()}
    T = template(img, mask)
    if "--profiles" in sys.argv:
        for sp in MARKER:
            for t, cx in zip(T_MIN, xt):
                c = int(round(cx))
                prof = [f"{r}:{'+'.join(str(len(x)) for x in runs(np.nonzero(mask[sp][r, c - 12:c + 13])[0]))}"
                        for r in range(46, 462) if mask[sp][r, c - 12:c + 13].any()]
                print(sp, t, " ".join(prof))
    points = {}
    for sp in MARKER:
        lm = np.linalg.norm(img - np.array(LINE[sp]), axis=2) < 12
        ends = {t: [] for t in T_MIN}
        for i in range(len(xt) - 1):
            cols, rows = [], []
            for x in range(int(xt[i] + 14), int(xt[i + 1] - 13)):
                r = np.nonzero(lm[46:461, x])[0] + 46
                if len(r) and np.ptp(r) < 12:
                    cols.append(x)
                    rows.append(r.mean())
            if len(cols) >= 10:
                k, b = np.polyfit(cols, rows, 1)
                ends[T_MIN[i]].append(float(y_of(k * xt[i] + b)))
                ends[T_MIN[i + 1]].append(float(y_of(k * xt[i + 1] + b)))
        pts = []
        for t, cx in zip(T_MIN, xt):
            best = None
            for dc in (-1.0, -0.5, 0.0, 0.5, 1.0):
                for crow in np.arange(30, 470, 0.5):
                    rr = np.round(T[:, 0] + crow).astype(int)
                    cc = np.round(T[:, 1] + cx + dc).astype(int)
                    ok = (rr >= 0) & (rr < H) & (cc >= 0) & (cc < W)
                    hits = int(mask[sp][rr[ok], cc[ok]].sum())
                    sc = hits - 2 * int(white[rr[ok], cc[ok]].sum())
                    if best is None or sc > best[0]:
                        best = (sc, float(crow), hits)
            _, crow, hits = best
            vis = hits / len(T)
            y_tpl = float(y_of(crow))
            est = ([y_tpl] if vis >= 0.9 else []) + ends[t]
            y = float(np.mean(est)) if est else y_tpl
            top, bot = CAPS.get((sp, t), (None, None))
            if top is not None and bot is not None:
                half = (bot - top) / 2 * cal["mg_per_px"]
            elif top is not None:
                half = (row_of(y) - top) * cal["mg_per_px"]
            elif bot is not None:
                half = (bot - row_of(y)) * cal["mg_per_px"]
            else:
                half = None
            pts.append({"t_min": t, "value_mg_N_per_L": round(y, 3), "template_centre_mg": round(y_tpl, 3),
                        "template_visible_fraction": round(vis, 2), "line_end_estimates_mg": [round(v, 3) for v in ends[t]],
                        "estimates_used": len(est), "estimate_spread_mg": round(float(np.ptp(est)), 3) if len(est) > 1 else None,
                        "cap_rows_top_bottom": [top, bot],
                        "error_bar_half_length_mg": None if half is None else round(float(half), 3)})
        points[sp] = pts
    outdir.mkdir(parents=True, exist_ok=True)
    rec = {"calibration": {k: v for k, v in cal.items() if k != "y_of_row"},
           "template": {"n_px": int(len(T)), "height_px": int(np.ptp(T[:, 0]) + 1), "width_px": int(np.ptp(T[:, 1]) + 1)},
           "points": points}
    (outdir / "extracted_points.json").write_text(json.dumps(rec, indent=1) + "\n")
    with open(outdir / "wpd_datasets.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(sum([[sp, ""] for sp in MARKER], []))
        w.writerow(["X", "Y"] * len(MARKER))
        for i in range(len(T_MIN)):
            w.writerow(sum([[T_MIN[i], points[sp][i]["value_mg_N_per_L"]] for sp in MARKER], []))
    print(json.dumps(rec["calibration"]))
    for sp, pts in points.items():
        print(sp, [(p["t_min"], p["value_mg_N_per_L"], p["error_bar_half_length_mg"]) for p in pts])


if __name__ == "__main__":
    main()
