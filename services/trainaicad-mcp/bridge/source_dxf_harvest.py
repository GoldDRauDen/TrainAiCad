"""Lossless, provenance-preserving DXF entity census for DATA_DXF sources.

This module deliberately does not infer manufacturing semantics, refit curves,
or claim physical scale from $INSUNITS. Unsupported entities remain in the
ledger and block a clean harvest status.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import Any

import ezdxf
from ezdxf.math import Matrix44, Vec3


SUPPORTED = {
    "LINE", "ARC", "CIRCLE", "LWPOLYLINE", "POLYLINE", "POINT",
    "SPLINE", "ELLIPSE", "INSERT",
}
MAX_INSERT_ARRAY_INSTANCES = 10_000


def _num(value: Any) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("DXF_NONFINITE_COORDINATE")
    return result


def _vec(value: Any) -> list[float]:
    return [_num(v) for v in value]


def _matrix(value: Matrix44) -> list[list[float]]:
    flat = [_num(v) for v in value]
    return [flat[i:i + 4] for i in range(0, 16, 4)]


def _inverse_matrix(value: Matrix44) -> list[list[float]]:
    inverse = value.copy()
    inverse.inverse()
    return _matrix(inverse)


def _point(value: Any) -> dict[str, float]:
    x, y, z = _vec(value)
    return {"x": x, "y": y, "z": z}


def _dxf(ent: Any, name: str, default: Any = None) -> Any:
    return ent.dxf.get(name, default)


def _common_geometry(ent: Any) -> dict[str, Any]:
    kind = ent.dxftype()
    d = ent.dxf
    if kind == "LINE":
        return {"start": _point(d.start), "end": _point(d.end),
                "thickness": _num(_dxf(ent, "thickness", 0.0)),
                "extrusion": _vec(_dxf(ent, "extrusion", (0, 0, 1)))}
    if kind in {"ARC", "CIRCLE"}:
        geometry = {"center": _point(d.center), "radius": _num(d.radius),
                    "thickness": _num(_dxf(ent, "thickness", 0.0)),
                    "extrusion": _vec(_dxf(ent, "extrusion", (0, 0, 1)))}
        if kind == "ARC":
            geometry.update(startAngleDeg=_num(d.start_angle), endAngleDeg=_num(d.end_angle))
        return geometry
    if kind == "LWPOLYLINE":
        points = list(ent.get_points("xyseb"))
        return {
            "closed": bool(ent.closed),
            "elevation": _num(_dxf(ent, "elevation", 0.0)),
            "constantWidth": _num(_dxf(ent, "const_width", 0.0)),
            "extrusion": _vec(_dxf(ent, "extrusion", (0, 0, 1))),
            "vertices": [{"x": _num(p[0]), "y": _num(p[1]), "startWidth": _num(p[2]),
                          "endWidth": _num(p[3]), "bulge": _num(p[4])} for p in points],
        }
    if kind == "POLYLINE":
        return {
            "flags": int(_dxf(ent, "flags", 0)),
            "closed": bool(ent.is_closed),
            "mode": "3D" if ent.is_3d_polyline else "2D",
            "elevation": _vec(_dxf(ent, "elevation", (0, 0, 0))),
            "extrusion": _vec(_dxf(ent, "extrusion", (0, 0, 1))),
            "vertices": [{
                "handle": vertex.dxf.handle,
                "location": _point(vertex.dxf.location),
                "bulge": _num(_dxf(vertex, "bulge", 0.0)),
                "startWidth": _num(_dxf(vertex, "start_width", 0.0)),
                "endWidth": _num(_dxf(vertex, "end_width", 0.0)),
                "flags": int(_dxf(vertex, "flags", 0)),
            } for vertex in ent.vertices],
        }
    if kind == "POINT":
        return {"location": _point(d.location),
                "thickness": _num(_dxf(ent, "thickness", 0.0)),
                "extrusion": _vec(_dxf(ent, "extrusion", (0, 0, 1)))}
    if kind == "SPLINE":
        return {
            "degree": int(_dxf(ent, "degree", 0)),
            "flags": int(_dxf(ent, "flags", 0)),
            "knotTolerance": _num(_dxf(ent, "knot_tolerance", 1e-7)),
            "controlPointTolerance": _num(_dxf(ent, "control_point_tolerance", 1e-7)),
            "fitTolerance": _num(_dxf(ent, "fit_tolerance", 1e-7)),
            "knots": [_num(v) for v in ent.knots],
            "weights": [_num(v) for v in ent.weights],
            "controlPoints": [_point(p) for p in ent.control_points],
            "fitPoints": [_point(p) for p in ent.fit_points],
            "startTangent": _point(_dxf(ent, "start_tangent", (0, 0, 0))),
            "endTangent": _point(_dxf(ent, "end_tangent", (0, 0, 0))),
        }
    if kind == "ELLIPSE":
        return {"center": _point(d.center), "majorAxis": _vec(d.major_axis),
                "ratio": _num(d.ratio), "startParam": _num(d.start_param),
                "endParam": _num(d.end_param),
                "extrusion": _vec(_dxf(ent, "extrusion", (0, 0, 1)))}
    if kind == "INSERT":
        return {"blockName": str(d.name), "insert": _vec(d.insert),
                "xScale": _num(_dxf(ent, "xscale", 1.0)),
                "yScale": _num(_dxf(ent, "yscale", 1.0)),
                "zScale": _num(_dxf(ent, "zscale", 1.0)),
                "rotationDeg": _num(_dxf(ent, "rotation", 0.0)),
                "rowCount": int(_dxf(ent, "row_count", 1)),
                "columnCount": int(_dxf(ent, "column_count", 1)),
                "rowSpacing": _num(_dxf(ent, "row_spacing", 0.0)),
                "columnSpacing": _num(_dxf(ent, "column_spacing", 0.0)),
                "extrusion": _vec(_dxf(ent, "extrusion", (0, 0, 1)))}
    raise ValueError(f"UNSUPPORTED_DXF_ENTITY:{kind}")


def _effective_layer(entity_layer: str, insert_layer: str | None) -> str:
    return (insert_layer or "0") if entity_layer == "0" and insert_layer else entity_layer


def _insert_array_instances(insert: Any) -> list[Any]:
    """Clone each MINSERT cell, including coincident cells with zero spacing."""
    d = insert.dxf
    rows = int(_dxf(insert, "row_count", 1))
    columns = int(_dxf(insert, "column_count", 1))
    row_spacing = _num(_dxf(insert, "row_spacing", 0.0))
    column_spacing = _num(_dxf(insert, "column_spacing", 0.0))
    rotation = _num(_dxf(insert, "rotation", 0.0))
    instances = []
    for row in range(rows):
        for column in range(columns):
            offset = Vec3(column * column_spacing, row * row_spacing)
            if rotation:
                offset = offset.rotate_deg(rotation)
            instance = insert.copy()
            instance.dxf.insert = Vec3(d.insert) + offset
            instance.dxf.discard("row_count")
            instance.dxf.discard("column_count")
            instance.dxf.discard("row_spacing")
            instance.dxf.discard("column_spacing")
            instances.append(instance)
    return instances


def harvest_data_dxf(path: str | Path) -> dict[str, Any]:
    source_path = Path(path).resolve(strict=True)
    source_bytes = source_path.read_bytes()
    source_sha = hashlib.sha256(source_bytes).hexdigest()
    doc = ezdxf.readfile(source_path)
    auditor = doc.audit()
    if auditor.has_errors:
        raise ValueError(f"DATA_DXF_AUDIT_FAILED:{len(auditor.errors)}")
    if auditor.fixes:
        raise ValueError(f"DATA_DXF_AUDIT_REPAIRS_REQUIRED:{len(auditor.fixes)}")

    entities: list[dict[str, Any]] = []
    unsupported: list[dict[str, str]] = []
    cycle_flags: list[str] = []
    identity = Matrix44()

    def visit(ent: Any, layout: str, transform: Matrix44,
              insert_chain: list[dict[str, str]], inherited_layer: str | None,
              block_stack: tuple[str, ...], depth: int) -> None:
        kind = ent.dxftype()
        handle = str(_dxf(ent, "handle", ""))
        layer = str(_dxf(ent, "layer", "0"))
        effective = _effective_layer(layer, inherited_layer)
        if kind not in SUPPORTED:
            unsupported.append({"handle": handle, "entityType": kind,
                                "layer": effective, "layout": layout})
            entities.append({
                "sequence": len(entities), "sourceHandle": handle,
                "entityType": kind, "layer": layer, "effectiveLayer": effective,
                "layout": layout, "insertChain": list(insert_chain),
                "transform4x4": _matrix(transform), "inverseTransform4x4": _inverse_matrix(transform),
                "geometry": None, "retained": False,
                "removalReason": f"UNSUPPORTED_DXF_ENTITY:{kind}",
            })
            return

        geometry = _common_geometry(ent)
        record = {
            "sequence": len(entities), "sourceHandle": handle,
            "entityType": kind, "layer": layer, "effectiveLayer": effective,
            "layout": layout, "insertChain": list(insert_chain),
            "transform4x4": _matrix(transform),
            "inverseTransform4x4": _inverse_matrix(transform),
            "geometry": geometry, "retained": True, "removalReason": None,
            "viewFaceAssignment": None,
            "canonicalization": "NONE_RAW_DXF_PARAMETERS_PRESERVED",
        }
        entities.append(record)

        if kind != "INSERT":
            return

        block_name = str(ent.dxf.name)
        chain_item = {"insertHandle": handle, "blockName": block_name}
        if block_name in block_stack:
            cycle_flags.append(f"BLOCK_INSERT_CYCLE:{':'.join((*block_stack, block_name))}")
            return
        if depth >= 32:
            cycle_flags.append(f"BLOCK_INSERT_DEPTH_LIMIT:{handle}")
            return
        block = doc.blocks.get(block_name)
        composed = transform @ ent.matrix44()
        child_chain = [*insert_chain, chain_item]
        child_inherited = effective
        instance_count = geometry["rowCount"] * geometry["columnCount"]
        if instance_count > MAX_INSERT_ARRAY_INSTANCES:
            cycle_flags.append(f"INSERT_ARRAY_EXPANSION_LIMIT:{handle}:{instance_count}")
            return
        instances = _insert_array_instances(ent) if instance_count > 1 else [ent]
        for instance_index, instance in enumerate(instances):
            instance_chain = child_chain
            if instance_count > 1:
                instance_chain = [*insert_chain, {
                    **chain_item, "arrayInstance": str(instance_index)
                }]
            instance_transform = transform @ instance.matrix44()
            for child in block:
                visit(child, layout, instance_transform, instance_chain, child_inherited,
                      (*block_stack, block_name), depth + 1)

    for layout in doc.layouts:
        for entity in layout:
            visit(entity, layout.name, identity, [], None, (), 0)

    insunits = int(doc.header.get("$INSUNITS", 0))
    declared_units = {0: "unitless", 1: "inches", 2: "feet", 4: "mm", 5: "cm", 6: "m"}.get(insunits, f"INSUNITS_{insunits}")
    flags = [f"UNSUPPORTED_DXF_ENTITY:{item['entityType']}:{item['handle']}" for item in unsupported]
    flags.extend(cycle_flags)
    if not entities:
        flags.append("DXF_NO_MODEL_GEOMETRY")
    flags.append("DXF_PHYSICAL_SCALE_UNPROVED")
    return {
        "schema": "TRAINSOURCE_GEOMETRY_LEDGER_V1",
        "sourceSha256": source_sha,
        "sourceBytes": len(source_bytes),
        "dxfVersion": str(doc.dxfversion),
        "declaredInsunits": insunits,
        "declaredUnits": declared_units,
        "scaleStatus": "UNPROVED",
        "physicalScaleProof": None,
        "entities": entities,
        "unsupportedEntities": unsupported,
        "flags": flags,
        "status": "REVIEW_REQUIRED",
        "semanticRefitApplied": False,
    }
