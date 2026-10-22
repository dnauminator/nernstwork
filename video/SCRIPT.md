# NernstWork video: shot list and voiceover

About 3:00 at a relaxed pace (roughly 150 words a minute). Daniel narrates; the shots are timed to the lines and can
be retimed to the recording. Shots 4, 5 and 5b are built (`Shots4to5`, 54 s); the others are planned.

Framing (Daniel, Oct 22): the engine proposes and finds plausible pathways; choosing among them is the weak point, so
an expert closes in with targeted experiments rather than a broad sweep. The data support the first half directly
(every AI search space held a top-4 predictor among hundreds of candidates). The second half is what the planner
offers (shot 7); we have not measured how many experiments it saves, so the narration does not claim a number.

| # | Time | On screen | Voiceover |
|---|---|---|---|
| 1 | 0:00–0:15 | The 725 °C phase curves draw themselves: anatase falls, Li₂TiO₃ spikes and decays, rutile and the spinel rise | Heat titanium dioxide with lithium carbonate and a battery material starts to form within minutes. In situ X-ray scattering lets us watch each phase rise and fall. Turning these curves into a reaction pathway is still done by hand. |
| 2 | 0:15–0:30 | The network lights up step by step, then multiplies into a grid of small networks | Which phase turns into which? At what rate? Are there steps we can't see? Even a handful of plausible steps combine into hundreds of candidate pathways, and the curves alone don't say which one is right. |
| 3 | 0:30–1:00 | Three-part loop: proposal text types on screen; mini-fits converge; the 750 °C run sits behind a seal | NernstWork splits the job between an AI model and code. The model reads the data and the literature and proposes the parts: the phases, the possible steps, the rate laws. Code builds every combination and fits each one to the runs at 700 and 725 °C. Then everything is frozen. The test is 750 °C, a temperature no model or agent saw. |
| 4 | 1:00–1:20 | **Built.** Three frozen models predict 750 °C; the sealed measurements land; ranks count down | Here are three frozen models predicting 750 °C. Now the measurements. A model from Claude Opus 5.5's search space ranks first of 153 reference models built by code. The rule that picks the best fit chose one that ranks fourth. The code-only baseline ranks eleventh. |
| 5 | 1:20–1:38 | **Built.** 153 reference models move from rank by fit to rank by prediction | Each gray line is one reference model, moving from its rank by fit to its rank by prediction. The best fit at 700 and 725 °C is not the best predictor at 750. |
| 5b | 1:38–1:54 | **Built.** Baseline and four AI runs: best in the search space, the agent's best plausible model, the rule's pick | Across two Claude runs and two Gemini runs, every search space held a top-four predictor, but picking by best fit chose anywhere from fourth to thirty-sixth. The AI narrows hundreds of pathways to a short list. Choosing among them takes an experiment. |
| 6 | 1:54–2:09 | One network diagram; activation energies from the four runs converge on each step; a lithium slider settles at the nominal amount | The runs agree on the chemistry: the same network, with similar activation energies from both models. They also flagged that the published phase fractions hold more lithium than the recipe supplied, and the conclusions hold when we vary the lithium input. |
| 7 | 2:09–2:29 | Two leading models overlap on the measured runs, then split apart under the proposed experiment | Then the agent says what to measure next. For the first Claude run, the most informative experiment is half the lithium carbonate at 725 °C, where its two leading models separate clearly at the two-minute mark. A targeted run like this is how the short list gets settled. |
| 8 | 2:29–2:54 | Nitrate test bed; the Wang rutile time course and fit; anatase (700 °C) and rutile (900 °C) side by side | The same engine runs on electrochemical nitrate reduction, our test bed. Valency's literature search found a direct link: Wang and colleagues made titanium dioxide at 700 °C, anatase, and at 900 °C, rutile, for nitrate-to-ammonia catalysts, and rutile performed best. That's the same change our models track. Closing the loop needs time courses for both. |
| 9 | 2:54–3:02 | Title card and credits | Propose broadly. Test on data the models never saw. Say what's unresolved, and plan the next experiment. |

## Facts behind each line

| Line | Value | Source |
|---|---|---|
| Battery material within minutes; in situ X-ray scattering | Li₄Ti₅O₁₂ appears within the first minute and grows over the 9.5 min record | Hu et al., JACS 145 (2023) 26545 (Chapman group), Fig. 2; `configs/investigations/chapman750.json` |
| Hundreds of candidate pathways | 154 baseline networks; 174–252 enumerated members per AI search space (plus 4 extra candidates each); 860 distinct dynamics across all runs | `docs/SYNTHESIS.md` results table; `docs/CHAPMAN_LI_SENSITIVITY_RESULTS.md` |
| First, fourth, eleventh of 153 | Ranks 1, 4, 11 among 153 reference models (RMSE 0.022, 0.025, 0.032) | `video/src/data/shots.json` (from the frozen runs) |
| Top-four predictor; fourth to thirty-sixth | Best in each AI space ranks 1, 4, 1, 1; the rule's picks rank 4, 36, 11, 36 | `shots.json`, `docs/examples/chapman750/arm_comparison.json` |
| Similar activation energies | Lithiation 210–224, anatase to rutile 279–295, spinel 231–245 kJ/mol | `docs/SYNTHESIS.md`, observation 4 |
| Lithium | Fitted starting carbonate returns to 0.39–0.40 per Ti and recovers the nominal results | `docs/PROGRESS.md` (Oct 22), `docs/CHAPMAN_LI_SENSITIVITY_RESULTS.md` |
| Half the lithium carbonate at 725 °C | The only design on the Opus run 1 menu with a separable pair: 7.2σ on rutile at 2 min | `docs/SYNTHESIS.md`, observation 6 |
| Wang 700 °C anatase, 900 °C rutile; rutile best | Calcined 3 h at 5 °C/min; at −0.5 V, conversion about 98% vs 85% and NH₃ FE about 79% vs 71% (read by eye from Fig. 3e,f) | Wang et al., J. Hazard. Mater. 488 (2025) 137174, section 2.1.2 and Fig. 3 |
| Wang time course | Rutile catalyst only (SI Fig. S18); fitted NO₃⁻→NO₂⁻→NH₄⁺ at 0.026 and 0.27 per min, about 9% of nitrate to an unmeasured sink | `docs/examples/wang2025_figS18/README.md` |

## Caveats to keep on screen or in the description

- Retrospective: the agents never saw 750 °C, but the team did inspect it earlier, and model pretraining may include the
  2023 paper.
- The scoring rule (one common noise scale) was changed after the baseline result and before the AI runs were scored.
- One chemistry, two runs per model. The models are overconfident about their own prediction error.
- The synthesis-to-catalysis link is an illustration: Wang's paper has a time course only for the rutile catalyst;
  the anatase comparison is endpoints only.
