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
"""
from __future__ import annotations

import json
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
    path = Path(spec["data"])
    if not path.is_file():
        _fail(f"{code}: data file {path} not found (run tools/dxf_assemble.py first)")
    assembled = json.loads(path.read_text(encoding="utf-8"))
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
    if spec["bend"].get("width") is not None:
        _, change, flag = gate(across, spec["bend"]["width"], customer, "DATA bề rộng")
        if flag:
            extra["flags"].append(flag)
    dv = float(spec.get("data_v", 0.0)) - origin[1 - k]

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
    out["outline"] = spec.get("outline") or _fail(f"{code}: a bent DATA part needs outline (usually auto)")
    out["envelope"] = spec.get("envelope") or _fail(f"{code}: envelope required (overall flat size)")
    extra["face_view"] = {"faces": [{"face": r[2], "view_range": [r[0], r[1]], "shift_along": r[3]} for r in ranges]}
    return _features(out, extra, by_member, meaning, outer_id, code, customer, mapper)


def _features(out, extra, by_member, meaning, outer_id, code, customer, mapper):
    """Holes, slots, cut-outs and KEGAKI of the DATA members; mapper(points) -> (translation, face note)."""
    holes, slots, cuts, marks = [], [], [], []
    for mid, es in by_member.items():
        if mid == outer_id:
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
                        d, change, flag = gate(d, m["pdf_d"], customer, f"{fid} Ø")
                        if change:
                            extra["changes"].append({"member": fid, "source": ref, **change})
                        if flag:
                            extra["flags"].append(flag)
                else:
                    d = m.get("d") or _fail(f"{code}: DATA POINT {mid} needs d (the PDF Ø) in members.{mid}")
                h["d"] = _r6(d)
                holes.append(h)
            elif role == "slot":
                try:
                    g = stadium_geometry(e["vertices"])
                except SlotAnchorError:
                    _fail(f"{code}: DATA slot {mid} is not a stadium: draw it as a cut-out member")
                mx, my = mv(g["midpoint"])
                slots.append({"id": fid, "group": group, "ev": ev, "datum_type": "REFERENCE_DATUM",
                              "w": _r6(g["width_mm"]), "cd": _r6(g["center_distance_mm"]),
                              "axis": [g["axis_unit"][0], g["axis_unit"][1]],
                              "wx": _ordinate(mx, ref, "SLOT_MIDPOINT"), "wy": _ordinate(my, ref, "SLOT_MIDPOINT")})
            elif role == "cutout":
                cuts.append({"id": fid, "group": group, "ev": ev,
                             "vertices": [mv(v[:2]) + [v[2]] for v in e["vertices"]]})
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


def finish(part: dict, extra: dict) -> dict:
    """Record DATA provenance and every routed change; AUTO_R corners are DATA_AUTO_R canonicalizations."""
    changes = list(extra["changes"])
    for row in part.get("corner_inventory", []):
        if row.get("decision") == "AUTO_R":
            changes.append({"rule": "DATA_AUTO_R_CANONICALIZATION", "parameter": "góc", "old": "sharp DATA vertex",
                            "new": part.get("laser_r_lookup", {}).get("laser_r"), "point": row["point"]})
    part["manufacturing_change_ledger"] = changes
    part["data_provenance"] = {"file": extra["data_file"], "source_sha256": extra["source_sha256"],
                               "transform": extra["transform"]}
    return part
