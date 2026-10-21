"""Matplotlib figures for evidence packs and reports (Agg backend, deterministic file output)."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

COLORS = {"NO3": "#1f77b4", "NO2": "#ff7f0e", "NH3": "#2ca02c", "N2": "#9467bd", "N2O": "#d62728"}


def _xscale(ax, tmax):
    if tmax > 1000:
        ax.set_xscale("symlog", linthresh=200)


def plot_dataset(ds: dict, path: Path):
    c0 = sum(ds["conditions"]["c0_mM_N"].values())
    fig, axs = plt.subplots(1, 2, figsize=(11, 4))
    tmax = 0
    for s in ds["series"]:
        t = [a for a, b in zip(s["t_min"], s["y"]) if b is not None]
        y = [b for b in s["y"] if b is not None]
        tmax = max(tmax, max(t))
        axs[0].plot(t, y, "o-", ms=4, color=COLORS.get(s["species"]), label=s["species"])
    axs[0].set_title(f"{ds['id']}: measured channels")
    axs[0].set_xlabel("time / min")
    axs[0].set_ylabel("mM-N")
    axs[0].legend()
    q = ds.get("quality", {})
    if "n_closure" in q:
        cl = q["n_closure"]
        axs[1].plot(cl["t_min"], [(1 - f) * c0 for f in cl["fraction"]], "ko-", ms=4, label="initial N - sum of measured")
    if "reported_n_loss" in q:
        r = q["reported_n_loss"]
        axs[1].plot(r["t_min"], r["y"], "x:", label="authors' reported N loss")
    axs[1].axhline(0, color="grey", lw=0.5)
    axs[1].set_title("N not accounted for by measured channels")
    axs[1].set_xlabel("time / min")
    axs[1].set_ylabel("mM-N")
    axs[1].legend()
    for ax in axs:
        _xscale(ax, tmax)
    fig.tight_layout()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=90)
    plt.close(fig)


def plot_fits(obs, fits: list[tuple[str, dict]], path: Path, title: str = ""):
    """Overlay fitted trajectories of several candidates on the data, one panel per channel plus unobserved N."""
    chans = obs.channel_names()
    fig, axs = plt.subplots(2, max(2, -(-(len(chans) + 2) // 2)), figsize=(13, 7))
    axs = axs.flat
    tmax = float(obs.t_union.max())
    styles = ["-", "--", ":", "-."]
    for k, ch in enumerate(chans):
        ax = axs[k]
        o = obs.channels[k]
        ax.plot(o.t, o.y, "ko", ms=4, label="data", zorder=5)
        for i, (name, fr) in enumerate(fits):
            tr = fr["trajectory"]
            sps = fr["_mapping"][ch]
            y = np.sum([fr["trajectory"]["species"][s] for s in sps], axis=0)
            ax.plot(tr["t_min"], y, styles[i % 4], color=f"C{i}", label=name)
        ax.set_title(ch)
        _xscale(ax, tmax)
    ax = axs[len(chans)]
    for i, (name, fr) in enumerate(fits):
        mapped = {x for v in fr["_mapping"].values() for x in v}
        un = [s for s in fr["trajectory"]["species"] if s not in mapped]
        if un:
            y = np.sum([fr["trajectory"]["species"][s] for s in un], axis=0)
            ax.plot(fr["trajectory"]["t_min"], y, styles[i % 4], color=f"C{i}", label=f"{name}: {'+'.join(un)}")
    c0 = sum(obs.c0.values())
    tt = sorted(set.intersection(*[set(c.t.tolist()) for c in obs.channels]))
    if tt:
        tot = [sum(float(c.y[list(c.t).index(t)]) for c in obs.channels) for t in tt]
        ax.plot(tt, [c0 - v for v in tot], "ko", ms=4, label="data deficit")
    ax.set_title("unobserved N (model) vs measured deficit")
    _xscale(ax, tmax)
    for a in axs:
        a.set_xlabel("time / min")
    handles, labels = axs[0].get_legend_handles_labels()
    axs[len(chans) + 1].axis("off")
    axs[len(chans) + 1].legend(handles, labels, loc="center", fontsize=8)
    for a in list(axs)[len(chans) + 2:]:
        a.axis("off")
    axs[len(chans)].legend(fontsize=7)
    fig.suptitle(title)
    fig.tight_layout()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=90)
    plt.close(fig)


def plot_residuals(fit_res: dict, path: Path, title: str = ""):
    ch = fit_res["residuals"]["channels"]
    fig, axs = plt.subplots(1, len(ch), figsize=(4 * len(ch), 3.2))
    axs = np.atleast_1d(axs)
    for ax, (name, d) in zip(axs, ch.items()):
        ax.axhline(0, color="grey", lw=0.5)
        ax.plot(d["t_min"], d["standardized"], "o-", ms=4)
        p = d["runs_test_p"]
        ax.set_title(f"{name} standardized residuals" + (f" (runs p={p:.2f})" if p is not None else ""), fontsize=9)
        if max(d["t_min"]) > 1000:
            ax.set_xscale("symlog", linthresh=200)
    fig.suptitle(title, fontsize=10)
    fig.tight_layout()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=90)
    plt.close(fig)


def plot_profiles(profiles: dict, path: Path, title: str = ""):
    ps = profiles["params"]
    n = len(ps)
    if not n:
        return
    fig, axs = plt.subplots(1, n, figsize=(3.2 * n, 3))
    axs = np.atleast_1d(axs)
    for ax, (name, d) in zip(axs, ps.items()):
        ax.plot(d["grid_theta"], d["delta_nll"], "o-", ms=3)
        ax.axhline(1.92, color="r", lw=0.8)
        ax.set_ylim(-0.1, max(4.0, min(10, max(d["delta_nll"]) if d["delta_nll"] else 4)))
        ax.set_title(f"{name}\n{d['classification']}", fontsize=8)
        ax.set_xlabel("log10 value" if d["transform"] == "log10" else "value", fontsize=8)
    fig.suptitle(title, fontsize=10)
    fig.tight_layout()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=90)
    plt.close(fig)
