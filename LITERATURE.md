# Literature

PDFs are not in the repo (publisher copyright, and about 140 MB). This file is the index: every paper with its DOI or arXiv link, what we use it for, and the file name it has in the local, git-ignored `literature/` folder, so anyone can drop the PDF in the same place. Several of the Nature Communications, Catalysts, JACS (Bai) and Cell Reports Physical Science papers are open access; the arXiv ones are free.

Local layout: `literature/01_method_prior_art/`, `literature/02_kinetics_benchmarks/`, `literature/03_timecourse_data/<paper folder>/`, `literature/04_synthesis/` (flat; all section 5 files).

## 1. Method prior art: how others infer mechanisms

| Paper | Link | Why we care | Local file |
|---|---|---|---|
| de Carvalho Servia & Hii, SiMBA: Simplest Mechanism Builder Algorithm, an automated microkinetic model discovery tool | arXiv:2410.21205 (https://arxiv.org/abs/2410.21205) | Simplest-mechanism-first enumeration scored by AIC; handles unobserved intermediates. Baseline method | servia2025_SiMBA_... |
| Kay & Zhang, A Data-Efficient Framework for Automated Identification of Reaction Networks and Interpretable Rate Models, J. Chem. Inf. Model. 66, 8735 (2026) | doi:10.1021/acs.jcim.5c03032 | Sparse network identification + symbolic regression + design of experiments; assumes full observability and noise-free data | kay2026_JCIM_... |
| Murphy, Model Discovery Agent: LLM-assisted Bayesian experiment design for data-efficient discovery of mechanistic world models | arXiv:2608.09696 | LLM proposes models, BIC and expected information gain pick experiments | murphy2026_Model_Discovery_Agent_... |
| Ma et al., Learning to Outgrow a Theory: experimental discovery beyond the initial hypothesis space (ICLR 2027) | arXiv:2610.07627 | Model-class revision when the hypothesis space is wrong | ma2026_Learning_to_Outgrow_a_Theory_... |
| Aliaga Medina, Quintanilla, del Rio Chanona, DASyR-LLM: Domain-aware symbolic regression with LLMs for kinetic model discovery | arXiv:2608.05120 | LLM plausibility critic inside symbolic regression; notes AIC can favour simple wrong models. No code found | aliagamedina2026_DASyR-LLM_... |
| Kabra et al., LLM-AutoSciLab: closed-loop scientific discovery via active experimentation with LLMs | arXiv:2605.24043; code https://github.com/scientific-discovery/LLM-AutoSciLab | Closed-loop LLM discovery; static enzyme rate laws (ActiveSciBench) | kabra2026_LLM-AutoSciLab_... |
| Li et al. (Sanofi), Mechanistic exploration and kinetic modeling through in-silico data generation and probabilistic machine learning analysis | Ind. Eng. Chem. Res. 64, 6825 (2025), doi:10.1021/acs.iecr.4c04301 (confirmed from the PDF) | Bayesian inference (elpd_loo/WAIC) + random-forest classifier on 456 in-silico two-step mechanisms + LLM text-to-JSON. Main article now in the folder (`ie4c04301.pdf`); see `docs/SPEC.md` 8b | ie4c04301.pdf |

## 2. Kinetics benchmarks: published rate constants we can reproduce

| Paper | Link | Use | Local file |
|---|---|---|---|
| Katsounaros, Dortsiou, Polatides, Preston, Kypraios, Kyriacou, Reaction pathways in the electrochemical reduction of nitrate on tin, Electrochim. Acta 71, 270 (2012) | doi:10.1016/j.electacta.2012.03.154 | Primary benchmark. Model B with hidden intermediate X, Table 1 constants, Bayes factor 2921 against model A. Fig. 1 digitized. World W3 uses these constants | katsounaros2012_Sn_... |
| Katsounaros & Kyriacou, Influence of nitrate concentration on its electrochemical reduction on tin cathode: identification of reaction intermediates, Electrochim. Acta 53, 5477 (2008) | doi:10.1016/j.electacta.2008.03.018 | Fig. 2 digitized: 1 M nitrate, five species plus the authors' plotted loss of mass balance | katsounaros2008_Sn_... |
| Katsounaros & Kyriacou, Influence of the concentration and the nature of the supporting electrolyte on the electrochemical reduction of nitrate on tin cathode, Electrochim. Acta 52, 6412 (2007) | doi:10.1016/j.electacta.2007.04.050 | Supporting-electrolyte effects; context | katsounaros2007_Sn_... |
| Polatides & Kyriacou, Electrochemical reduction of nitrate ion on various cathodes: reaction kinetics on bronze cathode, J. Appl. Electrochem. 35, 421 (2005) | doi:10.1007/s10800-004-8349-z | Fig. 3 digitized (second-order N2 branch; printed k2 looks 10x off, see `docs/SPEC.md` 7c). Figs. 5-6 (rate constants vs potential) are the source for W5 alphas, still to do | polatides2005_bronze_... |
| Tang, Stenlid, Guo, Corson, Tarpeh, Abild-Pedersen, Nitrate reduction modeling under acidic conditions with late transition metals, ACS Catal. 15, 4489 (2025) | doi:10.1021/acscatal.4c06394 | Microkinetic modelling in acid; context for pH dependence. Not yet summarized | tang2025_acidic_... (+ SI) |

## 3. Time-course data: experimental papers

| Paper | Link | Status | Local folder |
|---|---|---|---|
| Liao et al., Near-unity nitrate to ammonia conversion via reactant enrichment at the solid-liquid interface, Nat. Commun. (2025) | doi:10.1038/s41467-025-60671-y | **Used.** Source Data Supp. Figs. 49, 50a, 50b converted to `data/real/` | liao2025_MoS2_reactant_enrichment |
| Ebenezer, Velayudham, Yhobu, Schechter, A detailed kinetic study of selective electrochemical nitrate reduction to ammonia, Chem. Eng. J. 545, 179676 (2026) | doi:10.1016/j.cej.2026.179676 | **Read.** Initial-rate and 1 h data only, no time courses; orders inconsistent between table and text (`docs/SPEC.md` 8b) | ebenezer2026_NiCo2S4_... |
| Yu, Yan, Zhang, Wang, Kinetic understanding of the enhanced electroreduction of nitrate to ammonia for Co3O4-modified Cu2+1O nanowire electrocatalyst, Catalysts 15, 491 (2025) | doi:10.3390/catal15050491 | Fig. 4d concentrations over time; caption and text disagree on the species. Needs digitizing | yu2025_Co3O4-Cu2O_... |
| Bai et al., Electrocatalytic nitrate and nitrite reduction toward ammonia using Cu2O nanocubes: active species and reaction mechanisms, J. Am. Chem. Soc. 146, 9665 (2024) | doi:10.1021/jacs.3c13288 | FE vs time, nitrate-feed vs nitrite-feed experiments; no concentration-time fits | bai2024_Cu2O_... |
| Liu et al., Efficient tandem electroreduction of nitrate into ammonia through coupling Cu single atoms with adjacent Co3O4, Nat. Commun. (2024) | doi:10.1038/s41467-024-48035-4 | Source Data (nitrate/nitrite steps) located, not converted | liu2024_Cu-SA_Co3O4_tandem |
| He et al., Splicing the active phases of copper/cobalt-based catalysts achieves high-rate tandem electroreduction of nitrate to ammonia, Nat. Commun. (2022) | doi:10.1038/s41467-022-28728-4 | Not examined in detail | he2022_CuCo_tandem |
| Wang et al., Ammonia electrosynthesis from nitrate using a stable amorphous/crystalline dual-phase Cu catalyst, Nat. Commun. (2025) | doi:10.1038/s41467-025-55889-9 | SI and Source Data only; Source Data sheets not yet screened | wang2025_amorphous-crystalline_Cu |
| Wu et al., Steering the catalyst structure and intermediates adsorption configuration during pulsed nitrate electroreduction, Nat. Commun. (2025) | doi:10.1038/s41467-025-65391-x | Not examined in detail | wu2025_pulsed_... |
| Yuan et al., Sequential electrocatalytic reactions along a membrane electrode assembly drive efficient nitrate-to-ammonia conversion, Cell Rep. Phys. Sci. 5, 101977 (2024) | doi:10.1016/j.xcrp.2024.101977 | MEA time-dependent data; not examined in detail | yuan2024_MEA_... |

## 4. Added Oct 19 (network and simulation background)

| Paper | Link | Use | Local file |
|---|---|---|---|
| Barter et al., Predictive stochastic analysis of massive filter-based electrochemical reaction networks (HiPRGen), Digital Discovery (2023) | doi:10.1039/d2dd00117a | Enumerate-and-filter reaction generation; model for the enumeration baseline | barter_predictive_stochastic_2023.pdf |
| Liu et al., Establishing reaction networks in the 16-electron sulfur reduction reaction, Nature 626, 98 (2024) | doi:10.1038/s41586-023-06918-4 | Electrochemical plus chemical (comproportionation) steps, charge bookkeeping, shared network across catalysts | s41586-023-06918-4.pdf |
| Bagger & Wuttke, Atomistic catalytic reaction networks: case study on electrochemical reduction of CO, NO & combinations, PCCP 27, 25433 (2025) | doi:10.1039/d5cp03701h | Isomer-generator enumeration of surface intermediates; atomistic, background only | d5cp03701h.pdf |
| Horno, Garcia-Hernandez, Gonzalez-Fernandez, Digital simulation of electrochemical processes by the network approach, J. Electroanal. Chem. 352, 83 (1993) | DOI not printed in the extracted text; file name suggests the ScienceDirect id 002207289380256H | Diffusion-reaction simulation; out of scope | 1-s2.0-002207289380256H-main.pdf |

## 5. Solid-state synthesis (Oct 20 pivot)

Read Oct 20; see `docs/SPEC.md` section 7e and `docs/PROGRESS.md` section 2b.

| Paper | Link | Use | Local file |
|---|---|---|---|
| Szymanski, Nevatia, Bartel, Zeng, Ceder, Autonomous and dynamic precursor selection for solid-state materials synthesis (ARROWS3), Nat. Commun. (2023) | doi:10.1038/s41467-023-42329-9 | Data source (YBCO, NTMO, LTOPO via the ARROWS3 repository) and closest prior method. Source Data xlsx holds graph data only | s41467-023-42329-9.pdf, 41467_2023_42329_MOESM1_ESM.pdf, 41467_2023_42329_MOESM4_ESM.xlsx |
| Szymanski et al., An autonomous laboratory for the accelerated synthesis of novel materials (A-Lab), Nature 624, 86 (2023) | doi:10.1038/s41586-023-06734-w | 36 of 57 targets (published abstract). SI zip holds a recipes CSV and refinement results | s41586-023-06734-w.pdf, 41586_2023_6734_MOESM1_ESM.pdf, 41586_2023_6734_MOESM3_ESM.zip |
| Miura, Bartel, ..., Ceder, Sun, Observing and modeling the sequential pairwise reactions that drive solid-state ceramic synthesis | arXiv:2009.10896 | Pairwise-reaction model; in situ XRD of YBCO (BaCO3 vs BaO2) | 2009.10896v3.pdf |
| Walters, McDermott, Rendy, Fei, Persson, Ceder, The Precursor Genome: a pairwise reaction dataset for solid-state synthesis | arXiv:2607.09903; github.com/lauren-walters/precursor-genome; doi:10.5281/zenodo.21285546 (CC BY 4.0, links from the paper, not yet opened) | 1,035 pairwise reactions, one 1 h dwell at one temperature each; prior for proposer and critic | 2607.09903v1.pdf |
| Fei, McDermott, Rom, Wang, Ceder, Dara: automated multiple-hypothesis phase identification and refinement from powder XRD | arXiv:2510.19667; github.com/idocx/dara | Source of Precursor Genome labels; alternative hypotheses as label noise | 2510.19667v2.pdf |
| Leeman, Liu, Stiles, Lee, Bhatt, Schoop, Palgrave, Challenges in high-throughput inorganic materials prediction and autonomous synthesis, PRX Energy 3, 011002 (2024) | doi:10.1103/PRXEnergy.3.011002 | Critique of A-Lab phase assignments; label-noise limitation | PRXEnergy.3.011002.pdf |
| Hong, Jang, Bae, et al., Retro-Forge: a multi-step pairwise retrosynthesis framework for solid-state materials synthesis (ICML 2026) | no link found | Possible proposer; target-to-precursor task | 78_Retro_Forge_A_Multi_Step_Pa.pdf |
| Hu, Beauvais, Kamm, Mullens, Sanchez Monserrate, Vornholt, Chupas, Chapman, Resolving fast relative kinetics in inorganic solid-state synthesis, J. Am. Chem. Soc. 145, 26545 (2023) | doi:10.1021/jacs.3c10916 | Time-resolved TiO2 + Li2CO3 -> Li4Ti5O12 at four temperatures, Avrami fits; digitize Figs. 2-3 | ja3c10916.pdf, ja3c10916_si_001.pdf |
| Macchietti, Carta, Delogu, Grepioni, Emmerling, Casali, Scaling up mechanochemical reactions: linking crystalline phase evolution studied via in situ PXRD with kinetics from MCR-ALS, Chem. Sci. 17, 12047 (2026) | doi:10.1039/d6sc01158f | MCR-ALS with kinetic constraints; mechanochemical, low relevance | d6sc01158f.pdf, d6sc01158f1_suppl.pdf |
| Rosser, Farris, Leonard, Predictive machine learning models trained on experimental datasets for electrochemical nitrogen reduction, Digital Discovery 3, 667 (2024) | doi:10.1039/d3dd00151b | ML on 520 N2-reduction conditions; not nitrate or kinetic | d3dd00151b.pdf, d3dd00151b1_suppl.pdf |
| Gao et al., Breaking adsorption-energy scaling limitations of electrocatalytic nitrate reduction on intermetallic CuPd nanocubes by machine-learned insights, Nat. Commun. (2022) | doi:10.1038/s41467-022-29926-w | Ordered B2 versus random alloy as a synthesis-controlled catalyst state for NO3RR; endpoint FE only | s41467-022-29926-w.pdf, 41467_2022_29926_MOESM1_ESM.pdf |
| McDermott, Dwaraknath, Persson, A graph-based network for predicting chemical reaction pathways in solid-state materials synthesis, Nat. Commun. 12, 3097 (2021) | doi:10.1038/s41467-021-23339-x; code github.com/GENESIS-EFRC/reaction-network (PyPI `rxn-network`) | Thermochemistry-based reaction network and pathfinding; reproduces pathways for YMnO3, Y2Mn2O7, Fe2SiS4 and YBCO. Thermochemistry from Materials Project (version 2020.09.08) and NIST-JANAF. Candidate for a phase-network proposer and thermodynamic plausibility rules | s41467-021-23339-x.pdf, 41467_2021_23339_MOESM1_ESM.pdf |
| Bartel et al., Physical descriptor for the Gibbs energy of inorganic crystalline solids and temperature-dependent materials chemistry, Nat. Commun. 9, 4168 (2018) | doi:10.1038/s41467-018-06682-4; code github.com/CJBartel/predict-gibbs-energies | Temperature-dependent Gibbs energies for driving-force calculations (used by ARROWS3 and Miura). The CSV is the training table (formula, source FactSage/PhononDB, is_train, m, V, Tmax, sg, MP_ID) | s41467-018-06682-4.pdf, 41467_2018_6682_MOESM1_ESM.pdf, 41467_2018_6682_MOESM4_ESM.csv |
| Bianchini et al., The interplay between thermodynamics and kinetics in the solid-state synthesis of layered oxides, Nat. Mater. 19, 1088 (2020) | doi:10.1038/s41563-020-0688-6 | In situ synchrotron XRD of multistage Na0.67MO2 (M = Co, Mn) crystallisation with ab initio comparison. Data: "available from the corresponding author on request", source data for figures with the paper, so figures only | s41563-020-0688-6.pdf, 41563_2020_688_MOESM1_ESM.pdf |
| Kamm, Huang, Vornholt, McAuliffe, Veith, Thornton, Chapman, Relative kinetics of solid-state reactions: the role of architecture in controlling reactivity, J. Am. Chem. Soc. 144, 11975 (2022) | doi:10.1021/jacs.2c05043 (from the file name ja2c05043; not checked) | In situ synchrotron XRD of NaFeO2 + LiBr; a fast regime in the first minutes and a slow regime after; phase-field model. Same lab as the Chapman case | ja2c05043.pdf, ja2c05043_si_001.pdf |
| Zeng, Szymanski, He, Jun, Gallington, Huo, Bartel, Ouyang, Ceder, Selective formation of metastable polymorphs in solid-state synthesis, Sci. Adv. 10, eadj5431 (2024) | doi:10.1126/sciadv.adj5431 (from the file name; not checked) | Polymorph selection by surface energy and nucleation; context for the LTOPO polymorph competition in the ARROWS3 table (the paper's preprint is arXiv 2309.05800) | sciadv.adj5431.pdf, sciadv.adj5431_sm.pdf |
| ARROWS3 data and baselines (Szymanski, njszym/ARROWS, doi:10.5281/zenodo.8331001) | https://github.com/njszym/ARROWS ; Exp files are Git LFS | Experimental outcomes for YBCO, NTMO, LTOPO (`Exp.json` per target, stored here as `ExpYBCO.json`, `ExpNTMO.json`, `ExpLTOPO.json`, with `Settings*.json`), the black-box planners `d-optimal.py`, `bayesian-opt.py`, `genetic-algo.py`, and `MP_Energetics.json` (225.7 MB of 0 K and temperature-corrected formation energies from Materials Project and Bartel). No licence found for the ARROWS3 files: do not commit. ARROWS3 itself needs a Materials Project API key to run | ExpYBCO.json, ExpNTMO.json, ExpLTOPO.json, SettingsYBCO.json, SettingsNTMO.json, SettingsLTOPO.json, d-optimal.py, bayesian-opt.py, genetic-algo.py, MP_Energetics.json |

## Context

- Review: Recent advances in mechanistic studies and catalyst development for electrochemical nitrate reduction to ammonia, Commun. Chem. (2025), https://www.nature.com/articles/s42004-025-01864-w
- Mendeley dataset for a Nature Catalysis NO3RR paper (contents not verified): https://data.mendeley.com/datasets/dz3zy7vb3c

## Sharing PDFs with a collaborator

Send them outside the repo (shared drive or a zip) rather than committing paywalled PDFs. The three largest files (He 2022 SI, Liu 2024 Source Data, Wu 2025 Source Data) are only needed if someone screens those Source Data workbooks.
