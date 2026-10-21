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

## Held-out run (Fig. 50a): frozen candidates refit with the same protocol

Structure transfer: parameters are refit on the held-out run (different catalyst). Ranks are among one shared reference set: every member of every declared enumeration space (706 fits, pre-declared and post-hoc) fitted to the same held-out data.

| run | candidate | role | protocol AICc | protocol rank | numerically unreliable | sensitivity AICc | sensitivity rank | adequacy | RMSE |
|---|---|---|---|---|---|---|---|---|---|
| liao50-enumeration-v3 | C6d5e25b6d8 | selected | 179.17 | 13/706 | False | 179.17 | 16/706 | poor | {'NO3': 2.08, 'NO2': 0.75, 'NH3': 0.91} |
| liao50-enumeration-v3 | C29ca4c5b0b | selected | 179.3 | 14/706 | False | 179.3 | 17/706 | poor | {'NO3': 2.08, 'NO2': 0.75, 'NH3': 0.92} |
| liao50-enumeration-v3 | C160a84797b | selected | 179.41 | 15/706 | False | 179.41 | 18/706 | poor | {'NO3': 2.08, 'NO2': 0.75, 'NH3': 0.92} |
| liao50-posthoc-enumeration | C7a268d59de | selected | 153.67 | 1/706 | False | 153.67 | 1/706 | poor | {'NO3': 2.01, 'NO2': 0.32, 'NH3': 0.86} |
| liao50-propose_only-live2 | C99c623cc3e | selected | 207.7 | 95/706 | False | 207.7 | 109/706 | poor | {'NO3': 2.09, 'NO2': 0.78, 'NH3': 2.02} |
| liao50-critique_revise-live2 | C4c5ed52b1e | agent-plausible | 305.26 | 662/706 | True | 165.61 | 7/706 | poor | {'NO3': 22.59, 'NO2': 2.62, 'NH3': 0.98} |
| liao50-critique_revise-live2 | C28308d8958 | agent-plausible | 188.76 | 47/706 | False | 188.74 | 50/706 | poor | {'NO3': 2.36, 'NO2': 0.48, 'NH3': 1.66} |
| liao50-critique_revise-live2 | Cb716706e37 | agent-plausible | 192 | 48/706 | False | 192 | 51/706 | poor | {'NO3': 4.69, 'NO2': 0.35, 'NH3': 1.28} |
| liao50-critique_revise-live2 | Cb899debfb5 | selected+agent-plausible | 357.71 | 701/706 | True | 193.88 | 53/706 | poor | {'NO3': 22.1, 'NO2': 1.26, 'NH3': 9.78} |
