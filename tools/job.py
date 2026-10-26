#!/usr/bin/env python3
"""Job state on disk, so a compacted or resumed session continues from files, not memory.

    python tools/job.py init 521019-05 --codes 26-061247 26-061248 [--source x.pdf ...] [--customer 843] [--work DIR]
    python tools/job.py status [JOB|DIR]           # compact summary + next step (default: current job)
    python tools/job.py set CODE [--job JOB] [--stage L2] [--status PREVIEW] [--flag "..."] [--file spec=spec.yaml] [--note "..."]
    python tools/job.py census CODE [--job JOB]    # resolve_rules on census_<CODE>.json -> cards per stage
    python tools/job.py hook                       # SessionStart (compact/resume) hook: status of an open job, else silent

Work dir default: `.work/<JOB>/` in the repo (git-ignored); `.work/CURRENT` names the current job.
Files per code: census_<code>.json, ledger_<code>.md, spec_<code>.yaml / job.json — written by you as you go.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from resolve_rules import ResolutionError, census_template, resolve_rules  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WORK_ROOT = ROOT / ".work"
CURRENT = WORK_ROOT / "CURRENT"
STAGES = ("L0", "L1", "L2", "L3", "DONE")
NEXT = {
    "L0": "L1: read rules/READ_SOURCE.md + rules/CENSUS.md, inspect the source, fill census_<code>.json, run `job.py census <code>`",
    "L1": "L2: read the L2 cards from `job.py census`, build the ledger and spec/canonical part",
    "L2": "L3: read rules/VALIDATE.md + rules/OUTPUT.md, run the checks and export",
    "L3": "Report: rules/OUTPUT.md §8",
    "DONE": "nothing left for this code",
}


def _now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def _head() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _write(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")


def work_dir(job: str | None = None) -> Path:
    if job:
        p = Path(job)
        return p if (p / "job_state.json").is_file() else WORK_ROOT / job
    if not CURRENT.is_file():
        raise SystemExit("no current job: run `python tools/job.py init <JOB> --codes ...` first")
    return Path(CURRENT.read_text(encoding="utf-8-sig").strip())


def load(job: str | None = None) -> tuple[Path, dict]:
    d = work_dir(job)
    f = d / "job_state.json"
    if not f.is_file():
        raise SystemExit(f"{f} not found")
    return d, json.loads(f.read_text(encoding="utf-8-sig"))


def init(job: str, codes: list[str], sources: list[str], customer: str | None, work: str | None) -> dict:
    d = Path(work) if work else WORK_ROOT / job
    d.mkdir(parents=True, exist_ok=True)
    f = d / "job_state.json"
    if f.is_file():
        raise SystemExit(f"{f} exists: use `job.py status` / `job.py set`")
    state = {"job": job, "commit": _head(), "created": _now(), "customer_code": customer,
             "sources": sources, "codes": {}}
    for code in codes:
        census = census_template()
        census["part_code"] = code
        census["customer_code"] = customer
        _write(d / f"census_{code}.json", census)
        state["codes"][code] = {"stage": "L0", "status": "OPEN", "flags": [], "files": {"census": f"census_{code}.json"},
                                "notes": []}
    _write(f, state)
    WORK_ROOT.mkdir(exist_ok=True)
    CURRENT.write_text(str(d.resolve()) + "\n", encoding="utf-8")
    return state


def set_code(job: str | None, code: str, stage=None, status=None, flags=(), files=(), notes=()) -> dict:
    d, state = load(job)
    if code not in state["codes"]:
        raise SystemExit(f"{code} is not in job {state['job']} (codes: {', '.join(state['codes'])})")
    c = state["codes"][code]
    if stage:
        if stage not in STAGES:
            raise SystemExit(f"stage must be one of {STAGES}")
        c["stage"] = stage
    if status:
        c["status"] = status
    c["flags"] += [f for f in flags if f not in c["flags"]]
    for kv in files:
        key, _, val = kv.partition("=")
        if not val:
            raise SystemExit("--file needs key=path")
        c["files"][key] = val
    c["notes"] += list(notes)
    c["updated"] = _now()
    _write(d / "job_state.json", state)
    return state


def census(job: str | None, code: str) -> dict:
    d, state = load(job)
    f = d / state["codes"][code]["files"].get("census", f"census_{code}.json")
    try:
        plan = resolve_rules(json.loads(f.read_text(encoding="utf-8-sig")))
    except (ResolutionError, ValueError, KeyError) as exc:
        raise SystemExit(f"ROUTING_COVERAGE_GAP / census error for {code}: {exc}")
    cards = {s: plan["stage_plans"][s]["rule_paths"] for s in plan["stage_order"]}
    state["codes"][code]["cards"] = cards
    state["codes"][code]["customer_notes"] = plan["customer_rules"].get("notes", [])
    if state["codes"][code]["stage"] == "L0":
        state["codes"][code]["stage"] = "L1"
    _write(d / "job_state.json", state)
    return {"code": code, "cards": cards, "customer_notes": state["codes"][code]["customer_notes"]}


def summary(job: str | None = None) -> str:
    d, state = load(job)
    head = _head()
    lines = [f"JOB {state['job']}  work={d}  customer={state.get('customer_code')}"]
    if state.get("commit") and head and head != state["commit"]:
        lines.append(f"WARNING: repo HEAD {head[:9]} != pinned {state['commit'][:9]} (do not change rules mid-job)")
    lines.append("Re-read JOB_CARD.md, then the cards listed for the current stage.")
    for code, c in state["codes"].items():
        files = ", ".join(f"{k}={v}" for k, v in c["files"].items())
        lines.append(f"- {code}: {c['stage']} {c['status']}  files: {files}")
        cards = c.get("cards", {})
        stage_key = {"L1": "L1_SOURCE_CENSUS", "L2": "L2_GEOMETRY", "L3": "L3_VALIDATE_EXPORT_QA"}.get(c["stage"])
        if stage_key and cards.get(stage_key):
            lines.append(f"    cards now: {', '.join(cards[stage_key])}")
        for fl in c["flags"]:
            lines.append(f"    FLAG: {fl}")
        if c["notes"]:
            lines.append(f"    note: {c['notes'][-1]}")
        lines.append(f"    next: {NEXT[c['stage']]}")
    return "\n".join(lines)


def hook_text() -> str:
    """Context for a resumed/compacted session: the open job's status, or nothing."""
    try:
        _, state = load(None)
    except SystemExit:
        return ""
    if all(c["stage"] == "DONE" for c in state["codes"].values()):
        return ""
    return ("TrainAiCad: a CAD job is in progress. Continue from its files, not from memory:\n"
            + summary(None))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("init")
    i.add_argument("job")
    i.add_argument("--codes", nargs="+", required=True, help="slip work numbers (作業No), e.g. 26-061247")
    i.add_argument("--source", nargs="*", default=[])
    i.add_argument("--customer", help="numeric customer code from JOB STATISTICS")
    i.add_argument("--work", help="work directory (default .work/<JOB>)")
    s = sub.add_parser("status")
    s.add_argument("job", nargs="?")
    t = sub.add_parser("set")
    t.add_argument("code")
    t.add_argument("--job")
    t.add_argument("--stage", choices=STAGES)
    t.add_argument("--status")
    t.add_argument("--flag", action="append", default=[])
    t.add_argument("--file", action="append", default=[], metavar="KEY=PATH")
    t.add_argument("--note", action="append", default=[])
    c = sub.add_parser("census")
    c.add_argument("code")
    c.add_argument("--job")
    sub.add_parser("hook")
    a = ap.parse_args(argv)
    if a.cmd == "hook":
        text = hook_text()
        if text:
            print(text)
        return 0
    if a.cmd == "init":
        init(a.job, a.codes, a.source, a.customer, a.work)
        print(summary(a.work or a.job))
    elif a.cmd == "status":
        print(summary(a.job))
    elif a.cmd == "set":
        set_code(a.job, a.code, a.stage, a.status, a.flag, a.file, a.note)
        print(summary(a.job))
    else:
        print(json.dumps(census(a.job, a.code), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):
        _stream.reconfigure(encoding="utf-8")  # Vietnamese FLAG text on a Windows console
    raise SystemExit(main())
