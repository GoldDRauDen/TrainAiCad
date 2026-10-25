#!/usr/bin/env python3
"""BOXMET flat generator: L, W, H1..H4, T, material, N -> flat geometry (pure; no DXF writing).

Port of GoldDRauDen/BoxMetFlatV3 (boxvip/Boxmetcommand.cs) with the user-approved 2026-10-20 changes:

* R (outer corner radius) and lead come from the repo (material table / slit_geometry.lead_val), not from
  BoxMet's own literal ``SS`` test.  Nobi N is an INPUT (handwritten > customer > table is resolved by the
  reader, see references/NOBI_TABLES.md); this tool never looks N up.
* Retreat choice per corner = tools/corner_retreat.py (depth first, longer bend edge on ties).  For equal flange
  heights this is exactly BoxMet: L >= W -> Bottom/Top retreat by T, otherwise Left/Right retreat.  With unequal
  heights the SHALLOWER flange retreats at each corner (no khuyet_t).
* Output is geometry + a canonical job skeleton.  DXF is written only by tools/export_canonical_dxf.py.

Frame: base rectangle (0,0)-(L,W) is the formed outside rectangle; bend (outside) lines are its edges and the
inner Nobi rectangle is offset by N.  Flaps extend by (H - N).  The whole flat is then translated so that its
bounding box starts at (0,0) (BasePoint = (H4-N, H1-N)).

CLI:  python tools/boxmet_flat.py --L 200 --W 150 --H 30 30 30 30 --T 1.5 --material SS --N 2.54 [--json out.json]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from corner_retreat import choose_retreat  # noqa: E402
from slit_geometry import LeadValueUnproved, connected_slit, lead_val  # noqa: E402

SLIT_COLOR = 3


class BoxMetError(ValueError):
    pass


def laser_r(material, T):
    """Outer corner Laser R from references/MATERIAL_RULES.md rows 4-6, 10-11, 18-19 (None = no approved row)."""
    from material_resolver import MaterialResolveError, resolve_material
    try:
        group = resolve_material(material)["material_family"]
    except MaterialResolveError:
        return None
    if group == "SS":
        if T <= 3.2 or 4 <= T <= 5:
            return 0.5
        if 6 <= T <= 9:
            return 2.0
    elif group in {"SUS", "SUS_OTHER"}:
        if T <= 5 or T == 6:
            return 0.5
    elif group == "AL":
        if T <= 6:
            return 0.5
    return None


def _num(value, name, positive=True):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or \
            (positive and value <= 0):
        raise BoxMetError(f"{name}: positive finite number required")
    return float(value)


def box_geometry(L, W, H1, H2, H3, H4, T, material, N):
    """H1 bottom, H2 right, H3 top, H4 left (outside heights).  Returns dict(entities, polygon, ...)."""
    L, W, T, N = _num(L, "L"), _num(W, "W"), _num(T, "T"), _num(N, "N", positive=False)
    H = {k: _num(v, k) for k, v in (("H1", H1), ("H2", H2), ("H3", H3), ("H4", H4))}
    if N < 0 or 2 * T >= min(L, W) or any(h - N <= T for h in H.values()) or 2 * N >= min(L, W):
        raise BoxMetError("BOXMET_DIMENSIONS_INVALID")
    R = laser_r(material, T)
    sharp_corners = R is None
    R = 0.0 if sharp_corners else R
    try:
        lv = lead_val(material, T)
    except LeadValueUnproved as exc:
        raise BoxMetError(str(exc)) from exc  # FLAG: no proved lead for this material/thickness
    sl = T + 0.2
    h1, h2, h3, h4 = (H["H1"] - N, H["H2"] - N, H["H3"] - N, H["H4"] - N)
    if R and any(h <= R + T for h in (h1, h2, h3, h4)):
        raise BoxMetError("BOXMET_FLAP_TOO_SHORT_FOR_R")
    # Corner retreat: "H" = Bottom/Top flap retreats, "V" = Left/Right flap retreats.
    # corner -> (horizontal flap depth, vertical flap depth)
    depths = {"BL": (H["H1"], H["H4"]), "BR": (H["H1"], H["H2"]), "TR": (H["H3"], H["H2"]), "TL": (H["H3"], H["H4"])}
    retreat = {}
    for c, (dh, dv) in depths.items():
        r = choose_retreat(dh, dv, L, W)  # A = horizontal flap
        retreat[c] = "H" if r["retreat"] == "A" else "V"
    xL, xR, yb, yt = -h4, L + h2, -h1, W + h3  # outer extents
    # Flap side positions (retreated sides pulled in by T)
    bx0 = T if retreat["BL"] == "H" else 0.0   # bottom flap left x
    bx1 = L - T if retreat["BR"] == "H" else L
    tx1 = L - T if retreat["TR"] == "H" else L
    tx0 = T if retreat["TL"] == "H" else 0.0
    ry0 = 0.0 if retreat["BR"] == "H" else T      # right flap bottom y
    ry1 = W if retreat["TR"] == "H" else W - T
    ly1 = W if retreat["TL"] == "H" else W - T
    ly0 = 0.0 if retreat["BL"] == "H" else T
    lines, arcs = [], []

    def line(a, b, dashed=False, color=0):
        lines.append({"start": (a[0], a[1]), "end": (b[0], b[1]), "dashed": dashed, "color": color})

    def arc(c, a0, a1):
        arcs.append({"center": c, "radius": R, "start_angle": a0, "end_angle": a1, "color": 0})

    # dashed outside rectangle: only over the real bend edge length (interrupted where a flap retreats)
    line((bx0, 0), (bx1, 0), True)
    line((L, ry0 if retreat["BR"] == "V" else 0), (L, ry1 if retreat["TR"] == "V" else W), True)
    line((tx1, W), (tx0, W), True)
    line((0, ly1 if retreat["TL"] == "V" else W), (0, ly0 if retreat["BL"] == "V" else 0), True)
    if 2 * N < L and 2 * N < W:  # inner Nobi rectangle
        for a, b in (((N, N), (L - N, N)), ((L - N, N), (L - N, W - N)), ((L - N, W - N), (N, W - N)),
                     ((N, W - N), (N, N))):
            line(a, b, True)
    # Bottom flap (3 lines) + extra base-side edges where the side flaps retreat
    line((bx0, 0), (bx0, yb + R)); line((bx0 + R, yb), (bx1 - R, yb)); line((bx1, yb + R), (bx1, 0))
    if retreat["BL"] == "V":
        line((0, 0), (0, T))
    if retreat["BR"] == "V":
        line((L, 0), (L, T))
    # Top flap
    line((tx1, W), (tx1, yt - R)); line((tx1 - R, yt), (tx0 + R, yt)); line((tx0, yt - R), (tx0, W))
    if retreat["TR"] == "V":
        line((L, W), (L, W - T))
    if retreat["TL"] == "V":
        line((0, W), (0, W - T))
    # Right flap
    line((bx1 if retreat["BR"] == "H" else L, ry0), (xR - R, ry0)); line((xR, ry0 + R), (xR, ry1 - R))
    line((xR - R, ry1), (tx1 if retreat["TR"] == "H" else L, ry1))
    # Left flap
    line((tx0 if retreat["TL"] == "H" else 0, ly1), (xL + R, ly1)); line((xL, ly1 - R), (xL, ly0 + R))
    line((xL + R, ly0), (bx0 if retreat["BL"] == "H" else 0, ly0))
    if R:
        arc((bx0 + R, yb + R), 180, 270); arc((bx1 - R, yb + R), 270, 360)
        arc((xR - R, ry0 + R), 270, 360); arc((xR - R, ry1 - R), 0, 90)
        arc((tx1 - R, yt - R), 0, 90); arc((tx0 + R, yt - R), 90, 180)
        arc((xL + R, ly1 - R), 90, 180); arc((xL + R, ly0 + R), 180, 270)
    # Slits (B, S direction, lead delta)
    slits = []
    spec = {
        "BL": ((T, 0), (0, 1), (-lv, -lv)) if retreat["BL"] == "H" else ((0, T), (1, 0), (-lv, -lv)),
        "BR": ((L - T, 0), (0, 1), (lv, -lv)) if retreat["BR"] == "H" else ((L, T), (-1, 0), (lv, -lv)),
        "TR": ((L - T, W), (0, -1), (lv, lv)) if retreat["TR"] == "H" else ((L, W - T), (-1, 0), (lv, lv)),
        "TL": ((T, W), (0, -1), (-lv, lv)) if retreat["TL"] == "H" else ((0, W - T), (1, 0), (-lv, lv)),
    }
    for corner, (base, direction, delta) in spec.items():
        geo = connected_slit(base, direction, delta, sl)
        slits.append({"corner": corner, "retreat_flap": "BOTTOM_TOP" if retreat[corner] == "H" else "LEFT_RIGHT",
                      "base": base, "direction": direction, "lead_delta": delta, **geo})
    # Closed outer polygon, CCW, with flap outer corners flagged for rounding
    poly = [
        (xL, ly0, True), (bx0 if retreat["BL"] == "H" else 0, ly0, False), (bx0, yb, True),   # BL
        (bx1, yb, True), (bx1, ry0 if retreat["BR"] == "V" else 0, False), (xR, ry0, True),   # BR
        (xR, ry1, True), (tx1, ry1 if retreat["TR"] == "V" else W, False), (tx1, yt, True),   # TR
        (tx0, yt, True), (tx0, ly1 if retreat["TL"] == "V" else W, False), (xL, ly1, True),   # TL
    ]
    # Concave sharp vertices: H-retreat -> (T,0)-type point; V-retreat -> (0,T)-type point.
    fix = {1: ("BL", (T, 0), (0, T)), 4: ("BR", (L - T, 0), (L, T)), 7: ("TR", (L - T, W), (L, W - T)),
           10: ("TL", (T, W), (0, W - T))}
    poly = [(*(fix[i][1] if retreat[fix[i][0]] == "H" else fix[i][2]), False) if i in fix else p
            for i, p in enumerate(poly)]
    return {"L": L, "W": W, "T": T, "N": N, "R": R, "R_sharp_flag": sharp_corners, "lead": lv, "slit_depth": sl,
            "retreat": retreat, "lines": lines, "arcs": arcs, "slits": slits, "polygon": poly,
            "bbox": (xL, yb, xR, yt), "base_point": (h4, h1)}


def translate(geo, dx, dy):
    """Return a copy of the entities/slits translated by (dx, dy)."""
    mv = lambda p: (p[0] + dx, p[1] + dy)
    out = dict(geo)
    out["lines"] = [{**e, "start": mv(e["start"]), "end": mv(e["end"])} for e in geo["lines"]]
    out["arcs"] = [{**e, "center": mv(e["center"])} for e in geo["arcs"]]
    out["slits"] = [{**s, "base": mv(s["base"]), "line1": (mv(s["line1"][0]), mv(s["line1"][1])),
                     "line2": (mv(s["line2"][0]), mv(s["line2"][1])),
                     "arc": {**s["arc"], "center": mv(s["arc"]["center"])}} for s in geo["slits"]]
    out["polygon"] = [(*mv(p[:2]), p[2]) for p in geo["polygon"]]
    b = geo["bbox"]
    out["bbox"] = (b[0] + dx, b[1] + dy, b[2] + dx, b[3] + dy)
    return out


def box_flat(L, W, H1, H2, H3, H4, T, material, N):
    """Geometry translated so the flat bounding box starts at (0, 0)."""
    geo = box_geometry(L, W, H1, H2, H3, H4, T, material, N)
    return translate(geo, geo["base_point"][0], geo["base_point"][1])


def _main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--L", type=float, required=True)
    ap.add_argument("--W", type=float, required=True)
    ap.add_argument("--H", type=float, nargs=4, required=True, metavar=("H1_BOTTOM", "H2_RIGHT", "H3_TOP", "H4_LEFT"))
    ap.add_argument("--T", type=float, required=True)
    ap.add_argument("--material", required=True)
    ap.add_argument("--N", type=float, required=True, help="Nobi per bend (resolved by the reader; never looked up here)")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    geo = box_flat(a.L, a.W, *a.H, a.T, a.material, a.N)
    text = json.dumps(geo, indent=1, default=list)
    if a.json:
        Path(a.json).write_text(text, encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):
        _stream.reconfigure(encoding="utf-8")  # Vietnamese FLAG text on a Windows console
    sys.exit(_main())
