"""Canonical identity of a candidate.

Two hashes:
  dynamics_hash  what the fitter sees: network topology, rate-law families and modifiers, fixed values, bounds, ties
                 and the observation map. Unobserved species are anonymous (relabelling X as Y does not change it), and
                 electron counts and oxidation states are ignored because no measured channel depends on them.
  chem_hash      dynamics plus the chemical bookkeeping of every species and step (oxidation states, electrons).

Free-parameter starting values, descriptions, labels and support metadata are not part of either identity: the
evaluator ignores proposed starting values (all candidates get the same deterministic multistart), so two
submissions that differ only in those fields are the same hypothesis. Candidates with equal dynamics_hash and
different chem_hash are observationally equivalent on these channels: one fit serves both, and the report says the
data cannot separate them.
"""
from __future__ import annotations

import itertools

from .data import sha256_json
from .model import DEFAULT_BOUNDS, _bounds_key, _param_entries

MAX_ANON_PERMUTATIONS = 720  # up to 6 unobserved species


def default_observation_map(mech: dict, channels: list[str]) -> dict:
    ids = {s["id"] for s in mech["species"]}
    return {ch: [ch] for ch in channels if ch in ids}


def _f(x):
    return None if x is None else float(x)


def _reaction_sig(rxn: dict, label, bounds_table, with_chem: bool):
    """Normalized signature of one reaction (numbers as floats) and its parameter descriptors."""
    rl = rxn["rate_law"]
    params = {}
    for slot, sp, prm, kind in _param_entries(rxn):
        key = slot + (f":{label(sp)}" if sp else "")
        lo, hi = prm.get("bounds", bounds_table[_bounds_key(kind, rxn)])
        d = {"b": [float(lo), float(hi)]}
        if prm.get("fixed"):
            d["fixed"] = float(prm["value"])
        params[key] = (d, prm.get("tie"))
    sig = {
        "in": sorted([label(t["species"]), float(t["coeff"])] for t in rxn["reactants"]),
        "out": sorted([label(t["species"]), float(t["coeff"])] for t in rxn["products"]),
        "fam": rl["family"],
        "pot_Eref": _f(rl["potential_dependence"]["E_ref_V"]) if rl.get("potential_dependence") else None,
        "ph_ref": _f(rl["ph_dependence"]["pH_ref"]) if rl.get("ph_dependence") else None,
        "tmod": rl["time_modulation"]["kind"] if rl.get("time_modulation") else None,
        "rev": bool(rxn.get("reversible", False)),
    }
    if with_chem:
        sig["e"] = _f(rxn.get("electrons"))
    return sig, params


def _serialize(mech: dict, obs_map: dict, label, bounds_table, with_chem: bool):
    """Canonical form plus the mapping from this mechanism's names to canonical positions."""
    rx = []
    for rxn in mech["reactions"]:
        sig, params = _reaction_sig(rxn, label, bounds_table, with_chem)
        base = dict(sig, params={k: dict(d, tied=bool(t)) for k, (d, t) in params.items()})
        rx.append((sha256_json(base), sig, params, rxn))
    rx.sort(key=lambda z: z[0])
    tie_index: dict[str, int] = {}
    out_rx = []
    for _, sig, params, _rxn in rx:
        ps = {}
        for key in sorted(params):
            d, tie = params[key]
            d = dict(d)
            if tie:
                d["tie"] = tie_index.setdefault(tie, len(tie_index))
            ps[key] = d
        out_rx.append(dict(sig, params=ps))
    species = []
    for s in mech["species"]:
        d = {"id": label(s["id"]), "observable": bool(s.get("observable", True))}
        if with_chem:
            d["ox"] = _f(s.get("N_oxidation_state"))
        species.append(d)
    species.sort(key=lambda d: d["id"])
    om = {ch: sorted(label(x) for x in v) for ch, v in sorted(obs_map.items())}
    meta = {"labels": {s["id"]: label(s["id"]) for s in mech["species"]},
            "reaction_order": [z[3]["id"] for z in rx], "tie_index": tie_index}
    return {"species": species, "reactions": out_rx, "obs": om}, meta


def canonical_forms(mech: dict, obs_map: dict, fixed_names: set[str], bounds_table: dict | None = None) -> dict:
    """Return {'dynamics': (form, hash, meta), 'chem': (form, hash, meta)}.

    fixed_names: species ids that keep their names (initially present species and any species in the observation map).
    meta maps this mechanism's species, reactions and tie names to canonical labels and positions, so a result stored
    in canonical coordinates can be read back in any equivalent candidate's own names.
    """
    bounds_table = dict(DEFAULT_BOUNDS, **(bounds_table or {}))
    keep = set(fixed_names) | {x for v in obs_map.values() for x in v}
    anon = sorted(s["id"] for s in mech["species"] if s["id"] not in keep)
    out = {}
    for with_chem, key in ((False, "dynamics"), (True, "chem")):
        best = None
        perms = itertools.permutations(range(len(anon)))
        for n, perm in enumerate(perms):
            if n >= MAX_ANON_PERMUTATIONS:
                break
            names = {a: f"_u{perm[i]}" for i, a in enumerate(anon)}

            def label(sp, names=names):
                return names.get(sp, sp)

            form, meta = _serialize(mech, obs_map, label, bounds_table, with_chem)
            h = sha256_json(form)
            if best is None or h < best[1]:
                best = (form, h, meta)
        out[key] = best
    return out


def canonical_param_keys(compiled, meta: dict) -> list[str]:
    """Canonical key for each free parameter of a compiled mechanism, aligned with its theta vector."""
    order = {rid: i for i, rid in enumerate(meta["reaction_order"])}
    keys = []
    for p in compiled.free:
        if p.name.startswith("tie:"):
            keys.append(f"tie{meta['tie_index'][p.name[4:]]}")
            continue
        j, slot, sp = p.members[0]
        rid = compiled.mechanism["reactions"][j]["id"]
        keys.append(f"r{order[rid]}.{slot}" + (f".{meta['labels'][sp]}" if sp else ""))
    return keys
