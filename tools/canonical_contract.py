#!/usr/bin/env python3
"""Source-group/member -> canonical-entity completeness contract (the one canonical JSON contract)."""
from __future__ import annotations

import re
import math
from collections import defaultdict

from curve_guard import split_curve_errors
from weld_kegaki_guard import WeldKegakiError, validate_weld_kegaki

CONTRACT = "TrainAiCad-CANONICAL-V4.34"
SOURCE_STATUSES = {"PROVED", "FLAGGED", "CANCELED"}
CANON_SOURCE_STATUSES = {"PROVED", "PREVIEW", "FLAGGED_NO_GEOMETRY", "SOURCE_VIEW"}
ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


class CanonicalContractError(ValueError):
    pass


def fail(message: str) -> None:
    raise CanonicalContractError(message)


def ident(value, context: str) -> str:
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        fail(f"{context}: stable ASCII id required")
    return value


def _members_of(group):
    members = group.get("members")
    if not isinstance(members, list):
        fail(f"{group.get('group_id', '?')}: members list required")
    return members


def validate_part(part: dict, customer_code: str | None = None) -> dict:
    code = ident(part.get("code"), "part code")
    entities = part.get("entities")
    if not isinstance(entities, list) or not entities:
        fail(f"{code}: canonical entities required")

    entity_ids = []
    entity_by_id = {}
    for ent in entities:
        eid = ident(ent.get("entity_id"), f"{code} entity_id")
        if eid in entity_by_id:
            fail(f"{code}: duplicate entity_id {eid}")
        entity_ids.append(eid)
        entity_by_id[eid] = ent

    groups = part.get("source_groups")
    if not isinstance(groups, list) or not groups:
        fail(f"{code}: source_groups ledger required")

    source_member = {}
    source_group = {}
    group_member_ids = defaultdict(list)
    unknown_quantity_groups = set()
    flagged_source_members = set()
    for group in groups:
        gid = ident(group.get("group_id"), f"{code} group_id")
        if gid in source_group:
            fail(f"{code}: duplicate source group {gid}")
        status = group.get("status")
        family = group.get("family")
        if status not in SOURCE_STATUSES or not isinstance(family, str) or not family:
            fail(f"{code}/{gid}: family and source status required")
        source_group[gid] = group
        members = _members_of(group)
        qty = group.get("source_quantity")
        if qty is None:
            unknown_quantity_groups.add(gid)
        elif not isinstance(qty, int) or isinstance(qty, bool) or qty < 0:
            fail(f"{code}/{gid}: source_quantity must be non-negative integer or null")
        elif qty != len(members):
            fail(f"{code}/{gid}: GROUP_COUNT_CLOSURE source_quantity={qty} members={len(members)}")
        for member in members:
            mid = ident(member.get("member_id"), f"{code}/{gid} member_id")
            if mid in source_member:
                fail(f"{code}: duplicate source member {mid}")
            mstatus = member.get("status", status)
            if mstatus not in SOURCE_STATUSES:
                fail(f"{code}/{gid}/{mid}: invalid source member status")
            source_member[mid] = {"group_id": gid, "status": mstatus, "family": family}
            if mstatus == "FLAGGED" or status == "FLAGGED":
                flagged_source_members.add(mid)
            group_member_ids[gid].append(mid)

    canonical = part.get("canonical_members")
    if not isinstance(canonical, list):
        fail(f"{code}: canonical_members ledger required")

    canonical_ids = set()
    source_backed = {}
    entity_owners = defaultdict(list)
    for member in canonical:
        cid = ident(member.get("canonical_member_id"), f"{code} canonical_member_id")
        if cid in canonical_ids:
            fail(f"{code}: duplicate canonical_member_id {cid}")
        canonical_ids.add(cid)
        origin = member.get("origin")
        status = member.get("status")
        eids = member.get("entity_ids", [])
        if not isinstance(eids, list) or len(eids) != len(set(eids)):
            fail(f"{code}/{cid}: entity_ids must be a unique list")
        for eid in eids:
            ident(eid, f"{code}/{cid} entity_id")
            if eid not in entity_by_id:
                fail(f"{code}/{cid}: canonical member references missing entity {eid}")
            entity_owners[eid].append(cid)

        if origin == "SOURCE":
            mid = ident(member.get("source_member_id"), f"{code}/{cid} source_member_id")
            if mid not in source_member:
                fail(f"{code}/{cid}: unknown source member {mid}")
            if mid in source_backed:
                fail(f"{code}: source member {mid} mapped more than once")
            if member.get("group_id") != source_member[mid]["group_id"]:
                fail(f"{code}/{cid}: source group ownership mismatch for {mid}")
            if status not in CANON_SOURCE_STATUSES:
                fail(f"{code}/{cid}: invalid source-backed canonical status")
            src_status = source_member[mid]["status"]
            if src_status == "PROVED" and status != "PROVED":
                fail(f"{code}/{mid}: PROVED source member is not PROVED canonical")
            if src_status == "FLAGGED" and status not in {"PREVIEW", "FLAGGED_NO_GEOMETRY", "SOURCE_VIEW"}:
                fail(f"{code}/{mid}: FLAGGED source member lost its uncertainty state")
            if src_status == "CANCELED":
                fail(f"{code}/{mid}: canceled source member emitted into canonical model")
            if status == "PROVED" and not eids:
                fail(f"{code}/{mid}: PROVED canonical member requires physical entity_ids")
            if status in {"PREVIEW", "SOURCE_VIEW"} and not eids:
                fail(f"{code}/{mid}: {status} canonical member requires entity_ids")
            if status == "FLAGGED_NO_GEOMETRY" and eids:
                fail(f"{code}/{mid}: FLAGGED_NO_GEOMETRY cannot own fabricated geometry")
            source_backed[mid] = member
        elif origin == "DERIVED_RULE":
            if not isinstance(member.get("controlling_rule"), str) or not member["controlling_rule"]:
                fail(f"{code}/{cid}: DERIVED_RULE requires controlling_rule")
            source_ids = member.get("source_member_ids")
            if not isinstance(source_ids, list) or not source_ids:
                fail(f"{code}/{cid}: DERIVED_RULE requires source_member_ids")
            for mid in source_ids:
                if mid not in source_member or source_member[mid]["status"] == "CANCELED":
                    fail(f"{code}/{cid}: invalid DERIVED_RULE source member {mid}")
            if status not in {"PROVED", "PREVIEW"} or not eids:
                fail(f"{code}/{cid}: DERIVED_RULE requires physical PROVED/PREVIEW entities")
        else:
            fail(f"{code}/{cid}: origin must be SOURCE or DERIVED_RULE")

    active_source = {mid for mid, rec in source_member.items() if rec["status"] != "CANCELED"}
    if active_source != set(source_backed):
        missing = sorted(active_source - set(source_backed))
        extra = sorted(set(source_backed) - active_source)
        fail(f"{code}: SOURCE_FEATURE_COMPLETENESS_FAIL missing={missing} extra={extra}")

    proved_source = {mid for mid, rec in source_member.items() if rec["status"] == "PROVED"}
    proved_canonical = {mid for mid, rec in source_backed.items() if rec.get("status") == "PROVED"}
    if proved_source != proved_canonical:
        fail(f"{code}: PROVED_SOURCE_MEMBERS_EQ_CANONICAL failed")

    # Every manufacturing Layer-0 input entity must belong to a canonical member.
    # Adjacent preview note TEXT is annotation, not a manufacturing operation.
    for eid, ent in entity_by_id.items():
        annotation = (ent.get("type") == "TEXT" and ent.get("role") == "estimated_note") or ent.get("role") == "mark"
        if not annotation and eid not in entity_owners:
            fail(f"{code}: orphan canonical manufacturing entity {eid}")

    # A circle is one CIRCLE and an arc one ARC: no split arcs, no faceted circles (DATA parts exempt).
    curve_errors = split_curve_errors(part)
    if curve_errors:
        fail(f"{code}: {curve_errors[0]}")

    # Independent weld-site census is checked against real KEGAKI source
    # members and canonical RED marking, not merely source/canonical equality.
    try:
        weld_closure = validate_weld_kegaki(part, customer_code)
    except WeldKegakiError as exc:
        fail(str(exc))

    # PASS is a production claim: every active source member and group count
    # must be closed, regardless of caller-supplied checks/status summaries.
    if part.get("status") == "PASS":
        if flagged_source_members:
            fail(f"{code}: PASS_WITH_FLAGGED_SOURCE_MEMBERS:{sorted(flagged_source_members)}")
        if unknown_quantity_groups:
            fail(f"{code}: PASS_WITH_UNKNOWN_SOURCE_QUANTITY:{sorted(unknown_quantity_groups)}")

    return {
        "code": code,
        "weld_kegaki_closure": weld_closure,
        "source_group_count": len(groups),
        "source_member_count": len(source_member),
        "proved_source_member_count": len(proved_source),
        "canonical_member_count": len(canonical),
        "canonical_entity_count": len(entity_ids),
        "entity_ids": entity_ids,
        "entity_owners": {k: list(v) for k, v in entity_owners.items()},
        "unknown_quantity_groups": sorted(unknown_quantity_groups),
    }


def validate_canonical_job(job: dict) -> dict:
    contract = job.get("canonical_contract")
    if contract != CONTRACT:
        fail(f"job canonical_contract must be {CONTRACT}")
    parts = job.get("parts")
    if not isinstance(parts, list) or not parts:
        fail("canonical job requires parts")
    raw_customer_code = job.get("customer_code")
    if raw_customer_code is not None:
        if isinstance(raw_customer_code, bool) or not str(raw_customer_code).strip().isdigit():
            fail("customer_code must be the numeric code from job statistics")
        customer_code = str(int(str(raw_customer_code).strip()))
    else:
        customer_code = None
    records = [validate_part(part, customer_code=customer_code) for part in parts]
    from material_resolver import is_hairline, resolve_material, MaterialResolveError
    for part in parts:
        code = part["code"]
        try:
            resolve_material(part["material"], "LASER_R")
        except MaterialResolveError as exc:
            fail(f"{code}: {exc}")
        grain = part.get("grain", {})
        has_hl = is_hairline(part["material"]) or grain.get("is_hl", False)
        if has_hl and (not isinstance(grain, dict) or grain.get("is_hl") is not True):
            fail(f"{code}: HL_DIRECTION_UNPROVED: grain record required")
        if part["status"] == "REVIEW":
            if part.get("review_reason") != "HL_DIRECTION_UNPROVED" or not has_hl or not part.get("flags"):
                fail(f"{code}: REVIEW requires HL_DIRECTION_UNPROVED and a flag")
            if grain.get("direction_xy") is not None:
                fail(f"{code}: HL review cannot claim proved grain direction")
        elif part["status"] == "PASS" and has_hl:
            if not grain.get("evidence_ref") or grain.get("direction_xy") is None:
                fail(f"{code}: HL_DIRECTION_UNPROVED")
            vector = grain.get("direction_xy")
            try:
                x, y = (float(v) for v in vector)
            except (TypeError, ValueError):
                fail(f"{code}: HL_DIRECTION_INVALID")
            if not all(math.isfinite(v) for v in (x, y)) or math.hypot(x, y) <= 1e-10:
                fail(f"{code}: HL_DIRECTION_INVALID")
        proven = {
            member["member_id"] for group in part["source_groups"]
            if group["family"].upper() in {"HOLE", "SLOT"} and group["status"] == "PROVED"
            for member in group.get("members", [])
            if member.get("status", "PROVED") == "PROVED"
        }
        required = set(part.get("witness_required_feature_ids", []))
        if not proven <= required:
            fail(f"{code}: WITNESS_REQUIRED_FEATURE_MISSING:{sorted(proven - required)}")
        if proven and not part.get("feature_witness_graph"):
            fail(f"{code}: WITNESS_GRAPH_MISSING")
        hole_members = {
            member["member_id"] for group in part["source_groups"]
            if group["family"].upper() == "HOLE" and group["status"] == "PROVED"
            for member in group.get("members", [])
            if member.get("status", "PROVED") == "PROVED"
        }
        trace_targets = part.get("feature_witness_graph", {}).get("targets", [])
        if hole_members and any(
            not target.get("entity_id")
            for target in trace_targets if target.get("feature_id") in hole_members
        ):
            fail(f"{code}: WITNESS_CANONICAL_ENTITY_LINK_MISSING")
        canonical_by_source = {
            m.get("source_member_id"): set(m.get("entity_ids", []))
            for m in part["canonical_members"] if m.get("origin") == "SOURCE"
        }
        entity_id_set = {e["entity_id"] for e in part["entities"]}
        for target in trace_targets:
            feature = target.get("feature_id")
            if feature not in proven:
                continue
            eid = target.get("entity_id")
            if not eid or eid not in canonical_by_source.get(feature, set()):
                fail(f"{code}: WITNESS_CANONICAL_ENTITY_LINK_MISSING")
            datum_id = target.get("datum_entity_id")
            offset = target.get("datum_coordinate_mm")
            if (datum_id not in entity_id_set or isinstance(offset, bool) or
                    not isinstance(offset, (int, float)) or not math.isfinite(float(offset))):
                fail(f"{code}: WITNESS_DATUM_ENTITY_LINK_MISSING")
        for feature in proven:
            feature_targets = [t for t in trace_targets if t.get("feature_id") == feature]
            axes = [t.get("axis") for t in feature_targets]
            if len(feature_targets) != 2 or set(axes) != {"X", "Y"}:
                fail(f"{code}: WITNESS_REQUIRED_AXIS_MISSING:{feature}")
        slots = {
            member["member_id"] for group in part["source_groups"]
            if group["family"].upper() == "SLOT" and group["status"] == "PROVED"
            for member in group.get("members", [])
            if member.get("status", "PROVED") == "PROVED"
        }
        if slots and not slots <= {rec.get("slot_id") for rec in part.get("slot_anchor_records", [])}:
            fail(f"{code}: SLOT_ANCHOR_RECORD_MISSING")

        # A green POINT is a manufacturing piercing instruction, not a
        # display choice. It needs the scoped English stamp required by
        # rules/HOLE_TAP.md, linked to its source member and physical entity.
        groups_by_id = {g["group_id"]: g for g in part["source_groups"]}
        member_families = {
            member["source_member_id"]: groups_by_id[member["group_id"]]["family"].upper()
            for member in part["canonical_members"]
            if member.get("origin") == "SOURCE"
        }
        piercing_points = {
            e["entity_id"] for e in part["entities"]
            if e.get("type") == "POINT" and e.get("role") == "through_piercing"
        }
        authorizations = part.get("piercing_authorizations", [])
        authorized = set()
        for record in authorizations:
            text = str(record.get("stamp_text", "")).upper()
            mid, eid = record.get("member_id"), record.get("entity_id")
            if (not record.get("source_pdf_page") or not record.get("evidence_ref") or
                    "PIERCING" not in text or "THROUGH HOLE" not in text or
                    member_families.get(mid) not in {"HOLE", "PIASU"} or
                    eid not in piercing_points or eid not in next(
                        (set(m.get("entity_ids", [])) for m in part["canonical_members"]
                         if m.get("origin") == "SOURCE" and m.get("source_member_id") == mid), set()
                    )):
                fail(f"{code}: THROUGH_PIERCING_SOURCE_SCOPE_UNPROVED:{eid or '?'}")
            authorized.add(eid)
        if piercing_points - authorized:
            fail(f"{code}: THROUGH_PIERCING_SOURCE_SCOPE_UNPROVED:{sorted(piercing_points - authorized)}")

        bend_sources = {
            member["member_id"]: group["group_id"]
            for group in part["source_groups"]
            if group["family"].upper() == "BEND" and group["status"] == "PROVED"
            for member in group.get("members", [])
            if member.get("status", "PROVED") == "PROVED"
        }
        if part["status"] == "PASS" and bend_sources:
            graph = part.get("face_graph")
            faces = graph.get("faces") if isinstance(graph, dict) else None
            bends = graph.get("bends") if isinstance(graph, dict) else None
            if not isinstance(faces, list) or len(faces) < 2 or not isinstance(bends, list) or not bends:
                fail(f"{code}: PASS_WITHOUT_CLOSED_FACE_GRAPH")
            face_fields = ("source_view", "local_origin", "local_axis_u", "local_axis_v",
                           "contour_edge_ids", "source_dimensions", "normal_orientation")
            if any(not isinstance(f, dict) for f in faces):
                fail(f"{code}: FACE_GRAPH_FACE_RECORD_INCOMPLETE")
            face_ids = set()
            for face in faces:
                fid = ident(face.get("face_id"), f"{code} face_id")
                axes = []
                for key in ("local_axis_u", "local_axis_v"):
                    axis = face.get(key)
                    if not isinstance(axis, (list, tuple)) or len(axis) not in {2, 3}:
                        fail(f"{code}: FACE_GRAPH_FACE_RECORD_INCOMPLETE:{fid}")
                    try:
                        vector = [float(v) for v in axis]
                    except (TypeError, ValueError):
                        fail(f"{code}: FACE_GRAPH_FACE_RECORD_INCOMPLETE:{fid}")
                    if not all(math.isfinite(v) for v in vector) or math.sqrt(sum(v*v for v in vector)) <= 1e-10:
                        fail(f"{code}: FACE_GRAPH_FACE_RECORD_INCOMPLETE:{fid}")
                    axes.append(vector)
                origin = face.get("local_origin")
                if (fid in face_ids or any(not face.get(k) for k in face_fields) or
                        not isinstance(origin, (list, tuple)) or len(origin) not in {2, 3} or
                        any(not isinstance(face.get(k), list) or not face.get(k)
                            for k in ("contour_edge_ids", "source_dimensions"))):
                    fail(f"{code}: FACE_GRAPH_FACE_RECORD_INCOMPLETE:{fid}")
                try:
                    origin_values = [float(v) for v in origin]
                except (TypeError, ValueError):
                    fail(f"{code}: FACE_GRAPH_FACE_RECORD_INCOMPLETE:{fid}")
                if not all(math.isfinite(v) for v in origin_values):
                    fail(f"{code}: FACE_GRAPH_FACE_RECORD_INCOMPLETE:{fid}")
                face_ids.add(fid)
            covered = set()
            bend_ids = set()
            for bend in bends:
                if not isinstance(bend, dict):
                    fail(f"{code}: FACE_GRAPH_BEND_RECORD_INVALID")
                bid = bend.get("bend_id")
                members = bend.get("source_member_ids")
                required_fields = ("face_A_shared_edge", "face_B_shared_edge", "edge_orientation",
                                   "attachment_source_evidence", "signed_angle_deg", "material_domain")
                angle = bend.get("signed_angle_deg")
                domain = bend.get("material_domain")
                if (not isinstance(bid, str) or not bid or bid in bend_ids or
                        not isinstance(members, list) or len(members) != 1 or
                        not isinstance(members[0], str) or
                        bend.get("face_A") not in face_ids or bend.get("face_B") not in face_ids or
                        any(not bend.get(k) for k in required_fields if k != "signed_angle_deg") or
                        isinstance(angle, bool) or not isinstance(angle, (int, float)) or
                        not math.isfinite(float(angle)) or float(angle) == 0 or
                        not isinstance(domain, dict) or not isinstance(domain.get("entity_ids"), list) or
                        not domain["entity_ids"] or not domain.get("evidence_ref")):
                    fail(f"{code}: FACE_GRAPH_BEND_RECORD_INCOMPLETE:{bid or '?'}")
                bend_ids.add(bid)
                if any(mid not in bend_sources or mid in covered for mid in members):
                    fail(f"{code}: FACE_GRAPH_SOURCE_BEND_COVERAGE_MISMATCH:{bid}")
                covered.update(members)
                ledger_data = part.get("per_bend_witness_ledger", [])
                if not isinstance(ledger_data, list):
                    ledger_data = []
                ledger = [x for x in ledger_data if isinstance(x, dict) and
                          x.get("bend_id") == bid and
                          x.get("source_group_id") == bend_sources[members[0]]]
                if len(members) != 1 or len(ledger) != 1:
                    fail(f"{code}: BEND_WITNESS_LEDGER_MISSING:{bid}")
                item = ledger[0]
                if (not isinstance(item.get("od_actual_mm"), list) or len(item["od_actual_mm"]) != 2 or
                        not isinstance(item.get("bend_pair_mm"), list) or len(item["bend_pair_mm"]) != 2 or
                        any(item.get(k) is None for k in ("nobi_mm", "flat_mm")) or
                        not item.get("source_pdf_page") or not item.get("evidence_ref")):
                    fail(f"{code}: BEND_WITNESS_LEDGER_INCOMPLETE:{bid}")
            if covered != set(bend_sources):
                fail(f"{code}: FACE_GRAPH_SOURCE_BEND_COVERAGE_MISMATCH")

    all_ids = []
    for rec in records:
        all_ids.extend(rec["entity_ids"])
    if len(all_ids) != len(set(all_ids)):
        fail("entity_id must be globally unique across the composite job")
    return {"contract": contract, "parts": records, "entity_ids": all_ids}
