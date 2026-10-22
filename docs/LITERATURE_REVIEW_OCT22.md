# Literature checks for the October 22 sensitivity runs

Reviewed October 22, 2026. This is a methodological review, not a record of the new fit results. It uses Daniel's October 21, 22:44 EDT email, the attached Kosuge paper and SI, the local synthesis literature, and the supplied data files. The main decisions are:

- Rerun Chapman with the nominal and early-frame-inferred carbonate amounts, keeping the candidate set and scoring rule fixed. Interpret this as sensitivity to an uncertain input.
- Do not treat the first 10 seconds as isothermal. The cleaner SI extraction fixes visibility, not the heating transient.
- Keep LTOPO endpoints as an example of competing products unless the fit is explicitly labeled as conditional on a restricted model. They do not establish a unique pathway or activation energy.
- Check the LTOPO duplicate-pattern issue below before treating all 58 table entries as independent observations.

## Chapman: what the original paper supports

**Source:** Hu et al. (Chapman group), *Resolving Fast Relative Kinetics in Inorganic Solid-State Synthesis*, JACS 145, 26545-26549 (2023), [main and SI](https://doi.org/10.1021/jacs.3c10916). Local files: `ja3c10916.pdf`, `ja3c10916_si_001.pdf`. Main text and SI methods read; SI Figures S1 and S2 visually inspected.

The prepared mixture is **5:2 TiO2:Li2CO3**, so nominal carbonate is **0.4 formula units per Ti**, and nominal Li/Ti is 0.8. This preparation is stated in SI p. S2. The mixture was pelletized, broken into chunks, and loaded into a capillary. The main text explicitly notes an initial rutile impurity (p. 26546).

The SI heating calibration used a Si/NaCl mixture moved into a zone preheated to 750 C. Its temperature is within 50 K of the target after 6 seconds and within 7 K after 10 seconds (SI p. S4, Fig. S2). This is a calibration of the apparatus, not a measured temperature trace for each reacting sample. The first 10 seconds therefore confound heating and chemical conversion. A cleaner extraction of SI Fig. S1 does not justify applying a constant 700/725/750 C rate from the first plotted instant.

**Consequence for the rerun:** distinguish a source/extraction change, a carbonate-initialization change, and an early-time-window change. Keeping the existing 0.3-minute cutoff isolates the first two. If the cutoff is moved to 0.2 minutes, verify that averaging windows exclude pre-10-second columns. Earlier observations require a measured or explicitly approximate temperature history, or a separately labeled heating sensitivity. Omitting early observations alone does not remove error from integrating a constant-temperature model from insertion at t=0.

The paper's exposures vary from 1 to 30 seconds (SI Table S1). Pixel columns sampled from the plotted curves are not independent instrument observations. The fit should retain the established resampling policy; a denser extracted grid does not justify narrower uncertainty.

### Nominal lithium and lithium inferred from the first frame

The earliest supplied SI CSV row is at **0.05 minutes (3 seconds)**. Calculating carbonate formula units per Ti from that row gives:

| Temperature | Li2CO3 weight % | Li2CO3 per Ti | Li2TiO3 already plotted, weight % |
|---|---:|---:|---:|
| 700 C | 20.45 | 0.276828 | 0.44 |
| 725 C | 21.33 | 0.294804 | 2.92 |
| 750 C | 24.93 | 0.354635 | 0.76 |

Calculation uses the extraction's nominal masses: 73.89 g/mol for Li2CO3, 79.866 for TiO2, 109.75 for Li2TiO3, and 459.08 for Li4Ti5O12. The denominator is total Ti inferred from the four Ti-bearing phases. These numbers reproduce Daniel's approximate 0.28/0.30/0.36 values.

They are **remaining crystalline carbonate inferred at 3 seconds**, not independent measurements of the amount initially weighed. Heating and some conversion have already begun, particularly at 725 C. Use “early-frame-inferred carbonate” for this sensitivity. If initializing at that frame, account for its other phases and shifted time origin; changing carbonate alone at nominal t=0 is a deliberately partial perturbation.

The starting discrepancy is not resolved by the later intermediate's lithium deficiency: the early frame has mostly TiO2 and Li2CO3. Normalization, refinement, phase visibility, or sample/preparation differences remain possible explanations. The supplied phase curves do not discriminate between them.

### Fixed observation mapping and lithium deficiency

The paper reports an intermediate maximum around 52 wt%, above its approximate stoichiometric expectation of 48 wt%, and proposes a TiO2-rich/lithium-deficient intermediate. The printed formula is **Li2−xTiO3−x** (main pp. 26546-26547). It does not measure a unique x or establish the exact defect chemistry. Treat the printed formula as the authors' interpretation, not a refined composition or a charge-balanced network prescription.

Our observed amounts were derived using **fixed nominal molecular masses**. Changing lithium stoichiometry in a candidate while keeping those observed amounts fixed is an approximation. A changed molecular mass changes the weight-to-mole mapping; normalizing to total inferred Ti then changes the other channels too. The nominal Ti closure is imposed by the conversion and is not independent evidence that all material was measured.

**Smallest defensible correction:** report the initial-lithium sweep as input sensitivity under the fixed nominal observation map. Do not call a fitted initial amount a measurement of actual lithium inventory, or a fitted deficiency proof of defect composition. A physically consistent future analysis should fit the original weight fractions with a candidate-dependent observation map and account for unobserved material and normalization.

The authors themselves describe carbonate consumption as coinciding with slowing of the first step (p. 26546), but list microstructure, reaction architecture, and changing intermediate composition as possible explanations for the Avrami-slope transition (p. 26547). A carbonate-limited fit is consistent with this discussion; it does not uniquely identify the cause.

**Extraction-note correction:** recomputing `wt_sum` over the current SI CSV gives **97.55-101.73 wt%**, not the 99.5-101.7 range in its prose metadata. The lowest rows are early observations. This review does not modify that source file or mark the extraction verified.

### Normalized channels and conditional statistical uncertainty

The four observed amounts satisfy `anatase + rutile + intermediate + 5*spinel = 1` to rounding. Across the 20 saved grid times, the largest absolute departures from one are:

| Temperature | Fig. 2 | SI S1 |
|---|---:|---:|
| 700 C | 0.00009 | 0.00007 |
| 725 C | 0.00008 | 0.00006 |
| 750 C | 0.00007 | 0.00007 |

Normalization couples the phase errors. When modeled Ti is entirely represented by these four channels, their residuals have the same weighted linear constraint, up to rounding and numerical integration error. Rounding does not supply a fourth independent physical measurement. A model with hidden Ti instead requires an observation model for the missing fraction.

The unchanged [Gaussian objective](../src/nernstwork/fit.py#L122) sums independent per-channel terms and [profiles four phase noise scales](../src/nernstwork/fit.py#L138), shared across development temperatures; it does not model cross-phase or temporal covariance. The [sample counter](../src/nernstwork/data.py#L69) counts all scalar values: 160 for development (two temperatures, 20 times, four phases), and 80 for 750 C. [AICc uses that count](../src/nernstwork/fit.py#L466). Three composition coordinates per time give at most 120 development coordinates before temporal dependence, **not a corrected effective sample size**. Changing only the AICc sample count would not repair the likelihood.

The results report already labels profiles conditional on the network, extraction, noise model and starting-state policy, and notes poor residual adequacy. The additional qualification is that **AICc comparisons and nominal 95% profile ranges are conditional on an independent-Gaussian working likelihood despite normalization-induced dependence**. The [profile cutoff of delta NLL = 1.92](../src/nernstwork/fit.py#L390) has not been calibrated for these correlated, digitized observations. Numerically resolved profile endpoints therefore do not establish experimental 95% coverage or measured physical composition. No fit, count, score or cutoff was changed by this audit.

The next data request for Daniel is **unnormalized phase estimates or their joint covariance, alongside scan times and exposure windows**. Those would support a covariance-aware observation model; normalized data alone require independent composition coordinates with their covariance and explicit handling of near-zero phases. Absolute crystalline-content calibration is also needed to distinguish missing/amorphous material from the imposed closure. Source hashes, every grid's closure residuals, and actual saved-fit counts are in `data/derived/chapman_li_sensitivity/literature_verification/normalization_likelihood_audit.json`, with its reproducible arithmetic script alongside.

### Independent SI anchor verification during the campaign

All three source panels on SI p. S3 were visually inspected. A separate check rendered that page at 216 dpi, calibrated directly from the printed 0/600-second and 0/80-wt% ticks, and measured the local line-center pixels at 24 predefined phase/time anchors. This check did not call the original extraction code, follow its continuity rules, or normalize the measured fractions. The source CSV averages a wider approximately +/-1.6-second window, so the two checks need not agree exactly on a steep curve.

| Panel | Resolved anchors | Largest absolute difference from CSV | Largest difference for anchors at or after 18 seconds |
|---|---:|---:|---:|
| 700 C | 7 of 8 | 0.41 wt% | 0.41 wt% |
| 725 C | 8 of 8 | 0.31 wt% | 0.31 wt% |
| 750 C | 8 of 8 | 1.06 wt% | 0.50 wt% |

The eight checks per panel cover starting carbonate; intermediate growth, peak, and decay; rutile at 300 seconds; spinel at 570 seconds; and two anatase points. Examples of independent source reading versus CSV:

| Panel | Phase and time | Source reading, wt% | CSV, wt% |
|---|---|---:|---:|
| 700 C | Li2TiO3, 69 s | 54.41 | 54.22 |
| 700 C | rutile, 300 s | 24.52 | 24.54 |
| 725 C | Li2TiO3, 42 s | 55.78 | 55.64 |
| 725 C | spinel, 570 s | 35.24 | 35.20 |
| 750 C | Li2TiO3, 18 s | 55.70 | 55.90 |
| 750 C | spinel, 570 s | 46.34 | 46.56 |

The largest discrepancy is 750 C carbonate at 3 seconds, where a narrow source sample gives approximately 23.87 wt% against the CSV's 24.93 wt% during a steep decline. This point is outside the campaign fitting window. The 700 C anatase curve at 480 seconds could not be resolved separately from the near-zero overlaid lines; its CSV value of 0.52 wt% is not independently verified by this check.

**Scope:** these checks support the selected visible anchor values within about 0.5 wt% in the fitting window. They do not verify every interpolated point, recover hidden lines, establish sub-wt% instrumental accuracy, or validate the physical observation model. The complete per-anchor record is preserved in `data/derived/chapman_li_sensitivity/literature_verification/independent_anchor_checks.json`; the PDF panel renders are alongside it and remain ignored. No input files were changed while fits were running.

### A lithium bound that does not depend on fitted rates

Let `I(t)` and `S(t)` denote observed formula units per Ti for the intermediate and spinel. If the intermediate contains `l` Li per Ti, spinel is Li4Ti5O12, initial carbonate is `c0`, and there is no additional lithium source, nonnegative lithium in all other species requires:

`l*I(t) + 4*S(t) <= 2*c0`.

Thus exact agreement with every observed point requires `l <= min_t[(2*c0 - 4*S(t))/I(t)]`. The table below evaluates all 20 model-grid times, using the fixed nominal observation conversion:

| Temperature | Fig. 2: maximum l, nominal c0=0.4 | Fig. 2: maximum l, lower c0 | SI: maximum l, nominal c0=0.4 | SI: maximum l, lower c0 |
|---|---:|---:|---:|---:|
| 700 C | 1.534 | 0.846 (c0=0.28) | 1.542 | 0.848 |
| 725 C | 1.466 | 0.933 (c0=0.30) | 1.467 | 0.938 |
| 750 C | 1.438 | 1.194 (c0=0.36) | 1.448 | 1.200 |

Equivalently, under the lower initialization, the Fig. 2 curves require `x=2-l` to be at least **1.154, 1.067, and 0.806**, respectively, if a single fixed-composition intermediate must interpolate the data exactly. These are consistency bounds, not measured defect compositions. A composition shared across temperatures must satisfy the tightest bound.

For a fixed **Li1.6** intermediate, the minimum carbonate needed is `max_t[0.8*I(t)+2*S(t)]`: **0.411, 0.428, and 0.432** for Fig. 2; **0.410, 0.427, and 0.430** for the SI. All exceed 0.4. Therefore a fitted initial amount constrained to 0.25-0.4 cannot make that particular observation map and composition match every point exactly. Allowing finite residuals can still produce a fit.

These bounds assume the normalized crystalline fractions represent all Ti, retain nominal molecular masses, fix spinel stoichiometry, and treat the plotted values as exact. Unobserved or amorphous Ti, uncertain phase weights, variable intermediate composition, or a different observation map can invalidate their physical interpretation. Remaining carbonate or an unobserved lithium sink would tighten, not relax, the bound within those assumptions. The robust arithmetic conclusion is that lowering the supplied lithium **increases** the inconsistency under the current mapping; it cannot by itself resolve it.

### Deterministic digitization stress test

A separate arithmetic check perturbed each of the four Ti-bearing crystalline phase weights by **+/-0.5 absolute wt percentage points**, clipped negative values to zero, and evaluated all 16 sign combinations at each of the 20 campaign-grid times. The amplitude is motivated only by the selected, resolved SI fitting-window anchor discrepancies above. It is **not an experimental error estimate, a validated error bound for either extraction, or a confidence interval**. In particular, those SI anchor checks do not calibrate the Fig. 2 extraction.

The primary calculation preserves the converter's order: apply a given phase offset to each CSV row in the original averaging window, use the same nominal molar masses and total-Ti normalization for each row, then average formula-unit amounts. The phase offsets can vary independently between grid times, allowing the most favorable corner at every time. A second calculation averages raw phase weights before perturbing and normalizing; both give the same conclusions. Reconstructing unperturbed amounts from the rounded raw weights differs from the saved campaign amounts by at most 0.000096 formula units per Ti; the CSV separately rounds weight percentages and Ti fractions.

The table reports the **most favorable** whole-curve bounds among the tested offsets, not the unperturbed values:

| Extraction | Temperature | Minimum c0 still required for Li1.6 | Largest intermediate Li/Ti allowed under lower c0 |
|---|---:|---:|---:|
| Fig. 2 | 700 C | 0.40487 | 0.873 (c0=0.28) |
| Fig. 2 | 725 C | 0.42077 | 0.963 (c0=0.30) |
| Fig. 2 | 750 C | 0.42485 | 1.233 (c0=0.36) |
| SI S1 | 700 C | 0.40364 | 0.874 (c0=0.28) |
| SI S1 | 725 C | 0.42051 | 0.967 (c0=0.30) |
| SI S1 | 750 C | 0.42298 | 1.239 (c0=0.36) |

Thus the nominal-c0 and lower-c0 inconsistencies for a fixed Li1.6 intermediate both survive this specified stress test. The smallest nominal margin is only 0.00364 carbonate per Ti, at 700 C in the SI extraction; this test does not establish robustness to larger digitization biases or to any change in the physical observation assumptions. The intermediate bounds under lower c0 also remain below 1.6, even after favorable offsets. No observations or fits were changed.

The reproducible arithmetic script, source-file SHA256 hashes, all 16 corner offsets, each time's source weights and computed amounts, and both aggregation variants are recorded in `data/derived/chapman_li_sensitivity/literature_verification/digitization_li_stress.py` and `digitization_li_stress.json`. This check includes the 750 C curves as a retrospective consistency diagnostic; it is not new held-out validation.

## Kosuge: useful rate-law candidates, with a different inference contract

**Source:** Kosuge et al., *Reaction Modeling of the Rapid Two-Step Oxidation Process Assisted by Bayesian Inference with Isothermal Time-Resolved X-ray Diffraction Measurements*, JPCC 130, 10245-10250 (2026), [main and SI](https://doi.org/10.1021/acs.jpcc.6c02717). Retrieved from [Daniel's email](https://mail.google.com/mail/u/?authuser=jarrod%40dynamicalsystems.ai#all/1a1617f7ec459da1), attachments `acs.jpcc.6c02717.pdf` and `jp6c02717_si_001.pdf`; main and SI inspected, Table 1 visually checked.

At 400 C, the experiment observes SrCrO2.75 → SrCrO2.8 → SrCrO3 at 12-ms resolution. The analysis assumes the two stages proceed independently, rescales each stage to monotonic progress alpha from 0 to 1, and compares nine preselected kinetic shapes. It accounts for an initial approximately 20 wt% SrCrO2.8 by using loss of SrCrO2.75 for stage one and growth of SrCrO3 for stage two (pp. 10246-10248). It favors 3D contraction for the first stage and first-order kinetics for the second. This is not a learned joint reaction network.

The fitted functions are **integrated** laws, `g(alpha)=k*t`. D2-D4 are inverted numerically by bisection. The corresponding differential network law, when its assumptions hold, is `dalpha/dt=k/g'(alpha)`:

| Model | Published g(alpha) | Differential multiplier, `(dalpha/dt)/k` |
|---|---|---|
| R2 | `1-(1-alpha)^(1/2)` | `2*(1-alpha)^(1/2)` |
| R3 | `1-(1-alpha)^(1/3)` | `3*(1-alpha)^(2/3)` |
| F1 | `-ln(1-alpha)` | `1-alpha` |
| D1 | `alpha^2` | `1/(2*alpha)` |
| D2 | `(1-alpha)*ln(1-alpha)+alpha` | `1/[-ln(1-alpha)]` |
| D3 | `[1-(1-alpha)^(1/3)]^2` | `3*(1-alpha)^(2/3)/{2*[1-(1-alpha)^(1/3)]}` |
| D4 | `1-2*alpha/3-(1-alpha)^(2/3)` | `3/{2*[(1-alpha)^(-1/3)-1]}` |

All four diffusion multipliers are singular at alpha=0. A small starting extent or time offset requires a sensitivity check; it is an added numerical/model assumption, not validation from this paper. For coupled pathways, alpha must describe a reaction's progress or capacity, not simply an intermediate phase abundance that can later decrease. Finite conversion bounds and reactant availability also need enforcement.

The authors use uniform priors on **1/k**, with model-dependent ranges that prevent bounded integrated models from reaching completion too early (SI Table S1). Their posterior model probabilities therefore cannot be carried over to an AICc ranking with other parameter bounds. The paper also explicitly limits conclusions to the supplied candidate set (p. 10249).

SI Figures S12-S13 show that measurement position and gas-introduction rate alter induction delays. Figure S16 supports nearly constant temperature for the selected experiment. These controls reinforce the need to distinguish apparatus delays from chemistry.

## Kamm: test packing and a resolved slow regime separately

**Source:** Kamm et al., *Relative Kinetics of Solid-State Reactions: The Role of Architecture in Controlling Reactivity*, JACS 144, 11975-11979 (2022), [main and SI](https://doi.org/10.1021/jacs.2c05043). Local files `ja2c05043.pdf` and `ja2c05043_si_001.pdf`; main, experimental methods, and phase-field assumptions inspected.

The NaFeO2/LiBr study changes packing from about 25% to 85%. Heating takes **53 seconds**, and diffraction exposures are **90 seconds**. The densified sample already contains about 1 wt% NaBr before heating (SI pp. S2-S3).

The paper fits **only the slow regime, t>3 minutes**, using `C(t)=k*sqrt(t)+C0` (main p. 11976; SI p. S4). Its intercept represents unresolved fast progress; it differs by approximately 0.4 between packing conditions. The slow-regime slope is similar between packing conditions and **slightly decreases with increasing temperature**. Thus this is not immediate support for a single positive-activation-energy diffusion law from unreacted t=0.

A useful follow-up is a prespecified slow-regime fit with packing-dependent offsets, followed by a separate test of a fast/slow population model. Do not treat C0 as the initially weighed converted fraction or infer fast-stage rates that the exposure schedule did not resolve. The phase-field simulations support qualitative architecture effects under simplifying transport assumptions; they are not additional physical measurements.

## LTOPO: endpoints, an unresolved duplicate, and a better kinetic source

**Sources:** Szymanski et al., *Autonomous and dynamic precursor selection for solid-state materials synthesis*, Nature Communications 14, 6956 (2023), [main and SI](https://doi.org/10.1038/s41467-023-42329-9); local `ExpLTOPO.json` and `SettingsLTOPO.json`. Main methods/results, SI benchmarking design, and raw table inspected.

The local table contains 58 entries across 15 precursor sets. Four temperatures are listed (400/500/600/700 C), with 15/15/14/14 entries respectively. All are flagged experimentally verified and contain XRD arrays. Target phases appear in all 14 entries at 700 C and none below it; 10 of those 14 contain both structure labels. The file specifies **20 C/min heating, natural cooling, air**. The paper specifies a **4-hour hold**; that duration is not stored per row.

These are separate synthesis endpoints after ramp, hold, and cooling. They are not successive observations of the same sample. A single endpoint at each temperature can support conditional estimation in a very small, fixed model with known starting states and observation mapping. It does not generally identify reaction order, branching, induction time, or a unique network. Here the target is positively measured at only one temperature; unspecified detection limits below 700 C do not provide a well-resolved target-formation activation energy.

For any endpoint fit, preserve the two polymorph labels, use explicit precursor stoichiometry and measured protocol, model the weight-fraction observation basis, group by precursor set for validation, and test identifiability before reporting activation energies. A schema change permitting one observation time is necessary for representation but does not solve these inference limits.

### Table integrity issue found in this review

The table has **57 unique XRD arrays for 58 entries**. These two 700 C rows contain exactly the same 8,301 x values and 8,301 y values:

- `Li2TiO3, PH6NO4, TiO2`: reported `LiTiPO5_2` / `LiTiPO5_62` weights **23 / 8**.
- `Li2TiO3, PH9(NO2)2, TiO2`: reported corresponding weights **36 / 10**.

Both are marked `Experimentally Verified: true`. Exact equality was checked over the complete parsed XRD objects, not rounded plots. The duplicated pattern has SHA256 `2fea70dd5190b334e3fb8a0e09719e31194a051a613cc8a08b675fa52f8d75ac`, calculated from `json.dumps(XRD, sort_keys=True)`. Do not count these rows as independent pattern evidence or split them between train and test. Retain both provenance records and reconcile the source before choosing a corrected yield.

There is also a paper/table discrepancy: the main-text optimized `Li2O + TiO2 + P2O5` example reports 54% target before the ball-milling improvement, while the local corresponding table row contains 40% `LiTiPO5_2`. This review does not establish why. Report computed table results as results from this supplied version, not as a reproduction of the paper's campaign outcomes.

ARROWS3 already uses intermediate-phase evidence and pairwise reaction reasoning to guide precursor selection. The paper also calls its peak-intensity weight fractions approximate and says Rietveld refinement would be required for precision (Methods, pp. 10-11). A mechanistic network fit should not assume these are exact concentrations.

### A separate LTOPO paper has actual time-resolved observations

Zeng et al., *Selective formation of metastable polymorphs in solid-state synthesis*, Science Advances 10, eadj5431 (2024), [paper](https://doi.org/10.1126/sciadv.adj5431), is already in Daniel's ZIP as `sciadv.adj5431.pdf` with `sciadv.adj5431_sm.pdf`.

The main text's Figures 3B/D track two precursor routes at **25 C/min to 700 C followed by a 3-hour hold**, with 15-second diffraction acquisition (pp. 4-7). For one route, triclinic LTOPO forms first and converts to orthorhombic material during the 700 C hold with an S-shaped curve. For the other, low-temperature intermediates change the route. This is a more appropriate future source for a kinetic LTOPO case than assigning unobserved time courses to ARROWS3 endpoints.

**Not ready for direct kinetic fitting:** visual inspection of Fig. 3 shows weight percent on the horizontal axis and a shared temperature axis vertically, with 700 C repeated over the hold segment but no elapsed-time ticks. The paper's hold duration and acquisition interval do not establish the plotted pixel-to-time mapping. Obtain the underlying scan/time mapping before treating digitized points as measured time courses. The caption describes peak-intensity estimates whereas the methods discuss Rietveld refinement; clarify the provenance of these particular curves. The SI contains additional diffraction controls but no numerical phase-fraction time table was found in its extracted text.

Do not combine the two studies as interchangeable experiments: the Zeng samples were ball-milled for 20 hours, partially reacted or amorphized before heating, and had a different ramp and hold. In Zeng's first route, initial amorphous phase amounts are assigned from nominal stoichiometry, assuming CO2 loss during milling; they are not measured crystalline fractions (p. 4). Its target can form below 700 C. Therefore “target only at 700 C” must always be qualified as **in the supplied ARROWS3 table**.

## Related methods and presentation boundary

Macchietti et al., *Scaling up mechanochemical reactions: linking crystalline phase evolution studied via in situ PXRD with kinetics from MCR-ALS*, Chemical Science 17, 12047-12054 (2026), [main and SI](https://doi.org/10.1039/d6sc01158f), provides a relevant observation-model warning. It imposes kinetic equations within the diffraction decomposition; SI section 4 explicitly discusses rotational and intensity ambiguity. Such kinetically constrained concentration curves are not an independent benchmark for rediscovering the same kinetic model. Its reported raw-data archive is [Zenodo 18596362](https://doi.org/10.5281/zenodo.18596362); the archive itself was not inspected in this review.

The video can show measured curves, a fixed-model prediction at a new temperature, and how that conclusion changes under lithium sensitivity. Show a selected model's result, not only the best candidate found after reading the held-out outcome. Treat proposed experiments as proposals, alternative mechanisms as hypotheses, and LTOPO branching as observed endpoint coexistence unless a time-resolved fit is separately completed. These papers do not establish a measured synthesis-to-NO3RR performance link.

## Provenance and scope

The existing synthesis PDFs and ARROWS files were read under `/home/jarrodbarnes/nernstwork-inbox/daniel_literature_synthesis_2026-10-21/extracted/literature/04_synthesis/`. The Kosuge attachment PDFs, extracted text and message provenance are preserved under `/home/jarrodbarnes/nernstwork-inbox/daniel_kosuge_2026-10-22/`; temporary render intermediates are in `/tmp/nernstwork-literature-oct22/`. Copyrighted PDFs were not added to the repository. Publisher web requests were blocked, so the supplied full PDFs are the primary evidence for this review.

- Kosuge main PDF SHA256: `2403a3cd5bf9d97714aca782298e581db968b3c30a39fc8765854a1621ca335f`.
- Kosuge SI PDF SHA256: `8e9f3b1f23a74e947bbf5fad1854be1a8812e536b054bea1f1a6a4375c1e6b28`.
- Supplied `ExpLTOPO.json` SHA256: `2fd8f33c853fbca86081eb7a747a02ee51b4a8cfd1cfe598bef72786e971410a`.

No fit was executed or approved by this review. No source data, extraction metadata, experiment artifacts, or email were changed.
