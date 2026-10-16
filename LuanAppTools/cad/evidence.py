"""Original page rasters and loss-aware physical DATA evidence, never inferred parts."""

from __future__ import annotations
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import shutil
import ezdxf
import fitz


@dataclass
class Evidence:
    workspace: Path
    pages: list[dict]
    dxf: list[dict]

    @property
    def images(self):
        return tuple(Path(p["image"]) for p in self.pages)

    def public(self):
        return {"pages": self.pages, "dxf": self.dxf}


def _value(v):
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    try:
        return list(v)
    except TypeError:
        return str(v)


def physical_entity(e, parent=None):
    kind = e.dxftype()
    result = {
        "id": str(e.dxf.get("handle") or parent),
        "type": kind,
        "layer": e.dxf.layer,
        "attributes": {
            k: _value(v) for k, v in e.dxf.all_existing_dxf_attribs().items()
        },
    }
    if kind == "LINE":
        result.update(start=list(e.dxf.start), end=list(e.dxf.end))
        if e.dxf.start.z or e.dxf.end.z:
            result["unsupported"] = True
    elif kind in ("ARC", "CIRCLE"):
        result.update(
            center=list(e.dxf.center),
            radius=e.dxf.radius,
            extrusion=list(e.dxf.extrusion),
        )
        if kind == "ARC":
            result.update(start_angle=e.dxf.start_angle, end_angle=e.dxf.end_angle)
        if (
            e.dxf.center.z
            or abs(e.dxf.extrusion.z) != 1
            or e.dxf.extrusion.x
            or e.dxf.extrusion.y
        ):
            result["unsupported"] = True
    elif kind in ("LWPOLYLINE", "POLYLINE"):
        result["closed"] = bool(e.is_closed)
        result["vertices"] = (
            [list(v) for v in e.get_points("xyb")]
            if kind == "LWPOLYLINE"
            else [
                [v.dxf.location.x, v.dxf.location.y, v.dxf.get("bulge", 0)]
                for v in e.vertices
            ]
        )
        try:
            result["physical"] = [
                physical_entity(v, result["id"]) for v in e.virtual_entities()
            ]
        except Exception as exc:
            result.update(unsupported=True, decode_error=type(exc).__name__)
    elif kind == "INSERT":
        skipped = []
        result["transform"] = list(e.matrix44())
        try:
            result["physical"] = [
                physical_entity(v, result["id"])
                for v in e.virtual_entities(
                    skipped_entity_callback=lambda ent, reason: skipped.append(
                        {"type": ent.dxftype(), "reason": reason}
                    )
                )
            ]
        except Exception as exc:
            skipped.append({"reason": type(exc).__name__})
        if skipped:
            result.update(unsupported=True, skipped=skipped)
    elif kind in ("TEXT", "MTEXT"):
        result["text"] = e.dxf.text if kind == "TEXT" else e.text
    else:
        # Preserve unsupported raw payload; never replace splines/ellipses by chords.
        result["unsupported"] = True
        if kind == "SPLINE":
            result.update(
                control_points=[list(v) for v in e.control_points],
                fit_points=[list(v) for v in e.fit_points],
                knots=list(e.knots),
                weights=list(e.weights),
            )
    return result


def prepare_evidence(source: Path, workspace: Path):
    source = Path(source).resolve()
    workspace = Path(workspace).resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    copied = workspace / "source"
    copied.mkdir(exist_ok=True)
    rendered = workspace / "pages"
    rendered.mkdir(exist_ok=True)
    pages = []
    drawings = []
    for original in sorted(source.rglob("*")):
        if not original.is_file() or original.suffix.lower() not in (".pdf", ".dxf"):
            continue
        if original.is_symlink() or not original.resolve().is_relative_to(source):
            raise ValueError("Source escape")
        rel = original.relative_to(source)
        path = copied / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, path)
        if (
            hashlib.sha256(original.read_bytes()).digest()
            != hashlib.sha256(path.read_bytes()).digest()
        ):
            raise ValueError("Source copy changed")
        if path.suffix.lower() == ".pdf":
            with fitz.open(path) as pdf:
                for i, page in enumerate(pdf):
                    name = (
                        hashlib.sha256(rel.as_posix().encode()).hexdigest()[:12]
                        + f"-{i+1}.png"
                    )
                    image = rendered / name
                    page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False).save(
                        image
                    )
                    pages.append(
                        {
                            "id": rel.as_posix() + f":p{i+1}",
                            "file": str(path),
                            "page": i + 1,
                            "width": page.rect.width,
                            "height": page.rect.height,
                            "image": str(image),
                            "text_hint": page.get_text(),
                        }
                    )
        else:
            doc = ezdxf.readfile(path)
            if doc.audit().has_errors:
                raise ValueError("Source DXF audit failed")
            drawings.append(
                {
                    "id": rel.as_posix(),
                    "file": str(path),
                    "units": doc.units,
                    "entities": [physical_entity(e) for e in doc.modelspace()],
                }
            )
    if not pages:
        raise ValueError("No source PDF pages")
    ev = Evidence(workspace, pages, drawings)
    (workspace / "evidence.json").write_text(
        json.dumps(ev.public(), ensure_ascii=False), encoding="utf-8"
    )
    return ev


def crop_page(evidence: Evidence, page_id: str, rect: list[float]):
    p = next((p for p in evidence.pages if p["id"] == page_id), None)
    if (
        not p
        or len(rect) != 4
        or not (
            0 <= rect[0] < rect[2] <= p["width"]
            and 0 <= rect[1] < rect[3] <= p["height"]
        )
    ):
        raise ValueError("Invalid source crop region")
    name = hashlib.sha256(json.dumps([page_id, rect]).encode()).hexdigest()[:20]
    target = evidence.workspace / "pages" / f"crop-{name}.png"
    with fitz.open(p["file"]) as pdf:
        pdf[p["page"] - 1].get_pixmap(
            matrix=fitz.Matrix(3, 3), clip=fitz.Rect(rect), alpha=False
        ).save(target)
    return target


async def crop_page_bounded(
    evidence: Evidence,
    page_id: str,
    rect: list[float],
    cancel,
    *,
    timeout: float = 1200,
) -> Path:
    """Isolate native PDF rendering so deadline/cancel can actually stop it.

    Only this host-owned script is executed. A killed renderer cannot leave a
    partial crop at the published evidence path or overwrite an existing crop.
    """
    import os
    import sys
    import tempfile
    from .repository import run_tool

    with tempfile.TemporaryDirectory(
        prefix=".crop-", dir=evidence.workspace
    ) as temporary:
        (Path(temporary) / "pages").mkdir()
        payload = {
            "workspace": temporary,
            "pages": [p for p in evidence.pages if p["id"] == page_id],
            "page_id": page_id,
            "rect": rect,
        }
        await run_tool(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--crop",
                json.dumps(payload),
            ],
            evidence.workspace,
            cancel,
            timeout=timeout,
        )
        result = json.loads((Path(temporary) / "result.json").read_text())
        staged = Path(temporary) / "pages" / result["name"]
        if staged.parent != Path(temporary) / "pages" or not staged.is_file():
            raise ValueError("Invalid crop worker output")
        destination = evidence.workspace / "pages" / staged.name
        os.replace(staged, destination)
        return destination


def _canonical_primitives(entity):
    """Exact primitive decoding for comparison only; never creates delivery geometry."""
    doc = ezdxf.new()
    msp = doc.modelspace()
    kind = entity["type"]
    if kind == "LINE":
        return [msp.add_line(entity["start"], entity["end"])]
    if kind == "CIRCLE":
        return [msp.add_circle(entity["center"], entity["radius"])]
    if kind == "ARC":
        return [
            msp.add_arc(
                entity["center"],
                entity["radius"],
                entity["start_angle"],
                entity["end_angle"],
            )
        ]
    if kind == "LWPOLYLINE":
        return list(
            msp.add_lwpolyline(
                entity["vertices"], format="xyb", close=entity.get("closed", False)
            ).virtual_entities()
        )
    if kind == "POINT":
        return [msp.add_point(entity["point"])]
    raise ValueError("Unsupported canonical physical comparison: " + kind)


def _raw_primitives(entity):
    if entity.get("unsupported"):
        raise ValueError("Unsupported source curve cannot receive physical PASS")
    if "physical" in entity:
        return [p for child in entity["physical"] for p in _raw_primitives(child)]
    result = _canonical_primitives(entity)
    if entity["type"] in ("ARC", "CIRCLE"):
        for e in result:
            e.dxf.extrusion = entity.get("extrusion", [0, 0, 1])
    return result


def _physical_signature(entity):
    """Orientation-independent endpoints plus exact arc midpoint/sweep geometry."""
    import math

    kind = entity.dxftype()

    def pt(point):
        return tuple(round(float(v), 6) for v in point)

    if kind == "LINE":
        return (kind, tuple(sorted((pt(entity.dxf.start), pt(entity.dxf.end)))))
    if kind == "CIRCLE":
        return (
            kind,
            pt(entity.ocs().to_wcs(entity.dxf.center)),
            round(entity.dxf.radius, 6),
        )
    if kind == "ARC":
        sweep = (entity.dxf.end_angle - entity.dxf.start_angle) % 360
        middle = list(entity.vertices([entity.dxf.start_angle + sweep / 2]))[0]
        return (
            kind,
            pt(entity.ocs().to_wcs(entity.dxf.center)),
            round(entity.dxf.radius, 6),
            tuple(sorted((pt(entity.start_point), pt(entity.end_point)))),
            pt(middle),
            round(sweep, 6),
        )
    if kind == "POINT":
        return (kind, pt(entity.dxf.location))
    raise ValueError("Unsupported physical signature")


def check_data_provenance(part, drawings, scoped_ids, routed_paths, page_ids):
    """Bidirectional DATA accounting and exact untouched physical comparison.

    Changed scopes must carry actual before/after signatures, a routed rule and
    source evidence; their engineering meaning is separately challenged by QA.
    """
    import math
    from ezdxf.math import Matrix44

    if not scoped_ids:
        return
    records = part.get("data_provenance")
    if not isinstance(records, list):
        raise ValueError("DATA_PROVENANCE_REQUIRED")
    raw = {d["id"] + "#" + str(e["id"]): e for d in drawings for e in d["entities"]}
    if {r.get("source_id") for r in records} != set(scoped_ids) or len(records) != len(
        scoped_ids
    ):
        raise ValueError("RAW_DATA_SNAPSHOT_INCOMPLETE")
    canonical = {e["entity_id"]: e for e in part["entities"] if e["type"] != "TEXT"}
    covered = set()
    for record in records:
        ids = record.get("canonical_entity_ids", [])
        if not set(ids) <= set(canonical) or covered.intersection(ids):
            raise ValueError("DATA_CANONICAL_OWNERSHIP")
        covered.update(ids)
        refs = record.get("evidence_refs", [])
        if not refs or not set(refs) <= set(page_ids):
            raise ValueError("DATA_SCOPE_EVIDENCE_REQUIRED")
        disposition = record.get("disposition")
        if disposition in ("DRAWING_ONLY", "CANCELED", "UNRESOLVED"):
            if ids or not record.get("reason"):
                raise ValueError("DATA_EXCLUSION_SCOPE_REQUIRED")
            if disposition == "UNRESOLVED" and part["status"] == "PASS":
                raise ValueError("UNRESOLVED_DATA_CANNOT_PASS")
            continue
        source = _raw_primitives(raw[record["source_id"]])
        transform = record.get("transform", {})
        scale = transform.get("scale")
        rotation = transform.get("rotation_deg")
        translation = transform.get("translation")
        if (
            type(scale) not in (int, float)
            or not math.isfinite(scale)
            or scale <= 0
            or type(rotation) not in (int, float)
            or not math.isfinite(rotation)
            or not isinstance(translation, list)
            or len(translation) != 2
            or not all(
                type(v) in (int, float) and math.isfinite(v) for v in translation
            )
        ):
            raise ValueError("DATA_PROVED_TRANSFORM_REQUIRED")
        if transform.get("reflect_x") not in (None, False, True):
            raise ValueError("Invalid reflection")
        matrix = Matrix44.chain(
            Matrix44.scale(
                -scale if transform.get("reflect_x") else scale, scale, scale
            ),
            Matrix44.z_rotate(math.radians(rotation)),
            Matrix44.translate(*translation, 0),
        )
        for e in source:
            e.transform(matrix)
        before = sorted((_physical_signature(e) for e in source), key=repr)
        target = [e for id in ids for e in _canonical_primitives(canonical[id])]
        after = sorted((_physical_signature(e) for e in target), key=repr)
        if disposition == "UNCHANGED":
            if before != after:
                raise ValueError("UNTOUCHED_DATA_INVARIANCE_FAIL")
        elif disposition == "MANUFACTURING_CANONICALIZED":
            # A change is scoped at the physical primitive level. Untouched curves
            # outside that scope still require exact equality, never bbox matching.
            changes = record.get("changes")
            if not isinstance(changes, list) or not changes:
                raise ValueError("MANUFACTURING_CHANGE_LEDGER_REQUIRED")
            left = list(before)
            right = list(after)
            for change in changes:
                if (
                    change.get("controlling_rule") not in routed_paths
                    or not change.get("source_evidence")
                    or not change.get("same_parameter_gate_status")
                    in ("PASS", "CUSTOMER_EXCEPTION")
                ):
                    raise ValueError("UNAPPROVED_DATA_CHANGE")
                for key, actual in [("before", left), ("after", right)]:
                    for signature in change.get(key, []):
                        match = next(
                            (
                                v
                                for v in actual
                                if json.loads(json.dumps(v)) == signature
                            ),
                            None,
                        )
                        if match is None:
                            raise ValueError("MANUFACTURING_CHANGE_SIGNATURE_MISMATCH")
                        actual.remove(match)
                if not change.get("before") or not change.get("after"):
                    raise ValueError("EMPTY_MANUFACTURING_CHANGE_SCOPE")
            if left != right:
                raise ValueError("UNTOUCHED_DATA_INVARIANCE_FAIL")
        else:
            raise ValueError("Unknown DATA disposition")
    if covered != set(canonical):
        raise ValueError("CANONICAL_TO_SOURCE_PHYSICAL_INCOMPLETE")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3 or sys.argv[1] != "--crop":
        raise SystemExit("Host crop worker requires --crop payload")
    payload = json.loads(sys.argv[2])
    result = crop_page(
        Evidence(Path(payload["workspace"]), payload["pages"], []),
        payload["page_id"],
        payload["rect"],
    )
    (Path(payload["workspace"]) / "result.json").write_text(
        json.dumps({"name": result.name})
    )
