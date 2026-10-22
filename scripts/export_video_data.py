"""Export the numbers and curves the video shots draw, from the frozen runs and their final evaluations.

Every value in video/src/data/shots.json comes from a run artifact (frozen fits, held-out predictions, the arm
comparison); the Remotion compositions hardcode no result. Rerun after any run changes:

    PYTHONPATH=src .venv/bin/python scripts/export_video_data.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from nernstwork import investigation as inv
from nernstwork.data import load_dataset, observation_set
from nernstwork.evaluate import code_identity, fit_key, validate_submission
from nernstwork.fit import DEFAULT_MAX_RHS_EVALS
from nernstwork.model import compile_mechanism
from nernstwork.store import Run

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / "investigations"
OUT = REPO / "video" / "src" / "data" / "shots.json"
CHANNELS = ["anatase", "rutile", "Li2TiO3", "Li4Ti5O12"]
# full display names for the model ids recorded in each run's pi/usage.json
MODEL_NAMES = {"anthropic/claude-opus-5-5": "Claude Opus 5.5", "openrouter/google/gemini-4-argon": "Gemini 4 Argon"}


def run_label(run_id: str) -> tuple[str, str]:
    """(full model name, run number) from the model the run's investigator sessions actually used."""
    usage = ROOT / "runs" / run_id / "pi" / "usage.json"
    if not usage.exists():
        return "Baseline", "code only, no AI"
    models = {s["model"] for s in json.loads(usage.read_text())["sessions"].values() if s["label"] == "investigator"}
    (model,) = models  # one investigator model per run
    return MODEL_NAMES[model], f"run {run_id[-1]}"


def heldout(run: Run) -> tuple[dict, dict]:
    """The run's held-out dataset entry and its observation set."""
    h = [d for d in run.manifest()["datasets"] if d["role"] == "final_holdout"][0]
    ds, sha = load_dataset(REPO / h["path"])
    return ds, observation_set(ds, sha, run.protocol().get("exclude_t0", True))


def predicted_curves(run: Run, sub: dict, t: np.ndarray) -> dict:
    """Simulate a candidate at the held-out condition with its development-fitted parameters (no refitting)."""
    P, dev_obs = run.protocol(), inv._dev_obs(run)
    v = validate_submission(sub, dev_obs, P)
    body = run.cache.result(fit_key(v["dynamics_hash"], dev_obs.sha256, P, code_identity()["sha256"]))
    fr = inv._translate(sub, v, dev_obs, P, body["result"])
    comp = compile_mechanism(sub["mechanism"], dev_obs.conditions, P.get("bounds"))
    _, obs = heldout(run)
    max_rhs = int(P.get("ode", {}).get("max_rhs_evals", DEFAULT_MAX_RHS_EVALS))
    Y = comp.simulate(np.array(fr["theta"]), t, obs.c0, conditions=obs.conditions, max_rhs=max_rhs)
    return {ch: [round(float(x), 5) for x in Y[[comp.species.index(s) for s in v["observation_map"][ch]]].sum(0)]
            for ch in CHANNELS}


def final_rows(run: Run) -> dict:
    # the code-hash-suffixed file holds the current scoring (common noise scale); the enumeration run's unsuffixed file
    # predates that change
    code = code_identity()["sha256"][:12]
    ev = json.loads((run.dir / "final" / f"final_evaluation__{code}.json").read_text())["datasets"][0]
    return {r["candidate_id"]: r for r in ev["frozen_candidates"]}, ev


def shot4() -> dict:
    """750 C reveal: the Opus 1 frozen picks and the baseline's pick, predicted without refitting, against the data."""
    opus, base = Run(ROOT, "chapman750-propose_space-opus1"), Run(ROOT, "chapman750-enumeration")
    ds, _ = heldout(opus)
    t = np.round(np.linspace(0.0, 9.5, 191), 4)
    models = []
    for run, role, label in [(base, "baseline", "Baseline pick"), (opus, "rule", "Opus 1 · rule's pick"),
                             (opus, "plausible", "Opus 1 · agent's other plausible model")]:
        frozen = json.loads((run.dir / "frozen.json").read_text())
        rows, ev = final_rows(run)
        if role == "plausible":
            cid = next(c for c in frozen["agent_concluded_plausible"] if c not in frozen["selected_by_rule"])
        else:
            cid = frozen["top1"]
        r = rows[cid]
        models.append({"run_id": run.id, "model_name": run_label(run.id)[0], "candidate_id": cid, "role": role, "label": label,
                       "rank": r["rank_among_space"], "n_space": r["n_space"], "rmse_all": round(r["rmse_all"], 4),
                       "rank_by_rmse": r["rank_by_rmse"], "curves": predicted_curves(run, frozen["candidates"][cid], t)})
    obs = {s["species"]: {"t": s["t_min"], "y": s["y"]} for s in ds["series"] if s["species"] in CHANNELS}
    cite = ds["provenance"].get("citation", "")
    authors, _, journal = cite.partition(", J. ")
    short = f"{authors.split(',')[0]} et al., J. {journal}" if journal else cite
    return {"temperature_C": ds["conditions"]["temperature_C"], "t": t.tolist(), "observations": obs, "models": models,
            "provenance": cite, "short_citation": f"{short}, Fig. 2 (digitized)"}


def shot5() -> dict:
    """Fit rank vs prediction rank for the 153 reference models, with the Opus 1 frozen picks placed among them."""
    opus = Run(ROOT, "chapman750-propose_space-opus1")
    rows, ev = final_rows(opus)
    scores = json.loads((opus.dir / "final" / ev["dataset_id"] / "predictions.json").read_text())["scores"]
    ref = {c: s for c, s in scores.items() if c.startswith("S:") and s["status"] == "fitted"}
    by_dev = sorted(ref, key=lambda c: ref[c]["development_aicc"])
    by_score = sorted(ref, key=lambda c: ref[c]["heldout_score"])
    reference = [{"id": c[2:], "dev_rank": by_dev.index(c) + 1, "heldout_rank": by_score.index(c) + 1,
                  "rmse_all": round(ref[c]["rmse_all"], 4)} for c in by_dev]
    frozen = json.loads((opus.dir / "frozen.json").read_text())
    picks = []
    for cid in frozen["agent_concluded_plausible"]:
        r = rows[cid]
        # every Opus 1 frozen pick fits the development runs better than all reference models (AICc)
        better_than_all = r["development_aicc"] < ref[by_dev[0]]["development_aicc"]
        picks.append({"candidate_id": cid, "model_name": run_label(opus.id)[0], "run": run_label(opus.id)[1],
                      "role": "rule" if cid in frozen["selected_by_rule"] else "plausible",
                      "dev_aicc": round(r["development_aicc"], 1), "fits_better_than_all_reference": better_than_all,
                      "heldout_rank": r["rank_among_space"], "rmse_all": round(r["rmse_all"], 4)})
    return {"n_reference": len(ref), "reference": reference, "baseline_pick": by_dev[0][2:], "opus_picks": picks,
            "own_space_best": ev["run_candidates"]["best_predicting"]}


def shot5b() -> dict:
    """Across runs: where the rule's pick, the agent's best plausible model and the best model in the run's own
    space land among the reference models at 750 C."""
    arms = json.loads((REPO / "docs" / "examples" / "chapman750" / "arm_comparison.json").read_text())["rows"]
    out = []
    for a in arms:
        name, detail = run_label(a["run_id"])
        plaus = [r["rank_among_space"] for r in a["heldout_frozen"] if r.get("agent_concluded_plausible")]
        out.append({"run_id": a["run_id"], "name": name, "detail": detail,
                    "rule_pick_rank": a["heldout_top1"]["rank_among_space"],
                    "best_plausible_rank": min(plaus) if plaus else None,
                    "own_space_best_rank": a["own_space"]["best_predicting"]["rank_among_space"],
                    "n_space": a["heldout_top1"]["n_space"]})
    return {"runs": out}


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    data = {"generated_by": "scripts/export_video_data.py", "code_sha256": code_identity()["sha256"],
            "shot4": shot4(), "shot5": shot5(), "shot5b": shot5b()}
    OUT.write_text(json.dumps(data, indent=1))
    print(f"wrote {OUT.relative_to(REPO)}")
    for m in data["shot4"]["models"]:
        print(" shot4", m["label"], m["candidate_id"], "rank", m["rank"], "rmse", m["rmse_all"])
    for p in data["shot5"]["opus_picks"]:
        print(" shot5", p)
    for r in data["shot5b"]["runs"]:
        print(" shot5b", r)


if __name__ == "__main__":
    main()
