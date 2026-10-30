import json
import os
import time

import pytest

from luan_app import progress as pg


def _state(codes):
    return {"job": "J1", "codes": {c: {"stage": st, "status": s, "flags": fl} for c, (st, s, fl) in codes.items()}}


ALL_PASS = _state({"A": ("L3", "PASS", []), "B": ("L3", "PASS", [])})
ONE_PREVIEW = _state({"A": ("L3", "PASS", []), "B": ("L3", "PREVIEW", ["Nobi chưa rõ"])})
OK = {"verdict": "OK", "summary": "ổn"}
ISSUES = {"verdict": "ISSUES", "summary": "có lỗi"}
DXF = ["x.dxf"]


@pytest.mark.parametrize("kind,state,result,delivered,exit_code,cancelled,want", [
    ("RUN", ALL_PASS, OK, DXF, 0, False, "DONE"),
    ("RUN", ONE_PREVIEW, OK, DXF, 0, False, "REVIEW"),
    ("RUN", ALL_PASS, OK, [], 0, False, "ERROR"),
    ("RUN", ALL_PASS, ISSUES, DXF, 0, False, "REVIEW"),
    ("RUN", ALL_PASS, None, DXF, 0, False, "DONE"),
    ("RUN", None, OK, DXF, 0, False, "ERROR"),
    ("RUN", ALL_PASS, OK, DXF, 1, False, "ERROR"),
    ("QA", None, OK, [], 0, False, "DONE"),
    ("QA", None, ISSUES, [], 0, False, "REVIEW"),
    ("QA", None, None, [], 0, False, "ERROR"),
    ("RUN", ALL_PASS, OK, DXF, 0, True, "CANCELLED"),
])
def test_final_status_table(kind, state, result, delivered, exit_code, cancelled, want):
    status, summary = pg.final_status(kind, state, result, delivered, exit_code, cancelled)
    assert status == want and isinstance(summary, str) and summary


def test_summary_from_rows_when_no_result():
    _, s = pg.final_status("RUN", ONE_PREVIEW, None, DXF, 0, False)
    assert s == "1/2 PASS · 1 PREVIEW · 1 FLAG"


def test_code_rows():
    rows = pg.code_rows(ONE_PREVIEW)
    assert rows[1] == {"code": "B", "stage": "L3", "status": "PREVIEW", "flags": 1, "flag_texts": ["Nobi chưa rõ"]}
    assert pg.code_rows(None) == []


def test_review_items_validation(tmp_path):
    (tmp_path / "review_items.json").write_text(json.dumps([
        {"type": "NEW_LESSON", "title": "Kiểu gấp lạ", "code": "26-1", "card": "rules/BEND.md", "detail": "d"},
        {"type": "MISSING_DIM", "title": "x"},
        {"type": "NEED_SAMPLE_DXF", "title": ""},
    ], ensure_ascii=False), encoding="utf-8")
    items, warns = pg.read_review_items(tmp_path)
    assert [i["title"] for i in items] == ["Kiểu gấp lạ"] and len(warns) == 2
    assert pg.read_review_items(tmp_path / "none") == ([], [])
    (tmp_path / "review_items.json").write_text("{broken", encoding="utf-8")
    items, warns = pg.read_review_items(tmp_path)
    assert items == [] and warns


def test_read_result(tmp_path):
    assert pg.read_result(tmp_path) is None
    (tmp_path / "result.json").write_text('{"verdict": "MAYBE"}', encoding="utf-8")
    assert pg.read_result(tmp_path) is None
    (tmp_path / "result.json").write_text('{"verdict": "OK", "summary": "s"}', encoding="utf-8")
    assert pg.read_result(tmp_path)["verdict"] == "OK"


def test_find_job_state_prefers_named_job(tmp_path):
    for job in ("J1", "J2"):
        d = tmp_path / ".work" / job
        d.mkdir(parents=True)
        (d / "job_state.json").write_text(json.dumps({"job": job, "codes": {}}), encoding="utf-8")
    assert pg.find_job_state(tmp_path, "J1")["job"] == "J1"
    assert pg.find_job_state(tmp_path, "J9")["job"] in ("J1", "J2")
    assert pg.find_job_state(tmp_path / "nothing", "J1") is None


def test_delivered_since(tmp_path):
    ai = tmp_path / "AI_L"
    ai.mkdir()
    old, new = ai / "old.dxf", ai / "new.dxf"
    old.write_text("0")
    t0 = time.time() - 3600
    os.utime(old, (t0, t0))
    new.write_text("0")
    since = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.time() - 60))
    assert [os.path.basename(p) for p in pg.delivered(str(tmp_path), since)] == ["new.dxf"]
    assert pg.delivered(str(tmp_path / "missing"), since) == []


def test_search_text():
    t = pg.search_text({"job": "J1", "kind": "RUN"}, pg.code_rows(ONE_PREVIEW), {"summary": "Nobi"})
    assert "J1" in t and "B" in t and "Nobi chưa rõ" in t
