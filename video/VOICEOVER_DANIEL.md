# Voiceover for recording (Daniel)

A plain-language rewrite of the narration in `video/SCRIPT.md`, for an undergraduate-level audience. Same shots, same numbers, same order; only the wording changes, plus two fixes to the script (shot 4 and shot 9, see the notes column). Jarrod's `SCRIPT.md` is unchanged; update its narration column from this file if you agree.

Length: 505 words, about 3.3 minutes at 155 words a minute (463 words, about 3.0 minutes without the optional catalysis sentences). Jarrod's script is about 2:49. The shot timings in the Remotion project can be retimed to the recording.

## Narration

### Shot 1 (about 0:00, 83 words)

Heat titanium dioxide with lithium carbonate and a battery material forms. X-rays let us watch each substance rise and fall in real time. Our question: can an AI agent work out the reaction steps from curves like these? Does its set of candidate pathways include one that correctly forecasts a new experiment, and can we pick that one using only the data it was fitted to? We fit at 700 and 725 degrees, and forecast the 750-degree experiment, which no model has seen.

*Change from the script: Plain wording; 'predict a temperature' replaced by 'forecast the 750-degree experiment'.*

### Shot 3 (about ~0:33, 79 words)

NernstWork splits the job. The AI reads the data and notes from the literature, and proposes the building blocks: which substances, which steps, and how fast each might run, each with a reason. Code then checks that every combination conserves atoms, and fits them all the same way, using only the 700 and 725 degree data. The picks are locked in before we load 750. Finally, the AI tells us what the data can't settle, and which experiment would.

*Change from the script: 'reads the literature' narrowed to 'notes from the literature' (the agent gets a curated evidence pack, not open search).*

### Shot 4 (about ~1:07, 70 words)

First, what code alone would do: it tries 153 combinations of a fixed menu of steps and picks the best fit. That pick ranks eleventh at forecasting 750 degrees. Now the AI's route. It adds its own steps, code fits every combination, and the same best-fit rule picks one. That one ranks fourth. But the agent also named a second plausible model, before seeing 750, and that one ranks first.

*Change from the script: Fixes the script: the model ranking first is the agent's other plausible model (named before 750 C), not a hindsight pick from the whole search space. 'Rank' = place among the 153 code-built reference models by prediction error at 750 C.*

### Shot 5 (about ~1:36, 37 words)

Each gray line is one reference model. On the left, its rank by how well it fit the data we had. On the right, its rank at forecasting 750. The best fit is not the best forecaster.

*Change from the script: Same idea as the script, plainer.*

### Shot 5b (about ~1:52, 52 words)

Across four AI runs, two Claude and two Gemini, every set of candidates held a top-four forecaster, though we only know that after seeing 750. Picking by best fit chose anywhere from fourth to thirty-sixth. So the AI shrinks hundreds of possibilities to a short list. Choosing among them takes an experiment.

*Change from the script: Adds the hindsight caveat. This 'best in the whole search space' claim is different from shot 4, where the first-ranked model was on the agent's own short list.*

### Shot 7 (about ~2:13, 78 words)

So the agent suggests what to measure next: the experiment where its candidate explanations would disagree most. Its top pick is to halve the lithium carbonate at 725 degrees. That tests its own rival idea, that forming the battery material is linked to a second form of titanium dioxide, rutile, forming. By two minutes the two explanations differ by far more than measurement noise. Two of its leading models can't be told apart, and the agent says so.

*Change from the script: 'spinel' and '7 sigma' replaced by plain words.*

### Shot 9 (about ~2:42, 106 words)

Did the AI's candidates include a model that correctly forecasts the 750-degree experiment, having only seen 700 and 725? Yes, every time. Can we pick that model using only the 700 and 725 data? Not reliably. The chemistry agreed across models, and the agent said what it couldn't settle. [OPTIONAL: One illustration of why this matters: a study we found through Valency made titanium dioxide catalysts at 700 and 900 degrees, two different crystal forms, and the rutile one worked better for turning nitrate into ammonia. That's one example, not a result.] The AI is useful for proposing pathways. Choosing among them still takes a targeted experiment.

*Change from the script: Question 1 reworded (the old 'predict a new temperature' was unclear). Catalysis sentences marked optional: weakest-supported claim, cut first.*

## Say it this way

- Numbers: "seven hundred", "seven twenty-five", "seven fifty" (or "700 degrees"); "one fifty-three" for 153; "NernstWork" as one word.
- Terms to avoid or gloss: held-out temperature (say "the experiment no model has seen"), rate law (say "how fast a step runs"), activation energy (skip), Avrami, AICc, Rietveld (skip), identifiability (say "what the data can't tell apart"), sigma (say "far more than measurement noise").
- "Rank" always means place among the 153 reference models built by code, by forecast error at 750 degrees.

## Say these honestly (one sentence each, in the voiceover or on a closing card)

- One chemistry, two runs per model.
- The AI's choice among its candidates is inconsistent (fourth to thirty-sixth), so we do not claim it picks the right model.
- The published data were public, and the models may have seen the paper in training, so the test is retrospective.
- The models are overconfident about their own errors, and we claim no number for how many experiments this saves.
- The nitrate link, if kept, is one study and one example.

## Notes for Jarrod

- Shot 4 as scripted ("a model from Claude Opus 5.5's search space ranks first of 153") reads as a hindsight pick from the whole space. In `video/src/data/shots.json` the first-ranked model is `C74b7349674`, the agent's other plausible model, named before the 750 C data were loaded; the rule's pick `C914ebc19e9` ranks fourth. The on-screen card label already says "agent's other plausible model"; only the narration needs the change.
- Shot 1's second sub-question and shot 9's first answer say "predict an unseen temperature"; "forecast the 750 C experiment" says what is actually tested.
