"""Extract phase-fraction curves from Hu et al. (Chapman), JACS 145, 26545 (2023), Figs. 2 and 3.

The figures are raster images inside the PDF (flat colours, no vector data), so the curves are read by
colour classification instead of manual clicking:

* Fig. 2 (700, 725, 750 C): stacked areas of weight % versus time. Each pixel column is classified into
  the five phase colours; the five stacked boundaries give the weight fractions. A Hampel-style filter
  removes isolated bad columns caused by the in-figure label text.
* Fig. 3 (482 C): the Li2TiO3 curve in arbitrary units. The y axis has no ticks, so values are reported
  relative to the plot height only.

Usage:  python scripts/extract_chapman_fig2.py <path to ja3c10916.pdf> [out_dir]
The PDF is publisher-copyrighted and git-ignored; only the derived numbers are written.
Default out_dir: data/digitized_inputs/chapman2023_fig2
"""
import csv
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import median_filter

ROOT = Path(__file__).resolve().parents[1]

# stacked order bottom -> top, reference colours sampled from the figure
PHASES = ["anatase", "rutile", "Li4Ti5O12", "Li2TiO3", "Li2CO3"]
REF = np.array([(255, 142, 142), (210, 128, 128), (192, 146, 207), (241, 193, 255), (1, 213, 249)], float)
TOL = 28.0  # max colour distance for a pixel to count as a class
GAP = 12    # bridge gaps of this many px inside one class (label text, boundary lines)
# (row of 100 %, row of 0 %) per panel in the 985 x 1859 px image; t = 0 at x = 96 px, t = 10 min at x = 970 px
PANELS = {700: (12, 580), 725: (631, 1199), 750: (1251, 1819)}
X0, X10 = 96.0, 970.0
HAMPEL_WIN, HAMPEL_THR, T_SKIP = 41, 2.5, 0.5  # filter window (columns), threshold (wt %), apply after this t (min)

# Ti basis: molar masses (g/mol) and Ti atoms per formula unit (nominal stoichiometry)
M = {"anatase": 79.866, "rutile": 79.866, "Li2TiO3": 109.75, "Li4Ti5O12": 459.08}
NTI = {"anatase": 1, "rutile": 1, "Li2TiO3": 1, "Li4Ti5O12": 5}


def extract_images(pdf):
    import pymupdf
    doc = pymupdf.open(str(pdf))
    found = {}
    for page in doc:
        for im in page.get_images():
            xref, w, h = im[0], im[2], im[3]
            if (w, h) in ((985, 1859), (952, 515)):
                pix = pymupdf.Pixmap(doc, xref)
                if pix.n > 4:
                    pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
                found["fig2" if h == 1859 else "fig3"] = np.frombuffer(pix.samples, np.uint8).reshape(h, w, pix.n)[:, :, :3].astype(float)
    if set(found) != {"fig2", "fig3"}:
        raise SystemExit("did not find both figure images (expected 985x1859 and 952x515 px); is this ja3c10916.pdf?")
    return found


def classify(col):
    d = np.linalg.norm(col[:, None, :] - REF[None, :, :], axis=2)
    k = d.argmin(axis=1)
    k[d.min(axis=1) > TOL] = -1
    return k


def column_tops(im, y100, y0, x):
    """Top edge (in % from the bottom) of the longest run of each phase colour in one pixel column."""
    k = classify(im[y100:y0 + 1, x, :])
    n = len(k)
    pct = 100.0 * (n - 1 - np.arange(n)) / (n - 1)
    tops = []
    for ci in range(len(PHASES)):
        rows = np.nonzero(k == ci)[0]
        if len(rows) < 2:
            tops.append(np.nan)
            continue
        runs, start, prev = [], rows[0], rows[0]
        for r in rows[1:]:
            if r - prev > GAP:
                runs.append((start, prev))
                start = r
            prev = r
        runs.append((start, prev))
        a, b = max(runs, key=lambda ab: ab[1] - ab[0])
        tops.append(pct[a] if b - a >= 2 else np.nan)
    return tops


def panel_curves(im, T):
    y100, y0 = PANELS[T]
    mid = (y100 + y0) // 2
    xs_all = [x for x in range(int(X0) + 1, im.shape[1]) if im[mid + 60, x].sum() < 740]
    xs = np.arange(int(X0) + 1, xs_all[-1] + 1)
    tops = np.array([column_tops(im, y100, y0, int(x)) for x in xs]).T  # (phase, x)
    t = (xs - X0) / (X10 - X0) * 10.0
    cum = tops.copy()
    for i in range(len(PHASES)):  # a missing phase has zero width: its boundary equals the one below
        below = cum[i - 1] if i else np.zeros(len(xs))
        cum[i] = np.where(np.isnan(cum[i]), below, cum[i])
    cum[-1] = 100.0  # top of the stack is the 100 % line
    out = []
    for r in cum:
        med = median_filter(r, size=HAMPEL_WIN, mode="nearest")
        r2 = np.where((np.abs(r - med) > HAMPEL_THR) & (t > T_SKIP), med, r)
        out.append(median_filter(r2, size=5, mode="nearest"))
    cum = np.maximum.accumulate(np.vstack(out), axis=0)
    wt = np.diff(np.vstack([np.zeros(len(xs)), cum]), axis=0)
    return t, wt


def fig3_curve(im):
    """Li2TiO3 at 482 C: relative y (fraction of the plot height above the x axis), t in min."""
    h, w, _ = im.shape
    r0, g0, b0 = im[..., 0], im[..., 1], im[..., 2]
    gray_px = (abs(r0 - g0) < 12) & (abs(g0 - b0) < 12) & (r0 < 215)
    # x-axis line = the row with the longest gray run between the curve's left and right ends (row 463 in the 515 px image).
    # The previous 'darkest row' rule picked row 499, the tick-label text, and offset every value by about +0.07.
    y_axis = 400 + int(np.argmax(gray_px[400:490, 100:900].sum(axis=1)))
    x0, x5 = 43.0, 943.0
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    magenta = (r > 200) & (b > 200) & (g < 190)
    gray = (abs(r - g) < 12) & (abs(g - b) < 12) & (r > 90) & (r < 175)
    pts = []
    for x in range(int(x0), int(x5) + 1):
        col = magenta[:y_axis - 2, x].copy()
        if x < 80:  # heating strip is plotted grey
            col |= np.r_[np.zeros(300, bool), gray[300:y_axis - 2, x]]
        rows = np.nonzero(col)[0]
        if len(rows) == 0:
            continue
        run_end = rows[0]
        for r_ in rows[1:]:
            if r_ - run_end > 3:
                break
            run_end = r_
        yc = 0.5 * (rows[0] + run_end)  # centre of the topmost run (curve is above the 50 s label)
        pts.append(((x - x0) / (x5 - x0) * 5.0, (y_axis - yc) / (y_axis - 0)))
    return np.array(pts)


def to_ti_fractions(wt):
    idx = {p: i for i, p in enumerate(PHASES)}
    mol = np.array([wt[idx[p]] * NTI[p] / M[p] for p in M])
    return mol / mol.sum(axis=0)


def main():
    pdf = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "data/digitized_inputs/chapman2023_fig2"
    out.mkdir(parents=True, exist_ok=True)
    imgs = extract_images(pdf)

    grid_step = 0.05
    rows = []
    for T in PANELS:
        t, wt = panel_curves(imgs["fig2"], T)
        tg = np.arange(grid_step, t[-1], grid_step)  # skip t = 0: the axis line corrupts the first columns
        wg = np.array([np.interp(tg, t, w) for w in wt])
        ti = to_ti_fractions(wg)
        for j, tt in enumerate(tg):
            rows.append([T, round(tt, 3)] + [round(v, 2) for v in wg[:, j]] + [round(v, 4) for v in ti[:, j]])
        print(f"{T} C: t to {t[-1]:.2f} min, max Li2TiO3 {wg[PHASES.index('Li2TiO3')][tg > 0.3].max():.1f} wt%")
    header = ["T_C", "t_min"] + [f"wt_{p}" for p in PHASES] + [f"tifrac_{p}" for p in M]
    with open(out / "extracted_phase_fractions.csv", "w", newline="") as f:
        csv.writer(f).writerows([header] + rows)

    pts = fig3_curve(imgs["fig3"])
    tg = np.arange(0.0, pts[-1, 0], 0.02)
    yg = np.interp(tg, pts[:, 0], pts[:, 1])
    with open(out / "fig3_482C_li2tio3_relative.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t_min", "li2tio3_rel_plot_height"])
        w.writerows([[round(a, 3), round(b, 4)] for a, b in zip(tg, yg)])
    print(f"Fig. 3: {len(pts)} columns, t to {pts[-1, 0]:.2f} min")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(4, 1, figsize=(6, 11))
        cols = ["#ff8e8e", "#d28080", "#c092cf", "#f1c1ff", "#01d5f9"]
        for a, T in zip(ax, PANELS):
            t, wt = panel_curves(imgs["fig2"], T)
            a.stackplot(t, wt, colors=cols, labels=PHASES)
            a.set_title(f"{T} C (extracted)", fontsize=9)
            a.set_ylim(0, 100)
        ax[0].legend(fontsize=6, loc="center right")
        ax[3].plot(tg, yg, ".", ms=2)
        ax[3].set_title("482 C Li2TiO3, relative units (extracted)", fontsize=9)
        plt.tight_layout()
        plt.savefig(out / "reconstruction.png", dpi=80)
    except ImportError:
        pass


if __name__ == "__main__":
    main()
