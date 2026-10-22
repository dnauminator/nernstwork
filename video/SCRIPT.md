# NernstWork video: final script

About 2:42 at a relaxed pace (roughly 155 words a minute). Daniel narrates. Every shot below is built and plays in
order in the `Draft` composition (`npx remotion render src/index.ts Draft out/draft.mp4`); shots can be retimed to the
recording.

The question: can an AI infer how a material forms from time-resolved data, and prove it on a temperature it never
saw? What the video shows: the AI's search spaces held strong candidate pathways, selection among them is the weak
point, and the agent says what an experiment would have to settle. Framing agreed with Daniel on Oct 22. We have not
measured how many experiments this saves, so the narration claims no number. The first link from synthesis to catalyst
use (Daniel's goal since Oct 20) closes the findings.

Each shot carries one idea, the on-screen text stands without the narration, and the narration stands without the
pictures. Colours mean one thing throughout: blue the selection rule's pick, orange the agent's other plausible model,
aqua the best model in a search space, light gray the baseline, red (shot 7 only) the agent's rival explanation; the
four phase colours appear only in shot 1.

| # | Time | On screen | Voiceover |
|---|---|---|---|
| 1 | 0:00–0:20 | The measured 725 °C phase amounts draw themselves with a running clock; the chart dims and the question appears: *How does a material form? Can an AI infer the reaction pathway from data like this, and prove it on a temperature it never saw?* | Heat titanium dioxide with lithium carbonate and a battery material starts to form within minutes. In situ X-ray scattering lets us watch each phase rise and fall, but turning these curves into a reaction pathway is still done by hand. Can an AI work it out, and prove it on a temperature it never saw? |
| 3 | 0:20–0:54 | "How NernstWork works", one run start to finish (Claude Opus 5.5, run 1): the steps it proposed, each with rate-law options and a cited reason; 204 of 208 pathways checked for element balance and fitted, brightness by fit, its frozen picks in colour; frozen before the 750 °C data are loaded; what the data can't settle and its next experiment; a loop arrow back to the start | NernstWork divides the work between an AI model and code. The AI reads the data and the literature and proposes the parts: the phases, the possible steps, the rate laws, each with a reason. Code checks every combination for element balance and fits them all the same way to the runs at 700 and 725 °C. Then the parameters and picks are frozen, and the models are tested at 750 °C, data they never saw. Finally, the AI reports what the data can't settle, and which experiment would settle it. |
| 4 | 0:54–1:14 | "Predicting 750 °C without refitting." Three frozen models draw their predictions beside a sealed card; the measurements land; ranks count down to #1, #4, #11 of 153 | Here are three frozen models predicting 750 °C. Now the measurements. A model from Claude Opus 5.5's search space ranks first of 153 reference models built by code. The rule that picks the best fit chose one that ranks fourth. The code-only baseline ranks eleventh. |
| 5 | 1:14–1:32 | "The best fit is not the best predictor." 153 reference models move from rank by fit to rank by prediction; the baseline pick goes #1 → #11; the two Claude picks land #1 and #4 | Each gray line is one reference model, moving from its rank by fit to its rank by prediction. The best fit at 700 and 725 °C is not the best predictor at 750. |
| 5b | 1:32–1:48 | "Every AI run's search space held a top-4 predictor." Baseline and four AI runs; caption: picking by best fit chose #4 to #36 | Across two Claude runs and two Gemini runs, every search space held a top-four predictor, but picking by best fit chose anywhere from fourth to thirty-sixth. The AI narrows hundreds of pathways to a short list. Choosing among them takes an experiment. |
| 7 | 1:48–2:12 | "What to measure next." The planner's ranked experiments; under the top pick, the leading model (blue) and the agent's own rival (red) split at 2 min, 0.05 per Ti, about 7σ; a note that the other leading model stays within 0.8σ of the blue line | So the agent plans what to measure next, scoring experiments by how far the models' predictions would split. Its top pick, half the lithium carbonate at 725 °C, tests its own rival idea, that the spinel helps rutile form. The two explanations split clearly at two minutes. Its two leading models stay indistinguishable, and the agent reports that. |
| 9 | 2:12–2:42 | "What we found": five findings from the runs and the Wang link; the conclusion; credits | Across the runs, the AI's search spaces held top predictors, picking among them was the weak point, the chemistry agreed across models, and the agent named what was unresolved. There is also a first link to catalysis. A study found with Valency made titanium dioxide catalysts at 700 and 900 °C, anatase and rutile, and the rutile one performed best. Our engine fits its nitrate data. The AI is useful for proposing pathways. Choosing among them still takes a targeted experiment. |

## Facts behind each line

| Line | Value | Source |
|---|---|---|
| Battery material within minutes; in situ X-ray scattering | Li₄Ti₅O₁₂ is present from the first frame and grows over the 9.5 min record | Hu et al., JACS 145 (2023) 26545 (Chapman group), Fig. 2; `data/real/chapman2023_fig2_*.json` |
| 204 of 208 pathways checked and fitted; frozen picks | Claude Opus 5.5 run 1: 208 candidates, each validated for element balance; 204 fitted; the frozen picks are #1 and #2 by development AICc | `investigations/runs/chapman750-propose_space-opus1/frozen.json` via `video/src/data/shots.json` |
| Hundreds of pathways | 154 baseline networks; 174–252 enumerated members per AI search space (plus 4 extra candidates each); 860 distinct dynamics across all runs | `docs/SYNTHESIS.md` results table; `docs/CHAPMAN_LI_SENSITIVITY_RESULTS.md` |
| First, fourth, eleventh of 153 | Ranks 1, 4, 11 among 153 reference models (RMSE 0.022, 0.025, 0.032) | `shots.json` (from the frozen runs' final evaluations) |
| Top-four predictor; fourth to thirty-sixth | Best in each AI search space ranks 1, 4, 1, 1; the rule's picks rank 4, 36, 11, 36 | `shots.json`, `docs/examples/chapman750/arm_comparison.json` |
| Top experiment and the rival | Half the Li₂CO₃ at 725 °C, sampled to 30 min, ranks first of the planner's menu and separates 1 of 6 model pairs: the rule's pick vs the agent's own rival (rutile formation coupled to the spinel), 0.05 per Ti in rutile at 2 min, 7.2σ of the fitted noise. The two leading models stay within 0.8σ | `investigations/runs/chapman750-propose_space-opus1/analyses/plan-2.json` via `shots.json`; the run's conclusion |
| The chemistry agrees | The same network across all four runs and both models; activation energies: lithiation 210–224, anatase to rutile 279–295, spinel 231–245 kJ/mol | `docs/SYNTHESIS.md`, observation 4 |
| What's unresolved | The two leading pathways are indistinguishable; the rutile-to-spinel activation energy sits at its bound; the plotted phases do not balance lithium | The run's conclusion (`conclusions/`); lithium checks in `docs/PROGRESS.md` (Oct 22) |
| First link to catalysis | Valency surfaced Wang et al. 2025; TiO₂ calcined 3 h at 700 °C (anatase) or 900 °C (rutile) for TiO₂/Cu₂O nitrate-to-ammonia catalysts; rutile best (at −0.5 V about 98% vs 85% conversion, 79% vs 71% NH₃ FE, read by eye from Fig. 3e,f); our fit of the rutile catalyst's time course (SI Fig. S18): NO₃⁻→NO₂⁻→NH₄⁺ at 0.026 and 0.27 per min. The article has no anatase time course, so the link is illustrative | Wang et al., J. Hazard. Mater. 488 (2025) 137174; `docs/VALENCY_BRIDGE_OCT22.md`; `docs/examples/wang2025_figS18/README.md` |

## Caveats (for the description or a final card)

- Retrospective: the agents and the fits never saw 750 °C, but the team had seen the published figure, and model
  pretraining may include the 2023 paper.
- The scoring rule (one common noise scale) was changed after the baseline result and before the AI runs were scored.
- One chemistry, two runs per model. The models are overconfident about their own prediction error.
- The lithium inconsistency was checked: fitting the starting carbonate returns it to the nominal 0.4 per Ti and
  recovers the original results; the lower plotted amounts were not adopted.
- Extraction: on the cleaner SI Fig. S1 extraction (Daniel's), the agent's other pick still ranks #1 of the reference
  models at 750 °C (RMSE 0.021) and the rule's pick #4 (0.024); the baseline's pick changes to a different model and
  ranks #5 instead of #11. Sources: `docs/CHAPMAN_LI_SENSITIVITY_RESULTS.md` (s1_nominal rows) and the s1_nominal
  score records in `data/derived/chapman_li_sensitivity/scores/` (local).
- The catalysis link is one study, endpoint comparisons plus one rutile time course; it is not a fitted
  synthesis-to-rate-constant pair.
