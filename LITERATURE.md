# Literature

PDFs are not in the repo (publisher copyright, and about 140 MB). This file is the index: every paper with its DOI or arXiv link, what we use it for, and the file name it has in the local, git-ignored `literature/` folder, so anyone can drop the PDF in the same place. Several of the Nature Communications, Catalysts, JACS (Bai) and Cell Reports Physical Science papers are open access; the arXiv ones are free.

Local layout: `literature/01_method_prior_art/`, `literature/02_kinetics_benchmarks/`, `literature/03_timecourse_data/<paper folder>/`.

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

## Context

- Review: Recent advances in mechanistic studies and catalyst development for electrochemical nitrate reduction to ammonia, Commun. Chem. (2025), https://www.nature.com/articles/s42004-025-01864-w
- Mendeley dataset for a Nature Catalysis NO3RR paper (contents not verified): https://data.mendeley.com/datasets/dz3zy7vb3c

## Sharing PDFs with a collaborator

Send them outside the repo (shared drive or a zip) rather than committing paywalled PDFs. The three largest files (He 2022 SI, Liu 2024 Source Data, Wu 2025 Source Data) are only needed if someone screens those Source Data workbooks.
