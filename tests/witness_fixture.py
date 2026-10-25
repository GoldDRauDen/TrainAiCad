"""Test helper: give hand-built canonical fixtures the witness records the canonical contract requires.

Each PROVED HOLE/SLOT member gets OUTER_EDGE -> centre edges on X and Y measured from the outer contour's
min corner, and every PROVED slot a SLOT_MIDPOINT anchor record. Only for fixtures that test something else."""


import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from slot_anchor import stadium_geometry  # noqa: E402


def _center(ent):
    if ent["type"] == "CIRCLE":
        return ent["center"]
    if ent["type"] == "POINT":
        return ent.get("point") or ent.get("location")
    if ent.get("role") == "slot":
        return list(stadium_geometry(ent["vertices"])["midpoint"])
    xs = [v[0] for v in ent["vertices"]]
    ys = [v[1] for v in ent["vertices"]]
    return [(min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2]


def add_witnesses(job):
    for part in job["parts"]:
        if part.get("status") == "PASS":
            add_face_graph(part)
        ents = {e["entity_id"]: e for e in part["entities"]}
        outer = next(e for e in part["entities"] if e.get("role") == "outer")
        ox = min(v[0] for v in outer["vertices"])
        oy = min(v[1] for v in outer["vertices"])
        by_member = {m.get("source_member_id"): m.get("entity_ids", []) for m in part["canonical_members"]
                     if m.get("origin") == "SOURCE"}
        graph = part.setdefault("feature_witness_graph", {"nodes": {}, "edges": [], "targets": []})
        required = part.setdefault("witness_required_feature_ids", [])
        anchors = part.setdefault("slot_anchor_records", [])
        for group in part["source_groups"]:
            fam = group["family"].upper()
            if fam not in ("HOLE", "SLOT") or group["status"] != "PROVED":
                continue
            for member in group["members"]:
                mid = member["member_id"]
                if member.get("status", "PROVED") != "PROVED" or mid in required or not by_member.get(mid):
                    continue
                eid = by_member[mid][0]
                c = _center(ents[eid])
                to_type = "SLOT_MIDPOINT" if fam == "SLOT" else "HOLE_CENTER"
                required.append(mid)
                for axis, value, origin in (("X", c[0] - ox, ox), ("Y", c[1] - oy, oy)):
                    d, f = f"{mid}_{axis}_D", f"{mid}_{axis}_F"
                    graph["nodes"].update({d: "OUTER_EDGE", f: to_type})
                    graph["edges"].append({"from_node": d, "to_node": f, "axis": axis, "kind": "LOCAL",
                                           "value_mm": value, "proof": {"pdf_page": 1, "evidence_ref": "fixture",
                                                                        "endpoint_verified": True,
                                                                        "from_type": "OUTER_EDGE", "to_type": to_type}})
                    graph["targets"].append({"feature_id": mid, "datum_node": d, "feature_node": f, "axis": axis,
                                             "coordinate_mm": c[0] if axis == "X" else c[1],
                                             "datum_coordinate_mm": origin,
                                             "datum_entity_id": outer["entity_id"], "entity_id": eid})
                if fam == "SLOT":
                    g = stadium_geometry(ents[eid]["vertices"])
                    anchors.append({"slot_id": mid, "entity_id": eid, "source_pdf_page": 1, "evidence_ref": "fixture",
                                    "witness_verified": True, "anchor_point": list(g["midpoint"]),
                                    "anchor_type": "SLOT_MIDPOINT", "axis_unit": list(g["axis_unit"]),
                                    "width_mm": g["width_mm"], "center_distance_mm": g["center_distance_mm"],
                                    "overall_length_mm": g["overall_length_mm"], "canonical_midpoint": list(g["midpoint"])})
    return job


def add_face_graph(part):
    """Minimal closed face graph + per-bend ledger for a fixture's PROVED BEND members (straight bend pairs)."""
    groups = [g for g in part["source_groups"] if g["family"].upper() == "BEND" and g["status"] == "PROVED"]
    members = [(g["group_id"], m["member_id"]) for g in groups for m in g["members"]
               if m.get("status", "PROVED") == "PROVED"]
    if not members or part.get("face_graph"):
        return part
    ents = {e["entity_id"]: e for e in part["entities"]}
    by_member = {m.get("source_member_id"): m.get("entity_ids", []) for m in part["canonical_members"]}
    outer = next(e for e in part["entities"] if e.get("role") == "outer")
    faces = [{"face_id": f"F{k + 1}", "source_view": "fixture", "local_origin": [0, 0], "local_axis_u": [1, 0],
              "local_axis_v": [0, 1], "contour_edge_ids": ["fixture"], "source_dimensions": ["fixture"],
              "normal_orientation": "+Z"} for k in range(len(members) + 1)]
    bends, ledger = [], part.setdefault("per_bend_witness_ledger", [])
    for k, (gid, mid) in enumerate(members):
        lines = [ents[e] for e in by_member.get(mid, []) if ents[e]["type"] == "LINE"]
        vertical = abs(lines[0]["start"][0] - lines[0]["end"][0]) < 1e-9
        axis = 0 if vertical else 1
        lo = min(v[axis] for v in outer["vertices"])
        flat = max(v[axis] for v in outer["vertices"]) - lo
        y1, y2 = sorted(ln["start"][axis] - lo for ln in lines[:2])
        nobi = y2 - y1
        bends.append({"bend_id": f"B{k + 1}", "source_member_ids": [mid], "face_A": f"F{k + 1}", "face_B": f"F{k + 2}",
                      "face_A_shared_edge": "fixture", "face_B_shared_edge": "fixture", "edge_orientation": "fixture",
                      "attachment_source_evidence": "fixture", "signed_angle_deg": 90,
                      "material_domain": {"entity_ids": by_member[mid], "evidence_ref": "fixture"}})
        ledger.append({"bend_id": f"B{k + 1}", "source_group_id": gid, "od_actual_mm": [y2, flat + nobi - y2],
                       "bend_pair_mm": [y1, y2], "nobi_mm": nobi, "flat_mm": flat, "source_pdf_page": 1,
                       "evidence_ref": "fixture"})
    part["face_graph"] = {"faces": faces, "bends": bends}
    return part
