#!/usr/bin/env python3
"""Job state on disk, so a compacted or resumed session continues from files, not memory.

    python tools/job.py init 521019-05 [--codes 26-061247 26-061248] [--slip FOLDER|FILE.xlsx] [--source x.pdf ...] [--customer 843] [--work DIR]
                                                   # --slip (default: the *_依頼.xlsx next to --source) fills codes, customer per code, material, urgency
    python tools/job.py status [JOB|DIR]           # compact summary + next step (default: current job)
    python tools/job.py set CODE [--job JOB] [--stage L2] [--status PREVIEW] [--flag "..."] [--file spec=spec.yaml] [--note "..."]
    python tools/job.py census CODE [--job JOB] [--set HOLE=YES[:evidence] ...] [--rest NO] [--source-mode PDF_ONLY] [--part-mode BEND]
                                                   # resolve_rules on make/census_<CODE>.json -> cards per stage; --set edits the census first
    python tools/job.py deliver [JOB] [--dxf FILE] [--dest DIR]   # composite DXF -> <input folder>/AI_L/ (never overwrite: _v2, _v3)
    python tools/job.py order [JOB]                # codes easiest first (from the census): the delivery order of an urgent job
    python tools/job.py deliver-code CODE [JOB] [--dest DIR]      # urgent jobs: this code's DXF -> AI_L/<CODE>.dxf as soon as it is drawn (_v2 on change)
    python tools/job.py qa [JOB] [--dest DIR]      # DWGs of the job: roles (tools/dwg_roles.py), DXF + digest into QA/
    python tools/job.py hook                       # SessionStart (compact/resume) hook: status of an open job, else silent

Work dir default: `.work/<JOB>/` in the repo (git-ignored); `.work/CURRENT` names the current job.
Layout: job_state.json; make/ = everything we build (census_<code>.json, ledger_<code>.md, spec_<code>.yaml, <JOB>_job.json, report,
out/); QA/ (only when the job has DWGs) = copies of the DWG, their DXF, digests and roles.json.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from resolve_rules import ResolutionError, census_template, resolve_rules  # noqa: E402
import dwg_roles  # noqa: E402
import slip as slip_mod  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WORK_ROOT = ROOT / ".work"
CURRENT = WORK_ROOT / "CURRENT"
STAGES = ("L0", "L1", "L2", "L3", "DONE")
MAKE, QA, AI_L = "make", "QA", "AI_L"
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


def make_dir(d: Path) -> Path:
    m = Path(d) / MAKE
    m.mkdir(parents=True, exist_ok=True)
    return m


def init(job: str, codes: list[str], sources: list[str], customer: str | None, work: str | None,
         slip: str | None = None) -> dict:
    d = Path(work) if work else WORK_ROOT / job
    d.mkdir(parents=True, exist_ok=True)
    f = d / "job_state.json"
    if f.is_file():
        raise SystemExit(f"{f} exists: use `job.py status` / `job.py set`")
    slip_data = None
    if slip or (sources and not codes):
        try:
            slip_data = slip_mod.read_slip(slip or Path(sources[0]).parent)
        except SystemExit:
            if not codes:
                raise
    rows = {r["code"]: r for r in (slip_data or {"rows": []})["rows"]}
    codes = codes or list(rows)
    if not codes:
        raise SystemExit("no codes: pass --codes or a slip with 作業No rows")
    state = {"job": job, "commit": _head(), "created": _now(), "customer_code": customer,
             "sources": sources, "codes": {}}
    if slip_data:
        state.update(slip=slip_data["file"], urgent=slip_data["urgent"], delivery_tag=slip_data["tag"])
    make = make_dir(d)
    for code in codes:
        row = rows.get(code, {})
        cust = row.get("customer_code") or customer
        census = census_template()
        census["part_code"] = code
        census["customer_code"] = cust
        _write(make / f"census_{code}.json", census)
        state["codes"][code] = {"stage": "L0", "status": "OPEN", "flags": [], "notes": [],
                                "files": {"census": f"{MAKE}/census_{code}.json"}}
        if row:
            state["codes"][code]["slip"] = {k: row.get(k) for k in (
                "customer_code", "customer_name", "material_text", "family", "surface", "t", "size_x", "size_y")}
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
    spec = c["files"].get("spec")
    if stage == "L3" and spec and "overlay" not in c["files"]:
        try:
            if re.search(r"^\s*bend:", (d / spec).read_text(encoding="utf-8-sig"), re.M):
                print(f"WARN {code}: bent part without overlay_check (tools/overlay_check.py, >=3 anchors, <=1 mm): "
                      "run it and record --file overlay=PATH, or state why it was not run")
        except OSError:
            pass
    return state


def edit_census(c: dict, sets=(), rest=None, source_mode=None, part_mode=None, reference=None, multi=None,
                customer=None, notes=()) -> dict:
    """Edit a census dict in place from CLI flags (no JSON by hand). --set FAMILY=STATE[:evidence]; --rest sets every
    family still UNKNOWN (UNKNOWN != NO: only with evidence in --rest-evidence)."""
    for kv in sets:
        key, _, val = kv.partition("=")
        state, _, ev = val.partition(":")
        if key not in c["features"] or state not in ("YES", "NO", "UNKNOWN"):
            raise SystemExit(f"--set FAMILY=YES|NO|UNKNOWN[:evidence]; families: {', '.join(c['features'])}")
        c["features"][key] = {"state": state, "evidence": [ev] if ev else c["features"][key].get("evidence", [])}
    if rest:
        if rest not in ("NO", "UNKNOWN"):
            raise SystemExit("--rest NO|UNKNOWN")
        for k, v in c["features"].items():
            if v["state"] == "UNKNOWN" and rest == "NO":
                c["features"][k] = {"state": "NO", "evidence": v.get("evidence") or ["no such note/feature on the source"]}
    for key, val in (("source_mode", source_mode), ("part_mode", part_mode), ("reference_present", reference),
                     ("multi_code_or_assembly", multi), ("customer_code", customer)):
        if val:
            c[key] = val
    for n in notes:      # text|family|resolution
        text, _, rest_ = n.partition("|")
        fam, _, res = rest_.partition("|")
        c["source_manufacturing_notes"].append({"note_text": text, "code_scope": c["part_code"],
                                                "candidate_family": fam or "IRRELEVANT",
                                                "resolution": res or "ROUTED"})
    return c


def census(job: str | None, code: str, **edits) -> dict:
    d, state = load(job)
    f = d / state["codes"][code]["files"].get("census", f"{MAKE}/census_{code}.json")
    data = json.loads(f.read_text(encoding="utf-8-sig"))
    if any(edits.get(k) for k in ("sets", "rest", "source_mode", "part_mode", "reference", "multi", "customer", "notes")):
        data = edit_census(data, **edits)
        _write(f, data)
    try:
        plan = resolve_rules(data)
    except (ResolutionError, ValueError, KeyError) as exc:
        raise SystemExit(f"ROUTING_COVERAGE_GAP / census error for {code}: {exc}")
    cards = {s: plan["stage_plans"][s]["rule_paths"] for s in plan["stage_order"]}
    state["codes"][code]["cards"] = cards
    state["codes"][code]["customer_notes"] = plan["customer_rules"].get("notes", [])
    if state["codes"][code]["stage"] == "L0":
        state["codes"][code]["stage"] = "L1"
    _write(d / "job_state.json", state)
    return {"code": code, "cards": cards, "customer_notes": state["codes"][code]["customer_notes"]}


def _is_job_dir(name: str, job: str) -> bool:
    """The job number leads the folder name; whatever follows it (customer, urgency) is ignored."""
    return re.match(rf"{re.escape(job)}(?!\d)", name) is not None


def input_dir(job: str, sources: list[str], dest: str | None = None) -> Path:
    """Where the job was received: the source folder named after the job, else its unique sibling."""
    if dest:
        return slip_mod.norm_path(dest)
    for src in sources:
        folder = slip_mod.norm_path(src).parent
        if folder.is_dir() and _is_job_dir(folder.name, job):
            return folder
    for src in sources:
        sibs = [d for d in slip_mod.norm_path(src).parent.parent.glob("*") if d.is_dir() and _is_job_dir(d.name, job)]
        if len(sibs) == 1:
            return sibs[0]
    raise SystemExit(f"input folder of job {job} unclear (sources: {sources}): pass --dest DIR")


def _round(v):
    if isinstance(v, float):
        return round(v, 5)
    if isinstance(v, (list, tuple)):
        return [_round(x) for x in v]
    return v


def _digest(path: Path) -> str:
    """Content digest: a DXF is compared by its entities (a re-export of the same drawing differs in header times/handles)."""
    try:
        import ezdxf
        items = []
        for e in ezdxf.readfile(path).modelspace():
            attrs = {k: _round(list(v) if hasattr(v, "__iter__") and not isinstance(v, str) else v)
                     for k, v in e.dxfattribs().items() if k not in ("handle", "owner")}
            if e.dxftype() == "LWPOLYLINE":
                attrs["points"] = _round([list(p) for p in e.get_points("xyseb")])
            items.append(repr((e.dxftype(), sorted(attrs.items()))))
        return hashlib.sha256("\n".join(sorted(items)).encode("utf-8")).hexdigest()
    except Exception:
        return hashlib.sha256(path.read_bytes()).hexdigest()


def ai_l_dir(job: str, sources: list[str], dest: str | None = None) -> Path:
    """<input folder>/AI_L: the only place deliveries go (created on first use)."""
    inbox = input_dir(job, sources, dest)
    if not inbox.is_dir():
        raise SystemExit(f"{inbox} is not a folder")
    out = inbox / AI_L
    out.mkdir(exist_ok=True)
    return out


def _put(src: Path, target_dir: Path, stem: str) -> Path | None:
    """Copy src to target_dir/<stem>.dxf; never overwrite (_v2, _v3 ...), never repeat identical content."""
    same = [f for f in target_dir.glob(f"{stem}*.dxf") if re.fullmatch(rf"{re.escape(stem)}(_v\d+)?\.dxf", f.name)]
    if any(f.is_file() and _digest(f) == _digest(src) for f in same):
        print(f"already delivered (identical content): {target_dir}")
        return None
    out, n = target_dir / f"{stem}.dxf", 1
    while out.exists():
        n += 1
        out = target_dir / f"{stem}_v{n}.dxf"
    shutil.copyfile(src, out)
    return out


def deliver(job: str | None, dxf: str | None = None, dest: str | None = None) -> Path | None:
    """Copy the composite DXF to <input folder>/AI_L; never overwrite (_v2, _v3 ...), never repeat identical content."""
    d, state = load(job)
    name_re = re.compile(rf"{re.escape(state['job'])}_ALL(_REVIEW_ONLY)?\.dxf")
    if dxf:
        src = Path(dxf)
    else:
        found = [f for f in d.rglob("*.dxf") if name_re.fullmatch(f.name) and AI_L not in f.parts]
        if not found:
            raise SystemExit(f"no {state['job']}_ALL[_REVIEW_ONLY].dxf under {d}: pass --dxf FILE")
        src = max(found, key=lambda f: f.stat().st_mtime)
    if not name_re.fullmatch(src.name):
        raise SystemExit(f"{src.name} is not the composite {state['job']}_ALL[_REVIEW_ONLY].dxf")
    out = _put(src, ai_l_dir(state["job"], state.get("sources", []), dest), src.stem)
    if out:
        state.setdefault("delivered", []).append({"file": str(out), "time": _now()})
        _write(d / "job_state.json", state)
        print(f"delivered: {out}")
    return out


def job_json_path(d: Path, job: str) -> Path:
    for c in (d / MAKE / f"{job}_job.json", d / f"{job}_job.json"):
        if c.is_file():
            return c
    raise SystemExit(f"{job}_job.json not found under {d}: run tools/run_job.py first")


def deliver_code(job: str | None, code: str, dest: str | None = None) -> Path | None:
    """Urgent jobs (Express / とても急ぎます): the DXF of ONE code, in the same form as the composite (PREVIEW codes too),
    straight into AI_L as <CODE>.dxf as soon as it is drawn; a changed redraw becomes <CODE>_v2.dxf."""
    d, state = load(job)
    if code not in state["codes"]:
        raise SystemExit(f"{code} is not in job {state['job']} (codes: {', '.join(state['codes'])})")
    data = json.loads(job_json_path(d, state["job"]).read_text(encoding="utf-8-sig"))
    parts = [p for p in data["parts"] if p["code"] == code]
    if not parts:
        raise SystemExit(f"{code} is not built yet in {state['job']}_job.json")
    from export_canonical_dxf import export_canonical_job   # noqa: E402  (heavy import only when delivering)
    with tempfile.TemporaryDirectory(prefix="deliver_code_") as tmp:
        manifest = export_canonical_job({**data, "parts": parts}, Path(tmp), require_slip_codes=True)
        out = _put(Path(tmp) / manifest["filename"], ai_l_dir(state["job"], state.get("sources", []), dest), code)
    if out:
        state.setdefault("delivered", []).append({"file": str(out), "code": code, "time": _now()})
        _write(d / "job_state.json", state)
        print(f"delivered: {out}")
    return out


def qa_prepare(job: str | None, dest: str | None = None) -> dict:
    """QA/ of the job: every DWG of the input folder copied, converted to DXF, digested, with the roles of tools/dwg_roles.py."""
    import dwg_to_dxf
    import dxf_digest
    d, state = load(job)
    inbox = input_dir(state["job"], state.get("sources", []), dest)
    files = {f.name.lower(): f for f in [*inbox.glob("*.dwg"), *inbox.glob("*.DWG")]}
    roles = dwg_roles.classify(sorted(files.values()), state["job"])
    qa = d / QA
    qa.mkdir(exist_ok=True)
    for item in roles["files"]:
        src = Path(item["file"])
        shutil.copyfile(src, qa / src.name)
        dxf = dwg_to_dxf.convert(src, qa / f"{src.stem}.dxf")
        (qa / f"{src.stem}.digest.json").write_text(
            json.dumps(dxf_digest.digest(str(dxf)), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        item["dxf"] = str(dxf)
    _write(qa / "roles.json", roles)
    state["qa"] = {"sample": roles["sample"], "qa_target": roles["qa_target"], "time": _now()}
    _write(d / "job_state.json", state)
    return roles


_FAMILY_WEIGHT = {"HOLE": 1, "TAP": 2, "PIASU": 1, "SLOT_STRAIGHT": 2, "CURVED_SLOT": 3, "KEGAKI": 3, "RIB": 3,
                  "FORMING_FEATURES": 4, "SLIT_RELIEF": 1, "ACUTE_BEND_LT85": 3, "BOXMET": 3}
_MODE_WEIGHT = {"FLAT_NO_BEND": 0, "BEND": 3, "MULTI_FACE": 5, "UNKNOWN": 4}


def difficulty(census: dict) -> tuple[float, list[str]]:
    """Rough effort of one code from its census (lower = draw first): bend mode, families YES (UNKNOWN counts half), assembly."""
    why = []
    score = _MODE_WEIGHT.get(census.get("part_mode"), 4)
    why.append(f"{census.get('part_mode')}={score}")
    for fam, v in (census.get("features") or {}).items():
        w = _FAMILY_WEIGHT.get(fam, 1) * {"YES": 1.0, "UNKNOWN": 0.5}.get(v.get("state"), 0.0)
        if w:
            score += w
            why.append(f"{fam}:{v['state']}")
    if census.get("multi_code_or_assembly") == "YES":
        score += 2
        why.append("assembly")
    if census.get("source_mode") == "PDF_DATA_RAW":
        score += 1
        why.append("DATA")
    unresolved = sum(n.get("resolution") == "UNRESOLVED" for n in census.get("source_manufacturing_notes", []))
    if unresolved:
        score += unresolved
        why.append(f"{unresolved} note UNRESOLVED")
    return score, why


def order(job: str | None = None) -> list[dict]:
    """Codes of the job, easiest first (urgent jobs deliver in this order): from the filled census, ties by slip order."""
    d, state = load(job)
    rows = []
    for i, (code, c) in enumerate(state["codes"].items()):
        f = d / c["files"].get("census", f"{MAKE}/census_{code}.json")
        try:
            score, why = difficulty(json.loads(f.read_text(encoding="utf-8-sig")))
        except OSError:
            score, why = 99.0, ["no census"]
        rows.append({"code": code, "score": score, "why": why, "stage": c["stage"], "slip_index": i})
    rows.sort(key=lambda r: (r["stage"] == "DONE", r["score"], r["slip_index"]))
    state["order"] = [r["code"] for r in rows]
    _write(d / "job_state.json", state)
    return rows


def summary(job: str | None = None) -> str:
    d, state = load(job)
    head = _head()
    lines = [f"JOB {state['job']}  work={d}  customer={state.get('customer_code')}"]
    if "urgent" in state:
        lines.append("DELIVERY: " + ("URGENT (%s): deliver each code as soon as it is drawn (`job.py deliver-code CODE`), easy codes "
                                     "first, composite at the end" % state.get("delivery_tag")
                                     if state["urgent"] else "default: one composite (`job.py deliver`) into AI_L"))
    if state.get("commit") and head and head != state["commit"]:
        lines.append(f"WARNING: repo HEAD {head[:9]} != pinned {state['commit'][:9]} (do not change rules mid-job)")
    lines.append("Re-read JOB_CARD.md, then the cards listed for the current stage.")
    for code, c in state["codes"].items():
        files = ", ".join(f"{k}={v}" for k, v in c["files"].items())
        sl = c.get("slip")
        who = f"  [{sl['customer_code']} {sl['material_text']} t{sl['t']}]" if sl else ""
        lines.append(f"- {code}: {c['stage']} {c['status']}{who}  files: {files}")
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
    i.add_argument("--codes", nargs="+", default=[], help="slip work numbers (作業No), e.g. 26-061247 (default: all of the slip)")
    i.add_argument("--slip", help="job folder or <JOB>_依頼.xlsx (default: the one next to --source)")
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
    c.add_argument("--set", action="append", default=[], dest="sets", metavar="FAMILY=STATE[:EVIDENCE]")
    c.add_argument("--rest", choices=("NO", "UNKNOWN"), help="every family still UNKNOWN becomes this (NO needs evidence you checked)")
    c.add_argument("--source-mode")
    c.add_argument("--part-mode")
    c.add_argument("--reference", choices=("YES", "NO", "UNKNOWN"))
    c.add_argument("--multi", choices=("YES", "NO", "UNKNOWN"))
    c.add_argument("--customer")
    c.add_argument("--note", action="append", default=[], dest="notes", metavar="TEXT|FAMILY|RESOLUTION")
    v = sub.add_parser("deliver")
    v.add_argument("job", nargs="?")
    v.add_argument("--dxf", help="composite DXF (default: newest <JOB>_ALL[_REVIEW_ONLY].dxf under the work dir)")
    v.add_argument("--dest", help="input folder (default: the job folder named 52xxxx-xx next to the sources)")
    o = sub.add_parser("order")
    o.add_argument("job", nargs="?")
    dc = sub.add_parser("deliver-code")
    dc.add_argument("code")
    dc.add_argument("job", nargs="?")
    dc.add_argument("--dest", help="input folder (default: next to the sources)")
    q = sub.add_parser("qa")
    q.add_argument("job", nargs="?")
    q.add_argument("--dest", help="input folder holding the DWGs (default: next to the sources)")
    sub.add_parser("hook")
    a = ap.parse_args(argv)
    if a.cmd == "hook":
        text = hook_text()
        if text:
            print(text)
        return 0
    if a.cmd == "init":
        init(a.job, a.codes, a.source, a.customer, a.work, a.slip)
        print(summary(a.work or a.job))
    elif a.cmd == "deliver":
        deliver(a.job, a.dxf, a.dest)
    elif a.cmd == "order":
        for r in order(a.job):
            print(f"{r['score']:5.1f}  {r['code']}  {r['stage']}  {', '.join(r['why'])}")
    elif a.cmd == "deliver-code":
        deliver_code(a.job, a.code, a.dest)
    elif a.cmd == "qa":
        roles = qa_prepare(a.job, a.dest)
        for i in roles["files"]:
            print(f"{i['role']:9} {Path(i['file']).name}  creator={i['creator']} checker={i.get('checker_name')}  -> {i['dxf']}")
        print(f"sample={roles['sample']}  qa_target={roles['qa_target']}")
    elif a.cmd == "status":
        print(summary(a.job))
    elif a.cmd == "set":
        set_code(a.job, a.code, a.stage, a.status, a.flag, a.file, a.note)
        print(summary(a.job))
    else:
        print(json.dumps(census(a.job, a.code, sets=a.sets, rest=a.rest, source_mode=a.source_mode, part_mode=a.part_mode,
                                reference=a.reference, multi=a.multi, customer=a.customer, notes=a.notes),
                         ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):
        _stream.reconfigure(encoding="utf-8")  # Vietnamese FLAG text on a Windows console
    raise SystemExit(main())
