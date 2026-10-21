"""JSON command-line bridge: `python -m nernstwork.cli <command> [options]`, payloads on stdin, one JSON object on stdout.

Output is {"ok": true, "result": ...} or {"ok": false, "error": "...", "kind": "..."}. Handled errors exit 0;
unexpected exceptions exit 1 with a traceback on stderr. Commands marked host-only are never exposed as agent tools.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from pathlib import Path

from . import investigation as inv
from .store import ROOT_DEFAULT, Run

HOST_ONLY = {"init", "enumerate", "freeze", "final-eval", "report", "compare-arms"}


def _root(a) -> Path:
    return Path(a.root or os.environ.get("NW_ROOT") or ROOT_DEFAULT)


def _run(a) -> Run:
    r = Run(_root(a), a.run)
    if not r.exists():
        raise inv.InvestigationError(f"no run {a.run} under {_root(a)}")
    return r


def _stdin():
    data = sys.stdin.read()
    return json.loads(data) if data.strip() else {}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="nernstwork")
    p.add_argument("--root", help="investigations root (default: repo investigations/ or $NW_ROOT)")
    sub = p.add_subparsers(dest="cmd", required=True)

    def cmd(name, run=True, **kw):
        sp = sub.add_parser(name, **kw)
        if run:
            sp.add_argument("--run", required=True)
        return sp

    sp = cmd("init", run=False)
    sp.add_argument("--config", required=True)
    sp.add_argument("--arm", required=True)
    sp.add_argument("--run-id")
    cmd("evidence")
    cmd("submit")
    cmd("submit-space")
    cmd("plan")
    sp = cmd("evaluate")
    sp.add_argument("--ids", nargs="*")
    sp.add_argument("--workers", type=int)
    cmd("summaries")
    cmd("compare")
    sp = cmd("details")
    sp.add_argument("--id", required=True)
    sp = cmd("profile")
    sp.add_argument("--ids", nargs="+", required=True)
    cmd("discriminate")
    sp = cmd("bundle")
    sp.add_argument("--ids", nargs="*")
    sp = cmd("record-review")
    sp.add_argument("--bundle", required=True)
    sp = cmd("respond")
    sp.add_argument("--review", required=True)
    cmd("conclude")
    cmd("freeze")
    sp = cmd("final-eval")
    sp.add_argument("--workers", type=int)
    cmd("status")
    sp = cmd("enumerate")
    sp.add_argument("--space", required=True)
    sp.add_argument("--evaluate", action="store_true")
    sp.add_argument("--workers", type=int)
    sp = cmd("report")
    sp.add_argument("--out")
    sp = cmd("compare-arms", run=False)
    sp.add_argument("--runs", nargs="+", required=True)
    sp.add_argument("--out", required=True)
    sp.add_argument("--final", choices=["first", "latest"], default="first")
    sp = cmd("usage")
    a = p.parse_args(argv)
    try:
        res = dispatch(a)
        from .store import encode_nonfinite

        print(json.dumps({"ok": True, "result": encode_nonfinite(res)}, allow_nan=False, default=str))
        return 0
    except (inv.InvestigationError, KeyError, FileNotFoundError, json.JSONDecodeError) as e:
        print(json.dumps({"ok": False, "error": str(e), "kind": type(e).__name__}))
        return 0
    except Exception as e:  # noqa: BLE001 - last-resort handler: report any failure as JSON to the host
        traceback.print_exc()
        print(json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}", "kind": "internal"}))
        return 1


def dispatch(a):
    c = a.cmd
    if c == "init":
        r = inv.init_run(a.config, a.arm, a.run_id, _root(a))
        return {"run_id": r.id, "run_dir": str(r.dir), "evidence_dir": str(r.dir / "evidence"),
                "workspace_dir": str(r.dir / "workspace")}
    if c == "compare-arms":
        from .report import compare_arms

        return compare_arms([Run(_root(a), x) for x in a.runs], Path(a.out), a.final)
    r = _run(a)
    if c == "evidence":
        ev = r.dir / "evidence"
        return {"summary_markdown": (ev / "evidence_summary.md").read_text(),
                "files": sorted(str(q.relative_to(ev)) for q in ev.rglob("*") if q.is_file())}
    if c == "submit":
        d = _stdin()
        return inv.submit(r, d.get("candidates", []), d.get("origin", {}))
    if c == "submit-space":
        d = _stdin()
        return inv.submit_space(r, d.get("space", {}), d.get("origin", {}))
    if c == "plan":
        from .planner import plan

        d = _stdin()
        return plan(r, d.get("designs") or None, d.get("candidate_ids") or None, int(d.get("max_models", 6)))
    if c == "evaluate":
        return inv.evaluate(r, a.ids or None, a.workers)
    if c == "summaries":
        return inv.summaries(r)
    if c == "compare":
        return inv.compare(r)
    if c == "details":
        return inv.details(r, a.id)
    if c == "profile":
        return inv.profile(r, a.ids)
    if c == "discriminate":
        d = _stdin()
        return inv.discriminate(r, d["candidate_ids"], d["designs"])
    if c == "bundle":
        return inv.review_bundle(r, a.ids or None)
    if c == "record-review":
        d = _stdin()
        return inv.record_review(r, a.bundle, d["review"], d.get("reviewer", {}))
    if c == "respond":
        return inv.record_response(r, a.review, _stdin())
    if c == "conclude":
        return inv.conclude(r, _stdin())
    if c == "freeze":
        return inv.freeze(r)
    if c == "final-eval":
        return inv.final_evaluate(r, a.workers)
    if c == "status":
        return inv.status(r)
    if c == "enumerate":
        from .enumerate import enumerate_space

        space = json.loads(Path(a.space).read_text())
        subs = enumerate_space(space)
        res = inv.submit(r, subs, {"source": "enumerator", "space_id": space["space_id"]})
        out = {"space_id": space["space_id"], "n_generated": len(subs),
               "n_created": sum(1 for x in res if x.get("candidate_id") and not x.get("duplicate_of")),
               "n_duplicates": sum(1 for x in res if x.get("duplicate_of"))}
        if a.evaluate:
            ev = inv.evaluate(r, None, a.workers)
            out.update(n_fits_run=ev["n_fits_run"], wall_s=ev["wall_s"])
        return out
    if c == "report":
        from .report import write_report

        return write_report(r, Path(a.out) if a.out else None)
    if c == "usage":
        from .report import usage

        return usage(r)
    raise inv.InvestigationError(f"unknown command {c}")


if __name__ == "__main__":
    sys.exit(main())
