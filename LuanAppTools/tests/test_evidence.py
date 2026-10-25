"""Synthetic drawings only: physical evidence and actual pinned CAD tools."""

from pathlib import Path
import asyncio
import ezdxf
import fitz
import pytest
from LuanAppTools.cad.evidence import prepare_evidence, crop_page, crop_page_bounded
from LuanAppTools.cad.repository import PinnedRepository, CadError

ROOT = Path(__file__).resolve().parents[2]


def test_pdf_overviews_crops_and_physical_bulges(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    pdf = fitz.open()
    p = pdf.new_page(width=200, height=100)
    p.insert_text((10, 30), "SYNTHETIC 26-000001")
    pdf.save(source / "drawing.pdf")
    pdf.close()
    d = ezdxf.new()
    d.units = 4
    d.modelspace().add_lwpolyline([(0, 0, 1), (10, 0, 0)], format="xyb")
    d.modelspace().add_spline([(0, 0), (2, 4), (4, 0)])
    b = d.blocks.new("B")
    b.add_circle((0, 0), 2)
    d.modelspace().add_blockref("B", (20, 10), dxfattribs={"rotation": 90})
    d.saveas(source / "data.dxf")
    ev = prepare_evidence(source, tmp_path / "work")
    assert len(ev.pages) == 1 and ev.pages[0]["id"] == "drawing.pdf:p1"
    assert Path(ev.pages[0]["image"]).exists()
    curves = ev.dxf[0]["entities"]
    poly = next(e for e in curves if e["type"] == "LWPOLYLINE")
    assert poly["vertices"][0][2] == 1
    assert poly["physical"][0]["type"] == "ARC"
    assert any(e["type"] == "SPLINE" and e["unsupported"] for e in curves)
    block = next(e for e in curves if e["type"] == "INSERT")
    assert block["physical"][0]["center"] == [20.0, 10.0, 0.0]
    assert ev.dxf[0]["units"] == 4
    crop = crop_page(ev, "drawing.pdf:p1", [0, 0, 100, 50])
    assert crop.exists()
    bounded = asyncio.run(
        crop_page_bounded(
            ev, "drawing.pdf:p1", [0, 0, 100, 50], asyncio.Event(), timeout=10
        )
    )
    pixmap = fitz.Pixmap(str(bounded))
    assert (pixmap.width, pixmap.height) == (300, 150)
    assert not list(ev.workspace.glob(".crop-*"))
    with pytest.raises(ValueError):
        crop_page(ev, "drawing.pdf:p1", [-10, 0, 100, 50])


def test_pinned_commit_uses_real_resolver_and_rejects_tamper(tmp_path):
    repo = PinnedRepository.pin(ROOT, tmp_path / "repo")
    assert len(repo.commit) == 40 and repo.contract == "TrainAiCad-CANONICAL-V4.34"
    census = {
        "source_mode": "PDF_ONLY",
        "part_mode": "FLAT_NO_BEND",
        "reference_present": "NO",
        "multi_code_or_assembly": "NO",
        "features": {key: "NO" for key in repo.router["feature_routes"]},
    }
    census["features"]["HOLE"] = "UNKNOWN"
    route = asyncio.run(repo.resolve(census, tmp_path / "work", asyncio.Event()))
    assert "HOLE" in route["selected_features"]
    text = repo.stage_text(route, "L2_GEOMETRY")
    assert "HOLES_TAPS.md" in text
    (repo.root / "AI_ENTRYPOINT.md").write_text("tampered")
    with pytest.raises(CadError, match="changed"):
        repo.verify()


def test_data_reprojection_preserves_arcs_and_rejects_drift(tmp_path):
    from LuanAppTools.cad.evidence import check_data_provenance, physical_entity

    d = ezdxf.new()
    e = d.modelspace().add_circle((10, 20), 3)
    raw = {"id": "data.dxf", "entities": [physical_entity(e)]}
    sid = "data.dxf#" + e.dxf.handle
    part = {
        "status": "PASS",
        "entities": [
            {
                "entity_id": "E",
                "type": "CIRCLE",
                "center": [10, 20],
                "radius": 3,
                "role": "hole",
            }
        ],
        "data_provenance": [
            {
                "source_id": sid,
                "disposition": "UNCHANGED",
                "canonical_entity_ids": ["E"],
                "transform": {"scale": 1, "rotation_deg": 0, "translation": [0, 0]},
                "evidence_refs": ["drawing.pdf:p1"],
            }
        ],
    }
    check_data_provenance(part, [raw], [sid], [], ["drawing.pdf:p1"])
    part["entities"][0]["radius"] = 3.1
    with pytest.raises(ValueError, match="INVARIANCE"):
        check_data_provenance(part, [raw], [sid], [], ["drawing.pdf:p1"])


def test_dxf_preview_is_rendered_from_actual_saved_file(tmp_path):
    from LuanAppTools.cad.preview import render_dxf

    d = ezdxf.new()
    d.modelspace().add_arc((0, 0), 5, 0, 90)
    d.saveas(tmp_path / "arc.dxf")
    result = render_dxf(tmp_path / "arc.dxf", tmp_path / "arc.svg")
    assert "<svg" in result.read_text() and result.stat().st_size > 100
