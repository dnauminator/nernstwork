"""scripts/arrows3_to_endpoint.py: ARROWS3 Exp.json + Settings.json -> endpoint dataset.

Uses a tiny synthetic table in the ARROWS3 layout, so no licensed data are needed.
"""
import importlib.util
import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("arrows3_to_endpoint", ROOT / "scripts/arrows3_to_endpoint.py")
conv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(conv)

EXP = {"Universal File": {
    "Common Experimental Conditions": {"heating rate": "20 C/min", "cooling rate": "natural", "atmosphere": "air"},
    "Li2O, P2O5, TiO2": {"Precursor stoichiometry": [1.0, 1.0, 2.0], "Temperatures": {
        "600 C": {"XRD": None, "Experimentally Verified": True, "products": ["TiO2_141.cif", "Li3PO4_62.cif"],
                  "product weight fractions": [60, 40]},
        "700 C": {"XRD": None, "Experimentally Verified": True,
                  "products": ["LiTiPO5_2.cif", "LiTiPO5_62.cif", "TiP2O7_205"],
                  "product weight fractions": [40, 35, 25]}}},
    "LiOH, P2O5, TiO2": {"Precursor stoichiometry": [1.0, 1.0, 2.0], "Temperatures": {
        "700 C": {"Experimentally Verified": False, "Source": "Li2O, P2O5, TiO2 700", "products": ["LiTiPO5_2.cif"],
                  "product weight fractions": [100]}}},
}}
SETTINGS = {"Precursors": ["Li2O", "LiOH", "P2O5", "TiO2"], "Target": "LiTiPO5", "Temperatures": [600, 700]}


def _build(tmp_path):
    (tmp_path / "Exp.json").write_text(json.dumps(EXP))
    (tmp_path / "Settings.json").write_text(json.dumps(SETTINGS))
    return conv.convert(tmp_path / "Exp.json", tmp_path / "Settings.json")


def test_unverified_entries_are_dropped_and_listed(tmp_path):
    ds = _build(tmp_path)
    assert [(e["precursor_set"], e["temperature_C"]) for e in ds["experiments"]] == [
        (["Li2O", "P2O5", "TiO2"], 600.0), (["Li2O", "P2O5", "TiO2"], 700.0)]
    d = ds["quality"]["dropped_entries"]
    assert d["count"] == 1 and d["items"][0]["inferred_from"] == "Li2O, P2O5, TiO2 700"
    assert "unverified_entries_dropped" in ds["quality"]["flags"]
    assert ds["quality"]["counts"] == {"precursor_sets_in_file": 2, "entries_in_file": 3, "entries_kept": 2,
                                       "entries_dropped": 1, "entries_with_target": 1}


def test_phase_names_normalised_and_polymorphs_kept_distinct(tmp_path):
    ds = _build(tmp_path)
    ph = ds["experiments"][1]["phases"]
    assert [(p["name"], p["structure_id"]) for p in ph] == [("LiTiPO5", "2"), ("LiTiPO5", "62"), ("TiP2O7", "205")]
    assert ph[2]["raw_name"] == "TiP2O7_205"  # no .cif suffix in the source for this one
    assert ds["experiments"][1]["target_present"] and ds["experiments"][1]["target_wt_percent"] == 75.0
    assert not ds["experiments"][0]["target_present"]
    # Li3PO4_62 and LiTiPO5_62 share a suffix but are different phases: the suffix is never used as a phase identity
    assert ds["experiments"][0]["phases"][1]["name"] == "Li3PO4" and ds["experiments"][0]["phases"][1]["structure_id"] == "62"


def test_conditions_and_schema(tmp_path):
    ds = _build(tmp_path)
    assert ds["system"]["heating_rate_C_per_min"] == 20.0 and ds["system"]["atmosphere"] == "air"
    assert ds["system"]["hold_h"] == 4.0 and ds["id"] == "arrows3_ltopo"
    schema = json.loads((ROOT / "schema/endpoint_dataset.schema.json").read_text())
    assert not list(Draft202012Validator(schema).iter_errors(ds))
