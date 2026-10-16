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


def lead_val(material: str, T: float) -> float:
    """BOXMET LeadVal: 3.0 only when the tool material is exactly 'SS' and T<6, else 6.0."""
    return 3.0 if (material == "SS" and T < 6.0) else 6.0


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
