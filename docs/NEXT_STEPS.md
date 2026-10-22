# Next steps

Only what is still to do. Background, findings and the dated record are in `docs/PROGRESS.md`; design and data facts in `docs/SPEC.md`; the investigator's own notes in `docs/INVESTIGATOR.md`. When a task is done, delete it here and add one dated line to PROGRESS.

Last updated Oct 22 during the lithium sensitivity campaign. Team: Daniel and Jarrod. Split: Jarrod the model side, Daniel literature and data. Earlier submission notes below are historical planning context, not newly verified deadlines.

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
2. **Chapman lithium sensitivity: closed for the demo.** The S1 lower-lithium job on spark-f7e2 hit its own 8 GB memory cap at 12:22 on Oct 22 and stopped at 336/436; it is left stopped, like the fig2_lower fixed sweep (PROGRESS, Oct 22), because the data reject the lower amounts. The headline holds on the S1 extraction (see `video/SCRIPT.md` caveats). Rerun `scripts/summarize_chapman_li_sensitivity.py` only if either is resumed.
3. **Plausibility rules for synthesis** with Daniel. Element balance is in. Still to add: at most two reactants per
   step, non-negative driving force (McDermott and Bartel are in `literature/04_synthesis/`), and a cap on unassigned
   material.
4. **Marimo app skeleton and a Pyodide check** (does scipy and the fit run in the WASM export at interactive speed). Do
   the check early.
5. **Second time-resolved case.** Zeng's LTOPO data are promising once scan times, starting states and the phase-fraction method are established. Kamm fits only a slow regime after three minutes; Kosuge's integrated diffusion laws require a defined reaction extent and singularity treatment before network use. See [literature review](LITERATURE_REVIEW_OCT22.md) and [LTOPO data contract](LTOPO_OCT22.md).
6. Small: W5's declared bounds for the second-order step disagree with the protocol's (`docs/INVESTIGATOR.md` question
   6); pick narrowing the world or widening the protocol.
7. **Valency access:** ask for it. If granted, run the seeds and queries of `scripts/openalex_citation_pass.py` there and
   compare lists (PROGRESS, OpenAlex entry).

## Daniel (literature and data)

1. **Finish S1 extraction verification and clarify the initial state.** The Fig. 2 metadata corrections are already applied. The Oct 22 independent S1 check resolved 23 of 24 predefined anchors; fitting-window differences were at most 0.50 wt%, but the earliest 750 C carbonate point differed by 1.06 wt% and one late anatase point was obscured. This supports those anchors, not every extracted point. The actual S1 row sums are 97.55–101.73 wt%. Keep full-extraction verification false until the remaining values are checked. Distinguish the prepared 5:2 mixture from carbonate remaining in the first frame, and establish heating, initial rutile and any unobserved material before interpreting fitted initial lithium physically. Details are in [the literature checks](LITERATURE_REVIEW_OCT22.md).
2. **Curated hackathon datasets and sponsors.** Datasets: looked at on both computers; nothing kinetic that is not already used (re-read of the awesome-matchem-datasets list on Oct 21 in PROGRESS). Still to do: sponsor access and the deadline (8 pm EDT Oct 22, confirmed by Daniel). Marimo: trial it (see PROGRESS, marimo note). Valency is Jarrod's.
3. ~~Read the SrCrO3 and Chem. Mater. 2026 papers~~: done Oct 21 (PROGRESS, Oct 21 evening). Still to do: ARROWS3's main text for what it already covers, and put the result in the one-pager's "relation to prior work".
4. **Connect LTOPO measurements with their provenance.** The endpoint converter exists (`scripts/arrows3_to_endpoint.py`, `schema/endpoint_dataset.schema.json` sketch). Reconcile the two identical XRD patterns with different yields and the paper/table yield discrepancy before using those endpoint records quantitatively. For a kinetic case, obtain Zeng's scan/time mapping, starting-state information and phase-fraction method. The current LTOPO example remains an endpoint table and a separately labeled synthetic identifiability check, not a measured kinetic fit. See [the LTOPO audit](LTOPO_OCT22.md). Keep `data/arrows3/` uncommitted (licence unconfirmed).
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
