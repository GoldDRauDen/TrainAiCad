from pathlib import Path

from luan_app.prompts import build_prompt

OUT = Path("C:/LuanApp/runs/000007/out")
P = "\\\\VietNam2025\\banve\\521030-10"


def test_prompt_run_all_codes():
    t = build_prompt("RUN", P, None, OUT)
    assert t.splitlines()[0] == f"E2E {P}"
    assert "Mã cần làm: tất cả mã trong phiếu" in t
    assert t.count(P) == 1 and str(OUT) in t
    for s in ("Không hỏi lại", "NEED_SAMPLE_DXF", "NEW_LESSON", "chờ xác nhận Nobi", "result.json", "report.md",
              "review_items.json", "Không sửa file nào của repo"):
        assert s in t


def test_prompt_run_subset():
    t = build_prompt("RUN", P, ["26-064687", "26-064643"], OUT)
    assert "Mã cần làm: 26-064687, 26-064643 (job.py init ... --codes 26-064687 26-064643)" in t


def test_prompt_qa():
    t = build_prompt("QA", P, None, OUT)
    assert t.splitlines()[0] == f"QA {P}"
    assert "AI_L" in t and "Không sửa DXF được kiểm tra" in t
