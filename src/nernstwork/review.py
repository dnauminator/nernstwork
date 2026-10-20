"""Review bundles and evidence-linked review validation.

A bundle is a frozen, content-addressed snapshot of candidate definitions, the development evidence, code-computed
results and diagnostics. A review is accepted only if every finding points at artifacts that exist in that bundle
(`<artifact_id>#<json-pointer>`) and every number it quotes matches the bundle value. This makes reviews checkable;
it does not make them experimental validation.
"""
from __future__ import annotations

import math

SEVERITIES = {"blocker", "major", "minor", "note"}
CATEGORIES = {"chemistry", "statistics", "numerics", "data", "coverage", "interpretation"}
CHECKS = {"numerical", "literature", "assumption", "consistency"}
ACTIONS = {"new_candidate", "additional_analysis", "experiment", "reinterpret", "none"}
RESPONSE_ACTIONS = {"revised", "analysis", "disputed", "deferred", "accepted_no_change"}


def resolve(bundle: dict, ref: str):
    """Resolve '<artifact>#<json-pointer>' inside bundle['artifacts']. Raises KeyError with a reason."""
    if "#" in ref:
        art, ptr = ref.split("#", 1)
    else:
        art, ptr = ref, ""
    arts = bundle["artifacts"]
    if art not in arts:
        raise KeyError(f"unknown artifact '{art}'")
    node = arts[art]
    if ptr in ("", "/"):
        return node
    if not ptr.startswith("/"):
        raise KeyError(f"pointer must start with '/': {ref}")
    for tok in ptr[1:].split("/"):
        tok = tok.replace("~1", "/").replace("~0", "~")
        if isinstance(node, list):
            try:
                node = node[int(tok)]
            except (ValueError, IndexError):
                raise KeyError(f"{ref}: list index '{tok}' invalid") from None
        elif isinstance(node, dict):
            if tok not in node:
                raise KeyError(f"{ref}: key '{tok}' not found (available: {sorted(node)[:12]})")
            node = node[tok]
        else:
            raise KeyError(f"{ref}: cannot descend into a scalar at '{tok}'")
    return node


def _close(a, b) -> bool:
    try:
        a, b = float(a), float(b)
    except (TypeError, ValueError):
        return False
    return math.isclose(a, b, rel_tol=0.01, abs_tol=1e-6)


def validate_review(review: dict, bundle: dict) -> list[str]:
    errs = []
    if not isinstance(review, dict):
        return ["review must be an object"]
    if not isinstance(review.get("summary"), str) or not review["summary"].strip():
        errs.append("summary: required non-empty string")
    findings = review.get("findings")
    if not isinstance(findings, list) or not findings:
        errs.append("findings: required non-empty list")
        findings = []
    ids = set()
    for i, f in enumerate(findings):
        where = f"findings[{i}]"
        if not isinstance(f, dict):
            errs.append(f"{where}: must be an object")
            continue
        fid = f.get("id")
        if not isinstance(fid, str) or not fid or fid in ids:
            errs.append(f"{where}.id: required unique string")
        ids.add(fid)
        if f.get("severity") not in SEVERITIES:
            errs.append(f"{where}.severity: one of {sorted(SEVERITIES)}")
        if f.get("category") not in CATEGORIES:
            errs.append(f"{where}.category: one of {sorted(CATEGORIES)}")
        if not isinstance(f.get("claim"), str) or not f["claim"].strip():
            errs.append(f"{where}.claim: required")
        targets = f.get("targets")
        if not isinstance(targets, list) or not targets:
            errs.append(f"{where}.targets: at least one artifact reference")
            targets = []
        for t in targets:
            try:
                resolve(bundle, t)
            except KeyError as e:
                errs.append(f"{where}.targets: {e}")
        ev = f.get("evidence")
        if not isinstance(ev, list) or not ev:
            errs.append(f"{where}.evidence: at least one cited reference")
            ev = []
        for j, e in enumerate(ev):
            if not isinstance(e, dict) or "ref" not in e:
                errs.append(f"{where}.evidence[{j}]: object with 'ref'")
                continue
            try:
                val = resolve(bundle, e["ref"])
            except KeyError as ex:
                errs.append(f"{where}.evidence[{j}]: {ex}")
                continue
            if "value" in e and e["value"] is not None:
                if isinstance(val, (dict, list)):
                    errs.append(f"{where}.evidence[{j}]: quoted value but {e['ref']} is not a scalar")
                elif isinstance(val, (int, float)) and not isinstance(val, bool):
                    if not _close(e["value"], val):
                        errs.append(f"{where}.evidence[{j}]: quoted {e['value']} but bundle has {val} at {e['ref']}")
                elif str(e["value"]) != str(val):
                    errs.append(f"{where}.evidence[{j}]: quoted {e['value']!r} but bundle has {val!r}")
        chk = f.get("check")
        if not isinstance(chk, dict) or chk.get("type") not in CHECKS or not chk.get("description"):
            errs.append(f"{where}.check: {{type: one of {sorted(CHECKS)}, description}}")
        act = f.get("action")
        if not isinstance(act, dict) or act.get("type") not in ACTIONS or not act.get("description"):
            errs.append(f"{where}.action: {{type: one of {sorted(ACTIONS)}, description}}")
    a = review.get("assessment")
    cands = set(bundle.get("candidate_ids", []))
    if not isinstance(a, dict):
        errs.append("assessment: required object")
    else:
        for c in a.get("plausible_candidates", []):
            if c not in cands:
                errs.append(f"assessment.plausible_candidates: {c} not in bundle")
        for c in a.get("not_supported", []):
            if not isinstance(c, dict) or c.get("candidate_id") not in cands or not c.get("reason"):
                errs.append("assessment.not_supported: entries {candidate_id in bundle, reason}")
        if a.get("adequate_candidate_exists") not in ("yes", "no", "uncertain"):
            errs.append("assessment.adequate_candidate_exists: yes | no | uncertain")
        if not isinstance(a.get("ambiguities", []), list):
            errs.append("assessment.ambiguities: list of strings")
    return errs


def validate_response(response: dict, review: dict, known_candidates: set[str]) -> list[str]:
    errs = []
    fids = {f["id"] for f in review["findings"]}
    rs = response.get("responses")
    if not isinstance(rs, list) or not rs:
        return ["responses: required non-empty list"]
    seen = set()
    for i, r in enumerate(rs):
        if r.get("finding_id") not in fids:
            errs.append(f"responses[{i}].finding_id: unknown finding {r.get('finding_id')}")
        seen.add(r.get("finding_id"))
        if r.get("action") not in RESPONSE_ACTIONS:
            errs.append(f"responses[{i}].action: one of {sorted(RESPONSE_ACTIONS)}")
        for c in r.get("candidate_ids", []):
            if c not in known_candidates:
                errs.append(f"responses[{i}].candidate_ids: unknown candidate {c}")
        if not r.get("note"):
            errs.append(f"responses[{i}].note: required")
    missing = sorted(fids - seen)
    if missing:
        errs.append(f"no response to findings {missing}")
    return errs
