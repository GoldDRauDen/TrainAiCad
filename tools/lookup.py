#!/usr/bin/env python3
"""Deterministic lookup of approved shop tables — the AI calls this instead of
reading tables by eye.

The tables stay in their owning Markdown files (single source of truth); this
module parses them, so editing a table there changes the lookup result here.

    python tools/lookup.py nobi --material SPCC --t 1.6 --L 900
    python tools/lookup.py nobi --material SUS304 --t 3 --L 2000 --surface "#1"
    python tools/lookup.py nobi --material SPCC --t 2.5 --L 500          # t not tabulated -> FLAG
    python tools/lookup.py nobi --material SPCC --t 1.6 --L 900 --angle 135   # -> split flange
    python tools/lookup.py laser-r --material SS400 --t 9
    python tools/lookup.py hole --material SS400 --t 9 --dia 4.2
    python tools/lookup.py pilot --thread M8x1
    python tools/lookup.py idod --t 3 --angle 165
    python tools/lookup.py unfold --od 410.8 20.8 175 --nobi 1.68 0.36

Every result is JSON. ``status`` is ``OK`` or ``FLAG``; a FLAG carries
``flag_vi`` (Vietnamese text for the DXF FLAG line) and the ``action`` the
geometry must follow. The tool never invents a value: no table match is a FLAG.
"""
from __future__ import annotations

import argparse
from decimal import ROUND_HALF_UP, Decimal
from functools import lru_cache
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from material_resolver import MaterialResolveError, resolve_material  # noqa: E402

NOBI_MD = ROOT / "data" / "nobi_tables.md"
KH646_MD = ROOT / "data" / "nobi_kh646.md"
MATERIAL_MD = ROOT / "data" / "material_rules.md"
PILOT_MD = ROOT / "data" / "thread_pilot.md"
FINE_MD = ROOT / "data" / "thread_fine_pilot.md"

SPLIT_FLANGE = "SPLIT_FLANGE_10MM"
ANGLE_TOL = 0.5  # degrees; a bend is "90°" only within this tolerance
EPS = 1e-9


class LookupError_(ValueError):
    pass


def r2(value: float) -> float:
    """Ordinary half-up rounding to 0.01 mm (rules/BEND.md ID->OD rule)."""
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _num(cell: str):
    cell = cell.replace("*", "").replace("$", "").strip()
    try:
        return float(cell)
    except ValueError:
        return None


def _rows(text: str):
    for line in text.splitlines():
        if line.startswith("|") and not re.match(r"^\|\s*:?-", line):
            yield [c.strip() for c in line.strip().strip("|").split("|")]


# --------------------------------------------------------------------- Nobi
def _bracket(cell: str, prev_hi: float):
    """'~ 2400' -> (prev_hi, 2400]; '1001 ~ 1900' -> [1001, 1900]."""
    m = re.match(r"^\s*(\d+)?\s*~\s*(\d+)\s*$", cell)
    if not m:
        return None
    lo = float(m.group(1)) - 1 if m.group(1) else prev_hi
    return lo, float(m.group(2))


@lru_cache(maxsize=1)
def nobi_tables() -> dict:
    """Parse data/nobi_tables.md into {group: [row,...]}."""
    groups: dict[str, list] = {}
    current = None
    names = {"1.": "SS_SUS430_BRASS", "2.": "SUS", "3.": "AL", "4.": "CU"}
    prev_t, prev_hi = None, 0.0
    for line in NOBI_MD.read_text(encoding="utf-8").splitlines():
        head = re.match(r"^####\s+(\d\.)", line)
        if head:
            current = names.get(head.group(1))
            groups.setdefault(current, [])
            prev_t, prev_hi = None, 0.0
            continue
        if current is None or not line.startswith("|") or re.match(r"^\|\s*:?-", line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        t = _num(cells[0])
        if t is None:
            continue
        if t != prev_t:
            prev_t, prev_hi = t, 0.0
        br = _bracket(cells[1], prev_hi)
        if br is None:
            continue
        prev_hi = br[1]
        row = {"t": t, "L_gt": br[0], "L_le": br[1], "v_die": cells[2]}
        if current == "SUS":
            row["2B"], row["#1"] = _num(cells[3]), _num(cells[4])
        else:
            row["nobi"] = _num(cells[3])
        groups[current].append(row)
    return groups


@lru_cache(maxsize=1)
def kh646_tables() -> dict:
    groups: dict[str, list] = {"STEEL": [], "SUS304": []}
    current = None
    for line in KH646_MD.read_text(encoding="utf-8").splitlines():
        if line.startswith("## Standard steel"):
            current = "STEEL"
        elif line.startswith("## SUS304"):
            current = "SUS304"
        elif line.startswith("## "):
            current = None
        elif current and line.startswith("|") and not re.match(r"^\|\s*:?-", line):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            t = _num(cells[0])
            if t is None:
                continue
            row = {"t": t, "punch_R": _num(cells[1]), "v_die": cells[2], "nobi": _num(cells[3])}
            if current == "STEEL":
                row["min_L"] = _num(cells[4])
                row["L_gt"], row["L_le"] = 0.0, math.inf
            else:
                rng = cells[4]
                m = re.search(r"(\d+)\s*[–-]\s*(\d+)", rng)
                m2 = re.search(r"≤\s*(\d+)", rng)
                if m:
                    row["L_gt"], row["L_le"] = float(m.group(1)) - 1, float(m.group(2))
                elif m2:
                    row["L_gt"], row["L_le"] = 0.0, float(m2.group(1))
                else:
                    row["L_gt"], row["L_le"] = 0.0, math.inf
            groups[current].append(row)
    return groups


def _flag(action: str, reason: str, vi: str, **extra) -> dict:
    out = {"status": "FLAG", "action": action, "reason": reason, "flag_vi": vi}
    out.update(extra)
    return out


def _nobi_group(material: str) -> str:
    """Nobi table group for a printed material."""
    norm = material.upper()
    if any(k in norm for k in ("BRASS", "真ちゅう", "真鍮")) or re.match(r"^C2\d{3}", norm):
        return "SS_SUS430_BRASS"
    if "銅" in material or re.match(r"^(CU|C1)", norm):
        return "CU"
    group = resolve_material(material, "NOBI")["process_group"]
    return {"SS": "SS_SUS430_BRASS", "SS_SUS430_BRASS": "SS_SUS430_BRASS",
            "SUS": "SUS", "AL": "AL"}.get(group, group)


def nobi(material: str, t: float, L: float, angle: float = 90.0,
         surface: str | None = None, handwritten: float | None = None,
         j_symbol: bool = True, customer_code: str | None = None) -> dict:
    """Nobi decision per rules/BEND.md §6 (approved 2026-10-21)."""
    base = {"material": material, "t": t, "L": L, "angle": angle}
    if handwritten is not None:
        return {"status": "OK", "nobi": handwritten, "source": "HANDWRITTEN", **base}
    is90 = abs(angle - 90.0) <= ANGLE_TOL
    if not is90:
        return _flag(SPLIT_FLANGE, "NON_90_NO_HANDWRITTEN_NOBI",
                     f"Gấp {angle:g}° không có Nobi viết tay: tách bích cách 10 mm, chờ xác nhận Nobi",
                     **base)
    if not j_symbol:
        return _flag(SPLIT_FLANGE, "NO_J_NO_HANDWRITTEN_NOBI",
                     "Không có ký hiệu J và Nobi viết tay: tách bích cách 10 mm, chờ xác nhận", **base)
    if customer_code is not None and str(customer_code) == "646":
        return _nobi_646(material, t, L, base)
    try:
        group = _nobi_group(material)
    except MaterialResolveError as exc:
        return _flag(SPLIT_FLANGE, str(exc), f"Vật liệu {material} chưa xác định nhóm Nobi: tách bích cách 10 mm",
                     **base)
    rows = nobi_tables().get(group, [])
    same_t = [r for r in rows if abs(r["t"] - t) < EPS]
    if not same_t:
        tabulated = sorted({r["t"] for r in rows})
        return _flag(SPLIT_FLANGE, "THICKNESS_NOT_TABULATED",
                     f"t={t:g} không có trong bảng Nobi {group}: tách bích cách 10 mm, kiểm tra lại độ dày",
                     tabulated_t=tabulated, table=group, **base)
    hit = next((r for r in same_t if r["L_gt"] < L <= r["L_le"] + EPS), None)
    if hit is None:
        return _flag(SPLIT_FLANGE, "BEND_LENGTH_OUT_OF_TABLE",
                     f"Chiều dài gấp L={L:g} ngoài bảng Nobi t={t:g}: tách bích cách 10 mm, xác nhận Nobi với xưởng",
                     table=group, **base)
    if group == "SUS":
        s = (surface or "2B").replace(" ", "").upper()
        key = "#1" if s in ("#1", "NO.1", "NO1") else "2B"
        value = hit[key]
        surf = {"surface": key, "surface_default": surface is None}
    else:
        value, surf = hit["nobi"], {}
    if value is None:
        return _flag(SPLIT_FLANGE, "TABLE_CELL_CONFIRM",
                     f"Bảng Nobi t={t:g} L={L:g} ghi 'Confirm': tách bích cách 10 mm, xác nhận Nobi",
                     table=group, v_die=hit["v_die"], **base)
    return {"status": "OK", "nobi": value, "source": "TABLE", "table": group,
            "v_die": hit["v_die"], "row": f"t{t:g} L({hit['L_gt']:g},{hit['L_le']:g}]", **surf, **base}


def _nobi_646(material: str, t: float, L: float, base: dict) -> dict:
    sus = material.upper().startswith("SUS") and "430" not in material
    rows = kh646_tables()["SUS304" if sus else "STEEL"]
    same_t = [r for r in rows if abs(r["t"] - t) < EPS]
    hit = next((r for r in same_t if r["L_gt"] < L <= r["L_le"] + EPS), None)
    if hit is None or hit["nobi"] is None:
        return _flag(SPLIT_FLANGE, "KH646_NO_MATCH",
                     f"KH646: không có Nobi cho t={t:g} L={L:g}: tách bích cách 10 mm (không dùng bảng chung)",
                     table="KH646", **base)
    out = {"status": "OK", "nobi": hit["nobi"], "source": "TABLE", "table": "KH646",
           "v_die": hit["v_die"], "punch_R": hit["punch_R"], **base}
    if hit.get("min_L") is not None:
        out["min_L"] = hit["min_L"]
    return out


# ------------------------------------------------- Laser R / hole capacity
@lru_cache(maxsize=1)
def material_rows() -> list:
    text = MATERIAL_MD.read_text(encoding="utf-8")
    block = text.split("## Original worksheet entries", 1)[1].split("\n## ", 1)[0]
    rows = []
    for cells in _rows(block):
        if not cells[0].isdigit():
            continue
        grp = cells[1]
        group = ("SS" if grp.startswith("SS") else "SUS_OTHER" if grp.startswith("SUS")
                 else "AL" if grp.startswith("AL") else "CU_BRASS")
        rows.append({"excel_row": int(cells[0]), "group": group, "t_min": _num(cells[2]),
                     "t_max": _num(cells[3]), "laser_r": cells[5], "min_hole": cells[6],
                     "white_piercing": cells[7]})
    return rows


def _laser_group(material: str) -> str:
    if any(k in material.upper() for k in ("BRASS", "真ちゅう", "真鍮")) or "銅" in material:
        return "CU_BRASS"
    g = resolve_material(material, "LASER_R")["process_group"]
    return {"SUS": "SUS_OTHER", "SUS_OTHER": "SUS_OTHER", "SS": "SS", "AL": "AL",
            "CU_BRASS": "CU_BRASS"}[g]


def _material_row(group: str, t: float):
    """Workbook row for t: containing range (narrowest), else next higher row; no interpolation."""
    rows = [r for r in material_rows() if r["group"] == group]
    spans = []
    prev_hi = 0.0
    for i, r in enumerate(rows):
        last = i == len(rows) - 1
        if r["t_min"] is None:
            lo, hi, lo_inc = prev_hi, r["t_max"], False
        elif r["t_max"] is None:
            lo, hi, lo_inc = r["t_min"], (math.inf if last else r["t_min"]), True
        else:
            lo, hi, lo_inc = r["t_min"], r["t_max"], True
        spans.append((lo, hi, lo_inc, r))
        prev_hi = max(prev_hi, hi if hi != math.inf else prev_hi)
    inside = [s for s in spans if (s[0] < t or (s[2] and abs(s[0] - t) < EPS)) and t <= s[1] + EPS]
    if inside:  # most specific = narrowest range
        return min(inside, key=lambda s: s[1] - s[0])[3], False
    higher = [s for s in spans if s[0] > t]
    if higher:
        return min(higher, key=lambda s: s[0])[3], True
    return None, False


def laser_r(material: str, t: float) -> dict:
    base = {"material": material, "t": t}
    try:
        group = _laser_group(material)
    except (MaterialResolveError, KeyError) as exc:
        return _flag("ASK", str(exc), f"Vật liệu {material} chưa xác định nhóm Laser R", **base)
    if group == "CU_BRASS":  # L10 approved override
        r = "R0.5" if t <= 6 + EPS else "NONE"
        return {"status": "OK", "laser_r": r, "group": group, "rule": "L10", "corner_class": "outside ≤90°", **base}
    row, upward = _material_row(group, t)
    if row is None:
        return _flag("ASK", "THICKNESS_OUTSIDE_WORKBOOK", f"t={t:g} ngoài bảng Laser R nhóm {group}", **base)
    cell = row["laser_r"]
    m = re.search(r"R(\d+(?:\.\d+)?)", cell)
    value = f"R{m.group(1)}" if m else "NONE"
    scope = ("outer material perimeter only (incl. concave corners of that perimeter), never holes/slots"
             if value == "R3" else "outside corner ≤90°, uncalled-out only" if m else "no automatic R")
    return {"status": "OK", "laser_r": value, "group": group, "excel_row": row["excel_row"],
            "upward_row": upward, "corner_class": scope, **base}


def _min_hole(group: str, t: float):
    row, _ = _material_row(group, t)
    rows = [r for r in material_rows() if r["group"] == group]
    idx = rows.index(row)
    for r in reversed(rows[: idx + 1]):  # step 4: inherit within group only
        cell = r["min_hole"]
        if "≥" in cell:
            expr = cell.split("≥", 1)[1].strip()
            if expr.startswith("Ø"):
                return float(expr[1:]), r["excel_row"], cell
            if expr == "t":
                return t, r["excel_row"], cell
            m = re.match(r"^t/(\d+)$", expr)
            if m:
                return t / float(m.group(1)), r["excel_row"], cell
            m = re.match(r"^([\d.]+)t$", expr)
            if m:
                return float(m.group(1)) * t, r["excel_row"], cell
    return None, None, None


def hole(material: str, t: float, dia: float, piercing: bool = False, through: bool = False) -> dict:
    """POINT vs CIRCLE per rules/HOLE_TAP.md §2."""
    base = {"material": material, "t": t, "dia": dia}
    if piercing and through:
        return {"status": "OK", "entity": "POINT", "color": 3, "reason": "PIERCING+THROUGH", **base}
    if piercing:
        return {"status": "OK", "entity": "POINT", "color": "BYLAYER", "reason": "PIERCING", **base}
    if dia < t / 2 - EPS:
        return {"status": "OK", "entity": "POINT", "color": "BYLAYER", "reason": "DIA_LT_T_HALF", **base}
    try:
        group = _laser_group(material)
    except (MaterialResolveError, KeyError) as exc:
        return _flag("MAGENTA_CIRCLE", str(exc), f"Vật liệu {material} chưa rõ: lỗ Ø{dia:g} vẽ tạm Magenta",
                     **base)
    minimum, row, cell = _min_hole(group, t)
    if minimum is None:
        return _flag("MAGENTA_CIRCLE", "MIN_HOLE_UNKNOWN", f"Không tra được lỗ tối thiểu t={t:g}: lỗ Ø{dia:g} vẽ tạm Magenta",
                     **base)
    if dia < minimum - EPS:
        return {"status": "OK", "entity": "POINT", "color": "BYLAYER", "reason": "BELOW_MIN_HOLE",
                "min_hole": round(minimum, 3), "excel_row": row, **base}
    return {"status": "OK", "entity": "CIRCLE", "color": "BYLAYER", "min_hole": round(minimum, 3),
            "excel_row": row, **base}


# ------------------------------------------------------------ thread pilot
@lru_cache(maxsize=1)
def pilot_tables():
    coarse, fine = {}, {}
    for cells in _rows(PILOT_MD.read_text(encoding="utf-8")):
        m = re.match(r"^\**M([\d.]+)\**$", cells[0])
        if m and _num(cells[2]) is not None:
            coarse[float(m.group(1))] = (_num(cells[1]), _num(cells[2]))
    for cells in _rows(FINE_MD.read_text(encoding="utf-8")):
        m = re.match(r"^M([\d.]+)×([\d.]+)$", cells[0])
        if m:
            fine[(float(m.group(1)), float(m.group(2)))] = _num(cells[1])
    return coarse, fine


def pilot(thread: str) -> dict:
    m = re.match(r"^\s*M\s*([\d.]+)\s*(?:[x×X*]\s*([\d.]+))?\s*$", thread)
    if not m:
        return _flag("ASK", "THREAD_UNPARSED", f"Không đọc được ren '{thread}'", thread=thread)
    d, p = float(m.group(1)), (float(m.group(2)) if m.group(2) else None)
    coarse, fine = pilot_tables()
    if p is None or (d in coarse and abs(coarse[d][0] - p) < EPS):
        if d not in coarse:
            return _flag("ASK", "THREAD_NOT_IN_TABLE", f"Ren M{d:g} không có trong bảng lỗ khoan mồi", thread=thread)
        return {"status": "OK", "thread": thread, "pitch": coarse[d][0], "pilot_dia": coarse[d][1],
                "table": "COARSE"}
    if (d, p) in fine:
        return {"status": "OK", "thread": thread, "pitch": p, "pilot_dia": fine[(d, p)], "table": "FINE"}
    return _flag("ASK", "THREAD_NOT_IN_TABLE", f"Ren M{d:g}×{p:g} không có trong bảng lỗ khoan mồi", thread=thread)


# ------------------------------------------------------------ ID->OD, unfold
def idod(t: float, angle: float) -> dict:
    out = {"t": t, "angle": angle}
    if angle <= 85 + EPS:
        out.update(status="FLAG", action="USE_ACUTE_BEND_LT85",
                   reason="ACUTE_BEND_LT85", flag_vi="Góc ≤85°: dựng bán kính thật theo rules/BEND_ACUTE.md (tools/acute_bend.py)")
        return out
    raw = t * math.tan(math.radians((180.0 - angle) / 2.0))
    out.update(status="OK", offset_raw=raw, offset=r2(raw), rule="OD = ID + offset (offset rounded 0.01 first)")
    return out


def unfold(od: list[float], nobi_values: list[float]) -> dict:
    if len(nobi_values) != len(od) - 1:
        raise LookupError_("need len(nobi) == len(od) - 1")
    lines = []
    for k in range(1, len(od)):
        lines.append({"bend": k,
                      "line1": r2(sum(od[:k]) - sum(nobi_values[:k])),
                      "line2": r2(sum(od[:k]) - sum(nobi_values[:k - 1]))})
    return {"status": "OK", "flat_length": r2(sum(od) - sum(nobi_values)), "bend_lines": lines}


# ------------------------------------------------------------------- CLI
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("nobi")
    n.add_argument("--material", required=True)
    n.add_argument("--t", type=float, required=True)
    n.add_argument("--L", type=float, required=True, help="bend length mm")
    n.add_argument("--angle", type=float, default=90.0, help="included bend angle")
    n.add_argument("--surface", help="SUS surface: 2B (default) or #1")
    n.add_argument("--handwritten", type=float, help="legible handwritten Nobi on the PDF")
    n.add_argument("--no-j", action="store_true", help="J symbol absent")
    n.add_argument("--customer", help="numeric customer_code from job statistics")
    lr = sub.add_parser("laser-r")
    lr.add_argument("--material", required=True)
    lr.add_argument("--t", type=float, required=True)
    h = sub.add_parser("hole")
    h.add_argument("--material", required=True)
    h.add_argument("--t", type=float, required=True)
    h.add_argument("--dia", type=float, required=True, help="effective cut diameter (pilot Ø for M)")
    h.add_argument("--piercing", action="store_true")
    h.add_argument("--through", action="store_true")
    p = sub.add_parser("pilot")
    p.add_argument("--thread", required=True)
    i = sub.add_parser("idod")
    i.add_argument("--t", type=float, required=True)
    i.add_argument("--angle", type=float, required=True)
    u = sub.add_parser("unfold")
    u.add_argument("--od", type=float, nargs="+", required=True)
    u.add_argument("--nobi", type=float, nargs="*", default=[])
    a = ap.parse_args(argv)
    if a.cmd == "nobi":
        res = nobi(a.material, a.t, a.L, a.angle, a.surface, a.handwritten, not a.no_j, a.customer)
    elif a.cmd == "laser-r":
        res = laser_r(a.material, a.t)
    elif a.cmd == "hole":
        res = hole(a.material, a.t, a.dia, a.piercing, a.through)
    elif a.cmd == "pilot":
        res = pilot(a.thread)
    elif a.cmd == "idod":
        res = idod(a.t, a.angle)
    else:
        res = unfold(a.od, a.nobi)
    print(json.dumps(res, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):
        _stream.reconfigure(encoding="utf-8")  # Vietnamese FLAG text on a Windows console
    raise SystemExit(main())
