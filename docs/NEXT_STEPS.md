# Next steps

Only what is still to do. Background, findings and the dated record are in `docs/PROGRESS.md`; design and data facts in `docs/SPEC.md`; the investigator's own notes in `docs/INVESTIGATOR.md`. When a task is done, delete it here and add one dated line to PROGRESS.

Last updated Oct 21 (hackathon day 1). Team: Daniel and Jarrod. Split: Jarrod the model side, Daniel literature and data.

## Deadlines and gates

- Video and one-pager drafted by midday Oct 22; submission deadline stated as 5 pm PT Oct 22 (unverified, confirm on the event page).
- **Gate today:** look at the curated hackathon datasets. If one has multi-species time-course kinetics, add it as an extra case; if all are materials-property tables, the synthesis direction stands. If neither, reassess before building further.

## Decisions needed (Daniel and Jarrod, today)

1. **Which domain does the demo run on?** Current plan: synthesis first, nitrate reduction as a labelled illustration (SPEC section 1b). The evaluator today only runs the nitrate worlds.
2. **Which dataset is the headline?** Suggestion (mine, not agreed): fit on Chapman (time-resolved, works in a Ti-equivalent basis, so closest to what the evaluator already does), and show LTOPO as the branch-point example (target only at 700 C, polymorph split in 10 of 14 sets; SPEC section 7e). YBCO as the largest but time-less table.
3. **Who owns the schema extension?** One person, one branch, the other rebases (it touches `schema/mechanism.schema.json` and `src/nernstwork/model.py`).

## Jarrod (model side)

1. **Extend the schema and evaluator from mM-N to a conserved element (Ti for Chapman), then phases and elements** (SPEC section 7e). Done when the evaluator fits Chapman Figs. 2-3 (`data/digitized_inputs/chapman2023_fig2/`) with the enumeration baseline and reports identifiability.
2. **Plausibility rules for synthesis** with Daniel: element balance, at most two reactants per step, non-negative driving force (McDermott and Bartel are in `literature/04_synthesis/`), cap on unassigned material. Done when they reject a candidate in `docs/INVESTIGATOR.md` style output.
3. **Proposer and reviewer on a synthesis case** once item 1 works. Optional after that: Valency Bond citations on each candidate.
4. **Marimo app skeleton and a Pyodide check** (does scipy and the fit run in the WASM export at interactive speed). Do the check early.
5. Small: W5's declared bounds for the second-order step disagree with the protocol's (`docs/INVESTIGATOR.md` question 6); pick narrowing the world or widening the protocol.
6. **Valency access:** ask for it. If granted, run the seeds and queries of `scripts/openalex_citation_pass.py` there and compare lists (PROGRESS, OpenAlex entry).

## Daniel (literature and data)

1. **Spot-check the Chapman extraction** (10 min): 5-10 points per panel against the printed figure, compare `reconstruction.png` with Fig. 2, then set `verified_against_figure` to true in `data/digitized_inputs/chapman2023_fig2/meta.json`. Paper and SI are in `literature/04_synthesis/`.
2. **Check the curated hackathon datasets** (the gate above) and confirm sponsor access and the deadline.
3. **Read, about 1.5 h:** the J. Phys. Chem. C 2026 SrCrO3 Bayesian paper (doi 10.1021/acs.jpcc.6c02717) and the Chem. Mater. 2026 diffusion-limited selectivity paper (10.1021/acs.chemmater.6c01610), because they set how far our novelty claim can go; then ARROWS3's main text for what it already covers. Write the result in the one-pager's "relation to prior work", not here.
4. **Confirm Jarrod has the synthesis zip** and knows the three ARROWS3 files are renamed (`ExpYBCO.json` and so on) and must not be committed (no licence found).
5. **Data converters** (with Claude): ARROWS3 tables to the dataset schema once item 1 of Jarrod's list lands. Rules: drop unverified YBCO entries, normalise phase names (`.cif` and numeric suffixes), keep LTOPO polymorph names distinct, carry a measurement-noise flag.
6. Low priority: finish the SI-table match (names normalised); fetch the extra papers listed in PROGRESS section 2c.

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
