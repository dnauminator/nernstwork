# Chapman lithium sensitivity, 22 October 2026

This is a retrospective sensitivity campaign requested by Daniel Naumov and Jarrod Barnes. The existing 750 C results have been inspected. No result here is a fresh blind validation or proof of a reaction mechanism.

## Decision and controls fixed before new fits

Determine whether finite lithium supply changes the preferred reaction network, fitted activation energies, or temperature-transfer ranking enough to change the conclusions or the next experiment. Preserve the original datasets, candidate spaces, fit cache and runs.

1. Primary comparison uses the original Fig. 2 observations and time grid. Replace only Li2CO3 in the initial state from 0.4 to 0.28, 0.30 and 0.36 mol per mol Ti at 700, 725 and 750 C. Fit 700 + 725 C jointly and predict 750 C with frozen kinetic parameters. The three lower values are effective initial-condition hypotheses inferred from an early frame, not independent measurements of the weighed starting mixture.
2. Repeat the declared baseline and all saved Opus1 proposals. Run one fresh Opus proposer with the corrected development inputs, the same budgets and isolation. Jarrod authorized up to $10 for this one run. Use a $6 host stop threshold to leave headroom for an in-flight model response. No other paid runs are authorized.
3. Audit the finite union of the original baseline, eight saved AI spaces and standalone submissions. Keep unchanged valid candidates as the comparable set; report previously rejected candidates repaired only in their representation as a separate coverage control. Deduplicate by validated dynamics hash, not a reused space ID. Completeness means this declared finite space, not all possible chemistry.
4. Change extraction independently. Use supplement Fig. S1 on the identical 0.3–9.5 min grid under both nominal and lower initial lithium. Do not combine earlier points with the primary lithium comparison. If early-time sensitivity is informative, include only points at or after 0.2 min and label the remaining heating/time-origin approximation. The SI documents heating over the first ten seconds.
5. If interpretation, activation energies or rankings change, fit a shared effective initial Li2CO3 amount within 0.25–0.4 on development data. Count it as an additional parameter. Transfer that fitted value unchanged to 750 C. A secondary fit may estimate separate development initial amounts; any prediction at 750 C then explicitly conditions on its externally specified amount and is not a fitted initial-state prediction. Never estimate a held-out initial amount from held-out phase observations.

## Assessment

Use the existing synthesis-mle-v1 protocol unchanged for comparable fixed-initial-state fits. Rank development fits by AICc within identical observations. Report fit failures and inadequate residuals separately from chemical evidence. Compare 750 C using the original reference-best common per-channel noise scales, held fixed across campaigns, plus unweighted RMSE. A fitted candidate's own broad noise must not improve its predictive rank. Report both the development-selected candidate and the best retrospective prediction; do not relabel the latter as a prospective selection.

Track the same candidate across conditions as well as changes in the winning candidate. A numerical change in an activation energy at a bound or in an unidentifiable direction is not a resolved physical change. Profile consequential initial-state and activation-energy parameters where feasible. Check optimizer replication and revisit numerical failures before interpreting them.

Ti normalization couples errors across the four phase fractions. The unchanged comparison likelihood treats phase errors independently, so its profile ranges are conditional calculations, not calibrated 95% measurement uncertainty. Counting three independent composition coordinates does not by itself provide a corrected likelihood or AICc.

The Ti-only baseline should be exactly insensitive to carbonate because its rate equations do not consume it. Verify this directly. Lithium-conserving candidates can respond strongly. Lower supply cannot by itself resolve the published nominal lithium imbalance. Nominal phase molar masses, crystalline normalization, initial unmeasured material, initial rutile and heating remain possible observation/model errors.

## Follow-up selection rule

The primary fixed-input comparison covers all 904 distinct repaired-union dynamics, with the original 860 identified separately. Before the primary run finishes, the initial-amount follow-up includes the ten best original development fits that depend on carbonate, every original development-selected AI candidate, and each original AI run's best retrospective predictor. Add the fresh AI selection and every newly competitive development candidate within four AICc units of the best carbonate-dependent fit. Fit shared initial amount first; fit separate development amounts and profile parameters for candidates whose conclusions depend on that distinction. Carbonate-independent candidates have no information about the initial amount and do not receive a meaningless extra fitted parameter.

**Deviation (Oct 22).** The primary fixed-input grid at the lower carbonate amounts (fig2_lower × 904) was stopped before completion and will not be finished. Its purpose was to rank the union under the lower amounts, and the shared-initial-amount follow-up showed that the data reject them: every shortlisted carbonate-dependent model fits 0.39–0.40 against the 0.40 cap and recovers its nominal-lithium result. The fig2_nominal grid, the baseline at lower amounts, the initial-amount follow-ups, the fresh Opus run and the S1 comparisons are unaffected.

For the extraction control, include the entire declared baseline and original Opus1 candidate set, plus those follow-up candidates and any fresh AI selection. This is a targeted extraction sensitivity, not a full Cartesian product of every network and every nuisance assumption. Record the exact scheduled candidate list and completion count for each comparison.

Carbonate-independent fits can be reused only within an extraction after the runner verifies identical observations, other initial amounts, conditions and observed trajectories under both lithium inputs. S1 lower therefore reuses successful S1 nominal fits for those candidates; it never substitutes a Fig. 2 fit for an S1 fit. The source fit key and data hash remain recorded, without claiming a second optimization or creating a misleading changed-data cache entry.

## Execution recovery

On 22 October the fresh AI run's evaluation pool stalled after each of its four workers completed 20 fits. All 80 attempts were committed and no fit worker remained alive. This matches the documented [Python worker-recycling deadlock](https://github.com/python/cpython/issues/115634). The orchestration now closes and recreates a spawn pool between bounded batches, instead of using `max_tasks_per_child`. A real-process regression check crosses the old recycling threshold. The same run resumes from its saved fits and proposer session; candidate definitions, data, fitting protocol and numerical engine hash are unchanged. This is an execution repair, not a second paid AI rerun or a change to the scientific objective.

## Provenance and limits

All derived inputs and numerical results live under ignored data/derived/chapman_li_sensitivity or investigations, with source hashes and reproducible scripts. Adapter fits carry the adapter source hash in their identity. Original cache keys remain valid only with identical data, protocol and evaluator code. No raw publisher PDFs or unlicensed ARROWS3 tables are published.

Keep actual measurements, digitized curves, fitted predictions, synthetic identifiability demonstrations and proposed future experiments distinct. LTOPO endpoint records and in-situ literature are assessed separately. Kosuge integrated conversion laws require a mathematically appropriate adapter and observation model before they can be interpreted as network rates.
