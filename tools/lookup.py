#!/usr/bin/env python3
"""Deterministic lookup of approved shop tables — the AI calls this instead of
reading tables by eye.

The tables stay in their owning Markdown files (single source of truth); this
module parses them, so editing a table there changes the lookup result here.

    python tools/lookup.py nobi --material SPCC --t 1.6 --L 900
    python tools/lookup.py nobi --material SUS304 --t 3 --L 2000 --surface "#1"
    python tools/lookup.py nobi --material SPCC --t 2.5 --L 500          # t not tabulated -> FLAG
    python tools/lookup.py nobi --material SPCC --t 1.6 --L 900 --angle 135   # -> split flange
    python tools/lookup.py laser-r --material SS400 --t 9 [--customer 768]
    python tools/lookup.py hole --material SS400 --t 9 --dia 4.2
    python tools/lookup.py pilot --thread M8x1
    python tools/lookup.py countersink --thread M6
    python tools/lookup.py tooling --material SPCC --t 3
    python tools/lookup.py idod --t 3 --angle 165
    python tools/lookup.py unfold --od 410.8 20.8 175 --nobi 1.68 0.36      # also the [start, end] range of every face
    python tools/lookup.py slant --width 70 --rise 70 --opening 5 --t 1.5      # slanted plate from a side section (521030-10)

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
CUSTOMERS = ROOT / "data" / "customers.yaml"
COUNTERSINK_MD = ROOT / "data" / "countersink.md"
TOOLING_MD = ROOT / "data" / "bend_tooling.md"

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


@lru_cache(maxsize=1)
def _customers() -> dict:
    import yaml
    return yaml.safe_load(CUSTOMERS.read_text(encoding="utf-8")).get("customers", {})


def customer_record(code) -> dict:
    """Catalog record of a numeric JOB STATISTICS customer code ({} = general rules)."""
    if code is None:
        return {}
    return _customers().get(str(int(str(code).strip())), {})


def _customer_corner(code, t: float) -> dict | None:
    pol = customer_record(code).get("corner_policy")
    if not pol:
        return None
    rule = f"KH{int(str(code).strip())}"
    if pol.get("confirm_from_t") is not None and t >= pol["confirm_from_t"] - EPS:
        return _flag("ASK", "CUSTOMER_CORNER_CONFIRM",
                     f"{rule}: góc ngoài khi t≥{pol['confirm_from_t']:g} cần xác nhận với khách", rule=rule)
    value = pol["default"]
    if pol.get("max_t") is not None and t > pol["max_t"] + EPS:
        if pol.get("above_from_t") is not None and t < pol["above_from_t"] - EPS:
            return _flag("ASK", "CUSTOMER_CORNER_GAP",
                         f"{rule}: t={t:g} nằm giữa {pol['max_t']:g} và {pol['above_from_t']:g}, chưa rõ góc ngoài",
                         rule=rule)
        value = pol["above"]
    return {"status": "OK", "laser_r": "NONE" if value == "SHARP" else value, "rule": rule,
            "corner_class": "uncalled outside corner ≤93° (customer rule); drawn R/C still wins"}


def laser_r(material: str, t: float, customer: str | None = None) -> dict:
    """Automatic outside-corner treatment: customer corner rule first, else the shop workbook."""
    base = {"material": material, "t": t}
    if customer is not None:
        cust = _customer_corner(customer, t)
        if cust is not None:
            return {**cust, **base, "customer": str(customer)}
    try:
        group = _laser_group(material)
    except (MaterialResolveError, KeyError) as exc:
        return _flag("ASK", str(exc), f"Vật liệu {material} chưa xác định nhóm Laser R", **base)
    if group == "CU_BRASS":  # L10 approved override
        r = "R0.5" if t <= 6 + EPS else "NONE"
        return {"status": "OK", "laser_r": r, "group": group, "rule": "L10", "corner_class": "outside ≤93°", **base}
    row, upward = _material_row(group, t)
    if row is None:
        return _flag("ASK", "THICKNESS_OUTSIDE_WORKBOOK", f"t={t:g} ngoài bảng Laser R nhóm {group}", **base)
    cell = row["laser_r"]
    m = re.search(r"R(\d+(?:\.\d+)?)", cell)
    value = f"R{m.group(1)}" if m else "NONE"
    scope = ("outer material perimeter only (incl. concave corners of that perimeter), never holes/slots"
             if value == "R3" else "outside corner ≤93°, uncalled-out only" if m else "no automatic R")
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


def hole(material: str, t: float, dia: float, piercing: bool = False, through: bool = False,
         customer: str | None = None) -> dict:
    """POINT vs CIRCLE per rules/HOLE_TAP.md §2 (customer hole_policy may require confirmation)."""
    base = {"material": material, "t": t, "dia": dia}
    pol = customer_record(customer).get("hole_policy", {}) if customer is not None else {}
    if not piercing and pol.get("below_half_t") == "CONFIRM" and dia < t / 2 - EPS:
        code = int(str(customer).strip())
        return _flag("MAGENTA_CIRCLE", "CUSTOMER_CONFIRM_BELOW_HALF_T",
                     f"KH{code}: lỗ Ø{dia:g} < t/2 cần xác nhận với khách (vẽ tạm Magenta)", **base)
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
def countersink(thread: str) -> dict:
    """Through-hole / counterbore / 90° countersink mouth for M3–M8; only the through hole is a laser cut."""
    m = re.match(r"^M?(\d+(?:\.\d+)?)", thread.strip().upper())
    for cells in _rows(COUNTERSINK_MD.read_text(encoding="utf-8")):
        if m and cells[0].upper() == f"M{m.group(1)}":
            return {"status": "OK", "thread": cells[0], "through_hole": _num(cells[1]), "counterbore": _num(cells[2]),
                    "countersink_mouth": _num(cells[3]), "cut": "through_hole only (mouth = machining)"}
    return _flag("ASK", "COUNTERSINK_NOT_TABULATED", f"{thread}: không có trong bảng 皿ザグリ, xác nhận lỗ thông",
                 thread=thread)


def tooling(material: str, t: float) -> dict:
    """V dies and minimum leg L / Z for a material family and thickness (WARN only, never resizes)."""
    group = {"SS_SUS430_BRASS": "SS", "SUS": "SUS", "AL": "AL", "CU": "CU"}.get(_nobi_group(material), "SS")
    rows = []
    for cells in _rows(TOOLING_MD.read_text(encoding="utf-8")):
        if cells[0].upper() == group and _num(cells[1]) is not None and abs(_num(cells[1]) - t) < EPS:
            rows.append({"v_die": cells[2], "L_min": _num(cells[3]), "Z_min": _num(cells[4])})
    if not rows:
        return {"status": "OK", "group": group, "t": t, "dies": [], "note": "no tabulated die: no WARN possible"}
    return {"status": "OK", "group": group, "t": t, "dies": rows,
            "note": "WARN only when a proved leg is shorter than the selected die's L_min/Z_min"}


def idod(t: float, angle: float) -> dict:
    out = {"t": t, "angle": angle}
    if angle <= 85 + EPS:
        out.update(status="FLAG", action="USE_ACUTE_BEND_LT85",
                   reason="ACUTE_BEND_LT85", flag_vi="Góc ≤85°: dựng bán kính thật theo rules/BEND_ACUTE.md (tools/acute_bend.py)")
        return out
    raw = t * math.tan(math.radians((180.0 - angle) / 2.0))
    out.update(status="OK", offset_raw=raw, offset=r2(raw), rule="OD = ID + offset (offset rounded 0.01 first)")
    return out


def leg(a: float, b: float, t: float, angle: float, nobi: float | None = None) -> dict:
    """OD of the two legs of a non-90° bend whose section dims a (leg 1, to its end face) and b (leg 2, along its
    outer face from the end-face corner) do not reach the outer-face intersection (BEND.md §4):
    d = angle - 90, OD1 = a - t·tan d, OD2 = b + t/cos d (26-062885: 30, 50, t6, 100° -> 28.942 / 56.093)."""
    out = {"a": a, "b": b, "t": t, "angle": angle}
    if angle <= 85 + EPS:
        out.update(status="FLAG", action="USE_ACUTE_BEND_LT85", reason="ACUTE_BEND_LT85",
                   flag_vi="Góc ≤85°: dựng bán kính thật theo rules/BEND_ACUTE.md (tools/acute_bend.py)")
        return out
    if angle >= 180 - EPS:
        raise LookupError_("angle must be below 180")
    d = math.radians(angle - 90.0)
    od1, od2 = a - t * math.tan(d), b + t / math.cos(d)
    out.update(status="OK", od1=round(od1, 3), od2=round(od2, 3),
               rule="OD1 = a - t·tan(angle-90), OD2 = b + t/cos(angle-90)")
    if nobi is not None:
        out.update(nobi=nobi, flat_length=round(od1 + od2 - nobi, 3),
                   bend_line1_from_leg2_free_end=round(od2 - nobi, 3), bend_line2_from_leg2_free_end=round(od2, 3))
    return out


def unfold(od: list[float], nobi_values: list[float]) -> dict:
    """Bend lines and the [start, end] flat range of every face. A face dimensioned outer-plane to outer-plane (OD) spans exactly
    its OD there: its free edge toward a bend-less neighbour sits at start/end, i.e. ON the narrow neighbour's side bend line
    (S = 0), never one Nobi short of it (rules/SLIT_RELIEF.md §3)."""
    if len(nobi_values) != len(od) - 1:
        raise LookupError_("need len(nobi) == len(od) - 1")
    lines = []
    for k in range(1, len(od)):
        lines.append({"bend": k,
                      "line1": r2(sum(od[:k]) - sum(nobi_values[:k])),
                      "line2": r2(sum(od[:k]) - sum(nobi_values[:k - 1]))})
    total = r2(sum(od) - sum(nobi_values))
    faces = []
    for k, face_od in enumerate(od):
        start = 0.0 if k == 0 else lines[k - 1]["line1"]
        end = total if k == len(od) - 1 else lines[k]["line2"]
        faces.append({"face": k + 1, "od": face_od, "start": start, "end": end})
    return {"status": "OK", "flat_length": total, "bend_lines": lines, "faces": faces}


def slant(width: float, rise: float, opening: float, t: float, wall_t: float | None = None) -> dict:
    """Slanted plate in a side section: it leaves the far wall's outer-bottom corner (x = width, apex) and ends `rise` below it,
    its inner tip `opening` from the near wall's inner face (x = wall_t + opening). The tip's end face is square to the plate, so
    x_outer_tip = wall_t + opening + t*cos(a) with tan(a) = (width - x_outer_tip) / rise (a from vertical). Solved by iteration.
    included angle = 180 - a (the bend between the vertical wall and the slant); length = outer face from apex to tip."""
    import math
    wall_t = t if wall_t is None else wall_t
    x = wall_t + opening
    for _ in range(100):
        a = math.atan2(width - x, rise)
        nx = wall_t + opening + t * math.cos(a)
        if abs(nx - x) < 1e-12:
            break
        x = nx
    a_deg = math.degrees(a)
    return {"status": "OK", "x_outer_tip": r2(x), "angle_from_vertical": round(a_deg, 3),
            "included_angle": round(180 - a_deg, 3), "outer_length": r2(math.hypot(width - x, rise)),
            "run": r2(width - x), "tip_offset_x": r2(t * math.cos(a)), "tip_offset_y": r2(t * math.sin(a))}


# ------------------------------------------------------------ slit / retreat / KEGAKI (rules/SLIT_RELIEF.md, KEGAKI.md)
def slit(material: str, t: float, S: float | None = None, angle: float = 90.0) -> dict:
    """Bend-end relief decision: the proved step S decides at every angle (S>0 no slit, SLIT_RELIEF §3); the depth is T+0.2 at 90°, t·sin θ above (§4)."""
    import slit_geometry as sg
    base = {"material": material, "t": t, "angle": angle}
    non90 = abs(angle - 90.0) > ANGLE_TOL
    if non90 and not 90.0 < angle < 180.0:
        return _flag("ASK", "ANGLE_OUT_OF_RANGE", f"Góc {angle:g}° không thuộc 90–180°", **base)
    mechanism = "NON_90_RELIEF" if non90 else "BEND_END_OFFSET_90"
    if S is None:
        return _flag("FLAG", "S_UNPROVED", "Chưa chứng minh được bậc S ở đầu đường gấp: SLIT_RELIEF = UNKNOWN", **base)
    depth = sg.slit_depth_from_actual_edge(S, t, angle)
    if depth is None:
        return {"status": "OK", "mechanism": mechanism, "decision": "NO_SLIT", "S": S, **base}
    try:
        lead = sg.lead_val(material, t)
    except sg.LeadValueUnproved as exc:
        return _flag("FLAG", str(exc), "Chưa có giá trị lead cho vật liệu/độ dày này: không vẽ slit, FLAG", S=S, **base)
    return {"status": "OK", "mechanism": mechanism, "decision": "SLIT", "S": S,
            "depth_from_actual_edge": round(depth, 4),
            "depth_from_reference": round(sg.slit_depth_from_reference(S, t, angle), 4),
            "lead": lead, "arc_R": 0.5, **base}


def retreat(depth_a: float, depth_b: float, bend_len_a=None, bend_len_b=None) -> dict:
    """Same-direction corner: which flange retreats by t (SLIT_RELIEF §5)."""
    from corner_retreat import choose_retreat
    return {"status": "OK", **choose_retreat(depth_a, depth_b, bend_len_a, bend_len_b)}


def kegaki(t: float, slant_delta=None, tilt=None, edge=None, offset=None, host_t=None, k=None,
           run=None, short=None) -> dict:
    """Contact footprint numbers (rules/KEGAKI.md §3)."""
    import kegaki_footprint as kf
    out = {"status": "OK", "width": round(kf.contact_width(t, slant_delta=slant_delta, tilt_deg=tilt), 4)}
    if run is not None and short:
        out["slanted_edge_length"] = round(kf.slanted_edge_length(run, short[0], short[1]), 3)
    if edge is not None:
        out["contact_length"] = round(kf.contact_length(out.get("slanted_edge_length", edge), offset or 0.0), 4)
    if host_t is not None and k is not None:
        out["single_line_offset"] = round(kf.single_line_offset(host_t, k), 4)
    return out


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
    lr.add_argument("--customer", help="numeric customer_code from job statistics")
    h = sub.add_parser("hole")
    h.add_argument("--material", required=True)
    h.add_argument("--t", type=float, required=True)
    h.add_argument("--dia", type=float, required=True, help="effective cut diameter (pilot Ø for M)")
    h.add_argument("--piercing", action="store_true")
    h.add_argument("--through", action="store_true")
    h.add_argument("--customer", help="numeric customer_code from job statistics")
    p = sub.add_parser("pilot")
    p.add_argument("--thread", required=True)
    cs = sub.add_parser("countersink")
    cs.add_argument("--thread", required=True, help="M3..M8")
    tl = sub.add_parser("tooling")
    tl.add_argument("--material", required=True)
    tl.add_argument("--t", type=float, required=True)
    i = sub.add_parser("idod")
    i.add_argument("--t", type=float, required=True)
    i.add_argument("--angle", type=float, required=True)
    u = sub.add_parser("unfold")
    u.add_argument("--od", type=float, nargs="+", required=True)
    u.add_argument("--nobi", type=float, nargs="*", default=[])
    sl = sub.add_parser("slant", help="slanted plate from a side section: angle, outer length, tip offset")
    sl.add_argument("--width", type=float, required=True, help="outer-to-outer width between the walls (apex x)")
    sl.add_argument("--rise", type=float, required=True, help="vertical drop of the slant from the apex to the tip")
    sl.add_argument("--opening", type=float, required=True, help="gap from the near wall's inner face to the inner tip")
    sl.add_argument("--t", type=float, required=True)
    sl.add_argument("--wall-t", type=float)
    lg = sub.add_parser("leg", help="non-90° bend: OD of both legs from section dims that stop at the end faces")
    lg.add_argument("--a", type=float, required=True, help="leg 1 dim to its end face")
    lg.add_argument("--b", type=float, required=True, help="leg 2 dim along its outer face")
    lg.add_argument("--t", type=float, required=True)
    lg.add_argument("--angle", type=float, required=True)
    lg.add_argument("--nobi", type=float)
    sl = sub.add_parser("slit", help="bend-end relief: 90° from the proved step S, >90° t·sin θ")
    sl.add_argument("--material", required=True)
    sl.add_argument("--t", type=float, required=True)
    sl.add_argument("--S", type=float, help="proved signed step (+ protrudes, 0 flush, - recessed)")
    sl.add_argument("--angle", type=float, default=90.0)
    rt = sub.add_parser("retreat", help="same-direction corner: which flange retreats by t")
    rt.add_argument("--depth", type=float, nargs=2, required=True, metavar=("A", "B"))
    rt.add_argument("--bend-len", type=float, nargs=2, metavar=("A", "B"))
    kg = sub.add_parser("kegaki", help="weld contact footprint numbers")
    kg.add_argument("--t", type=float, required=True, help="child thickness")
    kg.add_argument("--slant-delta", type=float)
    kg.add_argument("--tilt", type=float, help="child tilt in degrees")
    kg.add_argument("--edge", type=float, help="contact edge length")
    kg.add_argument("--offset", type=float, help="printed offset along the contact edge")
    kg.add_argument("--run", type=float, help="slanted edge run (with --short)")
    kg.add_argument("--short", type=float, nargs=2, help="the two SHORTER alternate heights")
    kg.add_argument("--host-t", type=float)
    kg.add_argument("--k", type=float)
    a = ap.parse_args(argv)
    if a.cmd == "slit":
        res = slit(a.material, a.t, a.S, a.angle)
    elif a.cmd == "retreat":
        res = retreat(*a.depth, *(a.bend_len or (None, None)))
    elif a.cmd == "kegaki":
        res = kegaki(a.t, a.slant_delta, a.tilt, a.edge, a.offset, a.host_t, a.k, a.run, a.short)
    elif a.cmd == "nobi":
        res = nobi(a.material, a.t, a.L, a.angle, a.surface, a.handwritten, not a.no_j, a.customer)
    elif a.cmd == "laser-r":
        res = laser_r(a.material, a.t, a.customer)
    elif a.cmd == "hole":
        res = hole(a.material, a.t, a.dia, a.piercing, a.through, a.customer)
    elif a.cmd == "pilot":
        res = pilot(a.thread)
    elif a.cmd == "countersink":
        res = countersink(a.thread)
    elif a.cmd == "tooling":
        res = tooling(a.material, a.t)
    elif a.cmd == "idod":
        res = idod(a.t, a.angle)
    elif a.cmd == "slant":
        res = slant(a.width, a.rise, a.opening, a.t, a.wall_t)
    elif a.cmd == "leg":
        res = leg(a.a, a.b, a.t, a.angle, a.nobi)
    else:
        res = unfold(a.od, a.nobi)
    print(json.dumps(res, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):
        _stream.reconfigure(encoding="utf-8")  # Vietnamese FLAG text on a Windows console
    raise SystemExit(main())
