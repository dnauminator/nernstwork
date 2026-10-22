# Arm comparison: Chapman 2023, fit 700 + 725 C, predict 750 C

Every arm shares the protocol, the development data and the reference space. The 750 C run is predicted with development parameters (no refitting). Held-out score: squared error weighted by one common noise scale per phase, the development sigma of the reference member with the lowest development AICc (lower is better). Ranks are among the 153 reference-space members scored the same way; the own-sigma log-likelihood rank measures calibration (it penalizes models whose development noise estimate understates the extrapolation error).

| run | arm | model | candidates (by source) | spaces | best development AICc | frozen top-1 | held-out score | held-out rank | rank by RMSE | rank by own-sigma NLL | RMSE all | own space: best predictor rank | own space: dev-best rank | LLM cost, list USD |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| chapman750-enumeration | enumeration | - | 154 {'enumerator': 154} | 0 | -851.48 | C32c8c435ed | 1072 | 11/153 | 7 | 124 | 0.0317 | 1 | 11 | - |
| chapman750-propose_space-opus1 | propose_space | anthropic/claude-opus-5-5 | 208 {'agent_space': 204, 'agent': 4} | 2 | -1196 | C914ebc19e9 | 744.1 | 4/153 | 1 | 150 | 0.0248 | 1 | 4 | 3.9 |
| chapman750-propose_space-opus2 | propose_space | anthropic/claude-opus-5-5 | 256 {'agent_space': 252, 'agent': 4} | 2 | -1072.8 | C3a9765bced | 1567 | 36/153 | 16 | 149 | 0.0359 | 4 | 36 | 2.77 |
| chapman750-propose_space-gemini1 | propose_space | openrouter/google/gemini-4-argon | 178 {'agent_space': 174, 'agent': 4} | 2 | -1137.1 | C7cafaafde1 | 1040 | 11/153 | 1 | 147 | 0.0276 | 1 | 11 | 6.5 |
| chapman750-propose_space-gemini2 | propose_space | openrouter/google/gemini-4-argon | 220 {'agent_space': 216, 'agent': 4} | 2 | -1121 | Cf53e5b4f3d | 1587 | 36/153 | 11 | 151 | 0.0345 | 1 | 36 | 4.43 |

Reference space on the held-out run: best members enum-9db30b59d8 (603.8), enum-0d02fc61ca (604.2), enum-c0459e266c (606); the member with the best development AICc ranks 11.
