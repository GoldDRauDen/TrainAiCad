#!/usr/bin/env python3
"""V4.31 normal production entrypoint: canonical completeness -> DXF -> XDATA read-back."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import ezdxf

from canonical_contract import CONTRACT, CanonicalContractError, validate_canonical_job
from export_dxf import entity_signature, export_job
from export_job_artifacts import export_part_artifacts, _arc_from_bulge
from holistic_engineering_guard import canonical_job_anomalies

APPID = "TRAINAICAD"


def fail(message: str) -> None:
    raise CanonicalContractError(message)


def _owner_map(job: dict) -> dict[str, list[str]]:
    owners: dict[str, list[str]] = {}
    for part in job["parts"]:
        for member in part["canonical_members"]:
            cid = member["canonical_member_id"]
            for eid in member.get("entity_ids", []):
                owners.setdefault(eid, []).append(cid)
    return owners


def _expand_polyline(doc, ent, source_id: str, member_ids: list[str]) -> list[str]:
    """Replace a source composite polyline by exact individual LINE/ARC.

    Unlike the PASS-only CUT path, composite may contain OPEN KEGAKI/source
    views or Magenta source previews: preserve physical geometry and styles.
    """
    vertices = [list(row) for row in ent.get_points("xyb")]
    closed = bool(ent.closed)
    count = len(vertices) if closed else len(vertices) - 1
    if count < 1:
        fail(f"{source_id}: source polyline has no physical segment")
    attrs = {"layer": "0"}
    for key in ("color", "linetype"):
        if ent.dxf.hasattr(key):
            attrs[key] = ent.dxf.get(key)
    msp = doc.modelspace()
    result = []
    for i in range(count):
        p, q = vertices[i], vertices[(i + 1) % len(vertices)]
        if math.hypot(p[0] - q[0], p[1] - q[1]) <= 1e-12:
            fail(f"{source_id}: degenerate physical source segment")
        if abs(p[2]) <= 1e-14:
            obj = msp.add_line(p[:2], q[:2], dxfattribs=attrs)
        else:
            center, radius, sa, ea = _arc_from_bulge(p, q, p[2])
            obj = msp.add_arc(center, radius, sa, ea, dxfattribs=attrs)
        eid = f"{source_id}:S{i + 1:04d}"
        obj.set_xdata(APPID, [
            (1000, f"ENTITY_ID={eid}"),
            (1000, f"SOURCE_ENTITY_ID={source_id}"),
            (1000, "CANONICAL_MEMBER_IDS=" + ",".join(member_ids)),
        ])
        result.append(eid)
    msp.delete_entity(ent)
    return result


def _stamp_and_verify(job: dict, manifest: dict, output_dir: Path, validation: dict) -> dict:
    target = output_dir / manifest["filename"]
    doc = ezdxf.readfile(target)
    if APPID not in doc.appids:
        doc.appids.new(APPID)
    geometry = [e for e in doc.modelspace() if e.dxf.layer == "0"]
    source_ids = validation["entity_ids"]
    if len(geometry) != len(source_ids):
        fail(f"CANONICAL_SERIALIZATION_COMPLETENESS_FAIL expected={len(source_ids)} saved={len(geometry)}")
    source_entities = {e["entity_id"]: e for part in job["parts"] for e in part["entities"]}
    if len(source_entities) != len(source_ids):
        fail("CANONICAL_SERIALIZATION_COMPLETENESS_FAIL duplicated source IDs")
    owners = _owner_map(job)
    mapping: dict[str, list[str]] = {}
    for ent, eid in zip(geometry, source_ids):
        original = source_entities[eid]
        if ent.dxftype() != original["type"]:
            fail(f"{eid}: composite physical source entity type changed before decomposition")
        members = owners.get(eid, [])
        if not members and not (original.get("role") == "estimated_note" and original["type"] == "TEXT"):
            fail(f"{eid}: missing canonical member ownership")
        if ent.dxftype() == "LWPOLYLINE":
            mapping[eid] = _expand_polyline(doc, ent, eid, members)
        else:
            ent.set_xdata(APPID, [
                (1000, f"ENTITY_ID={eid}"),
                (1000, f"SOURCE_ENTITY_ID={eid}"),
                (1000, "CANONICAL_MEMBER_IDS=" + ",".join(members)),
            ])
            mapping[eid] = [eid]

    physical = [e for e in doc.modelspace() if e.dxf.layer == "0"]
    if any(ent.dxftype() in ("LWPOLYLINE", "POLYLINE") for ent in physical):
        fail("NO_LWPOLYLINE_COMPOSITE: physical polyline still present")
    expected = [entity_signature(e) for e in physical]
    expected_tags = []
    for ent in physical:
        values = [str(t.value) for t in ent.get_xdata(APPID) if t.code == 1000]
        expected_tags.append(values)
    flattened = [eid for eids in mapping.values() for eid in eids]
    if set(mapping) != set(source_ids) or len(flattened) != len(set(flattened)):
        fail("CANONICAL_TO_SAVED_SEGMENT_MAPPING_INCOMPLETE")
    if len(flattened) != len(physical):
        fail("CANONICAL_TO_SAVED_SEGMENT_COUNT_MISMATCH")
    doc.saveas(target)
    loaded = ezdxf.readfile(target)
    if loaded.audit().has_errors:
        fail(f"V4.31 saved-DXF audit failed: {target.name}")
    saved = [e for e in loaded.modelspace() if e.dxf.layer == "0"]
    if [entity_signature(e) for e in saved] != expected:
        fail("V4.31 source physical LINE/ARC/CIRCLE geometry changed during DXF roundtrip")
    found = []
    parents = []
    for ent, before in zip(saved, expected_tags):
        try:
            tags = [str(t.value) for t in ent.get_xdata(APPID) if t.code == 1000]
        except ezdxf.DXFError as exc:
            raise CanonicalContractError("saved Layer-0 physical entity missing XDATA") from exc
        if tags != before:
            fail("saved DXF segment provenance changed after read-back")
        values = dict(x.split("=", 1) for x in tags if "=" in x)
        found.append(values.get("ENTITY_ID"))
        parents.append(values.get("SOURCE_ENTITY_ID"))
    if set(found) != set(flattened) or len(found) != len(set(found)) or set(parents) != set(source_ids):
        fail("CANONICAL_ENTITY_IDS_EQ_SAVED_DXF_ENTITY_IDS failed (source -> segment 1:N)")
    manifest["canonical_contract"] = CONTRACT
    manifest["canonical_completeness"] = {
        "status": "PASS",
        "source_to_canonical": "PASS",
        "canonical_to_saved_dxf_entity_ids": "PASS",
        "canonical_to_saved_dxf_segment_ids": "PASS",
        "physical_segments": len(saved),
        "source_entity_count": len(source_ids),
        "source_to_serialized_segments": mapping,
        "parts": validation["parts"],
    }
    return manifest


def export_canonical_job(job: dict, output_dir, gap_mm=10.0, write_manifest=False) -> dict:
    """Validate full member ledger, serialize single composite, stamp/read back entity IDs."""
    validation = validate_canonical_job(job)
    source_anomalies = canonical_job_anomalies(job)
    if source_anomalies:
        fail("SOURCE_SEMANTIC_GUARD_FAIL: " + "; ".join(source_anomalies))
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    manifest = export_job(job, out, gap_mm=gap_mm, mode="single", write_manifest=False)
    manifest = _stamp_and_verify(job, manifest, out, validation)
    manifest["artifacts"] = export_part_artifacts(job, out)
    # Avoid stale production composites after PASS -> REVIEW (or reverse).
    obsolete = (f"{manifest['job_id']}_ALL.dxf"
                if manifest["status"] == "REVIEW_ONLY"
                else f"{manifest['job_id']}_ALL_REVIEW_ONLY.dxf")
    (out / obsolete).unlink(missing_ok=True)
    if write_manifest:
        (out / f"{manifest['job_id']}_MANIFEST.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return manifest


def main() -> None:
    ap = argparse.ArgumentParser(description="V4.31 canonical-member-complete single composite DXF")
    ap.add_argument("input_json", type=Path)
    ap.add_argument("output_dir", type=Path)
    ap.add_argument("--gap-mm", type=float, default=10.0)
    ap.add_argument("--write-manifest", action="store_true")
    args = ap.parse_args()
    job = json.loads(args.input_json.read_text(encoding="utf-8"))
    manifest = export_canonical_job(job, args.output_dir, args.gap_mm, args.write_manifest)
    print(json.dumps({
        "job_id": manifest["job_id"],
        "file": manifest["filename"],
        "canonical_contract": manifest["canonical_contract"],
        "completeness": manifest["canonical_completeness"]["status"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
