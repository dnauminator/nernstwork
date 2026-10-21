# nernstwork: spec (v0.1, draft for the Oct 21-22 2026 hackathon)

Working name. Infers branched reaction networks from multi-species time-course data, reports what the data cannot resolve, and proposes the next experiment.

## 1. Goal and scope

Given time courses of some species from an electrochemical (or other) conversion, return: a ranked set of candidate mechanisms (network + rate laws), parameter posteriors, an explicit list of unidentifiable parameters and unobserved N sinks, and the next experiments that would best separate the surviving candidates.

Primary demo: electrochemical nitrate reduction (NO3RR), because the branch points (NO2-, NH2OH, N2/N2O, NH3, HER competition) are real, the data are published, and mass balance routinely fails to close. Generalization module (stretch): a catalyst-synthesis stage whose product phase is a branch point, feeding a downstream NO3RR network as a "catalyst-state vector". Not required for the demo.

Out of scope for v0.1: spatial transport models, DFT, microkinetic mechanisms with surface coverages, CO2RR.

## 1b. Direction change (Oct 20): from NO3RR mechanisms to synthesis branch points

Decision (Daniel, Oct 20): the hackathon project moves from inferring NO3RR mechanisms to inferring **solid-state synthesis pathways**, to avoid overlap with ongoing work outside the hackathon. Same engine (propose a candidate network, fit, critique for plausibility, report what the data cannot settle, plan the next experiment), different domain. Everything in sections 3-9 about NO3RR stays as the validated test bed and as the downstream illustration described below. Sections 7e and 11 are the new material; the rest of the document is unchanged unless a section says otherwise.

Why synthesis fits the engine. In a solid-state synthesis the precursor set and temperature decide which intermediates form, and some intermediates consume the driving force needed for the target (the ARROWS3 and Miura et al. picture). That is a branched network with hidden intermediates and a "what is not observed" problem, which is what the engine reports on.

Two links to NO3RR, one of them an assumption. (1) The engine and its worlds (W1-W5) already exist and are the sanity test bed. (2) A catalyst-state vector (phase fractions out of the synthesis model) could feed the NO3RR toy model as modifiers on its rate constants. No dataset ties a synthesis outcome to NO3RR rate constants, and none of the three ARROWS3 targets (YBCO, Na2Te3Mo3O16, LiTiOPO4) is an NO3RR catalyst, so this link is a hypothetical mapping. In any demo it is labelled illustrative and is never presented as a prediction. Use only catalysts from public publications.

Status: pivot is proposed, data check is partly done (section 7e). Go/no-go inputs: the YBCO table is present and usable (done); NTMO and LTOPO tables not inspected; the curated kickoff datasets are unknown.

## 2. What is already known (prior art, one line each)

- SiMBA: simplest-mechanism-first enumeration with AIC, handles unobserved intermediates.
- Kay & Zhang (JCIM 2026): sparse network identification + symbolic regression + model-based design of experiments; assumes full observability and noise-free data.
- Model Discovery Agent: LLM proposes models, BIC scores, expected information gain picks experiments.
- "Learning to Outgrow a Theory": model-class revision; 89.5% exact recovery on 400 simulated environments.
- Sanofi SKAI: Bayesian inference, LLM text-to-equation spec, classifiers on in-silico mechanisms, design of experiments.
- DASyR-LLM: LLM plausibility critic inside a symbolic-regression loop; notes AIC can favor simple wrong models. No code found.
- LLM-AutoSciLab / ActiveSciBench: static enzyme rate laws. Reactive SINDy, CRNN, stoichiometrically informed SR: partial-observability and noise limits.

The gap we target: potential/pH-dependent electrochemical kinetics, real digitized or Source-Data curves rather than only simulations, hidden intermediates where BIC prefers an unphysical model, and identifiability reporting as a first-class output.

## 3. Conventions

- State variables: mM of nitrogen (mM-N). Stoichiometry is per N-equivalent. `ug N/mL / 14.007 = mM-N`.
- Time in minutes. Potential in V vs RHE. Temperature in C.
- NH4+/NH3 lumped as `NH3`. H, O, charge are implicit; electron count is carried per reaction and checked against N oxidation states (NO3- +5, NO2- +3, N2 0, NH3 -3).
- Hidden species have `observable: false` and `N_oxidation_state: null`; their reactions carry `electrons: null`.

## 4. Abstractions and files

| Object | Schema | Meaning |
|---|---|---|
| Mechanism | `schema/mechanism.schema.json` | species, reactions, rate laws, parameters with bounds/priors |
| Dataset | `schema/dataset.schema.json` | real measurements with provenance, units, N-closure, quality flags |
| Task (world) | `schema/task.schema.json` | hidden ground truth, observation/noise model, design space, budget, scoring |
| Result | `schema/result.schema.json` | candidates, fits, plausibility, identifiability, selected model, proposed experiments |

Semantic checks the schemas cannot express live in `nernstwork.validate_mechanism` (unknown species, N conservation, electron count vs oxidation states, Langmuir needs K).

### Rate-law registry (v0.1)

| Family / modifier | Form | Status |
|---|---|---|
| `mass_action` | r = k * prod c_i^coeff_i | implemented |
| `power_law` | r = k * prod c_i^order_i | implemented |
| `langmuir_saturation` | r = k c / (1 + c/K) | implemented |
| `potential_dependence` | k * exp(alpha F (E_ref - E)/(R T)), alpha lumped, not restricted to (0,1) | implemented |
| `ph_dependence` | k * 10^(-order (pH - pH_ref)) | implemented |
| `k_mt` | 1/k_eff = 1/k + 1/k_mt | implemented |
| `time_modulation` | activation 1 - exp(-t/tau); deactivation exp(-t/tau) | implemented, added after real-data calibration (section 7) |
| Avrami/JMAK | phase-transformation step for the synthesis module | not implemented (stretch) |

## 5. Benchmark worlds (`worlds/`, generated by `scripts/build_worlds.py`)

| World | Motif | Source of parameters | What it tests |
|---|---|---|---|
| W1_series_closed | series | illustrative | sanity: every method should pass |
| W2_liao_sink_deactivation | series + direct branch + N sink + deactivation | calibrated to Liao Supp. Fig. 50b | sink placement, catalyst-state term, identifiability |
| W3_katsounaros_hidden_intermediate | NO3- -> NO2- -> hidden X -> N2, plus NO2- -> NH3 and NO2- -> N2O | published: Katsounaros 2012 model B, Table 1 constants (min^-1) | does the method invent X, and how big does it let X get (about 24% of total N here; `max_hidden_fraction_of_total_N`) |
| W5_potential_dependent | series + second-order NO2- -> N2 sink, per-step alpha | published: Polatides 2005 constants at -2.0 V vs Ag/AgCl and Fig. 6 alphas (section 7d) | branching ratio shifts with E, experiment design across potential |

W4 (the "Model B trap": a candidate that wins on BIC but needs an implausibly large hidden pool) is deliberately not generated yet. Katsounaros 2012 reports model A (no hidden species) against model B (hidden X) with a Bayes factor of 2921 favouring B. W4 should be built from the digitized Fig. 1 data by fitting both models and checking that we reproduce that comparison (section 8); a trap with synthetic parameters would be arbitrary.

W3 uses the published Table 1 constants; with them the simulator reproduces the paper's Fig. 1 curves to within eyeballed reading error (the test is coarse until Fig. 1 is digitized). W1 is still illustrative and labelled so in its `source` fields. W5 now uses the Polatides 2005 constants and Fig. 6 alphas (section 7d).

## 6. Observation and noise model

Observed value = true * (1 + N(0, relative_sigma)) + N(0, absolute_sigma_mM), with optional outlier replacement (`outlier_prob`, `outlier_scale`), motivated by real data where an adjacent-point nitrite jump appears. Unobserved species are dropped; the N-closure deficit is the only evidence for sinks. Scoring uses held-out conditions (`heldout_nmsle`, pass threshold RMSLE 0.05) plus structure metrics (`exact_network_recovery`, `reaction_f1`, `trap_avoided`, `identifiability_flag_accuracy`, `experiments_to_recovery`).

## 7. What the real data say (first calibration)

Data: Liao et al. Nat. Commun. 2025 (doi 10.1038/s41467-025-60671-y) Source Data, Supp. Figs. 49, 50a, 50b. 0.5 M K2SO4 + 100 mM KNO3, H-cell, -0.6 V vs RHE (Fig. 49 is not stated in its caption, but its values are identical to Supp. Fig. 48, which states -0.6 V; confirmed Oct 19). Fig. 49: 12 points over 180 min, N closure 0.95-1.01. Fig. 50a/b: 18 points over 48 h, closure drops to about 0.77 by 3 h and 0.67-0.74 at 48 h. Catalyst assignment for Fig. 50a/b is from the caption (W-MoS2 / MoS2).

Calibration (`scripts/calibrate_liao.py`, least squares on scaled residuals, grid of starts, no uncertainty):

| Dataset | Model | RMSE NO3 / NO2 / NH3 (mM-N) |
|---|---|---|
| Fig. 49 | plain first-order series with leak | about 10 / 2 / 8 |
| Fig. 49 | + direct NO3->NH3 branch, no time term | 8.4 / 1.1 / 7.2 |
| Fig. 49 | + direct branch + activation (tau about 70 min) | 2.1 / 0.7 / 2.3 |
| Fig. 50a | + direct branch + deactivation, no sink | 15.7 / 0.7 / 4.3 |
| Fig. 50a | + direct branch + deactivation + NO3 sink (about 31 mM-N at 48 h) | 2.7 / 0.7 / 2.5 |
| Fig. 50b | no sink | 12.2 / 0.6 / 5.8 |
| Fig. 50b | + NO3 sink (about 23 mM-N at 48 h) | 3.4 / 0.7 / 3.9 |

Takeaways, with limits:

1. A plain NO3 -> NO2 -> NH3 series with first-order steps does not describe these curves. The registry needed a direct NO3 -> NH3 branch and a catalyst-state term. This is a real "model-class revision" case, and it is why `time_modulation` exists.
2. In Fig. 50 the sink is statistically demanded (RMSE on nitrate falls from 12-16 to 3-4 mM-N), consistent with the closure gap.
3. Not established: whether the sink hangs off NO3 or NO2 (the NO3 and NO2 placements gave similar costs in the earlier test), whether "deactivation" is really catalyst fouling or unbuffered-pH drift (pH not reported, treat as unknown), and any parameter uncertainty. Fits are single-start point estimates, and AIC/BIC comparison is not done yet.

## 7b. First digitized dataset: Katsounaros 2012 Fig. 1

Seven time points (0-180 min) for NO3, NO2, N2, N2O, NH3 in 0.5 M NaNO3 + 1 M NaOH on Sn, converted to mM-N (c0 = 500). Compared with the published model B (Table 1 constants) simulated by `nernstwork`: RMSE is 9, 16, 11, 6 and 4 mM-N for NO3, NO2, N2, N2O and NH3 (about 1-3% of c0), with the largest single residual 30 mM-N (NO2 at 30 min, where the figure itself shows the point below the curve). So the simulator and the published constants reproduce the real data to about the scatter in the paper's own fit.

The five measured species sum to only 358-422 mM-N after t = 0, so 78-142 mM-N (16-28% of total N) is unaccounted for. The model's hidden X peaks at 122 mM-N (24%) around 85 min, while the digitized deficit peaks around 60 min at about 142 mM-N (28%). That is close to the 0.30 plausibility cap in W3, and the digitized deficit combines measurement scatter from five species, so treat the 28% as an upper-end estimate. Model B places the hidden pool later than the data deficit suggests.

Caveat from the data, not the model: N2 and N2O are taken as N-equivalents. The sums never exceed 500, which agrees, but confirm against the paper text.

## 7c. Katsounaros 2008 and Polatides 2005 (digitized)

**Katsounaros 2008 Fig. 2** (`katsounaros2008_fig2_sn_nacl_1M`): 1 M NaNO3 + 1 M NaCl on Sn at -2.8 V vs Ag/AgCl, 14-15 time points to 210 min. N2 and N2O are plotted per molecule; converting them x2 closes the balance (993 of 1000 mM-N at 210 min) and reproduces the paper's final distribution (N2 83.5%, N2O 5.7%, NH3 8.6% of N against the paper's 85.7 / 6 / 8.9). The dataset labelled "Ag/AgCl" in the WebPlotDigitizer export is the authors' plotted loss of mass balance, stored as `quality.reported_n_loss`. It peaks at 261 mM-N (26% of N) at 90 min and returns to about 0 at 210 min; our own closure deficit tracks it to within about 6-16 mM-N. So the hidden pool is transient and fully converted, which is what a hidden intermediate between nitrite and N2 predicts.

Structure and rate-law fits (`scripts/calibrate_katsounaros2008.py`, point estimates, no uncertainty):

| Model | Parameters | RMSE (mM-N) | BIC |
|---|---|---|---|
| A: no hidden species | 4 | 59 | 589 |
| B: hidden X between nitrite and N2 | 5 | 37 | 528 |
| B with Langmuir-saturating nitrate step (K about 146 mM) | 6 | 15 | 404 |

Both the hidden species and the saturating rate law are demanded by the data, consistent with the 2012 paper's note that nitrate is first order at low concentration and zero order at high. This is a real-data instance of the structure-versus-rate-law question the benchmark is meant to pose, and the Langmuir family in the registry is exercised by real data. Limits: model B's hidden pool peaks at 239 mM-N at 60 min while the plotted loss peaks at 261 mM-N at 90 min, so the timing of X is not captured well, and the N-loss trace was not used in the fit.

**Polatides 2005 Fig. 3** (`polatides2005_fig3_sn85cu15_50mM`): Sn85Cu15 at -2.0 V vs Ag/AgCl, 50 mM nitrate, 8 points to 120 min. N2 is again per molecule (x2), established from closure only (0.93-1.12, so the paper's scatter is about 10%); flagged `units_unverified` and `noisy`. The paper's scheme is NO3 -> NO2 -> NH3 plus a second-order 2 NO2 -> N2. The printed k2 = 1.76e-5 s^-1 does not reproduce the paper's own NH3 curve (2.2 mM at 120 min against 20.3 digitized); 1.76e-4 s^-1 does (RMSE 1.5 mM), so the printed exponent is probably a typo. A fit of the digitized data gives k1 = 4.2e-4 s^-1, k2 = 1.8e-4 s^-1, k3 = 4.3e-3 L mol^-1 s^-1, against printed k1 = 4.9e-4 and k3 = 7.66e-3. A second-order step is expressible in the schema as a mass_action reaction with coefficient 2, which also makes this the first dataset with a bimolecular branch.

## 7d. Polatides 2005 Fig. 6 and W5

Fig. 6 plots ln k2 and ln k3 against -E (V vs Ag/AgCl), four potentials from -1.6 to -2.0 V. k1 is absent because nitrate reduction is diffusion limited between -1.7 and -2.0 V (the paper's Eq. 8 diffusion estimate is lower than the measured rate, which the authors attribute to forced convection from the He stream and electrode roughness). The plotted k values are in min and mM units: the printed constants at -2.0 V converted to min^-1 and L mmol^-1 min^-1 give ln k2 = -4.55 and ln k3 = -7.69, against digitized -4.51 and -7.69. That conversion also confirms independently that the abstract's k2 = 1.76e-5 s^-1 is a typo for 1.76e-4. Linear fits of the digitized points give slopes 5.17 and 3.50 V^-1 (r = 0.994, 0.935), i.e. alpha 0.133 and 0.090 at 298 K, against the paper's 5.12 (alpha 0.131) and alpha 0.089 (r = 0.994, 0.945).

W5 now carries these values: R1 NO3 -> NO2 k = 0.0294 min^-1, alpha 0 (not reported, diffusion limited); R2 NO2 -> NH3 k = 0.01056 min^-1, alpha 0.131; R3 2 NO2 -> N2 (SINK, mM-N basis) mass action with reactant coefficient 2, k = 4.6e-4 mM^-1 min^-1, alpha 0.089. Anchored at -2.0 V vs Ag/AgCl, which the world file expresses as -1.39 V vs RHE assuming pH 7 (catholyte pH drifted basic, so the offset is approximate; it moves E_ref, not the alphas). Check against the digitized Fig. 3 at E_ref: RMSE 3.4 / 3.0 / 1.6 mM for NO3 / NO2 / NH3 and 5.5 mM-N for N2 (simulated N2 is 23 mM-N at 120 min against 34 digitized, so the printed k3 undershoots the N2 curve). Limits: the alphas are apparent, from four points over a 0.4 V window; they say nothing outside -1.6 to -2.0 V; the paper reports Table 1 selectivities at only two potentials for Sn85Cu15 (-1.6 and -2.0 V), which can serve as a coarse held-out check on W5 (about 86/4/14% NO2/NH3/N2 at -1.6 V against 17/41/35% at -2.0 V, 12 h).

## 7e. Synthesis domain (draft, Oct 20): data, observation model, engine changes

**Data found.**

| Dataset | What it is | State |
|---|---|---|
| ARROWS3 experiments (Szymanski et al., Nat. Commun. 2023, doi 10.1038/s41467-023-42329-9; repo github.com/njszym/ARROWS, archived at doi 10.5281/zenodo.8331001) | YBCO, Na2Te3Mo3O16 (NTMO), triclinic LiTiOPO4 (t-LTOPO) synthesis outcomes by precursor set and temperature, 4 h holds. Paper Table 1: 188 / 46 / 120 "Nexp" over 47 / 23 / 30 precursor sets (YBCO 600-900 C, NTMO 300-400 C, LTOPO 400-700 C). Nexp is sets x temperatures, i.e. the size of the search grid. Methods: for YBCO all possible experiments were run and ARROWS3 was applied post hoc; for NTMO and LTOPO ARROWS3 guided the runs and only part of the grid was sampled | The paper's data availability statement points to the ARROWS3 repository (the Source Data xlsx holds only graph data: yield distributions, success rates, optimisation traces; no per-experiment phase tables). Files `Examples/<TARGET>/Exp.json` are Git LFS pointers; a plain `git clone` leaves 133-byte stubs and the real file comes from `https://media.githubusercontent.com/media/njszym/ARROWS/main/Examples/YBCO/Exp.json` (52 MB). Only the YBCO file has been inspected |
| Precursor Genome (Walters et al., arXiv:2607.09903, July 2026) | 1,035 pairwise solid-state reactions from the A-Lab, 46 precursors, 39 elements, 1,351 XRD scans, Dara automated Rietveld with expert review, CC BY 4.0 | **Read Oct 20.** Pairwise precursor reactions, one 1 h dwell per sample at a single temperature set by Tammann's rule (two-thirds of the lowest precursor melting point, 200-1100 C), 1,351 XRD scans on 1,035 samples, 1,950 Dara refinement cases with weight fractions, three-tier expert quality score, Pydantic-validated JSON ledger. Paper gives `github.com/lauren-walters/precursor-genome` and Zenodo 10.5281/zenodo.21285546, CC BY 4.0 (links not yet opened by us). No temperature series and no time axis: pairwise reactivity, not kinetics |
| Miura et al. (Observing and modeling the sequential pairwise reactions..., arXiv:2009.10896) | Pairwise-reaction model; in situ synchrotron XRD (30 C/min ramp to 940 C) of Y2O3 + BaCO3 + CuO versus Y2O3 + BaO2 + CuO, YBCO forms in 30 min from BaO2; SI Table S1 lists reported recipes (BaCO3 in 176 of 237) | Skimmed Oct 20. Phase evolution is shown as XRD patterns and phase-diagram maps, not tabulated fractions; same chemical system as the ARROWS3 YBCO table. Not a data source without digitizing |
| Hu et al. / Chapman (Resolving fast relative kinetics in inorganic solid-state synthesis, JACS 145, 26545, 2023) | Time-resolved in situ X-ray scattering of TiO2 (anatase) + Li2CO3 -> Li2TiO3 -> Li4Ti5O12 after sub-10 s heating, at 482, 700, 725 and 750 C. Rietveld phase fractions versus time (Figs. 2-3); Avrami slopes 1.4 and 0.5 for the Li2TiO3 step | Read Oct 20. Figures only: no data availability statement, SI is a heating profile. Digitize-from-figure, like Katsounaros |

**What the YBCO `Exp.json` contains (inspected Oct 20).** 47 precursor sets; 200 (set, temperature) entries at 600, 700, 800, 900 and 1000 C (the 1000 C ones cover only 12 sets). Each entry has `products` (phase names with an ICSD-style suffix, e.g. `Ba2YCu3O7_47`), `product weight fractions`, and a flag `Experimentally Verified`. 149 entries are verified and carry a raw XRD pattern; the other 51 are not verified and (for 50 of them) carry a `Source` field naming the experiment they were inferred from. Do not treat the unverified entries as data. The paper's 188 for YBCO is 47 sets x 4 temperatures (600-900 C), the full grid, and the Methods say all of it was run; the file has 200 entries (the extra 12 are the 1000 C runs) of which 149 are verified, and why 51 are not verified is still unexplained. For NTMO (46) and LTOPO (120) the numbers are grid sizes, and the paper says ARROWS3 sampled only part of the grid, so expect many fewer verified entries in those files. The target phase appears in 75 of the 149 verified entries. Mean number of phases per entry is 3.3. The weight fractions sum to 98.5-102 in every verified entry.

**Cautions that shape the noise model.**
- Weight fractions were estimated from relative peak intensities with XRD-AutoAnalyzer, not Rietveld refinement; the authors say Rietveld would be needed for precise values. Treat them as semi-quantitative.
- Because the fractions are normalized to about 100, amorphous or unidentified material is invisible. There is no analogue of the nitrogen-closure check, so the "unobserved" part of the problem has to be framed differently (see below).
- Leeman et al. (PRX Energy, March 2024) argue that automated Rietveld analysis of powder XRD is not yet reliable and that disorder is often neglected, using the A-Lab study as the example. Expect phase assignments to carry label noise.
- No repository licence was visible on the GitHub page (Zenodo lists "Other (Open)"). Do not commit the 52 MB file; commit only small derived tables, after checking the licence.

**Time-resolved candidate (read Oct 20): Chapman 2023.** The ARROWS3 tables have no time axis, which limits what a kinetic engine can say. The Chapman TiO2 + Li2CO3 data have one: anatase TiO2, rutile TiO2, Li2CO3, Li2TiO3 intermediate and Li4Ti5O12 product versus time (seconds to minutes) at four temperatures. It exercises the same features as the NO3RR benchmarks: a sequential network with an intermediate, a rate that depends on catalyst-like state (Li4Ti5O12 forms faster while anatase is still present and slows once only rutile remains), an Avrami regime change (slopes 1.4 to 0.5), and an apparent mass-balance gap (Li2TiO3 peaks at 52 wt%, above the 48 wt% stoichiometric maximum, which the authors attribute to a Li-deficient non-stoichiometric phase). Cautions: it is a sum-to-100 wt% basis with CO2 leaving as gas, so no conserved total exists as N does in NO3RR; convert to a conserved basis (moles of Ti) before checking closure, and say so. Two chemistries and one lab only. Use as a sanity benchmark and a second headline-figure candidate, not as the only data.

**Observation model (draft).** A dataset is a table of (precursor set with stoichiometry, temperature, hold time, phase weight fractions). The data have no time axis: each target has 4 to 5 temperatures per precursor set at a fixed hold. The unit of inference is therefore the pathway topology (which pairwise reactions occur, which intermediates form, which are consumed at higher temperature), not rate constants. With one hold time, an onset temperature and the steepness of a reaction's temperature response are only partly separable; report that as an identifiability finding, not a fit failure.

**Engine changes needed (none exist yet).**
1. Species type `phase` with a composition. Balance elements, not nitrogen; the mM-N convention in `mechanism.schema.json` does not apply here.
2. A pairwise reaction with a temperature response: extent after the fixed hold as a function of T (an onset temperature and a width), or an Arrhenius plus Avrami form if a time-resolved dataset turns up. Avrami/JMAK is listed in the registry as not implemented.
3. Plausibility rules: element balance; non-negative driving force from Materials Project thermochemistry (as ARROWS3 uses); at most two reactants per step (pairwise-first, per Miura); a cap on the fraction of material that cannot be assigned to an observed phase.
4. A converter from `Exp.json` (verified entries only) to the dataset schema, with a flag for phase-label noise.

**What is not new.** Pairwise-reaction reasoning and learning from failed syntheses are ARROWS3's contribution. What we can add is uncertainty and identifiability reporting, an explicit statement of what is not observable, an LLM proposer that cites literature, and next-experiment planning with an information-gain criterion. State this plainly in the pitch. A literature search found no paper combining a kinetic reaction network, in situ XRD phase tracking and Bayesian inference for thermal solid-state synthesis, which may be a gap or may be a narrow search; check before claiming it.

## 8. Real-data inventory and validation protocol

| Dataset | Status | Use |
|---|---|---|
| Liao 2025 Supp. Figs. 49, 50a, 50b | extracted to `data/real/` (Source Data) | calibration of W2; held-out evaluation of any method |
| Katsounaros 2012 Fig. 1 (0.5 M NaNO3 + 1 M NaOH, Sn; NO3, NO2, N2, N2O, NH3 at 0-180 min; model-B fit curves overlaid) | **digitized** (Daniel, WebPlotDigitizer) -> `data/real/katsounaros2012_fig1_sn_naoh.json`; see section 7b | W3 validation, W4 trap (model A vs B) |
| Ebenezer et al. 2026 (NiCo2S4, Chem. Eng. J. 545:179676) | **read** (main + SI). Initial-rate and 1 h electrolysis data only: no concentration-time curves, so it is not a fit benchmark. See section 8b | qualitative W5 targets (selectivity vs potential), feed-the-intermediate experiment design |
| Katsounaros 2008 Fig. 2 (1 M nitrate, 15-min sampling to 210 min, 5 species + authors' mass-balance loss) | **digitized** -> `data/real/katsounaros2008_fig2_sn_nacl_1M.json`; section 7c | hidden-intermediate and saturating-kinetics benchmark, model A vs B |
| Polatides 2005 Fig. 3 (50 mM nitrate, 0-120 min) | **digitized** -> `data/real/polatides2005_fig3_sn85cu15_50mM.json`; section 7c | second-order N2 branch; printed k2 looks 10x off |
| Polatides 2005 Fig. 6 (ln k2, ln k3 vs potential) | **digitized** -> `data/digitized_inputs/polatides2005_fig6/` (not a time course, so no `data/real` file); section 7d | W5 alphas. Fig. 5 (average rates vs potential) not digitized; only a qualitative cross-check |
| Liu et al. Source Data (nitrate/nitrite steps) | located, not yet converted | extra series, nitrite feed |

Protocol: a digitized curve is accepted only after the published rate constants, simulated with our simulator, reproduce the published curve within digitization error. Record `verified_against_figure: true` only then. Use real data for validation, not for tuning a method.

## 8b. Ebenezer 2026 read, and other literature added Oct 19

**Ebenezer (NiCo2S4, 0.1 M KOH + 0.5 M KNO3, H-cell).** Only 1 h potentiostatic runs at 50 mV steps (-0.05 to -0.50 V vs RHE) and initial-rate series versus concentration, with separate nitrate, nitrite and hydroxylamine feeds. No time courses in the paper or the SI (the SI has calibrations, spectra and tables), so nothing to digitize into our dataset schema. What it does give:

- Selectivity versus potential at fixed time: FE of NH3 about 57-67% across potential, NO2- 18.4% at -0.05 V falling to 7.7% at -0.50 V, NH2OH 5.9% falling to 1.1%, HER 18.7% rising to 37.4%. Usable as a qualitative target for W5 (branching ratio shifts with E), not as a calibration.
- Intermediate-feed experiments (nitrite alone, hydroxylamine alone) as a way to isolate step k's. This is an experiment type the planner should be able to propose.
- NH2OH as a measured intermediate, which no world includes yet.
- Warning on the numbers: the reaction orders are inconsistent inside the paper (Table 2: 0.47 / 0.36 / 0.97 for NO3 / NO2 / NH2OH; text on Fig. 3e: 0.79 / 0.52 / 1.43; Fig. 5 apparent orders: 0.41 / 0.59 / 1.29), the "rate constants" carry units of M s-1, which is a rate, and Eq. 15 for d[NH3]/dt has minus signs on the intermediate terms. Do not take W5 alphas or rate constants from this paper without resolving which set is meant. The paper also treats the sequence as strictly NO3 -> NO2 -> NH2OH -> NH3 with no direct branch, which is the structure our Liao fits say is insufficient.

**Sanofi SKAI (Li et al., Ind. Eng. Chem. Res. 2025, 64, 6825; doi 10.1021/acs.iecr.4c04301; main paper now in the folder).** Closest method relative to ours. Takeaways: (1) models are ranked by elpd_loo / WAIC from MCMC (NumPyro), a more honest comparison than point-estimate AIC for our 7-18 point datasets; (2) the random-forest classifier over 456 two-step mechanisms is only 52% exact, but errors cluster on near-neighbours, and Bayesian inference then picks among the top 3, so a classifier is a proposer, not a judge; (3) they note two top candidates have nearly identical ODEs when k2 is small, and say this could drive the next experiment, then leave it out of scope, which is our planner; (4) few-shot LLM text-to-JSON reaches 90% key accuracy on 10 curated pairs, a direct precedent for Jarrod's serializer and a ready-made eval for it; (5) limits that leave our niche open: two-step mechanisms only, simulated training data, no potential or pH dependence, no hidden intermediates, no mass-balance gap; (6) their Savitzky-Golay + spline smoothing is not appropriate for us: our curves have 7-18 points and the jumps are signal.

**Liu et al., Nature 626, 98 (2024), Li-S 16-electron network.** Not NO3RR, but three transferable points. (1) The network is electrochemical steps plus a non-electrochemical comproportionation (Li2S8 + Li2S4 -> 2 Li2S6) that creates a species no electrochemical step makes. The schema already allows this (`electrons: 0`), but `potential_dependence` must not be applied to such steps; add that check to `validate_mechanism`. NO3RR analogues are N-N coupling toward N2/N2O and the second-order 2 NO2 -> N2 of Polatides. (2) Charge bookkeeping splits the network into stages (4.08 : 11.92 electrons, about 1 : 3, identifies Li2S4 as the hinge). For us, charge passed depends on where the sink sits (NO3 -> N2 is 5 e per N, NO2 -> N2 is 3 e), but HER takes charge too, so it only helps if FE or total charge is recorded. Worth adding as an optional observable, not a promise. (3) A solubility limit (Li2S4, about 10 mM) shifts the apparent profile; the NO3RR counterpart is gaseous N2/N2O leaving solution, a plausible physical identity for part of the closure gap. Also, the same network with different catalysts (N,S-HGF versus HGF) changes only rates, which supports fitting Liao Figs. 49, 50a and 50b with a shared topology and per-catalyst parameters.

**Barter et al., Digital Discovery 2023 (HiPRGen).** Enumerate-then-filter: bucket species by composition, generate every stoichiometrically valid reaction, then drop by rules (more than two bonds changing, dissociative redox). Our species set is about 8, so full enumeration is cheap. The enumerator baseline should generate all N-balanced reactions among {NO3, NO2, NO, N2O, N2, NH2OH, NH3, X}, filter by electron count versus oxidation states (already in `validate_mechanism`) and a maximum step size, then search subsets simplest-first. Their kinetic Monte Carlo with arbitrary rate constants only finds which products are reachable, not rates, and they say so, so it is not a kinetics method. They keep only exergonic steps to avoid loops, matching our irreversible-by-default convention.

**Bagger and Wuttke, PCCP 2025.** Isomer generator (Surge) enumerating surface intermediates for CO/NO reduction, showing the count grows exponentially with reactants and steps. Atomistic and DFT-facing, which v0.1 excludes. One use: a sentence for the pitch on why hypothesis spaces explode and why a human-curated list misses things.

**Horno et al., J. Electroanal. Chem. 352, 83 (1993).** Network (circuit) simulation of diffusion-reaction systems, chronoamperometry and ECE. Spatial transport, out of scope. Skip.

## 9. Inference pipeline (stages and interfaces)

1. Propose: enumerate (all N-balanced reactions over the species list, filtered by oxidation-state rules, simplest subsets first; section 8b, Barter) or LLM-propose candidate mechanisms from the library plus revisions (output: `mechanism.schema.json` objects).
2. Fit: parameters by maximum likelihood or MCMC under the noise model; report `neg_log_lik`, AIC, BIC, posterior summaries, and elpd_loo/WAIC when MCMC is used (section 8b, SKAI).
3. Critique: rule-based plausibility (`max_hidden_fraction_of_total_N`, rate-constant bounds, `max_effective_alpha`) and optional LLM critic with rationale. A candidate may win BIC and fail plausibility.
4. Revise: if no candidate passes, change the model class (add a branch, a sink, a time term) rather than only re-fitting.
5. Identify: profile likelihood or posterior-width ratio; list `unidentifiable_params`.
6. Plan: pick the experiment (potential, pH, c0, sampling times) with the highest expected information gain among surviving candidates.
7. Evaluate: score against the task's metrics.

Contract: the proposer/critic (LLM side) consumes a dataset or task observation and emits candidates; the fitter/evaluator emits a result file. Both sides meet at `result.schema.json`.

## 10. Division of labor

| Owner | Work |
|---|---|
| Daniel | domain content: rate-law registry, plausibility constraints, digitizing and verifying Katsounaros/Polatides curves, world calibration, interpreting the real-data fits |
| Jarrod (proposed, to confirm with him) | LLM proposer and critic, prompt/agent loop, candidate-to-`mechanism.schema.json` serialization, result logging |
| Shared | fitter + information-gain planner, scoring harness, demo (marimo app, section 11b) |

The interface is the four schemas. Neither side should need to change the other's code to run a baseline: a trivial enumerator in place of the LLM must work end to end.

## 11. Timeline to Oct 21-22

Decision (Daniel, Oct 20): no fitter work before the event. Starting the fitter is the project's start, so it begins at kickoff on Oct 21. The domain is now synthesis pathways (section 1b); the NO3RR worlds stay as the test bed.

- Before the event: data and reading only. Inspect the NTMO and LTOPO `Exp.json` files, resolve the 188-versus-149 count, read ARROWS3 and Miura (the reading list is in NEXT_STEPS), keep the NO3RR datasets and worlds as they are.
- Day 1 (Oct 21): look at the curated datasets at kickoff (decision rule in section 11b); extend the schema to phases and elements (7e); converter for the YBCO table; fitter (MLE + AIC/BIC) and enumeration baseline, first on W1-W3 and W5 as regression tests of the engine, then on YBCO; Jarrod's proposer/critic once the fitter returns results; start the marimo app.
- Day 2 (Oct 22): identifiability output, next-experiment planning, headline figure, video and one-pager by midday, buffer before the submission deadline (stated as 5 pm PT; confirm on the event page). The synthesis-to-catalyst coupling is shown as a labelled illustration only. Cut it first if time runs short.

## 11b. Sponsors, demo and headline figure

Source: a planning conversation on claude.ai (Oct 20) that looked up the sponsors from their websites. The event pages list no sponsors, datasets or prize terms, so everything below about sponsor products is unverified until kickoff. Recommendation there: keep the project, narrow it, and let the sponsors shape the demo; no pivot looked better.

| Sponsor | What it is (from its site) | Use for us | Cost | Verdict |
|---|---|---|---|---|
| Marimo | open-source reactive Python notebook; can run as an app or export to WebAssembly HTML | the demo: sliders for potential and pH, live fit and mechanism ranking, public WASM link, and the video's visual | low | do it |
| Valency | Bond: literature search and citation graph for an LLM through one MCP endpoint (500M+ papers); early-access hub for publishing AI-assisted work | proposer retrieves published NO3RR pathways and attaches a citation to each candidate; critic checks plausibility against them | some of Jarrod's time | do it only after the stub proposer works end to end; the interface contract in section 9 is unchanged |
| Adaption | custom model training, dataset optimization | none obvious | | skip unless a curated kickoff dataset makes it natural |

Design constraints that follow (ours, not from the chat): the live-fit path in the marimo app must run in a browser (Pyodide), so the baseline fitter should depend on numpy and scipy only, and MCMC (NumPyro/JAX) stays an offline option, not the demo path. Check scipy availability in the marimo WASM export early on Oct 21.

Judging fit, as assessed there: impact and relevance decent; novelty defensible only in our niche (real potential-dependent electrochemical data, hidden intermediates, identifiability reporting), since generic LLM-guided model discovery and AIC enumeration are already published; innovativeness moderate. The real risks are execution: fitter and baseline not built, LLM side depends on Jarrod, only six small datasets (the Liao three from Source Data, the others digitized), and the 4-minute video needs one clear headline figure.

Headline figure (written before the Oct 20 direction change; revisit after the data check): the Katsounaros case (W4). If the synthesis pivot goes ahead, the headline should come from the YBCO table instead, for example a precursor set where several pathway topologies fit the 4-5 temperatures equally well, with the identifiability flags and the proposed discriminating experiment. W4 then becomes a supporting sanity check. Show the enumeration baseline selecting model B on real digitized data by BIC while needing an implausibly large hidden pool, and show the literature-grounded proposer, critic and identifiability flags flagging or correcting it. Two cautions. (1) Katsounaros 2012 itself reports model B favored (Bayes factor 2921), so "wrong" here means implausible by our `max_hidden_fraction_of_total_N` rule (X peaks near 24% of N in W3), not contradicted by the paper; state it that way. (2) W1, W3 and W5 parameters come from our own calibration or illustrative choices, so report the synthetic worlds as sanity checks, never as evidence.

Kickoff decision rule: if a curated dataset has multi-species time-course kinetics, add it as a seventh case. If the datasets are all materials-property tables with nothing kinetic, relevance to the judging criteria drops and the plan gets reassessed on the spot (the Catechol Benchmark, with its three-species flow time series, is a fallback out-of-domain case; section 12).

## 12. Open questions

- ~~Is Fig. 49 really at -0.6 V vs RHE?~~ Resolved Oct 19: yes, its values are identical to Fig. 48, which states -0.6 V. The `potential_unverified` flag is removed.
- Sink on NO3 or NO2 in Liao Fig. 50: needs profile likelihood, not just a cost comparison.
- Deactivation vs pH drift: can a pH-dependence term plus a pH-evolution state explain the stall instead of an empirical tau?
- Which observed-species sets should the benchmark vary (NH3 only, NO3+NH3, all three)?
- Licence terms for redistributing digitized curves; keep source workbooks out of the repo.
- Why does the YBCO `Exp.json` hold 149 verified entries when the paper says all 188 grid experiments were run (and 200 entries exist including 1000 C)? NTMO and LTOPO were only partly sampled, so how many verified entries do those files hold?
- Licence of the ARROWS3 data (none visible). Precursor Genome is CC BY 4.0 on GitHub and Zenodo per its paper; open the links and confirm the ledger loads.
- Can the Chapman Figs. 2-3 phase fractions be digitized well enough (five phases, four temperatures) to fit Avrami versus first-order steps, and is wt% convertible to moles of Ti?
- Is there any catalyst with both public synthesis-phase data and public NO3RR kinetics? If not, the synthesis-to-NO3RR coupling stays a labelled illustration.
- Sponsor facts (section 11b) and the submission deadline are unverified; confirm at kickoff.
- Can the fitter run in the marimo WASM export at interactive speed (scipy in Pyodide, ODE solve per slider move)? Test early on Oct 21.
