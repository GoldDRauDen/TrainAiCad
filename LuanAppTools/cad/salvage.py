"""Export what a run already proved, without another model call.

Every code that finished validation is stored as a canonical part. When a job stops before every code is done
(cancel, time, a code that could not be solved), those parts are still a valid input for the repository's exporter.
This module gathers them, optionally adds a clearly flagged draft for a code whose last candidate failed validation,
and exports one REVIEW-ONLY composite that names the codes it could not include. Rules, exporter and gates stay the
repository's; nothing here relaxes them for a part that passed.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

from LuanAppTools.cad.builders import CHECK_NAMES, resolve_part
from LuanAppTools.cad.contract import namespace_entity_ids
from LuanAppTools.cad.repository import CadError, run_tool

DRAFT_FLAG = "DRAFT_UNVALIDATED: last candidate failed validation; geometry as the model wrote it, not proved"
UTF8_MODE = ("-X", "utf8")


def last_validated_part(history, stage_dir=None):
    """The part of the newest validate/build_part request in an interaction history (None when there is none)."""
    for entry in reversed(history or ()):
        request = entry.get("request") or {}
        if request.get("name") not in ("validate", "build_part"):
            continue
        arguments = request.get("arguments") or {}
        part = arguments.get("part")
        try:
            if request["name"] == "validate":
                part = resolve_part(stage_dir, part) if stage_dir and part is not None else part
                if part is None and arguments.get("part_ref") and stage_dir:
                    part = resolve_part(stage_dir, {"part_ref": arguments["part_ref"]})
            else:
                part = (entry.get("result") or {}).get("part")
        except ValueError:
            part = None
        if isinstance(part, dict) and part.get("entities"):
            return part
    return None


def read_last(stage_dir):
    """The part most recently handed to a validating host tool (HostTools.remember), if any."""
    try:
        part = json.loads((Path(stage_dir) / "last.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    return part if isinstance(part, dict) else None


def capture_draft(state, stage_dir=None):
    """Keep the newest candidate of a failed attempt beside its code; call before the interaction is dropped."""
    history = (state.get("interaction") or {}).get("history")
    part = (read_last(stage_dir) if stage_dir else None) or last_validated_part(history, stage_dir)         or state.get("candidate")
    if isinstance(part, dict) and part.get("entities"):
        state["draft"] = part
    return state.get("draft")


def make_draft(part):
    """A flagged VIEWS_ONLY copy of an unvalidated candidate, or None when it has nothing drawable.

    VIEWS_ONLY is the repository's own state for source geometry that is shown but not proved to be a flat pattern, so
    the composite stays REVIEW ONLY and the draft is labelled as a view in the DXF.
    """
    if not isinstance(part, dict) or not isinstance(part.get("material"), str) or not part.get("code"):
        return None
    draft = copy.deepcopy(part)
    geometry = [e for e in draft.get("entities", []) if isinstance(e, dict) and e.get("type") not in (None, "TEXT")]
    if not geometry or not isinstance(draft.get("thickness_mm"), (int, float)):
        return None
    for entity in geometry:
        entity["view_id"] = "DRAFT"
    draft.update(status="VIEWS_ONLY", preview_reason="separate_source_views",
                 flags=[*[f for f in draft.get("flags", []) if f != DRAFT_FLAG], DRAFT_FLAG],
                 checks={name: "FLAGGED" for name in CHECK_NAMES})
    for key in ("review_reason",):
        draft.pop(key, None)
    return draft


def collect(rows, checkpoint, *, drafts=True):
    """Split a run's codes into proved parts, flagged drafts and codes with nothing to export.

    `rows` are the stored parts of the run (Store.parts); `checkpoint` supplies the code order and any draft.
    """
    saved = {row["code"]: row for row in rows}
    order = [c["code"] for c in (checkpoint.get("inventory") or {}).get("codes", [])] or list(saved)
    proved, drafted, missing = [], [], []
    for code in order:
        canonical = ((saved.get(code) or {}).get("data") or {}).get("canonical")
        if canonical:
            proved.append(canonical)
            continue
        state = (checkpoint.get("parts") or {}).get(code) or {}
        draft = make_draft(state.get("draft") or state.get("candidate")) if drafts else None
        if draft:
            drafted.append(draft)
        else:
            missing.append(code)
    return {"order": order, "proved": proved, "drafted": drafted, "missing": missing}


def ordered(collected):
    by_code = {p["code"]: p for p in [*collected["proved"], *collected["drafted"]]}
    return [by_code[c] for c in collected["order"] if c in by_code]


def report(collected):
    return {"proved": [p["code"] for p in collected["proved"]], "drafted": [p["code"] for p in collected["drafted"]],
            "missing": list(collected["missing"])}


def stamp_missing(path, missing, drafted):
    """Add the codes that are absent or drafted to the composite's non-plot AI_META layer, as plain text."""
    import ezdxf
    from ezdxf import bbox

    document = ezdxf.readfile(path)
    if "AI_META" not in document.layers:
        document.layers.add("AI_META", color=7, plot=0)
    modelspace = document.modelspace()
    extent = bbox.extents(modelspace)
    x = extent.extmin.x if extent.has_data else 0.0
    y = (extent.extmin.y if extent.has_data else 0.0) - 30.0
    lines = ["REVIEW ONLY - NO CUT - COMPOSITE IS INCOMPLETE"]
    if missing:
        lines.append("KHONG CO TRONG FILE (chua giai xong): " + ", ".join(missing))
    if drafted:
        lines.append("BAN NHAP CHUA KIEM CHUNG: " + ", ".join(drafted))
    for index, line in enumerate(lines):
        modelspace.add_text(line, height=6.0, dxfattribs={"layer": "AI_META", "insert": (x, y - index * 10.0)})
    document.saveas(path)


async def build_export(repo, collected, job, workspace, cancel, *, individual=False, timeout=600):
    """(metadata, {name: path}) for the proved parts plus drafts; the composite is REVIEW ONLY when anything is off.

    `job` is the job envelope without parts (canonical_contract, job_id, customer_code). Proved parts only go through
    the canonical exporter exactly as a complete run would; a draft needs the serializer's VIEWS_ONLY path, so a job
    with drafts is serialized by tools/export_dxf.py instead, and a draft the serializer refuses is left out.
    """
    workspace = Path(workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    output = workspace / "output"
    attempts = [True, False] if collected["drafted"] else [False]
    last_error = None
    for with_drafts in attempts:
        parts = namespace_entity_ids(
            ordered(collected) if with_drafts else
            [p for p in ordered(collected) if p["code"] in {q["code"] for q in collected["proved"]}])
        if not parts:
            break
        document = {**job, "parts": parts}
        path = workspace / "canonical.json"
        path.write_text(json.dumps(document), encoding="utf-8")
        for stale in output.rglob("*.dxf") if output.exists() else ():
            stale.unlink()
        try:
            if with_drafts:
                await run_tool([sys.executable, *UTF8_MODE, repo.root / "tools/export_dxf.py", path, output],
                               repo.root, cancel, timeout=timeout)
                metadata = {"serializer": "export_dxf", "drafts": [p["code"] for p in collected["drafted"]]}
            else:
                metadata, _ = await _canonical(repo, path, output, cancel, individual, timeout)
        except CadError as exc:
            last_error = exc
            continue
        files = {p.relative_to(output).as_posix(): p for p in output.rglob("*.dxf")}
        if not files:
            last_error = CadError("The exporter wrote no DXF")
            continue
        missing = list(collected["missing"])
        drafted = [p["code"] for p in collected["drafted"]] if with_drafts else []
        left_out = [p["code"] for p in collected["drafted"]] if not with_drafts else []
        if missing or drafted or left_out:
            files = _as_review_only(files, job["job_id"], [*missing, *left_out], drafted)
        metadata = {**(metadata if isinstance(metadata, dict) else {}), "salvage": {**report(collected),
                                                                                    "left_out": left_out}}
        return metadata, files
    raise CadError(f"Nothing could be exported from the saved parts: {last_error}" if last_error
                   else "No saved part can be exported")


async def _canonical(repo, path, output, cancel, individual, timeout):
    argv = [sys.executable, *UTF8_MODE, repo.root / "tools/export_canonical_dxf.py", path, output]
    if individual:
        argv.append("--individual-dxf")
    return json.loads(await run_tool(argv, repo.root, cancel, timeout=timeout)), None


def _as_review_only(files, job_id, missing, drafted):
    """Name the composite *_ALL_REVIEW_ONLY.dxf and stamp it; individual part files stay as the exporter made them."""
    production, review = f"{job_id}_ALL.dxf", f"{job_id}_ALL_REVIEW_ONLY.dxf"
    if production in files:
        source = files.pop(production)
        target = source.with_name(review)
        source.replace(target)
        files[review] = target
    if review not in files:
        raise CadError("The exporter wrote no composite DXF")
    stamp_missing(files[review], missing, drafted)
    return files
