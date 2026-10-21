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
    if space.get("kind") == "synthesis" or "steps" in space:
        return enumerate_synthesis_space(space)
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


# ====================================================================== synthesis spaces (element balance, phases)
SYNTH_RATE_LAWS = ("first_order", "avrami")
DEFAULT_MAX_MEMBERS = 600


def validate_synthesis_space(space: dict) -> list[str]:
    """Plain-language problems with a synthesis space (empty list = ok). The space is the 'parts list': species with
    compositions, candidate steps with allowed rate-law forms and support, and the rules for combining them."""
    errs = []
    for k in ("space_id", "species", "initial", "steps"):
        if k not in space:
            errs.append(f"missing '{k}'")
    if errs:
        return errs
    if not isinstance(space["space_id"], str) or not space["space_id"].replace("-", "").replace("_", "").replace(".", "").isalnum():
        errs.append("space_id: letters, digits, '-', '_' and '.' only")
    elements = (space.get("conservation") or {}).get("elements")
    if not elements:
        errs.append("conservation.elements: list the conserved elements, e.g. [\"Ti\"] or [\"Ti\", \"Li\"]")
        elements = []
    sp = {}
    for s in space["species"]:
        if not isinstance(s, dict) or not s.get("id"):
            errs.append(f"species entry without id: {s}")
            continue
        if s["id"] in sp:
            errs.append(f"duplicate species {s['id']}")
        if not isinstance(s.get("composition"), dict):
            errs.append(f"species {s['id']}: composition (atoms per formula unit of the conserved elements) is required")
        sp[s["id"]] = s
    for x in space["initial"]:
        if x not in sp:
            errs.append(f"initial species {x} is not declared")
    ids = set()
    for st in space["steps"]:
        sid = st.get("id")
        if not sid or sid in ids:
            errs.append(f"step without a unique id: {st.get('id')}")
        ids.add(sid)
        for side in ("reactants", "products"):
            if not isinstance(st.get(side), dict) or not st[side]:
                errs.append(f"step {sid}: {side} must be a non-empty object {{species: coefficient}}")
                continue
            for x, c in st[side].items():
                if x not in sp:
                    errs.append(f"step {sid}: unknown species {x}")
                if not isinstance(c, (int, float)) or c <= 0:
                    errs.append(f"step {sid}: coefficient of {x} must be a positive number")
        if errs:
            continue
        for el in elements:
            a = sum(c * sp[x]["composition"].get(el, 0.0) for x, c in st["reactants"].items())
            b = sum(c * sp[x]["composition"].get(el, 0.0) for x, c in st["products"].items())
            if abs(a - b) > 1e-9 * max(1.0, abs(a)):
                errs.append(f"step {sid}: {el} not conserved ({a:g} in, {b:g} out)")
        rls = st.get("rate_laws", ["first_order"])
        bad = [r for r in rls if r not in SYNTH_RATE_LAWS]
        if bad or not rls:
            errs.append(f"step {sid}: rate_laws must be a non-empty subset of {list(SYNTH_RATE_LAWS)}")
        for x in (st.get("orders") or {}):
            if x not in st["reactants"]:
                errs.append(f"step {sid}: orders given for non-reactant {x}")
        for e in st.get("support", []):
            if e.get("basis") not in ("literature", "data", "speculative"):
                errs.append(f"step {sid}: support basis must be literature | data | speculative")
            if e.get("basis") == "literature" and not e.get("source"):
                errs.append(f"step {sid}: literature support needs a source (DOI or citation plus location)")
    td = space.get("temperature_dependence", {"Ea": "per_step"})
    if td.get("Ea", "per_step") not in ("per_step", "shared", "none"):
        errs.append("temperature_dependence.Ea: per_step | shared | none")
    if td.get("Ea", "per_step") != "none" and "T_ref_C" not in td:
        errs.append("temperature_dependence.T_ref_C is required (quote k at a temperature inside the data range)")
    if space.get("avrami_exponent", "per_step") not in ("per_step", "shared"):
        errs.append("avrami_exponent: per_step | shared")
    for x in (space.get("require") or {}).get("produced", []):
        if x not in sp:
            errs.append(f"require.produced: unknown species {x}")
    return errs


def _synth_live(steps, initial) -> bool:
    present = set(initial)
    changed = True
    while changed:
        changed = False
        for st in steps:
            if all(x in present for x in st["reactants"]):
                for x in st["products"]:
                    if x not in present:
                        present.add(x)
                        changed = True
    return all(all(x in present for x in st["reactants"]) for st in steps)


def synthesis_structures(space: dict) -> list[tuple]:
    """Step subsets allowed by the space: size limits, required products, no dead step (one that can never run)."""
    steps = space["steps"]
    req = set((space.get("require") or {}).get("produced", []))
    must = set((space.get("require") or {}).get("steps", []))
    lo, hi = space.get("min_steps", 1), space.get("max_steps", len(steps))
    out = []
    for r in range(lo, hi + 1):
        for sub in itertools.combinations(steps, r):
            if not must <= {st["id"] for st in sub}:
                continue
            produced = {x for st in sub for x in st["products"]}
            if not req <= produced or not _synth_live(sub, space["initial"]):
                continue
            out.append(sub)
    return out


def _synth_mechanism(sub, variant, space: dict, mid: str) -> dict:
    sp = {s["id"]: s for s in space["species"]}
    used = []
    for x in list(space["initial"]) + [x for st in sub for x in list(st["reactants"]) + list(st["products"])]:
        if x not in used:
            used.append(x)
    keep = ("id", "label", "formula", "role", "observable", "phase", "composition")
    species = [{k: v for k, v in sp[x].items() if k in keep} for x in used]
    td = space.get("temperature_dependence", {"Ea": "per_step"})
    rxns = []
    for i, (st, rl_kind) in enumerate(zip(sub, variant), 1):
        orders = {x: {"value": float((st.get("orders") or {}).get(x, 1.0)), "fixed": True} for x in st["reactants"]}
        rl = {"family": "power_law", "params": {"k": {"value": 1.0}}, "orders": orders}
        if td.get("Ea", "per_step") != "none":
            ea = {"value": 150.0}
            if td.get("Ea") == "shared":
                ea["tie"] = "Ea_shared"
            rl["temperature_dependence"] = {"Ea_kJ_mol": ea, "T_ref_C": float(td["T_ref_C"])}
        if rl_kind == "avrami":
            n = {"value": 1.0}
            if space.get("avrami_exponent", "per_step") == "shared":
                n["tie"] = "n_avrami_shared"
            rl["time_modulation"] = {"kind": "avrami", "n": n}
        rxns.append({"id": f"R{i}", "reactants": [{"species": x, "coeff": float(c)} for x, c in st["reactants"].items()],
                     "products": [{"species": x, "coeff": float(c)} for x, c in st["products"].items()], "rate_law": rl})
    desc = "; ".join(f"{st['id']} {rk}" for st, rk in zip(sub, variant))
    return {"id": mid, "description": f"enumerated ({space['space_id']}): {desc}",
            "conservation": {"basis": "elements", "elements": list(space["conservation"]["elements"])},
            "species": species, "reactions": rxns}


def enumerate_synthesis_space(space: dict) -> list[dict]:
    """Every combination of steps and allowed rate-law forms, as ordinary candidate submissions.

    Each step is power-law, first order in every reactant unless the space gives orders (a solid-state step stops when
    any reactant phase is exhausted), with Arrhenius temperature dependence quoted at T_ref and, for the avrami form, a
    JMAK factor with a free exponent. Support entries declared on a step travel with every reaction made from it.
    Raises ValueError for an invalid space or one larger than max_members (never truncated silently).
    """
    errs = validate_synthesis_space(space)
    if errs:
        raise ValueError("invalid synthesis space: " + "; ".join(errs))
    out = []
    for sub in synthesis_structures(space):
        for variant in itertools.product(*[st.get("rate_laws", ["first_order"]) for st in sub]):
            code = ",".join(f"{st['id']}:{rk}" for st, rk in zip(sub, variant))
            name = f"enum-{sha256_json([space['space_id'], code])[:10]}"
            mech = _synth_mechanism(sub, variant, space, name)
            support = []
            for i, st in enumerate(sub, 1):
                ents = st.get("support") or [{"basis": "speculative", "note": f"step {st['id']} of space {space['space_id']}"}]
                support += [dict({k: v for k, v in e.items() if k in ("basis", "source", "note")}, target=f"R{i}") for e in ents]
            sub_out = {"name": name, "mechanism": mech, "support": support,
                       "rationale": f"enumerated: {code} | space {space['space_id']}"}
            if space.get("observation_map"):
                sub_out["observation_map"] = space["observation_map"]
            out.append(sub_out)
    cap = space.get("max_members", DEFAULT_MAX_MEMBERS)
    if len(out) > cap:
        raise ValueError(f"space {space['space_id']} has {len(out)} members, more than max_members={cap}; narrow it "
                         "(fewer steps, max_steps, fewer rate-law forms per step, or require steps/products)")
    n_free = lambda s: sum(1 + ("temperature_dependence" in r["rate_law"]) + ("time_modulation" in r["rate_law"])
                           for r in s["mechanism"]["reactions"])
    out.sort(key=lambda s: (n_free(s), s["name"]))
    return out
