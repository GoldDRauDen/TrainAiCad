#!/usr/bin/env python3
"""Same-direction box-corner retreat choice (user-approved 2026-10-20, job 521019-05 / 061247).

Two flanges bent to the SAME side meet at a corner and collide by the sheet
thickness t, so exactly one of them retreats its end edge by t.  The retreated
end has S = -t (BEND_END_OFFSET_90 Case C: slit t+0.2 from the retreated edge
perpendicular to that flange's own bend line); the other end has S = +t (Case A,
no slit).

Choice rule
-----------
1. Compare the flange DEPTH (OD extent perpendicular to the flange's own bend
   line).  If the depths differ by >= DEPTH_TOL, the SHALLOWER flange retreats.
   Retreating the deeper one leaves a ``khuyet_t`` (a t x shallower-depth notch
   in the deeper flange's side edge, visible after unfolding and wrong for
   assembly).
2. If the depths are equal (|diff| < DEPTH_TOL) either flange may retreat; prefer
   the flange with the LONGER bend edge, for appearance only (retreating a short
   edge by t is proportionally larger).
3. If the retreat of the chosen flange is impossible because of a feature or a
   view constraint, assemble as usual and FLAG locally (this is a local FLAG,
   never a guess).

Terminology (do not mix): ``bậc`` = S, the signed bend-end offset;
``khuyết_t`` = the notch described above.  They are different quantities.

Opposite-direction crossings are not handled here: neither flange may retreat
(both printed dimensions are fixed) -> fixed outside ``R=t`` relief
(OPPOSITE_FOLD_R_T).
"""
from __future__ import annotations

import math

DEPTH_TOL = 0.1  # mm; depths differing by >= 0.1 are "different" (user, 2026-10-20)


def _positive(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name}: positive finite number required")
    return float(value)


def choose_retreat(depth_a, depth_b, bend_len_a=None, bend_len_b=None, tol=DEPTH_TOL):
    """Return which flange retreats at a same-direction corner.

    Result: {"retreat": "A"|"B", "basis": "SHALLOWER_DEPTH"|"EQUAL_DEPTH_LONGER_BEND"|
             "EQUAL_DEPTH_EITHER", "either_ok": bool, "khuyet_t_if_other": bool}
    ``either_ok`` is True only for equal depths, where retreating the other flange
    is equally valid (no khuyet_t).
    """
    a, b = _positive(depth_a, "depth_a"), _positive(depth_b, "depth_b")
    if abs(a - b) >= tol:
        return {"retreat": "A" if a < b else "B", "basis": "SHALLOWER_DEPTH",
                "either_ok": False, "khuyet_t_if_other": True}
    if bend_len_a is not None and bend_len_b is not None:
        la, lb = _positive(bend_len_a, "bend_len_a"), _positive(bend_len_b, "bend_len_b")
        if abs(la - lb) >= tol:
            return {"retreat": "A" if la > lb else "B", "basis": "EQUAL_DEPTH_LONGER_BEND",
                    "either_ok": True, "khuyet_t_if_other": False}
    return {"retreat": "A", "basis": "EQUAL_DEPTH_EITHER", "either_ok": True, "khuyet_t_if_other": False}


def retreat_violation(witness):
    """Validate a ``corner_retreat`` site witness; return an error code or None.

    witness = {"flange_ids": [a, b], "depth_mm": {a: d, b: d},
               "bend_edge_length_mm": {a: L, b: L} (optional),
               "retreated_flange_id": a_or_b, "evidence_ref": str}
    """
    try:
        ids = witness.get("flange_ids")
        if (not isinstance(ids, list) or len(ids) != 2 or len(set(ids)) != 2 or
                not witness.get("evidence_ref") or witness.get("retreated_flange_id") not in ids):
            return "BEND_END_CORNER_RETREAT_UNPROVED"
        depth = witness.get("depth_mm", {})
        length = witness.get("bend_edge_length_mm") or {}
        choice = choose_retreat(depth[ids[0]], depth[ids[1]], length.get(ids[0]), length.get(ids[1]))
    except (KeyError, TypeError, ValueError, AttributeError):
        return "BEND_END_CORNER_RETREAT_UNPROVED"
    chosen = ids[0] if choice["retreat"] == "A" else ids[1]
    if choice["either_ok"] or witness["retreated_flange_id"] == chosen:
        return None
    return "BEND_END_CORNER_RETREAT_KHUYET_T"
