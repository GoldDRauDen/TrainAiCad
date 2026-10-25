"""build_canonical `bend:` block (tools/bend_flat.py): approved chains, refusals, export."""
import copy
import sys
from pathlib import Path

import ezdxf
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import bend_flat  # noqa: E402
import build_canonical as bc  # noqa: E402
from export_canonical_dxf import export_canonical_job  # noqa: E402

SPEC = yaml.safe_load((ROOT / "examples/bend_minimal.yaml").read_text(encoding="utf-8"))


def part_spec(**bend):
    ps = copy.deepcopy(SPEC["parts"][0])
    ps["bend"].update(bend)
    return ps


def chain_part(ods, nobis, signs=None, width=40, material="SPCC", t=2, axis="X", angle=90):
    faces = [{"id": f"F{i + 1}", "od": od, "ev": f"od {od}"} for i, od in enumerate(ods)]
    bends = [{"id": f"B{i + 1}", "angle": angle, "sign": (signs or [1] * len(nobis))[i], "nobi": n, "ev": "bend"}
             for i, n in enumerate(nobis)]
    total = sum(ods) - sum(n if n is not None else 3.44 for n in nobis)  # 3.44 = SPCC t2 table
    env = [total, width] if axis == "X" else [width, total]
    return {"code": "26-000020", "material": material, "t": t, "page": 1, "envelope": env,
            "bend": {"axis": axis, "width": width, "width_ev": "full width", "faces": faces, "bends": bends},
            "outline": "auto"}


def lines(part):
    return sorted((e["start"], e["end"]) for e in part["entities"] if e.get("role") == "bend")


def test_example_reproduces_the_approved_521017_17_main_chain():
    part = bc.build_part(copy.deepcopy(SPEC["parts"][0]))
    assert part["unfold"]["flat_length_mm"] == pytest.approx(228.64)
    assert [(b["line1"], b["line2"]) for b in part["unfold"]["bends"]] == [(46.32, 50.0), (106.64, 110.32)]
    holes = sorted(e["center"] for e in part["entities"] if e["type"] == "CIRCLE")
    assert holes == [[136.64, 10.0], [203.64, 30.0]]  # F3 start = B2 line1; from end = flat length
    assert part["status"] == "PASS" and part["checks"]["unfold"] == "PASS"
    led = part["per_bend_witness_ledger"]
    assert all(abs(x["od_actual_mm"][0] + x["od_actual_mm"][1] - x["nobi_mm"] - x["flat_mm"]) < 1e-9 for x in led)


@pytest.mark.parametrize("ods,nobis,signs,flat", [
    ([106, 222, 106], [3.8, 3.8], [1, 1], 426.4),          # U, 056956
    ([39.8, 128.8, 21.3], [4.62, 4.62], [1, -1], 180.66),  # Z, 057042
])
def test_u_and_z_chains(ods, nobis, signs, flat):
    part = bc.build_part(chain_part(ods, nobis, signs))
    assert part["unfold"]["flat_length_mm"] == pytest.approx(flat)
    angles = [b["signed_angle_deg"] for b in part["face_graph"]["bends"]]
    assert angles == [90 * s for s in signs]
    assert len(lines(part)) == 4


def test_table_nobi_when_no_handwriting():
    ps = chain_part([30, 50], [None])
    del ps["bend"]["bends"][0]["nobi"]
    part = bc.build_part(ps)
    b = part["unfold"]["bends"][0]
    assert b["nobi_source"] == "TABLE" and b["nobi"] == pytest.approx(3.44)  # SPCC t2 L40


def test_y_axis_chain_puts_bend_lines_horizontal():
    part = bc.build_part(chain_part([50, 64], [3.68], axis="Y"))
    (s1, e1), (s2, e2) = lines(part)
    assert s1[1] == e1[1] == pytest.approx(46.32) and s2[1] == e2[1] == pytest.approx(50.0)
    assert part["envelope_mm"] == [40.0, 110.32]


def test_missing_nobi_on_the_only_bend_splits_into_two_pieces():
    ps = chain_part([30, 50], [None], angle=120)
    del ps["bend"]["bends"][0]["nobi"]
    part = bc.build_part(ps)
    assert part["status"] == "PREVIEW" and not any(e["role"] == "bend" for e in part["entities"])
    assert [e["role"] for e in part["entities"] if e["type"] == "LWPOLYLINE"] == ["outer", "split_flange"]


def test_outline_change_inside_a_bend_zone_is_refused():
    ps = chain_part([50, 64], [3.68])
    ps["envelope"] = [110.32, 40]
    ps["outline"] = [[0, 0], [110.32, 0], [110.32, 30], [48, 30], [48, 40], [0, 40]]  # local flange, wall in zone
    with pytest.raises(bc.BuildError, match="bend-end junction"):
        bc.build_part(ps)


def test_bend_lines_are_clipped_to_material():
    ps = chain_part([50, 64], [3.68])
    ps["envelope"] = [110.32, 40]
    ps["outline"] = [[0, 0], [110.32, 0], [110.32, 40], [60, 40], [60, 25], [40, 25], [40, 40], [0, 40]]
    part = bc.build_part(ps)  # edge notch over the bend: the lines stop at the notch bottom
    assert lines(part) == [([46.32, 0.0], [46.32, 25.0]), ([50.0, 0.0], [50.0, 25.0])]


def test_a_void_across_the_bend_splits_it_into_two_members():
    ps = chain_part([50, 64], [3.68])
    ps["envelope"] = [110.32, 40]
    ps["outline"] = [[0, 0], [110.32, 0], [110.32, 40], [0, 40], [0, 25], [60, 25], [60, 15], [0, 15]]
    part = bc.build_part(ps)
    assert len(lines(part)) == 4
    assert {b["bend_id"] for b in part["face_graph"]["bends"]} == {"26-000020_B1_1", "26-000020_B1_2"}
    assert len(part["per_bend_witness_ledger"]) == 2


def test_hole_on_a_bend_line_is_refused():
    ps = part_spec()
    ps["holes"][0]["wu"] = [[2, "HOLE_CENTER", "too close"]]
    ps["holes"][0]["from"] = "start"
    ps["holes"][0]["face"] = "F3"
    ps["holes"][0]["wu"] = [[-1, "HOLE_CENTER", "inside the bend zone"]]
    with pytest.raises(bc.BuildError, match="overlaps bend"):
        bc.build_part(ps)


def test_face_relative_outline_points():
    ch = bend_flat.unfold_chain(SPEC["parts"][0]["bend"], "SPCC", 2, None, "X")
    pts = bend_flat.resolve_outline([{"face": "F2", "u": 10, "v": 5}, {"face": "F3", "from": "end", "u": 5, "v": 0, "R": 2}],
                                    ch, "X")
    assert pts[0] == [46.32 + 10, 5.0] and pts[1] == [228.64 - 5, 0.0, {"R": 2}]


def test_rotation_mirrors_the_ledger():
    part = {"per_bend_witness_ledger": [{"bend_pair_mm": [46.32, 50.0], "nobi_mm": 3.68, "flat_mm": 228.64,
                                         "od_actual_mm": [50.0, 182.32], "ordered_faces": ["F1", "F2"]}]}
    bend_flat.mirror_ledger(part, 228.64)
    item = part["per_bend_witness_ledger"][0]
    assert item["bend_pair_mm"] == [178.64, 182.32] and item["ordered_faces"] == ["F2", "F1"]
    assert item["od_actual_mm"][0] + item["od_actual_mm"][1] - 3.68 == pytest.approx(228.64)


def test_bent_example_exports_and_reads_back(tmp_path):
    job = bc.build_job(copy.deepcopy(SPEC))
    manifest = export_canonical_job(job, tmp_path)
    assert manifest["status"] == "PASS"
    doc = ezdxf.readfile(tmp_path / manifest["filename"])
    dashed = [e for e in doc.modelspace() if e.dxftype() == "LINE" and e.dxf.get("linetype", "").upper() == "DASHED"]
    assert sorted(round(e.dxf.start.x, 2) for e in dashed) == [46.32, 50.0, 106.64, 110.32]


def test_split_bend_part_passes_the_export_guards(tmp_path):
    ps = chain_part([50, 64], [3.68])
    ps["envelope"] = [110.32, 40]
    ps["outline"] = [[0, 0], [110.32, 0], [110.32, 40], [0, 40], [0, 25], [60, 25], [60, 15], [0, 15]]
    job = {"canonical_contract": bc.CONTRACT, "job_id": "T-SPLIT", "parts": [bc.build_part(ps)]}
    assert export_canonical_job(job, tmp_path)["status"] == "PASS"


def test_missing_nobi_draws_the_split_flange_10mm_away(tmp_path):
    # B2 at 120° without handwriting: no Nobi -> SPLIT_FLANGE_10MM (rules/BEND.md §6)
    ps = chain_part([50, 64, 30], [3.68, None])
    ps["bend"]["bends"][1]["angle"] = 120
    ps["envelope"] = [50 + 64 - 3.68 + 30, 40]
    ps["holes"] = [{"id": "H1", "d": 7, "group": "D7", "ev": "Ø7 on F3", "face": "F3", "from": "end",
                    "wu": [[10, "HOLE_CENTER", "10 from the free edge"]], "wv": [[20, "HOLE_CENTER", "20"]]}]
    part = bc.build_part(ps)
    assert part["status"] == "PREVIEW" and part["split_flange"][0]["bend"] == "B2"
    assert any("SPLIT_FLANGE_10MM" in f for f in part["flags"])
    outer = next(e for e in part["entities"] if e["role"] == "outer")
    piece = next(e for e in part["entities"] if e["role"] == "split_flange")
    assert outer.get("color", 256) == 256 and piece["color"] == 6
    xs = [v[0] for v in outer["vertices"]]
    assert (min(xs), max(xs)) == (0, 110.32)      # body F1+F2 at OD with B1 Nobi
    px = [v[0] for v in piece["vertices"]]
    assert (min(px), max(px)) == (120.32, 150.32)  # F3 at its OD 30, 10 mm after the body
    assert [round(e["start"][0], 2) for e in part["entities"] if e["role"] == "bend"] == [46.32, 50.0]
    hole = next(e for e in part["entities"] if e["type"] == "CIRCLE")
    assert hole["center"] == [140.32, 20.0]       # face-relative hole moves with its piece
    manifest = export_canonical_job({"canonical_contract": bc.CONTRACT, "job_id": "T-SF", "parts": [part]}, tmp_path)
    assert manifest["status"] == "REVIEW_ONLY"


def test_split_flange_with_a_shaped_outline_is_refused_with_the_reason():
    ps = chain_part([50, 64], [None])
    ps["bend"]["bends"][0]["angle"] = 120
    ps["outline"] = [[0, 0], [110, 0], [110, 40], [0, 40]]
    with pytest.raises(bc.BuildError, match="outline: auto"):
        bc.build_part(ps)
