"""File-based investigation store.

Scientific state lives here, not in any conversation. Layout under `investigations/`:

  cache/fits/<fit_key>/result.json          committed numerical fit (create-once; shared by all runs)
  cache/fits/<fit_key>/attempts/<id>.json   execution attempts: running | committed | duplicate | failed | abandoned
  cache/fits/<fit_key>/profile.json         profile likelihood (create-once)
  runs/<run_id>/run.json                    run config snapshot (arm, budgets, datasets, protocol hash)
  runs/<run_id>/protocol.json, manifest.json
  runs/<run_id>/candidates/<cid>.json       candidate versions (create-once; id from the canonical chemistry)
  runs/<run_id>/submissions/<sid>.json      every submission, including duplicates and rejected ones
  runs/<run_id>/evaluations/<cid>__<fk>.json candidate x development data under one fit key (create-once)
  runs/<run_id>/reviews/<rid>/...            frozen bundles, reviews, responses
  runs/<run_id>/events.jsonl                append-only log

A fit key identifies the logical computation (dynamics x data x protocol x code). Attempts are separate records, so an
interrupted attempt never masquerades as a result, and a result committed by one attempt is reused by every later
request with the same key. Changing the code, protocol or data changes the key, so stale results are never reused.
Arbitrary shell commands run by an agent are not covered by any exactly-once promise.
"""
from __future__ import annotations

import calendar
import json
import math
import os
import socket
import time
import uuid
from pathlib import Path

from .data import canonical_json, sha256_json

ROOT_DEFAULT = Path(__file__).resolve().parents[2] / "investigations"


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + f".{int(time.time() * 1000) % 1000:03d}Z"


def _fsync_dir(d: Path):
    try:
        fd = os.open(d, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError:
        pass


def encode_nonfinite(x):
    """JSON has no inf/nan: encode them as the strings "inf", "-inf", "nan" (explicit, never silently dropped)."""
    if isinstance(x, float) and not math.isfinite(x):
        return "nan" if math.isnan(x) else ("inf" if x > 0 else "-inf")
    if isinstance(x, dict):
        return {k: encode_nonfinite(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [encode_nonfinite(v) for v in x]
    return x


def _write_tmp(path: Path, obj) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
    with open(tmp, "w") as f:
        f.write(json.dumps(encode_nonfinite(obj), indent=1, sort_keys=False, allow_nan=False) + "\n")
        f.flush()
        os.fsync(f.fileno())
    return tmp


def atomic_write_json(path: Path, obj):
    """Replace path atomically (readers see the old or the new file, never a partial one)."""
    tmp = _write_tmp(path, obj)
    os.replace(tmp, path)
    _fsync_dir(path.parent)


def create_once_json(path: Path, obj) -> bool:
    """Create path atomically if it does not exist. Returns False (and leaves the file untouched) if it does."""
    tmp = _write_tmp(path, obj)
    try:
        os.link(tmp, path)
        _fsync_dir(path.parent)
        return True
    except FileExistsError:
        return False
    finally:
        os.unlink(tmp)


def read_json(path: Path):
    return json.loads(Path(path).read_text())


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def boot_time() -> float | None:
    """Epoch seconds of the last boot (Linux), or None where unknown."""
    try:
        for line in Path("/proc/stat").read_text().splitlines():
            if line.startswith("btime "):
                return float(line.split()[1])
    except OSError:
        pass
    return None


def attempt_alive(a: dict) -> bool:
    """An attempt is alive only on this host, with a live pid, and if it started after the last boot (a pid recorded
    before a reboot may have been reused by an unrelated process)."""
    if a["host"] != socket.gethostname() or not pid_alive(a["pid"]):
        return False
    bt = boot_time()
    if bt is None:
        return True
    try:
        started = calendar.timegm(time.strptime(a["started"][:19], "%Y-%m-%dT%H:%M:%S"))  # stored in UTC
    except (KeyError, ValueError):
        return True
    return started >= bt


class FitCache:
    def __init__(self, root: Path):
        self.root = Path(root) / "cache" / "fits"

    def dir(self, key: str) -> Path:
        return self.root / key

    def result(self, key: str):
        p = self.dir(key) / "result.json"
        return read_json(p) if p.exists() else None

    def begin_attempt(self, key: str, meta: dict) -> str:
        aid = f"{time.strftime('%Y%m%dT%H%M%S', time.gmtime())}-{uuid.uuid4().hex[:8]}"
        rec = {"attempt_id": aid, "fit_key": key, "state": "running", "pid": os.getpid(), "host": socket.gethostname(),
               "started": now(), **meta}
        atomic_write_json(self.dir(key) / "attempts" / f"{aid}.json", rec)
        return aid

    def end_attempt(self, key: str, aid: str, state: str, **extra):
        p = self.dir(key) / "attempts" / f"{aid}.json"
        rec = read_json(p)
        rec.update(state=state, ended=now(), **extra)
        atomic_write_json(p, rec)

    def live_attempt(self, key: str):
        d = self.dir(key) / "attempts"
        if not d.exists():
            return None
        host = socket.gethostname()
        for p in sorted(d.glob("*.json")):
            a = read_json(p)
            if a["state"] == "running" and a["host"] == host and a["pid"] != os.getpid() and attempt_alive(a):
                return a
        return None

    def commit(self, key: str, aid: str, result: dict) -> dict:
        """Commit once. A second commit for the same key is recorded as a duplicate and checked for reproducibility."""
        body = {"fit_key": key, "committed_by_attempt": aid, "committed_at": now(), "result": result}
        if create_once_json(self.dir(key) / "result.json", body):
            self.end_attempt(key, aid, "committed")
            return {"committed": True, "result": body}
        existing = read_json(self.dir(key) / "result.json")
        same = _numeric_digest(existing["result"]) == _numeric_digest(result)
        self.end_attempt(key, aid, "duplicate", reproduced_existing=same)
        return {"committed": False, "result": existing, "reproduced": same}

    def reconcile(self) -> dict:
        """Mark attempts whose process is gone. Returns counts; never deletes anything."""
        out = {"abandoned": [], "superseded": [], "running": []}
        if not self.root.exists():
            return out
        host = socket.gethostname()
        for p in self.root.glob("*/attempts/*.json"):
            a = read_json(p)
            if a["state"] != "running":
                continue
            key = a["fit_key"]
            res = self.dir(key) / "result.json"
            if res.exists() and not attempt_alive(a):
                mine = read_json(res).get("committed_by_attempt") == a["attempt_id"]
                a.update(state="committed" if mine else "superseded", ended=now(),
                         note="committed; process ended before closing the attempt" if mine
                         else "result committed by another attempt")
                atomic_write_json(p, a)
                out["superseded"].append(a["attempt_id"])
            elif a["host"] == host and not attempt_alive(a):
                a.update(state="abandoned", ended=now(), note="process no longer alive (or started before the last boot)")
                atomic_write_json(p, a)
                out["abandoned"].append(a["attempt_id"])
            else:
                out["running"].append(a["attempt_id"])
        return out


def _numeric_digest(res: dict) -> str:
    keep = {k: v for k, v in res.items() if k not in ("timing",)}
    return sha256_json(_round(keep))


def _round(x, nd=9):
    if isinstance(x, float):
        return float(f"{x:.{nd}g}")
    if isinstance(x, dict):
        return {k: _round(v, nd) for k, v in x.items()}
    if isinstance(x, list):
        return [_round(v, nd) for v in x]
    return x


class Run:
    def __init__(self, root: Path, run_id: str):
        self.root = Path(root)
        self.id = run_id
        self.dir = self.root / "runs" / run_id
        self.cache = FitCache(self.root)

    # ---------------------------------------------------------------- basics
    def exists(self) -> bool:
        return (self.dir / "run.json").exists()

    def config(self) -> dict:
        return read_json(self.dir / "run.json")

    def protocol(self) -> dict:
        return read_json(self.dir / "protocol.json")

    def manifest(self) -> dict:
        return read_json(self.dir / "manifest.json")

    def event(self, kind: str, **payload):
        self.dir.mkdir(parents=True, exist_ok=True)
        line = canonical_json({"t": now(), "pid": os.getpid(), "type": kind, **payload}) + "\n"
        fd = os.open(self.dir / "events.jsonl", os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        try:
            os.write(fd, line.encode())
            os.fsync(fd)
        finally:
            os.close(fd)

    def events(self) -> list[dict]:
        p = self.dir / "events.jsonl"
        if not p.exists():
            return []
        out = []
        for line in p.read_text().splitlines():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:  # a torn final line from a crash is ignored, never repaired in place
                continue
        return out

    def state(self) -> dict:
        p = self.dir / "state.json"
        return read_json(p) if p.exists() else {"phase": "development"}

    def set_state(self, **kv):
        s = self.state()
        s.update(kv, updated=now())
        atomic_write_json(self.dir / "state.json", s)

    # ---------------------------------------------------------------- candidates
    def candidate_path(self, cid: str) -> Path:
        return self.dir / "candidates" / f"{cid}.json"

    def candidate(self, cid: str) -> dict:
        return read_json(self.candidate_path(cid))

    def candidates(self) -> list[dict]:
        d = self.dir / "candidates"
        return sorted((read_json(p) for p in d.glob("*.json")), key=lambda c: c["created_at"]) if d.exists() else []

    def add_submission(self, rec: dict) -> str:
        sid = f"{time.strftime('%Y%m%dT%H%M%S', time.gmtime())}-{uuid.uuid4().hex[:8]}"
        rec = dict(rec, submission_id=sid, submitted_at=now())
        create_once_json(self.dir / "submissions" / f"{sid}.json", rec)
        return sid

    def create_candidate(self, rec: dict) -> bool:
        return create_once_json(self.candidate_path(rec["candidate_id"]), rec)

    # ---------------------------------------------------------------- evaluations
    def evaluation_path(self, cid: str, fkey: str | None) -> Path:
        return self.dir / "evaluations" / f"{cid}__{(fkey or 'nofit')[:16]}.json"

    def evaluation(self, cid: str, fkey: str | None):
        p = self.evaluation_path(cid, fkey)
        return read_json(p) if p.exists() else None

    def evaluations(self) -> list[dict]:
        d = self.dir / "evaluations"
        return [read_json(p) for p in sorted(d.glob("*.json"))] if d.exists() else []
