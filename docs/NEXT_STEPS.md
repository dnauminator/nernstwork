# Next steps (as of Oct 20, the day before the hackathon)

Ordered by how much each one unblocks. Time estimates are rough.

## Daniel

### 1. Katsounaros 2012 Fig. 1: done

Digitized, converted to `data/real/katsounaros2012_fig1_sn_naoh.json` and checked against published model B (SPEC section 7b). The convention for the next figures is in `docs/DIGITIZING.md`: name each WebPlotDigitizer dataset by species id, export the unified CSV, drop it in a new folder with a copied `meta.json`, and run the converter.

### 2. Digitize more figures: done

- Katsounaros 2008 Fig. 2: done. Converted to `data/real/katsounaros2008_fig2_sn_nacl_1M.json` (SPEC section 7c).
- Polatides 2005 Fig. 3: done. Converted to `data/real/polatides2005_fig3_sn85cu15_50mM.json` (SPEC section 7c).
- Polatides 2005 Fig. 6: done. Stored in `data/digitized_inputs/polatides2005_fig6/`, checked against the paper's printed constants and alphas, and wired into W5 (SPEC section 7d). Fig. 5 is not needed.

### 3. Read Ebenezer 2026: done

Initial-rate and 1 h data only; no time courses, and its reaction orders disagree between the table and the text. Not a replacement for Polatides Figs. 5-6 as the W5 calibration source. Details in `docs/SPEC.md` section 8b.

### 4. Screen the Liu 2024, Wang 2025 and Wu 2025 Source Data (about 1-2 h; optional)

Goal: find out whether any of these workbooks hold concentration-time series that can become `data/real/` datasets (extra nitrate/nitrite/ammonia time courses, ideally with a nitrite feed). Bring me the three workbooks plus each paper's main text and SI, and we do it together; or do the steps below yourself. Nothing here blocks the fitter, so cap it at the time you have.

For each workbook:

1. List every sheet with its first rows (sheet names are only figure numbers, e.g. "Fig. 3c", "Supplementary Fig. 21"). I can print this for you with openpyxl.
2. Match each sheet to its caption in the paper or SI. Mark the sheet **useful** only if it has concentration (mM, mg/L, ug/mL or ppm) against time (min or h) for at least two of NO3-, NO2-, NH3/NH4+, with 5 or more time points at a single fixed potential. Discard Faradaic efficiency vs potential, current-time, LSV, XRD and similar sheets.
3. For each useful sheet, write down: catalyst, electrolyte and pH, starting nitrate concentration, potential and its reference scale, cell type, units, and which species are present.
4. Check N closure (NO3 + NO2 + NH3 as N, against the initial nitrate). Flag any sheet that is far from 1, since the gap is exactly what the benchmark is about. Check ammonium units too (as NH3 or as N).
5. Priority, in this order: any run fed with nitrite instead of nitrate (isolates the second step), then runs at 2 or more potentials for the same catalyst (more W5 data), then anything else.

Deliverable: one table in `data/real/README.md` (workbook, sheet, caption figure, conditions, species, points, closure, useful yes/no). Convert only the sheets marked useful, using `scripts/build_real_datasets.py`.

Order of the three: Liu 2024 first (nitrate and nitrite steps are already located), then Wang 2025, then Wu 2025 (pulsed electrolysis, so the potential is not fixed; probably the least usable).

### 5. Get the repo to Jarrod: done

PDFs and workbooks are git-ignored, so only code, schemas, worlds, small datasets and the literature index go up. Repo has been shared.

## Jarrod (what to ask him for)

The LLM side: given a dataset or world observation, propose candidate mechanisms as `mechanism.schema.json` objects, critique them for plausibility, and emit a `result.schema.json` file. Give him the four schemas, `docs/SPEC.md` section 9, worlds W2 and W3, and `worlds/library/`. A stub that returns the library mechanisms unchanged is enough to start, so his work never blocks on the fitter. Ask him to confirm the split before you commit to it. If he has time after the stub works, a second step is retrieving published NO3RR pathways through Valency's Bond and attaching a citation to each candidate (SPEC section 11b); it is optional.

## What I can do next (tell me to start)

Per your decision, the fitter work starts at kickoff on Oct 21, not before. Until then only the data and docs items (4 and 5 below) are open.

1. **The fitter and enumeration baseline** (highest priority; everything else needs it). Maximum-likelihood fit under the noise model, AIC/BIC, plausibility rules (hidden-pool fraction, rate bounds), run on W1-W3, W5 and on the Liao datasets. This is also what Jarrod's LLM side has to beat.
2. **W4 trap**: fit model A and model B to the digitized Katsounaros data and check we reproduce the reported Bayes factor of 2921.
3. **Identifiability**: profile likelihood for the sink placement question in Liao Fig. 50, and for W5's alphas (four potentials, so expect wide intervals).
4. **Source Data screening** (Daniel's step 4), if you send me the workbooks and papers.
5. One-page project summary for the hackathon team.
6. **Marimo demo app** (day 1-2): potential and pH sliders, live fit, mechanism ranking, WASM export. Needs the fitter first; keep it numpy/scipy only (SPEC section 11b).

## Plan for the two days (updated Oct 20 with the sponsor read, SPEC section 11b)

- **Kickoff, Oct 21**: check the curated datasets first. Decision rule: a multi-species time-course dataset becomes a seventh case; if everything is materials-property tables, reassess the project before building. Confirm the sponsors and the deadline (the notes say 5 pm PT on Oct 22; unverified).
- **Day 1**: fitter and enumeration baseline (W1-W3, W5, Liao 49/50), W4 on the digitized Katsounaros data, Jarrod's proposer/critic against W2 and W3, marimo app skeleton. Check early that scipy and the ODE fit run in the marimo WASM export.
- **Day 2**: identifiability and W5 experiment planning, the headline figure, video and one-pager by midday, buffer before the deadline. The synthesis module is cut.
- **Headline figure**: Katsounaros W4. Baseline picks model B on BIC but needs an implausibly large hidden pool; proposer, critic and identifiability flag it. Say "implausible by our rule", not "wrong", since the paper itself favors B. Synthetic worlds are sanity checks only.
- **Sponsors**: Marimo for the demo (cheap, do it). Valency Bond for citations on proposed mechanisms (only after Jarrod's stub works end to end; ask him if he has time). Adaption: skip unless a kickoff dataset fits.

## Open data issues to keep in mind

- The printed Polatides k3 undershoots the digitized N2 curve (simulated N2 is 23 mM-N at 120 min against 34), so W5 is a good world but not an exact reproduction of Fig. 3. Do not tune a method against it.
- W5's potential axis maps the paper's Ag/AgCl scale to RHE at an assumed pH 7; the alphas are unaffected.
- The Catechol Benchmark (awesome-matchem-datasets) is a possible out-of-domain test, but only after the fitter exists; the Kaggle file columns and data licence are unchecked.
