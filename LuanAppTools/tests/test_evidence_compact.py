"""Compact DATA evidence, host-computed DATA groups and the summary-only intake view."""

import asyncio
import json

import ezdxf
import fitz
import pytest

from LuanAppTools.ai.tools import HostTools, TOOL_DESCRIPTION
from LuanAppTools.cad.evidence import compact_entity, prepare_evidence


def _source(tmp_path, holes=0):
    source = tmp_path / "source"
    source.mkdir()
    pdf = fitz.open()
    pdf.new_page(width=200, height=100)
    pdf.save(source / "drawing.pdf")
    pdf.close()
    d = ezdxf.new(setup=True)  # defines the DASHED linetype so it survives save/load
    msp = d.modelspace()
    # Part A: outline with a hole. Part B: far outline crossed by a dashed line.
    msp.add_lwpolyline([(0, 0), (40, 0), (40, 20), (0, 20)], close=True, dxfattribs={"color": 3})
    msp.add_circle((20, 10), 4)
    msp.add_lwpolyline([(100, 0), (140, 0), (140, 20), (100, 20)], close=True)
    msp.add_line((100, 10), (140, 10), dxfattribs={"linetype": "DASHED"})
    msp.add_text("NOTE", dxfattribs={"insert": (300, 300), "height": 2})
    for i in range(holes):  # many holes inside part B
        msp.add_circle((105 + i * 0.5, 15), 0.2)
    d.saveas(source / "data.dxf")
    return source


def test_solve_entities_are_compact_and_raw_evidence_stays_intact(tmp_path):
    ev = prepare_evidence(_source(tmp_path), tmp_path / "work")
    raw = ev.dxf[0]["entities"]
    entities = [compact_entity(e) for e in raw]
    # Raw evidence keeps every DXF attribute for host-side provenance checks.
    assert "attributes" in raw[0]
    assert all("attributes" not in e for e in entities)
    outline = next(e for e in entities if e["type"] == "LWPOLYLINE")
    assert outline["layer"] == "0" and outline["color"] == 3 and outline["closed"] is True
    assert outline["vertices"][1] == [40.0, 0.0, 0.0]
    assert outline["physical"][0]["type"] == "LINE"
    assert "id" not in outline["physical"][0]  # child decode inherits the parent id
    dashed = next(e for e in entities if e["type"] == "LINE")
    assert dashed["linetype"] == "DASHED" and "color" not in dashed
    assert len(json.dumps(entities)) < 0.6 * len(json.dumps(raw))


def test_data_groups_cluster_touching_geometry_and_cover_every_entity(tmp_path):
    ev = prepare_evidence(_source(tmp_path), tmp_path / "work")
    groups = ev.dxf[0]["groups"]
    by_id = {g["id"]: g for g in groups}
    assert list(by_id) == ["data.dxf#G1", "data.dxf#G2", "data.dxf#G3"]
    assert sorted(len(g["entity_ids"]) for g in groups) == [1, 2, 2]  # note; outline+hole; outline+line
    every = [i for g in groups for i in g["entity_ids"]]
    assert len(every) == len(set(every)) == len(ev.dxf[0]["entities"])
    assert set(every) == {"data.dxf#" + e["id"] for e in ev.dxf[0]["entities"]}
    assert by_id["data.dxf#G1"]["bbox"] == [0.0, 0.0, 40.0, 20.0]


def test_intake_view_has_group_summaries_and_no_entity_geometry(tmp_path):
    ev = prepare_evidence(_source(tmp_path), tmp_path / "work")
    drawing = ev.intake_view()["dxf"][0]
    assert "entities" not in drawing and drawing["entity_count"] == 5
    assert drawing["id"] == "data.dxf" and drawing["units"] == ev.dxf[0]["units"]
    groups = {g["id"]: g for g in drawing["groups"]}
    first = groups["data.dxf#G1"]
    assert first["bbox"] == [0.0, 0.0, 40.0, 20.0] and first["count"] == 2
    assert first["types"] == {"LWPOLYLINE": 1, "CIRCLE": 1}
    assert first["layers"] == {"0": 2}
    assert [(c["center"], c["radius"]) for c in first["circles"]] == [([20.0, 10.0], 4.0)]
    assert first["circles"][0]["id"] in {e["id"] for e in ev.dxf[0]["entities"]}
    assert groups["data.dxf#G3"]["texts"][0]["text"] == "NOTE"
    assert "entity_ids" not in first and "vertices" not in json.dumps(drawing)


def test_intake_view_caps_listed_holes_but_reports_the_total(tmp_path):
    ev = prepare_evidence(_source(tmp_path, holes=30), tmp_path / "work")
    drawing = ev.intake_view()["dxf"][0]
    group = next(g for g in drawing["groups"] if g["types"].get("CIRCLE") == 30)
    assert len(group["circles"]) == 12 and group["circles_total"] == 30
    # A group can always be inspected in full through the host tool.
    assert group["count"] == 32


def test_intake_view_reports_unsupported_curves(tmp_path):
    source = _source(tmp_path)
    d = ezdxf.readfile(source / "data.dxf")
    d.modelspace().add_spline([(0, 0), (2, 4), (4, 0)])
    d.saveas(source / "data.dxf")
    drawing = prepare_evidence(source, tmp_path / "work").intake_view()["dxf"][0]
    assert sum(g.get("unsupported", {}).get("SPLINE", 0) for g in drawing["groups"]) == 1


def test_data_group_tool_returns_compact_entities_on_demand(tmp_path):
    ev = prepare_evidence(_source(tmp_path, holes=5), tmp_path / "work")
    tools = HostTools(None, ev, [], "JOB", asyncio.Event())
    biggest = next(g for g in ev.intake_view()["dxf"][0]["groups"] if g["count"] == 7)

    def call(**arguments):
        return asyncio.run(tools.execute({"name": "data_group", "arguments": {"group_id": biggest["id"], **arguments}}))[0]

    answer = call()
    assert answer["total"] == 7 and answer["offset"] == 0 and len(answer["entities"]) == 7
    assert all("attributes" not in e for e in answer["entities"])
    page = call(offset=5, limit=5)
    assert [e["id"] for e in page["entities"]] == [e["id"] for e in answer["entities"][5:]]
    with pytest.raises(ValueError):
        asyncio.run(tools.execute({"name": "data_group", "arguments": {"group_id": "data.dxf#G99"}}))
    with pytest.raises(ValueError):
        call(limit=100000)
    assert "data_group" in TOOL_DESCRIPTION
