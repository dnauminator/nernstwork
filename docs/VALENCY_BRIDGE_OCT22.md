# Valency search: catalyst synthesis to NO3RR performance

Run October 22, 2026, at Daniel's request, as the Valency counterpart to the OpenAlex pass (`scripts/openalex_citation_pass.py`, PROGRESS section 2e). Discovery used only the Valency plugin. OpenAlex and Europe PMC were then queried read-only to check open-access status, citation overlap with the OpenAlex seeds, and table captions; they were not used to find papers. Unless a row says "full text" or "SI", every claim below comes from the abstract that Valency returned. Nothing was read in full. The SIs of Lim 2023 and Wang J. 2025 were checked later the same day for NO3RR time courses (section c).

## Verdict

Valency returned no dataset that tabulates catalyst synthesis conditions (precursor, calcination or annealing temperature, phase fractions) against NO3RR performance across more than a handful of conditions; the closest, Lim et al. 2023, varies PdCu annealing temperature (200–600 °C) to set the FCC/BCC ratio and compares three catalysts for NO3RR selectivity, with the numbers in text, figures and SI rather than in a table. Our engine could use such data only after digitizing several small series from different labs and electrolytes, which would support a labelled, illustrative synthesis-to-NO3RR link but not a fitted one.

## (a) Tools and queries

**Corpus.** `list_sources`: PubMed (41.2 M), arXiv (4.95 M), bioRxiv, medRxiv, PsyArXiv, ChemRxiv (57 k), SocArXiv, EarthArXiv and Valency Hub. Journal papers are in Valency only through PubMed or a preprint. Two papers already in SPEC 7e are absent: `search_by_title` finds neither Kosuge et al. 2026 (J. Phys. Chem. C) nor Karan and Persson 2026 (Chem. Mater.). One Appl. Catal. B paper appears only through its arXiv record. Valency alone would have missed the closest prior art we already know.

| Tool (skill) | Query or seed | Result |
|---|---|---|
| `semantic_search_papers` | calcination temperature → catalyst phase → NO3RR FE (30) | NiCo2O4 heating-rate paper, FeOOH polymorphs, TiO2 polymorphs |
| `semantic_search_papers` | catalysts annealed at different temperatures, NO3RR (40) | Cu/C pyrolysis series, CuNi/NC, IE-Cu-400 |
| `semantic_search_papers` | anatase vs rutile TiO2, Ti3+, NO3RR (30) | Wang 2025 TiO2/Cu2O; TiO2-x nitrite papers; Fe2TiO5 |
| `semantic_search_papers` | ordered intermetallic vs disordered CuPd, annealing (30) | Lim 2023 (published version and ChemRxiv preprint); Gao 2022 seed; AuCu3, CuZn intermetallics |
| `semantic_search_papers` | reviews tabulating synthesis vs NO3RR FE (40) | mostly reviews; Bai 2025 Adv. Sci. has the best table |
| `semantic_search_papers` | spinel composition series (30); perovskite A/B-site series (30) | Hu 2023 JACS, Yan 2023 Small, Zheng 2022 Small, Chu 2023 JACS |
| `semantic_search_papers` | ML on literature NO3RR + synthesis data (30) | Rosser NRR dataset (seed), Hu 2024 CuCo ML synthesis, Hossain 2026 thermocatalytic dataset |
| `semantic_search_papers` | high-throughput / combinatorial NO3RR libraries (25) | almost all OER/ORR; one NO3RR composition series (Filagrossi 2026) |
| `semantic_search_papers` | Li-containing oxide or lithium titanate NO3RR catalyst (25) | none; Ti hydride, Ti-N-C, Fe2TiO5 only |
| `semantic_search_papers` | precursor salt choice → phase → NO3RR (25); thermal-reduction Cu/Cu2O/CuO fractions (25) | Du 2025 JACS precatalysts, Takashima 2025, Cu2O facet papers |
| `semantic_search_papers` | in situ XRD during catalyst synthesis, then NO3RR (25) | none; only operando studies during electrolysis |
| `semantic_search_papers` | solid-state / ball-milled oxide as NO3RR catalyst (25) | BiFeO3, ferrites, mechanochemical MOF; no systematic synthesis series |
| `search_by_abstract` | `electrocatalytic nitrate ammonia "calcination temperature"`, `"annealing temperature"`, `"pyrolysis temperature"` (30–40) | each warned "keyword search returned insufficient results" and fell back to semantic search |
| `search_by_abstract_batch` | 10 keyword variants (calcination, annealing, precursor, spinel, perovskite, intermetallic, titanate, Li4Ti5O12, solid-state, phase transformation) | noisy; the Li4Ti5O12 and titanate variants returned battery and electrolyte papers, none on NO3RR |
| `find_similar_papers` (similar) | seeds 39388946, 37969250, 41556456, 39879777 (15 each) | neighbours are catalyst-design papers; no new synthesis series |
| `get_citing_papers` | Chapman 2023 (38019924) | 15 citing works in the citation graph, none on NO3RR |
| `get_keyword_trends` (trends) | see below | thermal synthesis steps are rarely mentioned in NO3RR abstracts |
| `export_papers_json`, `get_paper_by_id` | about 35 candidates | abstracts used for the table below |

**How often abstracts name a thermal step.** Valency abstract-word counts (words matched, not phrases; 2026 runs to Oct 21): `nitrate ammonia electrocatalyst` 524 papers from 2020 to 2026; adding `calcination` leaves 4, `annealing` 2, `pyrolysis` 11. About 3% of these abstracts mention a thermal synthesis step at all. A keyword search over abstracts therefore cannot find synthesis-series papers. Semantic search did better, but anything that varies temperature only in the methods or SI is invisible at the abstract level.

**The landscape and reading-list skills were not run as written.** Reading-list is anchored on a researcher, and landscape gives a field overview. Neither answers "which paper has both variables".

## (b) Ranked bridging papers

Ranking: (1) a thermal or precursor synthesis variable is varied and NO3RR is measured for each condition; (2) a synthesis-controlled phase or composition series with NO3RR for each member. Columns:

- **Tabulated** is what I checked, not what the paper may contain.
- **OA** is the OpenAlex `oa_status`, or the Europe PMC licence where a PMC copy exists.
- **Seed** asks whether the paper cites either NO3RR seed of the OpenAlex pass, Gao 2022 (`W4225114738`) or Rosser 2024 (`W4389257289`), according to OpenAlex `referenced_works`. "No" means the forward-citation pass could not have reached it from those seeds.

| # | Paper | DOI | Synthesis variable | NO3RR result (abstract unless marked) | Tabulated | OA | Seed |
|---|---|---|---|---|---|---|---|
| 1 | Lim et al., ACS Energy Lett. 2023 ([PubMed 37969250](https://pubmed.ncbi.nlm.nih.gov/37969250/); preprint [chemrxiv-2023-2m2l5](https://doi.org/10.26434/chemrxiv-2023-2m2l5)) | 10.1021/acsenergylett.3c01672 | Annealing of disordered PdCu/C at 200–600 °C sets the FCC/BCC ratio F/B: 0 as made, 0.76 at 500 °C, 0.96 at 600 °C, by XRD (full text) | Ordered PdCu: 91% N2, 94% removal, 480 h stable. Disordered: 44% N2 and 49% NH4+, with 10× more Cu loss. The product of interest is N2, not NH3 | No main-text tables. Product splits are bar charts (Fig. 2d–g) for the as-made and 500 °C samples only; the 600 °C sample has LSV and partial current only. The 200–400 °C samples have XRD only (SI Fig. 1). The SI tabulates ICP composition, ECSA and Pd/Cu leaching per catalyst | Yes, CC BY (PMC10644382) | No |
| 2 | Zhang P. et al., Small 2026 ([41556456](https://pubmed.ncbi.nlm.nih.gov/41556456/)) | 10.1002/smll.202513666 | Pyrolysis temperature moves Cu on N-doped carbon from single atoms to nanoparticles | Mixed single-atom + nanoparticle sample: NH3 FE 98.6%, 11.8 mg h⁻¹ cm⁻² at −0.3 V_RHE, acidic | Not checked | Bronze | No |
| 3 | Xu S. et al., J. Colloid Interface Sci. 2024 ([39388946](https://pubmed.ncbi.nlm.nih.gov/39388946/)) | 10.1016/j.jcis.2024.10.012 | Calcination heating rate sets surface O-vacancy content of NiCo2O4 | 5 °C/min sample: FE 94.4%, 193.2 mmol h⁻¹ g⁻¹; more vacancies, less nitrite | Not checked | Hybrid | No |
| 4 | Ma A. et al., Chem. Commun. 2026 ([42485089](https://pubmed.ncbi.nlm.nih.gov/42485089/)) | 10.1039/d6cc02673g | Gradient pyrolysis temperature of MOF-derived Cu/C; Cu/C-700 best | No numbers in the abstract | Not checked | Closed | No |
| 5 | Ji X.-Y. et al., Nano-Micro Lett. 2023 ([37121962](https://pubmed.ncbi.nlm.nih.gov/37121962/)) | 10.1007/s40820-023-01091-9 | Cu loading on N-doped TiO2/C from MOFs@CuPc precursors plus pyrolysis gives single atoms, clusters or nanoparticles | Restructured CuN4&Cu4: FE about 94.3%, 88.2 mmol h⁻¹ g⁻¹ at −0.75 V | No main-text tables (PMC) | Yes, CC BY | No |
| 6 | Babaei A. et al., Sci. Rep. 2025 ([41392211](https://pubmed.ncbi.nlm.nih.gov/41392211/)) | 10.1038/s41598-025-32713-4 | Sb:Cu precursor ratio, five compositions by sol-gel; all calcined at 600 °C; CuSb2O6 goes from α to β (full text) | CuSb2Ox: FE 89%, 7280 µg h⁻¹ cm⁻² at −0.7 V | Composition (ICP/EDS) and EIS tabulated per catalyst; FE per composition not in a main-text table | Yes, CC BY-NC-ND | No |
| 7 | Qin L. et al., Small 2026 ([41996079](https://pubmed.ncbi.nlm.nih.gov/41996079/)) | 10.1002/smll.73420 | Metal pair (Cu/Co/Ni), Cu precursor, and Co-MOF ligand | Cu1Co5: FE 97.53% at −1.0 V; 22.3 mg h⁻¹ mg⁻¹ at −1.1 V | Not checked | Closed | No |
| 8 | Hong M. et al., Sci. Total Environ. 2022 ([35257778](https://pubmed.ncbi.nlm.nih.gov/35257778/)) | 10.1016/j.scitotenv.2022.154349 | Electrodeposition plus annealing ("IE-Cu-400"); CuO precatalyst reduces to Cu | Nitrate removal rate 3.38× and NH4+ selectivity 1.36× versus conventional Cu electrodes | Not checked. That "400" is the annealing temperature is an inference from the name | Closed | No |
| 9 | Wang J. et al., J. Hazard. Mater. 2025 ([39879777](https://pubmed.ncbi.nlm.nih.gov/39879777/)) | 10.1016/j.jhazmat.2025.137174 | TiO2 polymorph (rutile vs anatase) in TiO2/Cu2O. SI Fig. S4: TiO2 calcined at 700 °C is anatase, at 800 °C mixed, at 900 °C rutile | R-TiO2/Cu2O: 99.8% removal in 180 min, 0.23 mmol h⁻¹ cm⁻², FE 85.7%, neutral | SI Table S2: rutile vs anatase NH3 yield 2.3 vs 1.1 mol h⁻¹ m⁻², FE 85.7 vs 67.0% at −0.5 V_RHE | Article closed; SI free from Elsevier | No |
| 10 | Qu K. et al., Small 2024 ([38429245](https://pubmed.ncbi.nlm.nih.gov/38429245/)) | 10.1002/smll.202401327 | Four FeOOH polymorphs (δ, γ, α, β) | δ: FE 90.2% at −1.0 V; 5.73 mg h⁻¹ cm⁻² at −1.2 V | Not checked | Bronze | Yes (Gao) |
| 11 | Hu Q. et al., JACS 2023 ([38155548](https://pubmed.ncbi.nlm.nih.gov/38155548/)) | 10.1021/jacs.3c06904 | Cu content in (CuxCo1−x)Co2O4; activity follows a volcano against the electronic structure of octahedral Co | x = 0.6: FE 96.5%, 1.09 mmol h⁻¹ cm⁻² at −0.45 V, 1 M KOH | Not checked | Closed | No |
| 12 | Zheng H. et al., Small 2023 ([36449575](https://pubmed.ncbi.nlm.nih.gov/36449575/)) | 10.1002/smll.202205625 | LaBO3 with B = Cr, Mn, Fe, Co (cubic, orthorhombic, hexagonal) | Activity order Cr < Mn < Fe < Co matches the O-vacancy order | Not checked | Closed | No |
| 13 | Chu K. et al., JACS 2023 ([37728869](https://pubmed.ncbi.nlm.nih.gov/37728869/)) | 10.1021/jacs.3c06402 | LaFe0.9M0.1O3 (M = Co, Ni, Cu), electrospinning plus calcination | M = Cu: 349 ± 15 µg h⁻¹ mg⁻¹, FE 48 ± 2% | No main-text tables (PMC) | Yes, CC BY | No |
| 14 | Cao Q. et al., Small 2025 ([41099229](https://pubmed.ncbi.nlm.nih.gov/41099229/)) | 10.1002/smll.202508642 | Ni5P4 vs Ni2P vs NiP2 | Ni5P4: FE 97.6%, NH4+ selectivity 97.7% at −0.4 V | Not checked | Closed | No |
| 15 | Du J. et al. (Buonsanti), JACS 2025 ([40983864](https://pubmed.ncbi.nlm.nih.gov/40983864/)) | 10.1021/jacs.5c09246 | Cu and Cu-oxide nanocrystal precatalysts varied in size, shape and oxide content | Higher oxide content and an optimal {111}/{100} ratio favour NH3; Cu–S10 gives 1064 mmol g⁻¹ h⁻¹ at −0.4 V (full text) | No main-text tables; SI Tables S1–S3 (literature comparison, crystallite size, ECSA) not opened | Yes, CC BY | No |
| 16 | Yin H. et al., Nano Lett. 2023 ([38071625](https://pubmed.ncbi.nlm.nih.gov/38071625/)) | 10.1021/acs.nanolett.3c03962 | Cu single-atom fraction (all single atoms, then mixed, then nanoparticles) | Single atoms: FE 100%, 7480 µg h⁻¹ mg⁻¹. NH3 FE falls and N2/N2O rise as the single-atom fraction falls | Not checked | Closed | No |

**Also returned, weaker as bridges** (abstract only):

- Crystal-phase series without a thermal variable:
  - Xiong et al., Adv. Mater. 2024: 2H vs fcc Cu shells. Doi 10.1002/adma.202407889; cites Gao.
  - Wang Y. et al., Angew. 2025: hcp/fcc CuNi. Doi 10.1002/anie.202508617.
  - Shen et al., J. Hazard. Mater. 2023: amorphous vs crystalline Cu. Doi 10.1016/j.jhazmat.2022.130651; cites Gao.
  - Yan et al., Small 2023: spinel A-site substitution, NiCo2O4 FE 99.89%. Doi 10.1002/smll.202308617.
- Precursor state:
  - Takashima et al., Chem. Asian J. 2025: Cu2O(100) vs Cu2O(111) precursors. Doi 10.1002/asia.202401796; cites Gao.
  - Anastasiadou et al., ChemRxiv 2022: the same comparison on electrodeposited Cu2O. Doi 10.26434/chemrxiv-2022-w6vr8.
  - Yuan et al., ACS AMI 2021: oxide-derived Cu made by annealing Cu foil in O2. Doi 10.1021/acsami.1c10946.
  - Guo et al., ACS Nano 2024: high-temperature-quenched Cu with Ir. Doi 10.1021/acsnano.4c05772.
- Du H. et al., Angew. 2023: Fe2TiO5 pseudobrookite nanofibres, FE 87.6% (doi 10.1002/anie.202215782). This is the only Ti-containing ternary oxide NO3RR catalyst that came up. It is a single composition, and no Li-Ti-O or Li4Ti5O12 NO3RR catalyst was returned.
- Filagrossi et al., Materials 2026 (doi 10.3390/ma19143122; OA, CC BY): electrodeposited Co-Ni-Cu films with deposit compositions and product analyses in tables (PMC full text). This is the most table-ready composition-to-product data found, but the synthesis is electrodeposition, not thermal.
- Hu Y. et al., ACS AMI 2024 (doi 10.1021/acsami.4c14956; arXiv 2408.00142, green OA): a multilayer perceptron guides the synthesis parameters of CuCo solid-solution alloys, reaching about 100% FE. The abstract does not say whether the training data include NO3RR outcomes or only alloy formation. Not verified.

**Reviews and datasets (category 3):**

| Paper | DOI | What is tabulated | OA | Seed |
|---|---|---|---|---|
| Bai J. et al., Adv. Sci. 2025 ([40698414](https://pubmed.ncbi.nlm.nih.gov/40698414/)) | 10.1002/advs.202508614 | "The NO3⁻RR performance of various catalysts": about 42 rows with catalyst, **synthesis method**, electrolyte, yield, FE, products and detection method (PMC full text). Synthesis is a coarse label such as "Hydrothermal and annealing" or "NaBH4 reduction", with no temperatures or precursors | Yes, CC BY | Yes (Gao) |
| Wang M. et al., J. Hazard. Mater. 2026 ([41691897](https://pubmed.ncbi.nlm.nih.gov/41691897/)) | 10.1016/j.jhazmat.2026.141470 | Phase-engineering review across six material classes (phase transitions, metastable phases, heterostructures). Tables not checked | Closed | Yes (Gao) |
| Bayode et al., ACS Omega 2024 ([38737083](https://pubmed.ncbi.nlm.nih.gov/38737083/)) | 10.1021/acsomega.4c01487 | Perovskite syntheses for NO3RR. The only main-text table lists advantages and disadvantages of synthesis routes; there is no performance table | Yes, CC BY | No |
| Lin P. et al., Nanoscale 2024 ([39240163](https://pubmed.ncbi.nlm.nih.gov/39240163/)) | 10.1039/d4nr02852j | Ti-based catalysts for electrochemical NH3 synthesis. Not checked | Closed | No |
| Pathak et al., ChemRxiv 2024 | 10.26434/chemrxiv-2024-9h3mn | Best practice for measuring NO3RR activity, selectivity and FE. Explains why numbers from different papers are not directly comparable | Yes (preprint) | n/a |
| Hossain et al., ES&T 2026 ([42208054](https://pubmed.ncbi.nlm.nih.gov/42208054/)) | 10.1021/acs.est.6c02715 | Multitask Gaussian process on a literature-curated dataset of Pd- and Pt-based catalytic nitrate reduction (H2-driven, not electrochemical). The abstract does not say whether synthesis variables are features | Closed | No |

**Overlap with the OpenAlex pass.** I checked 30 of the papers listed above in OpenAlex. Yuan 2021 was not checked, and three ChemRxiv DOIs did not resolve. Of the 30, 6 cite Gao 2022 and none cite Rosser 2024. The other 24 could not have entered the forward-citation pool from those seeds. They are all in OpenAlex; the difference comes from the search method (topic search instead of forward citation), not from coverage. I could not diff against Daniel's output list: `openalex_citing_works.json` is not in the repository.

## (c) Verdict and what the engine could use

The two-sentence verdict is at the top. The usable material is a handful of small series, led by:

- Lim 2023: annealing temperature → F/B phase ratio → N2/NH4+ selectivity; 3 conditions; OA.
- Zhang P. 2026: pyrolysis temperature → Cu dispersity → FE.
- Xu 2024: calcination heating rate → O vacancies → FE.

Each would have to be digitized from figures or SI.

One kind of data our engine could fit: batch NO3RR time courses (nitrate, nitrite and ammonia against time) measured on catalysts from different synthesis conditions. Fitting those would give NO3RR rate constants for each synthesis condition, the same fit the engine already runs on the W1–W5 worlds.

**Checked October 22, Lim 2023 and Wang J. 2025.** Neither paper gives such curves for more than one synthesis condition.

**Lim 2023: no within-run time courses.** Main text, SI and figure images checked; the SI came from the PMC open-data bucket, `PMC10644382.1/nz3c01672_si_001.pdf`.

- Every product measurement is a 24 h endpoint: 100 ppm NO3⁻-N in 0.05 M Na2SO4, analysed by nitrogen mass balance.
- Fig. 2d and 2f give conversion and the N2/NH4⁺/NO2⁻ split at −0.1, −0.3, −0.5 and −0.7 V_RHE for the as-made and 500 °C samples only.
- Fig. 2e and 2g give the same endpoints over 20 repeated 24 h cycles. For the disordered catalyst they drift: NH4⁺ selectivity goes 34% → 49% → 18% and N2 goes 55% → 44% → 79%, while Cu leaches (547 vs 42.3 ppb, SI Table 3). That is a slow record of the catalyst changing, sampled once a day, not reaction kinetics.
- SI Supp. Fig. 5 is current against time, not concentrations.
- By eye, the −0.5 V conversion in Fig. 2d reads about 87–88%, while the text gives 98% for that condition, matching cycle 1 of Fig. 2e. Check this before digitizing.
- The SI methods say heat treatments ran "from 200 to 500 °C", but SI Fig. 1 and the main text include 600 °C.

**Wang J. 2025: one fit-ready time course, for one catalyst.** The SI is freely downloadable from Elsevier (`1-s2.0-S030438942500086X-mmc1.docx`); the main text is paywalled and was not seen.

- SI Fig. S18 plots NO3⁻-N, NO2⁻-N and NH4⁺-N (mg N L⁻¹) at 0, 30, 60, 90, 120, 150 and 180 min, with error bars, for R-TiO2/Cu2O only, starting from 50 mg N L⁻¹ in 1 M Na2SO4. The caption does not give the potential.
- By eye at 180 min: NH4⁺ is about 45, NO3⁻ and NO2⁻ are each below 1, and nitrite peaks near 2 at 30 min. About 4 mg N L⁻¹ is unaccounted for, which the authors treat as N2 (SI Text S5).
- This has the same three-species structure as the W1–W5 worlds and could be digitized and fitted directly.
- The SI has no time course for A-TiO2/Cu2O. The anatase sample appears only in endpoint numbers (Table S2) and in chronoamperometry current traces (Fig. S12, five potentials for 3 h each).
- SI Fig. S4 shows the polymorph is set by calcination temperature: by peak positions (anatase 101 at about 25.3°, rutile 110 at about 27.4°), TiO2 calcined at 700 °C is anatase, at 800 °C mostly rutile with some anatase, and at 900 °C rutile. The reference-stick legend in that figure appears to have the anatase and rutile labels swapped relative to the stick positions.
- The SI does not say which calcination temperatures made the A and R samples. The main text does (section 2.1.2, checked Oct 22 from the article Daniel sent): R-TiO2 was calcined at 900 °C and A-TiO2 at 700 °C, each for 3 h at 5 °C/min.

**Digitized and fitted (October 22).** Fig. S18 is now `data/real/wang2025_figS18_rtio2cu2o.json` (mM-N, error bars as per-point sigma where readable, not yet verified against the figure). A fit of the `liao_core` nitrate networks prefers NO3⁻→NO2⁻→NH4⁺ with 9% of nitrate going to an unmeasured sink and a ~10 min start-up lag. Rate constants, the significance of the missing N and the caveats are in `docs/examples/wang2025_figS18/README.md`.

**Main article checked (Oct 22).** It has no anatase time course either. Its only time course is the rutile one in SI Fig. S18; the anatase catalyst appears as endpoints at five potentials (Fig. 3e NH3 FE, Fig. 3f NO3⁻ conversion). By eye at −0.5 V: conversion about 98% (R) vs 85% (A), NH3 FE about 79% vs 71%. The electrolysis time for those endpoints is not stated in the methods paragraph.

**What this means.** Wang 2025 is the closest thing found to the target data: a calcination temperature (700 vs 900 °C) sets the TiO2 polymorph, the same anatase/rutile pair as Chapman's precursors, and the rutile catalyst has a three-species NO3RR time course. A fitted synthesis-to-rate-constant pair would need the anatase time course, which neither the article nor the SI contains. The link stays an illustration, supported by endpoint comparisons.

## (d) Against the novelty notes in SPEC 7e

**Still holds.** Valency returned no paper that fits a kinetic reaction network to in situ XRD with Bayesian inference for thermal solid-state synthesis from precursors. Valency does not index Kosuge 2026, so this is weaker evidence than the OpenAlex pass, not stronger.

**Extends the prior-art list:**

- **Yokoyama, Kawaguchi and Mizumaki, Sci. Rep. 2023** ([37699922](https://pubmed.ncbi.nlm.nih.gov/37699922/), doi 10.1038/s41598-023-40573-z). A Bayesian framework selects time-evolution models and start times from time-resolved XRD of an adsorption process, and the abstract says it applies to chemical reactions. Bayesian model selection on time-resolved XRD therefore predates Kosuge 2026. The existing PROGRESS wording ("do not claim to be first at Bayesian model selection on time-resolved XRD") stands and gains a second citation. Whether it comes from the same group as Kosuge was not checked.
- **Karan et al., Nat. Mater. 2026** ([42049922](https://pubmed.ncbi.nlm.nih.gov/42049922/), doi 10.1038/s41563-026-02596-5; arXiv 2501.08560). A second Persson-group forward simulator: machine-learned transport through "liquid-like" product layers inside a cellular reaction model. It predicts Ba-Ti-O phase formation against time and temperature for several BaO:TiO2 ratios; the abstract describes predictions, not fits to data. This is the same category as the Chem. Mater. paper in 7e, and it covers a Ti-oxide system.
- **Tan, Kamm, …, Chapman and Sun, arXiv 2607.06685 (July 2026)**. Evidence that a transient liquid forms above the metastable eutectic temperature and acts as the fast diffusion medium that sets the reaction onset. This is a mechanism hypothesis our proposer could include for Chapman-type onset behaviour. It is not a methods competitor.
- **Szymanski et al., Sci. Adv. 2024** ([38959320](https://pubmed.ncbi.nlm.nih.gov/38959320/), doi 10.1126/sciadv.adp3309). The abstract confirms the ≥60 meV/atom threshold for thermodynamic control, from in situ characterization of 37 reactant pairs. PROGRESS records this figure only as quoted by Karan and Persson; it is now checked against the source abstract, though not the full text.

**Narrows the claims in 7e's "What we can add" list.** 7e lists uncertainty and identifiability reporting, an LLM proposer, and next-experiment planning with an information-gain criterion. As general methods, each of these now has a 2026 preprint:

- **Murphy, "Model Discovery Agent", arXiv 2608.09696 (Aug 2026)**: LLM-proposed model structures, value-of-information experiment design, and Bayesian inference over model structure and parameters, applied among other things to symbolic reaction rate laws.
- **Shetty and Braga-Neto, "LLM-IDEA", arXiv 2610.11253 (Oct 8, 2026)**: an identifiability engine inside a closed-loop LLM discovery agent. It gives a three-way verdict on a plateau: a capability limit, resolvable within the current design class, or certified exhausted. This is close to our "what the data cannot settle" report.
- **Aliaga Medina et al., "DASyR-LLM", arXiv 2608.05120**: an LLM critiques and proposes rate expressions inside symbolic regression for kinetic model discovery, including heterogeneous catalysis cases.
- **Esquivel et al. (Aspuru-Guzik), arXiv 2610.18825 (Oct 13, 2026)**: joint neural posterior estimation and model selection for chemical reaction networks from multi-experiment time series.
- **Kay and Zhang, J. Chem. Inf. Model. 2026** (doi 10.1021/acs.jcim.5c03032): automated reaction-network identification with symbolic regression and model-based design of experiments.
- **Grinberg Dana, Chem. Sci. 2026** (doi 10.1039/d5sc07692g): a perspective on agentic kinetic modelling.

None of these abstracts covers solid-state synthesis, in situ XRD or phase fractions. The distinguishing claims in 7e therefore still hold if they stay domain-specific: model-proposed parts for precursor solid-state synthesis, joint network fits across temperatures, a reserved-temperature test, and identifiability next to selection on in situ XRD data. "LLM proposer plus identifiability plus information-gain planning" should not be pitched as new in itself. MDA and LLM-IDEA should be read before the pitch wording is fixed.

**SPEC 1b link to NO3RR.** "No dataset ties a synthesis outcome to NO3RR rate constants" still holds. Valency adds small series that tie a synthesis temperature to a phase fraction and to NO3RR selectivity (Lim 2023). It also adds a polymorph hook that touches our headline data: Chapman's precursors are anatase and rutile TiO2, and Wang J. 2025 compares the two in TiO2/Cu2O and reports rutile as the active phase for NO3RR. This is a narrative connection with no shared data, so it must be labelled illustrative in any demo.

## Not verified

- The FE, yield and selectivity numbers come from abstracts, except where a row says "full text" or "SI". Full-text checks were keyword searches through Europe PMC XML for 8 open-access papers. Only the Lim 2023 and Wang J. 2025 SIs were opened, and values read from their figures are by eye, not digitized.
- OA status comes from OpenAlex `oa_status` and Europe PMC. Bronze and hybrid status can change.
- The "Seed" column depends on OpenAlex `referenced_works`, which can be incomplete.
- The raw Valency, OpenAlex and Europe PMC outputs were kept only in this session's scratchpad and are not in the repository.
