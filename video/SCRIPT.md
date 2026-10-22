# NernstWork video: final script

The final cut is the narrated `Final` composition (3:42), described first below; the silent `Draft` (2:49) and the
planned voiceover follow for reference.

The research question, stated in the opening shot: can a language-model agent infer a solid-state reaction pathway
from time-resolved phase data? (1) Does the pathway space it proposes contain a model that predicts an unseen
temperature? (2) Can that model be selected from the training runs alone? What the video shows: the AI's search spaces held strong candidate pathways, selection among them is the weak
point, and the agent says what an experiment would have to settle. Framing agreed with Daniel on Oct 22. We have not
measured how many experiments this saves, so the narration claims no number. The first link from synthesis to catalyst
use (Daniel's goal since Oct 20) closes the findings.

Each shot carries one idea, the on-screen text stands without the narration, and the narration stands without the
pictures. Colours mean one thing throughout: blue the selection rule's pick, orange the agent's other plausible model,
aqua the best model in a search space, light gray the baseline, red (shot 7 only) the agent's rival explanation; the
four phase colours appear only in shot 1.

## Narration as recorded (Daniel, Oct 22) and the final cut

Daniel recorded one clip per shot plus a closing statement, deliberately "a little less technical so that it's
accessible", and sent `silence.mp3` as room tone "as a baseline for any sort of audio editing". The `Final` composition
(`npx remotion render src/index.ts Final out/final.mp4`) times each shot to its clip and anchors the visual beats to his
words (`make_timing.py`, timestamps from the transcripts); his room tone fills every gap; the mix is normalised to
-16 LUFS integrated, -1.5 dBTP. Total 3:42.

Transcribed with IBM Granite Speech 5.0 2B (best open model on the Hugging Face Open ASR Leaderboard, 5.06% average WER,
Oct 2026) and cross-checked with faster-whisper small.en word timestamps. Granite garbles the spoken numbers "700 and
725" (as "772.5", "707.5", "705"); word-level timing confirms Daniel says "700 and 725" in shots 1 and 9, and "can't
settle" in shot 3.

| Shot | In the cut | As recorded | Check against the sources |
|---|---|---|---|
| 1 | 0:00–0:30 | If you heat titanium dioxide with lithium carbonate, you will form a battery material. X-rays let us watch each substance rise and fall in real time. Our question: can an AI agent work out the reaction steps from curves like these? Does its set of candidate pathways include one that correctly forecasts a new experiment, and can we pick that one only using the data it was fitted to? We fit at 700 and 725 degrees and forecast the 750 degree experiment, which no model has seen. | Matches the research question and the study design |
| 3 | 0:30–1:00 | NernstWork splits the job. The AI reads the data and the notes from the literature and proposes the building blocks: which substances, which steps, and how fast each might run, each with a reason. Code then checks that every combination conserves atoms and fits them all the same way, using only the 700 and 725 degree data. The picks are locked in before we load 750. Finally, the AI tells us what the data can't settle and which experiment would. | Matches (element balance, one protocol, frozen before 750 °C) |
| 4 | 1:00–1:28 | First, what code alone would do. It tries 153 combinations of a fixed menu of steps and picks the best fit. That pick ranks 11th at forecasting 750 degrees. Now the AI's route. It adds its own steps, code fits every combination, and the same best-fit rule picks one. That one ranks fourth, but the agent also named the second plausible model before seeing 750, and that one ranks first. | Matches: ranks 11, 4, 1. (The baseline enumerates 154 networks; 153 fitted and form the reference set.) Scoreboard rows now appear in his order |
| 5 | 1:28–1:43 | Each gray line is one reference model. On the left is its ranking by how well it fit the data we had; on the right, its ranking at forecasting 750 degrees. As you can see, the best fit is not the best forecaster. | Matches |
| 5b | 1:43–2:05 | Across four AI runs, two Claude and two Gemini, every set of candidates held a top-four forecaster, though we only know that after seeing the 750 degree results. Picking by the best fit chose anywhere from fourth to 36th best, so the AI shrinks hundreds of possibilities to a short list, and choosing among them takes an experiment. | Matches, with the hindsight caveat stated |
| 7 | 2:05–2:33 | So the agent suggests what to measure next: the experiment where its candidate explanations would disagree the most. Its top pick is to halve the lithium carbonate at 725 degrees. That would test its rival idea that forming the battery material is linked to a second form of titanium dioxide, rutile, forming. By two minutes, the two explanations differ by far more than measurement noise. Two of its leading models can't be told apart, and the agent says so. | Matches (rival: rutile formation coupled to the spinel; 7.2σ of the fitted noise at 2 min) |
| 9 | 2:33–3:16 | Did the AI's candidates include a model that correctly forecasts the 750 degree experiment, having only seen 700 and 725? Yes, every time. Can we pick that model using only the 700 and 725 data? Not reliably. The chemistry agreed across models, and the agent said what it couldn't settle. One illustration of why this matters: a study we found through Valency made titanium dioxide catalysts at 700 and 900 degrees, two different crystal forms, and the rutile one worked better for turning nitrate into ammonia. That's one example, not a result. The AI is useful for proposing pathways. Choosing among them still takes a targeted experiment. | "Correctly forecasts… every time" is slightly stronger than the data: every AI search space held a top-4 forecaster, #1 in 3 of 4 runs. The on-screen findings carry the exact numbers |
| End | 3:16–3:42 | Through NernstWork, we've shown that an AI agent can narrow a large space of possible reaction pathways in solid-state synthesis down to a short list of good candidates and suggest what to measure next. The implication is more targeted experiments in physical labs, experiments chosen because they tell rival explanations apart rather than tried blindly. It points to a better way to design experiments. | Supported within the scope in the caveats below (retrospective, one chemistry). New end card carries this statement and the credits |

## Planned voiceover (the script Daniel worked from)

| # | Time | On screen | Voiceover |
|---|---|---|---|
| 1 | 0:00–0:27 | Part A: *Research question: Can a language-model agent infer a solid-state reaction pathway from time-resolved phase data?* Sub-questions: *(1) Does the pathway space it proposes contain a model that predicts an unseen temperature? (2) Can that model be selected from the training runs alone?* Part B: the test case (TiO₂ + Li₂CO₃ → Li₄Ti₅O₁₂, a battery anode, by in situ X-ray scattering), the 725 °C phase amounts drawing themselves, and the study design: 700 and 725 °C fitted, 750 °C sealed and predicted without refitting, each prediction ranked against 153 reference models built by code | Our research question: can a language-model agent infer a solid-state reaction pathway from time-resolved phase data? Does the pathway space it proposes contain a model that predicts an unseen temperature, and can that model be selected from the training runs alone? *(Part B)* The test case is lithium titanate, a battery anode, measured by in situ X-ray scattering. Models are fitted at 700 and 725 °C and predict 750 °C. |
| 3 | 0:27–1:01 | "How NernstWork works", one run start to finish (Claude Opus 5.5, run 1): the steps it proposed, each with rate-law options and a cited reason; 204 of 208 pathways checked for element balance and fitted, brightness by fit, its frozen picks in colour; frozen before the 750 °C data are loaded; what the data can't settle and its next experiment; a loop arrow back to the start | NernstWork divides the work between an AI model and code. The AI reads the data and the literature and proposes the parts: the phases, the possible steps, the rate laws, each with a reason. Code checks every combination for element balance and fits them all the same way to the runs at 700 and 725 °C. Then the parameters and picks are frozen, and the models are tested at 750 °C, data they never saw. Finally, the AI reports what the data can't settle, and which experiment would settle it. |
| 4 | 1:01–1:21 | "Predicting 750 °C without refitting." Three frozen models draw their predictions beside a sealed card; the measurements land; ranks count down to #1, #4, #11 of 153 | Here are three frozen models predicting 750 °C. Now the measurements. A model from Claude Opus 5.5's search space ranks first of 153 reference models built by code. The rule that picks the best fit chose one that ranks fourth. The code-only baseline ranks eleventh. |
| 5 | 1:21–1:39 | "The best fit is not the best predictor." 153 reference models move from rank by fit to rank by prediction; the baseline pick goes #1 → #11; the two Claude picks land #1 and #4 | Each gray line is one reference model, moving from its rank by fit to its rank by prediction. The best fit at 700 and 725 °C is not the best predictor at 750. |
| 5b | 1:39–1:55 | "Every AI run's search space held a top-4 predictor." Baseline and four AI runs; caption: picking by best fit chose #4 to #36 | Across two Claude runs and two Gemini runs, every search space held a top-four predictor, but picking by best fit chose anywhere from fourth to thirty-sixth. The AI narrows hundreds of pathways to a short list. Choosing among them takes an experiment. |
| 7 | 1:55–2:19 | "What to measure next." The planner's ranked experiments; under the top pick, the leading model (blue) and the agent's own rival (red) split at 2 min, 0.05 per Ti, about 7σ; a note that the other leading model stays within 0.8σ of the blue line | So the agent plans what to measure next, scoring experiments by how far the models' predictions would split. Its top pick, half the lithium carbonate at 725 °C, tests its own rival idea, that the spinel helps rutile form. The two explanations split clearly at two minutes. Its two leading models stay indistinguishable, and the agent reports that. |
| 9 | 2:19–2:49 | "What we found": five findings, the first two tagged as the answers to Q1 and Q2, then the first link to catalysis; the conclusion; credits | On the first question, yes: every AI search space held a top predictor. On the second, not reliably: picking by best fit was the weak point. The chemistry agreed across models, and the agent named what was unresolved. A first link to catalysis: a study found with Valency made titanium dioxide catalysts at 700 and 900 °C, anatase and rutile, and the rutile one performed best. The AI is useful for proposing pathways. Choosing among them still takes a targeted experiment. |

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
