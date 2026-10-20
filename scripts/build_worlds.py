#!/usr/bin/env python3
"""Generate the benchmark world files in worlds/ (task.schema.json instances).

Parameters marked CALIBRATED come from least-squares fits to the real Liao 2025 curves
(see docs/SPEC.md section 7). Parameters marked ILLUSTRATIVE are placeholders chosen to make
the motif behave sensibly; replace them with published values once the Katsounaros 2012 /
Polatides 2005 tables have been checked against the PDFs.

Usage: python scripts/build_worlds.py worlds
"""
import json
import sys
from pathlib import Path

SPECIES = {
    "NO3": dict(id="NO3", label="NO3-", formula="NO3-", role="reactant", observable=True, N_oxidation_state=5),
    "NO2": dict(id="NO2", label="NO2-", formula="NO2-", role="intermediate", observable=True, N_oxidation_state=3),
    "NH3": dict(id="NH3", label="NH3/NH4+ (lumped)", formula="NH3", role="product", observable=True, N_oxidation_state=-3),
    "SINK": dict(id="SINK", label="N2/N2O (not measured)", formula="N2", role="sink", observable=False,
                 n_N_per_molecule=2, N_oxidation_state=0),
    "X": dict(id="X", label="hidden intermediate (e.g. NO/NH2OH-like)", role="hidden_intermediate", observable=False,
              N_oxidation_state=None),
    "N2": dict(id="N2", label="N2 (N-equivalent basis)", formula="N2", role="product", observable=True,
               N_oxidation_state=0),
    "N2O": dict(id="N2O", label="N2O (N-equivalent basis)", formula="N2O", role="product", observable=True,
                N_oxidation_state=1),
}


def p(value, unit="min^-1", bounds=None, source=None):
    d = {"value": value, "unit": unit}
    if bounds:
        d["bounds"] = bounds
    if source:
        d["source"] = source
    return d


def rxn(rid, a, b, k, e, mod=None, pot=None, src=None):
    rl = {"family": "mass_action", "params": {"k": p(k, bounds=[1e-6, 10.0], source=src)}}
    if mod:
        rl["time_modulation"] = {"kind": mod[0], "tau_min": p(mod[1], "min", [1, 1e5], src)}
    if pot:
        rl["potential_dependence"] = {"alpha": p(pot, "1", [0.0, 2.0], src), "E_ref_V": -0.6}
    return {"id": rid, "reactants": [{"species": a, "coeff": 1}], "products": [{"species": b, "coeff": 1}],
            "electrons": e, "rate_law": rl}


def mech(mid, desc, motif, sp, rxns):
    return {"id": mid, "description": desc, "motif": motif, "species": [SPECIES[s] for s in sp], "reactions": rxns}


def task(tid, title, diff, ref, gt, obs, design, budget, lib=None, plaus=None, metrics=None):
    t = {"id": tid, "title": title, "difficulty": diff, "reference": ref, "ground_truth": gt,
         "observation": obs, "design_space": design, "budget": budget,
         "scoring": {"metrics": metrics or ["exact_network_recovery", "reaction_f1", "parameter_rel_error",
                                            "heldout_nmsle", "identifiability_flag_accuracy"],
                     "pass_threshold_rmsle": 0.05}}
    if lib:
        t["candidate_library"] = lib
    if plaus:
        t["plausibility_constraints"] = plaus
    return t


NOISE = {"relative_sigma": 0.05, "absolute_sigma_mM": 0.1, "outlier_prob": 0.0, "outlier_scale": 0.0}


def build():
    worlds = {}

    # W1: closed series, ILLUSTRATIVE
    gt = mech("w1_series", "NO3- -> NO2- -> NH3, closed mass balance.", "series", ["NO3", "NO2", "NH3"],
              [rxn("R1", "NO3", "NO2", 0.03, 2, src="ILLUSTRATIVE"), rxn("R2", "NO2", "NH3", 0.08, 6, src="ILLUSTRATIVE")])
    worlds["W1_series_closed"] = task(
        "W1_series_closed", "Closed series NO3- to NH3 (sanity world)", "easy",
        {"notes": "Sanity check; every method should recover this. Parameters illustrative."}, gt,
        {"observed_species": ["NO3", "NO2", "NH3"], "sampling_times_min": [0, 10, 20, 30, 45, 60, 90, 120, 180],
         "noise": NOISE},
        {"potential_V_vs_RHE": [-0.6], "pH": [7.0], "c0_mM_N": [100.0]}, {"max_experiments": 1, "points_per_experiment": 9})

    # W2: Liao 50b CALIBRATED: direct branch + deactivation + nitrate sink
    src = "CALIBRATED to liao2025_mos2_suppfig50b (docs/SPEC.md s7)"
    gt = mech("w2_liao50b", "Series + direct NO3->NH3 branch + nitrate-side N sink, catalyst deactivation. Calibrated to Liao 2025 Supp. Fig. 50b.",
              "series_with_sink", ["NO3", "NO2", "NH3", "SINK"],
              [rxn("R1", "NO3", "NO2", 4.0e-4, 2, ("deactivation", 368), src=src),
               rxn("R2", "NO2", "NH3", 2.7e-3, 6, ("deactivation", 368), src=src),
               rxn("R3", "NO3", "NH3", 3.7e-3, 8, ("deactivation", 368), src=src),
               rxn("R4", "NO3", "SINK", 1.5e-3, 5, ("deactivation", 368), src=src)])
    worlds["W2_liao_sink_deactivation"] = task(
        "W2_liao_sink_deactivation", "Parallel branches, N sink and catalyst deactivation (calibrated to real data)", "hard",
        {"citation": "Liao et al. Nat. Commun. 2025", "doi": "10.1038/s41467-025-60671-y",
         "real_dataset_ids": ["liao2025_mos2_suppfig50b", "liao2025_wmos2_suppfig50a"],
         "notes": "Fit RMSE about 3-4 mM-N on the real curves. Leak placement (NO3 vs NO2) is weakly identified."},
        gt,
        {"observed_species": ["NO3", "NO2", "NH3"],
         "sampling_times_min": [0, 10, 20, 30, 40, 50, 60, 80, 100, 120, 150, 180, 360, 720, 1080, 1440, 2160, 2880],
         "noise": {"relative_sigma": 0.04, "absolute_sigma_mM": 0.3, "outlier_prob": 0.03, "outlier_scale": 0.3},
         "missing_species_note": "SINK (N2/N2O) is never observed; closure gap is the only evidence."},
        {"potential_V_vs_RHE": [-0.6], "pH": [7.0], "c0_mM_N": [50.0, 100.0]},
        {"max_experiments": 3, "points_per_experiment": 18},
        lib={"mechanism_ids": ["series_closed", "series_sink_NO3", "series_sink_NO2", "parallel_sink_NO3_deact"]},
        plaus={"rate_constant_bounds_min_inv": [1e-6, 10.0]},
        metrics=["exact_network_recovery", "reaction_f1", "parameter_rel_error", "heldout_nmsle",
                 "identifiability_flag_accuracy", "experiments_to_recovery"])

    # W3: hidden intermediate, PUBLISHED constants (Katsounaros 2012, "model B", Eqs. 8-13, Table 1)
    src = "Katsounaros et al. 2012, Electrochim. Acta 71:270, Table 1 (posterior means, min^-1)"
    gt = mech("w3_katsounaros_modelB",
              "Katsounaros 2012 model B: NO3- -> NO2-; NO2- -> X (hidden) -> N2; NO2- -> NH3; NO2- -> N2O. "
              "Eqs. (8)-(13) taken 1:1 in N-equivalents; this reproduces the paper's Fig. 1 curves.",
              "hidden_intermediate", ["NO3", "NO2", "X", "N2", "N2O", "NH3"],
              [rxn("R1", "NO3", "NO2", 0.0216, 2, src=src), rxn("R2", "NO2", "X", 0.0292, None, src=src),
               rxn("R3", "X", "N2", 0.0219, None, src=src), rxn("R4", "NO2", "NH3", 0.0021, 6, src=src),
               rxn("R5", "NO2", "N2O", 0.0048, 2, src=src)])
    worlds["W3_katsounaros_hidden_intermediate"] = task(
        "W3_katsounaros_hidden_intermediate", "Hidden intermediate between nitrite and N2 (Katsounaros 2012 model B)", "hard",
        {"citation": "Katsounaros, Dortsiou, Polatides, Preston, Kypraios, Kyriacou, Electrochim. Acta 71 (2012) 270-276",
         "notes": "Rate constants are the published Table 1 values. 0.5 M NaNO3 + 1 M NaOH, Sn, -2.2 V vs Ag/AgCl (about -1.2 V vs RHE "
                  "before iR correction, rough conversion). Paper observed NO3, NO2, N2, N2O, NH3 and attributed the lost mass balance "
                  "to X; in this model X peaks at about 24% of total N. Real curves still to be digitized (literature/02_kinetics_benchmarks).",
         "real_dataset_ids": []},
        gt,
        {"observed_species": ["NO3", "NO2", "N2", "N2O", "NH3"], "sampling_times_min": [0, 30, 60, 90, 120, 150, 180],
         "noise": {"relative_sigma": 0.08, "absolute_sigma_mM": 3.0, "outlier_prob": 0.0, "outlier_scale": 0.0},
         "missing_species_note": "X is never observed; the N-closure deficit is the only evidence."},
        {"potential_V_vs_RHE": [-1.2], "pH": [14.0], "c0_mM_N": [500.0]},
        {"max_experiments": 1, "points_per_experiment": 7},
        plaus={"max_hidden_fraction_of_total_N": 0.30})

    # W5: potential dependent, parameters from Polatides & Kyriacou 2005 (Sn85Cu15, Figs. 3 and 6, section 3.3)
    # Rate constants are the printed values at -2.0 V vs Ag/AgCl converted to min and mM-N units:
    # k1 4.9e-4 s^-1 -> 0.0294 min^-1; k2 1.76e-4 s^-1 (abstract's 1.76e-5 is a typo, see SPEC 7c) -> 0.01056 min^-1;
    # k3 7.66e-3 L mol^-1 s^-1 -> 4.60e-4 mM^-1 min^-1 (second order, 2 NO2- -> N2, so SINK is on the mM-N basis).
    # Alphas: paper's slopes of ln k2, ln k3 vs E (Fig. 6): 0.131, 0.089. k1 is diffusion limited between
    # -1.7 and -2.0 V and the paper gives no alpha for it, so R1 gets 0 (bounds still allow a fit).
    # The world's potential axis is V vs RHE; the paper's -2.0 V vs Ag/AgCl is mapped at an assumed pH 7
    # (E_RHE = E_Ag/AgCl + 0.197 + 0.059 pH = -1.39 V). Catholyte pH actually drifted basic, so this offset
    # is approximate; it shifts E_ref only and does not touch the alphas (slopes).
    src = "Polatides & Kyriacou 2005, J. Appl. Electrochem. 35:421, Sn85Cu15, -2.0 V vs Ag/AgCl"
    src_a = src + " (apparent alpha from Fig. 6 slope; 4 points)"
    src_k1 = src + "; nitrate step diffusion limited at -1.7 to -2.0 V, alpha not reported, set to 0"
    E_ref = -1.39
    def r5(rid, a, b, k, e, alpha, s, ksrc=src, kind="mass_action"):
        rl = {"family": "mass_action", "params": {"k": p(k, bounds=[1e-6, 10.0], source=ksrc)},
              "potential_dependence": {"alpha": p(alpha, "1", [0.0, 2.0], s), "E_ref_V": E_ref}}
        return {"id": rid, "reactants": a, "products": b, "electrons": e, "rate_law": rl}
    gt = mech("w5_potential", "Polatides scheme: NO3->NO2->NH3 plus second-order 2 NO2->N2 (SINK), each step with its own Tafel-like potential dependence.",
              "series_parallel", ["NO3", "NO2", "NH3", "SINK"],
              [r5("R1", [{"species": "NO3", "coeff": 1}], [{"species": "NO2", "coeff": 1}], 0.0294, 2, 0.0, src_k1),
               r5("R2", [{"species": "NO2", "coeff": 1}], [{"species": "NH3", "coeff": 1}], 0.01056, 6, 0.131, src_a),
               r5("R3", [{"species": "NO2", "coeff": 2}], [{"species": "SINK", "coeff": 2}], 4.6e-4, 6, 0.089, src_a)])
    worlds["W5_potential_dependent"] = task(
        "W5_potential_dependent", "Potential-dependent branching ratio", "medium",
        {"citation": "Polatides & Kyriacou 2005, J. Appl. Electrochem. 35:421-427",
         "notes": "Branching ratio R2/R3 shifts with E (alphas 0.131 vs 0.089 from Fig. 6; R3 is second order in nitrite so branching also depends on nitrite level). Single-potential data cannot separate alphas. Rate constants at -2.0 V vs Ag/AgCl (about -1.39 V vs RHE at assumed pH 7); only 4 potentials (-1.6 to -2.0 V) were measured."},
        gt,
        {"observed_species": ["NO3", "NO2", "NH3"], "sampling_times_min": [0, 10, 20, 40, 60, 90, 120, 180],
         "noise": NOISE},
        {"potential_V_vs_RHE": [-1.79, -1.39], "pH": [7.0], "c0_mM_N": [50.0],
         "initial_conditions": [{"potential_V_vs_RHE": -1.39, "pH": 7.0, "c0_mM_N": 50.0}]},
        {"max_experiments": 5, "points_per_experiment": 8})

    # candidate library for W2
    lib = {}
    def lm(mid, desc, motif, sp, rxns):
        lib[mid] = mech(mid, desc, motif, sp, rxns)
    lm("series_closed", "NO3->NO2->NH3", "series", ["NO3", "NO2", "NH3"],
       [rxn("R1", "NO3", "NO2", 1e-3, 2), rxn("R2", "NO2", "NH3", 1e-2, 6)])
    lm("series_sink_NO3", "series + NO3->SINK", "series_with_sink", ["NO3", "NO2", "NH3", "SINK"],
       [rxn("R1", "NO3", "NO2", 1e-3, 2), rxn("R2", "NO2", "NH3", 1e-2, 6), rxn("R3", "NO3", "SINK", 1e-3, 5)])
    lm("series_sink_NO2", "series + NO2->SINK", "series_with_sink", ["NO3", "NO2", "NH3", "SINK"],
       [rxn("R1", "NO3", "NO2", 1e-3, 2), rxn("R2", "NO2", "NH3", 1e-2, 6), rxn("R3", "NO2", "SINK", 1e-3, 3)])
    lm("parallel_sink_NO3_deact", "direct branch + sink + deactivation", "series_with_sink", ["NO3", "NO2", "NH3", "SINK"],
       [rxn("R1", "NO3", "NO2", 4e-4, 2, ("deactivation", 400)), rxn("R2", "NO2", "NH3", 3e-3, 6, ("deactivation", 400)),
        rxn("R3", "NO3", "NH3", 4e-3, 8, ("deactivation", 400)), rxn("R4", "NO3", "SINK", 1e-3, 5, ("deactivation", 400))])
    return worlds, lib


def main():
    out = Path(sys.argv[1])
    (out / "library").mkdir(parents=True, exist_ok=True)
    worlds, lib = build()
    for k, v in worlds.items():
        (out / f"{k}.json").write_text(json.dumps(v, indent=2) + "\n")
    for k, v in lib.items():
        (out / "library" / f"{k}.json").write_text(json.dumps(v, indent=2) + "\n")
    print(f"wrote {len(worlds)} worlds and {len(lib)} library mechanisms to {out}")


if __name__ == "__main__":
    main()
