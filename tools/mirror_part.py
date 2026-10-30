#!/usr/bin/env python3
"""対称 / 反対勝手 partner as a spec: the mirror image of another code's build spec.

    parts:
      - {code: 26-064687, ...}                                   # the source part
      - {code: 26-064688, mirror_of: {code: 26-064687, axis: y, ev: "p4 B 本図の反対勝手"}}

``axis`` follows tools/pair_consistency.py: ``y`` means y' = H - y, ``x`` means x' = W - x (W, H = the outline extents,
which start at 0). The outline is mirrored (order reversed, so it stays counter-clockwise), holes are re-measured from the
opposite flat edge with a signed witness chain, and tools/build_canonical.py runs pair_consistency on the pair afterwards.
A bent part may only be mirrored across the flat axis perpendicular to its chain (chain X -> axis y, chain Y -> axis x):
mirroring along the chain reverses the face order and is built by hand. Slots, cut-outs, KEGAKI, notch patterns, DATA parts
and two-axis chains are refused (MIRROR_UNSUPPORTED): the partner is then a hand-written part.
Keys of the partner spec other than ``code`` / ``mirror_of`` replace the mirrored ones (e.g. its own ``flags``).
"""
from __future__ import annotations

import copy

_REFUSED = ("slots", "cutouts", "kegaki", "data", "data_views")


class MirrorError(ValueError):
    pass


def _fail(msg):
    raise MirrorError(f"MIRROR_UNSUPPORTED: {msg}")


def _extent(spec, axis):
    env = spec.get("envelope") or _fail(f"{spec.get('code')}: envelope required to mirror")
    return float(env[0] if axis == "x" else env[1])


def _is_point(item):
    return isinstance(item, (list, tuple)) and len(item) >= 2 and all(isinstance(v, (int, float)) for v in item[:2])


def _mirror_outline(items, axis, size, bent_axis, code):
    i = 0 if axis == "x" else 1
    out = []
    for item in items:
        if _is_point(item):
            p = list(item)
            p[i] = round(size - float(p[i]), 6)
            out.append(p)
        elif isinstance(item, dict) and "face" in item:
            if bent_axis is None:
                _fail(f"{code}: face-relative outline point without a bend block")
            q = dict(item)
            q["v"] = round(size - float(q.get("v", 0.0)), 6)
            out.append(q)
        else:
            _fail(f"{code}: outline item {item!r} (notch pattern or unknown) cannot be mirrored: build the partner by hand")
    return out[::-1]


def _check_origin(items, axis, code):
    i = 0 if axis == "x" else 1
    lows = [float(p[i]) for p in items if _is_point(p)]
    if lows and min(lows) != 0.0:
        _fail(f"{code}: outline must start at 0 on the mirrored axis (min {min(lows):g})")


def _mirror_chain(steps, datum, size, src):
    total = datum + sum(float(s[0]) for s in steps)
    ev = f"mirror of {src}: " + "; ".join(str(s[2]) for s in steps)
    return [[size, "OUTER_EDGE", f"mirror of {src}: opposite edge"], [-total, "HOLE_CENTER", ev]]


def mirror_spec(source: dict, axis: str, code: str, source_code: str | None = None) -> dict:
    axis = str(axis).lower()
    if axis not in ("x", "y"):
        raise MirrorError("mirror axis must be x or y")
    src = copy.deepcopy(source)
    where = src.get("code", "?")
    for key in _REFUSED:
        if src.get(key):
            _fail(f"{where}: {key} is not mirrored automatically")
    bend = src.get("bend")
    bent_axis = None
    if bend:
        if "chains" in bend:
            _fail(f"{where}: a two-axis part is mirrored by hand")
        bent_axis = str(bend.get("axis", "X")).upper()
        if (bent_axis == "X") != (axis == "y"):
            _fail(f"{where}: chain along {bent_axis} cannot be mirrored with axis {axis} (that reverses the face order)")
    outline = src.get("outline")
    if not isinstance(outline, list):
        _fail(f"{where}: outline must be a list (an `auto` outline is symmetric: copy the part without mirror_of)")
    size = _extent(src, axis)
    _check_origin(outline, axis, where)
    ref = source_code or where
    src["outline"] = _mirror_outline(outline, axis, size, bent_axis, where)
    for h in src.get("holes") or []:
        if "at" in h:
            at = list(h["at"])
            at["xy".index(axis)] = round(size - float(at["xy".index(axis)]), 6)
            h["at"] = at
        if "face" in h:
            if bent_axis is None or "chain" in h:
                _fail(f"{where}: hole {h.get('id')} on a face needs a single-chain bend block")
            h["wv"] = _mirror_chain(h["wv"], float(h.get("datum_v", 0.0)), size, ref)
            h.pop("datum_v", None)
        else:
            key = "wy" if axis == "y" else "wx"
            dkey = "datum_y" if axis == "y" else "datum_x"
            h[key] = _mirror_chain(h[key], float(h.get(dkey, 0.0)), size, ref)
            h[dkey] = 0.0
    src["code"] = code
    return src


def expand_part(part: dict, siblings: dict) -> dict:
    """The spec of a ``mirror_of`` part: its source (a sibling spec of the same file) mirrored, plus its own overrides."""
    m = part["mirror_of"]
    if not isinstance(m, dict) or not m.get("code") or not m.get("axis"):
        raise MirrorError("mirror_of needs {code: <source code>, axis: x|y}")
    src = siblings.get(str(m["code"]))
    if src is None:
        raise MirrorError(f"mirror_of: source {m['code']} is not a part of the same spec file")
    if "mirror_of" in src:
        raise MirrorError("mirror_of: the source must be a built part, not itself a mirror")
    out = mirror_spec(src, m["axis"], str(part["code"]), str(m["code"]))
    out.update({k: v for k, v in part.items() if k not in ("code", "mirror_of")})
    return out
