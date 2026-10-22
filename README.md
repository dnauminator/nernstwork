# nernstwork

NernstWork pairs a language-model agent with fitting code to infer reaction pathways from time-resolved data. The agent
proposes the parts of a reaction network (phases, steps, rate-law forms, each with a cited reason); code checks every
combination for element balance and fits all of them with one protocol; the picks are frozen and tested on a held-out
condition; the agent then reports what the data cannot settle and a planner suggests the next experiment. Built by
Daniel Naumov and Jarrod Barnes for the Open Scientific Intelligence Hackathon, Oct 21-22 2026.

**Result (solid-state synthesis, [Hu et al., JACS 2023](https://doi.org/10.1021/jacs.3c10916)):** fitted at 700 and
725 C and frozen, every AI-proposed search space contained a model ranking in the top 4 of 153 code-built reference
models at 750 C, but picking it by best fit chose models ranking 4th to 36th. Details and caveats:
`docs/SYNTHESIS.md`; the hackathon write-up: `docs/submission/WRITEUP.md`; the video and its sourced script: `video/`.

**Reproduce the 750 C test** (Python 3.12; the LLM arm also needs Node and model credentials, see `docs/INVESTIGATOR.md`):

    pip install -r requirements.txt && pytest -q
    PYTHONPATH=src python -m nernstwork.cli init --config configs/investigations/chapman750.json --arm enumeration --run-id chapman750-enumeration
    PYTHONPATH=src python -m nernstwork.cli enumerate --run chapman750-enumeration --space configs/spaces/chapman_core.json --evaluate --workers 6
    PYTHONPATH=src python -m nernstwork.cli freeze --run chapman750-enumeration && PYTHONPATH=src python -m nernstwork.cli final-eval --run chapman750-enumeration

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

As of Oct 22: the evaluator (maximum likelihood with identifiability diagnostics), enumeration baseline, LLM proposer/reviewer loop, synthesis extensions (element balance, Arrhenius, Avrami, joint multi-temperature fits) and the Buzzi-Ferraris experiment planner are in (`docs/INVESTIGATOR.md`, `docs/SYNTHESIS.md`). Earlier test-bed notes: W3 uses the published Katsounaros 2012 constants; W5 uses the Polatides 2005 constants and Fig. 6 alphas; W1 uses illustrative parameters; W4 (model A vs model B trap) can now be built from the digitized Katsounaros curves.
