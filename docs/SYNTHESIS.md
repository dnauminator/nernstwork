# Synthesis pathways: the engine on Chapman 2023

The investigator now works on solid-state synthesis data. The first case is Hu, ..., Chapman, JACS 145, 26545 (2023):
anatase TiO2 + Li2CO3 forming Li2TiO3 and then spinel Li4Ti5O12, followed by in situ X-ray scattering. The roles are
split three ways:

1. **The model proposes the parts.** These are the phases, every plausible step between them, and the rate-law forms
   each step may take, each with its support.
2. **Code chooses.** It enumerates every allowed combination, fits each one jointly to two temperatures (700 and 725 C),
   and judges the frozen choice by predicting the third (750 C) without refitting.
3. **The model interprets.** It says what the data cannot pin down and asks the planner which experiment would best
   separate what survives.

The nitrate investigation is unchanged and stays the regression test bed (`docs/INVESTIGATOR.md`).

## Why this split

On the nitrate data, Opus's own picks transferred poorly to the held-out run (ranks 54-121 of 731), while enumerating
over the parts it proposed found the rank-1 structure. Method papers in Daniel's literature folder point the same way:
Kabra et al. 2026 report that LLM-only baselines default to textbook forms, and Murphy et al. 2026 report that letting
the LLM grow the hypothesis space beats a fixed library. So the model widens the space, and statistics on reserved data
does the choosing.

## Pipeline

| Step | Who | Tool or command | What it does |
|---|---|---|---|
| Evidence | code | `init` | Builds the evidence pack: development data only, sourced notes with the authors' Avrami analysis withheld, conventions, protocol |
| Parts | model | `nw_submit_space` | Species with compositions and conserved elements; element-balanced steps with allowed forms (`first_order`, `avrami`) and support; combination rules |
| Enumerate | code | `submit_space` | Every subset of steps that forms the required products with no dead step, crossed with every allowed form, becomes an ordinary candidate. Oversized spaces are rejected, never truncated |
| Fit and rank | code | `evaluate`, `compare` | Joint maximum-likelihood fit at both temperatures (shared Arrhenius parameters, one noise sigma per phase), AICc ranking |
| Interpret | model | `nw_candidate_details`, `nw_profile` | Profile likelihoods, sloppy directions, adequacy, observational equivalence |
| Plan | model + code | `nw_plan_experiments` | Ranks candidate experiments by expected separation of the surviving models |
| Freeze | code | `freeze` | Lowest development AICc plus everything within 2, chosen by rule before any held-out data are read |
| Held-out test | code | `final-eval` | Predicts 750 C with development parameters (no refitting) and ranks the prediction among the 153 fitted reference-space members and among the run's own members (scores below) |

## Engine changes

- **Element balance.** `mechanism.conservation = {basis: "elements", elements: [...]}` and a per-species `composition`
  replace the nitrogen-equivalent rule. Non-integer compositions express non-stoichiometric phases.
- **Arrhenius.** `rate_law.temperature_dependence` gives k(T) = k exp(-Ea/R (1/T - 1/T_ref)). A free Ea is refused as
  insufficient data unless at least two temperatures are fitted jointly.
- **Avrami (JMAK).** `time_modulation.kind = "avrami"` multiplies the rate by n (k t)^(n-1) with a free exponent n. A
  lone first-order step then follows alpha = 1 - exp(-(k t)^n), which is tested against the closed form.
- **Joint fits.** Several datasets are fitted with one parameter vector, each simulated under its own conditions, with
  one profiled sigma per measured phase shared across temperatures. Single-dataset fits are numerically unchanged; the
  nitrate tests pass.
- **Prediction mode** (`final_evaluation.mode = "predict"`): parameter transfer, a stricter test than nitrate's
  structure-transfer refit.
  - **Primary score:** squared prediction error weighted by one noise scale per phase that is shared by all models. It is
    the development sigma of the reference member with the lowest development AICc.
  - **Also reported:**
    - the rank by RMSE;
    - the rank by each model's own predictive log-likelihood. This measures calibration and penalizes models whose
      development noise estimate understates their extrapolation error.
  - **A scoring change, disclosed.** The first implementation ranked by the model-specific log-likelihood. On the code-only
    baseline that score was shown to reward poor development fits (they inflate their own sigma) and to punish tight
    ones. It was replaced on Oct 21, after the baseline's held-out evaluation and before any model run was scored. The
    baseline's first evaluation file is kept as written.
- **Planner** (`src/nernstwork/planner.py`). It uses the Buzzi-Ferraris pairwise criterion with Akaike weights over the
  survivors:

      U = sum w_i w_j d^T (2 S_eps + G_i V_i G_i^T + G_j V_j G_j^T)^-1 d

  Parameter uncertainty is in the denominator, so disagreement caused only by poorly determined parameters (for example
  an Arrhenius extrapolation) is discounted. Murphy et al. 2026 report that rewarding parameter spread instead was
  unstable. A pair counts as separable when D_ij > n_points. The bounded score 0.5 log det(I + S_eps^-1 S_mu) is
  reported alongside.
- **Reboot-safe store.** An attempt that started before the last boot is never treated as alive, because pids are reused
  after a reboot.

## How the ambition principles shaped it

The design follows Felix Rieseberg's "How to be more ambitious" (Oct 2026) and the Oct 21 call with Daniel.

- **Altitude: the goal beyond the goal.** The goal is not "fit Chapman". It is that a new time-resolved dataset Daniel
  adds runs end to end without us: converter, evidence pack, model-proposed space, code selection, held-out test,
  experiment plan. Hence a generic dataset basis, element balance and spaces rather than Chapman-specific code.
- **Depth: the field's own instruments.**
  - Solid-state kinetics (JMAK/Avrami with Arrhenius, multi-temperature fits rather than single-curve model fitting).
  - Profile likelihood for identifiability.
  - Model-discrimination design (Buzzi-Ferraris).
  - An outside judge: a reserved temperature, plus the authors' Avrami slopes kept back as an independent check.
- **Challenge what you know.** The extraction was checked against the printed figure before any claim was made; see
  `data/digitized_inputs/chapman2023_fig2/VERIFICATION.md`.
- **Range: replace nouns with verbs.** "Synthesis pathway inference" is "deciding which reaction sequence produced the
  observed phase evolution, and what to measure next". That brings in kinetics, crystallography (normalised Rietveld
  fractions hide amorphous material), statistics (selection versus testing) and experimental design.
- **Outside judge, not self-judgement.** The model never ranks its own candidates. The evaluator ranks, and the reserved
  temperature is the verdict.

## Data findings (to check with Daniel)

1. **The extraction matches the printed Fig. 2 within 1 wt % from 0.35 min.** That is 42 spot checks plus an
   independent outline-tracing read and the authors' SI Fig. S1. Before that it is unreliable, by up to 22 wt %. Our first
   grid point (0.3 min) averages one unreliable column. This error is the same for every arm; the next version of the
   datasets starts at 0.35 min.
2. **The published fractions need more lithium than the mix contains.** With nominal formulas they imply 0.95-1.02 Li
   per Ti; the 5:2 mix supplies 0.8. The cause is not a colour mix-up: the printed labels and the SI legend agree. The
   authors' explanation, a Li-deficient Li2-xTiO3, needs x of about 0.4-0.6, which the paper does not give. This is why
   the reference space conserves Ti only. Both Opus runs reached the same diagnosis from the data and proposed Li1.6TiO3.
3. **The paper reports no activation energies.** Its Avrami analysis covers Li2TiO3 only (slopes about 1.4, then 0.5).
   Rutile is visibly consumed at 725 and 750 C, which supports a rutile-to-spinel step.
4. **The 750 C panel's last columns are an edge artefact**, so every series stops at 9.5 min. The development files carry
   no 750 C values.
5. **`meta.json` needs five corrections** (listed in VERIFICATION.md).

## Results (Oct 21): fit 700 + 725 C, predict 750 C without refitting

Full tables are in `docs/examples/chapman750/arm_comparison.md`. Per-run reports cover each run's spaces, candidates,
parameters, profiles, conclusion, experiment plan and plots: `docs/examples/chapman750/*.md`. Held-out ranks are among
the 153 fitted members of the code-authored reference space (lower is better). A rank of 1 means no reference member
predicts 750 C better.

| Run | Model | Spaces proposed (elements; Li2TiO3 form) | Members | Best dev AICc | Rule-selected top-1: rank (by RMSE) | Best agent-plausible rank | Best member of own space | LLM cost |
|---|---|---|---|---|---|---|---|---|
| Baseline | none | Ti only; nominal | 154 | -851.5 | 11 (7) | n/a | 1 (the reference itself) | none |
| Opus 1 | Opus 5.5 | Ti+Li with Li1.6TiO3; Ti only, nominal | 204 + 4 | -1196.0 | 4 (1) | 1 | 1, better than every reference member (RMSE 0.023) | $3.90 |
| Opus 2 | Opus 5.5 | Ti+Li with Li1.6TiO3; stoichiometric plus deficient | 252 + 4 | -1072.8 | 36 (16); another selected member ranks 4 | 4 | 4 | $2.77 |
| Gemini 1 | Gemini 4 Argon | Ti+Li with Li1.6TiO3; Ti only | 174 + 4 | -1137.1 | 11 (1) | 10 | 1 (same dynamics as the reference best) | $6.50 |
| Gemini 2 | Gemini 4 Argon | Ti+Li with Li1.5625TiO3; Ti only | 216 + 4 | -1121.0 | 36 (11) | 10 | 1 (same as above) | $4.43 |

Observations:

1. **The models' proposed parts fit the development data far better than the baseline.** The best development AICc
   ranges from -1073 to -1196, against -851 for the baseline. Every run's space contains a member that ranks 1st-4th of
   153 at predicting 750 C. Opus 1's contains one that beats every reference member: held-out score 472 against 604,
   RMSE 0.023 against 0.031 mol per mol Ti.
2. **Choosing by development AICc inside those larger spaces transfers unevenly.**
   - The rule-selected top-1 ranks 4th, 36th, 11th and 36th; the baseline's ranks 11th.
   - In every run, the agent's own plausible set held a member that transfers better than the rule's top-1: rank 1 vs
     4, 4 vs 36, 10 vs 11, and 10 vs 36.
   - This is the nitrate pattern again: the space is good, but the development criterion is an unreliable chooser for
     temperature extrapolation.
3. **Point predictions transfer; stated uncertainty does not.** The selected models predict 750 C with an RMSE of
   0.025-0.036 mol per mol Ti. Every tight model is overconfident, though: ranked by its own development noise, each
   comes 145th-151st.
4. **The network and its parameters agree across all four runs and both models.**
   - Lithiation: anatase + Li2CO3 -> Li2TiO3, fast, first order and limited by Li2CO3. Ea 210-224 kJ/mol.
   - Anatase -> rutile: nucleation and growth, Avrami n 2.7-3.0. Ea 279-295 kJ/mol.
   - Spinel: Li2TiO3 + anatase -> Li4Ti5O12, Avrami n 2.4-2.5. Ea 231-245 kJ/mol.
   - Early rutile while carbonate is present: large AICc support.
   - A slow rutile -> spinel route: its Ea sits at the 600 kJ/mol bound in three runs, so it is not identifiable.

   The activation energies rest on two temperatures 25 C apart: they are partly sloppy (paired Fisher directions), and
   the paper reports none to compare against. The leading models need no Avrami regime change for lithiation, because a
   first-order step that stops when Li2CO3 runs out reproduces the fast-then-slow shape. That the authors' change of
   slope (about 1.4 to 0.5) reflects carbonate exhaustion is an interpretation to check, not a result.
5. **Lithium.**
   - All four runs found that the published fractions over-use lithium. Each proposed Li-deficient Li2TiO3 (x about 0.4),
     the same diagnosis the figure check reached independently.
   - They disagree on whether a fixed deficiency is enough. In Opus 1, Ti-only conservation beats the Li-balanced
     Li1.6TiO3 version by 48 AICc for the same topology, and strictly stoichiometric Li2TiO3 is rejected by 386. In Opus 2
     a Li-conserving Li1.6TiO3 structure leads.
6. **Recommended next experiments (planner, development data only):**
   - **Opus 1:** half the Li2CO3 at 725 C, sampled to 30 min. It is the only design on its menu with a separable pair
     (7.2 sigma on rutile at 2 min).
   - **Opus 2, Gemini 1 and Gemini 2:** a run at 775-800 C, where 15-19 of 28 model pairs separate for Gemini.
   - **The two Gemini runs also:** a pre-made Li2TiO3 + rutile mix at 750 C, to test the rutile-to-spinel route
     directly.
7. **Cost and behaviour.**
   - Opus runs took 26-38 min, 38-40 tool calls and $2.77-3.90; Gemini runs took 69-77 min, 96-103 tool calls and
     $4.43-6.50 (list prices).
   - Both models also submitted four individual candidates, outside their spaces.
   - Gemini's selected top-1 in run 1 is one of them: a two-component representation of Li2-xTiO3.

Caveats:

- One chemistry from one lab.
- The first grid point (0.3 min) carries some extraction error (same for every arm).
- Ti fractions sum to 1 by construction.
- Two development temperatures.
- Two runs per model.

## What not to claim

Checked against the seven method papers in Daniel's folder:

- **Not new:**
  - **Information-gain planning:** Murphy et al. 2026 do it, scored on held-out predictions, in simulation.
  - **Hidden or unobserved species:** inferred by SiMBA, Murphy and Ma.
  - **LLM picks being weaker than search:** supported by Kabra and DASyR, so ours is supporting evidence, not a new
    result.
- **Not found in these seven papers:**
  - citation-carrying LLM proposals of model parts;
  - profile-likelihood identifiability reported next to model selection;
  - a planner run on physical data and checked against a held-out experiment.

## Next dataset

Kamm et al., JACS 144, 11975 (2022), from the same group: Na/Li ion exchange in NaFeO2, with completion versus time at 178,
195 and 213 C for two packing densities. It suits the hold-out-a-temperature test, but its kinetics are a fast jump
followed by t^1/2 growth, so it needs a diffusion-limited or two-population rate law the engine does not yet have. It is
plotted only, so it needs digitizing. Alternatives:

- Bianchini et al., Nat. Mater. 2020: P2-NaxCoO2 phase evolution through intermediates; Source Data may exist.
- The ARROWS3 YBCO table: endpoint phase fractions at four temperatures for 47 precursor sets, already machine-readable.

## Run it

    .venv/bin/python -m pytest -q tests/test_synthesis.py tests/test_chapman_converter.py
    python scripts/chapman_to_dataset.py data/digitized_inputs/chapman2023_fig2 data/real
    # code-only baseline
    python -m nernstwork.cli init --config configs/investigations/chapman750.json --arm enumeration --run-id chapman750-enumeration
    python -m nernstwork.cli enumerate --run chapman750-enumeration --space configs/spaces/chapman_core.json --evaluate --workers 6
    python -m nernstwork.cli freeze --run chapman750-enumeration && python -m nernstwork.cli final-eval --run chapman750-enumeration
    # model-proposed parts (Opus 5.5, or Gemini 4 Argon via OpenRouter)
    cd agent && node src/cli.ts start --config ../configs/investigations/chapman750.json --arm propose_space \
        --run-id chapman750-propose_space-opus1 --model anthropic/claude-opus-5-5 --thinking high

Memory: a fit worker uses about 150 MB, so 16 workers need about 2.5 GB. Run long jobs under a cap, for example
`systemd-run --user --scope -p MemoryMax=24G`, on a shared machine.
