#!/usr/bin/env python3
"""Source-first weld-site -> KEGAKI completeness gate for canonical CAD jobs.

This is a ledger validator, not a vision/geometry solver. It does not infer
weld positions from DXF samples or invent KEGAKI geometry.
"""
from __future__ import annotations

import math
import re

IDENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


class WeldKegakiError(ValueError):
    """A proved/potential weld site lost its required KEGAKI provenance."""


def fail(message: str) -> None:
    raise WeldKegakiError("WELD_KEGAKI_CLOSURE_FAIL: " + message)


def _ids(value, context: str) -> list[str]:
    if not isinstance(value, list):
        fail(f"{context}: list required")
    if any(not isinstance(x, str) or not IDENT.fullmatch(x) for x in value):
        fail(f"{context}: invalid source id")
    if len(value) != len(set(value)):
        fail(f"{context}: duplicate source id")
    return value


def _evidence(value, context: str) -> str:
    if not isinstance(value, str) or len(value.strip()) < 8:
        fail(f"{context}: scoped source/witness evidence required")
    return value


def check_weld_site_census(
    *, customer_code: str | None, features: dict | None,
    source_assembly_view_ids, source_weld_site_ids, census,
    code: str,
) -> dict:
    """Independent source census closure, reusable at Router and canonical gates.

    A customer-specific welding obligation comes from explicit numeric job
    statistics, never from barcode suffixes or historical sample geometry.
    """
    mandatory = customer_code == "851"
    active = (mandatory or source_assembly_view_ids is not None
              or source_weld_site_ids is not None or census is not None)
    if not active:
        return {"active": False, "sites": [], "required_site_ids": []}
    if not isinstance(census, dict):
        fail(f"{code}: weld_site_census required before KEGAKI=NO / export")
    assembly = _ids(source_assembly_view_ids, f"{code} source_assembly_view_ids")
    discovered = _ids(source_weld_site_ids, f"{code} source_weld_site_ids")
    inspected = _ids(census.get("inspected_assembly_view_ids"),
                     f"{code} inspected_assembly_view_ids")
    if set(assembly) != set(inspected):
        fail(f"{code}: assembly views missing from weld-site inspection")
    _evidence(census.get("source_evidence"), f"{code} weld_site_census")
    sites = census.get("sites")
    if not isinstance(sites, list):
        fail(f"{code}: weld_site_census.sites list required")
    ids = _ids([s.get("weld_site_id") if isinstance(s, dict) else None for s in sites],
               f"{code} weld-site ids")
    if set(ids) != set(discovered):
        fail(f"{code}: source WELD_SITE census != weld-site ledger")
    if not sites:
        _evidence(census.get("no_weld_evidence"), f"{code} no-weld disposition")
        if mandatory and assembly:
            # CHAIN_CENSUS_EMPTY: a part drawn in an assembly view with other
            # LASER parts cannot silently carry an empty weld-site census.
            partners = census.get("assembly_laser_partner_codes")
            if not isinstance(partners, list) or any(
                    not isinstance(p, str) or not p.strip() for p in partners):
                fail(f"{code}: CHAIN_CENSUS_EMPTY: assembly_laser_partner_codes "
                     "list required when weld_site_census.sites is empty (KH851)")
            text = census["no_weld_evidence"]
            missing = [p for p in partners if p not in text]
            if missing:
                fail(f"{code}: CHAIN_CENSUS_EMPTY: no_weld_evidence must name each laser "
                     f"partner and why no KEGAKI host exists: {missing}")
    required_ids = []
    for site in sites:
        wid = site["weld_site_id"]
        if site.get("status") not in ("PROVED", "FLAGGED"):
            fail(f"{code}/{wid}: weld-site state must be PROVED or FLAGGED")
        if site.get("parent_code") != code:
            fail(f"{code}/{wid}: wrong host/parent part identity")
        if not isinstance(site.get("child_part_id"), str) or not site["child_part_id"].strip():
            fail(f"{code}/{wid}: child/constituent identity missing")
        view = site.get("assembly_view_id")
        if view not in inspected:
            fail(f"{code}/{wid}: assembly view not inspected / identity not locked")
        _evidence(site.get("source_evidence"), f"{code}/{wid} weld source")
        if site.get("status") == "PROVED":
            if not isinstance(site.get("host_face"), str) or not site["host_face"].strip():
                fail(f"{code}/{wid}: proved weld host face missing")
        elif not site.get("unresolved_fields"):
            fail(f"{code}/{wid}: FLAGGED weld needs explicit unresolved_fields")
        # KH851 is a site-specific MUST even without a KEGAKI/welding callout.
        # Others retain existing source cue + non-self-locating / explicit rule.
        needs_mark = (mandatory or site.get("mark_required_by_source") is True or
                      (site.get("weld_required_cue") is True and
                       site.get("self_locating") is False))
        if needs_mark:
            required_ids.append(wid)
            if features is not None:
                f = features.get("KEGAKI")
                state = f.get("state") if isinstance(f, dict) else f
                if state == "NO":
                    fail(f"{code}/{wid}: KEGAKI=NO despite required weld mark")
            if site.get("mark_status") not in ("PROVED", "FLAGGED"):
                fail(f"{code}/{wid}: required mark must be PROVED or local FLAGGED")
        elif not isinstance(site.get("not_required_evidence"), str) or not site["not_required_evidence"].strip():
            fail(f"{code}/{wid}: reason KEGAKI not required must be scoped")
    return {"active": True, "sites": sites, "required_site_ids": required_ids}


def _seg(ent):
    return ((float(ent["start"][0]), float(ent["start"][1])),
            (float(ent["end"][0]), float(ent["end"][1])))


def _shared(seg, other) -> float:
    """Positive length shared by two collinear straight segments."""
    (x0, y0), (x1, y1) = seg
    length = math.hypot(x1 - x0, y1 - y0)
    if length < 1e-6:
        return 0.0
    ux, uy = (x1 - x0) / length, (y1 - y0) / length
    (ox0, oy0), (ox1, oy1) = other
    if abs((ox0 - x0) * uy - (oy0 - y0) * ux) > 1e-6 or abs((ox1 - x0) * uy - (oy1 - y0) * ux) > 1e-6:
        return 0.0
    a = (ox0 - x0) * ux + (oy0 - y0) * uy
    b = (ox1 - x0) * ux + (oy1 - y0) * uy
    return max(0.0, min(length, max(a, b)) - max(0.0, min(a, b)))


def check_kegaki_drawing_form(part: dict) -> None:
    """KEGAKI LINEs: no duplicated/overlapping segment, none on the contour.

    A KEGAKI boundary that coincides with a part edge is not drawn, and
    adjacent contact zones are drawn as one UNION outline (rules/KEGAKI.md section 4).
    """
    code = part["code"]
    lines = [e for e in part.get("entities", [])
             if e.get("role") == "kegaki" and e.get("type") == "LINE"]
    for i, a in enumerate(lines):
        for b in lines[i + 1:]:
            if _shared(_seg(a), _seg(b)) > 1e-6:
                fail(f"{code}: KEGAKI_DUPLICATE_SEGMENT: {a['entity_id']} overlaps {b['entity_id']}")
    for outer in (e for e in part.get("entities", []) if e.get("role") == "outer"):
        verts = outer.get("vertices") or []
        for k, (x, y, bulge) in enumerate(verts):
            if abs(bulge) > 1e-9:
                continue
            nx, ny, _ = verts[(k + 1) % len(verts)]
            for line in lines:
                if _shared(_seg(line), ((x, y), (nx, ny))) > 1e-6:
                    fail(f"{code}: KEGAKI_ON_CONTOUR: {line['entity_id']} lies on the part contour; "
                         "a boundary coinciding with the part edge is not drawn")


def validate_weld_kegaki(part: dict, customer_code: str | None) -> dict:
    """Validate independently harvested weld sites against canonical KEGAKI."""
    code = part["code"]
    closure = check_weld_site_census(
        customer_code=customer_code,
        features=None,
        source_assembly_view_ids=part.get("source_assembly_view_ids"),
        source_weld_site_ids=part.get("source_weld_site_ids"),
        census=part.get("weld_site_census"),
        code=code,
    )
    if not closure["active"]:
        return {"status": "NOT_APPLICABLE"}
    check_kegaki_drawing_form(part)
    required = set(closure["required_site_ids"])
    groups = part["source_groups"]
    by_source = {}
    for group in groups:
        for member in group["members"]:
            by_source[member["member_id"]] = (
                group["family"], member.get("status", group["status"]))
    by_canonical = {m["source_member_id"]: m for m in part["canonical_members"]
                    if m.get("origin") == "SOURCE"}
    entities = {e["entity_id"]: e for e in part["entities"]}
    used_members = set()
    flagged_sites = []
    proved_sites = []
    for site in closure["sites"]:
        wid = site["weld_site_id"]
        if wid not in required:
            continue
        mids = _ids(site.get("mark_member_ids"), f"{code}/{wid} mark_member_ids")
        if not mids:
            fail(f"{code}/{wid}: KEGAKI source member missing")
        for mid in mids:
            if mid in used_members:
                fail(f"{code}/{wid}: mark shared across weld sites without independent evidence")
            used_members.add(mid)
            family, state = by_source.get(mid, (None, None))
            member = by_canonical.get(mid)
            if family != "KEGAKI" or member is None:
                fail(f"{code}/{wid}: {mid} not canonical KEGAKI")
            cstate = member["status"]
            eids = member["entity_ids"]
            if site["mark_status"] == "PROVED":
                if site["status"] != "PROVED":
                    fail(f"{code}/{wid}: unproved weld cannot have production mark")
                _evidence(site.get("datum_evidence"), f"{code}/{wid} mark datum")
                if state != "PROVED" or cstate != "PROVED" or not eids:
                    fail(f"{code}/{wid}: proved KEGAKI lost canonical geometry")
                for eid in eids:
                    ent = entities[eid]
                    if ent.get("type") not in ("LINE", "LWPOLYLINE") or ent.get("role") != "kegaki" or ent.get("color") != 1:
                        fail(f"{code}/{wid}: proved KEGAKI must be RED LINE/LWPOLYLINE")
            else:
                if state != "FLAGGED" or cstate not in ("PREVIEW", "FLAGGED_NO_GEOMETRY", "SOURCE_VIEW"):
                    fail(f"{code}/{wid}: unresolved KEGAKI must remain local FLAGGED")
                if not site.get("unresolved_fields"):
                    fail(f"{code}/{wid}: unresolved KEGAKI fields missing")
                for eid in eids:
                    ent = entities[eid]
                    if ent.get("color") != 6 or ent.get("role") not in ("estimated", "source_view"):
                        fail(f"{code}/{wid}: unproved marking cannot become RED/CUT")
        if site["mark_status"] == "FLAGGED":
            flagged_sites.append(wid)
        else:
            proved_sites.append(wid)
    if flagged_sites:
        if part.get("status") == "PASS":
            fail(f"{code}: FLAGGED weld sites cannot have PASS output: {flagged_sites}")
        if not part.get("flags"):
            fail(f"{code}: unresolved KEGAKI requires part flags")
    return {"status": "REVIEW" if flagged_sites else "PASS",
            "required_site_ids": sorted(required), "proved_site_ids": proved_sites,
            "flagged_site_ids": flagged_sites}
