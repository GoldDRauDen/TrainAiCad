"""Job paths: normalisation, allowed roots, slip (`*_依頼.xlsx`) -> code list."""
from __future__ import annotations

import os
import re
import sys

from .config import REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "tools"))
import slip as slip_mod  # noqa: E402

DRAWING_EXT = {".pdf", ".dxf", ".dwg", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".xlsx"}
JOB_RE = re.compile(r"\d{6}-\d{2}")


class SourceError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def clean(path: str) -> str:
    """Windows form: no quotes/space around, `\\` separators, no doubled or trailing `\\` (UNC prefix kept)."""
    p = (path or "").strip().strip('"').strip("'").strip().replace("/", "\\")
    unc = p.startswith("\\\\")
    body = re.sub(r"\\{2,}", r"\\", p.lstrip("\\") if unc else p)
    p = ("\\\\" + body) if unc else body
    if len(p) > 3 or not re.fullmatch(r"[A-Za-z]:\\", p):
        p = p.rstrip("\\") or p
    return p


def path_key(path: str) -> str:
    return clean(path).casefold()


def native(path: str) -> str:
    """The cleaned path as this OS opens it (posix: `/`; Windows UNC: forward slashes, see tools/slip.norm_path)."""
    p = clean(path)
    if os.name != "nt" or p.startswith("\\\\"):
        return p.replace("\\", "/")
    return p


def is_allowed(path: str, roots: list[str]) -> bool:
    k = path_key(path)
    for root in roots or []:
        r = path_key(root)
        if r and (k == r or k.startswith(r.rstrip("\\") + "\\")):
            return True
    return False


def _listdir(p: str) -> list[str]:
    try:
        return os.listdir(p)
    except OSError as e:
        raise SourceError("Không tìm thấy hoặc không đọc được thư mục.") from e


def inspect(path: str, roots: list[str], kind: str = "RUN") -> dict:
    cleaned = clean(path)
    if not cleaned or "\n" in cleaned or "\r" in cleaned:
        raise SourceError("Đường dẫn không hợp lệ.")
    if not is_allowed(cleaned, roots):
        raise SourceError("Đường dẫn không nằm trong thư mục được phép.")
    fs = native(cleaned)
    if os.path.isfile(fs):
        if kind != "QA" or not fs.lower().endswith(".dxf"):
            raise SourceError("Cần đường dẫn thư mục job." if kind != "QA" else "QA nhận thư mục job hoặc một file .dxf.")
        parent = os.path.dirname(fs)
        if os.path.basename(parent).upper() == "AI_L":
            parent = os.path.dirname(parent)
        job_fs = parent
    elif os.path.isdir(fs):
        job_fs = fs
    else:
        raise SourceError("Không tìm thấy hoặc không đọc được thư mục.")
    names = _listdir(job_fs)
    if not any(os.path.splitext(n)[1].lower() in DRAWING_EXT for n in names):
        raise SourceError("Thư mục không có bản vẽ (PDF/DXF/DWG/ảnh).")

    folder = os.path.basename(job_fs.rstrip("/\\"))
    info = {"path": cleaned, "path_key": path_key(cleaned), "job_dir": job_fs if os.name != "nt" else clean(job_fs),
            "job": None, "has_slip": False, "urgent": False, "tag": None, "codes": [], "warnings": []}
    try:
        data = slip_mod.read_slip(job_fs)
    except (SystemExit, Exception):  # no slip, two slips, locked file, unexpected layout
        data = None
        info["warnings"].append("Không đọc được phiếu 依頼 — sẽ làm tất cả mã.")
    if data:
        info.update(has_slip=True, urgent=bool(data.get("urgent")), tag=data.get("tag"), job=data.get("job"))
        for r in data["rows"]:
            sx, sy = r.get("size_x"), r.get("size_y")
            info["codes"].append({"code": r["code"], "material": r.get("material_text") or "", "family": r.get("family"),
                                  "t": r.get("t"), "size": f"{sx:g}×{sy:g}" if _num(sx) and _num(sy) else ""})
    if not info["job"] or not JOB_RE.fullmatch(str(info["job"])):
        m = JOB_RE.search(folder)
        info["job"] = info["job"] or (m.group(0) if m else folder)
    return info


def _num(v) -> bool:
    return isinstance(v, (int, float)) and v > 0


def validate_codes(selected: list[str] | None, info: dict) -> list[str] | None:
    """None = every code. A selection must come from the slip."""
    if not selected:
        return None
    known = [c["code"] for c in info.get("codes", [])]
    for code in selected:
        if code not in known:
            raise SourceError(f"Mã {code} không có trong phiếu.")
    if set(selected) == set(known):
        return None
    return [c for c in known if c in set(selected)]
