"""Per-run cost summary read back from the events a run already persists (read-only)."""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

TOKENS = {"input_tokens": "input_tokens", "output_tokens": "output_tokens",
          "cache_read_input_tokens": "cache_read", "cache_creation_input_tokens": "cache_creation"}
EMPTY = {"calls": 0, "prompt_characters": 0, "shared_context_characters": 0,
         "input_tokens": 0, "output_tokens": 0, "cache_read": 0, "cache_creation": 0}


def _label(payload):
    stage, code = payload.get("stage") or "?", payload.get("code")
    return stage if not code else f"{stage}:{code}"


def summarize(db_path, run_id=None):
    db = sqlite3.connect(str(Path(db_path).resolve()))
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA query_only=ON")
    try:
        if run_id is None:
            latest = db.execute("SELECT id FROM runs ORDER BY created DESC LIMIT 1").fetchone()
            if latest is None:
                raise ValueError("No runs recorded")
            run_id = latest["id"]
        run = db.execute("SELECT id, status, error FROM runs WHERE id=?", (run_id,)).fetchone()
        if run is None:
            raise ValueError("Unknown run " + str(run_id))
        events = db.execute("SELECT kind, payload, created FROM events WHERE run_id=? ORDER BY id", (run_id,)).fetchall()
    finally:
        db.close()

    rows, owner, parts, errors = {}, {}, {}, {}
    for event in events:
        payload = json.loads(event["payload"])
        if event["kind"] == "request_prepared":
            label = _label(payload)
            owner[payload.get("request_id")] = label
            row = rows.setdefault(label, dict(EMPTY))
            row["calls"] += 1
            row["prompt_characters"] += payload.get("prompt_characters", 0)
            row["shared_context_characters"] += payload.get("shared_context_characters", 0)
        elif event["kind"] == "usage":
            label = owner.get(str(payload.get("event_key", "")).split(":", 1)[0])
            if label is not None:
                for source, target in TOKENS.items():
                    rows[label][target] += payload.get("metrics", {}).get(source, 0)
        elif event["kind"] == "part_complete":
            parts[payload["code"]] = {"status": payload["status"], "attempts": payload["attempts"]}
        elif event["kind"] == "validation_error":
            key = f"{payload.get('code')}: {payload.get('signature')}"
            errors[key] = max(errors.get(key, 0), payload.get("count", 1))
    totals = {key: sum(row[key] for row in rows.values()) for key in EMPTY}
    return {
        "run_id": run["id"],
        "status": run["status"],
        "error": run["error"],
        "wall_seconds": round(events[-1]["created"] - events[0]["created"], 3) if events else 0,
        "by_stage_code": rows,
        "totals": totals,
        "parts": parts,
        "repeated_errors": errors,
    }


def _format(out):
    lines = [f"run {out['run_id']} status={out['status']} wall={out['wall_seconds']:.0f}s",
             f"{'stage:code':28} {'calls':>5} {'create':>9} {'read':>10} {'output':>8} {'prompt':>9} {'shared':>9}"]
    for label, r in out["by_stage_code"].items():
        lines.append(f"{label:28} {r['calls']:>5} {r['cache_creation']:>9} {r['cache_read']:>10} "
                     f"{r['output_tokens']:>8} {r['prompt_characters']:>9} {r['shared_context_characters']:>9}")
    t = out["totals"]
    lines.append(f"{'TOTAL':28} {t['calls']:>5} {t['cache_creation']:>9} {t['cache_read']:>10} "
                 f"{t['output_tokens']:>8} {t['prompt_characters']:>9} {t['shared_context_characters']:>9}")
    for code, info in out["parts"].items():
        lines.append(f"part {code}: {info['status']} after {info['attempts']} attempt(s)")
    for key, count in out["repeated_errors"].items():
        lines.append(f"repeated validation error x{count} - {key}")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("database", type=Path, help="path to state.sqlite")
    ap.add_argument("--run", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    out = summarize(args.database, args.run)
    print(json.dumps(out, indent=2) if args.json else _format(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
