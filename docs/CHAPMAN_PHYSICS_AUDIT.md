# Chapman physical diagnostics

Snapshot: 2026-10-22T11:54:14.348785+00:00.

This audit resimulates frozen fitted parameters. It does not change the engine, fit results, candidate selection or ranks. Missing files are unfinished coverage, not failed models. Negative amounts and declared-element drift are separate checks.

The core evaluates rates with `max(amount, 0)` but does not clip the integrated state. A reaction that consumes a species with an omitted or zero rate order can therefore continue below zero. The static check examines net consumption, so unchanged catalysts are not counted as depleted reactants.

| Candidate inventory | Dynamics representatives | Li + Ti declared | Ti only | Unprotected consumption | Free order can reach zero |
|---|---:|---:|---:|---:|---:|
| Historical union | 904 | 459 | 445 | 0 | 1 |
| Fresh proposals | 274 | 137 | 137 | 0 | 0 |

Counts refer to the stored representative chemistry, not every chemistry alias sharing its dynamics. Historical and fresh sets overlap and must not be added as unique candidates.

**Ti-only models deliberately do not impose a lithium balance.** They remain valid predictive baselines within that assumption, including models with an implicit unlimited lithium supply. Their fit cannot establish lithium conservation, lithium depletion or the intermediate's lithium stoichiometry. This audit never rejects them solely for lacking lithium conservation and does not infer missing Li compositions from species names.

Each fitted result uses its current 700/725/750 °C observations and starting amounts, including fitted initial amounts through the unchanged adapter. Cached unobserved trajectories are not used. The grid covers 0–9.5 min every 0.01 min plus all observed times. LSODA uses rtol=1e-8, atol=1e-10, at most 20,000 RHS evaluations and a 30-second timeout per integration; the audit runs on one CPU. No alternate solver recovery is silently applied.

| Result scenario / mode | Files in snapshot | Fitted | All 3 simulations completed | Any species < −1e−6 | Declared element drift > 1e−6 | Incomplete / error |
|---|---:|---:|---:|---:|---:|---:|
| fig2_lower__fixed | 206 | 206 | 206 | 1 | 0 | 0 |
| fig2_lower__shared | 11 | 11 | 11 | 0 | 0 | 0 |
| fig2_nominal__fixed | 874 | 865 | 863 | 0 | 0 | 2 |

Saved result files at snapshot start: 1091; audited in this invocation: 1091. Successful integrations: 3243; failed integrations: 3.

Amount thresholds are formula units per mol Ti; elemental drift is atoms per mol Ti. Largest sampled declared-element drift: 3.262945469373335e-12. The count of negative trajectories includes numerical overshoot; it is not by itself evidence that a rate law is structurally invalid.

| Flagged result | Temperature | Diagnostic |
|---|---:|---|
| `c233204ed62c` / fig2_nominal / fixed | 725.0 | SolverFailure: integration failed: Unexpected istate in LSODA. |
| `c233204ed62c` / fig2_nominal / fixed | 750.0 | SolverFailure: integration failed: Unexpected istate in LSODA. |
| `9dd6e2f275ac` / fig2_nominal / fixed | 750.0 | SolverFailure: right-hand-side evaluation budget (20000) exceeded |
| `c5ff5f494c54` / fig2_lower / fixed | 700.0 | Li2TiO3 minimum -3.8159e-06 at 2.03 min; sampled negative-amount flag |

The historical candidate with a free anatase order has these fitted values (zero is allowed by its bounds, not assumed): `b0013b1b5a7d` / fig2_nominal / fixed: 0.703453.

| Frozen selection / scenario / mode | Declared balance | Simulation status | Lowest sampled amount | Largest declared-element drift |
|---|---|---|---:|---:|
| Original Opus1 / fig2_nominal / fixed | Ti-only | all_simulated | -2.223500446075786e-11 | 1.7763568394002505e-15 |
| Original Opus1 / fig2_lower / shared | Ti-only | all_simulated | -2.2235018169008588e-11 | 1.3322676295501878e-15 |
| Original baseline / fig2_lower / fixed | Ti-only | all_simulated | -4.318648165882823e-12 | 1.5543122344752192e-15 |
| Original baseline / fig2_nominal / fixed | Ti-only | all_simulated | -4.318648165882823e-12 | 1.5543122344752192e-15 |
| Original Opus1 / fig2_lower / fixed | Ti-only | all_simulated | -8.300500882118869e-08 | 6.306066779870889e-14 |

The observation map still sums nominal phase amounts. The digitized weight fractions were converted with fixed nominal formula masses and normalized Ti closure. Changing Li content in a model does not recompute that conversion or account for amorphous material. A nonnegative, element-balanced trajectory therefore does not validate the assumed phase composition, observation mapping, thermal history, or reaction mechanism. Sampling cannot prove positivity between grid points or outside this time/temperature range. A solver failure leaves the physical check unresolved.

Full result identities, per-species minima, current initial amounts, declared-element drift and failures are in [the local audit snapshot](../data/derived/chapman_li_sensitivity/physics_audit/summary.json). For the observation-map and lithium-budget limits, see [the literature review](LITERATURE_REVIEW_OCT22.md).

Refresh without fitting:

```bash
.venv/bin/python scripts/audit_chapman_physics.py
```
