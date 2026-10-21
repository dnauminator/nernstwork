"""Enumeration baseline (SPEC section 9 step 1; Barter et al. enumerate-then-filter; SiMBA simplest-first).

Generates every network in a declared space: subsets of an explicit reaction pool (1:1 N-equivalent steps), crossed
with rate-law and catalyst-state variants, filtered by structural rules, simplest first. The output is ordinary candidate
submissions; they go through the same validator, fitter and ranking as anything an agent proposes.
"""
from __future__ import annotations

import itertools

from .data import sha256_json


def _step(item) -> tuple:
    """Normalize a pool entry to (reactants, products, code). [a, b] is the 1:1 step a -> b; a dict gives full
    N-equivalent stoichiometry, e.g. {"reactants": {"NO2": 1, "NH3": 1}, "products": {"SINK": 2}}."""
    if isinstance(item, dict):
        r = tuple(sorted((k, float(v)) for k, v in item["reactants"].items()))
        p = tuple(sorted((k, float(v)) for k, v in item["products"].items()))
        fmt = lambda side: "+".join(("" if c == 1 else f"{c:g}") + sp for sp, c in side)
        return r, p, f"{fmt(r)}>{fmt(p)}"
    a, b = item
    return ((a, 1.0),), ((b, 1.0),), f"{a}>{b}"


def reaction_pool(space: dict) -> list[tuple]:
    if space.get("pool") not in (None, "all_reductions"):
        return [_step(p) for p in space["pool"]]
    sp = {s["id"]: s for s in space["species"]}
    terminal = set(space.get("terminal", []))
    out = []
    for a, b in itertools.permutations(sp, 2):
        if a in terminal:
            continue
        oa, ob = sp[a].get("N_oxidation_state"), sp[b].get("N_oxidation_state")
        if oa is not None and ob is not None and oa <= ob:
            continue  # reduction direction only (cathode)
        out.append(_step((a, b)))
    return sorted(out, key=lambda st: st[2])


def _electrons(sp, step):
    r, p, _ = step
    ox = [sp[x].get("N_oxidation_state") for x, _ in r + p]
    if any(o is None for o in ox):
        return None
    return sum(c * sp[x]["N_oxidation_state"] for x, c in r) - sum(c * sp[x]["N_oxidation_state"] for x, c in p)


def _structurally_ok(steps, space) -> bool:
    req = space.get("require", {})
    consumed = {x for r, _, _ in steps for x, _ in r}
    produced = {x for _, p, _ in steps for x, _ in p}
    if not set(req.get("consumed", [])) <= consumed or not set(req.get("produced", [])) <= produced:
        return False
    present = set(space.get("initial", ["NO3"]))
    changed = True
    while changed:
        changed = False
        for r, p, _ in steps:
            if all(x in present for x, _ in r):
                for x, _ in p:
                    if x not in present:
                        present.add(x)
                        changed = True
    if any(not all(x in present for x, _ in r) for r, _, _ in steps):
        return False  # a dead step: its rate constant would carry no information
    hidden = {s["id"] for s in space["species"] if s.get("role") == "hidden_intermediate"}
    for h in hidden & (consumed | produced):
        if h not in consumed or h not in produced:
            return False  # a hidden species must be an intermediate, otherwise it is just another sink
    return True


def build_mechanism(steps, space, rate_law: str, cat_state: str, mid: str) -> dict:
    """catalyst_state: none | shared_activation | shared_deactivation (electrochemical steps share one tau; steps with
    electrons = 0 are not modulated) | split_deactivation (steps producing an unmeasured terminal species share their own
    tau, all other steps share tau_cat; a phenomenological shut-off, flagged by the validator when the step is chemical)."""
    sp = {s["id"]: s for s in space["species"]}
    used = sorted({x for r, p, _ in steps for x, _ in r + p} | set(space.get("initial", ["NO3"])), key=list(sp).index)
    species = [{k: v for k, v in sp[s].items() if k in ("id", "label", "role", "observable", "phase", "N_oxidation_state")}
               for s in used]
    sinks = {s["id"] for s in space["species"] if s.get("role") == "sink"}
    lang_targets = set(space.get("langmuir_reactants", ["NO3"]))
    rxns = []
    for i, step in enumerate(steps, 1):
        r, p, _ = step
        single = r[0][0] if len(r) == 1 and r[0][1] == 1 else None
        e = _electrons(sp, step)
        if rate_law == "langmuir_shared_K" and single in lang_targets:
            rl = {"family": "langmuir_saturation", "params": {"k": {"value": 1e-3}, "K": {"value": 100.0, "tie": f"K_{single}"}}}
        elif rate_law == "power_NO3_shared_order" and single == "NO3":
            rl = {"family": "power_law", "params": {"k": {"value": 1e-3}},
                  "orders": {"NO3": {"value": 1.0, "bounds": [0.0, 3.0], "tie": "n_NO3"}}}
        else:
            rl = {"family": "mass_action", "params": {"k": {"value": 1e-3}}}
        if cat_state == "shared_deactivation" and e != 0:
            rl["time_modulation"] = {"kind": "deactivation", "tau_min": {"value": 300.0, "tie": "tau_cat"}}
        elif cat_state == "shared_activation" and e != 0:
            rl["time_modulation"] = {"kind": "activation", "tau_min": {"value": 30.0, "tie": "tau_cat"}}
        elif cat_state == "split_deactivation":
            tie = "tau_sink" if any(x in sinks for x, _ in p) else "tau_cat"
            rl["time_modulation"] = {"kind": "deactivation", "tau_min": {"value": 300.0, "tie": tie}}
        rxns.append({"id": f"R{i}", "reactants": [{"species": x, "coeff": c} for x, c in r],
                     "products": [{"species": x, "coeff": c} for x, c in p], "electrons": e, "rate_law": rl})
    return {"id": mid, "description": f"enumerated ({space['space_id']}): " + ", ".join(st[2].replace(">", "->") for st in steps)
            + f"; {rate_law}; catalyst state {cat_state}", "species": species, "reactions": rxns}


def enumerate_space(space: dict) -> list[dict]:
    pool = reaction_pool(space)
    out = []
    max_r = space.get("max_reactions", len(pool))
    sinks = {s["id"] for s in space["species"] if s.get("role") == "sink"}
    for r in range(1, max_r + 1):
        for steps in itertools.combinations(pool, r):
            if not _structurally_ok(steps, space):
                continue
            singles = {st[0][0][0] for st in steps if len(st[0]) == 1}
            for rl in space.get("rate_laws", ["mass_action"]):
                if rl == "langmuir_shared_K" and not singles & set(space.get("langmuir_reactants", ["NO3"])):
                    continue
                if rl == "power_NO3_shared_order" and "NO3" not in singles:
                    continue
                for cs in space.get("catalyst_state", ["none"]):
                    if cs == "split_deactivation" and not any(x in sinks for st in steps for x, _ in st[1]):
                        continue  # identical to shared_deactivation without a loss step
                    code = ",".join(st[2] for st in steps)
                    name = f"enum-{sha256_json([code, rl, cs])[:10]}"
                    mech = build_mechanism(steps, space, rl, cs, name)
                    out.append({"name": name, "mechanism": mech,
                                "support": [{"target": rx["id"], "basis": "speculative",
                                             "note": f"member of declared enumeration space {space['space_id']}"}
                                            for rx in mech["reactions"]],
                                "rationale": f"enumerated: {code} | {rl} | {cs}"})
    n_free = lambda s: sum(1 + ("K" in r["rate_law"]["params"]) for r in s["mechanism"]["reactions"])
    out.sort(key=lambda s: (n_free(s), s["name"]))
    return out
