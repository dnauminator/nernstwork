# Arm comparison: Liao Fig. 50b (development) and Fig. 50a (held out)

Held-out results: pre-registered (first) final evaluation of each run.

All arms share the protocol, development data, validator and fitter (same deterministic multistart). Candidates outside the declared enumeration spaces enlarge the model space; compare best_in_space_aicc with the enumeration arm to separate discovery within the space from expansion of the space. 'Sensitivity' scores every fit by the lowest NLL any start reached, applied identically to all arms and all space members; it exposes fits where unconverged starts replicated a better optimum than the one the protocol reports.

## Development data (Fig. 50b, MoS2)

| run | arm | candidates | statuses | best (AICc) | in declared space? | best in-space | best out-of-space | unreliable fits | sensitivity best | fits run / reused | fit CPU s | LLM tokens in/out (cache read/write) | LLM cost, list USD | LLM wall s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| liao50-enumeration-v3 | enumeration | 654 | {'fitted': 654} | enum-2ed1b3b4a8 (204.95) | True | 204.95 | - | 3 | 204.95 | 654 / 0 | 2.16e+04 | - | - | - |
| liao50-posthoc-enumeration | enumeration | 90 | {'fitted': 90} | enum-fff2762723 (151.54) | True | 151.54 | - | 0 | 151.54 | 78 / 12 | 2.37e+03 | - | - | - |
| liao50-propose_only-live2 | propose_only | 10 | {'fitted': 10} | powerlaw_direct_NH3escape_deact (166.25) | False | 274.76 | 166.25 | 0 | 166.25 | 7 / 3 | 462 | 68/50595 (1479505/235065) | 2.48 | 3.44e+03 |
| liao50-critique_revise-live2 | critique_revise | 10 | {'fitted': 10} | comprop_N2_pHshutoff_powerlaw (168.74) | False | - | 168.74 | 0 | 168.74 | 4 / 6 | 67.2 | 184/125647 (6396397/538692) | 6.49 | 3.24e+03 |
| liao50-propose_only-live3 | propose_only | 10 | {'fitted': 10} | KG_powerlaw_NO2NH3_coupling (163.43) | False | 247.57 | 163.43 | 0 | 163.43 | 5 / 5 | 162 | 50/34087 (961837/94096) | 1.34 | 566 |
| liao50-critique_revise-live3 | critique_revise | 10 | {'fitted': 10} | c3_parallel_pl_NH4_transport_no_deact (166.25) | False | 247 | 166.25 | 0 | 166.25 | 5 / 5 | 207 | 104/68772 (2742300/214930) | 3 | 1.11e+03 |
| liao50-propose_only-gemini1 | propose_only | 10 | {'fitted': 10} | C10_dual_pathway_zeroorder_hidden (131.05) | False | 247 | 131.05 | 0 | 131.05 | 6 / 4 | 298 | 1061729/155620 (7970567/0) | 4.48 | 4.8e+03 |
| liao50-propose_only-gemini2 | propose_only | 10 | {'fitted': 10} | c06_ser_par_no2_branch (143.01) | False | 247 | 143.01 | 0 | 143.01 | 6 / 4 | 160 | 883555/140117 (8135233/0) | 3.98 | 5.19e+03 |
| liao50-critique_revise-gemini1 | critique_revise | 10 | {'fitted': 10} | dual_path_step_deact_n2 (143.01) | False | 247 | 143.01 | 0 | 143.01 | 7 / 3 | 225 | 560227/213677 (14230020/0) | 4.68 | 4.81e+03 |
| liao50-critique_revise-gemini2 | critique_revise | 10 | {'fitted': 10} | C5_v2_full_series_parallel_NO2_to_NH3_and_N2 (154.23) | False | 247 | 154.23 | 0 | 154.23 | 8 / 2 | 185 | 486656/191021 (10094868/0) | 3.89 | 4.11e+03 |

## Held-out run (Fig. 50a): frozen candidates refit with the same protocol

Structure transfer: parameters are refit on the held-out run (different catalyst). Ranks are among one shared reference set: every member of every declared enumeration space (1359 fits, pre-declared and post-hoc) fitted to the same held-out data.

| run | candidate | role | protocol AICc | protocol rank | numerically unreliable | sensitivity AICc | sensitivity rank | adequacy | RMSE |
|---|---|---|---|---|---|---|---|---|---|
| liao50-enumeration-v3 | C6d5e25b6d8 | selected | 179.17 | 13/1359 | False | 179.17 | 16/1359 | poor | {'NO3': 2.08, 'NO2': 0.75, 'NH3': 0.91} |
| liao50-enumeration-v3 | C29ca4c5b0b | selected | 179.3 | 15/1359 | False | 179.3 | 18/1359 | poor | {'NO3': 2.08, 'NO2': 0.75, 'NH3': 0.92} |
| liao50-enumeration-v3 | C160a84797b | selected | 179.41 | 17/1359 | False | 179.41 | 20/1359 | poor | {'NO3': 2.08, 'NO2': 0.75, 'NH3': 0.92} |
| liao50-posthoc-enumeration | C7a268d59de | selected | 153.67 | 1/1359 | False | 153.67 | 1/1359 | poor | {'NO3': 2.01, 'NO2': 0.32, 'NH3': 0.86} |
| liao50-propose_only-live2 | C99c623cc3e | selected | 207.7 | 173/1359 | False | 207.7 | 188/1359 | poor | {'NO3': 2.09, 'NO2': 0.78, 'NH3': 2.02} |
| liao50-critique_revise-live2 | C4c5ed52b1e | agent-plausible | 305.26 | 1278/1359 | True | 165.61 | 7/1359 | poor | {'NO3': 22.59, 'NO2': 2.62, 'NH3': 0.98} |
| liao50-critique_revise-live2 | C28308d8958 | agent-plausible | 188.76 | 78/1359 | False | 188.74 | 81/1359 | poor | {'NO3': 2.36, 'NO2': 0.48, 'NH3': 1.66} |
| liao50-critique_revise-live2 | Cb716706e37 | agent-plausible | 192 | 80/1359 | False | 192 | 83/1359 | poor | {'NO3': 4.69, 'NO2': 0.35, 'NH3': 1.28} |
| liao50-critique_revise-live2 | Cb899debfb5 | selected+agent-plausible | 357.71 | 1353/1359 | True | 193.88 | 85/1359 | poor | {'NO3': 22.1, 'NO2': 1.26, 'NH3': 9.78} |
| liao50-propose_only-live3 | C8ff8e358e4 | selected+agent-plausible | 193.11 | 80/1359 | False | 193.11 | 85/1359 | poor | {'NO3': 2.09, 'NO2': 0.55, 'NH3': 1.72} |
| liao50-critique_revise-live3 | Ce44565618a | agent-plausible | 168.17 | 8/1359 | False | 168.17 | 9/1359 | poor | {'NO3': 2.24, 'NO2': 0.49, 'NH3': 0.85} |
| liao50-critique_revise-live3 | C91676a641c | selected+agent-plausible | 187.47 | 78/1359 | False | 187.47 | 81/1359 | poor | {'NO3': 2.17, 'NO2': 0.75, 'NH3': 1.02} |
| liao50-critique_revise-live3 | C99c623cc3e | selected+agent-plausible | 207.7 | 173/1359 | False | 207.7 | 188/1359 | poor | {'NO3': 2.09, 'NO2': 0.78, 'NH3': 2.02} |
| liao50-propose_only-gemini1 | Cc27c260c8f | agent-plausible | 162.57 | 7/1359 | False | 162.57 | 7/1359 | poor | {'NO3': 1.97, 'NO2': 0.44, 'NH3': 0.76} |
| liao50-propose_only-gemini1 | Cdacf4d1fda | selected+agent-plausible | 159.13 | 6/1359 | False | 159.13 | 6/1359 | poor | {'NO3': 1.97, 'NO2': 0.44, 'NH3': 0.76} |
| liao50-propose_only-gemini2 | Cb18c56104e | agent-plausible | 154.25 | 2/1359 | False | 154.25 | 2/1359 | poor | {'NO3': 1.99, 'NO2': 0.36, 'NH3': 0.71} |
| liao50-propose_only-gemini2 | Cda222e794b | selected+agent-plausible | 160.18 | 6/1359 | False | 160.18 | 6/1359 | poor | {'NO3': 1.92, 'NO2': 0.36, 'NH3': 0.98} |
| liao50-propose_only-gemini2 | Cd19c0c2114 | selected+agent-plausible | 166.97 | 7/1359 | False | 166.97 | 8/1359 | poor | {'NO3': 1.84, 'NO2': 0.47, 'NH3': 0.96} |
| liao50-propose_only-gemini2 | C1a420ff7fa | selected+agent-plausible | 161.42 | 7/1359 | False | 161.42 | 7/1359 | poor | {'NO3': 1.85, 'NO2': 0.39, 'NH3': 0.98} |
| liao50-critique_revise-gemini1 | C1a420ff7fa | selected+agent-plausible | 161.42 | 7/1359 | False | 161.42 | 7/1359 | poor | {'NO3': 1.85, 'NO2': 0.39, 'NH3': 0.98} |
| liao50-critique_revise-gemini1 | Cd19c0c2114 | selected+agent-plausible | 166.97 | 7/1359 | False | 166.97 | 8/1359 | poor | {'NO3': 1.84, 'NO2': 0.47, 'NH3': 0.96} |
| liao50-critique_revise-gemini1 | C3d81e8b104 | selected+agent-plausible | 161.42 | 7/1359 | False | 161.42 | 7/1359 | poor | {'NO3': 1.85, 'NO2': 0.39, 'NH3': 0.98} |
| liao50-critique_revise-gemini2 | C39de24b5ec | agent-plausible | 165.11 | 7/1359 | False | 165.11 | 7/1359 | poor | {'NO3': 1.84, 'NO2': 0.54, 'NH3': 0.94} |
| liao50-critique_revise-gemini2 | C27d286ccc0 | agent-plausible | 169.05 | 8/1359 | False | 169.05 | 10/1359 | poor | {'NO3': 1.61, 'NO2': 0.43, 'NH3': 1.52} |
| liao50-critique_revise-gemini2 | C4bef486db1 | selected+agent-plausible | 172.72 | 10/1359 | False | 172.72 | 13/1359 | poor | {'NO3': 1.44, 'NO2': 0.74, 'NH3': 1.01} |
| liao50-critique_revise-gemini2 | C4e60f25464 | agent-plausible | 154.77 | 2/1359 | False | 154.77 | 2/1359 | poor | {'NO3': 1.61, 'NO2': 0.45, 'NH3': 0.97} |
