#!/usr/bin/env python3
"""Thin MCP bridge around TrainAiCad's approved DXF serializer.

Commands:
  export <input_json> <output_dir>
  audit <dxf_path>

All JSON output is single-line on stdout. Errors are raised to stderr/nonzero.
"""
import os
import json
import sys
from pathlib import Path

import ezdxf

ROOT = Path(os.environ.get("TRAINAICAD_RULE_SNAPSHOT", Path(__file__).resolve().parents[3])).resolve()
sys.path.insert(0, str(ROOT / "tools"))
import export_dxf as exporter  # noqa: E402


def mcp_validate_job(job):
    """MCP-only review validation.

    Production PASS remains strict. Reviewable uncertainty is serialized as a
    flagged PREVIEW inside the one composite REVIEW_ONLY DXF instead of forcing
    the chat to stop and ask the user. Structural/geometry validity still fails
    closed here and in the base serializer.
    """
    jid = exporter.safe_name(job.get("job_id"))
    parts = job.get("parts")
    if not isinstance(parts, list) or not parts:
        exporter.fail("Job must contain a nonempty ordered parts list")
    codes = set()
    for part in parts:
        code = exporter.safe_name(part.get("code"))
        if code in codes:
            exporter.fail(f"Duplicate code {code}; use unique code for each manufacturing part")
        codes.add(code)
        if not isinstance(part.get("material"), str) or not part["material"].strip():
            exporter.fail(f"{code}: material required")
        if exporter.number(part.get("thickness_mm"), f"{code} thickness") <= 0:
            exporter.fail(f"{code}: thickness must be positive")

        state = part.get("status")
        if state not in ("PASS", "PREVIEW", "VIEWS_ONLY"):
            exporter.fail(f"{code}: status must be PASS, PREVIEW or VIEWS_ONLY")
        checks = part.get("checks")
        permitted = ("PASS", "N/A") if state == "PASS" else ("PASS", "N/A", "FLAGGED")
        if not isinstance(checks, dict) or any(checks.get(key) not in permitted for key in exporter.CHECKS):
            exporter.fail(f"{code}: invalid upstream semantic checks for {state}")
        if state == "PASS" and (
            part.get("flags") or
            any(checks[k] != "PASS" for k in ("contour_topology", "datum", "feature_count", "containment", "material_rules"))
        ):
            exporter.fail(f"{code}: production PASS requires no flags and applicable critical checks")
        if state == "PREVIEW":
            if not part.get("flags"):
                exporter.fail(f"{code}: PREVIEW requires at least one review flag")
            reason = part.get("preview_reason")
            if reason not in ("numeric_only_known_topology", "review_flag_known_geometry"):
                exporter.fail(f"{code}: unsupported PREVIEW reason {reason}")
        if state == "VIEWS_ONLY" and (
            not part.get("flags") or part.get("preview_reason") != "separate_source_views"
        ):
            exporter.fail(f"{code}: VIEWS_ONLY requires independently proved source views, reason and unresolved flags")

        ents = part.get("entities")
        if not isinstance(ents, list) or not ents:
            exporter.fail(f"{code}: entities required")
        for ent in ents:
            exporter.validate_entity(ent, code, state != "PASS")
            if state == "VIEWS_ONLY" and ent["type"] != "TEXT":
                exporter.safe_name(ent.get("view_id"))
        if state != "VIEWS_ONLY" and sum(ent.get("role") == "outer" for ent in ents) != 1:
            exporter.fail(f"{code}: exactly one closed outside contour required")
        if state == "VIEWS_ONLY" and not any(ent["type"] != "TEXT" for ent in ents):
            exporter.fail(f"{code}: no proved source-view geometry")

        # Numeric-only preview keeps the repo's magenta-estimate convention.
        # Server-generated review flags preserve known geometry unchanged; the
        # composite is globally marked REVIEW ONLY - NO CUT in AI_META.
        if state == "PREVIEW" and part.get("preview_reason") == "numeric_only_known_topology":
            if not (any(e.get("color") == 6 for e in ents) and any(e.get("type") == "TEXT" for e in ents)):
                exporter.fail(f"{code}: numeric preview requires Magenta geometry AND adjacent Magenta TEXT")
    return jid


# export_single_job resolves validate_job from the module global at runtime.
# Keep the approved serializer/layout/read-back implementation, only relax the
# MCP review policy so semantic uncertainty becomes a no-cut flagged artifact.
exporter.validate_job = mcp_validate_job


def cmd_export(input_json: str, output_dir: str):
    payload = json.loads(Path(input_json).read_text(encoding="utf-8"))
    manifest = exporter.export_job(payload, Path(output_dir), mode="single", write_manifest=True)
    print(json.dumps({
        "ok": True,
        "manifest": manifest,
        "dxf_path": str((Path(output_dir) / manifest["filename"]).resolve()),
        "manifest_path": str((Path(output_dir) / f'{manifest["job_id"]}_MANIFEST.json').resolve()),
    }, ensure_ascii=False))


def cmd_audit(dxf_path: str):
    path = Path(dxf_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(path)

    doc = ezdxf.readfile(path)
    auditor = doc.audit()
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
        "path": str(path),
    }, ensure_ascii=False))


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: dxf_bridge.py export <json> <outdir> | audit <dxf>")
    cmd = sys.argv[1]
    if cmd == "export" and len(sys.argv) == 4:
        cmd_export(sys.argv[2], sys.argv[3])
    elif cmd == "audit" and len(sys.argv) == 3:
        cmd_audit(sys.argv[2])
    else:
        raise SystemExit("invalid command/arguments")


if __name__ == "__main__":
    main()
