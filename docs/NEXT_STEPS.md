# Next steps

Only what is still to do. Background, findings and the dated record are in `docs/PROGRESS.md`; design and data facts in `docs/SPEC.md`; the investigator's own notes in `docs/INVESTIGATOR.md`. When a task is done, delete it here and add one dated line to PROGRESS.

Last updated Oct 21 evening (hackathon day 1). Team: Daniel and Jarrod. Split: Jarrod the model side, Daniel literature and data.

## Deadlines and gates

- Video and one-pager drafted by midday Oct 22; submission deadline stated as 5 pm PT Oct 22 (unverified, confirm on the event page).
- **Gate today:** look at the curated hackathon datasets. If one has multi-species time-course kinetics, add it as an extra case; if all are materials-property tables, the synthesis direction stands. If neither, reassess before building further.

## Decisions (Daniel and Jarrod, agreed Oct 21)

1. **Domain: synthesis first, nitrate reduction as a labelled illustration (agreed Oct 21).** SPEC section 1b. The evaluator now runs both (Chapman results in `docs/SYNTHESIS.md`).
2. **Headline: Chapman (time-resolved, Ti basis) for the fit, LTOPO as the branch-point example (agreed Oct 21).** LTOPO: target only at 700 C, polymorph split in 10 of 14 sets (SPEC section 7e). YBCO stays the largest but time-less table.

## Jarrod (model side)

1. **Selection for extrapolation.** Development AICc picks poorly transferring members inside large spaces (Chapman
   top-1 ranks 4/36/11/36). Try selection on held-out time (fit early, predict late) or a complexity penalty tuned on the
   nitrate test bed, and report calibration: tight models are overconfident at 750 C.
2. **Chapman v2 datasets**, then rerun the baseline and one model run. Prefer `data/digitized_inputs/chapman2023_sifig_s1/` (SI Fig. S1; correct from t = 0, same CSV columns as the Fig. 2 extraction, so `scripts/chapman_to_dataset.py` already reads it unchanged (checked, output not committed); but its `GRID` starts at 0.3 min and `T_MIN` is 0.3, so the early-time advantage is unused until those are changed, and its notes text describes the Fig. 2 extraction). The Fig. 2 files in `data/real/` stay as they are so the `chapman750-*` runs remain reproducible. Done when the held-out ranks are reported for both versions.
   reported for both versions.
3. **Plausibility rules for synthesis** with Daniel. Element balance is in. Still to add: at most two reactants per
   step, non-negative driving force (McDermott and Bartel are in `literature/04_synthesis/`), and a cap on unassigned
   material.
4. **Marimo app skeleton and a Pyodide check** (does scipy and the fit run in the WASM export at interactive speed). Do
   the check early.
5. **Second time-resolved case.** Kamm et al. JACS 2022 (same group: completion at three temperatures x two packings)
   needs a diffusion-limited (t^1/2) rate law the engine does not have; Bianchini 2020 is the alternative.
6. Small: W5's declared bounds for the second-order step disagree with the protocol's (`docs/INVESTIGATOR.md` question
   6); pick narrowing the world or widening the protocol.
7. **Valency access:** ask for it. If granted, run the seeds and queries of `scripts/openalex_citation_pass.py` there and
   compare lists (PROGRESS, OpenAlex entry).

## Daniel (literature and data)

1. ~~Chapman extraction~~: done Oct 21. `VERIFICATION.md` was cross-read by Daniel; its five `meta.json` corrections are applied and `verified_against_figure` is set with the scope "t >= 0.35 min". Because SI Fig. S1 (separate line curves) is cleaner than the stacked Fig. 2, there is a second extraction, `data/digitized_inputs/chapman2023_sifig_s1/` (`scripts/extract_chapman_si_s1.py`): it agrees with the Fig. 2 extraction to 0.2-0.55 wt % RMS, is correct before 0.35 min (rutile about 4 wt % at t = 0, the 750 C Li2TiO3 peak at 0.3 min), and sums to 99.5-101.7 wt %. Still to do for you: a spot-check of the S1 extraction against the printed SI figure, then set its `verified_against_figure`.
   Apply the five `meta.json` corrections listed there, give it a quick look yourself, then set `verified_against_figure`
   with the scope "t >= 0.35 min".
2. **Curated hackathon datasets and sponsors.** Datasets: looked at on both computers; nothing kinetic that is not already used (re-read of the awesome-matchem-datasets list on Oct 21 in PROGRESS). Still to do: sponsor access and the deadline (8 pm EDT Oct 22, confirmed by Daniel). Marimo: trial it (see PROGRESS, marimo note). Valency is Jarrod's.
3. ~~Read the SrCrO3 and Chem. Mater. 2026 papers~~: done Oct 21 (PROGRESS, Oct 21 evening). Still to do: ARROWS3's main text for what it already covers, and put the result in the one-pager's "relation to prior work".
4. **Data converters** (with Claude): ARROWS3 to an endpoint dataset is done (`scripts/arrows3_to_endpoint.py`, `schema/endpoint_dataset.schema.json` sketch; unverified YBCO entries dropped and why, SPEC 7e). Still to do: Jarrod decides how an endpoint dataset (a temperature series at one hold) enters the fit; until then the LTOPO example is a table and a figure, not a fit. Keep `data/arrows3/` uncommitted (licence unconfirmed).
5. Low priority: finish the SI-table match (names normalised); fetch the extra papers listed in PROGRESS section 2c.

## Shared (day 2)

- **Headline figure** and video script; the visual abstract (`docs/visual_abstract.html`, not in the repo any more) must be redone for the synthesis story.
- **One-pager** with an explicit limitations paragraph: XRD weight fractions are semi-quantitative and sum to about 100, in situ packing effects can change reaction progress by about 50%, the synthetic worlds are sanity checks, the NO3RR link has no data behind it.
- **Positioning:** ARROWS3 already does pairwise reasoning and learning from failures. Our additions are uncertainty and identifiability, a statement of what is not observable, literature-cited proposals and next-experiment planning. Say so plainly (SPEC section 7e).

## Cut list, first to go

1. Valency Bond citations inside the proposer (the literature search use stays).
2. Katsounaros W4 trap as the headline (stays as a sanity case).
3. NTMO (18 entries).
4. The live marimo fit; fall back to static figures.
5. The synthesis-to-NO3RR coupling illustration.

## Blocked on

- Curated datasets and sponsor details: unknown until we look at them.
- ARROWS3 itself: a run with Daniel's own Materials Project key was started in a scratch directory; not needed for the demo. Do not quote any ARROWS3 numbers until it finishes.
