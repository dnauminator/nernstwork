"""Matplotlib figures for evidence packs and reports (Agg backend, deterministic file output)."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .data import basis_of, initial_amounts

COLORS = {"NO3": "#1f77b4", "NO2": "#ff7f0e", "NH3": "#2ca02c", "N2": "#9467bd", "N2O": "#d62728",
          "anatase": "#d62728", "rutile": "#ff7f0e", "Li2TiO3": "#2ca02c", "Li4Ti5O12": "#1f77b4"}


def _xscale(ax, tmax):
    if tmax > 1000:
        ax.set_xscale("symlog", linthresh=200)


def plot_dataset(ds: dict, path: Path):
    if basis_of(ds["conditions"]) != "mM-N":
        return _plot_dataset_basis(ds, path)
    c0 = sum(initial_amounts(ds["conditions"]).values())
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


def _plot_dataset_basis(ds: dict, path: Path):
    """Non-electrochemical basis (e.g. mol per mol Ti): measured series on linear and logarithmic time axes."""
    unit = basis_of(ds["conditions"])
    fig, axs = plt.subplots(1, 2, figsize=(11, 4))
    for s in ds["series"]:
        t = [a for a, b in zip(s["t_min"], s["y"]) if b is not None]
        y = [b for b in s["y"] if b is not None]
        for ax in axs:
            ax.plot(t, y, "o-", ms=4, color=COLORS.get(s["species"]), label=s["species"])
    T = ds["conditions"].get("temperature_C")
    axs[0].set_title(f"{ds['id']} ({T} C): measured series")
    axs[1].set_title("same, logarithmic time")
    axs[1].set_xscale("log")
    for ax in axs:
        ax.set_xlabel("time / min")
        ax.set_ylabel(unit)
        ax.legend(fontsize=8)
    fig.tight_layout()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=90)
    plt.close(fig)


def _plot_fits_joint(obs, fits: list[tuple[str, dict]], path: Path, title: str = ""):
    """Joint fit: one row per experiment (e.g. temperature), one column per measured channel."""
    chans = obs.channel_names()
    fig, axs = plt.subplots(len(obs.parts), len(chans), figsize=(3.4 * len(chans), 2.9 * len(obs.parts)), squeeze=False)
    styles = ["-", "--", ":", "-."]
    for r, part in enumerate(obs.parts):
        by = {c.name: c for c in part.channels}
        for k, ch in enumerate(chans):
            ax = axs[r][k]
            if ch in by:
                ax.plot(by[ch].t, by[ch].y, "ko", ms=3, label="data", zorder=5)
            for i, (name, fr) in enumerate(fits):
                tr = (fr.get("trajectories") or {}).get(part.dataset_id)
                if not tr:
                    continue
                y = np.sum([tr["species"][s] for s in fr["_mapping"][ch]], axis=0)
                ax.plot(tr["t_min"], y, styles[i % 4], color=f"C{i}", label=name)
            ax.set_title(f"{ch} at {part.conditions.T_C:g} C", fontsize=9)
            ax.set_xlabel("time / min")
    axs[0][0].legend(fontsize=7)
    fig.suptitle(title)
    fig.tight_layout()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=90)
    plt.close(fig)


def plot_fits(obs, fits: list[tuple[str, dict]], path: Path, title: str = ""):
    """Overlay fitted trajectories of several candidates on the data, one panel per channel plus unobserved N."""
    if hasattr(obs, "parts"):
        return _plot_fits_joint(obs, fits, path, title)
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
    ncol = min(len(ch), 4) if len(ch) > 5 else len(ch)
    nrow = -(-len(ch) // ncol)
    fig, axs = plt.subplots(nrow, ncol, figsize=(4 * ncol, 3.2 * nrow))
    axs = np.atleast_1d(axs).ravel()
    for ax in axs[len(ch):]:
        ax.axis("off")
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
