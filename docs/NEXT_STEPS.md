# Next steps (as of Oct 19, two days before the hackathon)

Ordered by how much each one unblocks. Time estimates are rough.

## Daniel

### 1. Katsounaros 2012 Fig. 1: done

Digitized, converted to `data/real/katsounaros2012_fig1_sn_naoh.json` and checked against published model B (SPEC section 7b). The convention for the next figures is in `docs/DIGITIZING.md`: name each WebPlotDigitizer dataset by species id, export the unified CSV, drop it in a new folder with a copied `meta.json`, and run the converter.

### 2. Digitize more figures: mostly done

- Katsounaros 2008 Fig. 2: done. Converted to `data/real/katsounaros2008_fig2_sn_nacl_1M.json` (SPEC section 7c).
- Polatides 2005 Fig. 3: done. Converted to `data/real/polatides2005_fig3_sn85cu15_50mM.json` (SPEC section 7c).
- Polatides 2005 Figs. 5-6 (rate constants vs potential): still to do. Needed to replace the illustrative alphas in W5. No `data/digitized_inputs/` folder exists for them yet.

### 3. Read Ebenezer 2026: done

Initial-rate and 1 h data only; no time courses, and its reaction orders disagree between the table and the text. Not a replacement for Polatides Figs. 5-6 as the W5 calibration source. Details in `docs/SPEC.md` section 8b.

### 4. Check three small facts (15 min)

- ~~The potential for Liao Supp. Fig. 49~~: -0.6 V vs RHE, confirmed (identical to Fig. 48).
- Whether Liu 2024, Wang 2025 and Wu 2025 Source Data contain concentration-time sheets (match sheet names to figure captions; sheets are labelled by figure number only).
- ~~The Sanofi paper~~: main article now in the folder; DOI confirmed.

### 5. Get the repo to Jarrod (30 min)

`git init`, commit, push to a private GitHub repo and add him. PDFs and workbooks are git-ignored, so only code, schemas, worlds, small datasets and the literature index go up. Do this before you write him, so the email can point to the repo.

## Jarrod (what to ask him for)

The LLM side: given a dataset or world observation, propose candidate mechanisms as `mechanism.schema.json` objects, critique them for plausibility, and emit a `result.schema.json` file. Give him the four schemas, `docs/SPEC.md` section 9, worlds W2 and W3, and `worlds/library/`. A stub that returns the library mechanisms unchanged is enough to start, so his work never blocks on the fitter. Ask him to confirm the split before you commit to it.

## What I can do next (tell me to start)

1. **The fitter and enumeration baseline** (highest priority; everything else needs it). Maximum-likelihood fit under the noise model, AIC/BIC, plausibility rules (hidden-pool fraction, rate bounds), run on W1-W3 and on the Liao datasets. This is also what Jarrod's LLM side has to beat.
2. **W4 trap**: fit model A and model B to the digitized Katsounaros data and check we reproduce the reported Bayes factor of 2921. Needs your digitized CSVs.
3. **Identifiability**: profile likelihood for the sink placement question in Liao Fig. 50.
4. **A reply to Jarrod** and a one-page project summary for the hackathon team.

## Suggested plan for the two days

Before Oct 21: steps 1 and 5 above, plus my fitter. At the event, day 1: Jarrod's proposer/critic against W2 and W3, plus the Liao run with identifiability output. Day 2: experiment planning on W5, results table, demo. Skip the synthesis module unless everything else is stable.
