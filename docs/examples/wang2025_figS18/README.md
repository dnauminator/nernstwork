# Wang 2025 SI Fig. S18: digitized time course and a nitrate-network fit

Done October 22, 2026, on Jarrod's request relayed by the mechanism-investigation session. Nothing here is committed.

**Data.** `data/real/wang2025_figS18_rtio2cu2o.json`, built from `data/digitized_inputs/wang2025_figS18_rtio2cu2o/` by `scripts/digitized_to_dataset.py`. The extraction is reproducible with `scripts/extract_wang2025_figS18.py` from the SI file, which is not committed. Values are in mM-N (mg N L⁻¹ ÷ 14.0067).

- 7 times × 3 species (nitrate, nitrite, ammonium) on R-TiO2/Cu2O, starting from 50 mg N L⁻¹.
- Error-bar half-lengths are stored as per-point `sigma` where readable (12 of 21 points).
- `verified_against_figure` is false; caveats are in `meta.json`.
- Observed N closure: 1.00, 0.90, 0.93, 0.90, 0.91, 0.91, 0.91.

**Fit.** Every member of `configs/spaces/liao_core.json` (36 networks) was fitted with the existing evaluator functions and the `mle-profiled-v1` protocol: sequential, 176 s, no investigation run. Results are in `fit_liao_core_summary.json`, with the data and the best fits in `fit_overlay.png`. Rate constants are in min⁻¹ at full activation; the activation multiplies every rate by 1 − exp(−t/τ). The fitted noise is 0.074 mM-N for nitrate; nitrite and ammonium sit at the protocol floor of 0.05 mM-N.

| Network | ΔAICc | NO3⁻→NO2⁻ | NO2⁻→NH4⁺ | Sink step | τ (min) |
|---|---:|---|---|---|---|
| NO3⁻→NO2⁻→NH4⁺, NO3⁻→sink, shared activation | 0 | 0.0255 (0.0228–0.0284) | 0.272 (0.184–0.404) | NO3⁻→sink 0.00252 (0.00186–0.00339) | 10.0 (6.5–15.4) |
| same, sink from NO2⁻ instead | 0.9 | 0.0280 (0.0246–0.0319) | 0.279 (0.184–0.422) | NO2⁻→sink 0.0274 (0.0161–0.0464) | 10.6 (6.9–16.4) |
| best with a sink, no activation | 9.5 | | | | |
| best without a sink (NO3⁻→NO2⁻→NH4⁺, activation) | 14.6, ammonium residuals clustered (runs test p < 0.001) | 0.0275 | 0.334 | none | 7.6 |

Ranges are Wald 95% intervals from the evaluator.

**Is the unaccounted N significant?** Within this model family and noise model, yes:

- Dropping the sink costs 14.6 AICc and leaves a systematic ammonium misfit: RMSE 0.31 against 0.04 mM-N, with the model overshooting from 60 min on.
- The sink rate's interval excludes zero.
- The best model routes 9.0% of the nitrate to the sink and predicts 0.318 mM-N (4.45 mg N L⁻¹) unmeasured at 180 min, matching the observed gap of 0.317 mM-N.
- Against the plotted error bars, the 120–150 min gap (about 4.5 mg N L⁻¹) is roughly 4–5 bar half-widths (ammonium ±0.8–0.9, nitrate ±0.5). At 30 min the bars (±4.5 and ±3.2) cover it.

What the data cannot settle:

1. The gap is already there at the first sample (closure 0.90 at 30 min) and stays flat at 0.27–0.36 mM-N. A constant ~9% offset between the three colorimetric assays would look the same as an early N2/N2O loss. Gases were not measured; the authors count the gap as N2 by assumption (SI Text S5).
2. Whether the sink branches from nitrate or from nitrite is not identifiable (ΔAICc 0.9).
3. The 10 min activation time is supported against no catalyst-state term (ΔAICc 9.5). But there is no sample between 0 and 30 min, so it is one parameter absorbing a slower first interval; a time-origin offset or a start-up transient would fit equally well. It should not be read as evidence of catalyst activation.
4. The fit used the protocol's per-channel noise, not the digitized error bars, which are stored for later use.
5. The potential for Fig. S18 is not stated in the SI. The catalyst's calcination temperature is inferred (rutile-only TiO2 appears at 900 °C in SI Fig. S4), not stated.

**Synthesis link.** This is one synthesis condition (rutile TiO2) with one set of rate constants. A synthesis-to-rate-constant comparison needs the anatase catalyst's time course, which is not in the SI and may be in the paywalled main text.
