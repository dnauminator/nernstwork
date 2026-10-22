# nernstwork

Infer branched reaction networks (mechanism, rate laws, uncertainty, identifiability, next experiment) from multi-species data. Direction as of Oct 20: solid-state synthesis pathways (precursor set and temperature to phases), with the electrochemical nitrate reduction work kept as the test bed and a labelled downstream illustration. See `docs/SPEC.md` section 1b. Built for the Open Scientific Intelligence Hackathon, Oct 21-22 2026. Name is a placeholder.

Read `docs/SPEC.md` first, then `docs/NEXT_STEPS.md` (what to do now); `docs/PROGRESS.md` is the dated record of findings and decisions. To add a digitized figure see `docs/DIGITIZING.md`.

## Layout

- `schema/`: JSON Schemas for mechanism, dataset, task (benchmark world), result. These are the contract between the LLM side and the fitting/evaluation side.
- `src/nernstwork/mechanism.py`: reference validator and ODE simulator (not the inference engine).
- `worlds/`: benchmark worlds and a small candidate library. Regenerate with `python scripts/build_worlds.py worlds`.
- `data/real/`: real datasets extracted from published Source Data. See its README.
- `scripts/`: `build_real_datasets.py`, `build_worlds.py`, `calibrate_liao.py`, `calibrate_katsounaros2008.py`, `digitized_to_dataset.py`.
- `data/digitized_inputs/`: per-figure folders (metadata + digitized CSVs) turned into datasets by `scripts/digitized_to_dataset.py`.
- `LITERATURE.md`: every paper with DOI/arXiv link, use and local file name. `literature/` is the local, git-ignored folder for the PDFs.
- `tests/`: schema, simulation and converter checks, plus investigator contract and synthetic-recovery tests.
- `src/nernstwork/{model,fit,evaluate,canonical,store,investigation,enumerate,review,report,cli}.py`: the shared evaluator, enumeration baseline, investigation store and JSON CLI (`python -m nernstwork.cli`).
- `agent/`: Pi host for the LLM investigator and reviewer (TypeScript, `@earendil-works/pi-coding-agent` 1.3.0). See `docs/INVESTIGATOR.md`.
- `configs/`: evaluation protocols, enumeration spaces and investigation configs.

## Quick start

    pip install -r requirements.txt
    pytest -q
    python scripts/calibrate_liao.py data/real

## Status

Schemas, simulator, four worlds, six real datasets and the first calibration are in. The fitter (maximum likelihood with identifiability diagnostics), enumeration baseline, LLM proposer/reviewer loop and a discrimination check for experiments are in (`docs/INVESTIGATOR.md`); a full information-gain experiment planner is not. W3 uses the published Katsounaros 2012 constants; W5 uses the Polatides 2005 constants and Fig. 6 alphas; W1 uses illustrative parameters; W4 (model A vs model B trap) can now be built from the digitized Katsounaros curves.

## Licence

The code, schemas, scripts and our own documentation are released under the MIT licence (`LICENSE`). **The licence covers our work only.** The datasets under `data/` are digitized or transcribed from published papers, supporting information, theses and repositories, and each remains under its source's terms (several are CC BY-NC 4.0 or publisher copyright). They are included for non-commercial research use with attribution; the per-source terms and how each was checked are in `docs/DATASETS.md` section 7 and in each dataset's metadata. The ARROWS3 tables, publisher PDFs and the Barrera 2023 data are deliberately not in the repository. If you reuse a dataset, follow its source's terms, not the MIT licence.
