import sys
from pathlib import Path

import ezdxf
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "services" / "trainaicad-mcp" / "bridge"))

from dxf_bridge import compare_physical_document  # noqa: E402
from export_dxf import export_job  # noqa: E402


CHECKS = {
    "contour_topology": "PASS", "datum": "PASS", "feature_count": "PASS", "unfold": "PASS",
    "containment": "PASS", "bend_domain": "PASS", "material_rules": "PASS", "slot_semantics": "PASS"
}


def part(code, shift=0):
    def x(value):
        return value + shift
    return {
        "code": code, "material": "SS400", "thickness_mm": 2, "status": "PASS", "checks": CHECKS,
        "entities": [
            {"type": "LWPOLYLINE", "role": "outer", "closed": True, "vertices": [[x(0), 0, 0], [x(20), 0, 0], [x(20), 20, 0], [x(0), 20, 0]]},
            {"type": "CIRCLE", "role": "hole", "center": [x(5), 5], "radius": 2},
            {"type": "LWPOLYLINE", "role": "slot", "closed": True, "vertices": [[x(2), 4, 0], [x(2), 6, 0], [x(8), 6, 0], [x(8), 4, 0]]},
            {"type": "LINE", "role": "relief", "color": 3, "start": [x(2), 2], "end": [x(3), 2]},
            {"type": "ARC", "role": "relief", "color": 3, "center": [x(4), 4], "radius": 0.5, "start_angle": 0, "end_angle": 90},
            {"type": "LINE", "role": "bend", "linetype": "DASHED", "start": [x(10), 0], "end": [x(10), 20]},
            {"type": "LINE", "role": "kegaki", "color": 1, "start": [x(1), 10], "end": [x(4), 10]},
            {"type": "POINT", "role": "through_piercing", "color": 3, "point": [x(15), 15]}
        ]
    }


@pytest.fixture
def written_composite(tmp_path):
    payload = {"job_id": "READBACK", "parts": [part("A"), part("B", 30)]}
    manifest = export_job(payload, tmp_path, mode="single", write_manifest=True)
    target = tmp_path / manifest["filename"]
    manifest_path = tmp_path / "READBACK_MANIFEST.json"
    return target, payload, manifest, manifest_path


def test_physical_readback_accepts_unmutated_composite(written_composite):
    target, payload, manifest, _ = written_composite
    result = compare_physical_document(ezdxf.readfile(target), payload, manifest)
    assert result["physical_geometry_match"] is True
    assert result["code_order_match"] is True
    assert result["compared_entity_count"] == 18
    assert result["labels"][:2] == ["A", "B"]


@pytest.mark.parametrize("mutation", [
    "delete_feature", "move_feature", "change_radius", "change_bulge", "delete_slit",
    "change_bend", "wrong_layer", "wrong_color", "wrong_linetype", "wrong_label", "wrong_code_order"
])
def test_physical_readback_rejects_geometry_and_semantic_mutations(written_composite, mutation):
    target, payload, manifest, _ = written_composite
    doc = ezdxf.readfile(target)
    msp = doc.modelspace()
    circles = list(msp.query("CIRCLE"))
    polylines = list(msp.query("LWPOLYLINE"))
    lines = list(msp.query("LINE"))
    texts = list(msp.query('TEXT[layer=="AI_META"]'))

    if mutation == "delete_feature":
        msp.delete_entity(circles[0])
    elif mutation == "move_feature":
        circles[0].dxf.center = (circles[0].dxf.center.x + 1, circles[0].dxf.center.y, 0)
    elif mutation == "change_radius":
        circles[0].dxf.radius += 0.25
    elif mutation == "change_bulge":
        points = list(polylines[1].get_points("xyb"))
        points[0] = (points[0][0], points[0][1], 0.5)
        polylines[1].set_points(points, format="xyb")
    elif mutation == "delete_slit":
        relief = next(entity for entity in msp.query("ARC") if entity.dxf.layer == "0")
        msp.delete_entity(relief)
    elif mutation == "change_bend":
        bend = next(entity for entity in lines if entity.dxf.get("linetype") == "DASHED")
        bend.dxf.start = (bend.dxf.start.x + 1, bend.dxf.start.y, 0)
    elif mutation == "wrong_layer":
        doc.layers.new("WRONG")
        list(msp.query('LWPOLYLINE[layer=="0"]'))[0].dxf.layer = "WRONG"
    elif mutation == "wrong_color":
        circles[0].dxf.color = 1
    elif mutation == "wrong_linetype":
        next(entity for entity in lines if entity.dxf.get("linetype") == "DASHED").dxf.linetype = "BYLAYER"
    elif mutation == "wrong_label":
        texts[0].dxf.text = "WRONG"
    elif mutation == "wrong_code_order":
        texts[0].dxf.text, texts[-1].dxf.text = texts[-1].dxf.text, texts[0].dxf.text
    else:
        raise AssertionError(mutation)

    with pytest.raises(ValueError, match="PHYSICAL_READBACK_(GEOMETRY|LABEL|CODE|AI_META)"):
        compare_physical_document(doc, payload, manifest)


def test_physical_readback_catches_saved_file_edit_after_a_prior_pass(written_composite):
    target, payload, manifest, _ = written_composite
    assert compare_physical_document(ezdxf.readfile(target), payload, manifest)["physical_geometry_match"]
    doc = ezdxf.readfile(target)
    list(doc.modelspace().query("CIRCLE"))[0].dxf.radius += 1
    doc.saveas(target)
    with pytest.raises(ValueError, match="PHYSICAL_READBACK_GEOMETRY_MISMATCH"):
        compare_physical_document(ezdxf.readfile(target), payload, manifest)
