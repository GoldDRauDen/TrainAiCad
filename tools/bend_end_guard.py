"""Source-edge bend-end step and scoped mechanism validation before DXF save.

The reader must inventory sites and prove edge identities/directions from source.
This guard remeasures those declared witnesses; it does not discover PDF sites.
"""
from __future__ import annotations

import math

TOL = 1e-7  # Coordinate arithmetic tolerance, never a manufacturing S threshold.
AUTO_RELIEF_RULES = {"BEND_END_OFFSET_90", "OPPOSITE_FOLD_R_T", "BOXMET", "NON_90_RELIEF"}
SPECIAL_RULES = {"OPPOSITE_FOLD_R_T", "BOXMET", "CUSTOM_SOURCE_SLIT", "NON_90_RELIEF"}
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


OUTLINE_RELIEF_TOL = 1e-4  # LWPOLYLINE vertices are stored rounded to 1e-6 mm


def _arc_of_segment(p, q, bulge):
    """(centre, radius) of the polyline arc segment p->q, or None for a straight segment."""
    from geom import GeometryError, bulge_circle
    if abs(bulge) <= 1e-12 or math.dist(p, q) <= TOL:
        return None
    try:
        cx, cy, radius, _ = bulge_circle(p, q, bulge)
    except GeometryError:
        return None
    return (cx, cy), radius


def _outline_relief_proved(site, relief, entities, thickness):
    """OPPOSITE_FOLD_R_T relief hole drawn INSIDE the outer contour (ByLayer arc of radius t, no Green entity).

    The owning member declares ``outline_relief: {center, radius}`` and owns the outer LWPOLYLINE; the polyline
    must really contain an arc segment of that centre and radius, and radius == t (R = t rule).
    """
    if not relief:
        return False
    try:
        for member in relief:
            geo, ids = member.get("outline_relief"), member.get("entity_ids") or []
            if (member.get("status") != "PROVED" or member.get("origin") != "DERIVED_RULE" or
                    member.get("controlling_rule") != "OPPOSITE_FOLD_R_T" or
                    member.get("bend_end_site_id") != site["site_id"] or not isinstance(geo, dict) or len(ids) != 1):
                return False
            outer = entities.get(ids[0], {})
            if outer.get("type") != "LWPOLYLINE" or outer.get("role") != "outer":
                return False
            center, radius = _point(geo.get("center")), _number(geo.get("radius"))
            if abs(radius - thickness) > OUTLINE_RELIEF_TOL:
                return False
            verts = outer.get("vertices") or []
            arcs = (_arc_of_segment(a[:2], verts[(i + 1) % len(verts)][:2], a[2] if len(a) > 2 else 0)
                    for i, a in enumerate(verts))
            if not any(arc and math.dist(arc[0], center) <= OUTLINE_RELIEF_TOL and
                       abs(arc[1] - radius) <= OUTLINE_RELIEF_TOL for arc in arcs):
                return False
        return True
    except (ValueError, TypeError, IndexError):
        return False


def _slit_construction_proved(site, part, edges, relief, entities, bends):
    """Rebuild the existing connected slit rule from proved canonical-flat edges."""
    from slit_geometry import LeadValueUnproved, connected_slit, lead_end_by_offset, lead_val, slit_dir_from_bend
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
    except LeadValueUnproved:
        raise  # surfaced as its own FLAG code (LEAD_VALUE_UNPROVED:...), not as a generic construction mismatch
    except (ValueError, TypeError, KeyError, StopIteration):
        return False


def _check_corner_retreat(site, claimed, thickness):
    """Same-direction box corner: depth-first retreat choice (rules/SLIT_RELIEF.md section 5)."""
    from corner_retreat import retreat_violation
    witness = site["corner_retreat"]
    error = retreat_violation(witness) if isinstance(witness, dict) else "BEND_END_CORNER_RETREAT_UNPROVED"
    if error:
        raise ValueError(error)
    own = witness.get("site_flange_id")
    if own not in witness["flange_ids"]:
        raise ValueError("BEND_END_CORNER_RETREAT_UNPROVED")
    # The retreated flange end is S=-t (slit); the other flange end is S=+t (no slit).
    wanted = -thickness if own == witness["retreated_flange_id"] else thickness
    if abs(claimed-wanted) > 1e-6:
        raise ValueError("BEND_END_CORNER_RETREAT_S_MISMATCH")


def _special_rule(site, part, edges, relief):
    mechanism = site.get("mechanism")
    if not relief:
        return "BEND_END_RELIEF_MEMBER_UNPROVED"
    if not site.get("special_rule_evidence_ref") or site.get("decision") != "SEPARATE_RULE":
        return "BEND_END_SPECIAL_RULE_UNPROVED"
    if mechanism == "OPPOSITE_FOLD_R_T":
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


def _segment_distance(a, b, c, d):
    """Minimum distance between segments ab and cd (0 when they intersect)."""
    def point_seg(p, q, r):
        v = (r[0]-q[0], r[1]-q[1])
        n = v[0]*v[0]+v[1]*v[1]
        u = 0.0 if n <= 0 else max(0.0, min(1.0, ((p[0]-q[0])*v[0]+(p[1]-q[1])*v[1])/n))
        return math.dist(p, (q[0]+u*v[0], q[1]+u*v[1]))
    cross = lambda x, y: x[0]*y[1]-x[1]*y[0]
    u, v, w = (b[0]-a[0], b[1]-a[1]), (d[0]-c[0], d[1]-c[1]), (c[0]-a[0], c[1]-a[1])
    denom = cross(u, v)
    if abs(denom) > 1e-12:
        t, s = cross(w, v)/denom, cross(w, u)/denom
        if 0 <= t <= 1 and 0 <= s <= 1:
            return 0.0
    return min(point_seg(a, c, d), point_seg(b, c, d), point_seg(c, a, b), point_seg(d, a, b))


def undeclared_corner_pairs(part, entities):
    """Bend pairs that share a face, are perpendicular and whose bend zones touch (distance <= max Nobi):
    each such pair is a bend-end corner and MUST own a declared site (never discovered from the PDF here;
    this closes the census against the part's own face graph and bend geometry)."""
    bends = part.get("face_graph", {}).get("bends", [])
    lines = {}
    for bend in bends:
        segs = []
        for eid in bend.get("material_domain", {}).get("entity_ids", []):
            ent = entities.get(eid, {})
            if ent.get("type") == "LINE" and ent.get("role") == "bend":
                try:
                    segs.append((_point(ent["start"]), _point(ent["end"])))
                except (ValueError, KeyError):
                    pass
        lines[bend.get("bend_id")] = segs
    declared = {frozenset(site.get("bend_ids") or []) for site in part.get("bend_end_junctions", [])
                if isinstance(site, dict)}
    out = []
    for i, b1 in enumerate(bends):
        for b2 in bends[i+1:]:
            if not ({b1.get("face_A"), b1.get("face_B")} & {b2.get("face_A"), b2.get("face_B")}):
                continue
            s1, s2 = lines.get(b1.get("bend_id")), lines.get(b2.get("bend_id"))
            if not s1 or not s2:
                continue
            u = (s1[0][1][0]-s1[0][0][0], s1[0][1][1]-s1[0][0][1])
            v = (s2[0][1][0]-s2[0][0][0], s2[0][1][1]-s2[0][0][1])
            if math.hypot(*u) <= TOL or math.hypot(*v) <= TOL or \
                    abs(sum(u[k]*v[k] for k in range(2))) > 1e-6*math.hypot(*u)*math.hypot(*v):
                continue
            try:
                zone = max(float(b1.get("N_mm", 0)), float(b2.get("N_mm", 0))) + 1e-6
            except (TypeError, ValueError):
                continue
            if min(_segment_distance(*x, *y) for x in s1 for y in s2) <= zone and \
                    frozenset((b1.get("bend_id"), b2.get("bend_id"))) not in declared:
                out.append(f"{b1.get('bend_id')}|{b2.get('bend_id')}")
    return out


def bend_end_errors(part):
    """Check a declared source site inventory, its actual S witnesses and output owners."""
    keys = ("source_bend_end_site_ids", "bend_end_junctions", "bend_end_source_edges")
    entities = {e.get("entity_id"): e for e in part.get("entities", [])}
    if not any(key in part for key in keys):
        if (any(_automatic_relief(m, entities) or "bend_end_site_id" in m for m in part.get("canonical_members", [])) or
                any("bend_end_site_id" in e for e in part.get("entities", []))):
            return ["BEND_END_SITE_CENSUS_MISMATCH"]
        if part.get("status") == "PASS" and undeclared_corner_pairs(part, entities):
            return ["BEND_END_SITE_CENSUS_MISMATCH"]  # perpendicular touching bends but no site inventory at all
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
    errors = [f"BEND_END_CORNER_SITE_MISSING:{pair}" for pair in undeclared_corner_pairs(part, entities)]
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
                if not (_relief_members_proved(site, relief, entities) or
                        mechanism == "OPPOSITE_FOLD_R_T" and
                        _outline_relief_proved(site, relief, entities, _number(part.get("thickness_mm")))):
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
            if "corner_retreat" in site:
                _check_corner_retreat(site, claimed, _number(part.get("thickness_mm")))
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
