# Mechanism investigator: design notes, repository map, status

Working document for the agentic layer (Jarrod's side of SPEC section 10). It records what was found in the
repository before any behavior changed, the plan, and a checklist kept current as work lands.

## 1. Repository facts (audited Oct 20 2026, checkout `bf24f03`, branch `main`, remote `dnauminator/nernstwork`)

Path from source evidence to reported fit, as it exists before this work:

| Stage | Where | What actually runs |
|---|---|---|
| Source evidence | `LITERATURE.md` (index); `literature/` is git-ignored and empty in this checkout | Nothing local: PDFs and the Liao Source Data workbook are not in the repo |
| Extraction | `scripts/build_real_datasets.py` (Liao xlsx -> JSON, needs the workbook); `scripts/digitized_to_dataset.py` (WebPlotDigitizer CSV + `meta.json` -> JSON) | Digitized conversions reproduce from `data/digitized_inputs/`; Liao conversion cannot be rerun without the workbook |
| Datasets | `data/real/*.json` (6 files, `schema/dataset.schema.json`) | Time trajectories only (no endpoint/FE/rate data) |
| Mechanisms | `schema/mechanism.schema.json`; `worlds/W*.json` (ground truth); `worlds/library/*.json` | `nernstwork.validate_mechanism` (N balance, electrons vs oxidation states, Langmuir K, power-law orders) |
| Simulation | `src/nernstwork/mechanism.py::simulate` (LSODA, dict-based RHS) | Ignores `reversible`, `prior`, `fixed`, `bounds` |
| Fitting | `scripts/calibrate_liao.py`, `scripts/calibrate_katsounaros2008.py` | Ad hoc models hand-coded in each script (not the schema simulator); single least-squares objective; no uncertainty |
| Ranking | `calibrate_katsounaros2008.py` prints Gaussian AIC/BIC from RSS | No ranking code elsewhere |
| Enumeration, LLM, planner | SPEC sections 9-10 | Not implemented |
| Tests | `tests/` (14 tests) | Schema validity, world N conservation, converter round trip, Polatides k2 typo check |

Baseline reproduced before any change (venv `.venv`, Python 3.12.13, numpy 2.5.4, scipy 1.18.1, jsonschema 4.26.0):
`pytest -q` 14 passed; `python scripts/calibrate_liao.py data/real` and `python scripts/calibrate_katsounaros2008.py data/real`
reproduce every number in SPEC sections 7 and 7c (for example Fig. 50b with NO3 sink: RMSE 3.4 / 0.65 / 3.87 mM-N, sink 23.2 mM-N at 48 h;
Katsounaros 2008 BIC 588.8 / 527.6 / 403.9).

Model system: the repository does not name one. Liao 2025 Supp. Fig. 50b (MoS2) is the most developed real-data case
(Source Data, W2 is calibrated to it, SPEC section 12 open questions are about it, NEXT_STEPS plans "the Liao run with identifiability
output"); LITERATURE.md calls Katsounaros 2012 the "primary benchmark" for the hidden-intermediate question. This work uses Liao Fig. 50b
for development and holds out Fig. 50a, and treats Katsounaros 2012 as a literature-assisted retrospective case. **Question for Daniel.**

### Measurement semantics per source

| Dataset | Kind | Observed channels (mM-N) | Missing | Conditions known | Uncertainty |
|---|---|---|---|---|---|
| liao2025_mos2_suppfig50b, liao2025_wmos2_suppfig50a | measured (Source Data), trajectories, 18 points to 48 h | NO3, NO2, NH4+ (as `NH3`) | N2, N2O, NH2OH, gas phase, anolyte | -0.6 V vs RHE, 0.5 M K2SO4, H-cell, 60 mL | none reported; pH not reported |
| liao2025_agmos2_suppfig49 | measured, 12 points to 3 h | NO3, NO2, NH3 | as above | as above, Ag-MoS2 | none |
| katsounaros2012_fig1_sn_naoh | digitized, 7 points | NO3, NO2, N2, N2O, NH3 (N-equivalents) | hidden X, NH2OH | -2.2 V vs Ag/AgCl (not RHE), pH 14 | digitization only; figure shows the paper's model-B curves |
| katsounaros2008_fig2_sn_nacl_1M | digitized, 14-15 points | NO3, NO2, NH3, N2O (x2), N2 (x2); authors' N-loss as derived series | hidden pool | -2.8 V vs Ag/AgCl, pH not tracked | digitization only |
| polatides2005_fig3_sn85cu15_50mM | digitized, 8 points | NO3, NO2, NH3, N2 (x2 inferred from closure) | | -2.0 V vs Ag/AgCl | closure scatter about 10%; `units_unverified` |

Ebenezer 2026 has selectivity/FE and initial-rate data only and is not in `data/real`; it must not be mixed with trajectories.

### Defects and risks found in the existing path

1. `t = 0` points are the initial condition by construction (pinned or used to define `c0`), yet the calibration scripts count them as
   observations (inflates n, deflates sigma, biases BIC).
2. `calibrate_liao.py` weights residuals by each species' maximum (NO2 residuals weigh about 25x more per mM than NO3); this is an
   implicit noise model. It also fits unused parameters (`kl` without a leak, `tau` without a time term), harmless for the cost
   but wrong for any parameter count.
3. The schema cannot express a parameter shared across reactions (the calibration uses one `tau` for all steps; W2 stores four
   independent `tau` values). Parameter counts for model comparison need explicit ties.
4. `reversible: true` is accepted by the schema and silently simulated as irreversible.
5. Potential and pH dependence cannot be informed by a single-condition dataset; `simulate` requires a numeric potential even when
   the dataset has `potential_V_vs_RHE: null`.
6. Contamination: `worlds/W2...` and `worlds/library/parallel_sink_NO3_deact.json` are Daniel's fitted answer for Liao Fig. 50b,
   `worlds/W3...` is Katsounaros model B, and SPEC sections 7-7c state the fit conclusions. An investigator that can read the repo is
   doing literature/annotation-assisted recovery, not blind discovery.
7. A user-level Pi configuration can load skills, packages and context files; the investigator must not inherit any of them.

## 2. Plan

- Python backend (`src/nernstwork/`): compiled models with ties and explicit unsupported-feature statuses; a single evaluator
  (validate, canonical identity, multistart maximum likelihood with profiled per-channel noise, AICc/BIC, Fisher and profile-likelihood
  identifiability, residual adequacy, plausibility rules); a file-based investigation store with atomic, create-once commits, attempts and
  reconciliation; the enumeration baseline over a declared space; review bundles with pointer-checked citations; a JSON CLI bridge.
- Pi host (`agent/`, TypeScript, `@earendil-works/pi-coding-agent` 1.3.0 pinned): one persistent investigator session per run,
  fresh reviewer session per review, scientific tools that call the Python CLI, built-in file and shell tools confined to a bubblewrap
  sandbox that sees only the run workspace and the development evidence, no ambient context files, skills or extensions.
- Protocol: development on Liao Fig. 50b, final evaluation on Fig. 50a (complete held-out run, structure transfer with refit
  parameters). Arms: enumeration; agent proposals without critique; agent proposals with critique-driven revision; equal candidate budgets.

## 3. What exists now (map)

| Piece | Path | Role |
|---|---|---|
| Candidate contract | `schema/candidate.schema.json`; `tie` added to `schema/mechanism.schema.json` | Native mechanism plus observation map, per-element support (literature / data / speculative), assumptions, rationale, predictions, parent |
| Compiled model | `src/nernstwork/model.py` | Free-parameter vector with ties, transforms and protocol bounds; vectorized RHS checked against `mechanism.simulate`; explicit statuses |
| Data layer | `src/nernstwork/data.py` | Content hashes, observation channels (t = 0 is the initial condition, not an observation), factual dataset descriptions |
| Fitter | `src/nernstwork/fit.py` | Deterministic Latin-hypercube multistart; IRLS maximum likelihood with per-channel profiled sigma (floored); local Fisher screen; profile likelihood; runs-test adequacy |
| Identity | `src/nernstwork/canonical.py` | `dynamics_hash` (what the fitter sees; unobserved species anonymous) and `chem_hash` (adds oxidation states, electrons) |
| Shared evaluator | `src/nernstwork/evaluate.py` | One validation and fitting path for every proposer; code-computed ranking |
| Store | `src/nernstwork/store.py` | Files only: atomic replace, create-once commits, attempts, reconciliation, event log |
| Service | `src/nernstwork/investigation.py` | Runs, manifests, evidence packs, submissions, evaluation pool, profiles, discrimination, bundles, reviews, conclusions, freeze, held-out evaluation |
| Enumeration baseline | `src/nernstwork/enumerate.py`, `configs/spaces/*.json` | Declared spaces, simplest first |
| Reports | `src/nernstwork/report.py`, `src/nernstwork/plots.py` | Run report and arm comparison from stored artifacts (pre-registered or re-scored held-out view) |
| Sandbox toolkit | `src/nernstwork/nwlab.py`; snapshot per run in `runs/<id>/toolkit/` | `import nwlab` in the sandbox: validator, simulator and a lighter fitter, labelled exploratory |
| JSON bridge | `src/nernstwork/cli.py` | `python -m nernstwork.cli <command>` |
| Protocols, investigation config | `configs/protocols/*.json`, `configs/investigations/liao50.json` | Versioned and hashed into every result |
| Sourced paper notes | `data/evidence/liao2025_paper_notes.json` | Each claim with location and how it was checked; held-out-revealing claims marked |
| Pi host | `agent/src/*.ts`, `agent/prompts/*.md` | Investigator and reviewer sessions, sandbox, tools, arm orchestration, resume, cost cap |
| Tests | `tests/test_investigator.py`, `tests/test_synthetic_recovery.py`, `agent/test/host.test.ts` | Contracts listed in section 6 |

Run state is written under `investigations/` (git-ignored): `runs/<run_id>/` and the shared fit cache `cache/fits/<fit_key>/`.

## 4. How to use it

Setup (once):

    uv venv .venv --python 3.12 && uv pip install --python .venv/bin/python -r requirements.txt
    cd agent && npm ci && cd ..

Tests and checks:

    .venv/bin/python -m pytest -q                       # 62 tests: 15 existing + 47 new (synthetic cases take ~3 min)
    cd agent && npm run typecheck && npm test           # 5 host tests (sandbox, toolkit, file submit; mocked-model run)

Reproduce the earlier baseline, then the same model inside the shared evaluator:

    .venv/bin/python scripts/calibrate_liao.py data/real
    .venv/bin/python -m pytest -q tests/test_investigator.py -k legacy

Enumeration arm (no LLM):

    export PYTHONPATH=src
    .venv/bin/python -m nernstwork.cli init --config configs/investigations/liao50.json --arm enumeration --run-id liao50-enumeration-v3
    .venv/bin/python -m nernstwork.cli enumerate --run liao50-enumeration-v3 --space configs/spaces/liao_core.json --evaluate
    .venv/bin/python -m nernstwork.cli enumerate --run liao50-enumeration-v3 --space configs/spaces/liao_extended.json --evaluate

Agent arms (persistent Pi investigator; `--mock` swaps in the scripted offline model):

    cd agent
    node src/smoke.ts anthropic/claude-opus-5-5                      # verify the model id and credentials
    node src/cli.ts start --config ../configs/investigations/liao50.json --arm critique_revise \
        --run-id liao50-critique_revise-live1 --model anthropic/claude-opus-5-5
    node src/cli.ts resume --run liao50-critique_revise-live1         # after any interruption
    node src/cli.ts status --run liao50-critique_revise-live1         # host state, store state, orphaned tool calls
    node src/cli.ts ask --run liao50-critique_revise-live1 --message "..."   # steer the same investigator by hand

Credentials: an Anthropic API key from `ANTHROPIC_API_KEY` or from an owner-only file (`NW_ANTHROPIC_KEY_FILE`, default
`~/.config/nernstwork/anthropic_api_key`); without one, Pi's stored credentials. Keys never reach the Python backend or the
sandbox.

Arms: `propose_only` (one proposal round, no revision), `self_revise` (revision with fit results, no reviewer),
`critique_revise` (fresh-context review of a frozen bundle, then revision). `NW_MAX_COST_USD` overrides the per-run cap.
The investigator's shell is pinned to `NW_SANDBOX_CPUS` (default: the last four cores) at nice 10 and has the `nwlab` toolkit
(validator, simulator and a fast exploratory fitter; the live2 runs predate it). Candidates can be submitted from a workspace
file (`nw_submit_candidates` with `file`).

Inspect, compare, freeze, evaluate on the held-out run (host-only commands):

    .venv/bin/python -m nernstwork.cli compare --run <run>
    .venv/bin/python -m nernstwork.cli details --run <run> --id <candidate>
    .venv/bin/python -m nernstwork.cli profile --run <run> --ids <c1> <c2>
    .venv/bin/python -m nernstwork.cli freeze --run <run>
    .venv/bin/python -m nernstwork.cli final-eval --run <run>
    .venv/bin/python -m nernstwork.cli report --run <run> --out docs/examples/<run>.md
    .venv/bin/python -m nernstwork.cli compare-arms --runs <r1> <r2> <r3> --out docs/examples/arm_comparison.md [--final first|latest]

## 5. Design decisions (short rationale)

- **Python stays the scientific core; TypeScript only hosts Pi.** Pi's SDK is TypeScript; everything that decides a number lives
  in Python behind a JSON CLI, so Daniel can extend fitting and enumeration without touching the host.
- **One evaluator, no proposer awareness.** The fit key is (dynamics, data bytes, protocol, evaluator code); proposed starting values
  are ignored; identical structures from different proposers share one stored fit.
- **Noise model.** No replicates exist for these runs, so sigma is profiled per channel (with a floor). Daniel's max-scaled
  objective is kept as `legacy-scaled-v1` to reproduce the earlier calibration and is not used for ranking. t = 0 points are excluded.
- **Statistics stated plainly.** AICc within identical observation sets; Akaike weights labelled as relative support; adequacy
  (runs test, standardized residuals) printed next to every rank; Fisher screen plus profile likelihood for identifiability.
- **Isolation by mechanism, not prompt.** The investigator's shell runs in bubblewrap with only the run workspace (rw), the evidence
  pack and the Python runtime (ro), no network and an empty environment. Host-side read/write tools resolve symlinks against those
  roots. Sessions load no context files, skills, extensions or packages; telemetry and version checks are off.
- **Recovery.** The store, not the conversation, is authoritative. Each scientific tool call is journaled; on resume the host lists
  calls whose results were stored but never reached the session and injects the store status. Re-requests are idempotent.
- **Budgets and caps.** Candidate budgets are enforced by the backend; per-round caps and phase gates by the host; a list-price cost
  cap aborts a run at a resumable point.

## 6. Checklist

- [x] Audit repository, reproduce baseline, record versions
- [x] Backend: compile/validate, evaluator, store, enumeration, review, CLI
- [x] Tests: units/provenance, round trip, invalid/unsupported, equivalence, numerics, caching, recovery, holdout separation
- [x] Pi host: sandbox, tools, investigator, reviewer, resume, cost cap
- [x] Synthetic recovery cases; mocked integration (crash after commit, resume); live smoke test
- [x] Enumeration on Liao 50b (core + extended + post-hoc); live agent arms; comparison; held-out evaluation; example reports
- [x] Evaluator convergence-policy fix; sandbox toolkit, CPU bound, submit-from-file, typed tool schemas (with tests)
- [x] Re-scoring of the frozen arms under the corrected evaluator; a second live run per agent arm (live3, with the toolkit)

## 7. Independent code review and fixes (Oct 20)

A read-only review of the backend (separate agent, hand-traced) reported these defects; each is fixed and has a
regression test in `tests/test_investigator.py`:

- **Shared fits read in the wrong names (high).** A cached fit serves every candidate with the same dynamics, but it was
  stored in the first fitter's reaction ids, parameter order and species names. An agent candidate reusing an enumerated
  fit could have printed one step's rate constant next to another step, or crashed on a renamed unmeasured species. Fits now
  carry canonical parameter keys and species labels, and every reader translates them into its own names
  (`evaluate.translate_fit`); profiles are stored in canonical keys too.
- **Candidates with no free parameters crashed evaluation (high).**
- **Canonical identity split identical candidates** written with `1` versus `1.0` or an explicit `"fixed": false` (medium).
- **Free power-law orders made k bounds depend on proposed starting values** (medium).
- **Profile likelihood treated an unconverged refit as a likelihood rise** (narrow, overconfident intervals) and could
  write non-JSON infinities; such directions are now reported as `inconclusive_numerics` (medium).
- **Freeze** could be left half-done after a crash, could freeze without current evaluations, and ordered conclusion
  files lexically; all fixed (medium).
- **Adequacy rule:** with a profiled sigma, `|standardized residual| > 4` can almost never fire (they are bounded by
  sqrt(n)); replaced by a lag-1 autocorrelation check (medium).
- **Tie checks depended on reaction order**; `K` on a non-Langmuir step became an unused free parameter (medium/low).
- Lower-severity: reconciliation labels, numbered records written create-once with retry, evidence pack built before the
  run marker, warning when a t = 0 value disagrees with the stated initial condition, equivalent candidates sharing one
  Akaike weight, optimizer warnings carried into rankings.

Because these change the evaluator's code hash, enumeration runs started before the fixes were stopped and marked
`SUPERSEDED.json`; the reported enumeration is `liao50-enumeration-v3`.

### Incidents during the live runs (Oct 20) and fixes

- **Reviewer tool schema.** `submit_review` declared its nested fields as `Any`; the model sent `assessment` as a JSON string
  and the validator rejected 11 submissions. The reviewer's final real review passed the bundle validator unchanged once
  parsed, so it was recorded with a provenance note; the tool now has a typed schema and parses stringified objects.
  Wasted spend: about $2.3 (list price).
- **Unbounded fits.** Free power-law orders let some multistart points imply rates near 1e7 mM-N/min; single ODE solves
  crawled and 14 post-hoc fits ran for over an hour. The fitter now has deterministic budgets (RHS evaluations per solve,
  ODE solves per fit); exceeding them is a solver failure or an explicit `nonconvergence` with a note. Previously stuck fits
  finish in 12-14 s; fits that had completed reproduce bit-identically under the new code (AICc difference 0.0).
- **Host timeouts and orphans.** The host's backend call had a 1 h default; when it fired, the evaluator's worker processes
  were orphaned. Backend calls now run in their own process group (killed as a group) with a 6 h last-resort ceiling.
- **Provider connection errors.** In the no-revision arm every model call of the conclude step failed with a connection
  error and the host advanced to freeze anyway, so that arm froze without a written conclusion. The selection is a code rule
  and was unaffected; the conclusion was recorded afterwards through the same persisted session (timestamps show the
  order). The host now stops at a resumable point when a turn ends on a provider error, and Pi retries up to six times
  with backoff. The second critique run hit this twice and completed after two resumes with nothing lost.
- **Convergence policy (found by the held-out evaluation).** The fitter reported the best formally converged start even when
  most unconverged starts replicated a much lower NLL (critique arm, held out: 10 of 12 starts at NLL 85.75, reported
  167.66). The optimum is now the lowest NLL that is formally converged or replicated by at least two starts; the
  pre-registered comparison is kept unchanged and a re-scoring under the corrected evaluator is reported next to it.
- **Resume path exercised for real.** The critique arm was stopped twice and resumed from the store; the host adopted the
  stored review instead of launching a second reviewer, and injected the store status into the persisted session.

## 8. Results (Oct 20): Liao Fig. 50b (development) and Fig. 50a (held out)

Full tables: `docs/examples/arm_comparison.md` (all runs, current evaluator). Per-run reports with candidate structures,
parameters, profiles, reviews, responses, conclusions and plots: `docs/examples/liao50-*.md`. The pre-registered comparison of
the first four runs, made before the convergence-policy fix, is kept unchanged in `docs/examples/arm_comparison_preregistered.md`.
Model for the first four agent runs: `anthropic/claude-opus-5-5` (thinking high) through Pi 1.3.0; run 1 without the
sandbox toolkit, run 2 with it. On Oct 21 the same arms were run twice with `openrouter/google/gemini-4-argon` (thinking
high, toolkit on), with a byte-identical evidence pack, protocol and evaluator code (65c1ac7c107b). Two runs per arm and
model are case results, not performance estimates.

| Run | Candidates | Dev best AICc (Fig. 50b) | Held-out AICc of the frozen selection (rank / 731) | Best agent-plausible candidate on held-out (rank) | LLM cost (list), session time |
|---|---|---|---|---|---|
| Enumeration, pre-declared spaces | 654 | 204.95 (three hidden-X topologies within 0.34) | 179.17 (20) | n/a | none |
| Post-hoc enumeration over the agents' dimensions | 90 | **151.54** | **153.67 (1)** | n/a | none |
| Propose only, run 1 | 10 | 166.25 | 207.70 (121) | 168.17 (9); conclusion recorded after freeze | $2.48, 57 min |
| Propose only, run 2 | 10 | 163.43 | 193.11 (58) | same as selection | $1.34, 9 min |
| Critique and revision, run 1 | 10 (6 + 4 revisions) | 168.74 | 193.88 (58) | 165.61 (7) | $6.49 (about $2.3 lost to a host bug), 54 min |
| Critique and revision, run 2 | 10 (6 + 4 revisions) | 166.25 | 187.47 (54); 207.70 (121) | 168.17 (9) | $3.00, 18 min |
| Gemini 4 Argon, propose only, run 1 | 10 | 131.05 | 159.13 (6) | same as selection | $4.48, 80 min |
| Gemini 4 Argon, propose only, run 2 | 10 | 143.01 | 160.18 (6); 161.42 (7); 166.97 (8) | 154.25 (2) | $3.98, 87 min |
| Gemini 4 Argon, critique and revision, run 1 | 10 (6 + 4 revisions) | 143.01 | 161.42 (7); 166.97 (8) | same as selection | $4.68, 80 min |
| Gemini 4 Argon, critique and revision, run 2 | 10 (6 + 4 revisions) | 154.23 | 172.72 (16) | 154.77 (2) | $3.89, 69 min |

The held-out reference set is every member of every declared enumeration space (pre-declared and post-hoc) refit on Fig. 50a:
731 of 733 structures fit (2 do not converge). The frozen selection is a code rule (development AICc within 2 of the best),
fixed before the held-out run was read.

What the measurements say:

1. **Daniel's model class is insufficient for Fig. 50b.** Its best member (the W2 structure, AICc 210.05) and every other
   enumerated candidate show systematic residuals. Adding a hidden intermediate (about 25% of N) gains about 5 AICc but
   leaves three different topologies indistinguishable, each with individually identifiable parameters: identifiable
   parameters did not mean an identified mechanism.
2. **The agents widened the hypothesis space, and did so reproducibly.** All four runs left the declared spaces with the same
   ideas: a direct NO3 -> NH3 route next to the nitrite route (36 of 40 candidates), an apparent nitrate order for the slowdown,
   a nitrogen loss with its own shut-off, and NO2- + NH4+ coupling to N2 (proposed in every run). Eight structures were proposed
   identically by two or more independent runs. Development bests of the four runs lie within 5.3 AICc of each other
   (163.4-168.7), 36-42 AICc better than the pre-declared enumeration.
3. **The agents' selections did not transfer, in all four runs.** Their frozen selections ranked 54th to 121st of 731 on the
   held-out run, behind the pre-declared enumeration's choice (20th). Systematically enumerating the agents' new dimensions
   (post-hoc, 90 candidates) gave the best structure on both runs. In this case the agent was useful as a source of
   hypotheses, and systematic search was needed to choose among them.
4. **The agents' own plausible sets often held a structure that transfers; the development ranking did not pick it out.**
   In three of four runs the investigator's concluded plausible set (three or four candidates) contained an NO2-/NH4+
   coupling structure ranked 7th or 9th on the held-out run, below the development best and outside the code-rule
   selection. The fourth run (propose only, run 2) named a single candidate (58th).
5. **Critique changed the analysis, not the selection.** In both critique runs the fresh reviewer raised substantive,
   evidence-linked points, and the investigator answered every finding with analyses and four revised candidates. The
   development best did not change: critique run 2's top selection is the structure propose-only run 1 selected.
6. **Scientific status of Fig. 50.** No candidate is adequate in any run. Supported across runs: a direct NO3 -> NH3 route
   alongside the nitrite route; a nitrogen loss of about 25 mM-N on Fig. 50b that starts after a delay and stops, better
   described by a loss branch with its own shut-off than by catalyst deactivation shared with all steps; a slowdown better
   described by an apparent nitrate order (about 1.4-2.2) than by single-exponential catalyst deactivation alone. In a single
   batch run that order is a lumped stand-in (pH drift, surface change), confounded with time. Not resolved: what the lost
   nitrogen is and what stops the loss. The second reviewer argued that both leading explanations are physically doubtful
   (NH4+ leaving the catholyte against migration through a cation-exchange membrane; homogeneous NH4+/NO2- comproportionation
   at the fitted rate at neutral to alkaline pH), and named two unconsidered ones: anion crossover to the anolyte, and
   nitrite interfering with the UV nitrate assay. The runs' recommended measurements agree: an N balance outside the
   catholyte (headspace N2/N2O, acid trap, anolyte NH4+ and NO3-, membrane type), nitrite-only and NH4+-spike runs, and
   pH logging.
7. **Sandbox toolkit.** With the exploratory toolkit, the second runs used fewer tokens and less session time
   (propose only: $1.34 and 9 min against $2.48 and 57 min) with development results in the same range.
8. **Numerical caveats found by running it.** (a) The original convergence policy reported the best formally converged
   start even when many unconverged starts replicated a much lower NLL. It distorted 2 of the first critique run's 4
   held-out fits (pre-registered rank 701 for its selection; 58 after the fix) and left 25 reference-set fits without a
   result. The fixed policy
   accepts the lowest NLL that is converged or replicated by two starts; the pre-registered table is kept as made. (b) The
   multistart can miss the optimum of a larger model: in critique run 2, a candidate that contains the best candidate as a
   special case (one extra rate constant at its lower bound) fitted 3.8 NLL worse. The investigator noticed and left it
   unresolved. Starting larger models from the fits of the models they contain would close this gap.

9. **Gemini 4 Argon (Oct 21) chose much better than Opus 5.5 on this case.** Its development bests (131.0-154.2) beat
   every Opus run (163.4-168.7) and the post-hoc enumeration (151.5), and its rule-selected candidates rank 6th to 16th
   of 731 on the held-out run (Opus: 54th to 121st); two of its agent-plausible candidates rank 2nd. The behaviour
   differed: Gemini ran dozens of exploratory fits in the sandbox toolkit before submitting (89-116 tool calls per run),
   in effect searching the space itself, and took 69-87 min and $3.9-4.7 per run. Through OpenRouter its long reasoning
   turns were repeatedly dropped ("upstream idle timeout"), so every Gemini run needed host restarts (up to 15) that resumed
   from the store; the thinking level was not lowered. With one case and two runs per arm this is a lead, not a ranking of
   models.

## 9. Limitations (current)

- One development run and one held-out run. The held-out test is structure transfer to another catalyst with refit
  parameters, not prediction of new conditions. Fig. 49 (Ag-MoS2, 3 h, closure about 1.0) is a different regime and unused.
- No replicate or assay-error information exists for these runs, so sigma is estimated from the misfit itself. When
  residuals cluster (adequacy "poor"), AICc differences are optimistic. Akaike weights are relative support within the set.
- The Fisher screen is local; profile likelihood is computed on request for selected candidates, not for every candidate.
  Structure-level ambiguity (which network) is reported through delta-AICc bands and observational-equivalence groups, not
  through a posterior over structures.
- `nw_discriminate` gives point predictions at the development MLE; it does not propagate parameter uncertainty and is not an
  expected-information-gain design optimizer.
- Two live runs per agent arm: case results for this model and prompt, not estimates of average performance.
- Contamination: retrospective analysis. The proposer's pretraining may include general NO3RR mechanism knowledge; the Liao
  paper reports no kinetic network, so it cannot leak a fitted answer, but the held-out run's 48 h endpoint is stated in its
  text (blocked for the fetch tool, withheld from the evidence pack).
- Isolation covers the investigator's own tools. The Python CLI does not authenticate callers; the boundary is that the
  sandbox cannot reach the repository, the held-out files, the CLI or the cache, and host-only commands are not exposed as tools.
- The Liao Source Data workbook is not in the repository, so `scripts/build_real_datasets.py` cannot be rerun here.

## 10. Questions for Daniel

1. Which dataset do you treat as "our model system"? This work assumed Liao Fig. 50b (development) and Fig. 50a (held out).
2. Catalyst assignment for Figs. 50a/50b: the caption says (a) W-MoS2, (b) MoS2, but the main text lists residual nitrate
   4.64 / 11.78 mM "for W-MoS2 and MoS2", which matches 50b / 50a respectively (claim L3). Which is right?
3. Is the H-cell membrane and anolyte known (claim L8)? Nitrate or ammonium crossover is observationally equivalent to N2
   formation on these channels; anolyte or headspace measurements would separate them.
4. Are there replicate runs or assay error estimates for the Liao concentrations? They would replace profiled sigma.
5. Should the declared enumeration space grow (separate catalyst-state constants per pathway, product inhibition, pH-drift
   state)? Anything the agents propose outside the space is reported separately so its effect can be judged.
6. W5's second-order NO2- -> N2 step declares k bounds [1e-6, 10] mM^-1 min^-1; the protocol's second-order bounds are
   [1e-10, 1], and the evaluator rejects declared bounds outside the protocol's. Narrow the world's bounds, or widen the
   protocol? (The simulator itself reproduces W5 exactly; the bounds matter only when W5's structure is fitted.)
