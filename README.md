# nernstwork

Infer branched reaction networks (mechanism, rate laws, uncertainty, identifiability, next experiment) from multi-species time-course data. First demo: electrochemical nitrate reduction. Built for the Open Scientific Intelligence Hackathon, Oct 21-22 2026. Name is a placeholder.

Read `docs/SPEC.md` first, then `docs/NEXT_STEPS.md`. To add a digitized figure see `docs/DIGITIZING.md`.

## Layout

- `schema/`: JSON Schemas for mechanism, dataset, task (benchmark world), result. These are the contract between the LLM side and the fitting/evaluation side.
- `src/nernstwork/mechanism.py`: reference validator and ODE simulator (not the inference engine).
- `worlds/`: benchmark worlds and a small candidate library. Regenerate with `python scripts/build_worlds.py worlds`.
- `data/real/`: real datasets extracted from published Source Data. See its README.
- `scripts/`: `build_real_datasets.py`, `build_worlds.py`, `calibrate_liao.py`, `calibrate_katsounaros2008.py`, `digitized_to_dataset.py`.
- `data/digitized_inputs/`: per-figure folders (metadata + digitized CSVs) turned into datasets by `scripts/digitized_to_dataset.py`.
- `LITERATURE.md`: every paper with DOI/arXiv link, use and local file name. `literature/` is the local, git-ignored folder for the PDFs.
- `tests/`: schema, simulation and converter checks.

## Quick start

    pip install -r requirements.txt
    pytest -q
    python scripts/calibrate_liao.py data/real

## Status

Schemas, simulator, four worlds, six real datasets and the first calibration are in. Not yet written: the fitter, enumeration baseline, LLM proposer/critic, experiment planner. W3 uses the published Katsounaros 2012 constants; W1 and W5 use illustrative parameters; W4 (model A vs model B trap) can now be built from the digitized Katsounaros curves.
