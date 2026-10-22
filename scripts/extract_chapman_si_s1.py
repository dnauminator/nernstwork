"""Extract phase abundances from the Supporting Information of Hu et al. (Chapman), JACS 145, 26545 (2023), Fig. S1.

SI Fig. S1 plots the same Rietveld results as main-text Fig. 2 as five separate line curves (wt % against seconds,
0-600 s) for 700, 725 and 750 C, instead of a stacked area. Every phase is a differently coloured line, so each curve
is read by colour. This avoids the label and boundary-line problems that corrupt the stacked figure before 0.35 min
(data/digitized_inputs/chapman2023_fig2/VERIFICATION.md).

Usage:  python scripts/extract_chapman_si_s1.py <path to ja3c10916_si_001.pdf> [out_dir]
Default out_dir: data/digitized_inputs/chapman2023_sifig_s1
The PDF is publisher-copyrighted and git-ignored; only derived numbers are written.

Output CSV has the same columns as the Fig. 2 extraction (T_C, t_min, wt_*, tifrac_*) plus wt_sum, on a 0.05 min grid.
"""
import csv
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PHASES = ["anatase", "rutile", "Li4Ti5O12", "Li2TiO3", "Li2CO3"]
COLOURS = {"anatase": (255, 0, 0), "rutile": (128, 0, 0), "Li4Ti5O12": (102, 0, 204),
           "Li2TiO3": (204, 102, 255), "Li2CO3": (3, 222, 245)}  # legend swatches in the figure
TOL = 55.0           # colour distance for a pixel to belong to a curve (the cyan line is lighter in the 725 C panel)
GAP_PX = 2           # bridge anti-aliasing gaps inside one line
MAX_INTERP_S = 15.0  # interpolate over curve segments hidden by another line up to this long
NEAR_ZERO_WT = 3.0   # a hidden segment between two near-zero values (line lying under another on the baseline) may be longer
LEGEND = (690, 190)  # only used to ignore the legend when finding the right end of the curves
MAX_JUMP_PX = 40     # largest column-to-column jump accepted when following a curve
Y_TOP_WT = 80.0      # the gray y axis spans 0-80 wt %
T_END_S = 600.0
TEMPS = (700, 725, 750)
GRID_MIN = 0.05
M = {"anatase": 79.866, "rutile": 79.866, "Li2TiO3": 109.75, "Li4Ti5O12": 459.08}
NTI = {"anatase": 1, "rutile": 1, "Li2TiO3": 1, "Li4Ti5O12": 5}


def load_panels(pdf):
    import pymupdf
    doc = pymupdf.open(str(pdf))
    page = next(p for p in doc if "Figure S1" in p.get_text())
    items = []
    for im in page.get_images():
        rect = page.get_image_rects(im[0])[0]
        pix = pymupdf.Pixmap(doc, im[0])
        if pix.n > 4:
            pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
        arr = np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w, pix.n)[:, :, :3].astype(int)
        items.append((rect.y0, arr))
    items.sort(key=lambda t: t[0])  # top to bottom: 700, 725, 750 C
    if len(items) != 3:
        raise SystemExit(f"expected 3 panel images on the Figure S1 page, found {len(items)}")
    return [a for _, a in items]


def axis_geometry(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    gray = (abs(r - g) < 10) & (abs(g - b) < 10) & (r > 120) & (r < 215)
    cols = gray[5:400, 60:100].sum(axis=0)
    x0 = 60 + int(cols.argmax())  # the gray y axis is the t = 0 line
    ys = np.nonzero(gray[:, x0])[0]
    ys = ys[ys < 410]
    return x0, int(ys.min()), int(ys.max())


def curve_y(a, colour, x0, x_last):
    """Per pixel column, the centre row of the pixel run near `colour` that continues the curve (NaN where it is hidden).

    The legend swatches and labels (upper right) use the same colours as the curves and can overlap them (the 750 C
    Li4Ti5O12 curve runs through its own legend label), so no region is masked: among the runs in a column the one
    closest to the previous column's position is taken (within MAX_JUMP_PX), else the longest run."""
    d = np.linalg.norm(a - np.array(colour)[None, None, :], axis=2) < TOL
    out = np.full(a.shape[1], np.nan)
    prev = None

    def runs_of(rows):
        runs, s, p = [], rows[0], rows[0]
        for r in rows[1:]:
            if r - p > GAP_PX:
                runs.append((s, p)); s = r
            p = r
        runs.append((s, p))
        return runs

    centre = lambda ab: 0.5 * (ab[0] + ab[1])
    for x in range(x0 + 1, x_last + 1):
        rows = np.nonzero(d[:410, x])[0]
        if len(rows) == 0:
            continue
        best = None
        if prev is not None:
            near = min(runs_of(rows), key=lambda ab: abs(centre(ab) - prev))
            if abs(centre(near) - prev) <= MAX_JUMP_PX:
                best = near
        if best is None:  # start of the curve, or a jump: take the longest run outside the legend box
            rows_f = rows[~((x >= LEGEND[0]) & (rows < LEGEND[1]))]
            if len(rows_f) == 0:
                continue
            best = max(runs_of(rows_f), key=lambda ab: ab[1] - ab[0])
        out[x] = centre(best)
        prev = out[x]
    return out


def extract(pdf):
    panels = load_panels(pdf)
    geo = [axis_geometry(a) for a in panels]
    # right end of the curves in the two full-length panels defines 600 s; the same scale is used for all three
    ends = []
    for a, (x0, _, _) in zip(panels[:2], geo[:2]):
        sat = (a.max(axis=2) - a.min(axis=2)) > 90
        sat[:LEGEND[1], LEGEND[0]:] = False
        ends.append(np.nonzero(sat[:400].any(axis=0))[0].max() - x0)
    px_per_s = float(np.mean(ends)) / T_END_S
    result = {}
    for T, a, (x0, ytop, ybot) in zip(TEMPS, panels, geo):
        x_last = min(a.shape[1] - 1, int(x0 + T_END_S * px_per_s) + 2)
        raw = {p: curve_y(a, COLOURS[p], x0, x_last) for p in PHASES}
        # zero level: anatase is fully consumed at the end of every panel
        t_px = (np.arange(a.shape[1]) - x0) / px_per_s
        late = {700: 540.0, 725: 250.0, 750: 150.0}[T]
        m = (t_px > late) & (t_px < T_END_S - 15) & ~np.isnan(raw["anatase"])
        y0 = float(np.median(raw["anatase"][m]))
        scale = (y0 - ytop) / Y_TOP_WT  # px per wt %
        wt = {p: (y0 - raw[p]) / scale for p in PHASES}
        valid = t_px >= 0
        # interpolate over hidden segments up to MAX_INTERP_S, leave longer gaps NaN
        t_all = t_px[valid]
        fill = {}
        for p in PHASES:
            v = wt[p][valid]
            good = ~np.isnan(v)
            if good.sum() < 10:
                fill[p] = np.full_like(v, np.nan)
                continue
            vi = np.interp(t_all, t_all[good], v[good])
            last = np.nonzero(good)[0].max()
            if v[last] >= NEAR_ZERO_WT:  # np.interp would hold the last value; a visible curve has ended
                vi[last + 1:] = np.nan  # (a near-zero curve lying hidden on the baseline is held)
            # mask gaps longer than MAX_INTERP_S, unless the line is hidden on the baseline (both ends near zero)
            gaps = ~good
            idx = np.nonzero(gaps)[0]
            if len(idx):
                breaks = np.split(idx, np.nonzero(np.diff(idx) > 1)[0] + 1)
                for br in breaks:
                    lo, hi = br[0] - 1, br[-1] + 1
                    ends_near_zero = (lo >= 0 and hi < len(v) and v[lo] < NEAR_ZERO_WT and v[hi] < NEAR_ZERO_WT)
                    if (t_all[br[-1]] - t_all[br[0]]) > MAX_INTERP_S and not ends_near_zero and br[-1] < len(t_all) - 1:
                        vi[br] = np.nan
            fill[p] = vi
        result[T] = {"t_s": t_all, "wt": fill, "scale_px_per_wt": scale, "y0_axis_px": ybot, "y0_anatase_px": y0,
                     "x0": x0, "t_last_s": min(T_END_S, float(t_all[~np.isnan(fill["rutile"])].max()))}
    return result, px_per_s


def grid_rows(res):
    rows = []
    for T, r in res.items():
        t_last = r["t_last_s"] / 60.0
        for g in np.arange(GRID_MIN, t_last - 1e-9, GRID_MIN):
            sel = np.abs(r["t_s"] / 60.0 - g) <= 1.6 / 60.0  # +-1.6 s: the pixel columns around each grid time
            wt = {}
            for p in PHASES:
                v = r["wt"][p][sel]
                v = v[~np.isnan(v)]
                wt[p] = float(np.mean(v)) if len(v) else float("nan")
            if any(np.isnan(list(wt.values()))):
                continue
            wt = {p: max(0.0, v) for p, v in wt.items()}
            mol = {p: wt[p] * NTI[p] / M[p] for p in M}
            tot = sum(mol.values())
            ti = {p: mol[p] / tot for p in M}
            rows.append([T, round(g, 3)] + [round(wt[p], 2) for p in PHASES] + [round(ti[p], 4) for p in M]
                        + [round(sum(wt.values()), 2)])
    return rows


def main():
    pdf = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "data/digitized_inputs/chapman2023_sifig_s1"
    out.mkdir(parents=True, exist_ok=True)
    res, px_per_s = extract(pdf)
    rows = grid_rows(res)
    header = ["T_C", "t_min"] + [f"wt_{p}" for p in PHASES] + [f"tifrac_{p}" for p in M] + ["wt_sum"]
    with open(out / "extracted_phase_fractions.csv", "w", newline="") as f:
        csv.writer(f).writerows([header] + rows)
    print(f"scale {px_per_s:.3f} px/s; {len(rows)} grid rows")
    for T, r in res.items():
        t = r["t_s"]
        li = r["wt"]["Li2TiO3"]
        k = int(np.nanargmax(li))
        sums = np.nansum(np.vstack([r["wt"][p] for p in PHASES]), axis=0)
        ok = (t > 5) & (t < r["t_last_s"] - 3)
        print(f"{T} C: axis-bottom row {r['y0_axis_px']} vs anatase baseline row {r['y0_anatase_px']:.1f}; "
              f"px/wt% {r['scale_px_per_wt']:.3f}; data to {r['t_last_s']:.0f} s; "
              f"max Li2TiO3 {li[k]:.1f} wt% at {t[k]:.0f} s; wt sum {np.nanmin(sums[ok]):.1f}-{np.nanmax(sums[ok]):.1f}")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(3, 1, figsize=(6, 9), sharex=True)
        col = {"anatase": "red", "rutile": "darkred", "Li4Ti5O12": "#6600cc", "Li2TiO3": "#cc66ff", "Li2CO3": "#03dee5"}
        for a, (T, r) in zip(ax, res.items()):
            for p in PHASES:
                a.plot(r["t_s"], r["wt"][p], color=col[p], lw=1, label=p)
            a.set_title(f"{T} C (extracted from SI Fig. S1)", fontsize=9)
            a.set_ylim(0, 80)
        ax[0].legend(fontsize=6, loc="upper right")
        ax[2].set_xlabel("t / s")
        plt.tight_layout()
        plt.savefig(out / "reconstruction.png", dpi=80)
    except ImportError:
        pass


if __name__ == "__main__":
    main()
