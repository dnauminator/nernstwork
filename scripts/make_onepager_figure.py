#!/usr/bin/env python3
"""Figure for the one-pager: three frozen models' predictions of the 750 C Chapman data, with the measurements.

Reads the shot-4 block of video/src/data/shots.json (built by scripts/export_video_data.py from the frozen runs and
their held-out evaluations) and writes docs/figures/chapman_750C_prediction.png (and .pdf).

Usage: python scripts/make_onepager_figure.py
"""
import json
import os
import sys
from pathlib import Path

if os.name == "nt":  # some Windows conda setups do not search Library\bin for extension-module DLLs
    for d in (Path(sys.prefix) / "Library" / "bin",):
        if d.is_dir():
            os.add_dll_directory(str(d))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "figures"

PHASES = [("anatase", "Anatase TiO$_2$"), ("rutile", "Rutile TiO$_2$"), ("Li2TiO3", "Li$_2$TiO$_3$"),
          ("Li4Ti5O12", "Li$_4$Ti$_5$O$_{12}$ spinel")]
STYLE = {  # role -> (colour, line style, legend text); colours follow the video (rule blue, agent's other model orange)
    "baseline": ("#7a7873", "--", "Code-only baseline's pick"),
    "rule": ("#1f6fd1", "-", "Opus 5.5, rule's pick (best fit)"),
    "plausible": ("#d95926", "-", "Opus 5.5, agent's other plausible model"),
}


def main():
    d = json.loads((ROOT / "video" / "src" / "data" / "shots.json").read_text(encoding="utf-8"))["shot4"]
    t = d["t"]
    fig, axes = plt.subplots(1, 4, figsize=(7.4, 2.05), constrained_layout=True)
    for ax, (ph, title) in zip(axes, PHASES):
        o = d["observations"][ph]
        ax.plot(o["t"], o["y"], "o", ms=2.6, color="#222222", zorder=5)
        for m in d["models"]:
            col, ls, _ = STYLE[m["role"]]
            ax.plot(t, m["curves"][ph], ls, color=col, lw=1.4, zorder=3)
        ax.set_title(title, fontsize=8)
        ax.set_xlabel("time (min)", fontsize=7)
        ax.tick_params(labelsize=6.5, length=2.5)
        ax.set_xlim(0, 9.6)
        ax.set_ylim(bottom=0)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.grid(axis="y", lw=0.3, alpha=0.5)
    axes[0].set_ylabel("formula units per mole Ti", fontsize=7)
    handles = [plt.Line2D([], [], marker="o", ls="", ms=3, color="#222222", label="measured at 750 °C (never used in fitting)")]
    for m in d["models"]:
        col, ls, text = STYLE[m["role"]]
        handles.append(plt.Line2D([], [], color=col, ls=ls, lw=1.4,
                                  label=f"{text}: rank {m['rank']} of {m['n_space']}"))
    fig.legend(handles=handles, loc="outside lower center", ncol=2, fontsize=6.8, frameon=False)
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "chapman_750C_prediction.png", dpi=300)
    fig.savefig(OUT / "chapman_750C_prediction.pdf")
    print("wrote", OUT / "chapman_750C_prediction.png")
    for m in d["models"]:
        print(m["role"], m["candidate_id"], "rank", m["rank"], "RMSE", m["rmse_all"])


if __name__ == "__main__":
    main()
