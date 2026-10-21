"""scripts/chapman_to_dataset.py: Chapman 2023 Fig. 2 extraction -> synthesis datasets (mol per mol Ti).

Self-contained on purpose: no nernstwork imports, schema loaded with jsonschema directly.
"""
import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data/digitized_inputs/chapman2023_fig2"
GRID = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0, 1.2, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 9.5]
IDS = ["chapman2023_fig2_700C", "chapman2023_fig2_725C", "chapman2023_fig2_750C"]
TI_PER_FU = {"anatase": 1, "rutile": 1, "Li2TiO3": 1, "Li4Ti5O12": 5}


def _validator():
    reg = Registry()
    for p in sorted((ROOT / "schema").glob("*.schema.json")):
        s = json.loads(p.read_text())
        reg = reg.with_resource(s["$id"], Resource(contents=s, specification=DRAFT202012))
    return Draft202012Validator(json.loads((ROOT / "schema/dataset.schema.json").read_text()), registry=reg)


@pytest.fixture(scope="module")
def converted(tmp_path_factory):
    out = tmp_path_factory.mktemp("chapman")
    r = subprocess.run([sys.executable, str(ROOT / "scripts/chapman_to_dataset.py"), str(SRC), str(out)],
                       capture_output=True, text=True, check=True)
    assert len(r.stdout.strip().splitlines()) == 3  # one summary line per file
    return out


def _load(folder):
    return {i: json.loads((folder / f"{i}.json").read_text()) for i in IDS}


def test_outputs_validate_and_use_the_grid(converted):
    assert sorted(p.stem for p in converted.glob("*.json")) == IDS
    v = _validator()
    for i, ds in _load(converted).items():
        assert not [e.message for e in v.iter_errors(ds)], i
        assert ds["id"] == i and ds["conditions"]["temperature_C"] == int(i.split("_")[-1][:-1])
        assert ds["conditions"]["basis"] == "mol per mol Ti"
        assert ds["conditions"]["c0"] == {"anatase": 1.0, "Li2CO3": 0.4}
        assert [s["species"] for s in ds["series"]] == ["anatase", "rutile", "Li2TiO3", "Li4Ti5O12"]
        assert ds["provenance"]["verified_against_figure"] is False
        for s in ds["series"]:
            assert s["t_min"] == GRID
            assert all(0.3 <= t <= 9.5 for t in s["t_min"])
            assert len(s["y"]) == len(GRID) and all(0.0 <= y <= 1.0 for y in s["y"])


def test_li4ti5o12_is_ti_fraction_over_five(converted):
    rows = list(csv.DictReader(open(SRC / "extracted_phase_fractions.csv", newline="")))
    for i, ds in _load(converted).items():
        T, g = float(i.split("_")[-1][:-1]), 2.0
        sel = [float(r["tifrac_Li4Ti5O12"]) for r in rows
               if float(r["T_C"]) == T and abs(float(r["t_min"]) - g) <= 0.051]
        assert len(sel) == 3
        lto = next(s for s in ds["series"] if s["species"] == "Li4Ti5O12")
        assert abs(lto["y"][GRID.index(g)] - sum(sel) / 3 / 5) < 1e-5, i


def test_first_point_uses_no_column_before_0p3_min(converted):
    rows = list(csv.DictReader(open(SRC / "extracted_phase_fractions.csv", newline="")))
    for i, ds in _load(converted).items():
        T = float(i.split("_")[-1][:-1])
        cols = {round(float(r["t_min"]), 2): r for r in rows if float(r["T_C"]) == T}
        for s in ds["series"]:
            n = TI_PER_FU[s["species"]]
            want = (float(cols[0.3][f"tifrac_{s['species']}"]) + float(cols[0.35][f"tifrac_{s['species']}"])) / 2 / n
            assert abs(s["y"][0] - want) < 1e-5, (i, s["species"], s["y"][0], want)


def test_ti_weighted_sum_is_one(converted):
    for i, ds in _load(converted).items():
        y = {s["species"]: s["y"] for s in ds["series"]}
        for k, t in enumerate(GRID):
            total = sum(n * y[sp][k] for sp, n in TI_PER_FU.items())
            assert abs(total - 1.0) <= 0.02, (i, t, total)


def test_committed_datasets_match_fresh_conversion(converted):
    for i in IDS:
        committed = ROOT / "data/real" / f"{i}.json"
        assert committed.read_text() == (converted / f"{i}.json").read_text(), f"rerun the converter for {i}"
