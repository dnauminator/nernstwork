"""Datasets as fitting targets: content hashes, observation channels, conditions.

Datasets are read, never modified. Every number the evaluator fits is traceable to a file and its sha256.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .model import Conditions

DEFAULT_T_C = 25.0


def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_json(obj) -> str:
    return sha256_bytes(canonical_json(obj).encode())


def sha256_file(path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def load_dataset(path) -> tuple[dict, str]:
    raw = Path(path).read_bytes()
    return json.loads(raw), sha256_bytes(raw)


def initial_amounts(cond: dict) -> dict:
    """Initial amounts: c0_mM_N for electrochemical datasets, c0 on conditions.basis otherwise."""
    return dict(cond["c0_mM_N"] if "c0_mM_N" in cond else cond["c0"])


def basis_of(cond: dict) -> str:
    return cond.get("basis", "mM-N")


@dataclass
class Channel:
    name: str
    t: np.ndarray
    y: np.ndarray
    scale: float  # max |y| over all reported points, including t = 0 (used only by the legacy objective)


@dataclass
class ObservationSet:
    dataset_id: str
    sha256: str
    source_type: str
    channels: list[Channel]
    c0: dict
    conditions: Conditions
    t_union: np.ndarray
    notes: list[str] = field(default_factory=list)

    @property
    def n_obs(self) -> int:
        return int(sum(len(c.y) for c in self.channels))

    def channel_names(self) -> list[str]:
        return [c.name for c in self.channels]


def observation_set(ds: dict, sha: str, exclude_t0: bool = True) -> ObservationSet:
    """Turn a dataset into fitting targets.

    t = 0 points are excluded by default: they are the initial condition (pinned for digitized data,
    or the value that defines c0 for Source Data), so the model reproduces them by construction and
    counting them would inflate n and deflate the noise estimate.
    """
    notes = []
    chans = []
    for s in ds["series"]:
        t = np.array(s["t_min"], float)
        y = np.array([np.nan if v is None else v for v in s["y"]], float)
        keep = np.isfinite(y)
        scale = float(np.max(np.abs(y[keep]))) if keep.any() else 1.0
        if (~keep).any():
            notes.append(f"{s['species']}: {int((~keep).sum())} missing points skipped")
        if exclude_t0:
            z = keep & (t == 0)
            if z.any():
                notes.append(f"{s['species']}: t=0 point treated as initial condition, not as an observation")
                c0 = float(initial_amounts(ds["conditions"]).get(s["species"], 0.0))
                y0 = float(y[z][0])
                if abs(y0 - c0) > 1e-6 * (1.0 + abs(c0)):
                    notes.append(f"{s['species']}: WARNING t=0 value {y0} differs from the stated initial condition {c0}")
            keep &= t > 0
        chans.append(Channel(s["species"], t[keep], y[keep], max(scale, 1e-9)))
    cond = ds["conditions"]
    T = cond.get("temperature_C")
    if T is None:
        notes.append(f"temperature not reported; {DEFAULT_T_C} C assumed (matters only for potential dependence)")
    conditions = Conditions(E_V=cond.get("potential_V_vs_RHE"), pH=cond.get("pH"),
                            T_C=DEFAULT_T_C if T is None else float(T))
    t_union = np.unique(np.concatenate([[0.0]] + [c.t for c in chans]))
    return ObservationSet(ds["id"], sha, ds["provenance"]["source_type"], chans, initial_amounts(cond), conditions,
                          t_union, notes)


@dataclass
class JointObservationSet:
    """Several experiments fitted jointly with one parameter vector (e.g. the same chemistry at several temperatures).

    Each part keeps its own conditions, initial amounts and channels; the fitter simulates every part with the shared
    parameters and profiles one noise sigma per measured species across parts. Attributes used for compile-time checks
    (conditions, c0, channel names) describe the union: conditions.n_temperatures counts distinct temperatures.
    """
    parts: list[ObservationSet]
    dataset_id: str
    sha256: str
    source_type: str
    conditions: Conditions
    notes: list[str] = field(default_factory=list)

    @property
    def n_obs(self) -> int:
        return int(sum(p.n_obs for p in self.parts))

    def channel_names(self) -> list[str]:
        out = []
        for p in self.parts:
            out += [c for c in p.channel_names() if c not in out]
        return out

    @property
    def c0(self) -> dict:
        keys = []
        for p in self.parts:
            keys += [k for k in p.c0 if k not in keys]
        return {k: max(float(p.c0.get(k, 0.0)) for p in self.parts) for k in keys}

    @property
    def t_union(self) -> np.ndarray:
        return np.unique(np.concatenate([p.t_union for p in self.parts]))


def parts_of(obs) -> list[ObservationSet]:
    return list(obs.parts) if isinstance(obs, JointObservationSet) else [obs]


def joint_observation_set(items: list[tuple[dict, str]], exclude_t0: bool = True):
    """One dataset gives an ObservationSet (unchanged single-run behaviour); several give a JointObservationSet."""
    if len(items) == 1:
        return observation_set(items[0][0], items[0][1], exclude_t0)
    parts = [observation_set(ds, sha, exclude_t0) for ds, sha in items]
    bases = {basis_of(ds["conditions"]) for ds, _ in items}
    if len(bases) > 1:
        raise ValueError(f"datasets fitted jointly must share one basis, got {sorted(bases)}")
    temps = sorted({p.conditions.T_C for p in parts})
    pots = {p.conditions.E_V for p in parts if p.conditions.E_V is not None}
    phs = {p.conditions.pH for p in parts if p.conditions.pH is not None}
    c = parts[0].conditions
    cond = Conditions(E_V=c.E_V, pH=c.pH, T_C=c.T_C, n_potentials=max(1, len(pots)), n_pH=max(1, len(phs)),
                      n_temperatures=len(temps))
    sha = sha256_json([p.sha256 for p in parts])
    notes = [f"{p.dataset_id}: {n}" for p in parts for n in p.notes]
    notes.append(f"joint fit of {len(parts)} experiments at T = {temps} C with one parameter vector")
    return JointObservationSet(parts, "+".join(p.dataset_id for p in parts), sha,
                               "+".join(sorted({p.source_type for p in parts})), cond, notes)


UNRESOLVED_FIELDS = [
    ("conditions.potential_V_vs_RHE", "potential not on the RHE scale"),
    ("conditions.pH", "pH not reported"),
    ("conditions.temperature_C", "temperature not reported"),
    ("conditions.volume_mL", "electrolyte volume not reported"),
]


def _get(d, dotted):
    for k in dotted.split("."):
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d


def describe_dataset(ds: dict, sha: str) -> dict:
    """Compact, factual description used in evidence summaries (no interpretation)."""
    c0 = initial_amounts(ds["conditions"])
    total0 = sum(c0.values())
    unit = basis_of(ds["conditions"])
    electrochem = unit == "mM-N"
    series = []
    for s in ds["series"]:
        y = [v for v in s["y"] if v is not None]
        series.append({
            "channel": s["species"], "n_points": len(y), "t_min_range": [min(s["t_min"]), max(s["t_min"])],
            ("y_range_mM_N" if electrochem else "y_range"): [round(min(y), 4), round(max(y), 4)],
            "reported_unit": s.get("reported_unit"), "conversion": s.get("conversion"), "has_reported_sigma": "sigma" in s,
        })
    q = ds.get("quality", {})
    fields = UNRESOLVED_FIELDS if electrochem else [f for f in UNRESOLVED_FIELDS if f[0] == "conditions.temperature_C"]
    unresolved = [msg for f, msg in fields if _get(ds, f) is None]
    if not ds["provenance"].get("verified_against_figure"):
        unresolved.append("values not verified against the plotted figure")
    out = {
        "dataset_id": ds["id"], "sha256": sha, "source_type": ds["provenance"]["source_type"],
        "kind": "time trajectories (concentration vs time)",
        "provenance": {k: ds["provenance"].get(k) for k in ("citation", "doi", "figure", "file", "sheet", "extraction",
                                                          "verified_against_figure", "notes")},
        "conditions": ds["conditions"], **({"initial_total_N_mM": total0} if electrochem else {"basis": unit}),
        "series": series, "quality_flags": q.get("flags", []), "unresolved_metadata": unresolved,
    }
    if "n_closure" in q:
        out["n_closure"] = q["n_closure"]
    if "reported_n_loss" in q:
        out["reported_n_loss"] = q["reported_n_loss"]
    if "n_basis_note" in q:
        out["n_basis_note"] = q["n_basis_note"]
    if "basis_note" in q:
        out["basis_note"] = q["basis_note"]
    return out
