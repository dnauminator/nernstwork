# NernstWork video (Remotion)

Data-driven shots for the hackathon video. Every number and curve comes from `src/data/shots.json`, which
`scripts/export_video_data.py` builds from the frozen runs and their held-out evaluations (`investigations/`, local
only). The compositions hardcode no result.

    # from the repository root: refresh the data after any run changes
    PYTHONPATH=src .venv/bin/python scripts/export_video_data.py

    # from video/
    npm install
    npx remotion studio                                   # preview and scrub
    npx remotion render src/index.ts Shots4to5 out/shots4to5.mp4 --codec=h264 --crf=18
    npx remotion still src/index.ts Shot4Reveal out/f.png --frame=520

| Composition | Length | Shows |
|---|---|---|
| `Shot1Open` | 20 s | The measured 725 °C phase amounts draw themselves, then the research question |
| `Shot3Loop` | 33 s | How it works, from Claude Opus 5.5 run 1's own files: proposed steps, 204 of 208 pathways fitted, frozen and sealed, what's unresolved and the next experiment |
| `Shot4Reveal` | 20 s | Fitted at 700 + 725 °C and frozen: the baseline pick and the Opus picks predict 750 °C, then the sealed measurements land; rank among the 153 reference models and RMSE |
| `Shot5Ranks` | 18 s | The 153 reference models ranked by fit and by 750 °C prediction; the baseline pick (#1 by fit) lands #11, the Opus picks land #1 and #4 |
| `Shot5bRuns` | 16 s | Baseline and all four AI runs: best model in the run's search space, the agent's best plausible model, the rule's pick |
| `Shot7Plan` | 24 s | The planner's ranked experiments; under the top pick the two leading models overlap and the agent's own rival splits off at 2 min |
| `Shot9Close` | 18 s | What we found (computed from the runs), the closing line, credits |
| `Shots4to5` | 54 s | Shots 4, 5 and 5b in sequence |
| `Draft` | 2:29 | Every built shot in story order; the narration is in `SCRIPT.md` |

Colours follow the entity across shots (dataviz reference palette, dark steps, validated all-pairs): blue is the
selection rule's pick, orange the agent's other plausible model, aqua the best model in a run's own space, light gray
the baseline. Remotion is used under its free licence (individuals, companies with up to three employees, non-profits).
