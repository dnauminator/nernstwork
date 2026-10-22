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
| `Shot4Reveal` | 20 s | Fitted at 700 + 725 °C and frozen: the baseline pick and the Opus 1 picks predict 750 °C, then the sealed measurements land; rank among the 153 reference models and RMSE |
| `Shot5Ranks` | 18 s | The 153 reference models ranked by fit and by 750 °C prediction; the baseline pick (#1 by fit) lands #11, the Opus 1 picks land #1 and #4 |
| `Shot5bRuns` | 16 s | Baseline and all four AI runs: best model in the run's own space, the agent's best plausible model, the rule's pick |
| `Shots4to5` | 54 s | The three in sequence with fades |

Colours follow the entity across shots (dataviz reference palette, dark steps, validated all-pairs): blue is the
selection rule's pick, orange the agent's other plausible model, aqua the best model in a run's own space, light gray
the baseline. Remotion is used under its free licence (individuals, companies with up to three employees, non-profits).
