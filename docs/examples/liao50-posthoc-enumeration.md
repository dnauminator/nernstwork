# Investigation report: liao50-posthoc-enumeration

- Investigation: `liao50`; arm: `enumeration`; phase: `final_evaluated`
- Protocol: `mle-profiled-v1` (sha256 `9d2cfcb0a1255b8c`); manifest sha256 `9f1f264187f050af`; evaluator code sha256 `04da1f3af06b6660` ({'python': '3.12.13', 'numpy': '2.5.4', 'scipy': '1.18.1'})
- Development data: `liao2025_mos2_suppfig50b` (sha256 `c291be31813c41e1`, source_data); 51 observations (NO3: t=0 point treated as initial condition, not as an observation; NO2: t=0 point treated as initial condition, not as an observation; NH3: t=0 point treated as initial condition, not as an observation; temperature not reported; 25.0 C assumed (matters only for potential dependence))

## Question
Which reaction networks and rate laws are supported by the 48 h H-cell nitrate-reduction time courses of Liao et al. 2025 (MoS2-family catalysts, -0.6 V vs RHE), what do the data leave ambiguous (in particular where the missing nitrogen goes and why the rates slow down), and which feasible measurement would best separate the surviving explanations?

## System boundary
Catholyte of an H-cell at fixed potential. Measured: NO3-, NO2- and NH4+/NH3 (lumped as NH3) in mM-N. Not measured: gas phase (N2, N2O, NH3 escape), anolyte (crossover), adsorbed or hidden species, pH, charge. Any nitrogen that leaves the measured channels must be represented by an explicit model species (an unmeasured product, a hidden intermediate, or a reservoir for transport out of the catholyte); the model as a whole must conserve N.

## Evidence status
- Partition: Complete experimental runs are reserved. Supp. Fig. 50a (other catalyst, same conditions and sampling) is the final held-out run; it is not read by any development-phase command, tool or evidence file. The final evaluation tests structure transfer: frozen candidate structures are refit on the held-out run with the same protocol (catalysts differ, so parameters are not transferred).
- Contamination: Retrospective analysis with literature-informed priors, not blind discovery: the proposer sees the development run, its derived N-closure series and a curated metadata note, and its pretraining may include general NO3RR mechanism knowledge.

## Ranked candidates (development data, computed in code)

Delta aicc <= 2.0: not distinguished by these data; <= 4.0: still supported. Akaike weights are relative support within this candidate set (one weight per distinct dynamics) under the stated noise model, not probabilities that a mechanism is true. Residual correlation from misspecification makes these differences optimistic.

| candidate | name | source | v | k | AICc | dAICc | weight | band | adequacy | RMSE NH3 | RMSE NO2 | RMSE NO3 | unobserved N end | in declared space | flags |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C7a268d59de | enum-fff2762723 | enumerator | 1 | 11 | 151.54 | 0.00 | 0.834 | indistinguishable_from_best | poor | 1.65 | 0.333 | 0.951 | 25.6 | liao-posthoc-v1 | R5: catalyst-state time modulation on a non-electrochemical step (electrons = 0), e.g. crossover or volatilization would not deactivate with the catalyst |
| Cf1c6fa1e64 | enum-130814dffa | enumerator | 1 | 12 | 154.98 | 3.44 | 0.149 | supported | poor | 1.65 | 0.333 | 0.951 | 25.6 | liao-posthoc-v1 | R5.k at a protocol bound (1e-07); R6: catalyst-state time modulation on a non-electrochemical step (electrons = 0), e.g. crossover or volatilization would not deactivate with the catalyst |
| Ce9ce065acc | enum-b3539f5c4f | enumerator | 1 | 10 | 161.01 | 9.47 | 0.007 | less_supported | poor | 1.83 | 0.347 | 1.2 | 25.5 | liao-posthoc-v1 | R5: catalyst-state time modulation on a non-electrochemical step (electrons = 0), e.g. crossover or volatilization would not deactivate with the catalyst |
| C73b758a2c4 | enum-c34ba4e7c1 | enumerator | 1 | 11 | 161.58 | 10.03 | 0.006 | less_supported | poor | 2.01 | 0.374 | 0.931 | 25.5 | liao-posthoc-v1 |  |
| Ca26e106288 | enum-291463a506 | enumerator | 1 | 11 | 164.29 | 12.75 | 0.001 | less_supported | poor | 1.82 | 0.344 | 1.22 | 25.5 | liao-posthoc-v1 | R6: catalyst-state time modulation on a non-electrochemical step (electrons = 0), e.g. crossover or volatilization would not deactivate with the catalyst |
| C225118e990 | enum-4c3f107c56 | enumerator | 1 | 10 | 164.68 | 13.13 | 0.001 | less_supported | poor | 1.97 | 0.459 | 0.936 | 26.3 | liao-posthoc-v1 | R4: catalyst-state time modulation on a non-electrochemical step (electrons = 0), e.g. crossover or volatilization would not deactivate with the catalyst |
| Cfc68f6529e | enum-d2bddbe3d3 | enumerator | 1 | 10 | 167.29 | 15.74 | 0.000 | less_supported | poor | 2.04 | 0.476 | 0.941 | 26 | liao-posthoc-v1 |  |
| C4078639df3 | enum-e659047796 | enumerator | 1 | 11 | 168.03 | 16.49 | 0.000 | less_supported | poor | 2 | 0.454 | 0.932 | 26.3 | liao-posthoc-v1 | R5: catalyst-state time modulation on a non-electrochemical step (electrons = 0), e.g. crossover or volatilization would not deactivate with the catalyst |
| Ce44565618a | enum-3a0a4e3c13 | enumerator | 1 | 10 | 168.27 | 16.73 | 0.000 | less_supported | poor | 1.75 | 0.521 | 1.04 | 25.6 | liao-posthoc-v1 | R4: catalyst-state time modulation on a non-electrochemical step (electrons = 0), e.g. crossover or volatilization would not deactivate with the catalyst |
| Cea99d470ed | enum-4eb44fd892 | enumerator | 1 | 11 | 171.54 | 20.00 | 0.000 | less_supported | poor | 1.75 | 0.521 | 1.04 | 25.6 | liao-posthoc-v1 | R4.k at a protocol bound (1e-07); R5: catalyst-state time modulation on a non-electrochemical step (electrons = 0), e.g. crossover or volatilization would not deactivate with the catalyst |
| Cd12d5d02ae | enum-cc7b4b492e | enumerator | 1 | 9 | 176.41 | 24.87 | 0.000 | less_supported | poor | 2.3 | 0.432 | 1.32 | 26.6 | liao-posthoc-v1 | R4: catalyst-state time modulation on a non-electrochemical step (electrons = 0), e.g. crossover or volatilization would not deactivate with the catalyst |
| Cbb1f9f0f1c | enum-97d5e9de00 | enumerator | 1 | 10 | 176.90 | 25.36 | 0.000 | less_supported | poor | 2.37 | 0.521 | 0.986 | 26 | liao-posthoc-v1 |  |
| C25007bcd00 | enum-8f3dff9344 | enumerator | 1 | 10 | 177.03 | 25.48 | 0.000 | less_supported | poor | 2.3 | 0.424 | 1.25 | 25.2 | liao-posthoc-v1 |  |
| Ca055a4f106 | enum-ea74ce3cb6 | enumerator | 1 | 10 | 179.60 | 28.06 | 0.000 | less_supported | poor | 2.33 | 0.426 | 1.33 | 26.6 | liao-posthoc-v1 | R5: catalyst-state time modulation on a non-electrochemical step (electrons = 0), e.g. crossover or volatilization would not deactivate with the catalyst |
| C4c5ed52b1e | enum-b42bf0930a | enumerator | 1 | 9 | 181.76 | 30.22 | 0.000 | less_supported | poor | 1.84 | 0.443 | 1.89 | 25.7 | liao-posthoc-v1 | R4: catalyst-state time modulation on a non-electrochemical step (electrons = 0), e.g. crossover or volatilization would not deactivate with the catalyst |
| C8db3ba6292 | enum-b5b17374f1 | enumerator | 1 | 9 | 184.56 | 33.01 | 0.000 | less_supported | poor | 2.86 | 0.593 | 0.985 | 26.5 | liao-posthoc-v1 | R3: catalyst-state time modulation on a non-electrochemical step (electrons = 0), e.g. crossover or volatilization would not deactivate with the catalyst |
| C825c48059a | enum-0664916a97 | enumerator | 1 | 10 | 184.87 | 33.33 | 0.000 | less_supported | poor | 1.84 | 0.443 | 1.89 | 25.7 | liao-posthoc-v1 | R4.k at a protocol bound (1e-07); R5: catalyst-state time modulation on a non-electrochemical step (electrons = 0), e.g. crossover or volatilization would not deactivate with the catalyst |
| Cdabb793668 | enum-043406897c | enumerator | 1 | 9 | 185.02 | 33.47 | 0.000 | less_supported | poor | 2.62 | 0.433 | 1.49 | 26.5 | liao-posthoc-v1 |  |
| Caeb0743439 | enum-6fb738f43e | enumerator | 1 | 10 | 185.07 | 33.52 | 0.000 | less_supported | poor | 2 | 0.803 | 0.96 | 24.9 | liao-posthoc-v1 |  |
| C8c303fb0a5 | enum-3051374df9 | enumerator | 1 | 9 | 186.85 | 35.30 | 0.000 | less_supported | poor | 1.96 | 0.949 | 0.957 | 24.8 | liao-posthoc-v1 |  |
| C43aaf9df62 | enum-8822febd69 | enumerator | 1 | 10 | 187.67 | 36.12 | 0.000 | less_supported | poor | 2.86 | 0.593 | 0.985 | 26.5 | liao-posthoc-v1 | R3.k at a protocol bound (1e-07); R4: catalyst-state time modulation on a non-electrochemical step (electrons = 0), e.g. crossover or volatilization would not deactivate with the catalyst |
| C4b62026750 | enum-42aeea4aac | enumerator | 1 | 9 | 189.42 | 37.88 | 0.000 | less_supported | poor | 2.56 | 0.785 | 0.958 | 28 | liao-posthoc-v1 |  |
| C21ef2d151b | enum-10d63a660e | enumerator | 1 | 9 | 189.54 | 38.00 | 0.000 | less_supported | poor | 2.53 | 0.794 | 0.961 | 23.6 | liao-posthoc-v1 |  |
| C5bf03f4934 | enum-db1e19b92f | enumerator | 1 | 9 | 190.92 | 39.38 | 0.000 | less_supported | poor | 2.91 | 0.709 | 0.976 | 26.9 | liao-posthoc-v1 |  |
| Cafcf343bb7 | enum-5ca2428ba4 | enumerator | 1 | 10 | 192.53 | 40.99 | 0.000 | less_supported | poor | 2.56 | 0.785 | 0.958 | 28 | liao-posthoc-v1 | R5.k at a protocol bound (1e-10) |

65 lower-ranked fitted candidates omitted here; `python -m nernstwork.cli compare --run liao50-posthoc-enumeration` lists all of them.

## Top candidates in detail

### C7a268d59de `enum-fff2762723` (source enumerator, version 1)

Rationale (proposer): enumerated: NO3>NO2,NO3>NH3,NO3>SINK,NO2>NH3,NH3+NO2>2SINK | power_NO3_shared_order | split_deactivation

    R1: NO3 -> NO2 [power_law, deactivation(tau tie=tau_cat); e=2.0]; R1.k=0.000114 (95% Wald 4.54e-05-0.000288, moderately_determined)
    R2: NO3 -> NH3 [power_law, deactivation(tau tie=tau_cat); e=8.0]; R2.k=0.000566 (95% Wald 0.00023-0.00139, moderately_determined)
    R3: NO3 -> SINK [power_law, deactivation(tau tie=tau_sink); e=5.0]; R3.k=0.000219 (95% Wald 7.51e-05-0.00064, moderately_determined)
    R4: NO2 -> NH3 [mass_action, deactivation(tau tie=tau_cat); e=6.0]; R4.k=0.000623 (95% Wald 0.00029-0.00134, moderately_determined)
    R5: NH3 + NO2 -> 2 SINK [mass_action, deactivation(tau tie=tau_sink); e=0.0]; R5.k=0.00157 (95% Wald 0.001-0.00247, well_determined)
    shared: tie:tau_cat=1.78e+03 (95% Wald 790-4.01e+03, moderately_determined); tie:n_NO3=1.41 (95% Wald 1.2-1.62, well_determined); tie:tau_sink=109 (95% Wald 90.9-130, well_determined)

- Support entries: {'literature': 0, 'data': 0, 'speculative': 5}; reactions without support: []
  - R1: speculative --  member of declared enumeration space liao-posthoc-v1
  - R2: speculative --  member of declared enumeration space liao-posthoc-v1
  - R3: speculative --  member of declared enumeration space liao-posthoc-v1
  - R4: speculative --  member of declared enumeration space liao-posthoc-v1
  - R5: speculative --  member of declared enumeration space liao-posthoc-v1
- sigma (profiled): NO3=1, NO2=0.333, NH3=1.65; adequacy: poor ['NH3: residual signs cluster (runs test p=0.025)', 'NH3: residuals are serially correlated (lag-1 r=0.66)']
- Profile likelihood: R1.k: identifiable (95% 5.05e-05-0.000289); tie:tau_cat: identifiable (95% 1e+03-1.26e+04); tie:n_NO3: identifiable (95% 1.2-1.62); R2.k: identifiable (95% 0.000227-0.00137); R3.k: identifiable (95% 7.36e-05-0.000625); tie:tau_sink: identifiable (95% 91.1-129); R4.k: inconclusive_numerics (95% 0.000245-0.000652); R5.k: identifiable (95% 0.00101-0.00212)
  ![profile](liao50-posthoc-enumeration_plots/C7a268d59de_profile.png)

### Cf1c6fa1e64 `enum-130814dffa` (source enumerator, version 1)

Rationale (proposer): enumerated: NO3>NO2,NO3>NH3,NO3>SINK,NO2>NH3,NO2>SINK,NH3+NO2>2SINK | power_NO3_shared_order | split_deactivation

    R1: NO3 -> NO2 [power_law, deactivation(tau tie=tau_cat); e=2.0]; R1.k=0.000115 (95% Wald 4.21e-05-0.000314, moderately_determined)
    R2: NO3 -> NH3 [power_law, deactivation(tau tie=tau_cat); e=8.0]; R2.k=0.000568 (95% Wald 0.000217-0.00149, moderately_determined)
    R3: NO3 -> SINK [power_law, deactivation(tau tie=tau_sink); e=5.0]; R3.k=0.00022 (95% Wald 7.01e-05-0.000691, moderately_determined)
    R4: NO2 -> NH3 [mass_action, deactivation(tau tie=tau_cat); e=6.0]; R4.k=0.000626 (95% Wald 0.000276-0.00142, moderately_determined)
    R5: NO2 -> SINK [mass_action, deactivation(tau tie=tau_sink); e=3.0]; R5.k=1e-07 (95% Wald 1e-07-10, not_determined_locally)
    R6: NH3 + NO2 -> 2 SINK [mass_action, deactivation(tau tie=tau_sink); e=0.0]; R6.k=0.00158 (95% Wald 0.000989-0.00252, well_determined)
    shared: tie:tau_cat=1.77e+03 (95% Wald 789-3.98e+03, moderately_determined); tie:n_NO3=1.41 (95% Wald 1.19-1.63, well_determined); tie:tau_sink=109 (95% Wald 90.8-130, well_determined)

- Support entries: {'literature': 0, 'data': 0, 'speculative': 6}; reactions without support: []
  - R1: speculative --  member of declared enumeration space liao-posthoc-v1
  - R2: speculative --  member of declared enumeration space liao-posthoc-v1
  - R3: speculative --  member of declared enumeration space liao-posthoc-v1
  - R4: speculative --  member of declared enumeration space liao-posthoc-v1
  - R5: speculative --  member of declared enumeration space liao-posthoc-v1
  - R6: speculative --  member of declared enumeration space liao-posthoc-v1
- sigma (profiled): NO3=1, NO2=0.333, NH3=1.65; adequacy: poor ['NH3: residual signs cluster (runs test p=0.025)', 'NH3: residuals are serially correlated (lag-1 r=0.66)']
- Locally unidentifiable combinations: [{'eigenvalue_rel': 6.484665480996704e-11, 'combination': {'R5.k': 1.0}}]
- Profile likelihood: not computed (identifiability beyond the local Fisher screen is unassessed)

### Ce9ce065acc `enum-b3539f5c4f` (source enumerator, version 1)

Rationale (proposer): enumerated: NO3>NO2,NO3>NH3,NO3>SINK,NO2>NH3,NH3+NO2>2SINK | mass_action | split_deactivation

    R1: NO3 -> NO2 [mass_action, deactivation(tau tie=tau_cat); e=2.0]; R1.k=0.000707 (95% Wald 0.000552-0.000906, well_determined)
    R2: NO3 -> NH3 [mass_action, deactivation(tau tie=tau_cat); e=8.0]; R2.k=0.00333 (95% Wald 0.00312-0.00355, well_determined)
    R3: NO3 -> SINK [mass_action, deactivation(tau tie=tau_sink); e=5.0]; R3.k=0.00161 (95% Wald 0.00119-0.00219, well_determined)
    R4: NO2 -> NH3 [mass_action, deactivation(tau tie=tau_cat); e=6.0]; R4.k=0.00184 (95% Wald 0.00109-0.00311, well_determined)
    R5: NH3 + NO2 -> 2 SINK [mass_action, deactivation(tau tie=tau_sink); e=0.0]; R5.k=0.00175 (95% Wald 0.000979-0.00311, well_determined)
    shared: tie:tau_cat=690 (95% Wald 605-786, well_determined); tie:tau_sink=96.4 (95% Wald 77.8-119, well_determined)

- Support entries: {'literature': 0, 'data': 0, 'speculative': 5}; reactions without support: []
  - R1: speculative --  member of declared enumeration space liao-posthoc-v1
  - R2: speculative --  member of declared enumeration space liao-posthoc-v1
  - R3: speculative --  member of declared enumeration space liao-posthoc-v1
  - R4: speculative --  member of declared enumeration space liao-posthoc-v1
  - R5: speculative --  member of declared enumeration space liao-posthoc-v1
- sigma (profiled): NO3=1.2, NO2=0.347, NH3=1.83; adequacy: poor ['NO3: residual signs cluster (runs test p=0.013)', 'NH3: residual signs cluster (runs test p=0.009)', 'NH3: residuals are serially correlated (lag-1 r=0.72)']
- Profile likelihood: not computed (identifiability beyond the local Fisher screen is unassessed)

### C73b758a2c4 `enum-c34ba4e7c1` (source enumerator, version 1)

Rationale (proposer): enumerated: NO3>NO2,NO3>NH3,NO3>SINK,NO2>NH3,NO2>SINK | power_NO3_shared_order | split_deactivation

    R1: NO3 -> NO2 [power_law, deactivation(tau tie=tau_cat); e=2.0]; R1.k=9.25e-05 (95% Wald 3.52e-05-0.000243, moderately_determined)
    R2: NO3 -> NH3 [power_law, deactivation(tau tie=tau_cat); e=8.0]; R2.k=0.00032 (95% Wald 0.000128-0.000798, moderately_determined)
    R3: NO3 -> SINK [power_law, deactivation(tau tie=tau_sink); e=5.0]; R3.k=0.000152 (95% Wald 5.46e-05-0.000422, moderately_determined)
    R4: NO2 -> NH3 [mass_action, deactivation(tau tie=tau_cat); e=6.0]; R4.k=0.00044 (95% Wald 0.000161-0.0012, moderately_determined)
    R5: NO2 -> SINK [mass_action, deactivation(tau tie=tau_sink); e=3.0]; R5.k=0.029 (95% Wald 0.0171-0.0492, well_determined)
    shared: tie:tau_cat=3.2e+03 (95% Wald 719-1.42e+04, moderately_determined); tie:n_NO3=1.51 (95% Wald 1.3-1.72, well_determined); tie:tau_sink=186 (95% Wald 153-225, well_determined)

- Support entries: {'literature': 0, 'data': 0, 'speculative': 5}; reactions without support: []
  - R1: speculative --  member of declared enumeration space liao-posthoc-v1
  - R2: speculative --  member of declared enumeration space liao-posthoc-v1
  - R3: speculative --  member of declared enumeration space liao-posthoc-v1
  - R4: speculative --  member of declared enumeration space liao-posthoc-v1
  - R5: speculative --  member of declared enumeration space liao-posthoc-v1
- sigma (profiled): NO3=1, NO2=0.374, NH3=2.01; adequacy: poor ['NH3: residual signs cluster (runs test p=0.025)', 'NH3: residuals are serially correlated (lag-1 r=0.71)']
- Profile likelihood: not computed (identifiability beyond the local Fisher screen is unassessed)

![top fits](liao50-posthoc-enumeration_plots/top_fits.png)

## Frozen selection

- Rule: lowest AICc among fitted candidates without a hidden-pool plausibility violation, plus every such candidate within delta AICc <= 2.0
- Selected: ['C7a268d59de']
- Agent-concluded plausible: []
- Frozen at 2026-10-20T17:31:55.626Z

## Final held-out evaluation: liao2025_wmos2_suppfig50a

Version: current evaluator code; the pre-registered evaluation (earlier code) is kept in final/final_evaluation.json.

Structure transfer: each frozen structure is refit on the held-out run (different catalyst) with the development protocol; parameters are not transferred. Rank is among all members of the declared enumeration spaces fitted to the same run.
Sensitivity: AICc at the lowest NLL any start reached (flags fits whose reported optimum is beaten by replicated unconverged starts). See docs/examples/arm_comparison.md for ranks in a shared reference set.

- C7a268d59de: fitted; AICc 154, delta to best 0, rank 1/766 among this run's declared-space members; numerically unreliable: False; sensitivity AICc 154 (rank 1); adequacy poor; RMSE {'NO3': 2.01, 'NO2': 0.32, 'NH3': 0.86}
- Best declared-space members on the held-out run: [('S:enum-fff2762723', 153.67, 'enumerated: NO3>NO2,NO3>NH3,NO3>SINK,NO2>NH3,NH3+NO2>2SINK | power_NO3_shared_order | split_deactivation'), ('S:enum-b3539f5c4f', 154.85, 'enumerated: NO3>NO2,NO3>NH3,NO3>SINK,NO2>NH3,NH3+NO2>2SINK | mass_action | split_deactivation'), ('S:enum-8f3dff9344', 157.05, 'enumerated: NO3>NO2,NO3>NH3,NO3>SINK,NO2>NH3,NO2>SINK | mass_action | split_deactivation')]

## Cost and runtime

- Numerics: 78 fits run, 12 reused from the shared cache, 2371 CPU s fitting, 136 s profiles (current evaluator code only; earlier code versions' records are excluded)
- LLM: none recorded

## Unresolved assumptions and metadata

- liao2025_mos2_suppfig50b: verified_against_figure=False
- [L3] catalyst assignment: unresolved discrepancy
- [L4] selectivity numbers: unresolved
- [L5] pH: stated for a related experiment; not measured for these runs
- [L6] NH3 escape: stated (qualitative)
- [L7] reference and iR: stated (flow cell)
- [L8] membrane: not found for the H-cell
- [L9] volume: stated for 0.5 h tests
- [L11] gas and crossover: not measured for these runs
- [L12] N balance: not found
- [L13] charge: not found for these runs
- [L14] mechanism (authors): stated (surface pathway, not a solution-phase kinetic model)
- [L15] replicates: no replicate information for these runs
- Noise model: independent Gaussian errors per channel (profiled sigma); no replicate information exists for these runs, so sigma is estimated from misfit and includes model error.
- AICc differences assume independent errors; clustered residual signs (adequacy 'poor') make them optimistic.

