# Chapman history and numerical audit, 22 October 2026

The lithium campaign is a retrospective check of an existing result. The 750 C
observations and earlier predictions were already inspected. Neither rerunning
the saved proposals nor using another figure from the same experiment creates a
new blind validation.

## Evidence examined

The historical audit parsed all 7,475 JSONL records in the local Claude session
`~/.claude/projects/-home-jarrodbarnes-nernstwork/2f0ca813-164d-42c1-b20e-3085343a5780.jsonl`,
searched its messages and tool results, and inspected the relevant reports and
subagent traces. In that session's `subagents/` directory, the principal traces
were `agent-a1524f31794339ca3.jsonl` (backend audit),
`agent-a33b3a170f877959e.jsonl` (Chapman conversion),
`agent-a35ec3357646340bf.jsonl` (figure verification),
`agent-a40c75cfb6bcf2f89.jsonl` (methods), and
`agent-af330774a81d03369.jsonl` (synthesis literature).
Historical claims were checked against current code, saved submissions, frozen
choices, final predictions and content-addressed fit results.

Useful transcript locations are lines 1314 (backend audit), 6205 (synthesis
implementation and experiment design), 6388–6393 (scoring revision), 6444
(independent figure check), 6591 and 6833–6845 (reported OOM and recovery), and
7469 (final report at 00:34 UTC on 22 October). Local transcript line numbers
refer to the audited file, including duplicated context after resumptions.

## Decisions that matter for this campaign

- The original primary score changed after the baseline's 750 C predictions
  were inspected, before final scoring of the AI arms. The first likelihood
  evaluation remains on disk. The current comparison uses squared prediction
  error weighted by a common development-derived noise scale. A model's own
  broad fitted noise must not improve its primary predictive rank. This history
  limits any claim that the original comparison was fully preregistered.
- Historical cache correctness fixes cover canonical parameter/species
  translation, numeric normalization and fixed/free ties. Freeze requires
  current completed fits. Unconverged likelihood-profile points are not accepted
  as evidence of a confidence bound. A replicated optimizer minimum may be
  accepted despite individual starts exhausting their stopping budget.
- After the reported OOM, recovery reused committed fits and resumed incomplete
  work. The historical repair recycled each investigation worker after 20 tasks.
  On 22 October, that executor stopped progressing after all four workers had
  completed 20 tasks and exited. The current execution repair uses explicit
  spawned pool batches instead. It changes scheduling only; the numerical
  engine hash is unchanged, and the same AI run resumed from its 80 committed
  fits. See the execution-repair record in
  [the campaign protocol](CHAPMAN_LI_SENSITIVITY_PROTOCOL.md). A partial run or
  failed prediction is not evidence against its chemistry; fit status and
  prediction status must remain separate.
- Multistart seeds include the development file hash. Changing only initial
  carbonate therefore also changes the ordinary seed. The isolated numerical
  controls retain the original seed **and canonical parameter order**, since
  an equivalent candidate can otherwise reorder the random starting values.
- Original held-out simulation uses LSODA at `rtol=1e-8`, `atol=1e-10`. Fitting
  uses the unchanged protocol's `1e-7`, `1e-9`. The independent score sidecars
  restore the original held-out settings without changing a fitted parameter.

The 22 October lower-carbonate fit exposed a consequential optimizer limitation
in the original Opus1 selected model. The official run returned a formally
converged NLL of -106.882, while unfinished starts reached about -393.79. The
best two unfinished values differed by 0.0118, just outside the 0.01 replication
tolerance. Its stored warning correctly says the reported optimum may not be
global. In this fallback branch, `fit.py` counts all better unfinished starts as
replicates of the returned fit, so the reported count of six is misleading.
Do not interpret this returned fit's activation-energy shifts as chemistry.
The core is preserved during the campaign; extended-budget numerical rescues
are stored separately, with per-start convergence and absolute replication
differences checked directly.

That isolated rescue subsequently converged from all three requested starts
(the nominal fitted parameters and regenerated primary starts 4 and 0), agreeing
in NLL within 3.1e-10. Its NLL is -393.83735614 and AICc -746.82364845. The
rescued R1/R2/R4 activation energies are 222.19/301.35/230.06 kJ/mol, so the
dramatic shifts in the original returned result were numerical artifacts.
Held-out RMSE is 0.05092 and residual adequacy remains poor. This establishes
optimizer repeatability for this candidate, not physical mechanism validity.

The rescued lower-carbonate activation-energy profiles initially timed out
when each constrained fit reset its noise scales to the generic initializer.
Separate 30- and 120-second-per-point attempts remain on disk as numerically
inconclusive. A source-hashed diagnostic initialized those scales at the rescued
fit, while retaining the same objective, bounds, ODE settings and subsequent
noise updates. All 26 constrained fits then converged in 72 seconds total;
independently recomputed NLLs matched exactly. Approximate conditional 95%
profile ranges are R1: 138–346, R2: 285–316 and R4: 219–240 kJ/mol. These
overlap the nominal/shared ranges and remain conditional on a model with poor
residuals. Failed profile endpoints are never confidence bounds. The successful
artifact is `profiles/fig2_lower__fixed_rescue/` under the campaign output,
with identity prefix `2f030ae0747e` and per-point validation records.

An independent stoichiometric check explains part of the lower-data mismatch:
only R1 creates Li2TiO3, and `Li2CO3 + 0.8*Li2TiO3` cannot increase. Thus the
initial amounts 0.28 and 0.30 cap the intermediate at 0.35 and 0.375, below
the observed peaks 0.46943 and 0.48610. This is a structural limit of this
submitted network, independent of rate fitting. The network conserves Ti only;
its effective carbonate certificate does not validate elemental Li balance or
measure the true starting composition. Exact matrices, source hashes and
observed-peak checks are in `numerics/opus1_carbonate_feasibility.json`.

## Finite candidate coverage

`scripts/build_chapman_sensitivity_inventory.py` reproduces the baseline, eight
saved proposed spaces and standalone proposals: 1,108 source records. The
originally valid union contains 860 unique dynamics. Repairing 92 rejected
members produces 904 unique dynamics: 72 need invalid optional Li2O metadata
removed or corrected, and 20 refer to an optional species absent from their
enumerated observation map. Reactions, stoichiometry and rate laws are preserved.
The 44 added dynamics are a separate coverage repair, not part of the original
comparable set. Source paths and hashes are retained because space IDs repeat.

The original 860 exact cache entries contain 843 fitted and 17 nonconverged
results. Of the 860, 174 cannot respond to carbonate in their measured outputs;
these include every baseline member. Reuse for changed initial carbonate is
labelled as an invariant-objective control, with direct trajectory checks. It
does not create a counterfeit changed-data entry in the official cache.

## Reproduction and interpretation

All campaign artifacts are under ignored `data/derived/chapman_li_sensitivity/`.
The inventory, `source_records.json`, `repair_log.json` and
`historical_runtime.json` record coverage, repairs and cache provenance.
`scripts/check_chapman_sensitivity_numerics.py` writes independent results to
`scores/<scenario>__<mode>/<dynamics_hash>.json`, retaining input-result and score
source hashes. It records each solver attempt. A fallback must agree with a
second tighter or different integration; unresolved disagreement is excluded
from rankings. Each prediction attempt has a 30-second wall guard, reported in
its record, to keep a pathological integration from blocking the finite audit.

`--plan-repeats` exports the two original-seed controls. Explicit
`--run-repeat baseline_selected` or `--run-repeat opus1_selected` executes one
serially under `numerics/optimizer_repeats/`, outside the official fit cache and
primary rankings. Shared-initial-amount scores additionally report a conditional
prediction with the same fitted kinetics and external 750 C carbonate of 0.36;
the primary shared prediction transfers its fitted amount unchanged.

Fig. S1 and Fig. 2 describe the same physical experiment. Extraction, heating,
normalization and effective initial carbonate remain separate uncertainties.
Better fit or transfer within this finite model family does not establish a
reaction mechanism or validate a proposed next experiment.
