import hashlib
import sys
from pathlib import Path

import ezdxf
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "trainaicad-mcp" / "bridge"))

from source_dxf_harvest import harvest_data_dxf  # noqa: E402


def save_fixture(path: Path, *, array=False):
    doc = ezdxf.new("R2018")
    doc.header["$INSUNITS"] = 4
    model = doc.modelspace()
    line = model.add_line((1.125, 2.25, 0), (7.5, 8.75, 0), dxfattribs={"layer": "CUT"})
    circle = model.add_circle((3.1, 4.2, 0), 1.7, dxfattribs={"layer": "HOLES"})
    arc = model.add_arc((5, 6, 0), 2.5, 17.25, 233.75)
    poly = model.add_lwpolyline([(0, 0, 0, 0, 0.41421356237309503), (2, 0, 0, 0, 0)], format="xyseb", close=True)
    point = model.add_point((9, 10, 0))
    spline = model.new_entity("SPLINE", {})
    spline.set_open_uniform([(0, 1, 0), (2, 4, 0), (6, 2, 0)], degree=2)
    ellipse = model.add_ellipse((11, 12, 0), major_axis=(4, 0, 0), ratio=0.625,
                               start_param=0.2, end_param=4.8)
    unsupported = model.add_hatch()

    block = doc.blocks.new("CUT_BLOCK")
    block_line = block.add_line((0, 0), (3, 0), dxfattribs={"layer": "0"})
    insert = model.add_blockref("CUT_BLOCK", (20, 30), dxfattribs={"layer": "INSERT_LAYER"})
    insert.dxf.rotation = 90
    insert.dxf.xscale = 2
    insert.dxf.yscale = 2
    if array:
        insert.dxf.row_count = 2
        insert.dxf.row_spacing = 5

    doc.saveas(path)
    return {"line": line.dxf.handle, "circle": circle.dxf.handle, "arc": arc.dxf.handle,
            "poly": poly.dxf.handle, "point": point.dxf.handle, "spline": spline.dxf.handle,
            "ellipse": ellipse.dxf.handle, "unsupported": unsupported.dxf.handle,
            "insert": insert.dxf.handle, "block_line": block_line.dxf.handle}


def test_harvest_preserves_geometry_provenance_and_insert_transform(tmp_path):
    path = tmp_path / "source.dxf"
    handles = save_fixture(path)
    raw = path.read_bytes()
    result = harvest_data_dxf(path)

    assert result["schema"] == "TRAINSOURCE_GEOMETRY_LEDGER_V1"
    assert result["sourceSha256"] == hashlib.sha256(raw).hexdigest()
    assert result["declaredUnits"] == "mm"
    assert result["scaleStatus"] == "UNPROVED"  # INSUNITS alone is not physical proof
    assert "DXF_PHYSICAL_SCALE_UNPROVED" in result["flags"]
    by_handle = {entity["sourceHandle"]: entity for entity in result["entities"]}

    assert by_handle[handles["line"]]["geometry"] == {
        "start": {"x": 1.125, "y": 2.25, "z": 0.0},
        "end": {"x": 7.5, "y": 8.75, "z": 0.0},
        "thickness": 0.0, "extrusion": [0.0, 0.0, 1.0],
    }
    assert by_handle[handles["circle"]]["geometry"]["radius"] == 1.7
    assert by_handle[handles["arc"]]["geometry"]["startAngleDeg"] == 17.25
    vertices = by_handle[handles["poly"]]["geometry"]["vertices"]
    assert vertices[0]["bulge"] == pytest.approx(0.41421356237309503)
    assert by_handle[handles["spline"]]["geometry"]["controlPoints"] == [
        {"x": 0.0, "y": 1.0, "z": 0.0},
        {"x": 2.0, "y": 4.0, "z": 0.0},
        {"x": 6.0, "y": 2.0, "z": 0.0},
    ]
    assert by_handle[handles["ellipse"]]["geometry"]["ratio"] == 0.625

    block_child = by_handle[handles["block_line"]]
    assert block_child["effectiveLayer"] == "INSERT_LAYER"
    assert block_child["insertChain"] == [{"insertHandle": handles["insert"], "blockName": "CUT_BLOCK"}]
    assert block_child["transform4x4"][3][:2] == pytest.approx([20, 30])
    assert block_child["transform4x4"][0][:2] == pytest.approx([0, 2])
    assert block_child["transform4x4"][1][:2] == pytest.approx([-2, 0])
    assert by_handle[handles["insert"]]["geometry"]["blockName"] == "CUT_BLOCK"

    assert by_handle[handles["unsupported"]]["retained"] is False
    assert by_handle[handles["unsupported"]]["geometry"] is None
    assert result["unsupportedEntities"] == [{
        "handle": handles["unsupported"], "entityType": "HATCH", "layer": "0", "layout": "Model",
    }]
    assert any(flag.startswith("UNSUPPORTED_DXF_ENTITY:HATCH:") for flag in result["flags"])
    assert result["semanticRefitApplied"] is False
    assert result["status"] == "REVIEW_REQUIRED"


def test_insert_array_expands_every_instance_with_its_own_transform(tmp_path):
    path = tmp_path / "array.dxf"
    handles = save_fixture(path, array=True)
    result = harvest_data_dxf(path)
    children = [entity for entity in result["entities"]
                if entity["sourceHandle"] == handles["block_line"]]
    assert len(children) == 2
    assert {item["insertChain"][0]["arrayInstance"] for item in children} == {"0", "1"}
    offsets = {tuple(round(value, 6) for value in item["transform4x4"][3][:2]) for item in children}
    assert len(offsets) == 2
    assert not any(flag.startswith(f"INSERT_ARRAY_NOT_EXPANDED:{handles['insert']}")
                   for flag in result["flags"])
    assert result["status"] == "REVIEW_REQUIRED"


def test_insert_array_over_limit_is_hard_flagged_without_claiming_expansion(tmp_path):
    path = tmp_path / "huge_array.dxf"
    handles = save_fixture(path, array=True)
    doc = ezdxf.readfile(path)
    insert = doc.entitydb[handles["insert"]]
    insert.dxf.row_count = 101
    insert.dxf.column_count = 100
    doc.saveas(path)
    result = harvest_data_dxf(path)
    assert f"INSERT_ARRAY_EXPANSION_LIMIT:{handles['insert']}:10100" in result["flags"]
    children = [entity for entity in result["entities"]
                if entity["sourceHandle"] == handles["block_line"]]
    assert children == []
    assert result["status"] == "REVIEW_REQUIRED"


def test_real_acute_bend_regression_dxf_census_is_honest_about_scale():
    path = ROOT / "regression" / "assets" / "acute_bend_lt85" / "ACUTE_BEND_LT85_SOURCE_FIXTURE.dxf"
    result = harvest_data_dxf(path)
    assert result["sourceSha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert result["entities"]
    assert result["status"] == "REVIEW_REQUIRED"
    assert "DXF_PHYSICAL_SCALE_UNPROVED" in result["flags"]
