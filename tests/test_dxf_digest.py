"""tools/dxf_digest.py: every DATA primitive gets an id and exactly one home; nothing is dropped or altered."""
import json
import math
import sys
from pathlib import Path

import ezdxf
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import dxf_digest  # noqa: E402

Q = math.tan(math.radians(90) / 4)  # quarter-circle bulge


def _sheet(tmp_path, *, glyphs=True, layers=("0",)):
    """A mini customer sheet: frame, a 100x50 plate view with a bulged R3 corner + hole + tap pair,
    a second small view, exploded glyph noise, a dimension, an ELLIPSE, one duplicated line."""
    doc = ezdxf.new("R2010")
    for name in layers:
        if name not in doc.layers:
            doc.layers.add(name)
    msp = doc.modelspace()
    msp.add_lwpolyline([(0, 0), (400, 0), (400, 300), (0, 300)], close=True)               # sheet frame
    msp.add_lwpolyline([(50, 100, 0), (147, 100, Q), (150, 103, 0), (150, 150, 0), (50, 150, 0)],
                       format="xyb", close=True)                                              # plate, R3 corner
    msp.add_circle((70, 125), 3.3)                                                            # hole
    msp.add_circle((120, 125), 2.0)                                                           # tap nominal ring
    msp.add_circle((120, 125), 1.62)                                                          # tap pilot (concentric)
    msp.add_line((100, 95), (100, 155), dxfattribs={"linetype": "DASHDOT", "color": 1})       # centre line (isolated)
    msp.add_lwpolyline([(200, 100), (240, 100), (240, 120), (200, 120)], close=True)          # second view
    if glyphs:
        for k in range(6):                                                                   # exploded text: tiny LINE chains
            x = 300 + 3 * k
            msp.add_line((x, 50), (x + 1, 50))
            msp.add_line((x + 1, 50), (x + 1, 52))
    msp.add_line((60, 60), (80, 60))                                                          # duplicated pair
    msp.add_line((60, 60), (80, 60))
    msp.add_ellipse((260, 200), major_axis=(5, 0), ratio=0.5)                                 # unsupported curve
    msp.add_text("NOTE", dxfattribs={"insert": (10, 10), "height": 3})
    path = tmp_path / "sheet.dxf"
    doc.saveas(path)
    return str(path)


def _all_ids(d):
    ids = []
    for v in d["views"]:
        ids += v["piece_ids"]
    return ids


def test_every_piece_has_one_home(tmp_path):
    d = dxf_digest.digest(_sheet(tmp_path))
    ids = _all_ids(d)
    piece_ids = {p["id"] for p in d["pieces"]}
    assert len(ids) == len(set(ids)), "a piece is listed in two views"
    assert set(ids) == piece_ids | {u["id"] for u in d["unsupported"]}, "a piece has no home"
    assert d["ledger"]["pieces"] == len(piece_ids) and d["ledger"]["homeless"] == 0


def test_numbers_are_copied_not_rounded_away(tmp_path):
    d = dxf_digest.digest(_sheet(tmp_path))
    holes = [p for p in d["pieces"] if p["type"] == "CIRCLE"]
    assert sorted(p["radius"] for p in holes) == [1.62, 2.0, 3.3]
    arc = next(p for p in d["pieces"] if p["type"] == "ARC")
    assert arc["radius"] == pytest.approx(3.0, abs=1e-9) and arc["from"] == "LWPOLYLINE"
    assert arc["start"] == pytest.approx([147.0, 100.0], abs=1e-9)
    assert arc["end"] == pytest.approx([150.0, 103.0], abs=1e-9)


def test_unsupported_curve_is_listed_never_flattened(tmp_path):
    d = dxf_digest.digest(_sheet(tmp_path))
    assert [u["type"] for u in d["unsupported"]] == ["ELLIPSE"]
    assert all(p["type"] in {"LINE", "ARC", "CIRCLE", "POINT"} for p in d["pieces"])
    assert d["views"][-1]["id"] == "B_UNSUPPORTED" and d["views"][-1]["piece_ids"] == [d["unsupported"][0]["id"]]


def test_text_is_an_annotation_not_geometry(tmp_path):
    d = dxf_digest.digest(_sheet(tmp_path))
    assert [a["text"] for a in d["annotations"] if a["type"] == "TEXT"] == ["NOTE"]


def test_exact_duplicates_are_bucketed_with_their_original(tmp_path):
    d = dxf_digest.digest(_sheet(tmp_path))
    dup = next(v for v in d["views"] if v["id"] == "B_DUPLICATE")
    assert len(dup["piece_ids"]) == 1
    rec = next(p for p in d["pieces"] if p["id"] == dup["piece_ids"][0])
    orig = next(p for p in d["pieces"] if p["id"] == rec["duplicate_of"])
    assert orig["start"] == rec["start"] and orig["end"] == rec["end"]


def test_frame_view_plate_and_noise_are_separated(tmp_path):
    d = dxf_digest.digest(_sheet(tmp_path), noise_mm=5.0)
    kinds = {v["id"]: v["kind"] for v in d["views"]}
    assert "FRAME_CANDIDATE" in kinds.values()
    plate = next(v for v in d["views"] if v["kind"] == "PART_VIEW_CANDIDATE" and v["size"][0] == pytest.approx(100.0))
    assert plate["holes_by_dia"] == {"Ø3.24": 1, "Ø4": 1, "Ø6.6": 1}   # circles join the plate that contains them
    assert plate["arc_radii"] == {"R3": 1}
    noise = next(v for v in d["views"] if v["id"] == "B_NOISE")
    assert len(noise["piece_ids"]) == 12 and noise["kind"] == "NOISE_CANDIDATES"


def test_noise_is_off_unless_asked(tmp_path):
    d = dxf_digest.digest(_sheet(tmp_path))
    assert all(v["id"] != "B_NOISE" for v in d["views"])


def test_circle_is_never_noise(tmp_path):
    doc = ezdxf.new("R2010")
    doc.modelspace().add_circle((1, 1), 0.14)
    p = tmp_path / "c.dxf"
    doc.saveas(p)
    d = dxf_digest.digest(str(p), noise_mm=5.0)
    assert all(v["id"] != "B_NOISE" for v in d["views"]) and d["pieces"][0]["type"] == "CIRCLE"


def test_tap_pair_candidates_are_reported_concentric_circles(tmp_path):
    d = dxf_digest.digest(_sheet(tmp_path))
    assert len(d["tap_pair_candidates"]) == 1
    pair = d["tap_pair_candidates"][0]
    assert sorted(pair["dia"]) == [3.24, 4.0] and pair["center"] == pytest.approx([120.0, 125.0])


def test_centre_line_keeps_its_linetype_hint_only(tmp_path):
    d = dxf_digest.digest(_sheet(tmp_path))
    line = next(p for p in d["pieces"] if p["type"] == "LINE" and p["linetype"] == "DASHDOT")
    assert line["hint"] == "BEND_SUPPORT_OR_CENTRE" and line["color"] == 1


def test_digest_is_deterministic_and_hashes_the_source(tmp_path):
    path = _sheet(tmp_path)
    a, b = dxf_digest.digest(path), dxf_digest.digest(path)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    assert len(a["source"]["sha256"]) == 64


def test_source_file_is_not_modified(tmp_path):
    path = _sheet(tmp_path)
    before = Path(path).read_bytes()
    dxf_digest.digest(path)
    assert Path(path).read_bytes() == before


def test_catia_profile_is_detected_from_structure(tmp_path):
    d = dxf_digest.digest(_sheet(tmp_path))
    assert d["profile"] == "generic"     # glyph share is small in the mini sheet
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    for k in range(60):
        msp.add_line((k, 0), (k + 0.5, 0.5))
    msp.add_line((0, 0), (100, 0))
    p = tmp_path / "catia.dxf"
    doc.saveas(p)
    assert dxf_digest.digest(str(p))["profile"] == "catia_exploded_sheet"


def test_cli_writes_json(tmp_path):
    out = tmp_path / "digest.json"
    assert dxf_digest.main([_sheet(tmp_path), "--out", str(out)]) == 0
    assert json.loads(out.read_text(encoding="utf-8"))["ledger"]["homeless"] == 0


def test_glyph_like_zigzag_over_noise_size_is_still_noise_candidate(tmp_path):
    """Exploded words are wider than a letter: many sub-mm LINEs in a small blob are glyph noise, not a view."""
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    pts = [(300 + 0.7 * k, 50 + (0.4 if k % 2 else 0.0)) for k in range(14)]       # 13 segments, ~0.8 mm each, 9 mm wide
    for a, b in zip(pts, pts[1:]):
        msp.add_line(a, b)
    msp.add_lwpolyline([(0, 0), (100, 0), (100, 40), (0, 40)], close=True)            # a real 100x40 outline
    p = tmp_path / "zig.dxf"
    doc.saveas(p)
    d = dxf_digest.digest(str(p), noise_mm=5.0)
    noise = next(v for v in d["views"] if v["id"] == "B_NOISE")
    assert len(noise["piece_ids"]) == 13
    assert any(v["kind"] != "NOISE_CANDIDATES" and v["size"] == [100.0, 40.0] for v in d["views"])


def test_frame_is_found_even_when_notes_sit_outside_it(tmp_path):
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    msp.add_lwpolyline([(0, 0), (300, 0), (300, 200), (0, 200)], close=True)
    for x in (20, 120):
        msp.add_lwpolyline([(x, 50), (x + 60, 50), (x + 60, 100), (x, 100)], close=True)
    msp.add_line((0, -30), (60, -30))                                                  # footer note outside the frame
    p = tmp_path / "frame.dxf"
    doc.saveas(p)
    d = dxf_digest.digest(str(p))
    assert [v["kind"] for v in d["views"][:1]] == ["FRAME_CANDIDATE"]


def test_png_overview_is_optional_and_written_when_matplotlib_exists(tmp_path):
    pytest.importorskip("matplotlib")
    png = tmp_path / "v.png"
    assert dxf_digest.main([_sheet(tmp_path), "--out", str(tmp_path / "d.json"), "--png", str(png)]) == 0
    assert png.stat().st_size > 1000


def _composite(tmp_path):
    """Two stacked parts as an AI composite / QA target: bulged corners, holes, a red mark, a label."""
    q = math.tan(math.radians(90) / 4)
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    msp.add_lwpolyline([(0, 300, 0), (97, 300, q), (100, 303, 0), (100, 350, 0), (0, 350, 0)], format="xyb", close=True)
    msp.add_circle((20, 325), 3.3)
    msp.add_circle((80, 325), 3.3)
    msp.add_line((40, 310), (60, 310), dxfattribs={"color": 1})
    msp.add_lwpolyline([(0, 0, 0), (60, 0, 0), (60, 40, 0), (1, 40, q), (0, 39, 0)], format="xyb", close=True)
    msp.add_text("26-000001", dxfattribs={"insert": (0, 360)})
    path = tmp_path / "composite.dxf"
    doc.saveas(path)
    return str(path)


def test_summary_lists_parts_top_to_bottom_with_holes_radii_and_colours(tmp_path):
    s = dxf_digest.summary(dxf_digest.digest(_composite(tmp_path)))
    top, bottom = [v for v in s["views_top_to_bottom"] if v["id"].startswith("V")]
    assert top["size"] == [100.0, 50.0] and top["holes_by_dia"] == {"Ø6.6": 2} and top["arc_radii"] == {"R3": 1}
    assert top["colors"]["1"] == 1
    assert bottom["size"] == [60.0, 40.0] and bottom["arc_radii"] == {"R1": 1}
    assert s["annotations"] == {"TEXT": 1}


def test_polyline_bulges_are_marked_as_decoded_arcs(tmp_path):
    d = dxf_digest.digest(_composite(tmp_path))
    arcs = [p for p in d["pieces"] if p["type"] == "ARC"]
    assert len(arcs) == 2 and all(p.get("bulge_decoded") for p in arcs)


def test_cli_without_out_prints_the_summary_only(tmp_path, capsys):
    assert dxf_digest.main([_composite(tmp_path)]) == 0
    assert "views_top_to_bottom" in capsys.readouterr().out
