"""Read what a run produced: job_state.json, AI_L deliveries, result.json, review_items.json; decide the final status."""
from __future__ import annotations

import datetime as dt
import glob
import json
import os
from pathlib import Path

REVIEW_TYPES = {"NEW_LESSON", "NEED_SAMPLE_DXF"}
RANK = {"DONE": 0, "REVIEW": 1, "ERROR": 2}


def _load(p) -> dict | list | None:
    try:
        return json.loads(Path(p).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None


def find_job_state(slot_dir: Path, job: str | None) -> dict | None:
    work = Path(slot_dir) / ".work"
    if job:
        named = _load(work / job / "job_state.json")
        if isinstance(named, dict):
            return named
    found = []
    for f in glob.glob(str(work / "*" / "job_state.json")):
        d = _load(f)
        if isinstance(d, dict):
            found.append((os.path.getmtime(f), d))
    if not found:
        return None
    found.sort(key=lambda x: x[0], reverse=True)
    return next((d for _, d in found if d.get("job") == job), found[0][1])


def code_rows(job_state: dict | None) -> list[dict]:
    if not job_state:
        return []
    rows = []
    for code, c in (job_state.get("codes") or {}).items():
        flags = [str(f) for f in (c.get("flags") or [])]
        rows.append({"code": code, "stage": c.get("stage"), "status": c.get("status"), "flags": len(flags), "flag_texts": flags})
    return rows


def delivered(job_dir: str, since_iso: str | None) -> list[str]:
    since = dt.datetime.fromisoformat(since_iso).timestamp() if since_iso else 0
    out = []
    for f in glob.glob(os.path.join(job_dir, "AI_L", "*.dxf")):
        try:
            if os.path.getmtime(f) >= since:
                out.append(f)
        except OSError:
            pass
    return sorted(out)


def read_result(out_dir) -> dict | None:
    d = _load(Path(out_dir) / "result.json")
    if isinstance(d, dict) and d.get("verdict") in ("OK", "ISSUES"):
        return d
    return None


def read_review_items(out_dir) -> tuple[list[dict], list[str]]:
    f = Path(out_dir) / "review_items.json"
    if not f.is_file():
        return [], []
    data = _load(f)
    if not isinstance(data, list):
        return [], ["review_items.json không đọc được"]
    items, warns = [], []
    for i, it in enumerate(data, 1):
        if isinstance(it, dict) and it.get("type") in REVIEW_TYPES and str(it.get("title") or "").strip():
            items.append({k: (str(it[k]) if it.get(k) is not None else None)
                          for k in ("type", "code", "card", "title", "detail", "evidence")})
        else:
            warns.append(f"Bỏ mục chờ duyệt sai định dạng #{i}")
    return items, warns


def _rows_summary(rows: list[dict]) -> str:
    if not rows:
        return ""
    n = len(rows)
    passed = sum(r["status"] == "PASS" for r in rows)
    parts = [f"{passed}/{n} PASS"]
    others: dict[str, int] = {}
    for r in rows:
        if r["status"] != "PASS":
            others[r["status"] or "?"] = others.get(r["status"] or "?", 0) + 1
    parts += [f"{v} {k}" for k, v in others.items()]
    flags = sum(r["flags"] for r in rows)
    if flags:
        parts.append(f"{flags} FLAG")
    return " · ".join(parts)


def final_status(kind, job_state, result, delivered_files, exit_code, cancelled) -> tuple[str, str]:
    rows = code_rows(job_state)
    summary = (result or {}).get("summary") or _rows_summary(rows)
    if cancelled:
        return "CANCELLED", summary or "Đã hủy"
    if exit_code not in (0, None):
        return "ERROR", summary or f"Claude thoát với mã {exit_code}"
    if kind == "QA":
        if not result:
            return "ERROR", "Không có kết quả QA (result.json)"
        return ("DONE" if result["verdict"] == "OK" else "REVIEW"), summary
    if not job_state:
        return "ERROR", "Không có job_state.json — job chưa được khởi tạo"
    if not delivered_files:
        return "ERROR", (summary + " · " if summary else "") + "chưa giao DXF vào AI_L"
    state_s = "DONE" if rows and all(r["status"] == "PASS" for r in rows) else "REVIEW"
    res_s = {"OK": "DONE", "ISSUES": "REVIEW"}.get((result or {}).get("verdict"), "DONE")
    return max(state_s, res_s, key=RANK.get), summary


def search_text(run: dict, rows: list[dict], result: dict | None) -> str:
    parts = [run.get("job") or "", run.get("kind") or "", (result or {}).get("summary") or ""]
    for r in rows:
        parts.append(r["code"])
        parts.extend(r["flag_texts"])
    return " ".join(p for p in parts if p)
