"""Draw <JOB>_AI_QA.dxf from a QA issues JSON: copies of each failing profile with red circles, leaders and notes.

Claude in a headless QA run can only run single `python ...` commands, so it writes the JSON and this tool draws.
Usage: python tools/qa_markup.py ISSUES.json OUT.dxf
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import ezdxf
from ezdxf import bbox
from ezdxf.addons.importer import Importer
from ezdxf.math import Matrix44

LAYER, RED, TOL, STYLE = "AI_QA", 1, 0.5, "AI_QA"


def _load_issues(path: str) -> dict:
    p = Path(path)
    if not p.is_file():
        raise ValueError(f"không thấy file issues: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON lỗi ({p.name}): {e}") from None
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list) or not items or not all(isinstance(i, dict) for i in items):
        raise ValueError("issues JSON phải có 'items' là danh sách khác rỗng")
    return data


def _inside(ext, box) -> bool:
    x0, y0, x1, y1 = min(box[0], box[2]), min(box[1], box[3]), max(box[0], box[2]), max(box[1], box[3])
    return (ext.has_data and ext.extmin.x >= x0 - TOL and ext.extmin.y >= y0 - TOL
            and ext.extmax.x <= x1 + TOL and ext.extmax.y <= y1 + TOL)


def _explode_dim(dim) -> list:
    """Importer drops a DIMENSION's geometry block, so copy what it draws (in the in-memory source only)."""
    layer, color, lt = dim.dxf.layer, dim.dxf.color, dim.dxf.linetype
    try:
        parts = list(dim.explode())
    except Exception:
        return []
    for e in parts:
        if e.dxf.layer == "0":
            e.dxf.layer = layer
        if e.dxf.color == 0:
            e.dxf.color = color
        if e.dxf.get("linetype", "").upper() == "BYBLOCK":
            e.dxf.linetype = lt
    return parts


def _select(sdoc, box) -> list:
    ents = list(sdoc.modelspace())
    if box:
        cache = bbox.Cache()
        ents = [e for e in ents if _inside(bbox.extents([e], cache=cache), box)]
    return [p for e in ents for p in (_explode_dim(e) if e.dxftype() == "DIMENSION" else [e])]


def _text(msp, s: str, x: float, y: float, h: float) -> None:
    msp.add_text(s, height=h, dxfattribs={"layer": LAYER, "color": RED, "style": STYLE}).set_placement((x, y))


def _mark(msp, m: dict, dx: float, dy: float, size: float, th: float) -> None:
    r = float(m.get("r") or max(3.0, 0.04 * size))
    cx, cy = float(m["x"]) + dx, float(m["y"]) + dy
    attrs = {"layer": LAYER, "color": RED}
    msp.add_circle((cx, cy), r, dxfattribs=attrs)
    a = math.radians(45)
    start = (cx + r * math.cos(a), cy + r * math.sin(a))
    elbow = (start[0] + 2 * th, start[1] + 2 * th)
    end = (elbow[0] + th, elbow[1])
    msp.add_leader([start, elbow, end], dxfattribs=attrs)
    _text(msp, str(m.get("note") or ""), end[0] + 0.5 * th, end[1] - 0.5 * th, th)


def _copy(tdoc, sdoc, ents: list, dx: float, dy: float) -> int:
    msp = tdoc.modelspace()
    before = {e.dxf.handle for e in msp}
    imp = Importer(sdoc, tdoc)
    imp.import_entities(ents, msp)
    imp.finalize()
    m, n = Matrix44.translate(dx, dy, 0), 0
    for e in [e for e in msp if e.dxf.handle not in before]:
        try:
            e.transform(m)
            n += 1
        except (NotImplementedError, ezdxf.DXFError):
            msp.delete_entity(e)  # cannot be moved: dropping beats leaving it on top of another profile
    return n


def build(issues: dict, out: Path) -> list[str]:
    tdoc = ezdxf.new("R2010", units=4)
    tdoc.layers.add(LAYER, color=RED)
    tdoc.styles.add(STYLE, font="arial.ttf")
    msp, report, notes, placed = tdoc.modelspace(), [], [], []
    cursor, max_h, max_th = 0.0, 0.0, 2.5
    for it in issues["items"]:
        code, note = str(it.get("code") or "?"), str(it.get("note") or "")
        marks = [m for m in it.get("marks") or [] if isinstance(m, dict)]
        why = "không có src"
        if it.get("src"):
            try:
                src = Path(it["src"])
                if src.resolve() == out.resolve():
                    raise ValueError("OUT trùng với src")
                sdoc = ezdxf.readfile(src)
                ents = _select(sdoc, it.get("bbox"))
                ext = bbox.extents(ents)
                if not ents or not ext.has_data:
                    raise ValueError("không chọn được entity nào (bbox?)")
                if not placed:  # units follow the first copied source
                    tdoc.header["$INSUNITS"] = sdoc.header.get("$INSUNITS", 4)
                w, h = ext.size.x, ext.size.y
                size = max(w, h, 1.0)
                th = max(2.5, 0.025 * size)
                dx, dy = cursor - ext.extmin.x, -ext.extmin.y
                n = _copy(tdoc, sdoc, ents, dx, dy)
                _text(msp, f"{code}: {note}", cursor, h + th, th)
                for m in marks:
                    _mark(msp, m, dx, dy, size, th)
                cursor += w + max(50.0, 0.3 * size)
                max_h, max_th = max(max_h, h), max(max_th, th)
                report.append(f"ok {code}: {n} entity, {len(marks)} mark")
                placed.append(code)
                continue
            except Exception as e:  # one bad item must not stop the others
                why = f"{type(e).__name__}: {e}"
        notes.append([f"{code}: {note}"] + [f"  - {m.get('note', '')} ({m.get('x')}, {m.get('y')})" for m in marks])
        report.append(f"note-only {code}: {why}")
    y = -3 * max_th
    for block in notes:
        for line in block:
            _text(msp, line, 0.0, y, max_th)
            y -= 1.6 * max_th
    title = f"AI QA {issues.get('job') or ''}".strip()
    _text(msp, title, 0.0, max_h + 4 * max_th, 1.5 * max_th)
    out.parent.mkdir(parents=True, exist_ok=True)
    tdoc.saveas(out)
    return report


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print("usage: python tools/qa_markup.py ISSUES.json OUT.dxf", file=sys.stderr)
        return 2
    try:
        issues = _load_issues(argv[0])
        out = Path(argv[1])
        for line in build(issues, out):
            print(line)
    except (ValueError, OSError) as e:
        print(f"lỗi: {e}", file=sys.stderr)
        return 1
    print(f"wrote: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
