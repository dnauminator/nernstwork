# NernstWork video: final script

About 2:29 at a relaxed pace (roughly 155 words a minute). Daniel narrates. Every shot below is built and plays in
order in the `Draft` composition (`npx remotion render src/index.ts Draft out/draft.mp4`); shots can be retimed to the
recording. The nitrate test bed and the Wang rutile/anatase link are left to the submission description.

The question: can an AI infer how a material forms from time-resolved data, and prove it on a temperature it never
saw? The answer the video gives: it finds strong candidate pathways, the selection among them is the weak point, and it
says what an experiment would have to settle. Framing agreed with Daniel on Oct 22: the engine proposes and finds
plausible pathways; choosing among them is where a targeted experiment comes in. We have not measured how many
experiments that saves, so the narration claims no number.

| # | Time | On screen | Voiceover |
|---|---|---|---|
| 1 | 0:00–0:20 | The measured 725 °C phase amounts draw themselves with a running clock; the chart dims and the question appears: *How does a material form? Can an AI infer the reaction pathway from data like this, and prove it on a temperature it never saw?* | Heat titanium dioxide with lithium carbonate and a battery material starts to form within minutes. In situ X-ray scattering lets us watch each phase rise and fall, but turning these curves into a reaction pathway is still done by hand. Can an AI work it out, and prove it on a temperature it never saw? |
| 3 | 0:20–0:53 | "The AI proposes, code tests, the data decide." Four cards for Claude Opus 5.5, run 1: the steps it proposed with rate-law options and cited reasons; 204 of 208 pathways fitted, brightness by fit, its frozen picks in colour; frozen before the 750 °C data are loaded; what the data can't settle and its next experiment; a loop arrow back to the start | NernstWork splits the job. The AI reads the data and the literature and proposes the parts: the phases, the possible steps, the rate laws, each with a reason. Code builds every combination and fits them all the same way to the runs at 700 and 725 °C. Then the parameters and picks are frozen, and the models are tested at 750 °C, data they never saw. Finally, the AI reports what the data can't settle, and which experiment would settle it. |
| 4 | 0:53–1:13 | "Predicting 750 °C without refitting." Three frozen models draw their predictions beside a sealed card; the measurements land; ranks count down to #1, #4, #11 of 153 | Here are three frozen models predicting 750 °C. Now the measurements. A model from Claude Opus 5.5's search space ranks first of 153 reference models built by code. The rule that picks the best fit chose one that ranks fourth. The code-only baseline ranks eleventh. |
| 5 | 1:13–1:31 | "The best fit is not the best predictor." 153 reference models move from rank by fit to rank by prediction; the baseline pick goes #1 → #11; the two Claude picks land #1 and #4 | Each gray line is one reference model, moving from its rank by fit to its rank by prediction. The best fit at 700 and 725 °C is not the best predictor at 750. |
| 5b | 1:31–1:47 | "Every AI run's search space held a top-4 predictor." Baseline and four AI runs; caption: picking by best fit chose #4 to #36 | Across two Claude runs and two Gemini runs, every search space held a top-four predictor, but picking by best fit chose anywhere from fourth to thirty-sixth. The AI narrows hundreds of pathways to a short list. Choosing among them takes an experiment. |
| 7 | 1:47–2:11 | "What to measure next." The planner's ranked experiments; under the top pick, the two leading models overlap while the agent's own rival splits off at 2 min (0.05 per Ti, about 7σ) | So the agent plans what to measure next, scoring experiments by how far the models' predictions would split. Its top pick, half the lithium carbonate at 725 °C, tests its own rival idea, that the spinel helps rutile form. The two explanations split clearly at two minutes. Its two leading models stay indistinguishable, and it says so. |
| 9 | 2:11–2:29 | "What we found": four findings computed from the runs, the closing line, credits | The AI's search spaces held top predictors. Picking among them is the weak point. The chemistry agrees across models, and the agent says what's unresolved and what to measure next. Propose broadly, test on data the models never saw, and plan the next experiment. |

## Facts behind each line

| Line | Value | Source |
|---|---|---|
| Battery material within minutes; in situ X-ray scattering | Li₄Ti₅O₁₂ is present from the first frame and grows over the 9.5 min record | Hu et al., JACS 145 (2023) 26545 (Chapman group), Fig. 2; `data/real/chapman2023_fig2_*.json` |
| 204 of 208 pathways fitted; frozen picks | Claude Opus 5.5 run 1: 208 candidates, 204 fitted; the frozen picks are #1 and #2 by development AICc | `investigations/runs/chapman750-propose_space-opus1/frozen.json` via `video/src/data/shots.json` |
| Hundreds of pathways | 154 baseline networks; 174–252 enumerated members per AI search space (plus 4 extra candidates each); 860 distinct dynamics across all runs | `docs/SYNTHESIS.md` results table; `docs/CHAPMAN_LI_SENSITIVITY_RESULTS.md` |
| First, fourth, eleventh of 153 | Ranks 1, 4, 11 among 153 reference models (RMSE 0.022, 0.025, 0.032) | `shots.json` (from the frozen runs' final evaluations) |
| Top-four predictor; fourth to thirty-sixth | Best in each AI search space ranks 1, 4, 1, 1; the rule's picks rank 4, 36, 11, 36 | `shots.json`, `docs/examples/chapman750/arm_comparison.json` |
| Top experiment and the rival | Half the Li₂CO₃ at 725 °C, sampled to 30 min, ranks first of the planner's menu and separates 1 of 6 model pairs: the rule's pick vs the agent's own rival (rutile formation coupled to the spinel), 0.05 per Ti in rutile at 2 min, 7.2σ of the fitted noise. The two leading models stay within 0.8σ | `investigations/runs/chapman750-propose_space-opus1/analyses/plan-2.json` via `shots.json`; the run's conclusion |
| The chemistry agrees | The same network across all four runs and both models; activation energies: lithiation 210–224, anatase to rutile 279–295, spinel 231–245 kJ/mol | `docs/SYNTHESIS.md`, observation 4 |
| What's unresolved | The two leading pathways are indistinguishable; the rutile-to-spinel activation energy sits at its bound; the plotted phases do not balance lithium | The run's conclusion (`conclusions/`); lithium checks in `docs/PROGRESS.md` (Oct 22) |

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
