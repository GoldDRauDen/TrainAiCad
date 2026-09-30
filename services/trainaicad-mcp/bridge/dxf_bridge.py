#!/usr/bin/env python3
"""Thin MCP bridge around TrainAiCad's approved DXF serializer.

Commands:
  export <input_json> <output_dir>
  audit <dxf_path>
  harvest <source_dxf_path>

All JSON output is single-line on stdout. Errors are raised to stderr/nonzero.
"""
import json
import sys
from pathlib import Path

import ezdxf

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
import export_dxf  # noqa: E402
from export_dxf import export_job  # noqa: E402


def cmd_export(input_json: str, output_dir: str):
    payload = json.loads(Path(input_json).read_text(encoding="utf-8"))
    manifest = export_job(payload, Path(output_dir), mode="single", write_manifest=True)
    print(json.dumps({
        "ok": True,
        "manifest": manifest,
        "dxf_path": str((Path(output_dir) / manifest["filename"]).resolve()),
        "manifest_path": str((Path(output_dir) / f'{manifest["job_id"]}_MANIFEST.json').resolve()),
    }, ensure_ascii=False))


def source_entity_signature(source, translation):
    """Independently project one locked serializer primitive into composite space."""
    dx, dy = translation
    t = source["type"]
    color = source.get("color", 256)
    linetype = source.get("linetype", "BYLAYER")
    attrs = (t, "0", color, linetype)
    def xy(p):
        return (round(p[0] + dx, 6), round(p[1] + dy, 6))
    if t == "LWPOLYLINE":
        geometry = (bool(source.get("closed", False)), tuple(
            (round(v[0] + dx, 6), round(v[1] + dy, 6), round(v[2], 8)) for v in source["vertices"]
        ))
    elif t == "CIRCLE":
        geometry = (xy(source["center"]), round(source["radius"], 6))
    elif t == "POINT":
        geometry = xy(source["point"])
    elif t == "LINE":
        geometry = (xy(source["start"]), xy(source["end"]))
    elif t == "ARC":
        geometry = (xy(source["center"]), round(source["radius"], 6),
                    round(source["start_angle"], 6), round(source["end_angle"], 6))
    elif t == "TEXT":
        geometry = (xy(source["insert"]), source["text"], round(source.get("height", 2.5), 6))
    else:
        raise ValueError(f"PHYSICAL_READBACK_UNSUPPORTED_SOURCE_ENTITY:{t}")
    return (attrs, geometry)


def annotation_signature(text, insert, color=8, height=3.0):
    return (("TEXT", "AI_META", color, "BYLAYER"),
            ((round(insert[0], 6), round(insert[1], 6)), text, round(height, 6)))


def compare_physical_document(doc, payload, manifest):
    if manifest.get("coordinate_units") != "mm" or manifest.get("contract") != "TrainAiCad-DXF-V4.9":
        raise ValueError("PHYSICAL_READBACK_MANIFEST_CONTRACT_MISMATCH")
    parts = payload.get("parts", [])
    positions = manifest.get("positions", [])
    records = {item.get("code"): item for item in manifest.get("parts", [])}
    codes = [part.get("code") for part in parts]
    if not parts or [item.get("code") for item in positions] != codes:
        raise ValueError("PHYSICAL_READBACK_CODE_ORDER_MISMATCH")
    if len(records) != len(parts) or any(code not in records for code in codes):
        raise ValueError("PHYSICAL_READBACK_PART_RECORD_MISMATCH")

    expected = []
    expected_labels = []
    total_height = sum(records[p["code"]]["bbox_mm"][3] - records[p["code"]]["bbox_mm"][1] for p in parts)
    clearance = float(manifest.get("positions", [{}])[0].get("clearance_mm", 10.0)) if positions else 10.0
    # V4.9 manifest stores the layout gap at the composite level in its layout contract;
    # the serializer payload uses 10 mm for this production bridge.
    clearance = 10.0
    total_height += clearance * (len(parts) - 1)
    cursor = total_height
    for part, pos in zip(parts, positions):
        code = part["code"]
        record = records[code]
        xmin, ymin, xmax, ymax = record["bbox_mm"]
        height = ymax - ymin
        bottom = cursor - height
        translation = [-xmin, bottom - ymin]
        if any(abs(float(a) - float(b)) > 1e-6 for a, b in zip(pos.get("translation_mm", []), translation)):
            raise ValueError(f"PHYSICAL_READBACK_LAYOUT_TRANSFORM_MISMATCH:{code}")

        for source_entity in part["entities"]:
            expected.append(source_entity_signature(source_entity, translation))
        status_suffix = "" if part["status"] == "PASS" else " [FLAG]"
        if part["status"] == "VIEWS_ONLY":
            status_suffix = " [VIEWS_ONLY - FLAG]"
        expected_labels.append(annotation_signature(code + status_suffix, (0.0, cursor + 2)))
        if part.get("flags"):
            expected_labels.append(annotation_signature(code + " FLAG: SEE STAGE1; NO CUT",
                (max(xmax - xmin, 20), cursor + 2), color=6))
        if part["status"] == "VIEWS_ONLY":
            for view_id, bounds in record.get("source_view_boxes", {}).items():
                expected_labels.append(annotation_signature(code + " VIEW " + view_id,
                    (bounds[0] + translation[0], bounds[3] + translation[1])))
        cursor = bottom - clearance

    review = any(part.get("status") != "PASS" or part.get("flags") for part in parts)
    if review:
        expected_labels.append(annotation_signature("REVIEW ONLY - NO CUT - UNRESOLVED CODES PRESENT", (0, total_height + 12), color=6))
    expected_all = []
    # Exporter writes each code's geometry followed by that code's labels, then global warning.
    label_index = 0
    cursor = total_height
    for part in parts:
        code = part["code"]
        record = records[code]
        xmin, ymin, xmax, ymax = record["bbox_mm"]
        height = ymax - ymin
        bottom = cursor - height
        translation = [-xmin, bottom - ymin]
        expected_all.extend(source_entity_signature(entity, translation) for entity in part["entities"])
        expected_all.append(expected_labels[label_index]); label_index += 1
        if part.get("flags"):
            expected_all.append(expected_labels[label_index]); label_index += 1
        if part["status"] == "VIEWS_ONLY":
            view_count = len(record.get("source_view_boxes", {}))
            expected_all.extend(expected_labels[label_index:label_index + view_count])
            label_index += view_count
        cursor = bottom - clearance
    if review:
        expected_all.append(expected_labels[-1])

    actual = [export_dxf.entity_signature(entity) for entity in doc.modelspace()]
    if actual != expected_all:
        mismatch = next((i for i, pair in enumerate(zip(actual, expected_all)) if pair[0] != pair[1]), min(len(actual), len(expected_all)))
        raise ValueError(f"PHYSICAL_READBACK_GEOMETRY_MISMATCH:entity_{mismatch}:expected_{len(expected_all)}:actual_{len(actual)}")
    labels = [entity.dxf.text for entity in doc.modelspace() if entity.dxf.layer == "AI_META" and entity.dxftype() == "TEXT"]
    if labels != [sig[1][1] for sig in expected_labels]:
        raise ValueError("PHYSICAL_READBACK_LABEL_ORDER_MISMATCH")
    if "AI_META" not in doc.layers or int(doc.layers.get("AI_META").dxf.get("plot", 1)) != 0:
        raise ValueError("PHYSICAL_READBACK_AI_META_LAYER_INVALID")
    return {"physical_geometry_match": True, "compared_entity_count": len(actual),
            "code_order_match": True, "labels": labels}


def cmd_audit(dxf_path: str, expected_json: str, manifest_json: str):
    path = Path(dxf_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(path)

    doc = ezdxf.readfile(path)
    auditor = doc.audit()
    if auditor.has_errors:
        raise ValueError(f"DXF_READBACK_AUDIT_FAILED:{path.name}")
    expected = json.loads(Path(expected_json).read_text(encoding="utf-8"))
    manifest = json.loads(Path(manifest_json).read_text(encoding="utf-8"))
    physical = compare_physical_document(doc, expected, manifest)
    msp = list(doc.modelspace())
    layers = {}
    labels = []
    by_type = {}
    for ent in msp:
        by_type[ent.dxftype()] = by_type.get(ent.dxftype(), 0) + 1
        layer = ent.dxf.layer
        layers[layer] = layers.get(layer, 0) + 1
        if layer == "AI_META" and ent.dxftype() == "TEXT":
            labels.append(ent.dxf.text)

    ai_meta_plot = None
    if "AI_META" in doc.layers:
        ai_meta_plot = int(doc.layers.get("AI_META").dxf.get("plot", 1))

    print(json.dumps({
        "ok": not auditor.has_errors,
        "audit_error_count": len(auditor.errors),
        "audit_fix_count": len(auditor.fixes),
        "insunits": int(doc.header.get("$INSUNITS", 0)),
        "entity_count": len(msp),
        "layers": layers,
        "entity_types": by_type,
        "labels": labels,
        "ai_meta_plot": ai_meta_plot,
        **physical,
        "path": str(path),
    }, ensure_ascii=False))


def cmd_harvest(source_dxf_path: str):
    from source_dxf_harvest import harvest_data_dxf

    print(json.dumps(harvest_data_dxf(source_dxf_path), ensure_ascii=False,
                     separators=(",", ":")))


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: dxf_bridge.py export <json> <outdir> | audit <dxf>")
    cmd = sys.argv[1]
    if cmd == "export" and len(sys.argv) == 4:
        cmd_export(sys.argv[2], sys.argv[3])
    elif cmd == "audit" and len(sys.argv) == 3:
        raise SystemExit("audit requires: dxf_path serializer_input.json manifest.json")
    elif cmd == "audit" and len(sys.argv) == 5:
        cmd_audit(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == "harvest" and len(sys.argv) == 3:
        cmd_harvest(sys.argv[2])
    else:
        raise SystemExit("invalid command/arguments")


if __name__ == "__main__":
    main()
