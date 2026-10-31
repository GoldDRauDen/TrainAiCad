"""Find past app runs from Claude Code or a terminal: where each run's transcript, report and .work copy are.

    python -m luan_app.runs                 # latest runs
    python -m luan_app.runs 521031-03       # search: job, code, FLAG text, summary words
    python -m luan_app.runs --id 4          # one run: its files, codes and result
"""
from __future__ import annotations

import argparse
import json
import sys

from .config import load_paths
from .store import Store


def _files(paths, run: dict) -> dict:
    d = paths.runs_dir / f"{int(run['id']):06d}"
    work = d / "work" / (run.get("job") or "")
    return {"folder": str(d), "transcript": str(d / "transcript.jsonl"), "report": str(d / "out" / "report.md"),
            "result": str(d / "out" / "result.json"), "work": str(work) if work.is_dir() else None,
            "job_state": str(work / "job_state.json") if (work / "job_state.json").is_file() else None}


def _line(r: dict) -> str:
    model = (r.get("usage") or {}).get("model") or ""
    return (f"#{r['id']:<4} {r['kind']:<3} {r.get('job') or '?':<10} {r['status']:<9} {(r.get('ended_at') or '')[:16]:<16} "
            f"{r.get('user_name') or 'Admin':<10} {model:<18} {(r.get('summary') or '')[:90]}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("query", nargs="*", help="words to search (job, code, FLAG, summary)")
    ap.add_argument("--id", type=int, help="show one run in full (JSON)")
    ap.add_argument("--limit", type=int, default=30)
    a = ap.parse_args(argv)
    paths = load_paths()
    store = Store(paths.db_path)
    if a.id is not None:
        r = store.get_run(a.id)
        if not r:
            print(f"không có lượt #{a.id}", file=sys.stderr)
            return 1
        keep = ("id", "kind", "job", "path", "status", "user_name", "queued_at", "started_at", "ended_at", "summary",
                "error", "codes", "result", "usage", "delivered", "warnings", "commit", "rerun_of", "resume_of")
        print(json.dumps({**{k: r.get(k) for k in keep}, "files": _files(paths, r)}, ensure_ascii=False, indent=1))
        return 0
    rows = store.list_runs(q=" ".join(a.query) or None, limit=a.limit)
    for r in rows:
        print(_line(r))
        print("      " + _files(paths, r)["folder"])
    if not rows:
        print("không tìm thấy lượt chạy nào")
    return 0


if __name__ == "__main__":
    sys.exit(main())
