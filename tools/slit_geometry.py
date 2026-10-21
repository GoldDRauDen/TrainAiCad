#!/usr/bin/env python3
"""Bend-end slit decision (BEND_END_OFFSET_90) and BOXMET connected LINE+ARC+LINE construction.

Pure geometry; no I/O. See references/BEND_EDGE_RELIEF_90.md and BOXMET_SLIT_RELIEF.md.
"""
from __future__ import annotations

import math


def slit_depth_from_actual_edge(S: float, T: float):
    """90-degree BEND_END_OFFSET_90: None = NO slit (S>0); else T+0.2 from the actual edge."""
    if S > 0:
        return None
    return T + 0.2


def slit_depth_from_reference(S: float, T: float):
    """Same slit measured from the zero/outside reference: |S|+T+0.2 (S<0), T+0.2 (S=0)."""
    if S > 0:
        return None
    return abs(S) + T + 0.2


def _vector(value, name):
    """Fail closed on invalid or non-finite 2D construction vectors."""
    try:
        if len(value) != 2:
            raise ValueError
        result = (float(value[0]), float(value[1]))
        if not all(math.isfinite(x) for x in result):
            raise ValueError
        return result
    except (TypeError, ValueError, IndexError) as exc:
        raise ValueError(f"{name}: finite 2D vector required") from exc


def _positive(value, name):
    try:
        v = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name}: positive finite value required") from exc
    if not math.isfinite(v) or v <= 0:
        raise ValueError(f"{name}: positive finite value required")
    return v


class LeadValueUnproved(ValueError):
    """The lead table has no proved straight value for this material/thickness (local FLAG, never a guess)."""


def _lead_rows(group):
    import yaml
    from pathlib import Path
    cfg = yaml.safe_load((Path(__file__).resolve().parents[1] / "references" / "LEAD_TABLE.yaml").read_text(encoding="utf-8"))
    return cfg["groups"].get(group)


def _in_row(row, t):
    lo, hi = row["t_min"], row.get("t_max")
    above = t > lo if row.get("min_open") else t >= lo
    below = True if hi is None else (t < hi if row.get("t_max_open") else t <= hi)
    return above and below


def lead_val(material: str, T: float) -> float:
    """Slit lead value (offset of both meeting edges) from references/LEAD_TABLE.yaml (workbook column G).

    Raises LeadValueUnproved (code LEAD_VALUE_UNPROVED:...) for an unresolved material, a thickness that falls in a
    gap between rows, a missing row (e.g. Cu/Brass t>6) or the hook rows (t>=19): these are FLAGGED, not guessed.
    """
    thickness = _positive(T, "thickness")
    from material_resolver import MaterialResolveError, resolve_material
    try:
        group = resolve_material(material)["material_family"]
    except MaterialResolveError as exc:
        raise LeadValueUnproved(f"LEAD_VALUE_UNPROVED:MATERIAL:{exc}") from exc
    rows = _lead_rows("SUS" if group == "OTHER" else group)
    if rows is None:
        raise LeadValueUnproved(f"LEAD_VALUE_UNPROVED:GROUP:{group}")
    row = next((r for r in rows if _in_row(r, thickness)), None)
    if row is None:
        raise LeadValueUnproved(f"LEAD_VALUE_UNPROVED:NO_ROW:{group}:t{thickness:g}")
    if row["shape"] != "STRAIGHT":
        raise LeadValueUnproved(f"LEAD_VALUE_UNPROVED:HOOK_{row['shape']}:{group}:t{thickness:g}")
    return float(row["lead"])


def slit_dir_from_bend(bend_dir, inward_hint):
    """Slit ray S = unit PERPENDICULAR to the bend line, pointing inward (toward the bend/web side).
    bend_dir: bend-line direction; inward_hint: any vector pointing inward (sign picker)."""
    direction = _vector(bend_dir, "bend_dir")
    hint = _vector(inward_hint, "inward_hint")
    n = math.hypot(*direction)
    if n <= 1e-12:
        raise ValueError("BEND_DIRECTION_UNPROVED")
    s = (-direction[1] / n, direction[0] / n)
    dot = s[0] * hint[0] + s[1] * hint[1]
    if abs(dot) <= 1e-10:
        raise ValueError("SLIT_INWARD_SIDE_UNPROVED")
    return s if dot > 0 else (-s[0], -s[1])


def lead_end_by_offset(B, n_side, n_web, lead: float):
    """Lead end P = intersection of the flange-side line and the web edge, each offset by `lead`
    (perpendicular distance) toward the void. n_* are unit outward (void-side) normals of those
    two edges that meet at B. For a 90-degree corner this equals B + lead*(n_side + n_web),
    i.e. the BOXMET (+-lead, +-lead) sign table; any other corner angle uses the same offsets."""
    base = _vector(B, "base")
    side = _vector(n_side, "side normal")
    web = _vector(n_web, "web normal")
    distance = _positive(lead, "lead")
    if any(abs(math.hypot(*n) - 1.0) > 1e-8 for n in (side, web)):
        raise ValueError("SLIT_VOID_NORMAL_NOT_UNIT")
    cross = side[0] * web[1] - side[1] * web[0]
    if abs(cross) <= 1e-9:
        raise ValueError("SLIT_EDGES_PARALLEL_REVIEW")
    c = side[0] * web[0] + side[1] * web[1]
    k = distance / (1.0 + c)
    return (base[0] + k * (side[0] + web[0]),
            base[1] + k * (side[1] + web[1]))


def connected_slit(B, S, D, slit_len: float, R: float = 0.5) -> dict:
    """Return LINE(E1->T1), ARC(centre,R,start,end deg CCW), LINE(T2->E2) for one slit.

    B base point, S unit short-ray direction (into material), D lead delta (e.g. (-LV,-LV)).
    """
    base, short, delta = (_vector(B, "base"), _vector(S, "slit direction"),
                          _vector(D, "lead delta"))
    depth, radius = _positive(slit_len, "slit_len"), _positive(R, "radius")
    if abs(math.hypot(*short) - 1.0) > 1e-8:
        raise ValueError("SLIT_DIRECTION_NOT_UNIT")
    n = math.hypot(*delta)
    if n <= 1e-12:
        raise ValueError("SLIT_LEAD_ZERO")
    u1, u2 = short, (delta[0] / n, delta[1] / n)
    theta = math.acos(max(-1.0, min(1.0, u1[0] * u2[0] + u1[1] * u2[1])))
    if theta <= 1e-6 or math.pi - theta <= 1e-6:
        raise ValueError("SLIT_RAYS_COLLINEAR_REVIEW")
    td = radius / math.tan(theta / 2)
    if td >= min(depth, n) - 1e-9:
        raise ValueError("SLIT_FILLET_EXCEEDS_AVAILABLE_RAYS")
    cd = radius / math.sin(theta / 2)
    B, S, D, slit_len, R = base, short, delta, depth, radius
    E1 = (B[0] + S[0] * slit_len, B[1] + S[1] * slit_len)
    E2 = (B[0] + D[0], B[1] + D[1])
    bis = (u1[0] + u2[0], u1[1] + u2[1])
    bl = math.hypot(*bis)
    c = (B[0] + bis[0] / bl * cd, B[1] + bis[1] / bl * cd)
    T1 = (B[0] + u1[0] * td, B[1] + u1[1] * td)
    T2 = (B[0] + u2[0] * td, B[1] + u2[1] * td)
    a1 = math.degrees(math.atan2(T1[1] - c[1], T1[0] - c[0])) % 360
    a2 = math.degrees(math.atan2(T2[1] - c[1], T2[0] - c[0])) % 360
    start, end = (a1, a2) if (a2 - a1) % 360 <= 180 else (a2, a1)
    return {"line1": (E1, T1), "arc": {"center": c, "radius": R, "start_angle": start, "end_angle": end},
            "line2": (T2, E2), "theta_deg": math.degrees(theta), "tangent_dist": td}
