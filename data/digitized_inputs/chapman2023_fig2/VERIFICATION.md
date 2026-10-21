# Chapman 2023 Fig. 2: check of the extraction against the published figure (2026-10-21)

Source: `ja3c10916.pdf` and `ja3c10916_si_001.pdf` from Daniel's synthesis literature zip. Checked by an assistant
subagent and not yet re-checked by a person.

Method:
- Fig. 2 was read at native resolution: an embedded raster of 985 x 1859 px, 300 ppi.
- Axes were calibrated from the tick marks: 87.45 px per min and 5.675 px per wt %.
- Curves were read as the centre of each area's coloured outline. This is independent of the extraction script's
  fill-colour classification.
- The authors' line plot of the same results (SI Fig. S1, p. S3) was read as a second reference.

## Verdict

- **From t ≥ 0.35 min the extraction matches the figure.**
  - All 42 spot checks agree within 1 wt % (largest difference 0.9).
  - The RMS error per phase over every 0.05 min column is 0.07-0.47 wt %.
  - Colours are assigned to the right phases: the labels printed inside Fig. 2 and the SI Fig. S1 legend agree.
- **At t ≤ 0.3 min the values are wrong**, by up to 22 wt % (Li2TiO3) and 14 wt % (Li2CO3). The vertical Li2CO3 label
  and the converging lines are the cause.
  - The rutile impurity of about 4 wt % present from t = 0 is read as 0.
  - The 750 C Li2TiO3 peak (about 55.5-56 wt % at about 0.28-0.30 min) is lost.
  - Anatase reaches zero too early at 700 C (7.6 min; printed about 8.0-8.5) and at 725 C (2.45 min; printed about
    2.75-2.8), because tails below 1 wt % are cut to 0.
- **Consequence for `data/real/chapman2023_fig2_*C.json`.** Their first grid point (0.3 min) averages the 0.30 and
  0.35 min columns, so it carries part of this error. The Oct 21 investigations (`chapman750-*`) used these files as they
  are; the error is the same for every arm.
- **Next version:** start the grid at 0.35 min. Mark the files `verified_against_figure` only with the scope
  "t ≥ 0.35 min".

## Spot checks (wt %; printed = reading of Fig. 2, extr = CSV)

| T | t (min) | phase | printed | extr |
|---|---|---|---|---|
| 700 | 1 | Li2TiO3 | 53.8 | 53.8 |
| 700 | 5 | Li2TiO3 | 42.1 | 42.1 |
| 700 | 5 | Li4Ti5O12 | 28.3 | 28.4 |
| 700 | 9 | rutile | 27.0 | 26.9 |
| 725 | 0.5 | Li2TiO3 | 54.6 | 54.0 |
| 725 | 2 | Li4Ti5O12 | 23.3 | 23.6 |
| 725 | 9 | Li4Ti5O12 | 34.7 | 34.5 |
| 750 | 2 | Li4Ti5O12 | 33.3 | 33.3 |
| 750 | 5 | Li2TiO3 | 35.4 | 34.5 |
| 750 | 9 | rutile | 20.5 | 20.2 |

The full 42-point table is in the session record. Maximum Li2TiO3:

| T | printed | extraction |
|---|---|---|
| 700 C | 54.4 wt % | 54.2 |
| 725 C | 55.7 wt % | 55.4 |
| 750 C | about 55.5-56 wt % | 53.7 |

## Lithium balance

The published fractions do not conserve lithium. With nominal formulas, readings of the printed figure give the Li per
Ti below; the 5:2 mix supplies 0.80. The extraction reproduces these within 0.015, and swapping the two purple bands
would contradict the printed labels without fixing the balance.

| T | 1 min | 2 min | 5 min | 9 min |
|---|---|---|---|---|
| 700 C | 0.95 | 0.98 | 0.96 | 0.96 |
| 725 C | 1.02 | 1.02 | 0.97 | 0.95 |
| 750 C | 1.02 | 0.99 | 0.95 | 0.95 |

The authors attribute the high Li2TiO3 fraction to a Li-deficient phase, written Li2-xTiO3-x (p. 26546-26547, no x
given). Restoring 0.8 Li per Ti would need x of about 0.4-0.6. The paper does not discuss amorphous content, an internal
standard, or peak overlap between Li2TiO3 and spinel Li4Ti5O12.

## What the paper states

- **Reactions (p. 26546):**
  - TiO2 + Li2CO3 → Li2TiO3 + CO2
  - 3 TiO2 + 2 Li2TiO3 → Li4Ti5O12
  - anatase → rutile
- **Preparation (SI p. S2):**
  - 5:2 molar anatase (30 nm) : Li2CO3, as a pellet in a 1.1 mm SiO2 capillary.
  - Rietveld refinement in TOPAS 6.
  - Not stated: the list of refined phases, amorphous content or atmosphere.
- **Heating (SI Fig. S2):**
  - The sample is within 50 K of target after 6 s and within 7 K after 10 s, measured at 750 C.
  - t = 0 is insertion into the hot zone.
- **Avrami analysis (p. 26547, Fig. 4):**
  - It covers Li2TiO3 formation and consumption only.
  - Formation slopes are about 1.4, then about 0.5. No per-temperature values and no rate constants are given.
- **Activation energy:** none reported in the main text or the SI.
- **Rutile:**
  - "increases throughout" (p. 26546).
  - Li4Ti5O12 forms faster while anatase remains and slows once only rutile remains (p. 26547).
  - In the figure, rutile falls at 750 C (about 26 to 20.5 wt %) and at 725 C (about 28 to 26). After Li2CO3 is gone no
    gas leaves, so the falling weight fraction means rutile is consumed.
- **Data availability:** no statement; the SI has no numerical tables.

## Corrections to `meta.json` (not applied; Daniel's file)

1. **The Li2TiO3 maximum is not about 2 wt % high from line thickness.** The printed data peak at 54-56 wt %; "~52" is
   the authors' approximate figure.
2. **The Li2CO3 strip is not a line-width artefact.** SI Fig. S1 plots Li2CO3 at 0.5-0.9 wt % (700 and 750 C) and
   1.7-1.9 wt % (725 C) through 600 s. Treating it as zero is still defensible, because the text says its peaks are
   indistinguishable after 30 s.
3. **The "initial 75/25 vs 73/27" check is coincidental.** The paper shows about 76 anatase, 4 rutile and 20-21 Li2CO3
   at 700 C.
4. **The Fig. 3 (482 C) baseline is wrong.** The script uses row 499, the tick-label text, as the x axis instead of row
   463, so every amount is offset by about +0.07. Slope ratios are unaffected.
5. **The initiation note should cite SI Fig. S2.**
