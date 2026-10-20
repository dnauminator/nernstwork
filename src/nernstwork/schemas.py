"""JSON Schema validation against the repository schemas (shared registry so $refs resolve)."""
from __future__ import annotations

import json
from functools import cache
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012


def _schema_dir() -> Path:
    here = Path(__file__).resolve()
    for d in (here.parents[2] / "schema", here.parents[1] / "schema"):  # repository layout, then sandbox toolkit layout
        if (d / "candidate.schema.json").exists():
            return d
    raise FileNotFoundError("schema directory not found")


SCHEMA_DIR = _schema_dir()
NAMES = ("mechanism", "dataset", "task", "result", "candidate")


@cache
def _registry():
    reg = Registry()
    for n in NAMES:
        s = json.loads((SCHEMA_DIR / f"{n}.schema.json").read_text())
        reg = reg.with_resource(s["$id"], Resource(contents=s, specification=DRAFT202012))
    return reg


@cache
def validator(name: str) -> Draft202012Validator:
    s = json.loads((SCHEMA_DIR / f"{name}.schema.json").read_text())
    return Draft202012Validator(s, registry=_registry())


def errors(name: str, obj) -> list[str]:
    out = []
    for e in sorted(validator(name).iter_errors(obj), key=lambda e: list(e.absolute_path)):
        path = "/".join(str(p) for p in e.absolute_path)
        out.append(f"{path or '(root)'}: {e.message[:300]}")
    return out
