# Willoughby et al. 2026, Supporting Information: what was digitized

Source: Willoughby, Hannagan, Guo, Benedek, Yap, Burke Stevens, Nielander, Tarpeh, Jaramillo, "Dynamic Quantification of Nitrogen Species in Acidic Titanium-Catalyzed Nitrate Reduction toward Ammonia", ACS Electrochem. 2 (2026) 353, doi 10.1021/acselectrochem.5c00405. Only the SI was available; the main text was not read.

Licence: the SI is CC BY-NC 4.0 per ACS figshare article 31048851 (doi 10.1021/acselectrochem.5c00405.s001). The unstamped file used here has the same MD5 as the figshare file (checked Oct 20 2026). The stamped copy came from pubs.acs.org, whose own SI terms were not checked. Whether NernstWork's use counts as NonCommercial is the repository owner's decision (`docs/DATASETS.md`, section 7).

Two uploaded SI files (`ec5c00405_si_001.pdf`, `ec5c00405_si_001__1_.pdf`) have identical text and byte-identical figure images. The second adds only an ACS "Downloaded from pubs.acs.org ... by guest on 20 October 2026" stamp in the right margin of every page, plus different PDF metadata. The unstamped file was used.

Extracted by agent team, 2026-10-20. All files in these folders are inputs. They are gas-phase EC-MS signals, not batch concentration trajectories. Do not run `scripts/digitized_to_dataset.py` on them and do not copy them to `data/real`.

## What the SI contains

| Item | Page | Content | Extracted |
|---|---|---|---|
| Table S1, S3 | S2, S7 | m/z channels tracked per candidate species (14N, 15N) | no (text) |
| Table S2 | S3 | Henry constants, M/atm: N2 6.24e-4 (25 C), N2O 2.5e-2 (15 C), NO 1.94e-3 (20 C), NO2 1.31e-3 (25 C), NH3 80.9 (17.5 C) | values listed here |
| Fig. S1 | S4 | 14N, galvanostatic pulses -0.1 mA/cm2, 0-57 min. (a) raw m/z 2, 17, 28, 30, 32, 33, 44 (pA); (b) m/z 30 total vs N2O fragment; (c) H2, NO, N2O flux plus j and E | S1c |
| Fig. S2 | S5 | as S1 at -0.2 mA/cm2, 0-36 min | S2c |
| Fig. S3 | S6 | as S1, potentiostatic -1.0 V vs RHE for 1 h, 5-67 min | S3c (no current) |
| Fig. S4 | S9 | 15N raw ion currents m/z 2, 18, 30, 31, 32, 34, 46 plus j and E: (a) -0.1 mA/cm2 pulses, (b) -0.2 mA/cm2 pulses, (c) -1.0 V vs RHE (JPEG) | m/z 30, 31, 46, j, E |
| Fig. S5 | S10 | 15N m/z 15 (total, and with 15NO/15N2O fragment contributions removed) and m/z 31 (total, and its 15N2O fragment contribution) (a, b, c as S4) | S5a, S5b |
| Fig. S6 | S12 | 1000 ppm H2, N2O, N2, O2 calibration gas in He through the electrolyte (A) | S6b (N2O), S6c (N2) |
| Table S4 | S14 | relative sensitivity factors: H2 0.84, N2 1, NO 1.20, N2O 1.13 | values listed here |
| Fig. S7 | S15 | XPS Ti 2p: CA at -1.0 V vs RHE after 0, 20, 40, 60 min in HNO3/KNO3; pre, exposed and post in 0.1 M HClO4 | no |

The quantification section (S11-S14) gives equations only: signal-to-flux factor, FE, partial current density, the RSF route used for NO, and disk area 0.196 cm2. No FE values, totals or partial currents are reported in the SI.

Conditions throughout: Ti disk, 0.1 M HNO3 + 0.3 M KNO3 (or the 15N analogues as captioned), EC-MS with ixdat analysis and He carrier. Potentials are plotted vs RHE. The SI does not state pH, temperature, cell volume or the 15N isotopic purity.

## What was extracted

| Folder | Figure | Traces | Points per trace |
|---|---|---|---|
| `willoughby2026_figS1c_ecms_14n` | S1c | H2, NO, N2O (mol s-1 cm-2), j, E | 527 |
| `willoughby2026_figS2c_ecms_14n` | S2c | H2, NO, N2O, j, E | 526 |
| `willoughby2026_figS3c_ecms_14n` | S3c | H2, NO, N2O, E | 516-528 |
| `willoughby2026_figS4_ecms_15n` | S4a, S4b, S4c | m/z 30 (a, b only), m/z 31, m/z 46 (pA), j, E | 332-337 (4 for the S4c lower j axis segment) |
| `willoughby2026_figS5_ecms_15n_fragcheck` | S5a, S5b | m/z 15 total and residual, m/z 31 total and 15N2O fragment, j, E | 276-338 |
| `willoughby2026_figS6_ms_calibration` | S6b, S6c | N2O m/z 44, 30, 16; N2 m/z 28, 14 (A) | 299-496 |

Every figure is an embedded raster with no vector paths or text layer. All values therefore come from raster digitization:

- Axes were fitted to located tick marks (residuals under 0.55 px).
- Each pixel column gives one point, the median row of the trace-coloured stroke, with `value_lo`/`value_hi` for the stroke's vertical extent in that column.
- Nothing was smoothed or filled.
- Every point was redrawn on the original image through the inverse calibration and inspected; the overlays are in scratch, not the repo.

`meta.json` in each folder records tick pairs, colours, masks, per-trace flags, pulse schedules taken from the plotted current steps, and derived checks.

Pulse timing read from the j traces is 5 min on / 5 min off with steps near 6, 11, 16, 21 ... min (±0.1-0.25 min). The 15N -0.2 mA/cm2 run is offset by about +0.2 min. The S3c hold runs from 6.05 to 66.05 min.

## Derived checks (computed here, not reported by the authors)

- **Units.** S1c/S2c fluxes integrated per pulse cycle (pulse start to next pulse start) give, at -0.1 mA/cm2 for cycles 1-4, FE of about 32-41% NO, 13-16% N2O and 2-5% H2 (sum 53-57%). Cycle 5 is cut short by the end of the record. At -0.2 mA/cm2 they give 6-25% NO, 9-20% N2O and 2-9% H2 (sum 24-47%, falling with cycle). These are plausible, which supports reading the axis label "Product Concentration (mol/s*cm2)" as molar flux per geometric area.
- **S3c partial currents.** Median fluxes over 15-60 min at -1.0 V vs RHE are NO 1.2e-10, N2O 8.9e-11 and H2 1.2e-10 mol s-1 cm-2. These imply partial currents of about 0.035, 0.069 and 0.023 mA/cm2. Between 10 and 65 min, NO falls to about 40% and N2O to about 33% of its 10-min value.
- **Electrode state differs between runs.** At the same current the 14N and 15N runs sit at different potentials. At -0.1 mA/cm2 both are near -0.8 V vs RHE, but the 14N trace is noisy (-0.6 to -0.9 V, S1c) while the 15N trace is flat at -0.79 V (S4a). At -0.2 mA/cm2 the 14N run sits at a median of -1.45 V with excursions to -0.6 V (S2c), and the 15N run sits at -0.41 V (S4b/S5b). The isotope runs are not replicates of one electrode state.

## Use in a batch kinetic model

What these data can support:

- NO and N2O as transient gas products. Both rise within about a minute of current onset and decay over several minutes after it stops, so the data constrain an NO/N2O escape (stripping) sink and the NO:N2O branch ratio under these conditions.
- HER competition, as H2 flux on the same time base.
- Order-of-magnitude N loss to the gas phase. Per -0.1 mA/cm2 cycle this is about 4e-8 mol NO and 6e-9 mol N2O per cm2.

What they cannot support:

- No liquid-phase concentrations (NO3-, NO2-, NH4+, NH2OH) appear anywhere in the SI, so these runs carry no information on nitrate consumption kinetics or NH3 accumulation. With 0.4 M nitrate and 0.1-0.2 mA/cm2 pulses, depletion during the pulsed runs is negligible; the -1.0 V hold current and the cell volume are not given.
- The signals are outlet fluxes convolved with EC-MS transport (membrane inlet, gas-liquid partition), and the SI gives no instrument response time. Rise and decay constants are therefore upper bounds on the chemistry, not intrinsic rate constants.
- N2 is reported as not detected, but see the doubt below. A model should not treat N2 = 0 as established.
- On acidic Ti the surface changes during operation: XPS shows Ti2+/Ti3+/Ti4+ evolving over 60 min (the authors note these states may partly come from post-reaction air exposure), and the S3c fluxes drift. Any rate constant fitted here is time-dependent.
- The steady current at -1.0 V vs RHE is unreadable (S3c broken axis), so FE at that potential cannot be computed from the SI.
- The 15N traces are raw ion currents, not converted to flux.

## What the main text would add

The main text was not read. Per the abstract (OpenAlex record, read Oct 20 2026), the work combines gas chromatography, ion chromatography and EC-MS to quantify NH4+, H2, NO3-, NO2-, N2O and NO, and reports an average NH4+ FE of 82.3 % at -1.0 V vs RHE. Whether the main text gives concentration time courses is unverified. If it does, they would be the actual batch trajectory for nitrate, nitrite and ammonia, and together with the total current, cell volume and an N balance they would let the S3c gas fluxes act as gas-loss terms in a fitted mechanism. The main text may also state the 15N enrichment and resolve the N2 question.

## Doubts

1. **m/z 30 in the 15N runs is not explained by the SI.**
   - **Observed.** The authors label m/z 30 "15N2 & 15N2O frag." and conclude that only NO and N2O form. At pulse ends, however, m/z 30/m/z 31 = 0.28-0.34 (S4a) and 0.36-0.37 (S4b), and m/z 30/m/z 46 = 2.6-4.4. The 15N2+ fragment of 15N2O should be roughly 0.1 x m/z 46 (NIST N2O m/z 28/44; the SI does not report this ratio). That predicts about 0.6-1.5 pA at m/z 30, against 16-57 pA observed.
   - **Candidate explanations (interpretation, not established).** One is 15N2 formed in step with NO. The other is 14NO from unlabelled nitrate: a 25% 14N fraction gives 14NO/15NO ≈ 0.33, which is the 0.1 M : 0.3 M acid-to-salt ratio, although the caption states H15NO3. The ratio m/z 30/m/z 31 stays nearly constant while m/z 30/m/z 46 drifts, which points to a source tied to NO.
   - **The m/z 15 check is weak.** The authors' own N2 calibration (S6c) gives m/z 14/28 ≈ 0.010-0.012, so 15N2 producing the observed m/z 30 would add only about 0.2 pA (S4a) to 0.6 pA (S4b) at m/z 15. The plotted m/z 15 residuals are about 0-0.1 pA (S5a) and 0.6-0.8 pA (S5b), the latter about what 15N2 would give.
2. **S3c current cannot be read**, and **the 15N -1.0 V run (S4c) is questionable.** S4c shows square-wave O2 and m/z 34 artefacts up to ~1800 pA, a potential glitch at 12.2 min, and a plotted hold current of only about -0.04 mA/cm2.
3. **Near-zero values are not informative.** Off-period traces lie exactly on zero for long stretches, so the authors' baseline-subtracted data appear floored at 0.
4. **Resolution limits.** Time resolution is one pixel column: 0.06-0.18 min, coarser than the EC-MS sampling. Spikes narrower than a column, and anything hidden under another trace or a legend, are lost or flagged.
