# Next steps (as of Oct 21, hackathon day 1)

**Direction change (Oct 20).** The project is moving from NO3RR mechanism inference to solid-state synthesis pathways (SPEC section 1b); the NO3RR worlds and datasets stay as the engine's test bed. This file is reordered around that. The visual abstract (`docs/visual_abstract.html`) still shows the old NO3RR story and needs a rewrite once the framing is settled.

Go/no-go inputs: (1) the YBCO table is usable: **yes, checked Oct 20** (below). (2) NTMO and LTOPO tables: not checked. (3) What the curated datasets at kickoff look like: unknown. If the kickoff datasets are kinetic time courses, reassess.

## Daniel

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

**Gaps from the search.** I found no dataset that records synthesis precursor, temperature and phase composition together with NO3RR performance, and no paper combining a kinetic reaction network, in situ XRD and Bayesian inference for thermal solid-state synthesis. Both could be real gaps or narrow searches; try Google Scholar with "Bayesian", "in situ XRD" and "solid-state reaction", and "text-mined electrocatalysis synthesis".

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

### 3. Done so far, still true

- Digitized and checked against the papers: Katsounaros 2012 Fig. 1, Katsounaros 2008 Fig. 2, Polatides 2005 Fig. 3 and Fig. 6 (SPEC sections 7b-7d). W5 now uses the Polatides constants and alphas.
- Ebenezer 2026 read: no time courses, not a fit benchmark (SPEC section 8b).
- Repo is with Jarrod.

### 4. Parked

- Screening the Liu 2024, Wang 2025 and Wu 2025 Source Data for NO3RR time courses. Worth doing only if the NO3RR side gets more weight again. The checklist is in git history (commit fabf802).
- Katsounaros W4 trap as the headline figure. It stays as a sanity case; the headline should now come from the synthesis data (SPEC section 11b).

## Jarrod: investigator pipeline (Oct 20)

Built and tested: shared evaluator (MLE, profiled noise, AICc, Fisher and profile-likelihood identifiability, adequacy),
enumeration baseline over declared spaces, file-based investigation store with recovery, and a Pi-hosted investigator and
fresh-context reviewer. Design, commands, results and open questions for Daniel: `docs/INVESTIGATOR.md`.

## Jarrod (what to ask him for)

The LLM side: given a dataset or world observation, propose candidate mechanisms as schema objects, critique them for plausibility, and emit a result file. With the pivot, "mechanism" means a set of pairwise reactions among phases, and the schemas have to be extended to phases and elements first (SPEC section 7e); until then his stub can keep working on the NO3RR worlds W2 and W3. A stub that returns the library mechanisms unchanged is enough to start, so his work never blocks on the fitter. Ask him to confirm the split before you commit to it. If he has time after the stub works, a second step is retrieving published pathways through Valency's Bond and attaching a citation to each candidate (SPEC section 11b); optional.

## Recommended order for Daniel right now (Oct 21)

Division agreed with Jarrod on Oct 21: he handles the model side, you are in charge of literature and data.

1. **Send Jarrod the synthesis zip.** `nernstwork_literature_04_synthesis.zip` (outside the repo) holds only `04_synthesis`, since he already has `01`-`03`. It now includes the three ARROWS3 tables (YBCO 52 MB) and the black-box scripts, so it is bigger than before.
2. **Spot-check the Chapman extraction** (10 min): 5-10 points per panel against the printed figure, compare `reconstruction.png` with Fig. 2, then set `verified_against_figure` to true in `data/digitized_inputs/chapman2023_fig2/meta.json`. The paper and SI are now local (`literature/04_synthesis/ja3c10916*.pdf`).
3. **Reading, in this order** (about 2 h total; take notes into section 2b above): ARROWS3 main paper and SI (what it already does that we planned to claim); Precursor Genome (the loader and the three quality tiers); Miura (the pairwise rule). Leeman and Dara only for the limitations paragraph.
4. **Tell Jarrod what data he can build on today**, with the caveats above: Chapman (time-resolved, Ti basis, spot-check pending); LTOPO (58 verified entries, a polymorph branch point at 700 C, the cleanest small case); YBCO (verified entries only, no time axis); NTMO (18 entries, secondary); the Precursor Genome ledger (pairwise, no time, a prior and held-out test, loads as plain JSON). All but Chapman need the phase and element schema.
5. Confirm the framing and the headline target, then stop; kickoff is today.

## What I can do next (tell me to start)

Per your decision, fitter work starts at kickoff on Oct 21, not before. Until then only reading and data items are open.

1. **Summarise the NTMO and LTOPO files** once you download them, and finish the SI-table match.
2. **Draft the phase and element extension** of the schemas as a document only (no code): species type, element balance, temperature response, plausibility rules (SPEC section 7e).
3. **Rewrite the visual abstract** for the synthesis framing, once you confirm the framing and which target is the headline.
4. At kickoff: schema extension, `Exp.json` converter, the fitter and enumeration baseline, W4 as a sanity case, the marimo demo.
5. One-page project summary for the hackathon team.

## Plan for the two days (updated Oct 20)

- **Kickoff, Oct 21**: check the curated datasets first. If a curated dataset has multi-species time-course kinetics, add it as an extra case; if everything is materials-property tables, the synthesis direction is on firmer ground. Confirm the sponsors and the deadline (the notes say 5 pm PT on Oct 22; unverified).
- **Day 1**: schema extension to phases, YBCO converter, fitter and enumeration baseline (first regression-tested on W1-W3 and W5), Jarrod's proposer/critic, marimo app skeleton. Check early that scipy and the fit run in the marimo WASM export.
- **Day 2**: identifiability and next-experiment planning on YBCO, the headline figure, video and one-pager by midday, buffer before the deadline. The synthesis-to-NO3RR coupling is a labelled illustration, cut first if time runs short. The old synthesis-module stretch goal is now the main project.
- **Sponsors**: Marimo for the demo (do it). Valency Bond for citations on proposed pathways (only after Jarrod's stub works end to end). Adaption: skip unless a kickoff dataset fits.
- **Position against prior work**: ARROWS3 already does pairwise reasoning and learning from failures. Our additions are uncertainty and identifiability, a statement of what is not observable, literature-cited proposals, and next-experiment planning. Say so plainly.

## Open data issues to keep in mind

- **Liao Fig. 50a/50b catalyst assignment (Jarrod's Q2): resolved Oct 21.** The SI caption (a = W-MoS2, b = MoS2) is right and the files are labelled correctly. Main-text Fig. 5e plots NO3--N against time out to 48 h for all three catalysts; read off the plot, W-MoS2 (orange) ends near 150 ug/mL N (about 11 mM) and MoS2 (pink) near 65 ug/mL (about 4.6 mM), matching our 50a final 11.47 mM and 50b final 4.55 mM. The main-text sentence "residual NO3- 4.64 mM and 11.78 mM" for "W-MoS2 and MoS2" lists them in the reverse order. Values read by eye from the figure, so treat the matching as clear but approximate.
- The printed Polatides k3 undershoots the digitized N2 curve (simulated N2 is 23 mM-N at 120 min against 34), so W5 is a good world but not an exact reproduction of Fig. 3. Do not tune a method against it.
- W5's potential axis maps the paper's Ag/AgCl scale to RHE at an assumed pH 7; the alphas are unaffected.
- The YBCO weight fractions are semi-quantitative (relative peak intensities from a neural-network phase identifier) and sum to about 100, so they hide any amorphous material.
- None of the three ARROWS3 targets is an NO3RR catalyst, so the synthesis-to-NO3RR link has no data behind it.
- The Catechol Benchmark (awesome-matchem-datasets) remains a possible out-of-domain test; its file columns and data licence are unchecked.
