"""Source-edge bend-end step and scoped mechanism validation before DXF save.

The reader must inventory sites and prove edge identities/directions from source.
This guard remeasures those declared witnesses; it does not discover PDF sites.
Legacy jobs without this inventory retain their original contract.
"""
from __future__ import annotations

import math

TOL = 1e-7  # Coordinate arithmetic tolerance, never a manufacturing S threshold.
AUTO_RELIEF_RULES = {"BEND_END_OFFSET_90", "OPPOSITE_FOLD_R_T", "CROSSING_BEND", "BOXMET", "NON_90_RELIEF"}
SPECIAL_RULES = {"OPPOSITE_FOLD_R_T", "CROSSING_BEND", "BOXMET", "CUSTOM_SOURCE_SLIT", "NON_90_RELIEF"}
RELIEF_ROLES = {"slit", "relief", "bend_relief"}


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("BEND_END_NUMBER_INVALID")
    return float(value)


def _point(value):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError("BEND_END_EDGE_UNPROVED")
    return tuple(_number(x) for x in value)


def _edge(edges, eid, frame):
    edge = edges.get(eid)
    if not isinstance(edge, dict):
        raise ValueError("BEND_END_EDGE_UNPROVED")
    if not frame or edge.get("frame_id") != frame:
        raise ValueError("BEND_END_FRAME_MISMATCH")
    proof = edge.get("proof", {})
    if (edge.get("type") != "LINE" or not edge.get("physical_edge_id") or
            not isinstance(proof, dict) or proof.get("endpoint_verified") is not True or
            not proof.get("evidence_ref") or not (proof.get("source_pdf_page") or proof.get("source_ref"))):
        raise ValueError("BEND_END_EDGE_UNPROVED")
    start, end = _point(edge.get("start")), _point(edge.get("end"))
    if math.dist(start, end) <= TOL:
        raise ValueError("BEND_END_EDGE_UNPROVED")
    return start, end


def _measured_step(site, edges):
    if not site.get("positive_axis_evidence_ref"):
        raise ValueError("BEND_END_DIRECTION_UNPROVED")
    axis = _point(site.get("positive_axis"))
    if abs(math.hypot(*axis)-1) > TOL:
        raise ValueError("BEND_END_MEASUREMENT_AXIS_INVALID")
    flush = _edge(edges, site.get("flush_edge_id"), site.get("frame_id"))
    web = _edge(edges, site.get("web_edge_id"), site.get("frame_id"))
    if edges[site["flush_edge_id"]]["physical_edge_id"] == edges[site["web_edge_id"]]["physical_edge_id"]:
        raise ValueError("BEND_END_EDGE_IDENTITY_INVALID")
    for a, b in (flush, web):
        delta = (b[0]-a[0], b[1]-a[1])
        if abs(sum(delta[i]*axis[i] for i in range(2))) > TOL*math.hypot(*delta):
            raise ValueError("BEND_END_MEASUREMENT_AXIS_INVALID")
    return math.fsum((web[0][i]-flush[0][i])*axis[i] for i in range(2))


def _physical_intersection(site, edges):
    ids = site.get("intersection_edge_ids")
    if not isinstance(ids, list) or len(ids) != 2 or len(set(ids)) != 2:
        return False
    try:
        a, b = _edge(edges, ids[0], site.get("frame_id"))
        c, d = _edge(edges, ids[1], site.get("frame_id"))
    except (ValueError, TypeError):
        return False
    if ({edges[eid].get("bend_id") for eid in ids} != set(site["bend_ids"]) or
            edges[ids[0]]["physical_edge_id"] == edges[ids[1]]["physical_edge_id"]):
        return False
    u, v, w = (b[0]-a[0], b[1]-a[1]), (d[0]-c[0], d[1]-c[1]), (c[0]-a[0], c[1]-a[1])
    cross = lambda x, y: x[0]*y[1]-x[1]*y[0]
    denom = cross(u, v)
    if abs(denom) <= TOL*math.hypot(*u)*math.hypot(*v):
        return False
    if site.get("mechanism") == "CROSSING_BEND" and abs(sum(u[i]*v[i] for i in range(2))) > TOL*math.hypot(*u)*math.hypot(*v):
        return False
    return all(-TOL <= value <= 1+TOL for value in (cross(w, v)/denom, cross(w, u)/denom))


def _automatic_relief(member, entities):
    return (member.get("controlling_rule") in AUTO_RELIEF_RULES or
            member.get("origin") == "DERIVED_RULE" and
            any(entities.get(eid, {}).get("role") in RELIEF_ROLES for eid in member.get("entity_ids", [])))


def _relief_members_proved(site, relief, entities):
    for member in relief:
        if (member.get("status") != "PROVED" or member.get("bend_end_site_id") != site["site_id"] or
                not member.get("entity_ids") or
                member.get("origin") == "DERIVED_RULE" and member.get("controlling_rule") != site.get("mechanism") or
                member.get("origin") == "SOURCE" and site.get("mechanism") != "CUSTOM_SOURCE_SLIT"):
            return False
        for eid in member["entity_ids"]:
            ent = entities.get(eid, {})
            if (ent.get("bend_end_site_id") != site["site_id"] or ent.get("role") not in RELIEF_ROLES or
                    ent.get("type") not in {"LINE", "ARC"} or ent.get("color") != 3):
                return False
    return True


def _slit_construction_proved(site, part, edges, relief, entities, bends):
    """Rebuild the existing connected slit rule from proved canonical-flat edges."""
    from slit_geometry import connected_slit, lead_end_by_offset, lead_val, slit_dir_from_bend
    try:
        witness = site.get("slit_construction", {})
        if not witness.get("evidence_ref") or witness.get("bend_id") not in site["bend_ids"]:
            return False
        a, b = _edge(edges, witness.get("actual_edge_id"), "CANONICAL_FLAT")
        c, d = _edge(edges, witness.get("side_edge_id"), "CANONICAL_FLAT")
        if edges[witness["actual_edge_id"]]["physical_edge_id"] != edges[site["web_edge_id"]]["physical_edge_id"]:
            return False
        u, v, w = (b[0]-a[0], b[1]-a[1]), (d[0]-c[0], d[1]-c[1]), (c[0]-a[0], c[1]-a[1])
        cross = lambda x, y: x[0]*y[1]-x[1]*y[0]
        denom = cross(u, v)
        if abs(denom) <= TOL*math.hypot(*u)*math.hypot(*v):
            return False
        t, s = cross(w, v)/denom, cross(w, u)/denom
        if not all(-TOL <= k <= 1+TOL for k in (t, s)):
            return False
        base = (a[0]+t*u[0], a[1]+t*u[1])
        web_n, side_n = _point(witness.get("web_void_normal")), _point(witness.get("side_void_normal"))
        if any(abs(sum(vec[i]*normal[i] for i in range(2))) > TOL*math.hypot(*vec)
               for vec, normal in ((u, web_n), (v, side_n))):
            return False
        bend_entities = [entities[eid] for eid in bends[witness["bend_id"]].get("material_domain", {}).get("entity_ids", [])]
        bend_line = next(e for e in bend_entities if e.get("type") == "LINE" and e.get("role") == "bend")
        start, end = _point(bend_line["start"]), _point(bend_line["end"])
        direction = slit_dir_from_bend((end[0]-start[0], end[1]-start[1]), witness.get("inward_hint"))
        if sum(direction[i]*web_n[i] for i in range(2)) >= -TOL:
            return False
        thickness = _number(part.get("thickness_mm"))
        lead = lead_end_by_offset(base, side_n, web_n, lead_val(part.get("material"), thickness))
        expected = connected_slit(base, direction, (lead[0]-base[0], lead[1]-base[1]), thickness+0.2)
        actual = [entities[eid] for m in relief for eid in m["entity_ids"]]
        lines, arcs = [e for e in actual if e["type"] == "LINE"], [e for e in actual if e["type"] == "ARC"]
        if len(lines) != 2 or len(arcs) != 1:
            return False
        close = lambda p, q: math.dist(_point(p), _point(q)) <= TOL
        for key in ("line1", "line2"):
            p, q = expected[key]
            match = next((e for e in lines if (close(e["start"], p) and close(e["end"], q)) or
                          (close(e["end"], p) and close(e["start"], q))), None)
            if match is None:
                return False
            lines.remove(match)
        arc, wanted = arcs[0], expected["arc"]
        return (close(arc["center"], wanted["center"]) and abs(_number(arc["radius"])-wanted["radius"]) <= TOL and
                all(abs((_number(arc[key])-wanted[key]+180) % 360-180) <= TOL for key in ("start_angle", "end_angle")))
    except (ValueError, TypeError, KeyError, StopIteration):
        return False


def _special_rule(site, part, edges, relief):
    mechanism = site.get("mechanism")
    if not relief:
        return "BEND_END_RELIEF_MEMBER_UNPROVED"
    if not site.get("special_rule_evidence_ref") or site.get("decision") != "SEPARATE_RULE":
        return "BEND_END_SPECIAL_RULE_UNPROVED"
    if mechanism in {"OPPOSITE_FOLD_R_T", "CROSSING_BEND"}:
        if not _physical_intersection(site, edges):
            return "BEND_END_PHYSICAL_INTERSECTION_UNPROVED"
    elif mechanism == "BOXMET":
        neighbors = {}
        for bend in part.get("face_graph", {}).get("bends", []):
            for a, b in ((bend.get("face_A"), bend.get("face_B")), (bend.get("face_B"), bend.get("face_A"))):
                neighbors.setdefault(a, set()).add(b)
        controlled_faces = [{b.get("face_A"), b.get("face_B")} for b in part.get("face_graph", {}).get("bends", [])
                            if b.get("bend_id") in site["bend_ids"]]
        common = set.intersection(*controlled_faces)
        if not any(face and len(neighbors.get(face, set())) == 4 and None not in neighbors[face] for face in common):
            return "BEND_END_SPECIAL_RULE_UNPROVED"
    elif mechanism == "CUSTOM_SOURCE_SLIT":
        group = next((g for g in part.get("source_groups", []) if g.get("group_id") == site.get("source_group_id")), {})
        source_ids = {m.get("member_id") for m in group.get("members", [])}
        if (group.get("family") != "SLIT_RELIEF" or group.get("status") != "PROVED" or
                not group.get("evidence") or not relief or
                any(m.get("origin") != "SOURCE" or m.get("source_member_id") not in source_ids for m in relief)):
            return "BEND_END_SPECIAL_RULE_UNPROVED"
    elif mechanism == "NON_90_RELIEF":
        if abs(_number(site.get("included_angle_deg"))-90) <= TOL or not site.get("angle_evidence_ref"):
            return "BEND_END_SPECIAL_RULE_UNPROVED"
    return None


def bend_end_errors(part):
    """Check a declared source site inventory, its actual S witnesses and output owners."""
    keys = ("source_bend_end_site_ids", "bend_end_junctions", "bend_end_source_edges")
    entities = {e.get("entity_id"): e for e in part.get("entities", [])}
    if not any(key in part for key in keys):
        if (any(_automatic_relief(m, entities) or "bend_end_site_id" in m for m in part.get("canonical_members", [])) or
                any("bend_end_site_id" in e for e in part.get("entities", []))):
            return ["BEND_END_SITE_CENSUS_MISMATCH"]
        return []
    expected, sites = part.get(keys[0]), part.get(keys[1])
    if (not isinstance(expected, list) or any(not isinstance(x, str) or not x for x in expected) or
            len(expected) != len(set(expected)) or not isinstance(sites, list) or
            any(not isinstance(s, dict) for s in sites)):
        return ["BEND_END_SITE_CENSUS_MISMATCH"]
    seen = [s.get("site_id") for s in sites]
    if any(not isinstance(x, str) for x in seen) or len(seen) != len(set(seen)) or set(seen) != set(expected):
        return ["BEND_END_SITE_CENSUS_MISMATCH"]
    edges = part.get(keys[2], {})
    if not isinstance(edges, dict):
        return ["BEND_END_EDGE_UNPROVED"]
    members = {m.get("canonical_member_id"): m for m in part.get("canonical_members", [])}
    bends = {b.get("bend_id"): b for b in part.get("face_graph", {}).get("bends", [])}
    errors = []
    for member in members.values():
        owner = member.get("bend_end_site_id")
        if (owner is not None or _automatic_relief(member, entities)) and owner not in expected:
            errors.append("BEND_END_RELIEF_SCOPE_MISSING")
    for entity in entities.values():
        if "bend_end_site_id" in entity and entity["bend_end_site_id"] not in expected:
            errors.append("BEND_END_RELIEF_SCOPE_MISSING")
    for site in sites:
        sid = site["site_id"]
        try:
            ids = site.get("relief_member_ids")
            if not isinstance(ids, list) or any(not isinstance(x, str) or x not in members for x in ids):
                raise ValueError("BEND_END_RELIEF_MEMBER_UNPROVED")
            owned_entities = {eid for eid, ent in entities.items() if ent.get("bend_end_site_id") == sid}
            linked = set(ids) | {mid for mid, m in members.items() if m.get("bend_end_site_id") == sid or owned_entities.intersection(m.get("entity_ids", []))}
            relief = [members[mid] for mid in linked]
            if any(not m.get("entity_ids") for m in relief):
                raise ValueError("BEND_END_RELIEF_MEMBER_UNPROVED")
            if site.get("status") == "FLAGGED":
                if part.get("status") == "PASS" or site.get("decision") != "FLAGGED" or relief:
                    raise ValueError("BEND_END_STEP_UNRESOLVED")
                continue
            if site.get("status") != "PROVED":
                raise ValueError("BEND_END_STEP_UNRESOLVED")
            controlled = site.get("bend_ids")
            if (not isinstance(controlled, list) or len(controlled) != 2 or
                    any(not isinstance(b, str) or b not in bends for b in controlled) or len(set(controlled)) != 2):
                raise ValueError("BEND_END_BEND_OWNERSHIP_UNPROVED")
            mechanism = site.get("mechanism")
            if mechanism in SPECIAL_RULES:
                if not _relief_members_proved(site, relief, entities):
                    raise ValueError("BEND_END_RELIEF_MEMBER_UNPROVED")
                error = _special_rule(site, part, edges, relief)
                if error:
                    raise ValueError(error)
                continue
            if mechanism != "BEND_END_OFFSET_90" or abs(_number(site.get("included_angle_deg"))-90) > TOL:
                raise ValueError("BEND_END_MECHANISM_UNPROVED")
            actual = _measured_step(site, edges)
            claimed = _number(site.get("S_mm"))
            if abs(actual-claimed) > TOL:
                raise ValueError("BEND_END_STEP_MISMATCH")
            # Source S is independently closed against the measured edges;
            # use it at exact zero to avoid pose-roundoff inventing a step.
            if claimed > 0:
                if site.get("decision") != "NO_RELIEF" or relief:
                    raise ValueError("BEND_END_RELIEF_FOR_POSITIVE_STEP")
            else:
                if site.get("decision") != "SLIT" or not relief:
                    raise ValueError("BEND_END_SLIT_REQUIRED")
                if not _relief_members_proved(site, relief, entities):
                    raise ValueError("BEND_END_RELIEF_MEMBER_UNPROVED")
                if not _slit_construction_proved(site, part, edges, relief, entities, bends):
                    raise ValueError("BEND_END_SLIT_CONSTRUCTION_UNPROVED")
        except (ValueError, TypeError) as exc:
            errors.append(f"{exc}:{sid}")
    return sorted(set(errors))
