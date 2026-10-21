# Progress log

What has been done, found and decided, newest first. This is a record, not a to-do list: what to work on next is in `docs/NEXT_STEPS.md`, the design and data facts are in `docs/SPEC.md`, and the investigator's own notes are in `docs/INVESTIGATOR.md` (Jarrod).

Rules: findings and results go here. When a task in NEXT_STEPS is finished, delete it there and add one dated line below with the result. Dates are 2026.

## Change log

**Oct 21**
- Hackathon kickoff. Aryan is not joining; the team is Daniel and Jarrod. Agreed split: Jarrod the model side (evaluator, agent, schema extension), Daniel literature and data.
- All three ARROWS3 tables (YBCO, NTMO, LTOPO) inspected; LTOPO found to be a polymorph branch point at 700 C (findings below). Precursor Genome ledger opened and loads. A-Lab SI inspected.
- Synthesis literature folder `04_synthesis` assembled (reference-list papers, ARROWS data and black-box scripts, `MP_Energetics.json`) and zipped for Jarrod.
- ARROWS greedy random-forest baseline ran on the YBCO table: barely better than random order. ARROWS3 itself needs a Materials Project API key (a run was started in a scratch directory with one; not finished at the time of this entry).
- OpenAlex forward-citation pass (`scripts/openalex_citation_pass.py`): found a 2026 Bayesian model-selection paper on time-resolved XRD of a solid-gas reaction, so the novelty claim was limited to precursor synthesis (SPEC section 7e).
- Liao Fig. 50a/50b catalyst assignment resolved: SI caption and our labels are right, the main-text sentence swaps the two residual-nitrate values.

**Oct 20**
- Direction change from NO3RR mechanism inference to solid-state synthesis pathways, to avoid overlap with work outside the hackathon (SPEC section 1b). The NO3RR worlds and datasets stay as the test bed and as a labelled downstream illustration.
- Jarrod's investigator pipeline merged: shared evaluator (maximum likelihood, profiled noise, AICc, identifiability, adequacy), enumeration baseline, investigation store, Pi-hosted investigator and fresh-context reviewer (`docs/INVESTIGATOR.md`). Built on Liao Fig. 50 (NO3RR); not yet adapted to synthesis.
- Chapman 2023 Figs. 2-3 phase fractions extracted by colour classification (`data/digitized_inputs/chapman2023_fig2/`); spot-check pending.
- W5 recalibrated to Polatides 2005 (constants at -2.0 V vs Ag/AgCl, Fig. 6 alphas 0.131 and 0.089, k1 alpha 0); Fig. 6 digitization checked against the printed constants (SPEC section 7d).
- Sponsor read from a planning chat (unverified): Marimo for the demo, Valency Bond for citations, Adaption skipped (SPEC section 11b). Fitter work deferred to kickoff, then found already built by Jarrod.
- Visual abstract built (NO3RR framing; no longer in `docs/`, needs a synthesis rewrite).

**Oct 19**
- Katsounaros 2012 Fig. 1, Katsounaros 2008 Fig. 2 and Polatides 2005 Fig. 3 digitized and converted; Ebenezer 2026 read (no time courses). Repo shared with Jarrod.

## Findings (moved from the old NEXT_STEPS, Oct 21)

Sections 1 to 4 below are the findings and reading notes as they stood on Oct 21. Task lists inside them that read "still to do" have been carried into NEXT_STEPS or are done; treat this as a record.

### 1. Data availability for the synthesis data (partly done)

**What the ARROWS3 paper says.** Szymanski, Nevatia, Bartel, Zeng, Ceder, Nat. Commun. 2023 (PMC10618174), data availability statement, verbatim: "The phase information associated with the experimental outcomes in the YBCO, NTMO, and LTOPO synthesis datasets ... can be found in the ARROWS3 repository." It adds: "Source data for all graphs are also provided as a Source Data file with this publication." Code availability: the public repository github.com/njszym/ARROWS, "archived at 10.5281/zenodo.8331001". The Zenodo record is a 101 kB archive of the code, with no paper link and no dataset description; the data are in the repository.

**What I found in the repository (Oct 20).**
- `Examples/YBCO/Exp.json`, `Examples/NTMO/Exp.json`, `Examples/LTOPO/Exp.json` are Git LFS pointers. A plain `git clone` gives 133-byte stubs. The real file is at `https://media.githubusercontent.com/media/njszym/ARROWS/main/Examples/YBCO/Exp.json` (52 MB). Same pattern for NTMO and LTOPO, which I did not download.
- YBCO: 47 precursor sets, 200 (set, temperature) entries at 600-1000 C, 149 flagged `Experimentally Verified` with raw XRD patterns, the rest inferred. Phases per entry with weight fractions that sum to about 100. Details and cautions in SPEC section 7e.
- No licence visible on the repository page; Zenodo says "Other (Open)". Do not commit the files.

**Checked Oct 21 with the files now in `literature/04_synthesis/` (19 files, complete).**
- **ARROWS3 SI Tables 1-3 versus the YBCO `Exp.json`: no clean match, but no evidence of missing sets.** The SI says 47 YBCO precursor sets were tested and only 10 gave YBCO with no detectable impurity. A text parse of Table 1 recovered 37 of the 47 sets and 33 of them match `Exp.json` keys exactly; the unmatched ones are mostly formula spellings (Ba2Cu3O6 in the SI against Ba2(CuO2)3 in the file). Needs a person or a name-normalising script to finish.
- **The YBCO file is not fully verified.** Verified entries per precursor set: 6 sets have none, 1 set has 1, 1 has 2, 17 have 3, 15 have 4, 7 have 5. The 51 unverified entries are 22 at 600 C, 11 at 700 C, 8 at 800 C, 9 at 900 C and 1 at 1000 C. Any converter must drop them and tolerate sets with missing temperatures.
- **A-Lab SI (`41586_2023_6734_MOESM3_ESM.zip`, 48 MB unzipped).** `20230502 Synthesis Results with Recipes.csv` has 57 targets with columns Target, Result, Materials Project ID, Symmetry, Spacegroup, Precursors + Masses, Temperature (C), Duration (hours). Results: 33 Success, 15 Failed, 7 Partial, 2 Success (offline). Each target has one recipe at one temperature (500-1100 C) and 4 h (one "4 -> regrind -> 4"); the 15 failed rows have no recipe filled in. No phase fractions in the CSV. `Refinement-Table.xlsx` (1,092 rows) holds free-text conclusions and lattice parameters from automated and manual refinements. Not a trajectory or temperature-series dataset; useful as a prior and for label-noise analysis, not as a fit case.
- **Precursor Genome ledger: opened and loads (Oct 21).** `ledger_precursor_genome.json` (31 MB, plain JSON on GitHub, `github.com/lauren-walters/precursor-genome`, CC BY 4.0). 1,035 samples, 995 distinct precursor pairs, so no pair has more than one sample and there is no temperature series. Heating time 60 min (750 samples) or 240 min (231), 14 missing; heating temperature 200-1100 C (9 distinct values, 14 missing); 40 samples have no synthesis metadata and 26 have no reaction category. Categories: transformed 384, unreacted 369, completely reacted 143, partially reacted 113. Phase weights are fractions that sum to 1.0 (0.999-1.0), mean 2.7 phases per sample, 994 samples with phases. No time axis, as expected. The Zenodo record (doi 10.5281/zenodo.21285546, CC BY 4.0) holds only raw scans and plots (five zips, 7.6 GB); the ledger alone is enough for us. Its README says the Zenodo deposit is restricted and about 17 GB while the record I queried is open at 7.6 GB, so the two disagree; irrelevant unless someone wants the raw XRD.

**All three ARROWS3 tables are now local and inspected (Oct 21).** Files in `literature/04_synthesis/`: `ExpYBCO.json`, `ExpNTMO.json`, `ExpLTOPO.json` (renamed from `Exp.json`; the YBCO file is byte-identical to the one I downloaded) and `Settings*.json`. Anything reading them, including the ARROWS scripts, needs the names changed back or a path argument.

| Target | Precursor sets | Entries (verified) | Temperatures | Entries containing the target |
|---|---|---|---|---|
| YBCO | 47 | 200 (149) | 600-900 C, plus 12 at 1000 C | 75 of 149 |
| NTMO | 13 | 18 (18) | 300 C (5), 400 C (13) | 9 of 18 |
| LTOPO | 15 | 58 (58) | 400, 500, 600, 700 C (14-15 each) | 14 of 58, all at 700 C |

- **LTOPO is the cleanest branch point in the data.** The target appears only at 700 C. Of the 14 sets run there, 10 give both polymorphs (`LiTiPO5_2` triclinic and `LiTiPO5_62` orthorhombic), 2 give only the orthorhombic, 2 only the triclinic. At 400-600 C no entry contains either, only intermediates. Caveat: 14 experiments at one temperature. Zeng et al. (Sci. Adv. 2024, now local) is the paper behind the polymorph question.
- **NTMO is small** (18 entries, 13 sets, two temperatures); use it as a second, not a lead, case.
- **YBCO is the largest** but 51 of 200 entries are unverified and must be dropped (SPEC section 7e).
- Phase names carry a `.cif` suffix in NTMO and LTOPO (and an ICSD-style number suffix everywhere); the converter needs to normalise them. Weight fractions sum to 98-102, so no amorphous-material signal in any of the three.

**Still to do.**
1. Finish the SI-table match for Tables 1-3 against these keys, with name normalisation (SPEC section 7e has the YBCO partial result). The SI says YBCO sets were all tested; NTMO and LTOPO sets listed there number 23 and 30, the files hold 13 and 15, so the rest were never run (consistent with the paper's "only part of the design space was sampled").
2. Licence of the ARROWS3 data is still unknown (none on the repo page; Zenodo "Other (Open)"). Sending the files to Jarrod privately is fine; do not commit them.

### 2. Reading and literature scouting

Scouted Oct 20 from search results and abstract pages only; none read in full. All 19 files are now in `literature/04_synthesis/` on the lab PC (Oct 21). Priority order, with what to look for.

| # | Paper | Why it matters | What to check |
|---|---|---|---|
| 1 | Szymanski et al., Autonomous and dynamic precursor selection for solid-state materials synthesis (ARROWS3), Nat. Commun. 2023, doi 10.1038/s41467-023-42329-9; arXiv 2304.09353 | The data source and the closest prior method. It already learns which pairwise reactions consume the driving force and updates precursor rankings | How much of our proposed contribution it already covers (uncertainty, unobserved material, experiment planning); Table 1 and Methods for the 188 count |
| 2 | Miura et al., Observing and modeling the sequential pairwise reactions that drive solid-state ceramic synthesis, arXiv 2009.10896 | The pairwise-reaction model our plausibility rules would use; SI has a table of reported Y-Ba-Cu-O syntheses | The rule for which interface reacts first; how they handle intermediates; whether the SI table is usable as a second dataset |
| 3 | Walters, McDermott, Rendy, Fei, Persson, Ceder, The Precursor Genome: a pairwise reaction dataset for solid-state synthesis, arXiv 2607.09903 (July 2026) | 1,035 pairwise reactions from the A-Lab, CC BY 4.0; possibly the best dataset for us and possibly a competitor, since it is built for training predictive models | Where the data live; whether records have temperatures and hold times; schema; the three-tier quality labels |
| 4 | Leeman et al., Challenges in high-throughput inorganic materials prediction and autonomous synthesis, PRX Energy, March 2024 | Argues that automated Rietveld analysis is unreliable and that the A-Lab's claimed new materials do not hold up | Sets the noise model and our limitations paragraph; how to flag untrustworthy phase labels |
| 5 | Szymanski et al., An autonomous laboratory for the accelerated synthesis of novel materials (A-Lab), Nature 2023, doi 10.1038/s41586-023-06734-w | Source of the A-Lab data in the awesome-matchem-datasets list (about 57 targets) | Published abstract: 36 of 57 targets (checked Oct 20); Leeman quotes 41 new materials from an earlier version. Cite the published figure |
| 6 | Dara: automated multiple-hypothesis phase identification and refinement from powder XRD, arXiv 2510.19667 | The tool behind the Precursor Genome labels; relevant if we ever quantify phase-assignment uncertainty | Whether it outputs alternative hypotheses with scores that we could use as label noise |
| 7 | Chapman group, time-resolved in situ X-ray scattering of TiO2 + Li2CO3 to Li4Ti5O12, JACS 2023 | A real time-resolved thermal synthesis; shows when kinetics are identifiable | Whether the data are public; whether intermediates were resolved |
| 8 | Macchietti et al., in situ XRD with MCR-ALS and a kinetic model, Chem. Sci. 17, 12047 (2026) | A method precedent for combining phase deconvolution and kinetic modelling (mechanochemical, not thermal) | What they constrain and how they report rate-parameter uncertainty |
| 9 | Rosser, Farris, Leonard, machine learning from experimental datasets for electrocatalytic nitrogen reduction, Digital Discovery | The nearest precedent for linking experimental conditions to electrocatalytic performance (up to 520 conditions; N2 reduction, not nitrate) | Whether the approach could be borrowed for a synthesis-to-activity link |
| 10 | Gao et al., Breaking adsorption-energy scaling limitations of electrocatalytic nitrate reduction on intermetallic CuPd nanocubes, Nat. Commun. 2022 | An example of machine-learning insight plus controlled synthesis for NO3RR; the closest thing I found to a synthesis-to-activity story | Whether any of its synthesis parameters are given as data |
| 11 | MRS Spring 2026 abstract on precursor choice, onset temperature and the Tammann rule; Retro-Forge, pairwise retrosynthesis (ICML 2026) | Both appear to be close to our space and possible competitors | Skim for anything we would be claiming that they already do |

**Gaps from the search (revised Oct 21 after the OpenAlex pass, section 2e).** I still found no dataset that records synthesis precursor, temperature and phase composition together with NO3RR performance. The claim "no paper combines a kinetic network, in situ XRD and Bayesian inference" is too strong: one 2026 paper does it for a solid-gas oxidation (section 2e). What I can still say is that none turned up for thermal solid-state synthesis from precursors in the sources searched on Oct 21, which is a statement about those searches, not about the literature.

### 2b. New literature read Oct 20 (13 files; abstracts and the relevant sections, not every page)

- **Chapman JACS 2023 (row 7) is the most useful.** Phase fractions versus time at 482, 700, 725 and 750 C for TiO2 + Li2CO3 -> Li2TiO3 -> Li4Ti5O12, in figures only. It is the synthesis analogue of Katsounaros: sequential network, intermediate, catalyst-like state (anatase), Avrami regime change, a mass-balance oddity (Li2TiO3 at 52 wt% above the 48 wt% stoichiometric maximum). Digitizing Figs. 2-3 gives a time-resolved case for the synthesis engine. Caveat: wt% with CO2 leaving as gas, so convert to moles of Ti before any closure check.
- **Miura (row 2)**: in situ XRD of the YBCO system (BaCO3 versus BaO2 route), figures only, qualitative; useful for the pairwise-reaction rule and as context for the ARROWS3 YBCO table, not a second dataset.
- **Precursor Genome (row 3)**: located and read, but pairwise reactivity at one temperature, no kinetics. Best use is a prior for the proposer and critic (is a pair reactive, which product) and a held-out test of the pairwise rule.
- **Dara (row 6)**: returns several hypotheses when a pattern is ambiguous; a source of label noise for Precursor Genome. Code: github.com/idocx/dara. ARROWS3's own phase labels came from XRD-AutoAnalyzer, not Dara.
- **Leeman (row 4)**: argues automated Rietveld is not yet reliable and that none of the A-Lab's claimed new materials are new. Cite for the label-noise limitation.
- **Retro-Forge (row 11, in part)**: single-step pairwise reactant prediction composed by tree search, no temperatures (future work). Possible proposer; its task (target to precursors) differs from ours (outcomes to pathway). The MRS abstract is not in the folder.
- **Macchietti (row 8)**: mechanochemical, MCR-ALS with kinetic constraints; low relevance, no uncertainty reporting seen.
- **Rosser (row 9)**: shallow ML on 520 N2-reduction conditions; not nitrate, not kinetic. **Gao (row 10)**: ordered B2 CuPd versus random alloy is the closest public "catalyst state" for NO3RR, with endpoint FE (92.5%) only. Neither changes the conclusion that the synthesis-to-NO3RR link is a labelled illustration.

### 2c. Papers added Oct 21 from the reference lists (now local; skimmed, not read)

| Item | What it gives us | Notes |
|---|---|---|
| McDermott 2021 + code (`github.com/GENESIS-EFRC/reaction-network`, PyPI `rxn-network`) | Candidate-reaction enumeration and cost-based pathfinding over Materials Project thermochemistry; reproduces YBCO, YMnO3, Y2Mn2O7, Fe2SiS4 pathways | Needs Materials Project data (version 2020.09.08 in the paper) and, in recent releases, an API key; the PyPI demo notebook is reported broken in 2.0.3. Setup time is the risk. Best use: a reference list of thermodynamically allowed pairwise reactions for the YBCO and LTOPO precursor sets, to seed or check the proposer |
| Bartel 2018 + code (`github.com/CJBartel/predict-gibbs-energies`) | Gibbs energy as a function of temperature for driving-force terms | The CSV in the folder is the training table, not the predictions. I did not verify the pymatgen implementation |
| ARROWS `Black-Box/` scripts | `d-optimal.py` is self-contained (scikit-learn, cvxpy with CVXOPT); `bayesian-opt.py` and `genetic-algo.py` read `Exp.json` and a precursor list from `Rxn_TD.csv` | `bayesian-opt.py` ran Oct 21 (section 2d). The ARROWS3 algorithm itself did not run (needs a Materials Project API key) |
| Bianchini 2020 (Nat. Mater.) | Multistage in situ crystallisation of Na0.67MO2 with a thermodynamics-versus-kinetics framework | Data on request, figures only. A possible second time-resolved case after Chapman, at digitizing cost |
| Kamm 2022 (JACS) | Fast and slow kinetic regimes in NaFeO2 + LiBr from in situ XRD | Not checked for data; same lab and style as Chapman |
| Zeng 2024 (Sci. Adv.) | Why one LiTiOPO4 polymorph forms before the other (surface energy and nucleation) | Read it before presenting LTOPO |

Not yet in the folder, still worth fetching if there is time: Franceschini and Macchietto 2008 (model-based design of experiments for parameter precision), Malkowski 2021 and Todd 2021 (pairwise-reaction case studies), Chang et al. arXiv 2308.07897 (probabilistic phase labeling), the opXRD in situ subset (arXiv 2503.05577), Kononova 2019 text-mined recipes (Sci. Data 6, 203).

### 2d. ARROWS3 baseline: what ran and what did not (Oct 21)

`MP_Energetics.json` (225.7 MB, the 0 K and Bartel temperature-corrected formation energies) is now in `literature/04_synthesis/`. I assembled a working ARROWS directory outside the repo (code from `github.com/njszym/ARROWS` with LFS files replaced by the real ones, a Python 3.9 virtualenv with pymatgen, scikit-learn, cvxpy and cvxopt).

- **ARROWS3 itself does not run offline.** `gather_rxns.py` and `suggest.py` call `energetics.get_pd_dict`, which fetches every entry in the chemical system from the Materials Project API (`MPRester.get_entries_in_chemsys`) and only then applies the temperature corrections from the local JSON. The upstream code hard-codes someone else's API key in `arrows/energetics/__init__.py` (line 263); I did not use it and you should not either. To run ARROWS3 you need your own free Materials Project API key (set it in that line or read it from an environment variable). The installed `mp-api` and `pymatgen` versions also conflict on Python 3.9 (import error in `emmet`), so use Python 3.10 or later, or pin older versions. Until then, no ARROWS3 numbers of ours exist; do not quote any.
- **The greedy random-forest baseline ran.** I rebuilt `Rxn_TD.csv` from the 47 precursor sets in `ExpYBCO.json` (the script only reads the first column) and ran the unmodified `bayesian-opt.py` (100 campaigns, one random starting set, then pure greedy selection by random-forest predicted yield, fixed temperature 900 C, oracle = the YBCO table). Result: 10 of the 47 sets give pure target at 900 C (matches the SI's "10 of 47"). The greedy forest found its first optimum at selection 4.1 on average and had all optima at selection 41.5 (of 46); random order over the same sets gives 4.4 and 43.6 by simulation. So it is barely better than random on this table. An `mp_api` stub was needed only to satisfy an import; the run took about 5 minutes.
- **What this is and is not.** It is a reduced baseline: precursor set only, temperature fixed at 900 C, 47 candidates. It is not the paper's benchmark (that one ranges over precursor set and temperature, 188 experiments, and compares against ARROWS3). The oracle also includes the 51 unverified, inferred YBCO entries, which is how the original script treats the table. Not run: `genetic-algo.py` (needs the `geneticalgorithm` package) and `d-optimal.py` (self-contained, quick; not done).
- **Use for us.** The YBCO table can serve as an experiment-planning testbed: choose a set (and temperature) to try next, and count experiments to the first and to all pure-target sets. Greedy-RF and random are the two floor baselines; ARROWS3 and our planner would need the API key and the work above.

### 2e. OpenAlex forward-citation pass (Oct 21)

`scripts/openalex_citation_pass.py` (standard library only, unauthenticated API, no email or key sent) lists the works that cite 11 seed papers and tags their titles and abstracts by topic. Seeds: ARROWS3, Miura 2021, Chapman 2023, McDermott 2021, Bianchini 2020, Kamm 2022, Zeng 2024, A-Lab, Gao 2022, Rosser 2024, Precursor Genome (0 citing works indexed yet). 1,873 unique citing works; 52 match synthesis + kinetics or in situ + (uncertainty or network); 2 match all of synthesis, kinetics, uncertainty and XRD. Caveats: OpenAlex lists 48 citing works for ARROWS3 and returned 47 (A-Lab 1,006 of 1,012, Gao 417 of 420); the topic tags are keyword matches on abstracts and miss works without abstracts; coverage on the day is not the literature. Nothing here was read beyond the abstract.

What it turned up, most relevant first (all new to us):
- **Bayesian model selection on time-resolved synchrotron XRD for a solid-state reaction exists.** *Reaction Modeling of the Rapid Two-Step Oxidation Process Assisted by Bayesian Inference with Isothermal Time-Resolved X-ray Diffraction Measurements*, J. Phys. Chem. C (2026), doi 10.1021/acs.jpcc.6c02717. SrCrO2.75 oxidises to SrCrO3 in about 7 s at 400 C through SrCrO2.8; "assumption-free model selection" shows the two steps differ in nucleation-and-growth behaviour. It is a solid-gas reaction of one compound, not precursor-to-target synthesis, and it covers one system. It is the closest prior art to our method on the inference side; read it before claiming novelty.
- **Diffusion-Limited Solid-State Synthesis Selectivity in the Presence of Oxidation/Reduction Processes**, Chem. Mater. (2026), doi 10.1021/acs.chemmater.6c01610. Extends a thermodynamics plus machine-learned ion-transport framework to Ba-Fe-O and Y-Fe-O, benchmarked against in situ XRD; cites ARROWS3, McDermott, Miura and Bianchini. A kinetic-selectivity competitor and a possible source of in situ benchmark data.
- **Considerations for quantitative in situ X-ray powder diffraction studies of solid-state reactions** (Kamm et al., J. Appl. Crystallogr. 2023, doi 10.1107/s160057672301021x). The observed reaction progress for NaFeO2 + LiCl differed by about 50% with capillary packing. A systematic measurement error of that size belongs in the noise model and in the limitations paragraph for the Chapman data.
- **Adaptively driven X-ray diffraction guided by machine learning** (npj Comput. Mater. 2023, doi 10.1038/s41524-023-00984-y): ML-steered measurement for phase identification; related to next-experiment planning, not to kinetics.
- **The RAPTR furnace** (J. Appl. Crystallogr. 2024, doi 10.1107/s1600576723011020), Chapman and Kamm's rapid-heating furnace for in situ scattering: more time-resolved data of the Chapman type may exist or be coming.
- Further in situ pathway studies citing Bianchini or Miura (leads only): Kinetic pathways templated by low-temperature intermediates (Chem. Mater. 2020, 10.1021/acs.chemmater.0c02568); in situ studies of BiOCuSe synthesis (JACS 2021, 10.1021/jacs.1c03947); real-time LiCoO2 crystallisation (Chem. Mater. 2022, 10.1021/acs.chemmater.2c02050); mechanistically guided nitride synthesis (JACS 2024, 10.1021/jacs.3c12114). Baibakova et al. (Digit. Discov. 2025, 10.1039/d5dd00160a) combines text-mined sol-gel recipes with a reaction network analysis for BiFeO3.
- **NO3RR side: nothing.** The citing works of Gao 2022 and Rosser 2024 that mention nitrate and synthesis, phase or data are reviews and catalyst-design papers; none provides a dataset linking synthesis phases to NO3RR performance. The gap stands, as a statement about this search only.

To do: read the SrCrO3 paper and the Chem. Mater. 2026 paper in full (about 1 h); run the same seeds and queries in Valency at kickoff if access exists and compare lists (SPEC section 11b).

### 3. Done so far, still true

- Digitized and checked against the papers: Katsounaros 2012 Fig. 1, Katsounaros 2008 Fig. 2, Polatides 2005 Fig. 3 and Fig. 6 (SPEC sections 7b-7d). W5 now uses the Polatides constants and alphas.
- Ebenezer 2026 read: no time courses, not a fit benchmark (SPEC section 8b).
- Repo is with Jarrod.

### 4. Parked

- Screening the Liu 2024, Wang 2025 and Wu 2025 Source Data for NO3RR time courses. Worth doing only if the NO3RR side gets more weight again. The checklist is in git history (commit fabf802).
- Katsounaros W4 trap as the headline figure. It stays as a sanity case; the headline should now come from the synthesis data (SPEC section 11b).

## Open data issues (as of Oct 21)

- **Liao Fig. 50a/50b catalyst assignment (Jarrod's Q2): resolved Oct 21.** The SI caption (a = W-MoS2, b = MoS2) is right and the files are labelled correctly. Main-text Fig. 5e plots NO3--N against time out to 48 h for all three catalysts; read off the plot, W-MoS2 (orange) ends near 150 ug/mL N (about 11 mM) and MoS2 (pink) near 65 ug/mL (about 4.6 mM), matching our 50a final 11.47 mM and 50b final 4.55 mM. The main-text sentence "residual NO3- 4.64 mM and 11.78 mM" for "W-MoS2 and MoS2" lists them in the reverse order. Values read by eye from the figure, so treat the matching as clear but approximate.
- The printed Polatides k3 undershoots the digitized N2 curve (simulated N2 is 23 mM-N at 120 min against 34), so W5 is a good world but not an exact reproduction of Fig. 3. Do not tune a method against it.
- W5's potential axis maps the paper's Ag/AgCl scale to RHE at an assumed pH 7; the alphas are unaffected.
- The YBCO weight fractions are semi-quantitative (relative peak intensities from a neural-network phase identifier) and sum to about 100, so they hide any amorphous material.
- None of the three ARROWS3 targets is an NO3RR catalyst, so the synthesis-to-NO3RR link has no data behind it.
- The Catechol Benchmark (awesome-matchem-datasets) remains a possible out-of-domain test; its file columns and data licence are unchecked.
