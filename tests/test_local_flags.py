"""Local FLAG (521023-09 directive): only the flagged entity is Magenta; notes are white AI_META text (code, FLAG at the right,
dx / HL at the left); no 'Ước lượng' note TEXT; a DATA/PDF difference paints only its own R / C / hole / slot."""
import json
import sys
from pathlib import Path

import ezdxf
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_canonical as bc  # noqa: E402
import data_part  # noqa: E402
import dxf_assemble  # noqa: E402
import dxf_digest  # noqa: E402
from export_canonical_dxf import export_canonical_job  # noqa: E402

MAGENTA = 6


def _spec(**over):
    part = {"code": "26-000100", "material": "SPCC", "t": 2, "page": 1, "envelope": [200, 100],
            "outline": [[0, 0, {"C": 5, "group": "C5", "qty": 2, "ev": "p1 2-C5"}],
                        [200, 0, {"R": 10, "FLAG": "R10 khác PDF", "group": "R10", "qty": 1, "ev": "p1 R10"}],
                        [200, 100, {"C": 5, "group": "C5", "ev": "p1 2-C5"}], [0, 100, {"SHARP": "ピン角"}]],
            "holes": [{"id": "H1", "d": 8, "group": "D8", "qty": 2, "ev": "p1 2-Ø8", "flag": "2-M8 hay 4 lỗ?",
                       "wx": [[50, "HOLE_CENTER", "p1 50"]], "wy": [[50, "HOLE_CENTER", "p1 50"]]},
                      {"id": "H2", "d": 8, "group": "D8", "flag": "2-M8 hay 4 lỗ?",
                       "wx": [[150, "HOLE_CENTER", "p1 150"]], "wy": [[50, "HOLE_CENTER", "p1 50"]]},
                      {"id": "H3", "d": 6, "group": "D6", "qty": 1, "ev": "p1 Ø6",
                       "wx": [[100, "HOLE_CENTER", "p1 100"]], "wy": [[20, "HOLE_CENTER", "p1 20"]]}],
            "slots": [{"id": "S1", "w": 8, "cd": 12, "axis": [0, 1], "group": "SL", "qty": 2, "ev": "p1 slots",
                       "flag": "lỗ dài lệch PDF",
                       "wx": [[30, "SLOT_MIDPOINT", "p1 30"]], "wy": [[70, "SLOT_MIDPOINT", "p1 70"]]},
                      {"id": "S2", "w": 8, "cd": 12, "axis": [0, 1], "group": "SL", "ev": "p1 slots",
                       "wx": [[170, "SLOT_MIDPOINT", "p1 170"]], "wy": [[70, "SLOT_MIDPOINT", "p1 70"]]}]}
    part.update(over)
    return part


def _export(tmp_path, spec, tweak=None):
    job = bc.build_job({"job_id": "LF", "parts": [spec]})
    if tweak:
        tweak(job["parts"][0])
    manifest = export_canonical_job(job, tmp_path, require_slip_codes=False)
    return job["parts"][0], ezdxf.readfile(tmp_path / manifest["filename"])


def _geom(doc):
    return [e for e in doc.modelspace() if e.dxf.layer == "0"]


def test_only_the_flagged_entities_are_magenta(tmp_path):
    part, doc = _export(tmp_path, _spec())
    assert part["status"] == "PREVIEW" and part["entities"][0].get("color", 256) == 256
    magenta = [e for e in _geom(doc) if e.dxf.get("color", 256) == MAGENTA]
    assert sorted(e.dxftype() for e in magenta).count("CIRCLE") == 2          # H1, H2 (not H3)
    assert all(e.dxftype() in ("CIRCLE", "ARC", "LINE") for e in magenta)
    outline_arcs = [e for e in magenta if e.dxftype() == "ARC" and abs(e.dxf.radius - 10) < 1e-6]
    assert len(outline_arcs) == 1                                            # the flagged R10, one piece of the outline
    ordinary = [e for e in _geom(doc) if e.dxf.get("color", 256) == 256]
    assert any(e.dxftype() == "LINE" for e in ordinary) and any(e.dxftype() == "CIRCLE" for e in ordinary)   # H3, the rest of the outline
    slot_pieces = [e for e in magenta if e.dxftype() == "LINE" and abs(e.dxf.start.x - 30) < 5]
    assert slot_pieces and not any(e.dxftype() == "LINE" and abs(e.dxf.start.x - 170) < 5 for e in magenta)    # S1 yes, S2 no


def test_no_estimate_note_and_every_note_is_white(tmp_path):
    part, doc = _export(tmp_path, _spec(dx_label=True))
    assert not any(e.get("role") == "estimated_note" for e in part["entities"])
    texts = [e for e in doc.modelspace() if e.dxftype() == "TEXT"]
    assert texts and all(e.dxf.color == 7 for e in texts)
    assert doc.layers.get("AI_META").dxf.color == 7
    assert not any("Ước lượng" in e.dxf.text for e in texts)
    body = [e.dxf.text for e in texts]
    assert body.count("26-000100") == 1 and "dx" in body                      # code only (no [FLAG] suffix)
    notes = [e for e in texts if e.dxf.layer == "AI_META"]
    flag_lines = [e for e in notes if e.dxf.text.startswith("FLAG: ")]
    assert {e.dxf.text for e in flag_lines} >= {"FLAG: 2-M8 hay 4 lỗ?", "FLAG: lỗ dài lệch PDF", "FLAG: R10 khác PDF"}
    assert all(e.dxf.insert.x > 200 for e in flag_lines)                      # at the right of the part
    dx = next(e for e in texts if e.dxf.text == "dx")
    assert dx.dxf.layer == "0" and dx.dxf.insert.x < 0                         # dx / HL: Layer 0, left of the part


def test_hairline_part_gets_an_hl_label_at_the_left(tmp_path):
    def hl(part):
        part["grain"] = {"is_hl": True, "direction_xy": [1, 0], "evidence_ref": "p1 arrow"}
    _, doc = _export(tmp_path, _spec(dx_label=True), hl)
    left = {e.dxf.text: e for e in doc.modelspace() if e.dxftype() == "TEXT" and e.dxf.text in ("dx", "HL")}
    assert set(left) == {"dx", "HL"} and all(e.dxf.insert.x < 0 and e.dxf.layer == "0" for e in left.values())
    assert left["HL"].dxf.insert.y < left["dx"].dxf.insert.y                   # stacked downward, never overlapping
    outline = [e for e in doc.modelspace() if e.dxf.layer == "0" and e.dxftype() == "LINE"]
    assert min(min(e.dxf.start.x, e.dxf.end.x) for e in outline) == 0          # the labels never move the part origin


def test_flag_with_nothing_to_point_at_is_a_note_only():
    part = bc.build_part({"code": "26-000101", "material": "SPCC", "t": 2, "page": 1, "envelope": [50, 50],
                          "flags": ["kích thước tổng chưa rõ"],
                          "outline": [[0, 0, {"SHARP": "x"}], [50, 0, {"SHARP": "x"}], [50, 50, {"SHARP": "x"}],
                                      [0, 50, {"SHARP": "x"}]]})
    assert part["status"] == "PREVIEW" and part["flags"] == ["kích thước tổng chưa rõ"]
    assert part["entities"][0].get("color", 256) == 256 and not any(e["type"] == "TEXT" for e in part["entities"])


# ---------------------------------------------------------------------------------------- DATA/PDF differences are local
def _assemble(tmp_path, name, dg, members):
    used = {i for m in members for i in m["pieces"]}
    rest = [p["id"] for p in dg["pieces"] if p["id"] not in used and not p.get("duplicate_of")]
    plan = {"members": members, "excluded": [{"reason": "OTHER", "note": "not harvested", "pieces": rest}]}
    out = tmp_path / name
    out.write_text(json.dumps(dxf_assemble.assemble(dg, plan)), encoding="utf-8")
    return str(out)


def _plate(tmp_path):
    doc = ezdxf.new("R2010", setup=True)
    msp = doc.modelspace()
    for a, b in (((0, 0), (100, 0)), ((100, 0), (100, 60)), ((100, 60), (0, 60)), ((0, 60), (0, 0))):
        msp.add_line(a, b)
    msp.add_circle((20, 30), 4)                       # DATA Ø8 (a PDF Ø6 makes this one a local FLAG)
    msp.add_circle((60, 30), 4)
    for xx in (40.0, 80.7):                           # vertical stadium slots W6, centre distance 10; the right one sits at 80.7
        msp.add_line((xx - 3, 25), (xx - 3, 35))
        msp.add_line((xx + 3, 25), (xx + 3, 35))
        msp.add_arc((xx, 35), 3, 0, 180)
        msp.add_arc((xx, 25), 3, 180, 360)
    path = tmp_path / "plate.dxf"
    doc.saveas(path)
    dg = dxf_digest.digest(str(path))

    def line(a, b):
        return next(p["id"] for p in dg["pieces"] if p["type"] == "LINE" and
                    {tuple(round(c, 3) for c in p["start"]), tuple(round(c, 3) for c in p["end"])} == {a, b})

    def circle(c):
        return next(p["id"] for p in dg["pieces"] if p["type"] == "CIRCLE" and tuple(round(v, 3) for v in p["center"]) == c)

    def at(p):
        return (p.get("start") or p["center"])[0]

    slot_pieces = [p for p in dg["pieces"] if p["type"] in ("LINE", "ARC") and 20 < (p.get("start") or p["center"])[1] < 40
                   and 30 < at(p) < 90]
    members = [{"id": "L", "role": "datum", "pieces": [line((0.0, 0.0), (0.0, 60.0))]},
               {"id": "R", "role": "datum", "pieces": [line((100.0, 0.0), (100.0, 60.0))]},
               {"id": "B", "role": "datum", "pieces": [line((0.0, 0.0), (100.0, 0.0))]},
               {"id": "T", "role": "datum", "pieces": [line((0.0, 60.0), (100.0, 60.0))]},
               {"id": "H1", "role": "hole", "pieces": [circle((20.0, 30.0))]},
               {"id": "H2", "role": "hole", "pieces": [circle((60.0, 30.0))]},
               {"id": "S1", "role": "slot", "pieces": [p["id"] for p in slot_pieces if at(p) < 60]},
               {"id": "S2", "role": "slot", "pieces": [p["id"] for p in slot_pieces if at(p) >= 60]}]
    return _assemble(tmp_path, "plate.json", dg, members)


def _data_spec(tmp_path, **members):
    return {"code": "26-000110", "material": "SPCC", "t": 2, "page": 1, "envelope": [100, 60],
            "data_views": [{"data": _plate(tmp_path), "origin": ["L.min.x", "B.min.y"], "members": members}],
            "outline": [["L.min.x", "B.min.y"], ["R.min.x", "B.min.y"], ["R.min.x", "T.min.y"], ["L.min.x", "T.min.y"]]}


def _members(**over):
    base = {"H1": {"group": "D", "ev": "p1 Ø8", "pdf_d": 8}, "H2": {"group": "D", "ev": "p1 Ø8", "pdf_d": 8},
            "S1": {"group": "S", "ev": "p1 slot"}, "S2": {"group": "S", "ev": "p1 slot"}}
    base.update(over)
    return base


def test_hole_diameter_difference_flags_only_that_hole(tmp_path):
    part = bc.build_part(_data_spec(tmp_path, **_members(H1={"group": "D", "ev": "p1 Ø6", "pdf_d": 6})))
    magenta = [e["entity_id"] for e in part["entities"] if e.get("color") == MAGENTA]
    assert magenta == ["E_26-000110_H1"] and part["entities"][0].get("color", 256) == 256
    assert any("H1" in f and "DATA_PDF_DIM_DIFF" in f for f in part["flags"])


def test_slot_position_difference_flags_only_that_slot(tmp_path):
    members = _members(S1={"group": "S", "ev": "p1 slot", "pdf_pos": [{"from": "L.min.x", "axis": "x", "pdf": 40}]},
                       S2={"group": "S", "ev": "p1 slot",
                           "pdf_pos": [{"from": "L.min.x", "axis": "x", "pdf": 80, "label": "lỗ dài phải X"}]})
    spec = _data_spec(tmp_path, **members)
    part = bc.build_part(spec)
    assert [e["entity_id"] for e in part["entities"] if e.get("color") == MAGENTA] == ["E_26-000110_S2"]   # DATA 80.7 vs PDF 80
    assert any("lỗ dài phải X" in f for f in part["flags"])
    spec["data_views"][0]["members"]["S1"]["pdf_pos"] = [{"from": "L.min.x", "axis": "x"}]
    with pytest.raises(bc.BuildError, match="needs from"):
        bc.build_part(spec)


def test_corner_radius_difference_paints_only_that_arc(tmp_path):
    doc = ezdxf.new("R2010", setup=True)
    msp = doc.modelspace()
    for a, b in (((5, 0), (40, 0)), ((40, 0), (40, 30)), ((40, 30), (0, 30)), ((0, 30), (0, 5))):
        msp.add_line(a, b)
    msp.add_arc((5, 5), 5, 180, 270)
    path = tmp_path / "corner.dxf"
    doc.saveas(path)
    dg = dxf_digest.digest(str(path))
    by_ends = {frozenset((tuple(round(c) for c in p["start"]), tuple(round(c) for c in p["end"]))): p["id"]
               for p in dg["pieces"] if p["type"] == "LINE"}
    members = [{"id": "RC", "role": "datum", "pieces": [next(p["id"] for p in dg["pieces"] if p["type"] == "ARC")]},
               {"id": "B", "role": "datum", "pieces": [by_ends[frozenset({(5, 0), (40, 0)})]]},
               {"id": "R", "role": "datum", "pieces": [by_ends[frozenset({(40, 0), (40, 30)})]]},
               {"id": "T", "role": "datum", "pieces": [by_ends[frozenset({(0, 30), (40, 30)})]]},
               {"id": "L", "role": "datum", "pieces": [by_ends[frozenset({(0, 5), (0, 30)})]]}]
    spec = {"code": "26-000120", "material": "SPCC", "t": 2, "page": 1, "envelope": [40, 30],
            "data_views": [{"data": _assemble(tmp_path, "corner.json", dg, members), "origin": ["L.min.x", "B.min.y"], "members": {}}],
            "outline": [["L.min.x", "B.min.y", {"R": "RC.radius", "pdf_R": 6, "group": "R6", "ev": "p1 R6"}],
                        ["R.min.x", "B.min.y"], ["R.min.x", "T.min.y"], ["L.min.x", "T.min.y"]]}
    part = bc.build_part(spec)
    outer = part["entities"][0]
    assert outer.get("color", 256) == 256 and len(outer["flag_segments"]) == 1
    assert outer["vertices"][outer["flag_segments"][0]][2] != 0               # the flagged piece is the arc (R5 in DATA, R6 on the PDF)
    assert any("DATA_PDF_DIM_DIFF" in f and "R" in f for f in part["flags"])
    spec["outline"][0][2]["pdf_R"] = 5
    assert "flag_segments" not in bc.build_part(spec)["entities"][0]
