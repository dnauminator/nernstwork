#!/usr/bin/env python3
"""Audit local LTOPO endpoints and demonstrate a *synthetic* fixed-time ambiguity.

Run with the project environment:
  .venv/bin/python scripts/analyze_ltopo_endpoints.py

No real kinetic model is fitted. Row-level output stays in ignored data/arrows3/.
Only aggregate counts and a separately labelled synthetic example are exported to
docs/examples/ltopo_oct22/. The ARROWS data licence remains unconfirmed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import jsonschema
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from arrows3_to_endpoint import convert  # noqa: E402
from nernstwork.mechanism import R  # noqa: E402
from nernstwork.model import Conditions, compile_mechanism  # noqa: E402

ALIASES = {"LiHO": "LiOH", "PH6NO4": "NH4H2PO4", "PH9(NO2)2": "(NH4)2HPO4",
           "N2H8HPO4": "(NH4)2HPO4"}
# Li, Ti, P atoms. Gas products contain none of these three elements.
COMPOSITIONS = {"Li2O": (2, 0, 0), "LiOH": (1, 0, 0), "Li2CO3": (2, 0, 0),
                "Li2TiO3": (2, 1, 0), "Li4Ti5O12": (4, 5, 0), "TiO2": (0, 1, 0),
                "P2O5": (0, 0, 2), "NH4H2PO4": (0, 0, 1),
                "(NH4)2HPO4": (0, 0, 1), "Li3PO4": (3, 0, 1)}
# Recipe ratios transcribed from Szymanski et al. 2023, SI Table 3, PDF pp. 14-15.
# They are weighed recipe amounts, NOT observed c0 phase fractions at the hold.
SI_RECIPES = [
    {"Li2O": 1, "TiO2": 2, "P2O5": 1},
    {"TiO2": 1, "LiOH": 1, "(NH4)2HPO4": 1},
    {"Li2O": 1, "TiO2": 2, "(NH4)2HPO4": 2},
    {"Li4Ti5O12": 1, "LiOH": 1, "(NH4)2HPO4": 5},
    {"Li2O": 1, "Li4Ti5O12": 2, "(NH4)2HPO4": 10},
    {"TiO2": 2, "Li2CO3": 1, "(NH4)2HPO4": 2},
    {"Li4Ti5O12": 2, "Li2CO3": 1, "(NH4)2HPO4": 10},
    {"Li2TiO3": 1, "Li4Ti5O12": 1, "(NH4)2HPO4": 6},
    {"Li2TiO3": 1, "TiO2": 1, "(NH4)2HPO4": 2},
    {"TiO2": 1, "NH4H2PO4": 1, "LiOH": 1},
    {"Li2O": 1, "TiO2": 2, "NH4H2PO4": 2},
    {"Li4Ti5O12": 1, "NH4H2PO4": 5, "LiOH": 1},
    {"TiO2": 2, "Li2CO3": 1, "NH4H2PO4": 2},
    {"Li2TiO3": 1, "TiO2": 1, "NH4H2PO4": 2},
    {"TiO2": 2, "P2O5": 1, "LiOH": 2},
]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def audit(exp_path, settings_path):
    raw = json.loads(exp_path.read_text())["Universal File"]
    ds = convert(exp_path, settings_path)
    schema = json.loads((ROOT / "schema/endpoint_dataset.schema.json").read_text())
    jsonschema.Draft202012Validator(schema).validate(ds)
    if ds["system"]["target"] != "LiTiPO5":
        raise ValueError("This audit is specific to the LTOPO dataset")
    xrd_count = 0
    xrd_groups = defaultdict(list)
    for key, block in raw.items():
        if key == "Common Experimental Conditions":
            continue
        for temperature, record in block["Temperatures"].items():
            if record.get("Experimentally Verified"):
                if len(record["products"]) != len(record["product weight fractions"]):
                    raise ValueError(f"Mismatched product and fraction lengths: {key}")
                xrd = record.get("XRD", {})
                xrd_count += bool(xrd.get("x")) and len(xrd["x"]) == len(xrd.get("y", []))
                if xrd.get("x"):
                    fingerprint = hashlib.sha256(json.dumps({k: xrd[k] for k in ("x", "y")},
                                                sort_keys=True, separators=(",", ":")).encode()).hexdigest()
                    xrd_groups[fingerprint].append({"precursor_set": key, "temperature": temperature,
                                                    "products": record["products"],
                                                    "product_weight_fractions": record["product weight fractions"]})

    recipes = []
    indexed = {frozenset(x): x for x in SI_RECIPES}
    for key, block in raw.items():
        if key == "Common Experimental Conditions":
            continue
        original = [s.strip() for s in key.split(",")]
        normal = [ALIASES.get(s, s) for s in original]
        si = indexed.get(frozenset(normal))
        if si is None:
            raise ValueError(f"No inspected SI Table 3 recipe for {normal}")
        totals = sum((np.array(COMPOSITIONS[s]) * si[s] for s in normal), np.zeros(3))
        if not np.allclose(totals, totals[1]):
            raise ValueError(f"SI recipe fails Li:Ti:P = 1:1:1: {normal}")
        recipes.append({"raw_precursors": original, "canonical_precursors": normal,
                        "stoichiometry_in_json": block.get("Precursor stoichiometry"),
                        "SI_Table_3_coefficients_in_canonical_order": [si[s] for s in normal],
                        "recipe_formula_units_per_mol_Ti": {s: si[s] / totals[1] for s in normal},
                        "basis": "published recipe; not measured hold-start phase fractions"})

    temps = sorted({e["temperature_C"] for e in ds["experiments"]})
    by_temp = []
    for temp in temps:
        rows = [e for e in ds["experiments"] if e["temperature_C"] == temp]
        classes = Counter()
        prevalence = Counter()
        for e in rows:
            ids = {p["structure_id"] for p in e["phases"] if p["name"] == "LiTiPO5"}
            if ids - {"2", "62"}:
                raise ValueError(f"Unexpected target structure IDs: {ids}")
            classes["both" if len(ids) == 2 else f"{next(iter(ids))}_only" if ids else "none"] += 1
            prevalence.update({p["name"] for p in e["phases"]})
        by_temp.append({"temperature_C": temp, "n_endpoints": len(rows),
                        "n_target_detected": sum(e["target_present"] for e in rows),
                        "target_structure_classes": dict(classes),
                        "phase_presence_counts": dict(sorted(prevalence.items())),
                        "target_reported_percent_range": [min(e["target_wt_percent"] for e in rows),
                                                           max(e["target_wt_percent"] for e in rows)]})
    phases = Counter(p["raw_name"].removesuffix(".cif") for e in ds["experiments"] for p in e["phases"])
    sums = [e["wt_sum"] for e in ds["experiments"]]
    # Neither conflicting copy is selected as the truth: exclude both for this sensitivity check.
    suspect = {(tuple(s.strip() for s in row["precursor_set"].split(",")), float(row["temperature"].split()[0]))
               for group in xrd_groups.values() if len(group) > 1 for row in group}
    conservative = [e for e in ds["experiments"] if (tuple(e["precursor_set"]), e["temperature_C"]) not in suspect]
    target_classes = Counter()
    for e in conservative:
        if e["temperature_C"] == 700:
            ids = {p["structure_id"] for p in e["phases"] if p["name"] == "LiTiPO5"}
            target_classes["both" if len(ids) == 2 else f"{next(iter(ids))}_only" if ids else "none"] += 1
    # Compare the file with the explicit example in the paper (p. 7); do not reconcile by substitution.
    comparison = next(e for e in ds["experiments"]
                      if set(e["precursor_set"]) == {"Li2O", "P2O5", "TiO2"} and e["temperature_C"] == 700)
    summary = {"source_type": "local ARROWS repository table; descriptive audit, not a kinetic fit",
               "source_hashes": {exp_path.name: digest(exp_path), settings_path.name: digest(settings_path)},
               "counts": ds["quality"]["counts"], "verified_rows_with_nonempty_matching_XRD_arrays": int(xrd_count),
               "unique_XRD_xy_arrays": len(xrd_groups),
               "duplicate_XRD_groups": sum(len(group) > 1 for group in xrd_groups.values()),
               "records_in_duplicate_XRD_groups": sum(len(group) for group in xrd_groups.values() if len(group) > 1),
               "sensitivity_excluding_all_duplicate_pattern_records": {
                   "remaining_records": len(conservative),
                   "target_detected_below_700C": sum(e["target_present"] for e in conservative if e["temperature_C"] < 700),
                   "target_structure_classes_700C": dict(target_classes)},
               "n_sets_with_json_stoichiometry": sum(x["stoichiometry_in_json"] is not None for x in recipes),
               "n_sets_matched_to_published_SI_recipe": len(recipes),
               "reported_weight_sum_range": [min(sums), max(sums)],
               "distinct_phase_labels": sorted(phases), "by_temperature": by_temp,
               "fixed_hold_h_from_paper_not_table": 4,
               "paper_table_discrepancy": {"precursors": "Li2O + TiO2 + P2O5", "temperature_C": 700,
                                            "paper_p7_target_percent": 54,
                                            "local_table_total_target_percent": comparison["target_wt_percent"],
                                            "status": "unresolved; different source values, not replicate error"},
               "limits": ["No replicate identifiers or per-row timing metadata",
                          "Repeated identical XRD arrays do not constitute independent measurements",
                          "Not listed means not reported/detected; no detection limit supplied",
                          "Normalised semiquantitative crystalline fractions do not measure absolute conversion",
                          "Structure IDs are retained; crystal-name mapping is not independently verified",
                          "Adaptive precursor selection prevents population-frequency claims"]}
    return ds, {"summary": summary, "recipe_mapping": recipes,
                "duplicate_XRD_records": {key: group for key, group in xrd_groups.items() if len(group) > 1}}


def synthetic_demo():
    """An exact algebraic ambiguity, checked against the existing shared ODE model."""
    hold_min, ref_C, target = 240.0, 700.0, 0.60
    # Base model n=1, Ea=120 kJ/mol; all alternative n use the same fixed-hold curve.
    a = np.log(-np.log1p(-target))
    b = 120.0
    temperatures = np.array([400.0, 500.0, 600.0, 700.0])
    times = np.linspace(0.0, 480.0, 161)
    alternatives = []
    worst_error = 0.0
    for n in (0.6, 1.0, 2.0, 3.0):
        k, ea = float(np.exp(a / n) / hold_min), b / n
        fixed = lambda value: {"value": value, "fixed": True}
        mech = {"id": "synthetic_fixed_time_ambiguity", "description": "Synthetic unit-pool A to B; not LTOPO chemistry",
                "conservation": {"basis": "elements", "elements": ["Ti"]},
                "species": [{"id": "A", "composition": {"Ti": 1}}, {"id": "B", "composition": {"Ti": 1}}],
                "reactions": [{"id": "R1", "reactants": [{"species": "A", "coeff": 1}],
                               "products": [{"species": "B", "coeff": 1}],
                               "rate_law": {"family": "mass_action", "params": {"k": fixed(k)},
                                            "temperature_dependence": {"Ea_kJ_mol": fixed(ea), "T_ref_C": ref_C},
                                            "time_modulation": {"kind": "avrami", "n": fixed(n)}}}]}
        jsonschema.Draft202012Validator(json.loads((ROOT / "schema/mechanism.schema.json").read_text())).validate(mech)
        compiled = compile_mechanism(mech, Conditions(None, None, ref_C, n_temperatures=4))
        numerical, analytic = [], []
        for temp in temperatures:
            cond = Conditions(None, None, float(temp))
            numerical.append(float(compiled.simulate([], [0.0, hold_min], {"A": 1.0}, conditions=cond)[1, -1]))
            k_t = k * np.exp(-ea * 1e3 / R * (1 / (temp + 273.15) - 1 / (ref_C + 273.15)))
            analytic.append(float(-np.expm1(-(k_t * hold_min) ** n)))
        trajectory = -np.expm1(-(k * times) ** n)
        ode_curve = compiled.simulate([], times, {"A": 1.0})[1]
        worst_error = max(worst_error, float(np.max(np.abs(np.array(numerical) - analytic))),
                          float(np.max(np.abs(ode_curve - trajectory))))
        alternatives.append({"n": n, "k_ref_per_min": k, "Ea_kJ_per_mol": ea,
                             "endpoint_4h_analytic": analytic, "endpoint_4h_shared_ODE": numerical,
                             "B_fraction_1h_at_700C": float(-np.expm1(-(k * 60) ** n)),
                             "trajectory_700C": trajectory.tolist()})
    endpoint_spread = float(np.ptp([x["endpoint_4h_analytic"] for x in alternatives], axis=0).max())

    # Jacobian of log(-log(1-f)) wrt [log(k_ref), Ea(kJ/mol), n] at the n=1 base.
    def jacobian(designs):
        rows = []
        k_ref = np.exp(a) / hold_min
        for time, temp in designs:
            delta = 1 / (temp + 273.15) - 1 / (ref_C + 273.15)
            rows.append([1.0, -1e3 / R * delta, np.log(k_ref * time) - b * 1e3 / R * delta])
        return np.array(rows)
    designs = [(hold_min, float(t)) for t in temperatures]
    ranks = [int(np.linalg.matrix_rank(jacobian(d), tol=1e-9))
             for d in (designs, designs + [(60.0, ref_C)])]
    if endpoint_spread > 1e-12 or worst_error > 5e-5 or ranks != [2, 3]:
        raise AssertionError((endpoint_spread, worst_error, ranks))
    return {"source_type": "synthetic analytical example; NOT fitted to LTOPO",
            "initial_state": {"A": 1.0, "B": 0.0}, "temperatures_C": temperatures.tolist(),
            "time_min": times.tolist(), "hold_min": hold_min, "reference_temperature_C": ref_C,
            "alternatives": alternatives, "maximum_analytic_endpoint_spread": endpoint_spread,
            "maximum_shared_ODE_vs_analytic_error": worst_error,
            "jacobian_rank_fixed_4h_three_parameters": ranks[0],
            "jacobian_rank_with_one_added_1h_700C_point": ranks[1],
            "parameter_combinations": ["n * log(k_ref * t_hold)", "n * Ea"],
            "interpretation": "A second time breaks this specific toy ambiguity; it does not prove real network identifiability"}


def make_plots(summary, demo, out_dir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False,
                         "svg.fonttype": "none", "savefig.dpi": 180})

    fig, (ax, bx) = plt.subplots(1, 2, figsize=(11, 4.8), layout="constrained")
    rows = summary["by_temperature"]
    x = np.arange(len(rows))
    total = np.array([r["n_endpoints"] for r in rows])
    detected = np.array([r["n_target_detected"] for r in rows])
    ax.bar(x, total, color="#d9dfe5", label="No target reported")
    ax.bar(x, detected, color="#0072B2", label="Target reported")
    for i, (num, den) in enumerate(zip(detected, total)):
        ax.text(i, den + .35, f"{num}/{den}", ha="center")
    ax.set(xticks=x, xticklabels=[f"{r['temperature_C']:g}" for r in rows], xlabel="Hold temperature (°C)",
           ylabel="Number of endpoints", ylim=(0, 19), title="A  Target appears only at 700 °C")
    ax.legend(loc="upper left", fontsize=9)
    high = next(r for r in rows if r["temperature_C"] == 700)["target_structure_classes"]
    values = [high.get("both", 0), high.get("2_only", 0), high.get("62_only", 0)]
    bx.bar(np.arange(3), values, color=["#009E73", "#0072B2", "#D55E00"])
    for i, v in enumerate(values):
        bx.text(i, v + .2, str(v), ha="center")
    bx.set(xticks=np.arange(3), xticklabels=["Both IDs", "ID 2 only", "ID 62 only"],
           ylabel="Precursor sets at 700 °C", ylim=(0, 13), title="B  Two target structures often coexist")
    fig.suptitle("LTOPO: what the local ARROWS table reports", fontsize=15)
    fig.supxlabel(f"{summary['counts']['entries_kept']} endpoint records / {summary['unique_XRD_xy_arrays']} unique XRD patterns"
                  " • 4 h hold from paper • structure IDs retained", fontsize=10)
    for ext in ("png", "svg"):
        fig.savefig(out_dir / f"endpoint_counts.{ext}")
    plt.close(fig)

    fig, (ax, bx) = plt.subplots(1, 2, figsize=(11, 4.8), layout="constrained")
    palette = ["#0072B2", "#E69F00", "#009E73", "#CC79A7"]
    patterns = ["-", "--", "-.", ":"]
    for alt, color, pattern in zip(demo["alternatives"], palette, patterns):
        label = f"n={alt['n']:g}; Ea={alt['Ea_kJ_per_mol']:g} kJ/mol"
        ax.plot(demo["temperatures_C"], alt["endpoint_4h_analytic"], color=color, ls=pattern, lw=2.6,
                marker="o", markersize=7, label=label)
        bx.plot(np.array(demo["time_min"]) / 60, alt["trajectory_700C"], color=color, ls=pattern, lw=2.2)
    ax.set(xlabel="Temperature (°C)", ylabel="Synthetic B fraction after 4 h", ylim=(-.02, .85),
           title="A  Four rate models give the same endpoints")
    ax.legend(fontsize=9, loc="upper left")
    bx.axvline(4, color="#555555", lw=1)
    bx.axvline(1, color="#555555", lw=1, ls="--")
    bx.text(4.12, .05, "same at 4 h", rotation=90, fontsize=10)
    bx.text(1.12, .6, "measure at 1 h", rotation=90, fontsize=10)
    bx.set(xlabel="Time at 700 °C (h)", ylabel="Synthetic B fraction", ylim=(-.02, 1.03),
           title="B  An earlier measurement separates them")
    fig.suptitle("SYNTHETIC illustration: an endpoint cannot settle these rates", fontsize=15)
    fig.supxlabel("Assumed A → B, known initial A=1 • not fitted to LTOPO • shared ODE engine checked against exact solution", fontsize=10)
    for ext in ("png", "svg"):
        fig.savefig(out_dir / f"synthetic_time_ambiguity.{ext}")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exp", type=Path, default=ROOT / "literature/04_synthesis/ExpLTOPO.json")
    parser.add_argument("--settings", type=Path, default=ROOT / "literature/04_synthesis/SettingsLTOPO.json")
    parser.add_argument("--private-out", type=Path, default=ROOT / "data/arrows3/ltopo_oct22")
    parser.add_argument("--figure-out", type=Path, default=ROOT / "docs/examples/ltopo_oct22")
    args = parser.parse_args()
    # Do not accidentally export the licensed row-level data into a tracked directory.
    if not args.private_out.resolve().is_relative_to((ROOT / "data/arrows3").resolve()):
        parser.error("--private-out must remain inside the ignored data/arrows3 directory")
    ds, report = audit(args.exp, args.settings)
    demo = synthetic_demo()
    args.private_out.mkdir(parents=True, exist_ok=True)
    args.figure_out.mkdir(parents=True, exist_ok=True)
    for filename, obj in (("endpoint_dataset.json", ds), ("audit.json", report)):
        (args.private_out / filename).write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")
    # No precursor-specific experimental rows are exported with the aggregate figure.
    (args.figure_out / "synthetic_demonstration.json").write_text(json.dumps(demo, indent=2, allow_nan=False) + "\n")
    make_plots(report["summary"], demo, args.figure_out)
    print(json.dumps({"audit": report["summary"], "synthetic_verification": {k: v for k, v in demo.items()
                     if k not in {"alternatives", "time_min"}}}, indent=2))


if __name__ == "__main__":
    main()
