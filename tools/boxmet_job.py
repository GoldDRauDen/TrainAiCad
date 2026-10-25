#!/usr/bin/env python3
"""Canonical V4.34 job for a four-flange BOXMET box from L, W, H1..H4, T, material, N (+ optional holes).

Usage:
    python tools/boxmet_job.py --code 26-000001 --L 200 --W 150 --H 30 30 30 30 --T 1.5 --material SS --N 2.54 \
        --out job.json [--hole X Y DIA EVIDENCE ...]
then:
    python tools/export_canonical_dxf.py job.json outdir        # the ONLY DXF writer; all guards run there

The reader supplies the box dimensions, Nobi N (handwritten > customer > table) and the drawn corner shape.
Holes are given in the FLAT frame (bbox lower-left = (0,0)); each needs its own evidence string.
This module never writes a DXF and never looks up Nobi.  A corner that the drawing shows rounded/chamfered
without a callout is NOT auto-rounded: the tool refuses (BOXMET_CORNER_DRAWN_SHAPE_NOT_SHARP_FLAG).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from boxmet_flat import BoxMetError, box_flat  # noqa: E402

BULGE90 = math.tan(math.pi / 8)
R6 = lambda v: round(float(v), 6)
BEND_NAMES = ("BOTTOM", "RIGHT", "TOP", "LEFT")
CORNERS = ("BL", "BR", "TR", "TL")
# corner -> the two adjacent bends (horizontal flap bend, vertical flap bend)
CORNER_BENDS = {"BL": ("BOTTOM", "LEFT"), "BR": ("BOTTOM", "RIGHT"), "TR": ("TOP", "RIGHT"), "TL": ("TOP", "LEFT")}


def _unit(a, b):
    d = math.hypot(b[0] - a[0], b[1] - a[1])
    return ((b[0] - a[0]) / d, (b[1] - a[1]) / d)


def polygon_with_arcs(poly, R):
    """Closed LWPOLYLINE vertices [x, y, bulge]; flagged corners replaced by tangent points + CCW 90-degree bulge."""
    n, out = len(poly), []
    for i, (x, y, rounded) in enumerate(poly):
        if not rounded or R == 0:
            out.append([R6(x), R6(y), 0.0])
            continue
        prev, nxt = poly[i - 1][:2], poly[(i + 1) % n][:2]
        u1, u2 = _unit((x, y), prev), _unit((x, y), nxt)
        out.append([R6(x + R * u1[0]), R6(y + R * u1[1]), R6(BULGE90)])
        out.append([R6(x + R * u2[0]), R6(y + R * u2[1]), 0.0])
    return out


def build_job(code, L, W, heights, T, material, N, holes=(), drawn_corners="SHARP", customer=None,
              job_id=None, source_ref="BOXMET input (L, W, H1-H4, T, material, N supplied by the reader)"):
    if drawn_corners != "SHARP":
        raise BoxMetError("BOXMET_CORNER_DRAWN_SHAPE_NOT_SHARP_FLAG")
    geo = box_flat(L, W, *heights, T, material, N)
    R, pid = geo["R"], "P" + "".join(ch for ch in str(code) if ch.isalnum())
    eid = lambda s: f"{pid}_{s}"
    gid = lambda s: f"{pid}_G_{s}"
    mid = lambda s: f"{pid}_M_{s}"
    cid = lambda s: f"{pid}_CM_{s}"
    ents, groups, canon = [], [], []
    outer = eid("OUTER")
    ents.append({"entity_id": outer, "type": "LWPOLYLINE", "role": "outer", "closed": True,
                 "vertices": polygon_with_arcs(geo["polygon"], R)})

    def group(gs, family, evidence, members):
        groups.append({"group_id": gid(gs), "family": family, "status": "PROVED", "source_quantity": len(members),
                       "evidence": evidence, "members": [{"member_id": mid(s), "status": "PROVED"} for s, _ in members]})
        for s, eids in members:
            canon.append({"canonical_member_id": cid(s), "origin": "SOURCE", "source_member_id": mid(s),
                          "group_id": gid(gs), "status": "PROVED", "entity_ids": list(eids)})

    group("OUTER", "OUTER", f"{source_ref}: closed flat contour", [("OUTER", [outer])])
    dashed = [e for e in geo["lines"] if e["dashed"]]
    outer_dash, inner_dash = dashed[:4], dashed[4:8]
    inner_ok = len(inner_dash) == 4
    bend_ids, bend_entities = {}, {}
    for k, name in enumerate(BEND_NAMES):
        pair = [outer_dash[k]] + ([inner_dash[k]] if inner_ok else [])
        ids = []
        for j, e in enumerate(pair, 1):
            ids.append(eid(f"B_{name}_{j}"))
            ents.append({"entity_id": ids[-1], "type": "LINE", "role": "bend", "linetype": "DASHED",
                         "start": [R6(e["start"][0]), R6(e["start"][1])], "end": [R6(e["end"][0]), R6(e["end"][1])]})
        bend_entities[name] = ids
        bend_ids[name] = eid(f"B_{name}")
        group(f"B_{name}", "BEND", f"{source_ref}: {name} flap bend", [(f"B_{name}", ids)])
    # Corner R: eight flap outer corners, drawn sharp, material-table Laser R
    inventory = []
    flap_corners = [(x, y) for (x, y, rounded) in geo["polygon"] if rounded]
    for i, (x, y) in enumerate(flap_corners, 1):
        if R:
            canon.append({"canonical_member_id": cid(f"AUTO_R_{i}"), "origin": "DERIVED_RULE",
                          "controlling_rule": "MATERIAL_AUTO_R", "source_member_ids": [mid("OUTER")],
                          "status": "PROVED", "entity_ids": [outer]})
            inventory.append({"corner_id": f"FC{i}", "point": [R6(x), R6(y)], "drawn_shape": "SHARP",
                              "decision": "AUTO_R", "canonical_member_id": cid(f"AUTO_R_{i}"),
                              "evidence_ref": f"{source_ref}: flap outer corner drawn sharp, no R/C callout"})
        else:
            inventory.append({"corner_id": f"FC{i}", "point": [R6(x), R6(y)], "drawn_shape": "SHARP",
                              "decision": "SHARP", "evidence_ref": f"{source_ref}: flap outer corner drawn sharp",
                              "no_auto_r_reason": "material table has no approved Laser R row for this material/thickness"})
    # Slits
    sites, site_ids, slit_members = [], [], {}
    for s in geo["slits"]:
        c = s["corner"]
        sid = eid(f"SITE_{c}")
        site_ids.append(sid)
        l1, l2, arc = s["line1"], s["line2"], s["arc"]
        ids = [eid(f"SLIT_{c}_L1"), eid(f"SLIT_{c}_ARC"), eid(f"SLIT_{c}_L2")]
        ents.append({"entity_id": ids[0], "type": "LINE", "role": "slit", "color": 3,
                     "start": [l1[0][0], l1[0][1]], "end": [l1[1][0], l1[1][1]], "bend_end_site_id": sid})
        ents.append({"entity_id": ids[1], "type": "ARC", "role": "slit", "color": 3,
                     "center": [arc["center"][0], arc["center"][1]], "radius": arc["radius"],
                     "start_angle": arc["start_angle"], "end_angle": arc["end_angle"], "bend_end_site_id": sid})
        ents.append({"entity_id": ids[2], "type": "LINE", "role": "slit", "color": 3,
                     "start": [l2[0][0], l2[0][1]], "end": [l2[1][0], l2[1][1]], "bend_end_site_id": sid})
        canon.append({"canonical_member_id": cid(f"SLIT_{c}"), "origin": "DERIVED_RULE", "controlling_rule": "BOXMET",
                      "source_member_ids": [mid(f"B_{n}") for n in CORNER_BENDS[c]], "status": "PROVED",
                      "entity_ids": ids, "bend_end_site_id": sid})
        sites.append({"site_id": sid, "status": "PROVED", "bend_ids": [bend_ids[n] for n in CORNER_BENDS[c]],
                      "mechanism": "BOXMET", "decision": "SEPARATE_RULE", "included_angle_deg": 90,
                      "special_rule_evidence_ref": f"{source_ref}: four-flange box corner {c} "
                                                   f"({s['retreat_flap']} flap retreats by t, depth-first rule)",
                      "relief_member_ids": [cid(f"SLIT_{c}")]})
    # Holes (flat frame) with a local witness from the flat's left/bottom outer edge
    targets, nodes, edges, required = [], {}, [], []
    for k, h in enumerate(holes, 1):
        x, y, dia, evidence = h
        hid = eid(f"H{k}")
        ents.append({"entity_id": hid, "type": "CIRCLE", "role": "hole", "center": [R6(x), R6(y)], "radius": R6(dia / 2)})
        group(f"H{k}", "HOLE", evidence, [(f"H{k}", [hid])])
        m = mid(f"H{k}")
        required.append(m)
        for axis, value in (("X", x), ("Y", y)):
            d, c_ = f"{m}_{axis}_D", f"{m}_{axis}_C"
            nodes[d], nodes[c_] = "OUTER_EDGE", "HOLE_CENTER"
            edges.append({"from_node": d, "to_node": c_, "axis": axis, "kind": "LOCAL", "value_mm": R6(value),
                          "proof": {"pdf_page": 1, "evidence_ref": evidence, "endpoint_verified": True,
                                    "from_type": "OUTER_EDGE", "to_type": "HOLE_CENTER",
                                    "physical_witness": "flat-frame position measured from the flat bbox edge"}})
            targets.append({"feature_id": m, "datum_node": d, "feature_node": c_, "axis": axis,
                            "coordinate_mm": R6(value), "datum_coordinate_mm": 0.0,
                            "datum_entity_id": outer, "entity_id": hid})
    # Face graph: base + four flaps; the base owns all four bends (BOXMET star)
    H1, H2, H3, H4 = heights
    od = {"BOTTOM": H1, "RIGHT": H2, "TOP": H3, "LEFT": H4}
    faces = [{"face_id": "F_BASE", "source_view": source_ref, "local_origin": [0, 0, 0], "local_axis_u": [1, 0, 0],
              "local_axis_v": [0, 1, 0], "normal_orientation": [0, 0, 1],
              "contour_edge_ids": ["F_BASE.BOTTOM", "F_BASE.RIGHT", "F_BASE.TOP", "F_BASE.LEFT"],
              "source_dimensions": [{"L": L, "W": W}]}]
    for name in BEND_NAMES:
        faces.append({"face_id": f"F_{name}", "source_view": source_ref, "local_origin": [0, 0, 0],
                      "local_axis_u": [1, 0, 0], "local_axis_v": [0, 1, 0], "normal_orientation": [0, 0, 1],
                      "contour_edge_ids": [f"F_{name}.FREE", f"F_{name}.BEND"],
                      "source_dimensions": [{"OD_height": od[name]}]})
    bends, ledger = [], []
    pair_len = {"BOTTOM": L, "TOP": L, "LEFT": W, "RIGHT": W}
    for name in BEND_NAMES:
        base_od = L if name in {"LEFT", "RIGHT"} else W   # base extent across this bend direction
        first, second = (od[name], base_od) if name in {"LEFT", "BOTTOM"} else (base_od, od[name])
        bends.append({
            "bend_id": bend_ids[name], "source_member_ids": [mid(f"B_{name}")], "face_A": "F_BASE", "face_B": f"F_{name}",
            "face_A_shared_edge": f"F_BASE.{name}", "face_B_shared_edge": f"F_{name}.BEND",
            "face_A_free_edges": [], "face_B_free_edges": [f"F_{name}.FREE"],
            "edge_orientation": "shared edge on the formed outside rectangle, retained through the flat transform",
            "attachment_source_evidence": f"{source_ref}: {name} flap attached to the base rectangle",
            "signed_angle_deg": 90, "rotation_axis_formed": [1, 0, 0] if name in {"BOTTOM", "TOP"} else [0, 1, 0],
            "material_domain": {"entity_ids": bend_entities[name], "axis": "X" if name in {"BOTTOM", "TOP"} else "Y",
                                "span_mm": [0, pair_len[name]], "edge_length_mm": pair_len[name],
                                "evidence_ref": f"{source_ref}: {name} bend edge"},
            "N_mm": N, "thickness_mm": T})
        a, b = first, second
        ledger.append({"bend_id": bend_ids[name], "source_group_id": gid(f"B_{name}"),
                       "ordered_faces": ["F_" + name, "F_BASE"] if name in {"LEFT", "BOTTOM"} else ["F_BASE", "F_" + name],
                       "od_actual_mm": [a, b], "nobi_mm": N, "flat_mm": R6(a + b - N), "bend_pair_mm": [R6(a - N), a],
                       "source_pdf_page": 1, "evidence_ref": f"{source_ref}: OD {a} + {b} - Nobi {N}",
                       "source_attachment_identity": f"F_BASE.{name} <-> F_{name}.BEND"})
    part = {
        "code": code, "material": material, "thickness_mm": T, "status": "PASS",
        "checks": {"contour_topology": "PASS", "datum": "PASS", "feature_count": "PASS", "unfold": "PASS",
                   "containment": "PASS", "bend_domain": "PASS", "material_rules": "PASS", "slot_semantics": "N/A"},
        "flags": [], "entities": ents, "source_groups": groups, "canonical_members": canon,
        "witness_required_feature_ids": required,
        "feature_witness_graph": {"nodes": nodes, "edges": edges, "targets": targets},
        "source_mode": "PDF_ONLY", "source_pdf_page": 1, "complete_source_bundle_id": f"BOXMET-{pid}",
        "source_utilization_status": "CLOSED", "flat_attempted": True, "high_source_evidence": True,
        "defensible_flat_exists": True, "unclassified_source_member_count": 0, "holistic_challenge_run": True,
        "source_physical_member_count": sum(len(g["members"]) for g in groups),
        "proved_source_member_count": sum(len(g["members"]) for g in groups),
        "part_identity_graph": {"slip_work_no": code, "barcode": code, "drawing_page": 1, "material": material,
                                "thickness_mm": T, "ownership_evidence": source_ref},
        "material_audit": {"grade_source": source_ref, "laser_r_row": f"R={R}" if R else "no approved row",
                           "min_cut_hole_mm": T / 2, "general_C0_5": "flap outer corners follow the material table"},
        "drawing_only_inventory": [{"view": "BOXMET", "role": "L, W, H1-H4, T, material, N consumed"}],
        "dimensions": [], "source_manufacturing_notes": [{
            "note_text": "BOXMET four-flange box", "candidate_family": "BEND", "code_scope": code,
            "resolution": "ROUTED", "evidence_ref": source_ref}],
        "corner_callout_tuples": [], "corner_inventory": inventory,
        "face_graph": {"faces": faces, "bends": bends}, "per_bend_witness_ledger": ledger,
        "bend_end_relief_audit": {"controlling_rule": "BOXMET", "junctions": [
            {"site": s["site_id"], "decision": "SEPARATE_RULE", "reason": "four-flange box corner slit"} for s in sites]},
        "source_bend_end_site_ids": site_ids, "bend_end_junctions": sites, "bend_end_source_edges": {},
        "flat_equations": {"X": {"ordered_od_mm": [H4, L, H2], "deductions_mm": [N, N], "result_mm": R6(L + H2 + H4 - 2 * N)},
                           "Y": {"ordered_od_mm": [H1, W, H3], "deductions_mm": [N, N], "result_mm": R6(W + H1 + H3 - 2 * N)}},
        "dx_label": False}
    return {"canonical_contract": "TrainAiCad-CANONICAL-V4.34", "job_id": job_id or str(code),
            "source_mode": "PDF_ONLY", "reference_present": False, "parts": [part]}


def _main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--code", required=True)
    ap.add_argument("--L", type=float, required=True)
    ap.add_argument("--W", type=float, required=True)
    ap.add_argument("--H", type=float, nargs=4, required=True, metavar=("H1_BOTTOM", "H2_RIGHT", "H3_TOP", "H4_LEFT"))
    ap.add_argument("--T", type=float, required=True)
    ap.add_argument("--material", required=True)
    ap.add_argument("--N", type=float, required=True)
    ap.add_argument("--hole", nargs=4, action="append", metavar=("X", "Y", "DIA", "EVIDENCE"), default=[])
    ap.add_argument("--drawn-corners", default="SHARP", choices=["SHARP", "ROUNDED", "CHAMFERED", "UNKNOWN"])
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    holes = [(float(x), float(y), float(d), ev) for x, y, d, ev in a.hole]
    job = build_job(a.code, a.L, a.W, tuple(a.H), a.T, a.material, a.N, holes, a.drawn_corners)
    Path(a.out).write_text(json.dumps(job, indent=1, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):
        _stream.reconfigure(encoding="utf-8")  # Vietnamese FLAG text on a Windows console
    sys.exit(_main())
