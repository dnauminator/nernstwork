# Next steps

Only what is still to do. Background, findings and the dated record are in `docs/PROGRESS.md`; design and data facts in `docs/SPEC.md`; the model side's results in `docs/SYNTHESIS.md`, `docs/INVESTIGATOR.md` and the Oct 22 notes (`docs/CHAPMAN_LI_SENSITIVITY_RESULTS.md`, `docs/LTOPO_OCT22.md`, `docs/VALENCY_BRIDGE_OCT22.md`, `docs/LITERATURE_REVIEW_OCT22.md`). When a task is done, delete it here and add one dated line to PROGRESS.

Last updated Oct 22 early afternoon (hackathon day 2), from the Daniel-Jarrod email thread and Jarrod's `jarrod/chapman-li-sensitivity` branch (through commit `2df9ebd`, which closed the lithium question for the demo). Team: Daniel and Jarrod. Split: Jarrod the model side, Daniel literature and data. Times below are proposals, adjust them.

## Deadline and plan for today

- **Submission deadline: 8 pm EDT Oct 22** (Daniel noted it as confirmed; Jarrod's branch treats it as unverified, so re-read it on the event page). Aim to submit by 7:30 pm. Also check there: required deliverables, video length limit (the planning notes said 4 minutes; Jarrod proposes 2 to 3), whether the repo must be public.
- **Freeze the numbers at about 4 pm** (proposal). The lithium sensitivity runs are closed (S1 lower stopped at 336/436); report the numbers that exist, with their coverage.
- Until about 4 pm Daniel is in the lab (async: reading, checks, replies). About 4 to 6 pm: voice-over, one-pager. 6 to 7:30 pm: edit, check every claim against the list below, submit.

## Decisions

1. **Domain: synthesis first, nitrate reduction as a labelled illustration** (agreed Oct 21; SPEC section 1b).
2. **Headline: the Chapman 750 C held-out prediction** (time-resolved, Ti basis). Agreed Oct 21: LTOPO as the branch-point example. Updated Oct 22 after the LTOPO audit: LTOPO is shown as a *measured table of competing product structures plus a clearly labelled synthetic demonstration* that fixed-hold endpoints cannot fix a rate model. It is **not fitted**. (Proposal, needs your OK: drop the earlier plan to fit LTOPO with a single-time-point schema change.)
3. **The nitrate link:** one thread, labelled illustration only: the synthesis side makes anatase and rutile (Chapman); Wang et al. 2025 report that rutile TiO2/Cu2O is the better nitrate catalyst and give a nitrate time course for it (SI Fig. S18, digitized by Jarrod, fitted with the existing nitrate networks). No anatase time course is available yet.
4. **Video outline (Jarrod's proposal):** the problem; how it works (the model proposes the parts, code chooses with a held-out test, the model says what is unresolved and what to run next); the Chapman 750 C result; nitrate as the test bed. 2 to 3 minutes.

## Claims we can and cannot make (check the video script and the one-pager against this)

Can say (one chemistry, two runs per model; sources `docs/SYNTHESIS.md` and `docs/CHAPMAN_LI_SENSITIVITY_RESULTS.md`):
- In every run the model-proposed space contained a member ranking 1st to 4th of the reference models on the held-out 750 C data, and an Opus member beat every reference member. This is only known after seeing 750 C: it is about finding candidates, not choosing them. A fresh run using the lower carbonate values again contained a member that beat every reference member (held-out score 462 against 603) with a poor development rank.
- The runs agree on the pathway: Li2CO3-limited lithiation, anatase to rutile, a Li2TiO3 plus anatase route to the spinel, and a rutile-to-spinel route whose activation energy is not identifiable.
- The planner's suggestions (half the Li2CO3 at 725 C, or 775-800 C) are recommendations; none was tested.
- LTOPO (measured, from the repository table): at 700 C, 10 of 14 sets report both target structures, 2 only one and 2 only the other, and all 14 still contain the LiTi2(PO4)3 impurity; at 400-600 C no entry contains the target. The paper's own Fig. 6a (Source Data) is consistent in kind: the orthorhombic polymorph is measured at 700 C in sets 1 and 3 and predicted for sets 2 and 4-7, and only the optimised Li2O + TiO2 + P2O5 set (set 8) shows the triclinic one alone, with no LiTi2(PO4)3 at 400 C. Say "competing product structures", not "polymorph selection mechanism", and quote counts, not per-entry yields (the table's yields differ from the paper's, below).

Cannot say:
- That the automatic selection works. Selected members ranked 4th and 36th (Opus), 11th and 36th (Gemini) and 11th (baseline); the fresh lower-carbonate Opus run's pick ranked 10th of 151 (RMSE 0.046 against 0.025 for the earlier pick), the baseline's 11th. Choosing is the weak point; say so.
- That lithium is conserved or that the intermediate has a measured Li-deficient composition. Jarrod closed the lithium question for the demo (commit `2df9ebd`): fitting the starting carbonate within 0.25-0.40 sends every shortlisted carbonate-dependent model to 0.39-0.40 and recovers its nominal-lithium fit, so the data reject the fixed lower amounts and the nominal 0.4 stands. At the fixed lower values the original Opus pick predicts 750 C worse (RMSE about 0.051 against 0.025), and the fresh run kept titanium conservation only; those are model-conditional sensitivity results with poor residual adequacy. The plotted first-frame carbonate (0.28/0.30/0.36 per Ti) is carbonate remaining at 3 s, after heating and some conversion, not the weighed amount.
- That errors are calibrated, or that it generalises: one chemistry, two runs per model, the scoring rule was changed after seeing the baseline result and before scoring the AI runs, and the lower-lithium sweeps were stopped part-way (Fig. 2 inputs at 343 of 904 by decision, recorded as a protocol deviation; S1 at 336 of 436 by a memory cap). On the cleaner S1 extraction the rule's pick still ranks 4th, the agent's other model 1st, and the baseline's pick moves from 11th to 5th.
- That the first 10 seconds are isothermal. The apparatus reaches within 50 K of 750 C after 6 s and within 7 K after 10 s (SI Fig. S2); those frames mix heating and reaction.
- That synthesis predicts nitrate performance, or that the nitrate and Chapman comparisons are the same test (the nitrate one refits rates on the reserved data).
- That LTOPO's reaction mechanism or rate parameters were inferred, or that the repository table reproduces the paper's Fig. 6a. It does not: the 700 C polymorph fractions differ for every set measured there (paper, Source Data Fig. 6a: set 1 17 % triclinic and 35 % orthorhombic, set 3 48 % and 29 %, optimised set 54 % and 0 %; table: 52 % and 9 % for the set-1 recipe, 40 % and 0 % for the optimised set) while the 400 C impurity values agree where they can be matched (40 % and 0 %). Two 700 C table records also share one XRD pattern but report different fractions. Unresolved from the files.
- That we are first at Bayesian model selection on time-resolved XRD (Kosuge et al. 2026; a 2023 Sci. Rep. paper) or first to pair an identifiability check with an LLM discovery agent (LLM-IDEA, arXiv Oct 2026). The claim that holds is specific: precursor synthesis, a held-out temperature test, model-proposed parts, joint fit across temperatures, identifiability, next-experiment suggestion (SPEC section 7e).

## Jarrod (model side)

1. **Chapman lithium sensitivity: closed for the demo.** The S1 lower-lithium job on spark-f7e2 hit its own 8 GB memory cap at 12:22 on Oct 22 and stopped at 336/436; it is left stopped, like the fig2_lower fixed sweep (PROGRESS, Oct 22), because the data reject the lower amounts. The headline holds on the S1 extraction (`video/SCRIPT.md` caveats). Rerun `scripts/summarize_chapman_li_sensitivity.py` only if either is resumed.
2. **Video material:** figures and screen captures for the outline above (Chapman 750 C held-out prediction `docs/examples/chapman_li_oct22/phase_predictions_750C.png`, the ranks plot, an identifiability or planner screen, the LTOPO endpoint counts and the synthetic ambiguity figure in `docs/examples/ltopo_oct22/`, the Wang S18 fit overlay in `docs/examples/wang2025_figS18/`).
3. **Wang S18 fit, wording for the video:** a sink (about 9 % of nitrate, 0.32 mM-N unmeasured at 180 min) is needed within the nitrate networks tried (14.6 AICc), but the gap is already there at the first sample (closure 0.90 at 30 min) and stays flat, so a constant offset between the three assays would look the same, the sink origin (nitrate or nitrite) is not identifiable (0.9 AICc), and the 10 min activation time is not evidence of activation. Potential and calcination temperature are not stated in the SI. Present it as an example, not a finding.
4. **Wang 2025 main text: checked** (Jarrod, `docs/VALENCY_BRIDGE_OCT22.md`): it confirms TiO2 calcined at 700 C (anatase) and 900 C (rutile) and has endpoints only for anatase (at -0.5 V about 98 % against 85 % conversion and 79 % against 71 % NH3 FE, read by eye from Fig. 3e,f), no anatase time course. The nitrate link stays one labelled sentence; the shot-9 sentence in the video script is the only place it appears.
5. Later, only if time remains: selection for extrapolation (fit early, predict late); plausibility rules (at most two reactants, non-negative driving force, cap on unassigned material); contracting and diffusion rate laws from Kosuge's catalogue (differential forms with a small starting conversion); marimo live fit; W5 bound mismatch (`docs/INVESTIGATOR.md` question 6).

## Daniel (literature and data)

Done Oct 22 (details in PROGRESS): Wang 2025 main text obtained and sent to Jarrod; the S18 digitization spot-check looks correct; the S1 extraction checked and looks good; the Rietveld question analysed; the LTOPO table-versus-paper mismatch traced to its source (it is a table-versus-Source-Data difference, not resolvable from the files); LLM-IDEA and Kosuge read and `docs/RELATION_TO_PRIOR_WORK.md` written.

1. **Send Jarrod three things:** the first-frame (Rietveld) answer (PROGRESS, Oct 22 entry "first frame"), the LTOPO reconciliation (PROGRESS, same date) and `docs/RELATION_TO_PRIOR_WORK.md`. Then, if you are satisfied with the S1 check, set `verified_against_figure` in `data/digitized_inputs/chapman2023_sifig_s1/meta.json` with a scope that says what was checked (23 of 24 anchors; the 0.05 min 750 C carbonate point differs by 1.06 wt %).
2. **Read the one-pager draft against the claims list above** once Jarrod has the final Chapman and nitrate numbers (freeze at about 4 pm). Use `docs/RELATION_TO_PRIOR_WORK.md` for the prior-work paragraph; trim it to the length the submission allows.
3. **One-pager and voice-over** (about 4 pm onward). Limitations paragraph: XRD weight fractions are semi-quantitative and normalised to about 100; the first frame is not the weighed mixture and the first 6-10 s are not isothermal; separate capillaries start from visibly different compositions (first-frame carbonate 20.5, 21.3 and 24.9 wt % for the same 5:2 mix); in situ packing can change reaction progress by about 50 %; one chemistry; LTOPO endpoints cannot fix a rate model and the repository table disagrees with the paper's own Fig. 6a values; the nitrate link has one rutile time course and no anatase one unless Wang's main text has it.
4. **Submission check** (about 4 pm): deliverables, video limit, public repo, deadline on the event page; nothing under `data/arrows3/` and no API key in the repo.
5. Low priority: Zeng 2024 Fig. 3B/D as a future time-resolved LTOPO case (needs a scan-to-time mapping; no numeric table found); Zhang 2026 and Xu 2024 nitrate papers only if Wang gives nothing; the ARROWS3 SI-table match; the extra papers in PROGRESS section 2c.

## Cut list, first to go

1. LTOPO beyond the table and the synthetic ambiguity figure.
2. The live marimo fit (static figures instead; a refit takes 12-14 s natively).
3. Valency Bond citations inside the proposer.
4. The contracting and diffusion rate laws, selection for extrapolation, a second time-resolved case.
5. The synthesis-to-nitrate link beyond one labelled sentence, unless an anatase time course turns up.
6. Katsounaros W4 trap, NTMO, the full ARROWS3 benchmark.

## Blocked on

- Event page: deadline, deliverables, video limit, public-repo requirement.
