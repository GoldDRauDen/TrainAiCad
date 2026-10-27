"""521027-26: customer DATA is copied 100%; the tools, not the AI, close the gaps (rules/DATA_DXF.md)."""
import json
import sys
from pathlib import Path

import ezdxf
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_canonical as bc  # noqa: E402
import dxf_assemble  # noqa: E402
import dxf_digest  # noqa: E402
from export_canonical_dxf import export_canonical_job  # noqa: E402
from material_resolver import MaterialResolveError, resolve_material  # noqa: E402


def _digest(tmp_path, draw):
    doc = ezdxf.new("R2010")
    draw(doc.modelspace())
    path = tmp_path / "data.dxf"
    doc.saveas(path)
    return dxf_digest.digest(str(path))


def _rect_lines(msp, pts):
    for a, b in pts:
        msp.add_line(a, b)


def _outer_plan(d, **extra):
    return {"members": [{"id": "OUT", "role": "outer", "pieces": [p["id"] for p in d["pieces"] if p["type"] == "LINE"]}],
            "excluded": [], **extra}


def test_two_letter_alias_matches_its_numbered_grades():
    for name in ("SK85", "SK5", "SK-5", "sk85"):
        r = resolve_material(name)
        assert r["material_family"] == "SS" and r["source_cell"].endswith("A33")
    with pytest.raises(MaterialResolveError):
        resolve_material("SKD11")        # a different steel family, not the SK alias


# ---- the digest is sealed: a hand-edited piece list is refused ------------------------------------------------------

def test_edited_digest_pieces_are_refused(tmp_path):
    d = _digest(tmp_path, lambda m: _rect_lines(m, [((0, 0), (100, 0)), ((100, 0), (100, 50)), ((100, 50), (0, 50)), ((0, 50), (0, 0))]))
    assert dxf_assemble.assemble(d, _outer_plan(d))["invariance"]["ok"]
    d["pieces"][0]["start"][0] += 0.5
    with pytest.raises(dxf_assemble.AssembleError, match="DIGEST_PIECES_ALTERED"):
        dxf_assemble.assemble(d, _outer_plan(d))
    d2 = _digest(tmp_path, lambda m: _rect_lines(m, [((0, 0), (100, 0)), ((100, 0), (100, 50)), ((100, 50), (0, 50)), ((0, 50), (0, 0))]))
    d2["pieces"].append({**d2["pieces"][0], "id": "X_SYNTHETIC"})
    with pytest.raises(dxf_assemble.AssembleError, match="DIGEST_PIECES_ALTERED"):
        dxf_assemble.assemble(d2, _outer_plan(d2))


# ---- closure noise and T-junctions are closed by the tool, each with a ledger row -----------------------------------

def test_sub_micron_gap_is_joined_by_the_tool_and_listed(tmp_path):
    d = _digest(tmp_path, lambda m: _rect_lines(m, [((0, 0), (100, 0)), ((100.0006, 0), (100, 50)), ((100, 50), (0, 50)), ((0, 50), (0, 0))]))
    res = dxf_assemble.assemble(d, _outer_plan(d))
    rows = [r for r in res["changes"] if r["rule"] == "CLOSURE_NOISE"]
    assert len(rows) == 1 and 5e-4 < rows[0]["gap_mm"] < 7e-4
    assert res["invariance"]["ok"] and len(res["entities"][0]["vertices"]) == 4


def test_a_real_gap_is_still_an_open_contour(tmp_path):
    d = _digest(tmp_path, lambda m: _rect_lines(m, [((0, 0), (100, 0)), ((100.01, 0), (100, 50)), ((100, 50), (0, 50)), ((0, 50), (0, 0))]))
    with pytest.raises(dxf_assemble.AssembleError, match="CHAIN_NOT_CLOSED"):
        dxf_assemble.assemble(d, _outer_plan(d))


def test_t_junction_cuts_the_line_and_drops_only_the_overhang(tmp_path):
    # the left edge is one DATA line that runs 5 mm below the bottom edge (the neighbouring plate's rectangle)
    d = _digest(tmp_path, lambda m: _rect_lines(m, [((0, 5 * -1), (0, 50)), ((0, 0), (100, 0)), ((100, 0), (100, 50)), ((100, 50), (0, 50))]))
    res = dxf_assemble.assemble(d, _outer_plan(d))
    rules = sorted(r["rule"] for r in res["changes"])
    assert rules == ["T_SPLIT", "T_SPUR"]
    assert len(res["entities"][0]["vertices"]) == 4 and res["invariance"]["ok"]
    ys = [v[1] for v in res["entities"][0]["vertices"]]
    assert min(ys) == 0.0 and max(ys) == 50.0          # the overhang below y = 0 is not in the contour


def test_a_free_end_of_an_original_piece_is_never_pruned(tmp_path):
    d = _digest(tmp_path, lambda m: _rect_lines(m, [((0, 0), (100, 0)), ((100, 0), (100, 50)), ((100, 50), (0, 50)), ((0, 50), (0, 5)), ((60, 0), (60, -9))]))
    with pytest.raises(dxf_assemble.AssembleError):
        dxf_assemble.assemble(d, _outer_plan(d))


# ---- round blank (two half circles) and DATA away from the origin build and export without hand patches -----------

def _assembled_spec(tmp_path, draw, plan_fn, part):
    d = _digest(tmp_path, draw)
    res = dxf_assemble.assemble(d, plan_fn(d))
    (tmp_path / "assembled.json").write_text(json.dumps(res), encoding="utf-8")
    path = tmp_path / "spec.yaml"
    path.write_text(yaml.safe_dump({"job_id": "520930-03", "parts": [{**part, "data": "assembled.json"}]}, allow_unicode=True),
                    encoding="utf-8")
    return path


def test_round_blank_data_builds_and_exports(tmp_path):
    def draw(m):
        m.add_arc((500, 300), 59.5, 0, 180)
        m.add_arc((500, 300), 59.5, 180, 360)
        m.add_circle((550, 300), 5)
        m.add_circle((450, 300), 5)

    def plan(d):
        arcs = [p["id"] for p in d["pieces"] if p["type"] == "ARC"]
        holes = [p["id"] for p in d["pieces"] if p["type"] == "CIRCLE"]
        return {"members": [{"id": "OUT", "role": "outer", "pieces": arcs}, {"id": "H", "role": "hole", "pieces": holes}],
                "excluded": []}
    spec = _assembled_spec(tmp_path, draw, plan, {"code": "26-062001", "material": "SS400", "t": 3.2, "page": 1,
                                                  "envelope": [119, 119],
                                                  "members": {"H": {"group": "D10", "qty": 2, "ev": "p1 2-Ø10", "pdf_d": 10}}})
    job = bc.build_from_files([spec])
    part = job["parts"][0]
    outer = part["entities"][0]
    assert [v[2] for v in outer["vertices"]] == [1, 1]                                  # one full circle
    assert sorted(e["center"] for e in part["entities"] if e["type"] == "CIRCLE") == [[9.5, 59.5], [109.5, 59.5]]
    assert any(c["rule"] == "TRANSLATE_TO_ORIGIN" for c in part["manufacturing_change_ledger"])
    export_canonical_job(job, tmp_path / "OUT", require_slip_codes=True)


def test_flat_data_far_from_the_origin_exports_with_the_datum_at_its_own_edge(tmp_path):
    def draw(m):
        m.add_lwpolyline([(1000, 500), (1200, 500), (1200, 600), (1000, 600)], close=True)
        m.add_circle((1030, 550), 4.5)

    def plan(d):
        return {"members": [{"id": "OUT", "role": "outer", "pieces": [p["id"] for p in d["pieces"] if p["type"] == "LINE"]},
                            {"id": "H", "role": "hole", "pieces": [p["id"] for p in d["pieces"] if p["type"] == "CIRCLE"]}],
                "excluded": []}
    spec = _assembled_spec(tmp_path, draw, plan, {"code": "26-062002", "material": "SS400", "t": 3.2, "page": 1,
                                                  "envelope": [200, 100],
                                                  "members": {"H": {"group": "D9", "qty": 1, "ev": "p1 Ø9", "pdf_d": 9}}})
    job = bc.build_from_files([spec])
    assert [e["center"] for e in job["parts"][0]["entities"] if e["type"] == "CIRCLE"] == [[30.0, 50.0]]
    export_canonical_job(job, tmp_path / "OUT", require_slip_codes=True)


def test_long_strip_with_the_straight_edge_at_the_bottom_keeps_the_data_roundtrip(tmp_path):
    def draw(m):
        m.add_lwpolyline([(0, 0), (1100, 0), (1100, 90), (700, 90), (700, 70), (400, 70), (400, 90), (0, 90)], close=True)
        m.add_circle((200, 30), 4)

    def plan(d):
        return {"members": [{"id": "OUT", "role": "outer", "pieces": [p["id"] for p in d["pieces"] if p["type"] == "LINE"]},
                            {"id": "H", "role": "hole", "pieces": [p["id"] for p in d["pieces"] if p["type"] == "CIRCLE"]}],
                "excluded": []}
    spec = _assembled_spec(tmp_path, draw, plan, {"code": "26-062003", "material": "SS400", "t": 3.2, "page": 1,
                                                  "envelope": [1100, 90],
                                                  "members": {"H": {"group": "D8", "qty": 1, "ev": "p1 Ø8", "pdf_d": 8}}})
    part = bc.build_from_files([spec])["parts"][0]
    assert part["canonical_rotation_deg"] == 180        # J/LJ turn: the DATA roundtrip must follow it, not fail
    assert [e["center"] for e in part["entities"] if e["type"] == "CIRCLE"] == [[900.0, 60.0]]
