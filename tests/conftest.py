import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pytest
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012


def _schema(name):
    return json.loads((ROOT / "schema" / name).read_text())


@pytest.fixture(scope="session")
def registry():
    reg = Registry()
    for n in ("mechanism.schema.json", "dataset.schema.json", "task.schema.json", "result.schema.json"):
        s = _schema(n)
        reg = reg.with_resource(s["$id"], Resource(contents=s, specification=DRAFT202012))
    return reg


@pytest.fixture(scope="session")
def validator(registry):
    from jsonschema import Draft202012Validator

    def make(name):
        return Draft202012Validator(_schema(name), registry=registry)

    return make


@pytest.fixture(scope="session")
def root():
    return ROOT
