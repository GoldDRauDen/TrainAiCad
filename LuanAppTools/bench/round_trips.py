"""Count provider rounds per code and tool requests per tool for a stored run (read-only).

Every host tool request costs one more provider call that re-reads the whole conversation, so this shows where
rounds go before deciding which tool is worth building. It never writes to the state database.

    python -m LuanAppTools.bench.round_trips [--state-dir DIR] [--run RUN_ID]
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
from collections import Counter
from pathlib import Path


def default_state_dir():
    return Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "LuanAppTools"


def summarize(db, run_id=None):
    run = db.execute(
        "SELECT id, job_id, status, checkpoint FROM runs " + ("WHERE id=?" if run_id else "ORDER BY created DESC LIMIT 1"),
        (run_id,) if run_id else ()).fetchone()
    if run is None:
        raise SystemExit("No run found")
    rounds = Counter()
    for kind, payload in db.execute("SELECT kind, payload FROM events WHERE run_id=?", (run["id"],)):
        if kind == "request_prepared":
            data = json.loads(payload)
            rounds[(data.get("stage"), data.get("code") or "-")] += 1
    tools = Counter()
    checkpoint = json.loads(run["checkpoint"] or "{}")
    for key, agent in checkpoint.items():
        if key == "agent" or key.startswith("agent:"):
            for turn in agent.get("turns", []):
                for call in (turn.get("answer") or {}).get("tool_requests", []) or []:
                    tools[call.get("name", "?")] += 1
    return {"run": run["id"], "job": run["job_id"], "status": run["status"], "rounds": rounds, "tools": tools}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--state-dir", type=Path, default=default_state_dir())
    ap.add_argument("--run")
    a = ap.parse_args(argv)
    database = (a.state_dir / "state.sqlite").resolve()
    db = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    result = summarize(db, a.run)
    print(f"run {result['run'][:8]} job {result['job'][:8]} status {result['status']}")
    print("provider rounds per (stage, code):")
    for (stage, code), count in sorted(result["rounds"].items(), key=lambda item: (str(item[0][0]), str(item[0][1]))):
        print(f"  {stage:8} {code:12} {count}")
    print(f"  total {sum(result['rounds'].values())}")
    print("tool requests by name (whole conversation):")
    for name, count in result["tools"].most_common():
        print(f"  {name:14} {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
