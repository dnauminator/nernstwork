# Next steps (as of Oct 20, the day before the hackathon)

**Direction change (Oct 20).** The project is moving from NO3RR mechanism inference to solid-state synthesis pathways (SPEC section 1b); the NO3RR worlds and datasets stay as the engine's test bed. This file is reordered around that. The visual abstract (`docs/visual_abstract.html`) still shows the old NO3RR story and needs a rewrite once the framing is settled.

Go/no-go inputs: (1) the YBCO table is usable: **yes, checked Oct 20** (below). (2) NTMO and LTOPO tables: not checked. (3) What the curated datasets at kickoff look like: unknown. If the kickoff datasets are kinetic time courses, reassess.

## Daniel

### 1. Data availability for the synthesis data (partly done)

**What the ARROWS3 paper says.** Szymanski, Nevatia, Bartel, Zeng, Ceder, Nat. Commun. 2023 (PMC10618174), data availability statement, verbatim: "The phase information associated with the experimental outcomes in the YBCO, NTMO, and LTOPO synthesis datasets ... can be found in the ARROWS3 repository." It adds: "Source data for all graphs are also provided as a Source Data file with this publication." Code availability: the public repository github.com/njszym/ARROWS, "archived at 10.5281/zenodo.8331001". The Zenodo record is a 101 kB archive of the code, with no paper link and no dataset description; the data are in the repository.

**What I found in the repository (Oct 20).**
- `Examples/YBCO/Exp.json`, `Examples/NTMO/Exp.json`, `Examples/LTOPO/Exp.json` are Git LFS pointers. A plain `git clone` gives 133-byte stubs. The real file is at `https://media.githubusercontent.com/media/njszym/ARROWS/main/Examples/YBCO/Exp.json` (52 MB). Same pattern for NTMO and LTOPO, which I did not download.
- YBCO: 47 precursor sets, 200 (set, temperature) entries at 600-1000 C, 149 flagged `Experimentally Verified` with raw XRD patterns, the rest inferred. Phases per entry with weight fractions that sum to about 100. Details and cautions in SPEC section 7e.
- No licence visible on the repository page; Zenodo says "Other (Open)". Do not commit the files.

**Still to do (about 30 min).**
1. Download the NTMO and LTOPO `Exp.json` the same way and tell me, or put them in a folder outside the repo; I will summarise them as I did YBCO.
2. ~~The 188-versus-149 count~~: partly answered Oct 20. 188 is the full grid (47 sets x 4 temperatures, 600-900 C) and the Methods say all of it was run for YBCO; the file's 200 entries include 12 at 1000 C, and why 51 are unverified is still open. NTMO (46) and LTOPO (120) are grid sizes only, ARROWS3 sampled part of them. The Source Data xlsx holds graph data only, not phase tables.
3. Check the paper's Supplementary Tables 1-3 (precursor sets) against the keys in `Exp.json`.
4. ~~Precursor Genome hosting~~: answered Oct 20 from the paper. `github.com/lauren-walters/precursor-genome` and Zenodo 10.5281/zenodo.21285546, CC BY 4.0; one 1 h dwell at one Tammann-rule temperature per pair, weight fractions from Dara, three-tier quality score. Still to do: open the links and check the ledger loads.

### 2. Reading and literature scouting

Scouted Oct 20 from search results and abstract pages only; none read in full. Priority order, with what to look for.

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

## Recommended order for Daniel right now (Oct 20)

1. Download the NTMO and LTOPO `Exp.json` (outside the repo) so I can summarise them; expect partial grids.
2. ~~Digitize Chapman Figs. 2-3~~: extracted Oct 20 by colour classification (`scripts/extract_chapman_fig2.py`, output in `data/digitized_inputs/chapman2023_fig2/`). Still to do for you (10 min): spot-check 5-10 points per panel against the printed figure and compare `reconstruction.png` with Fig. 2, then set `verified_against_figure` to true in its `meta.json`.
3. Open the Precursor Genome GitHub and Zenodo links and check the ledger loads.
4. Confirm the framing and the headline target, then stop; the fitter starts at kickoff.

## What I can do next (tell me to start)

Per your decision, fitter work starts at kickoff on Oct 21, not before. Until then only reading and data items are open.

1. **Summarise the NTMO and LTOPO files** once you download them, and chase down the 188-versus-149 count.
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
