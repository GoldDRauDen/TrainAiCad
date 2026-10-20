"""Deterministic helpers for work that needs no judgement: unfold arithmetic, part bookkeeping, a drawing of a part.

The model still reads the drawing and decides every geometric fact (which dimension, which Nobi, which face, which
evidence). These functions only compute from those decisions, so the model neither re-types the same arithmetic nor
hand-writes the ledgers that the repository's gates derive from the geometry. Nothing here knows the repository's
rules: a builder that decided PASS, a Nobi or an endpoint on its own would be a second, unreviewed interpreter, so
status, checks and every endpoint claim must be stated by the caller, and anything left out is an error.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from pathlib import Path

DECIMALS = 2
CHECK_NAMES = ("contour_topology", "datum", "feature_count", "unfold", "containment", "bend_domain",
               "material_rules", "slot_semantics")
STATUSES = ("PASS", "PREVIEW", "VIEWS_ONLY", "REVIEW")
PART_REF = re.compile(r"PART-[0-9a-f]{10}")


class BuilderError(ValueError):
    """The caller's input is incomplete or inconsistent; the message names what to state."""


def _num(value, name, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise BuilderError(f"{name} must be a finite number")
    if positive and value <= 0:
        raise BuilderError(f"{name} must be greater than 0")
    return float(value)


def _r(value):
    return round(value, DECIMALS)


# ---------------------------------------------------------------------------------------------------------------
# unfold arithmetic
# ---------------------------------------------------------------------------------------------------------------

def unfold_calc(args):
    """Flat length, bend line pairs and ledger numbers from the OD chain the caller read.

    segments: ordered faces along the unfold axis. Each is {"od_mm": x} or {"id_mm": x, "t_count": k}, where k
    (0, 1 or 2) is how many sheet thicknesses the caller decided the printed dimension lacks (a decision the drawing
    owns, so it has no default). Nobi: "nobi_mm" for every bend or "nobi_each_mm" for one value per bend.
    Optional "place": [{"name", "from": "start"|"end"|"center", "offset": mm}] returns flat-pattern coordinates,
    and "expect_flat_mm" reports whether the flat length matches a number the caller already holds.
    """
    segments = args.get("segments")
    if not isinstance(segments, list) or not segments:
        raise BuilderError("segments must be a non-empty list")
    thickness = args.get("thickness_mm")
    ods = []
    for index, segment in enumerate(segments, 1):
        if not isinstance(segment, dict):
            raise BuilderError(f"segments[{index}] must be an object")
        if "od_mm" in segment:
            ods.append(_num(segment["od_mm"], f"segments[{index}].od_mm", positive=True))
        else:
            count = segment.get("t_count")
            if "id_mm" not in segment or count not in (0, 1, 2) or isinstance(count, bool):
                raise BuilderError(f"segments[{index}] needs od_mm, or id_mm with t_count 0, 1 or 2 (your reading)")
            if count and thickness is None:
                raise BuilderError("thickness_mm is required when a segment adds sheet thickness")
            ods.append(_r(_num(segment["id_mm"], f"segments[{index}].id_mm", positive=True)
                          + count * (_num(thickness, "thickness_mm", positive=True) if count else 0)))
    bends = len(ods) - 1
    if "nobi_each_mm" in args:
        nobi = args["nobi_each_mm"]
        if not isinstance(nobi, list) or len(nobi) != bends:
            raise BuilderError(f"nobi_each_mm needs {bends} value(s), one per bend")
        nobi = [_num(n, "nobi_each_mm", positive=True) for n in nobi]
    elif bends:
        nobi = [_num(args.get("nobi_mm"), "nobi_mm", positive=True)] * bends
    else:
        nobi = []
    flat = _r(sum(ods) - sum(nobi))
    pairs, ledger = [], []
    for k in range(1, bends + 1):
        total = sum(ods[:k])
        line1 = _r(total - sum(nobi[:k]))
        line2 = _r(total - sum(nobi[:k - 1]))
        pairs.append([line1, line2])
        ledger.append({"bend_index": k, "bend_pair_mm": [line1, line2], "nobi_mm": nobi[k - 1], "flat_mm": flat,
                       "od_actual_mm": [line2, _r(flat - line2 + nobi[k - 1])]})
    result = {"od_mm": ods, "nobi_mm": nobi, "flat_mm": flat, "bend_pairs_mm": pairs, "ledger": ledger,
              "flat_equation": {"ordered_od_mm": ods, "deductions_mm": nobi, "result_mm": flat}}
    expected = args.get("expect_flat_mm")
    if expected is not None:
        result["expected_flat_mm"] = _num(expected, "expect_flat_mm")
        result["matches_expected"] = abs(flat - result["expected_flat_mm"]) < 0.0051
    places = args.get("place")
    if places:
        coordinates = {}
        for item in places:
            origin = {"start": 0.0, "end": flat, "center": flat / 2}.get(item.get("from"))
            if origin is None or not isinstance(item.get("name"), str):
                raise BuilderError("place entries need name and from start|end|center")
            offset = _num(item.get("offset", 0), "place.offset")
            coordinates[item["name"]] = _r(origin + offset if item["from"] != "end" else origin - offset)
        result["places_mm"] = coordinates
    return result


# ---------------------------------------------------------------------------------------------------------------
# part bookkeeping from a sketch
# ---------------------------------------------------------------------------------------------------------------

def _outer_vertices(outer):
    if "vertices" in outer:
        return [list(v) for v in outer["vertices"]]
    rect = outer.get("rect")
    if not (isinstance(rect, list) and len(rect) == 2):
        raise BuilderError("outer needs vertices [[x,y,bulge]...] or rect [length, width]")
    length, width = _num(rect[0], "rect[0]", positive=True), _num(rect[1], "rect[1]", positive=True)
    radius = outer.get("corner_r")
    if not radius:
        return [[0, 0, 0], [length, 0, 0], [length, width, 0], [0, width, 0]]
    radius = _num(radius, "corner_r", positive=True)
    bulge = math.tan(math.radians(90) / 4)
    return [[radius, 0, 0.0], [length - radius, 0, bulge], [length, radius, 0.0], [length, width - radius, bulge],
            [length - radius, width, 0.0], [radius, width, bulge], [0, width - radius, 0.0], [0, radius, bulge]]


def _require(mapping, key, where):
    if key not in mapping or mapping[key] in (None, ""):
        raise BuilderError(f"{where} must state {key}")
    return mapping[key]


def _witness_chain(base, axis, steps, page, nodes, edges):
    previous = f"{base}_{axis}_D"
    nodes[previous] = "OUTER_EDGE"
    if not isinstance(steps, list) or not steps:
        raise BuilderError(f"{base}: witness {axis} needs at least one step")
    for index, step in enumerate(steps):
        where = f"{base} witness {axis}[{index}]"
        value = _num(_require(step, "value_mm", where), where + ".value_mm")
        target_type = _require(step, "to_type", where)
        evidence = _require(step, "evidence", where)
        if type(step.get("endpoint_verified")) is not bool:
            raise BuilderError(f"{where} must state endpoint_verified true or false (true only when the endpoint is "
                               "visible in the source)")
        node = f"{base}_{axis}_{index}"
        nodes[node] = target_type
        edges.append({"from_node": previous, "to_node": node, "axis": axis, "kind": step.get("kind", "CHAIN"),
                      "value_mm": value,
                      "proof": {"pdf_page": step.get("pdf_page", page), "evidence_ref": evidence,
                                "endpoint_verified": step["endpoint_verified"], "from_type": nodes[previous],
                                "to_type": target_type, "physical_witness": step.get("physical_witness", evidence)}})
        previous = node
    return previous


def build_part(sketch):
    """A complete canonical part from a compact sketch; see tools.TOOL_DESCRIPTION for the sketch's shape."""
    if not isinstance(sketch, dict):
        raise BuilderError("sketch must be an object")
    code = _require(sketch, "code", "sketch")
    status = _require(sketch, "status", "sketch")
    if status not in STATUSES:
        raise BuilderError(f"status must be one of {', '.join(STATUSES)}; the host never chooses it for you")
    checks = _require(sketch, "checks", "sketch")
    if not isinstance(checks, dict) or set(checks) != set(CHECK_NAMES):
        raise BuilderError("checks must hold exactly: " + ", ".join(CHECK_NAMES))
    _num(_require(sketch, "thickness_mm", "sketch"), "thickness_mm", positive=True)
    prefix = sketch.get("id_prefix") or "P" + re.sub(r"[^A-Za-z0-9]", "", str(code))[-8:]
    page = sketch.get("source_pdf_page", 1)
    outer_id = f"{prefix}_OUTER"
    entities, groups, members = [], [], []

    def group(group_id, family, quantity, evidence, member_ids, entity_lists, member_status="PROVED"):
        groups.append({"group_id": f"{prefix}_G_{group_id}", "family": family, "status": member_status,
                       "source_quantity": quantity, "evidence": evidence,
                       "members": [{"member_id": f"{prefix}_M_{m}", "status": member_status} for m in member_ids]})
        for member, ids in zip(member_ids, entity_lists):
            members.append({"canonical_member_id": f"{prefix}_CM_{member}", "origin": "SOURCE",
                            "source_member_id": f"{prefix}_M_{member}", "group_id": f"{prefix}_G_{group_id}",
                            "status": member_status, "entity_ids": ids})

    outer = sketch.get("outer")
    if outer:
        entities.append({"entity_id": outer_id, "type": "LWPOLYLINE", "role": "outer",
                         "vertices": _outer_vertices(outer), "closed": True})
        group("OUTER", "OUTER", 1, outer.get("evidence", "closed outer profile of the blank"), ["OUTER"], [[outer_id]])
    for extra in sketch.get("extra_groups") or []:
        # corners, chamfers and the like: the caller names the group and which entities each member owns
        _require(extra, "members", "extra_groups[]")
        group(_require(extra, "group_id", "extra_groups[]"), _require(extra, "family", "extra_groups[]"),
              extra.get("quantity", len(extra["members"])), _require(extra, "evidence", "extra_groups[]"),
              [m["id"] for m in extra["members"]],
              [[outer_id if e == "OUTER" else f"{prefix}_{e}" for e in m.get("entities", ["OUTER"])]
               for m in extra["members"]], extra.get("status", "PROVED"))

    # bends
    flat = None
    bends_in = sketch.get("bends") or []
    ledger, face_bends, bend_lines = [], [], []
    if bends_in:
        flat = unfold_calc({"segments": sketch.get("segments"), "thickness_mm": sketch.get("thickness_mm"),
                            **({"nobi_each_mm": sketch["nobi_each_mm"]} if "nobi_each_mm" in sketch
                               else {"nobi_mm": sketch.get("nobi_mm")})})
        if len(bends_in) != len(flat["bend_pairs_mm"]):
            raise BuilderError(f"bends has {len(bends_in)} item(s) but segments imply {len(flat['bend_pairs_mm'])}")
        axis = sketch.get("bend_axis", "Y")
        span = sketch.get("bend_span")
        if not (isinstance(span, list) and len(span) == 2):
            raise BuilderError("bend_span [low, high] along the bend lines is required")
        for number, (bend, (line1, line2)) in enumerate(zip(bends_in, flat["bend_pairs_mm"]), 1):
            lines = []
            for which, position in ((1, line1), (2, line2)):
                entity_id = f"{prefix}_B{number}_LINE{which}"
                lines.append(entity_id)
                start, end = ([position, span[0]], [position, span[1]]) if axis == "Y" else \
                    ([span[0], position], [span[1], position])
                entities.append({"entity_id": entity_id, "type": "LINE", "role": "bend", "start": start, "end": end,
                                 "linetype": "DASHED"})
            group(f"B{number}", "BEND", 1, _require(bend, "evidence", f"bends[{number}]"), [f"B{number}"], [lines])
            bend_lines.append(lines)
            face_a, face_b = _require(bend, "faces", f"bends[{number}]")
            edge_a, edge_b = _require(bend, "shared_edges", f"bends[{number}]")
            nobi = flat["nobi_mm"][number - 1]
            face_bends.append({
                "bend_id": f"{prefix}_B{number}", "source_member_ids": [f"{prefix}_M_B{number}"],
                "face_A": face_a, "face_B": face_b, "face_A_shared_edge": edge_a, "face_B_shared_edge": edge_b,
                "face_A_free_edges": bend.get("free_edges", [[], []])[0],
                "face_B_free_edges": bend.get("free_edges", [[], []])[1],
                "edge_orientation": _require(bend, "edge_orientation", f"bends[{number}]"),
                "attachment_source_evidence": _require(bend, "attachment_evidence", f"bends[{number}]"),
                "signed_angle_deg": _num(_require(bend, "signed_angle_deg", f"bends[{number}]"), "signed_angle_deg"),
                "rotation_axis_formed": _require(bend, "rotation_axis", f"bends[{number}]"),
                "material_domain": {"entity_ids": lines, "axis": "X" if axis == "Y" else "Y",
                                    "span_mm": [float(span[0]), float(span[1])],
                                    "edge_length_mm": _r(float(span[1]) - float(span[0])),
                                    "evidence_ref": bend.get("domain_evidence", bend["evidence"])},
                "N_mm": nobi, "thickness_mm": sketch["thickness_mm"]})
            ledger.append({
                "bend_id": f"{prefix}_B{number}", "source_group_id": f"{prefix}_G_B{number}",
                "ordered_faces": [face_a, face_b], "od_actual_mm": flat["ledger"][number - 1]["od_actual_mm"],
                "nobi_mm": nobi, "flat_mm": flat["flat_mm"], "bend_pair_mm": [line1, line2],
                "source_pdf_page": page, "evidence_ref": bend.get("ledger_evidence", bend["evidence"]),
                "thickness_single_use": bend.get("thickness_single_use", sketch.get("thickness_single_use", "")),
                "source_attachment_identity": f"{face_a}.{edge_a.split('.')[-1]} <-> {face_b}.{edge_b.split('.')[-1]}"})

    # features: circles or raw entities, with their witness chains
    nodes, edges, targets, witnessed = {}, [], [], []
    by_group = {}
    for feature in sketch.get("features") or []:
        fid = _require(feature, "id", "features[]")
        where = f"feature {fid}"
        if feature.get("kind", "circle") == "circle":
            center = _require(feature, "center", where)
            radius = _num(_require(feature, "radius", where), where + ".radius", positive=True)
            ids = [f"{prefix}_{fid}"]
            entities.append({"entity_id": ids[0], "type": "CIRCLE", "role": feature.get("role", "hole"),
                             "center": [float(center[0]), float(center[1])], "radius": radius})
        else:
            raw = _require(feature, "entities", where)
            ids = []
            for index, entity in enumerate(raw, 1):
                entity = dict(entity)
                entity.setdefault("entity_id", f"{prefix}_{fid}_{index}")
                ids.append(entity["entity_id"])
                entities.append(entity)
            center = feature.get("center")
        by_group.setdefault(feature.get("group", fid), []).append((fid, feature, ids))
        witness = feature.get("witness")
        if witness:
            base = f"{prefix}_M_{fid}"
            if center is None:
                raise BuilderError(f"{where} needs center to be witnessed")
            for axis, coordinate in (("X", center[0]), ("Y", center[1])):
                end = _witness_chain(base, axis, witness.get(axis), page, nodes, edges)
                targets.append({"feature_id": base, "datum_node": f"{base}_{axis}_D", "feature_node": end,
                                "axis": axis, "coordinate_mm": float(coordinate), "datum_coordinate_mm": 0.0,
                                "datum_entity_id": outer_id, "entity_id": ids[0]})
            if feature.get("family", "HOLE") in ("HOLE", "SLOT"):
                witnessed.append(base)
    for group_id, items in by_group.items():
        first = items[0][1]
        group(group_id, first.get("family", "HOLE"), first.get("quantity", len(items)),
              _require(first, "evidence", f"group {group_id}"), [i[0] for i in items], [i[2] for i in items],
              first.get("status", "PROVED"))

    part = {
        "code": code, "material": _require(sketch, "material", "sketch"),
        "thickness_mm": _num(_require(sketch, "thickness_mm", "sketch"), "thickness_mm", positive=True),
        "status": status, "checks": dict(checks), "flags": list(sketch.get("flags") or []),
        "entities": entities, "source_groups": groups, "canonical_members": members,
        "witness_required_feature_ids": witnessed,
        "feature_witness_graph": {"nodes": nodes, "edges": edges, "targets": targets},
        "source_physical_member_count": len(members), "proved_source_member_count":
            sum(1 for m in members if m["status"] == "PROVED"),
        "unclassified_source_member_count": sketch.get("unclassified_source_member_count", 0),
    }
    if bends_in:
        part["face_graph"] = {"faces": _require(sketch, "faces", "sketch"), "bends": face_bends}
        part["per_bend_witness_ledger"] = ledger
        part["flat_equations"] = {"X": flat["flat_equation"],
                                  **({"Y": {"ordered_od_mm": [float(sketch["strip_width_mm"])], "deductions_mm": [],
                                            "result_mm": float(sketch["strip_width_mm"])}}
                                     if sketch.get("strip_width_mm") else {})}
    # Anything else the part contract allows (dx_label, notes, callouts, weld census ...): the caller's own words.
    clash = set(sketch.get("part_fields") or {}) & {"code", "entities", "source_groups", "canonical_members", "checks",
                                                    "status"}
    if clash:
        raise BuilderError("part_fields cannot replace builder-owned keys: " + ", ".join(sorted(clash)))
    part.update(copy.deepcopy(sketch.get("part_fields") or {}))
    return part


# ---------------------------------------------------------------------------------------------------------------
# staged parts: durable on disk so a resumed run still finds what a tool built
# ---------------------------------------------------------------------------------------------------------------

def stage_part(directory, part):
    text = json.dumps(part, sort_keys=True, ensure_ascii=False)
    ref = "PART-" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:10]
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{ref}.json"
    if not target.exists():
        temporary = target.with_suffix(".tmp")
        temporary.write_text(text, encoding="utf-8")
        temporary.replace(target)
    return ref


def load_part(directory, ref):
    if not isinstance(ref, str) or not PART_REF.fullmatch(ref):
        raise BuilderError("part_ref must be a reference returned by build_part or a generator")
    target = Path(directory) / f"{ref}.json"
    if not target.is_file():
        raise BuilderError(f"Unknown part_ref {ref}; build the part again in this attempt")
    return json.loads(target.read_text(encoding="utf-8"))


def resolve_part(directory, value):
    """A part given inline or as {"part_ref": ...}."""
    if isinstance(value, dict) and set(value) == {"part_ref"}:
        return load_part(directory, value["part_ref"])
    return value


def summarize_part(part):
    return {"code": part.get("code"), "status": part.get("status"), "entities": len(part.get("entities", [])),
            "source_groups": len(part.get("source_groups", [])),
            "canonical_members": len(part.get("canonical_members", [])),
            "witness_edges": len((part.get("feature_witness_graph") or {}).get("edges", [])),
            "ledger": len(part.get("per_bend_witness_ledger") or [])}


# ---------------------------------------------------------------------------------------------------------------
# a drawing of a part
# ---------------------------------------------------------------------------------------------------------------

_COLORS = {1: (210, 30, 30), 3: (20, 150, 60), 6: (190, 40, 190), 256: (20, 20, 20)}


def _bulge_points(p1, p2, bulge, steps=24):
    if not bulge:
        return [p1, p2]
    theta = 4 * math.atan(bulge)
    chord = math.dist(p1, p2)
    if chord == 0:
        return [p1, p2]
    radius = chord / (2 * math.sin(theta / 2))
    mid = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
    offset = radius * math.cos(theta / 2)
    nx, ny = -(p2[1] - p1[1]) / chord, (p2[0] - p1[0]) / chord
    centre = (mid[0] + nx * offset, mid[1] + ny * offset)
    start = math.atan2(p1[1] - centre[1], p1[0] - centre[0])
    return [(centre[0] + abs(radius) * math.cos(start + theta * i / steps),
             centre[1] + abs(radius) * math.sin(start + theta * i / steps)) for i in range(steps + 1)]


def _strokes(entity):
    kind = entity.get("type")
    if kind == "LINE":
        return [[tuple(entity["start"]), tuple(entity["end"])]]
    if kind == "CIRCLE":
        cx, cy = entity["center"]
        r = entity["radius"]
        return [[(cx + r * math.cos(a * math.pi / 32), cy + r * math.sin(a * math.pi / 32)) for a in range(65)]]
    if kind == "ARC":
        cx, cy = entity["center"]
        r = entity["radius"]
        a0, a1 = math.radians(entity["start_angle"]), math.radians(entity["end_angle"])
        if a1 <= a0:
            a1 += 2 * math.pi
        return [[(cx + r * math.cos(a0 + (a1 - a0) * i / 32), cy + r * math.sin(a0 + (a1 - a0) * i / 32))
                 for i in range(33)]]
    if kind == "LWPOLYLINE":
        vertices = entity["vertices"]
        count = len(vertices) if entity.get("closed") else len(vertices) - 1
        points = []
        for i in range(count):
            a, b = vertices[i], vertices[(i + 1) % len(vertices)]
            points.extend(_bulge_points((a[0], a[1]), (b[0], b[1]), a[2] if len(a) > 2 else 0)[:-1])
        if not entity.get("closed") and vertices:
            points.append((vertices[-1][0], vertices[-1][1]))
        elif points:
            points.append(points[0])
        return [points]
    if kind == "POINT":
        x, y = entity["point"]
        return [[(x - .5, y), (x + .5, y)], [(x, y - .5), (x, y + .5)]]
    return []


def render_part_png(part, destination, *, size=1100, margin=40):
    """Draw every geometric entity of a part (colours as in the DXF, DASHED bend lines dashed) to a PNG."""
    from PIL import Image, ImageDraw

    drawn = [(e, _strokes(e)) for e in part.get("entities", []) if isinstance(e, dict)]
    points = [p for _, strokes in drawn for stroke in strokes for p in stroke]
    if not points:
        raise BuilderError("The part has no drawable entity")
    x0, x1 = min(p[0] for p in points), max(p[0] for p in points)
    y0, y1 = min(p[1] for p in points), max(p[1] for p in points)
    scale = (size - 2 * margin) / max(x1 - x0, y1 - y0, 1e-6)
    width, height = int((x1 - x0) * scale) + 2 * margin, int((y1 - y0) * scale) + 2 * margin

    def pixel(p):
        return (margin + (p[0] - x0) * scale, height - margin - (p[1] - y0) * scale)

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    for entity, strokes in drawn:
        colour = _COLORS.get(entity.get("color", 256), _COLORS[256])
        if entity.get("role") == "kegaki":
            colour = _COLORS[1]
        dashed = entity.get("linetype") == "DASHED"
        for stroke in strokes:
            pixels = [pixel(p) for p in stroke]
            if not dashed:
                draw.line(pixels, fill=colour, width=2)
                continue
            for a, b in zip(pixels, pixels[1:]):
                length = math.dist(a, b)
                steps = max(int(length // 8), 1)
                for i in range(0, steps, 2):
                    s, t = i / steps, min((i + 1) / steps, 1)
                    draw.line([(a[0] + (b[0] - a[0]) * s, a[1] + (b[1] - a[1]) * s),
                               (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)], fill=colour, width=2)
    draw.text((8, 6), f"{part.get('code')} {part.get('status')}  x {x0:.2f}..{x1:.2f}  y {y0:.2f}..{y1:.2f} mm",
              fill=(0, 0, 0))
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination)
    return {"image": str(destination), "bbox_mm": [_r(x0), _r(y0), _r(x1), _r(y1)], "entities": len(drawn)}
