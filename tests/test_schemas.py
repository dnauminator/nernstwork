import json

import pytest

from nernstwork import validate_mechanism


def _files(root, pattern):
    return sorted(root.glob(pattern))


def test_schemas_are_valid_schemas(root):
    from jsonschema import Draft202012Validator

    for p in (root / "schema").glob("*.json"):
        Draft202012Validator.check_schema(json.loads(p.read_text()))


def test_real_datasets_validate(root, validator):
    v = validator("dataset.schema.json")
    files = _files(root, "data/real/*.json")
    assert len(files) >= 3
    for p in files:
        errs = list(v.iter_errors(json.loads(p.read_text())))
        assert not errs, f"{p.name}: {errs[0].message}"


def test_worlds_validate_and_are_semantically_consistent(root, validator):
    v = validator("task.schema.json")
    files = _files(root, "worlds/W*.json")
    assert len(files) >= 4
    for p in files:
        w = json.loads(p.read_text())
        errs = list(v.iter_errors(w))
        assert not errs, f"{p.name}: {errs[0].message} at {list(errs[0].path)}"
        assert validate_mechanism(w["ground_truth"]) == [], p.name
        sp = {s["id"] for s in w["ground_truth"]["species"]}
        assert set(w["observation"]["observed_species"]) <= sp


def test_library_validates(root, validator):
    v = validator("mechanism.schema.json")
    for p in _files(root, "worlds/library/*.json"):
        m = json.loads(p.read_text())
        assert not list(v.iter_errors(m)), p.name
        assert validate_mechanism(m) == [], p.name


def test_validate_mechanism_catches_errors():
    bad = {
        "id": "bad",
        "species": [{"id": "A", "N_oxidation_state": 5}, {"id": "B", "N_oxidation_state": 3}],
        "reactions": [{"id": "R1", "reactants": [{"species": "A", "coeff": 1}],
                       "products": [{"species": "B", "coeff": 2}, {"species": "Z", "coeff": 1}],
                       "electrons": 7, "rate_law": {"family": "langmuir_saturation", "params": {"k": {"value": 1}}}}],
    }
    msgs = " | ".join(validate_mechanism(bad))
    assert "unknown species Z" in msgs
    assert "not conserved" in msgs
    assert "needs params.K" in msgs
