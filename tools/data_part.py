#!/usr/bin/env python3
"""Customer DATA part for tools/build_canonical.py: DATA geometry + PDF meaning -> an ordinary build spec.

    parts:
      - code: 26-062000
        material: SS400
        t: 3.2
        page: 1
        data: assembled_062000.json        # tools/dxf_assemble.py output (path relative to this spec)
        envelope: [300, 200]               # PDF overall size: DATA/PDF gate on the outline, never a refit
        members:                           # PDF meaning of every assembled member id except the outline
          H1: {group: D9, qty: 4, ev: "p1 4-Ø9", pdf_d: 9}     # pdf_d: the PDF Ø of the same holes (gate)
          T1: {thread: M6, qty: 2, ev: "p1 2-M6"}             # tap: one pilot from the table per DATA circle
          PT: {d: 3, piercing: true, ev: "p1 PIERCING 3-Ø3"}  # DATA POINTs need the PDF Ø
          SL1: {ev: "p1 長穴"}
          CUT1: {ev: "p1 角穴"}
          K1: {ev: "p2 ケガキ"}
        corners: [{at: [0, 0], SHARP: "lý do"}]               # optional per DATA vertex: SHARP / FLAG / R / C

DATA coordinates are copied (to 1e-6 mm), never retyped. Changes are only the routed ones, each in
`manufacturing_change_ledger` (rules/DATA_DXF.md §3): Laser R on sharp DATA corners (DATA_AUTO_R), tap pilots,
PDF_PRIORITY customer values. DATA vs PDF on the same parameter: Δ < threshold (0.1 mm; customer
data_pdf_tolerance_mm) keeps DATA; above it the customer data_pdf_policy decides (DATA_NO_DIM_COMPARE keeps DATA,
PDF_PRIORITY takes the PDF value, otherwise DATA kept + FLAG DATA_PDF_DIM_DIFF + PREVIEW).
Bend lines in DATA are not automated yet (refused with the reason).

Bent part from SEVERAL DATA views (`data_views`, rules/DATA_DXF.md section 1): each view is one dxf_assemble result with
its own proved transform (a mirror/rotation per view so that its along axis runs with the chain), `origin` (the flat edge
v = 0) and `data_faces`. Coordinates are never typed: they are `datum` members of the view read as
`<member>.<start|end|min|max>.<x|y>`. Outline corners use the same references (`START`/`END` = the chain's free edges):

    data_views:
      - {data: web.json, origin: LEFT.min.x, width: RIGHT.max.x,
         data_faces: [{face: FW, from: start, at: BOT.min.y, to: TOP.max.y}], members: {H1: {...}}}
    outline: [[LEFT.min.x, START], [FB_END.max.x, START], [SLANT.start.x, SLANT.start.y], ...]
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

import lookup
from slot_anchor import SlotAnchorError, stadium_geometry

DEFAULT_TOL_MM = 0.1


class DataPartError(ValueError):
    pass


def _fail(msg):
    raise DataPartError(msg)


def _r6(v):
    r = round(float(v), 6)
    return 0.0 if r == 0 else r


def policy(customer):
    rec = lookup.customer_record(customer) if customer is not None else {}
    return rec.get("data_pdf_policy"), float(rec.get("data_pdf_tolerance_mm", DEFAULT_TOL_MM))


def gate(data_value, pdf_value, customer, what):
    """(value to use, change row or None, flag or None) for one same-parameter DATA/PDF pair."""
    pol, tol = policy(customer)
    delta = abs(float(data_value) - float(pdf_value))
    if delta < tol - 1e-12 or pol == "DATA_NO_DIM_COMPARE":
        return float(data_value), None, None
    if pol == "PDF_PRIORITY":
        return float(pdf_value), {"rule": "PDF_PRIORITY", "parameter": what, "old": data_value, "new": pdf_value,
                                  "gate": f"Δ {delta:g} ≥ {tol:g}"}, None
    return float(data_value), None, (f"DATA_PDF_DIM_DIFF {what}: DATA {data_value:g} / PDF {pdf_value:g} "
                                     f"(Δ {delta:g} ≥ {tol:g}) - giữ DATA, xác nhận với khách")


def _ordinate(value, ref, end):
    return [[_r6(value), end, f"DATA {ref} (dxf_assemble)", "ORDINATE"]]


def to_spec(spec: dict, customer=None):
    """Return (ordinary build spec, extra records for finish())."""
    code = spec.get("code") or _fail("part: code required")
    if spec.get("data_views") is not None:
        return _views_spec(spec, customer)
    path = Path(spec["data"])
    if not path.is_file():
        _fail(f"{code}: data file {path} not found (run tools/dxf_assemble.py first)")
    assembled = json.loads(path.read_text(encoding="utf-8-sig"))
    ents = assembled.get("entities") or _fail(f"{code}: {path.name} has no entities")
    if not assembled.get("invariance", {}).get("ok"):
        _fail(f"{code}: {path.name} did not pass the dxf_assemble invariance check")
    if any(e.get("role") == "bend" for e in ents):
        _fail(f"{code}: DATA bend lines are not used: give the faces in a `bend:` block and the view of one face as "
              "`data:` + `data_face:` (rules/DATA_DXF.md)")
    if spec.get("bend") and not (spec.get("data_face") or spec.get("data_faces")):
        _fail(f"{code}: a bent DATA part needs data_face (or data_faces): which face(s) the DATA view shows")
    meaning = spec.get("members") or {}
    by_member: dict[str, list] = {}
    for e in ents:
        mid = e.get("member_id") or _fail(f"{code}: {path.name} predates member ids: run tools/dxf_assemble.py again")
        by_member.setdefault(mid, []).append(e)
    outers = [m for m, es in by_member.items() if any(e["role"] == "outer" for e in es)]
    if len(outers) != 1:
        _fail(f"{code}: DATA needs exactly one outer member, got {outers}")
    unknown = set(meaning) - set(by_member)
    if unknown:
        _fail(f"{code}: members {sorted(unknown)} are not in {path.name}")
    out = {k: v for k, v in spec.items() if k not in ("data", "members", "corners", "envelope", "data_face", "data_faces", "data_v")}
    extra = {"changes": [], "flags": [], "data_file": path.name, "transform": assembled.get("transform"),
             "source_sha256": assembled.get("source", {}).get("sha256")}

    outer = by_member[outers[0]][0]
    xs, ys = [v[0] for v in outer["vertices"]], [v[1] for v in outer["vertices"]]
    size = [max(xs) - min(xs), max(ys) - min(ys)]  # vertex extent = the builder's nominal envelope
    if spec.get("data_face") or spec.get("data_faces"):
        return _face_view(spec, out, extra, by_member, meaning, outers[0], (min(xs), min(ys)), size, customer)

    # outline: DATA vertices (arcs kept as bulges) + per-vertex corner decisions
    overrides = {}
    for c in spec.get("corners") or []:
        at = c.get("at") or _fail(f"{code}: corners[] needs at [x, y]")
        overrides[(round(float(at[0]), 4), round(float(at[1]), 4))] = {k: v for k, v in c.items() if k != "at"}
    items, used = [], set()
    for x, y, b in outer["vertices"]:
        key = (round(x, 4), round(y, 4))
        opts = dict(overrides.get(key, {}))
        if b:
            opts["bulge"] = b
        if key in overrides:
            used.add(key)
        items.append([_r6(x), _r6(y), opts] if opts else [_r6(x), _r6(y)])
    if set(overrides) - used:
        _fail(f"{code}: corners {sorted(set(overrides) - used)} are not DATA outline vertices")
    out["outline"] = items
    if spec.get("envelope"):
        for axis, (dv, pv) in enumerate(zip(size, spec["envelope"])):
            _, change, flag = gate(dv, pv, customer, f"bao {'XY'[axis]}")
            if change:
                _fail(f"{code}: PDF_PRIORITY on the overall size changes the DATA outline: build by hand")
            if flag:
                extra["flags"].append(flag)
    out["envelope"] = [_r6(v) for v in size]
    return _features(out, extra, by_member, meaning, outers[0], code, customer, lambda pts: ((0.0, 0.0), ""))


def _face_view(spec, out, extra, by_member, meaning, outer_id, origin, size, customer):
    """DATA view of faces of a one-axis bent part: each feature goes onto the face whose part of the view holds it.

    The view (after dxf_assemble: proved scale, rotated/mirrored so its along axis runs with the chain) gives, per
    face, `at` = the view coordinate of that face's datum and `to` = the other end of its visible part:
    `from: start` (datum = the face start: the previous face's outer plane, or the free edge of the first face) or
    `from: end` (the next face's outer plane, or the free edge of the last face). Across, the view's lower edge is the
    flat edge v = data_v (default 0). `data_face: W` alone = the whole view is face W from its start (its length is
    gated against the OD); a middle face's span |to - at| is gated against its OD, the view width against bend.width."""
    import bend_flat
    code = spec["code"]
    if "chains" in spec["bend"]:
        _fail(f"{code}: a DATA face view on a two-axis part: build by hand")
    try:
        ch = bend_flat.unfold_chain(spec["bend"], spec["material"], float(spec["t"]), customer, code)
    except bend_flat.BendError as exc:
        _fail(str(exc))
    k = 0 if ch["axis"] == "X" else 1
    along, across = size[k], size[1 - k]
    entries = spec.get("data_faces")
    if entries is None:
        entries = [{"face": spec["data_face"], "from": "start", "at": origin[k], "to": origin[k] + along, "gate": True}]
    ranges = _ranges(code, ch, entries, customer, extra)
    if spec["bend"].get("width") is not None:
        _, change, flag = gate(across, spec["bend"]["width"], customer, "DATA bề rộng")
        if flag:
            extra["flags"].append(flag)
    dv = float(spec.get("data_v", 0.0)) - origin[1 - k]
    mapper = _mapper(code, ranges, k, dv)
    out["outline"] = spec.get("outline") or _fail(f"{code}: a bent DATA part needs outline (usually auto)")
    out["envelope"] = spec.get("envelope") or _fail(f"{code}: envelope required (overall flat size)")
    extra["face_view"] = {"faces": [{"face": r[2], "view_range": [r[0], r[1]], "shift_along": r[3]} for r in ranges]}
    return _features(out, extra, by_member, meaning, outer_id, code, customer, mapper)


def _ranges(code, ch, entries, customer, extra):
    """[(lo, hi, face, shift)] of the data_faces entries: a feature inside [lo, hi] is on `face`, flat = view + shift."""
    ranges = []
    for n, e in enumerate(entries):
        face, frm = e.get("face"), str(e.get("from", "start"))
        f = ch["faces"].get(face) or _fail(f"{code}: data_faces[{n}] face {face} is not a face of the bend chain")
        at, to = float(e["at"]), float(e["to"])
        if frm not in ("start", "end") or (to > at) != (frm == "start"):
            _fail(f"{code}: data_faces[{n}] ({face}): from start runs to a larger view coordinate, from end to a smaller "
                  "one (mirror the view in dxf_assemble if it runs against the chain)")
        if e.get("gate") or not (f["first"] or f["last"]):
            _, change, flag = gate(abs(to - at), f["od"], customer, f"DATA {face} OD")
            if change:
                _fail(f"{code}: PDF_PRIORITY on the {face} OD changes the DATA view: build by hand")
            if flag:
                extra["flags"].append(flag)
        ranges.append((min(at, to), max(at, to), face, (f["start"] if frm == "start" else f["end"]) - at))
    return ranges


def _mapper(code, ranges, k, dv):
    def mapper(points):
        a = [pt[k] for pt in points]
        hit = [r for r in ranges if r[0] - 1e-6 <= min(a) and max(a) <= r[1] + 1e-6]
        if len(hit) != 1:
            _fail(f"{code}: DATA feature at {[round(v, 3) for v in points[0]]} is not inside exactly one data_faces "
                  "range (on a bend, or a range missing)")
        lo, hi, face, d_along = hit[0]
        shift = [0.0, 0.0]
        shift[k], shift[1 - k] = d_along, dv
        return shift, f" on {face}"
    return mapper


# ---------------------------------------------------------------- bent / flat part from several DATA views
_REF = re.compile(r"^([A-Za-z0-9_]+)\.(?:(start|end|min|max)\.([xy])|(length|radius|leg))$")
CLOSURE_TOL_MM = 0.02        # outline edges that should be straight but differ by up to this are snapped (ledger row)


def _entity_points(e):
    return [e["start"], e["end"]] if e["type"] == "LINE" else [v[:2] for v in e["vertices"]]


def _datum_scalar(mid, what, ents, code):
    from geom import bulge_circle
    if what == "length":
        total = 0.0
        for e in ents:
            if e["type"] == "LINE":
                total += math.dist(e["start"], e["end"])
            else:
                v = e["vertices"]
                _, _, r, theta = bulge_circle(v[0][:2], v[1][:2], v[0][2])
                total += r * abs(theta)
        return total
    if len(ents) != 1:
        _fail(f"{code}: {mid}.{what} needs a single datum entity")
    e = ents[0]
    if what == "radius":
        if e["type"] != "LWPOLYLINE" or not e["vertices"][0][2]:
            _fail(f"{code}: {mid}.radius needs an ARC datum")
        return bulge_circle(e["vertices"][0][:2], e["vertices"][1][:2], e["vertices"][0][2])[2]
    (x0, y0), (x1, y1) = _entity_points(e)[0], _entity_points(e)[-1]
    if e["type"] != "LINE" or abs(abs(x1 - x0) - abs(y1 - y0)) > 1e-3:
        _fail(f"{code}: {mid}.leg needs a 45-degree LINE datum (a symmetric chamfer)")
    return abs(x1 - x0)


def _datum_value(ref, datums, code):
    m = _REF.match(str(ref).strip()) or _fail(f"{code}: {ref!r} is not <datum member>.<start|end|min|max>.<x|y> or "
                                              "<member>.<length|radius|leg>")
    mid, which, ax, scalar = m.groups()
    ents = datums.get(mid) or _fail(f"{code}: {mid} is not a `datum` member of this DATA view")
    if scalar:
        return _datum_scalar(mid, scalar, ents, code)
    i = 0 if ax == "x" else 1
    if which == "start":
        return float(_entity_points(ents[0])[0][i])
    if which == "end":
        return float(_entity_points(ents[-1])[-1][i])
    vals = [float(p[i]) for e in ents for p in _entity_points(e)]
    return min(vals) if which == "min" else max(vals)


def _value(v, datums, code):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else _datum_value(v, datums, code)


def _view_of(mid, loaded, code):
    owners = [w for w in loaded if mid in w["datums"]]
    if len(owners) != 1:
        _fail(f"{code}: datum {mid} must be a `datum` member of exactly one DATA view")
    return owners[0]


def _scalar(v, loaded, code):
    """A number, `ZERO`, a scalar datum reference (<m>.length|radius|leg) or {span: [ref, ref]} = |ref1 - ref2|."""
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v)
    if isinstance(v, str) and v.strip() == "ZERO":
        return 0.0
    if isinstance(v, str):
        m = _REF.match(v.strip())
        if m and m.group(4):
            return _datum_value(v, _view_of(m.group(1), loaded, code)["datums"], code)
    if isinstance(v, dict) and isinstance(v.get("span"), (list, tuple)) and len(v["span"]) == 2:
        refs = [_REF.match(str(r).strip()) for r in v["span"]]
        if not all(refs) or any(m.group(4) for m in refs) or refs[0].group(3) != refs[1].group(3):
            _fail(f"{code}: span needs two coordinate references on the same axis, got {v['span']}")
        w = _view_of(refs[0].group(1), loaded, code)
        if refs[1].group(1) not in w["datums"]:
            _fail(f"{code}: span {v['span']} must stay inside one DATA view")
        return abs(_datum_value(v["span"][0], w["datums"], code) - _datum_value(v["span"][1], w["datums"], code))
    if isinstance(v, dict) and isinstance(v.get("hypot"), (list, tuple)) and v["hypot"]:
        return math.sqrt(sum(_scalar(x, loaded, code) ** 2 for x in v["hypot"]))     # a length from two spans (dx, dy)
    _fail(f"{code}: {v!r} is not a number, ZERO, a scalar datum reference, a span or a hypot")


def _resolve_bend(bend, loaded, customer, code, extra):
    """Face ODs and the width may be {span: [ref, ref], pdf: n}: DATA decides, the PDF value is a same-parameter gate."""
    import copy
    bend = copy.deepcopy(bend)
    slots = [(f, "od", f"DATA OD {f.get('id')}") for f in bend.get("faces", [])] + [(bend, "width", "DATA bề rộng")]
    for holder, key, what in slots:
        val = holder.get(key)
        if isinstance(val, dict):
            span = _scalar({"span": val["span"]}, loaded, code)
            if val.get("pdf") is not None:
                _, _, flag = gate(round(span, 6), val["pdf"], customer, what)
                if flag and flag not in extra["flags"]:
                    extra["flags"].append(flag)
            holder[key] = round(span, 6)
            if key == "od":
                holder["ev"] = f"{holder.get('ev', '')} [DATA span {val['span'][0]} .. {val['span'][1]}]".strip()
            elif not holder.get("width_ev"):
                holder["width_ev"] = f"DATA span {val['span'][0]} .. {val['span'][1]}"
    return bend


def _views_spec(spec, customer):
    import bend_flat
    code = spec["code"]
    flat = not spec.get("bend")                 # flat part: every view is only translated into the flat frame
    if not flat and "chains" in spec["bend"]:
        _fail(f"{code}: data_views needs a one-axis `bend:` block (two axes: build by hand)")
    extra = {"changes": [], "flags": [], "data_file": [], "transform": [], "source_sha256": [], "face_view": [], "trace": []}
    loaded = []
    for n, entry in enumerate(spec["data_views"]):
        path = Path(entry.get("data") or _fail(f"{code}: data_views[{n}] needs data"))
        if not path.is_file():
            _fail(f"{code}: data file {path} not found (run tools/dxf_assemble.py first)")
        assembled = json.loads(path.read_text(encoding="utf-8-sig"))
        if not assembled.get("invariance", {}).get("ok"):
            _fail(f"{code}: {path.name} did not pass the dxf_assemble invariance check")
        by_member: dict[str, list] = {}
        for e in assembled.get("entities") or _fail(f"{code}: {path.name} has no entities"):
            by_member.setdefault(e.get("member_id") or _fail(f"{code}: {path.name} predates member ids"), []).append(e)
        if any(e.get("role") == "bend" for es in by_member.values() for e in es):
            _fail(f"{code}: DATA bend lines are not used (faces come from the `bend:` block)")
        if any(mid in {m for w in loaded for m in w["by_member"]} for mid in by_member):
            _fail(f"{code}: member ids must be unique across data_views ({path.name})")
        loaded.append({"entry": entry, "path": path, "assembled": assembled, "by_member": by_member,
                       "datums": {mid: es for mid, es in by_member.items() if es[0]["role"] == "datum"},
                       "features": {mid: es for mid, es in by_member.items() if es[0]["role"] != "datum"}})
    out = {k: v for k, v in spec.items() if k not in ("data_views", "data", "members", "corners", "envelope", "outline")}
    ch, along_idx = None, None
    if not flat:
        bend = _resolve_bend(spec["bend"], loaded, customer, code, extra)
        out["bend"] = bend
        try:
            ch = bend_flat.unfold_chain(bend, spec["material"], float(spec["t"]), customer, code)
        except bend_flat.BendError as exc:
            _fail(str(exc))
        along_idx = 0 if ch["axis"] == "X" else 1   # flat axis of the chain = the view axis after the proved transform
    for n, w in enumerate(loaded):
        entry, datums, path = w["entry"], w["datums"], w["path"]
        sub = {"changes": [], "flags": [], "trace": []}
        w.update(k=along_idx, dv=None, mapper=None, flat=None)
        if flat:
            if entry.get("origin") is not None:
                if not isinstance(entry["origin"], (list, tuple)) or len(entry["origin"]) != 2:
                    _fail(f"{code}: a flat data view needs origin [x ref|null, y ref|null] (the flat X = 0 and Y = 0 edges)")
                org = [None if o is None else _value(o, datums, code) for o in entry["origin"]]
                w["flat"] = org

                def mapper(points, org=org):
                    if any(o is None for o in org):
                        _fail(f"{code}: a view that carries features needs both origin refs")
                    return [-org[0], -org[1]], ""
                w["mapper"] = mapper
            ranges = []
        else:
            ranges = []
            if entry.get("data_faces"):
                if entry.get("origin") is None:
                    _fail(f"{code}: data_views[{n}] needs origin (a datum reference for the flat edge v = 0)")
                origin = _value(entry["origin"], datums, code)
                faces = [{**e, "at": _value(e["at"], datums, code), "to": _value(e["to"], datums, code)}
                         for e in entry["data_faces"]]
                ranges = _ranges(code, ch, faces, customer, sub)
                if entry.get("width") is not None:
                    _, _, flag = gate(abs(_value(entry["width"], datums, code) - origin), out["bend"]["width"], customer,
                                      "DATA bề rộng")
                    if flag:
                        sub["flags"].append(flag)
                w["dv"] = float(entry.get("data_v", 0.0)) - origin
                w["mapper"] = _mapper(code, ranges, along_idx, w["dv"])
            elif entry.get("origin") is not None:
                w["dv"] = float(entry.get("data_v", 0.0)) - _value(entry["origin"], datums, code)
        meaning = entry.get("members") or {}
        if set(meaning) - set(w["features"]):
            _fail(f"{code}: members {sorted(set(meaning) - set(w['features']))} are not feature members of {path.name}")
        part_out = {}
        if w["features"]:
            if w["mapper"] is None:
                _fail(f"{code}: data_views[{n}] has feature members but no data_faces / origin to place them")
            _features(part_out, sub, w["features"], meaning, None, code, customer, w["mapper"], datums)
        for key in ("holes", "slots", "cutouts", "kegaki"):
            if part_out.get(key):
                out.setdefault(key, []).extend(part_out[key])
        for key in ("changes", "trace"):
            extra[key] += sub[key]
        extra["flags"] += [f for f in sub["flags"] if f not in extra["flags"]]
        extra["data_file"].append(path.name)
        extra["transform"].append(w["assembled"].get("transform"))
        extra["source_sha256"].append(w["assembled"].get("source", {}).get("sha256"))
        extra["face_view"].append({"view": path.name, "faces": [
            {"face": r[2], "view_range": [r[0], r[1]], "shift_along": r[3]} for r in ranges]})
    items = []
    for it in spec.get("outline") or _fail(f"{code}: data_views needs an outline (datum references)"):
        items.append(_outline_item(it, loaded, ch, along_idx, code, customer, extra))
    out["outline"] = _reconcile(items, extra, code)
    out["envelope"] = spec.get("envelope") or _fail(f"{code}: envelope required (overall flat size)")
    if extra["flags"]:
        out["flags"] = list(out.get("flags") or []) + extra["flags"]
    extra["data_file"] = ", ".join(extra["data_file"])
    return out, extra


def _coord(v, i, loaded, ch, along_idx, code, extra):
    """One outline coordinate (slot i of the point): number, ZERO, START/END, scalar/span, or a coordinate reference.
    Returns (flat value, trace dict or None)."""
    if isinstance(v, str) and v.strip() in ("START", "END"):
        if ch is None:
            _fail(f"{code}: START/END need a `bend:` chain (a flat part takes every coordinate from a datum reference)")
        if i != along_idx:
            _fail(f"{code}: START/END only fill the chain-axis coordinate of an outline point")
        return (ch["origin"] if v.strip() == "START" else ch["origin"] + ch["total"]), None
    m = _REF.match(v.strip()) if isinstance(v, str) else None
    if not m or m.group(4):                                    # number, ZERO, scalar reference, span
        return _scalar(v, loaded, code), None
    w = _view_of(m.group(1), loaded, code)
    raw = _datum_value(v, w["datums"], code)
    axis_idx = 0 if m.group(3) == "x" else 1
    if w["flat"] is not None:
        if w["flat"][axis_idx] is None or axis_idx != i:
            _fail(f"{code}: outline coordinate {v} needs its view's origin on the same axis and the same slot of the point")
        return raw - w["flat"][axis_idx], {"ref": v, "raw": raw}
    if w["dv"] is None and (w["mapper"] is None or axis_idx != w["k"]):
        _fail(f"{code}: outline coordinate {v} needs its view's origin (or data_faces)")
    if axis_idx == w["k"]:
        shift, _ = w["mapper"]([(raw, raw)])
        flat, flat_axis = raw + shift[w["k"]], along_idx
    else:
        flat, flat_axis = raw + w["dv"], 1 - along_idx
    if flat_axis != i:
        _fail(f"{code}: outline coordinate {v} is on the other flat axis than its position in the point")
    return flat, {"ref": v, "raw": raw}


def _outline_item(item, loaded, ch, along_idx, code, customer, extra):
    """One outline item with every coordinate resolved from the DATA views (rules/DATA_DXF.md)."""
    if isinstance(item, dict):
        return item
    pt, traces = [], []
    for i in (0, 1):
        value, tr = _coord(item[i], i, loaded, ch, along_idx, code, extra)
        pt.append(value)
        traces.append(tr)
    opts = dict(item[2]) if len(item) > 2 and isinstance(item[2], dict) else {}
    nominal = opts.pop("pdf", None)                           # PDF nominal [x, y] of this point: closure tie-break only
    for key in ("R", "C"):
        if key in opts and not isinstance(opts[key], (int, float)):
            val = _scalar(opts[key], loaded, code)
            opts[key] = round(val, 6)
        pdf_val = opts.pop(f"pdf_{key}", None)
        if pdf_val is not None and key in opts:
            _, _, flag = gate(opts[key], pdf_val, customer, f"{opts.get('pdf_label') or 'góc'} {key}")
            if flag:
                opts["FLAG"] = flag            # only this R / C is painted Magenta (local FLAG)
    opts.pop("pdf_label", None)
    point = [pt[0], pt[1]] + ([opts] if opts else [])
    point_meta = {"nominal": nominal, "traces": traces, "corner": {k: opts[k] for k in ("R", "C") if k in opts}}
    return _Pt(point, point_meta)


class _Pt(list):
    """An outline point [x, y, opts?] that remembers where its coordinates came from."""
    def __init__(self, items, meta):
        super().__init__(items)
        self.meta = meta


def _reconcile(items, extra, code):
    """Outline edges that are meant to be straight along an axis but whose two DATA ordinates differ by <= 0.02 mm
    (views never agree to the last digit): keep the ordinate nearer to the PDF nominal, snap the other (ledger row)."""
    n = len(items)
    for i in range(n):
        a, b = items[i], items[(i + 1) % n]
        if isinstance(a, dict) or isinstance(b, dict):
            continue
        for ax in (0, 1):
            d = abs(a[ax] - b[ax])
            if not 0 < d <= CLOSURE_TOL_MM:
                continue
            na, nb = (a.meta["nominal"] or [None, None])[ax], (b.meta["nominal"] or [None, None])[ax]
            nom = na if na is not None else nb              # the PDF dimension belongs to the edge, i.e. to both ends
            ea = None if nom is None else abs(a[ax] - nom)
            eb = None if nom is None else abs(b[ax] - nom)
            keep_a = ea is None or ea <= eb
            keep, move = (a, b) if keep_a else (b, a)
            old, new = move[ax], keep[ax]
            move[ax] = new
            for tr in move.meta["traces"][ax:ax + 1]:
                if tr:
                    tr["snapped"] = d
            extra["changes"].append({"rule": "CLOSURE_SNAP", "parameter": f"outline {'XY'[ax]}", "old": round(old, 6),
                                     "new": round(new, 6), "gate": f"Δ {d:g} ≤ {CLOSURE_TOL_MM:g}; kept the ordinate nearer "
                                                                  "to the PDF dimension" + ("" if ea is not None or eb is not None else " (none given)")})
            if ea is None and eb is None:
                extra["flags"].append(f"CLOSURE_SNAP outline {'XY'[ax]} {old:.4g} → {new:.4g}: chưa có kích thước PDF để chọn cạnh đúng hơn")
    for it in items:
        if isinstance(it, _Pt):
            extra["trace"].append({"kind": "outline", "flat": [it[0], it[1]], "traces": it.meta["traces"], "corner": it.meta["corner"]})
    return [list(it) if isinstance(it, _Pt) else it for it in items]


def _bbox(verts):
    """(width, height) of a closed bulged loop, arcs included (exact extrema)."""
    from geom import bulge_circle
    xs, ys = [v[0] for v in verts], [v[1] for v in verts]
    n = len(verts)
    for i, (x, y, b) in enumerate(verts):
        if not b:
            continue
        cx, cy, r, theta = bulge_circle((x, y), verts[(i + 1) % n][:2], b)
        a0 = math.atan2(y - cy, x - cx)
        for k in range(4):                                  # axis extremes lying on the arc's sweep
            ang = k * math.pi / 2
            rel = (ang - a0) % (2 * math.pi) if theta > 0 else (a0 - ang) % (2 * math.pi)
            if rel <= abs(theta):
                xs.append(cx + r * math.cos(ang))
                ys.append(cy + r * math.sin(ang))
    return max(xs) - min(xs), max(ys) - min(ys)


def _position_flags(m, centre, datums, code, customer, fid, n_entities):
    """Same-parameter position gate: `pdf_pos: [{from: <datum ref>, axis: x|y, pdf: n, label?}]` compares |centre - datum|
    (view coordinates, after the proved transform) with the PDF dimension; Δ >= the customer threshold is a local FLAG."""
    out = []
    for n, row in enumerate(m.get("pdf_pos") or []):
        if n_entities != 1:
            _fail(f"{code}: members.{fid}.pdf_pos needs a one-entity member (a dimension belongs to one centre)")
        if datums is None:
            _fail(f"{code}: pdf_pos needs `datum` members of a data_views view")
        axis = str(row.get("axis", "")).lower()
        if axis not in ("x", "y") or row.get("pdf") is None or not row.get("from"):
            _fail(f"{code}: members.{fid}.pdf_pos[{n}] needs from (datum ref), axis x|y and pdf")
        ref = _datum_value(row["from"], datums, code)
        _, _, flag = gate(round(abs(centre["xy".index(axis)] - ref), 6), row["pdf"], customer, row.get("label") or f"{fid} vị trí {axis.upper()}")
        if flag:
            out.append(flag)
    return out


def _features(out, extra, by_member, meaning, outer_id, code, customer, mapper, datums=None):
    """Holes, slots, cut-outs and KEGAKI of the DATA members; mapper(points) -> (translation, face note)."""
    holes, slots, cuts, marks = [], [], [], []
    for mid, es in by_member.items():
        if mid == outer_id or es[0]["role"] == "datum":
            continue
        m = meaning.get(mid) or _fail(f"{code}: DATA member {mid} needs its PDF meaning in members.{mid} "
                                      "(ev, group/qty, thread/pdf_d/piercing)")
        ev = m.get("ev") or _fail(f"{code}: members.{mid} needs ev (the PDF callout)")
        group = str(m.get("group") or mid)
        if m.get("qty") is not None and int(m["qty"]) != len(es):
            _fail(f"{code}: GROUP_COUNT_CLOSURE {mid}: PDF qty {m['qty']} but DATA has {len(es)}")
        role = es[0]["role"]
        if any(e["role"] != role for e in es):
            _fail(f"{code}: member {mid} mixes roles")
        for k, e in enumerate(es, 1):
            fid = mid if len(es) == 1 else f"{mid}_{k}"
            pts = ([e["center"]] if "center" in e else [e["point"]] if "point" in e else
                   [v[:2] for v in e["vertices"]] if "vertices" in e else [e["start"], e["end"]])
            if role == "slot":
                pts = [v[:2] for v in e["vertices"]]
            (dx, dy), where = mapper(pts)
            local = [str(m["flag"])] if m.get("flag") else []     # local FLAGs of THIS entity (painted Magenta)

            def mv(pt, dx=dx, dy=dy):
                return [pt[0] + dx, pt[1] + dy]
            ref = (",".join(e.get("source_piece_ids", [])) or e["entity_id"]) + where
            if role in ("hole", "ordinary_point"):
                c = mv(e["center"] if role == "hole" else e["point"])
                h = {"id": fid, "group": group, "ev": ev, "datum_type": "REFERENCE_DATUM", "at": [_r6(c[0]), _r6(c[1])],
                     "wx": _ordinate(c[0], ref, "HOLE_CENTER"), "wy": _ordinate(c[1], ref, "HOLE_CENTER")}
                for key in ("piercing", "through", "stamp"):
                    if key in m:
                        h[key] = m[key]
                if m.get("thread"):
                    pl = lookup.pilot(str(m["thread"]))
                    if pl.get("status") != "OK":
                        _fail(f"{code}: {mid} {pl.get('flag_vi')}")
                    d = float(pl["pilot_dia"])
                    data_d = 2 * e["radius"] if role == "hole" else None
                    if data_d is None or abs(data_d - d) > 1e-9:
                        extra["changes"].append({"member": fid, "rule": "TAP_PILOT", "parameter": "Ø",
                                                 "old": data_d, "new": d, "source": ref, "ev": f"{m['thread']} {ev}"})
                elif role == "hole":
                    d = 2 * e["radius"]
                    if m.get("pdf_d") is not None:
                        d, change, flag = gate(d, m["pdf_d"], customer, f"{m.get('pdf_label') or fid} Ø")
                        if change:
                            extra["changes"].append({"member": fid, "source": ref, **change})
                        if flag:
                            local.append(flag)
                else:
                    d = m.get("d") or _fail(f"{code}: DATA POINT {mid} needs d (the PDF Ø) in members.{mid}")
                h["d"] = _r6(d)
                local += _position_flags(m, c, datums, code, customer, fid, len(es))
                if local:
                    h["flag"] = " | ".join(local)
                holes.append(h)
                extra.setdefault("trace", []).append({"kind": "hole", "id": fid, "flat": c, "shift": [dx, dy],
                                                      "raw": list(e["center"] if role == "hole" else e["point"])})
            elif role == "slot":
                try:
                    g = stadium_geometry(e["vertices"])
                except SlotAnchorError:
                    _fail(f"{code}: DATA slot {mid} is not a stadium: draw it as a cut-out member")
                mx, my = mv(g["midpoint"])
                local += _position_flags(m, g["midpoint"], datums, code, customer, fid, len(es))
                extra.setdefault("trace", []).append({"kind": "slot", "id": fid, "flat": [mx, my], "shift": [dx, dy],
                                                      "raw": list(g["midpoint"])})
                slots.append({"id": fid, "group": group, "ev": ev, "datum_type": "REFERENCE_DATUM",
                              "w": _r6(g["width_mm"]), "cd": _r6(g["center_distance_mm"]),
                              "axis": [g["axis_unit"][0], g["axis_unit"][1]],
                              "wx": _ordinate(mx, ref, "SLOT_MIDPOINT"), "wy": _ordinate(my, ref, "SLOT_MIDPOINT"),
                              **({"flag": " | ".join(local)} if local else {})})
            elif role == "cutout":
                verts = [mv(v[:2]) + [v[2]] for v in e["vertices"]]
                if m.get("pdf_size") is not None:
                    box = _bbox(verts)
                    for axis, dv, pv in zip("XY", box, m["pdf_size"]):
                        _, change, flag = gate(round(dv, 6), pv, customer, f"{m.get('pdf_label') or fid} {axis}")
                        if change:
                            _fail(f"{code}: PDF_PRIORITY on the size of cut-out {fid} changes the DATA loop: build by hand")
                        if flag:
                            local.append(flag)
                cuts.append({"id": fid, "group": group, "ev": ev, "vertices": verts,
                             **({"flag": " | ".join(local)} if local else {})})
                extra.setdefault("trace", []).append({"kind": "cutout", "id": fid, "flat": verts, "shift": [dx, dy],
                                                      "raw": [list(v) for v in e["vertices"]]})
            elif role == "kegaki":
                marks.append({"id": fid, "group": group, "ev": ev, "lines": [mv(e["start"]) + mv(e["end"])]})
            else:
                _fail(f"{code}: DATA role {role} ({mid}) has no automatic route")
    for key, val in (("holes", holes), ("slots", slots), ("cutouts", cuts), ("kegaki", marks)):
        if val:
            out[key] = val
    if extra["flags"]:
        out["flags"] = list(out.get("flags") or []) + extra["flags"]
    return out, extra


def _boundary_distance(point, verts):
    """Distance from a point to a closed bulged polyline (arcs flattened finely) and the largest adjacent arc radius."""
    from geom import bulge_circle, bulge_points
    pts, arcs = [], []
    n = len(verts)
    for i, (x, y, b) in enumerate(verts):
        pts.append((x, y))
        if b:
            q = verts[(i + 1) % n]
            arcs.append((bulge_circle((x, y), q[:2], b)[2], (x, y), tuple(q[:2])))
            pts += bulge_points((x, y), q[:2], b, 200)
    best = math.inf
    for p0, p1 in zip(pts, pts[1:] + pts[:1]):
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        L2 = dx * dx + dy * dy
        u = 0.0 if L2 == 0 else max(0.0, min(1.0, ((point[0] - p0[0]) * dx + (point[1] - p0[1]) * dy) / L2))
        best = min(best, math.hypot(point[0] - (p0[0] + u * dx), point[1] - (p0[1] + u * dy)))
    near = [r for r, a, b in arcs if min(math.dist(point, a), math.dist(point, b)) <= 1.6 * r]
    return best, (max(near) if near else 0.0)


def _roundtrip(part, extra):
    """After the whole build every harvested coordinate must map back to the DATA coordinate (rules/DATA_DXF.md §3):
    holes, slot midpoints and cut-out loops invert their view shift; outline corners lie on the contour (a rounded
    corner within its R); the only allowed deviations are the CLOSURE_SNAP rows (<= 0.02 mm)."""
    code = part["code"]
    ents = {e["entity_id"]: e for e in part["entities"]}
    outer = next((e for e in part["entities"] if e.get("role") == "outer"), None)
    bad = []
    for t in extra.get("trace", []):
        kind = t["kind"]
        if kind in ("hole", "slot"):
            e = ents.get(f"E_{code}_{t['id']}")
            got = (e.get("center") or e.get("point")) if e and kind == "hole" else None
            if kind == "slot":
                rec = next((r for r in part.get("slot_anchor_records", []) if r.get("entity_id") == f"E_{code}_{t['id']}"), None)
                got = rec["canonical_midpoint"] if rec else None
            if got is None or math.dist([got[0] - t["shift"][0], got[1] - t["shift"][1]], t["raw"]) > 2e-6:
                bad.append(f"{kind} {t['id']}")
        elif kind == "cutout":
            e = ents.get(f"E_{code}_{t['id']}")
            want = sorted((round(v[0], 6), round(v[1], 6), round(v[2], 6)) for v in t["flat"])
            if e is None or sorted((round(v[0], 6), round(v[1], 6), round(v[2], 6)) for v in e["vertices"]) != want:
                bad.append(f"cutout {t['id']}")
        elif kind == "outline" and outer is not None:
            dist, r = _boundary_distance(t["flat"], outer["vertices"])
            called = t.get("corner") or {}
            cut = max(called.get("R", 0.0) * (math.sqrt(2) - 1), called.get("C", 0.0) / math.sqrt(2))   # a called R/C cuts the corner
            allow = 2e-6 + max(r * (math.sqrt(2) - 1), cut) + max((tr.get("snapped", 0) for tr in t["traces"] if tr), default=0.0)
            if dist > allow:
                bad.append(f"outline point {t['flat']}")
    if bad:
        _fail(f"{code}: DATA_ROUNDTRIP_FAIL: {', '.join(bad[:6])} no longer map back to the DATA coordinates")


def finish(part: dict, extra: dict) -> dict:
    """Record DATA provenance and every routed change; AUTO_R corners are DATA_AUTO_R canonicalizations."""
    changes = list(extra["changes"])
    for row in part.get("corner_inventory", []):
        if row.get("decision") == "AUTO_R":
            changes.append({"rule": "DATA_AUTO_R_CANONICALIZATION", "parameter": "góc", "old": "sharp DATA vertex",
                            "new": part.get("laser_r_lookup", {}).get("laser_r"), "point": row["point"]})
    _roundtrip(part, extra)
    part["manufacturing_change_ledger"] = changes
    part["data_provenance"] = {"file": extra["data_file"], "source_sha256": extra["source_sha256"],
                               "transform": extra["transform"]}
    return part
