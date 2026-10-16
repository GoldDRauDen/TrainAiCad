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


SS_FAMILY = {"SS", "SPCC", "SPHC", "SECC", "SGCC", "SGHC"}


def lead_val(material: str, T: float) -> float:
    """Bend-end slit LeadVal (user-confirmed 2026-10-16): 3.0 only for the SS group with T<=3.2,
    otherwise 6.0 (aluminium, stainless, SS thicker than 3.2, unknown material)."""
    return 3.0 if (str(material).upper() in SS_FAMILY and T <= 3.2) else 6.0


def lead_end_by_offset(B, n_side, n_web, lead: float):
    """Lead end P = intersection of the flange-side line and the web edge, each offset by `lead`
    (perpendicular distance) toward the void. n_* are unit outward (void-side) normals of those
    two edges that meet at B. For a 90-degree corner this equals B + lead*(n_side + n_web),
    i.e. the BOXMET (+-lead, +-lead) sign table; any other corner angle uses the same offsets."""
    c = n_side[0] * n_web[0] + n_side[1] * n_web[1]
    if c <= -1.0 + 1e-9:
        raise ValueError("edges are parallel: offset lines never intersect; flag for review")
    k = lead / (1.0 + c)
    return (B[0] + k * (n_side[0] + n_web[0]), B[1] + k * (n_side[1] + n_web[1]))


def connected_slit(B, S, D, slit_len: float, R: float = 0.5) -> dict:
    """Return LINE(E1->T1), ARC(centre,R,start,end deg CCW), LINE(T2->E2) for one slit.

    B base point, S unit short-ray direction (into material), D lead delta (e.g. (-LV,-LV)).
    """
    E1 = (B[0] + S[0] * slit_len, B[1] + S[1] * slit_len)
    E2 = (B[0] + D[0], B[1] + D[1])
    n = math.hypot(*D)
    u1, u2 = (S[0], S[1]), (D[0] / n, D[1] / n)
    theta = math.acos(max(-1.0, min(1.0, u1[0] * u2[0] + u1[1] * u2[1])))
    td = R / math.tan(theta / 2)
    cd = R / math.sin(theta / 2)
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
