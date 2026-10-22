# Next steps

Only what is still to do. Background, findings and the dated record are in `docs/PROGRESS.md`; design and data facts in `docs/SPEC.md`; the model side's results in `docs/SYNTHESIS.md`, `docs/INVESTIGATOR.md` and the Oct 22 notes (`docs/CHAPMAN_LI_SENSITIVITY_RESULTS.md`, `docs/LTOPO_OCT22.md`, `docs/VALENCY_BRIDGE_OCT22.md`, `docs/LITERATURE_REVIEW_OCT22.md`). When a task is done, delete it here and add one dated line to PROGRESS.

Last updated Oct 22 midday (hackathon day 2), from the Daniel-Jarrod email thread and Jarrod's `jarrod/chapman-li-sensitivity` branch (through commit `2df9ebd`, which closed the lithium question for the demo). Team: Daniel and Jarrod. Split: Jarrod the model side, Daniel literature and data. Times below are proposals, adjust them.

## Deadline and plan for today

- **Submission deadline: 8 pm EDT Oct 22** (Daniel noted it as confirmed; Jarrod's branch treats it as unverified, so re-read it on the event page). Aim to submit by 7:30 pm. Also check there: required deliverables, video length limit (the planning notes said 4 minutes; Jarrod proposes 2 to 3), whether the repo must be public.
- **Freeze the numbers at about 4 pm** (proposal). Only the S1 lower-lithium comparison is still running (on spark-f7e2); whatever is complete at the freeze is reported with its coverage, the rest is stated as not finished.
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
- LTOPO (measured): at 700 C, 10 of 14 sets report both target structures, 2 only one and 2 only the other, and all 14 still contain the LiTi2(PO4)3 impurity; at 400-600 C no entry contains the target. Say "competing product structures", not "polymorph selection mechanism".

Cannot say:
- That the automatic selection works. Selected members ranked 4th and 36th (Opus), 11th and 36th (Gemini) and 11th (baseline); the fresh lower-carbonate Opus run's pick ranked 10th of 151 (RMSE 0.046 against 0.025 for the earlier pick), the baseline's 11th. Choosing is the weak point; say so.
- That lithium is conserved or that the intermediate has a measured Li-deficient composition. Jarrod closed the lithium question for the demo (commit `2df9ebd`): fitting the starting carbonate within 0.25-0.40 sends every shortlisted carbonate-dependent model to 0.39-0.40 and recovers its nominal-lithium fit, so the data reject the fixed lower amounts and the nominal 0.4 stands. At the fixed lower values the original Opus pick predicts 750 C worse (RMSE about 0.051 against 0.025), and the fresh run kept titanium conservation only; those are model-conditional sensitivity results with poor residual adequacy. The plotted first-frame carbonate (0.28/0.30/0.36 per Ti) is carbonate remaining at 3 s, after heating and some conversion, not the weighed amount.
- That errors are calibrated, or that it generalises: one chemistry, two runs per model, the scoring rule was changed after seeing the baseline result and before scoring the AI runs, and the S1 lower-lithium comparison was still running at the time of writing (its rankings are provisional; the fixed-lower sweep on the Fig. 2 inputs was stopped at 343 of 904 by decision, recorded as a protocol deviation). On SI Fig. S1 the original Opus pick still ranks 4th and the baseline's pick moves from 11th to 5th, provisionally.
- That the first 10 seconds are isothermal. The apparatus reaches within 50 K of 750 C after 6 s and within 7 K after 10 s (SI Fig. S2); those frames mix heating and reaction.
- That synthesis predicts nitrate performance, or that the nitrate and Chapman comparisons are the same test (the nitrate one refits rates on the reserved data).
- That LTOPO's reaction mechanism or rate parameters were inferred. Two of the 700 C records share an identical XRD pattern but report different yields, and the paper's 54 % target yield for Li2O + TiO2 + P2O5 differs from 40 % in the table; neither is resolved.
- That we are first at Bayesian model selection on time-resolved XRD (Kosuge et al. 2026; a 2023 Sci. Rep. paper) or first to pair an identifiability check with an LLM discovery agent (LLM-IDEA, arXiv Oct 2026). The claim that holds is specific: precursor synthesis, a held-out temperature test, model-proposed parts, joint fit across temperatures, identifiability, next-experiment suggestion (SPEC section 7e).

## Jarrod (model side)

1. **Chapman lithium sensitivity: only S1 lower is left.** It runs on spark-f7e2 and syncs back by itself (`nernstwork-li-s1-sync-oct22`). When it finishes, rerun `scripts/summarize_chapman_li_sensitivity.py` and push the refreshed `docs/CHAPMAN_LI_SENSITIVITY_RESULTS.md`; if it is not done at the freeze, report it as unfinished. The fig2_lower fixed sweep is stopped for good. Keep the primary time grid at 0.3-9.5 min.
2. **Merge to `main`:** `jarrod/chapman-li-sensitivity` is three commits ahead of `d0ce7fa`; Daniel's doc edits sit on a branch cut from it, so merge yours first.
3. **Video material:** figures and screen captures for the outline above (Chapman 750 C held-out prediction `docs/examples/chapman_li_oct22/phase_predictions_750C.png`, the ranks plot, an identifiability or planner screen, the LTOPO endpoint counts and the synthetic ambiguity figure in `docs/examples/ltopo_oct22/`, the Wang S18 fit overlay in `docs/examples/wang2025_figS18/`).
4. **Wang S18 fit, wording for the video:** a sink (about 9 % of nitrate, 0.32 mM-N unmeasured at 180 min) is needed within the nitrate networks tried (14.6 AICc), but the gap is already there at the first sample (closure 0.90 at 30 min) and stays flat, so a constant offset between the three assays would look the same, the sink origin (nitrate or nitrite) is not identifiable (0.9 AICc), and the 10 min activation time is not evidence of activation. Potential and calcination temperature are not stated in the SI. Present it as an example, not a finding.
5. Later, only if time remains: selection for extrapolation (fit early, predict late); plausibility rules (at most two reactants, non-negative driving force, cap on unassigned material); contracting and diffusion rate laws from Kosuge's catalogue (differential forms with a small starting conversion); marimo live fit; W5 bound mismatch (`docs/INVESTIGATOR.md` question 6).

## Daniel (literature and data)

1. **Get Wang et al. 2025 (J. Hazard. Mater., doi 10.1016/j.jhazmat.2025.137174) main text through NYU access.** Looking for: a nitrate time course for the **anatase** TiO2/Cu2O catalyst (the S18 time course is rutile only, from the SI, which is free from Elsevier), the electrolysis potential for S18, and the TiO2 calcination temperatures (SI Fig. S4: 700 C anatase, 800 C mixed, 900 C rutile; SI Table S2: rutile against anatase NH3 yield 2.3 against 1.1 and FE 85.7 % against 67.0 % at -0.5 V). If an anatase time course exists, it is the one real synthesis-to-rate-constant comparison available; if not, the link stays a sentence. Also spot-check Jarrod's S18 digitization (`data/digitized_inputs/wang2025_figS18_rtio2cu2o/`, `verified_against_figure` is false).
2. **Finish the S1 extraction check and answer the lithium question for the one-pager.** The independent check resolved 23 of 24 anchors; the earliest 750 C carbonate point differs by 1.06 wt % (about 0.015 Li2CO3 per Ti, so the 0.36 value carries that much uncertainty) and one late anatase point is obscured. Keep `verified_against_figure` false for the full S1 extraction until those are looked at; the S1 row sums are 97.55-101.73 wt %. Your Rietveld view is wanted on what the first frame is missing (normalization, phase visibility, the heating transient, initial rutile); The evidence so far (Jarrod's tests, the sensitivity campaign, the literature check) favours the weighed 0.4 as the model input and treats the early values as carbonate remaining after 3 s.
3. **LTOPO provenance:** try to resolve the two issues in `docs/LTOPO_OCT22.md` from the paper and SI (which of the two identical-pattern 700 C records is right; why the paper says 54 % and the table 40 %). If it cannot be resolved today, the one-pager says so. Use the aggregate counts, not per-entry yields, in the video. The data stay in `data/arrows3/`, git-ignored.
4. **Read the abstracts of LLM-IDEA and the 2023 Sci. Rep. paper**, plus Kosuge and Karan/Persson if not yet done, and put the result in the one-pager's "relation to prior work". About 30 minutes. Valency does not index Kosuge or Karan/Persson; keep OpenAlex alongside it.
5. **One-pager and voice-over.** Draft the text: problem, method, the Chapman result, and the limitations paragraph (XRD weight fractions are semi-quantitative and sum to 97-102; the first ten seconds are not isothermal and the first frame is not the weighed mixture; in situ packing can change reaction progress by about 50 %; one chemistry; LTOPO endpoints cannot fix a rate model and carry two unresolved source inconsistencies; the nitrate link has no fittable data yet). Be free after about 4 pm to record.
6. **Submission check:** deliverables and limits on the event page; nothing under `data/arrows3/` and no API key in the repo (ARROWS3 data licence unconfirmed); decide whether the repo is public.
7. Low priority: the Zhang 2026 and Xu 2024 nitrate papers (only if Wang gives nothing); Zeng 2024 Fig. 3B/D as a future second time-resolved case (needs a scan-to-time mapping; no numeric table found); the ARROWS3 SI-table match; the extra papers in PROGRESS section 2c.

## Cut list, first to go

1. LTOPO beyond the table and the synthetic ambiguity figure.
2. The live marimo fit (static figures instead; a refit takes 12-14 s natively).
3. Valency Bond citations inside the proposer.
4. The contracting and diffusion rate laws, selection for extrapolation, a second time-resolved case.
5. The synthesis-to-nitrate link beyond one labelled sentence, unless an anatase time course turns up.
6. Katsounaros W4 trap, NTMO, the full ARROWS3 benchmark.

## Blocked on

- The S1 lower-lithium comparison (running): needed only for the S1 sentence in the one-pager; everything else for the demo is final.
- Event page: deadline, deliverables, video limit, public-repo requirement.
- Wang main text: whether an anatase time course exists.
