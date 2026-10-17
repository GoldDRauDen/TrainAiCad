"""Compact model-facing DATA evidence and host-computed DATA groups (raw evidence stays intact)."""

import json

import ezdxf
import fitz

from LuanAppTools.cad.evidence import prepare_evidence


def _source(tmp_path):
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
    d.saveas(source / "data.dxf")
    return source


def test_prompt_evidence_is_compact_and_keeps_raw_evidence_intact(tmp_path):
    ev = prepare_evidence(_source(tmp_path), tmp_path / "work")
    prompt = ev.prompt()
    entities = prompt["dxf"][0]["entities"]
    assert len(entities) == len(ev.dxf[0]["entities"])
    # Raw evidence keeps every DXF attribute for host-side provenance checks.
    assert "attributes" in ev.dxf[0]["entities"][0]
    assert all("attributes" not in e for e in entities)
    outline = next(e for e in entities if e["type"] == "LWPOLYLINE")
    assert outline["layer"] == "0" and outline["color"] == 3 and outline["closed"] is True
    assert outline["vertices"][1] == [40.0, 0.0, 0.0]
    assert outline["physical"][0]["type"] == "LINE"
    assert "id" not in outline["physical"][0]  # child decode inherits the parent id
    dashed = next(e for e in entities if e["type"] == "LINE")
    assert dashed["linetype"] == "DASHED" and "color" not in dashed
    assert len(json.dumps(prompt["dxf"])) < 0.6 * len(json.dumps(ev.public()["dxf"]))


def test_data_groups_cluster_touching_geometry_and_cover_every_entity(tmp_path):
    ev = prepare_evidence(_source(tmp_path), tmp_path / "work")
    groups = ev.dxf[0]["groups"]
    by_id = {g["id"]: g for g in groups}
    assert list(by_id) == ["data.dxf#G1", "data.dxf#G2", "data.dxf#G3"]
    assert sorted(len(g["entity_ids"]) for g in groups) == [1, 2, 2]  # note; outline+hole; outline+line
    every = [i for g in groups for i in g["entity_ids"]]
    assert len(every) == len(set(every)) == len(ev.dxf[0]["entities"])
    assert set(every) == {"data.dxf#" + e["id"] for e in ev.dxf[0]["entities"]}
    first = by_id["data.dxf#G1"]
    assert first["bbox"] == [0.0, 0.0, 40.0, 20.0]
    # The prompt view tags each entity with its group and lists compact group summaries.
    prompt = ev.prompt()["dxf"][0]
    assert {g["id"] for g in prompt["groups"]} == set(by_id)
    assert all("entity_ids" not in g and g["count"] >= 1 for g in prompt["groups"])
    tagged = {e["id"]: e["group"] for e in prompt["entities"]}
    member = first["entity_ids"][0].split("#", 1)[1]
    assert tagged[member] == "data.dxf#G1"
