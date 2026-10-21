# Katsounaros thesis Diag 12.1: measured intermediates against the nitrogen deficit

Derived inputs, not a dataset in `data/real`. The source is the Katsounaros PhD thesis (AUTh 2009, doi 10.12681/eadd/19491), Diag 12.1. It plots production and consumption rates for the 0.5 M NaNO3 + 1 M NaOH run on Sn at -2.2 V vs Ag/AgCl, which is the run in Katsounaros et al. 2012 Fig. 1 (W3/W4). Those rates were digitized and verified in `../katsounaros2009thesis_diag12p1_rates/` and are integrated here to concentrations. The integrals are compared with the deficit in `data/real/katsounaros2012_fig1_sn_naoh.json`, defined as 500 mM-N minus NO3, NO2, N2, N2O and NH3.

## Result

The main estimate is `fd_inverse` (method below). Coverage is (NH2OH + 2 x H2N2O2) / deficit. Brackets give the 68% interval from the rate reading error plus the deficit's digitization error (3.4 mM-N).

| t (min) | deficit, mM-N (% of N) | NH2OH | 2 x H2N2O2 | measured intermediates | coverage, fd_inverse | trapezoid | step rules | coverage if the +-10% bars are 1 sigma | unmeasured remainder, mM-N (% of N) | model B X |
|---|---|---|---|---|---|---|---|---|---|---|
| 30 | 114.3 (22.9) | 7.7 | 3.6 | 11.3 +- 0.2 | 0.099 [0.096-0.102] | 0.136 | 0.099-0.172 | 0.08-0.13 | 103.0 (20.6) | 64.3 |
| 60 | 142.2 (28.4) | 27.0 | 12.4 | 39.4 +- 0.4 | 0.277 [0.270-0.284] | 0.222 | 0.218-0.225 | 0.24-0.32 | 102.8 (20.6) | 117.8 |
| 90 | 95.7 (19.1) | 5.7 | 30.2 | 35.9 +- 0.4 | 0.375 [0.362-0.390] | 0.396 | 0.340-0.453 | 0.31-0.49 | 59.8 (12.0) | 122.5 |
| 120 | 106.3 (21.3) | 2.3 | 38.1 | 40.4 +- 0.5 | 0.380 [0.367-0.393] | 0.371 | 0.330-0.412 | 0.31-0.51 | 66.0 (13.2) | 101.4 |
| 150 | 86.4 (17.3) | 0.0 | 41.2 | 41.1 +- 0.6 | 0.476 [0.457-0.497] | 0.471 | 0.405-0.537 | 0.35-0.73 | 45.2 (9.0) | 74.4 |
| 180 | 77.7 (15.5) | 0.0 | 40.1 | 40.2 +- 0.7 | 0.517 [0.493-0.542] | 0.517 | 0.438-0.596 | 0.36-0.85 | 37.6 (7.5) | 50.7 |

All values are in mM-N. The step-rule column is the range of the left and right rectangle rules. Model B X uses the paper's Table 1 constants (as in `worlds/W3...`) and peaks at 125.2 mM-N (25.0% of N) at 77.8 min. With the deficit computed from the thesis copy of the figure (Diag 12.3 markers) instead of Daniel's reading, fd_inverse coverage is 0.099, 0.270, 0.386, 0.406, 0.491 and 0.498.

**N basis.** NH2OH counts as 1 N. H2N2O2 counts as 2 N because the plotted rates are per molecule. Four pieces of evidence support this:
- All six species share the mM/min axis. The other 2-N species, N2 and N2O, are per molecule: doubled, their integrals reproduce the N-equivalent concentrations to 0.2 mM-N.
- Hyponitrite was measured by ion chromatography (AS19, UV 248 nm) calibrated in mg/L of the anion (thesis printed pp. 70-71).
- The thesis writes the hyponitrite reactions per molecule (2 HNO -> H2N2O2, H2N2O2 -> N2O + H2O).
- With the x2 basis the intermediates never exceed the deficit.

The mass balance alone does not discriminate between bases. Over 30-180 min, weighted by deficit, the unmeasured share is 0.67 with x2 and 0.80 if the rates were already N-equivalents. The thesis's "remaining ~70% is nitramide" is closer to the x2 figure, but the thesis states it for a different run.

**Method.** The plotted rates are numerical derivatives of the 30-min (or 15-min GC) concentration samples, not instantaneous rates. Each point is the mean of the two adjacent interval slopes, which is a central difference on this grid, with one-sided slopes at the ends (Origin's Differentiate). Differentiating the thesis's NO2- markers this way reproduces the stored rates to within 0.01 mM/min. Inverting the scheme (`fd_inverse`) reproduces the thesis's plotted NO2-, N2 and N2O to 0.17-0.19 mM-N RMS. The trapezoid rule gives 11.4, 1.9 and 0.7, and for NO2- it is 21 mM low at 30 min. The trapezoid and step rules are kept in `extracted.csv` for comparison.

**Thesis text.** NH2OH was measured colorimetrically (8-hydroxyquinoline at 705 nm, or ferrozine/Fe3+ at 562 nm) and hyponitrite by ion chromatography at 248 nm. Nitramide (NH2NO2) is proposed as the remaining loss but was never quantified; the thesis kinetic model uses it as the hidden species. See `meta.json` (`thesis_statements`) for pages and quotes.

## What this means for model B (W3/W4)

- From 90 min on, 36-41 mM-N (7-8% of total N) sits in two species the thesis measured but the five-species dataset leaves out. Hyponitrite holds nearly all of it from 120 min on (at 90 min NH2OH is still 5.7 of 35.9 mM-N, 16%), and it stays at about 40 mM-N through 180 min. That is 38-52% of the deficit.
- The thesis assigns these species to other routes: hyponitrite decomposes to N2O (a hyponitrite electrolysis gave N2O:N2 = 30:1), and NH2OH goes to NH3. Model B's X feeds only N2, so it should not absorb them. The unmeasured remainder is the pool a nitramide-like X would have to hold.
- That remainder peaks at about 103 mM-N (20.6% of N) at 30-60 min (98.8-111.2 across integration schemes and deficit sources), falls to 60-66 at 90-120 min and to 38 by 180 min. Weighted by deficit, it is two thirds of the loss, close to the thesis's "about 70%".
- Model B's X peaks at 125.2 mM-N (25.0% of N) at 77.8 min. It exceeds the remainder by 15.0, 62.7, 35.5, 29.2 and 13.1 mM-N at 60-180 min, and it falls 38.7 mM-N short at 30 min. Two qualifications:
  - The excess is not all hidden-pool size. X minus the deficit equals the observed data minus model B's observed species, so the excess includes model B's misfit. At 90 min X (122.5) exceeds even the whole deficit (95.7) by 26.8 mM-N, because model B under-predicts NO3 + NO2 there (149.3 against 184.1 mM-N). The 62.7 mM-N excess at 90 min is 26.8 of misfit plus the 35.9 of measured intermediates.
  - Noise. If the +-10% bars are 1 sigma, the deficit carries 20-32 mM-N (27.6, 20.0, 21.8, 26.3, 30.2, 31.9 at 30-180 min), and the remainder at least as much. The 60- and 180-min excesses (15.0 and 13.1) are within 1 sigma. Only 90 min clears it clearly, 120 min marginally, and 150 min sits at about 1 sigma.
- What holds up is X's timing (it peaks at 78 min, after the remainder, which is highest at 30-60 min) and the sign of its excess at 90-150 min; the size of that excess is uncertain. Hyponitrite and NH2OH explain part of the "hidden pool", but not all of it.
- For the plausibility rule (`max_hidden_fraction_of_total_N` = 0.30): the data-implied unobserved pool falls from 28.4% of N (the deficit at 60 min) to 20.6% once the measured intermediates are removed, and model B's X peaks at 25.0%. Even with the intermediates removed, a substantial unmeasured pool remains, so "implausibly large" should be argued from X's size and timing relative to this remainder, not from X's existence.

## Limits

- The rates were digitized from a plot. The verified reading error, at most 0.004 mM/min, adds no more than 0.65 mM-N to any integral.
- The fd_inverse scheme is validated on NO2-, N2 and N2O only. NH2OH and H2N2O2 concentrations are not plotted anywhere in the thesis, so their inversion cannot be checked directly.
- NH3 does not invert to the thesis markers: the inverted values are 3.3, 8.0, 14.9, 20.8, 23.9 and 27.1 mM, against markers of 4.3, 4.8, 15.0, 26.2, 24.3 and 27.4. The NH3 rates must therefore come from slightly different NH3 values (closer to Daniel's 7.6 and 19.6 at 60 and 120 min), and the same could be true for other species. With the trapezoid instead, coverage moves by up to 0.055. This is why the earlier cross-check verdict on Daniel's NH3 at 60 and 120 min ("misclick", "occlusion") is now unresolved and source-dependent (`docs/DATASETS.md`, section 2).
- The thesis does not state that Diag 12.1, Diag 12.3 and paper Fig. 1 are the same run. The identity is inferred from matching conditions and times and from the integrated rates reproducing the plotted concentrations.
- The deficit is a difference of large numbers. If the thesis's +-10% bars are 1-sigma errors, it carries 20-32 mM-N, and the coverage at 150-180 min is bounded only to 0.35-0.85.
- NH2OH can react with nitrite before analysis, and hyponitrite decomposes to N2O (thesis printed pp. 140 and 145). The measured intermediates are therefore lower bounds.

Files: `extracted.csv` (4 methods x 6 species; columns in `meta.json`) and `meta.json`. Scripts: `literature/extraction_scripts/k12_hidden/integrate_intermediates.py` and `write_meta_intermediates.py`.
