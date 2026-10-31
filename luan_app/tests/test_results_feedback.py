"""Short per-code results, AI_L for everyone, feedback, QA files in AI_L, urgent codes reaching the share mid-run."""
import os
import time
from pathlib import Path

from luan_app import progress, staging
from luan_app.api import ai_l_dir
from luan_app.prompts import build_prompt
from luan_app.store import FINAL
from luan_app.tests.test_api import admin, client, ctx, named, wait_final  # noqa: F401 (fixtures)
from luan_app.tests.test_scheduler import sched, user, wait_for  # noqa: F401 (fixtures)

OUT = Path("C:/LuanApp/runs/000007/out")
LOCAL = "C:\\TrainAiCad-slots\\slot1\\.work\\521028-04\\source"


def test_result_view_takes_both_forms_and_fills_from_job_state():
    result = {"codes": {"A": "PASS", "B": {"status": "fail", "note": "R5 thiếu"}}, "questions": ["Lỗ 6 hay 6.5?"]}
    rows = [{"code": "C", "status": "PREVIEW", "flag_texts": ["Nobi chưa rõ"]}, {"code": "A", "status": "PASS", "flag_texts": []}]
    v = progress.result_view(result, rows)
    assert v["codes"] == [{"code": "A", "status": "PASS", "note": ""}, {"code": "B", "status": "FAIL", "note": "R5 thiếu"},
                          {"code": "C", "status": "PREVIEW", "note": "Nobi chưa rõ"}]
    assert v["questions"] == ["Lỗ 6 hay 6.5?"]
    assert progress.result_view(None, []) is None


def test_prompts_ask_for_short_reports_and_qa_files():
    run = build_prompt("RUN", LOCAL, None, OUT, share_path="\\\\S\\j", local_job_dir=LOCAL, job="521028-04")
    assert "deliver-code <mã>` NGAY" in run and "không kể quá trình" in run and "questions" in run
    qa = build_prompt("QA", LOCAL, None, OUT, share_path="\\\\S\\j", local_job_dir=LOCAL, job="521028-04")
    for s in (LOCAL + "\\AI_L\\521028-04_AI_QA.txt", "ALL_PASS", "521028-04_AI_QA.dxf", "qa_markup.py",
              "KHÔNG phải DATA của khách", "không phải lỗi", "hướng vân"):
        assert s in qa, s


def _staged(tmp_path):
    job = tmp_path / "share" / "521028-04"
    (job / "AI_L").mkdir(parents=True)
    (job / "521028-04.pdf").write_bytes(b"%PDF")
    (job / "AI_L" / "old.dxf").write_text("drafter\n")
    return job, staging.stage_in(str(job), str(job), tmp_path / "slot1", "521028-04")


def test_stage_out_mid_run_waits_until_a_file_stops_changing(tmp_path):
    job, st = _staged(tmp_path)
    f = st.local_dir / "AI_L" / "26-000001.dxf"
    f.write_text("code 1\n")
    assert staging.stage_out(st, final=False) == []                      # first look: may still be written
    assert [os.path.basename(p) for p in staging.stage_out(st, final=False)] == ["26-000001.dxf"]
    assert staging.stage_out(st, final=False) == [] and staging.stage_out(st) == []
    assert st.copied == [str(job / "AI_L" / "26-000001.dxf")]


def test_stage_out_qa_sends_only_the_ai_qa_files(tmp_path):
    job, st = _staged(tmp_path)
    ai_l = st.local_dir / "AI_L"
    for n in ("521028-04_AI_QA.txt", "521028-04_AI_QA.dxf", "scratch.dxf", "notes.txt"):
        (ai_l / n).write_text(n)
    assert sorted(os.path.basename(p) for p in staging.stage_out(st, "QA")) == ["521028-04_AI_QA.dxf", "521028-04_AI_QA.txt"]
    assert not (job / "AI_L" / "scratch.dxf").exists() and (job / "AI_L" / "old.dxf").read_text() == "drafter\n"


def test_qa_run_puts_ai_qa_txt_in_the_share(sched, store, user, job_dir):  # noqa: F811
    rid = sched.submit(user, "QA", str(job_dir), None, confirm_rerun=False, is_admin=True)
    r = wait_for(sched, store, rid, FINAL)
    assert r["status"] == "DONE", r
    assert (job_dir / "AI_L" / "521030-10_AI_QA.txt").read_text(encoding="utf-8") == "ALL_PASS\n"
    assert [os.path.basename(p) for p in r["delivered"]] == ["521030-10_AI_QA.txt"]


def test_urgent_codes_reach_the_share_while_the_run_goes_on(sched, store, user, job_dir):  # noqa: F811
    sched.extra_env.update(FAKE_MODE="urgent", FAKE_SLOW="2", FAKE_CODES="26-000001,26-000002,26-000003")
    rid = sched.submit(user, "RUN", str(job_dir), None, confirm_rerun=False, is_admin=False)
    end = time.time() + 30
    while time.time() < end and not (job_dir / "AI_L" / "26-000001.dxf").exists():
        sched.tick()
        time.sleep(0.1)
    assert (job_dir / "AI_L" / "26-000001.dxf").exists()
    assert store.get_run(rid)["status"] == "RUNNING"                       # not waiting for the end of the run
    r = wait_for(sched, store, rid, FINAL, timeout=60)
    names = sorted(os.listdir(job_dir / "AI_L"))
    assert names == ["26-000001.dxf", "26-000002.dxf", "26-000003.dxf", "521030-10_ALL.dxf"], names  # each once
    assert r["result"]["codes"][-1]["code"] == "26-000003"


def test_preview_result_shows_reason_and_questions(ctx, job_dir):  # noqa: F811
    ctx["sched"].extra_env["FAKE_MODE"] = "preview"
    c = named(ctx, "Hùng")
    rid = c.post("/api/runs", json={"path": str(job_dir), "kind": "RUN"}).json()["id"]
    wait_final(ctx, rid)
    d = c.get(f"/api/runs/{rid}").json()
    bad = [x for x in d["result"]["codes"] if x["status"] != "PASS"]
    assert bad and bad[0]["note"] == "Nobi chưa rõ" and d["result"]["questions"] == ["Lỗ 6 hay 6.5?"]
    assert d["ai_l"] == str(job_dir) + "\\AI_L" if os.name == "nt" else d["ai_l"].endswith("AI_L")
    assert c.get("/api/runs").json()["runs"][0]["ai_l"] == d["ai_l"]


def test_ai_l_dir_of_old_runs_and_qa_dxf():
    assert ai_l_dir({"path": "\\\\S\\j\\521028-04"}) == "\\\\S\\j\\521028-04\\AI_L"
    assert ai_l_dir({"path": "\\\\S\\j\\521028-04\\gui\\x.dxf", "job_dir": "\\\\S\\j\\521028-04"}) == "\\\\S\\j\\521028-04\\AI_L"


def test_open_folder_any_local_user_but_not_remote(ctx, job_dir):  # noqa: F811
    c = named(ctx, "Hùng")
    rid = c.post("/api/runs", json={"path": str(job_dir), "kind": "RUN"}).json()["id"]
    wait_final(ctx, rid)
    assert c.post("/api/open-folder", json={"run_id": rid}).status_code == 403          # remote: the UI copies the path
    local = named(ctx, "Tâm", ("127.0.0.1", 1))
    if os.name != "nt":
        assert local.post("/api/open-folder", json={"run_id": rid}).json()["ok"]


def test_feedback_is_stored_and_waits_for_review(ctx, job_dir):  # noqa: F811
    c = named(ctx, "Hùng")
    assert c.post("/api/feedback", json={"text": "  "}).status_code == 400
    assert c.post("/api/feedback", json={"text": "x" * 5000}).status_code == 400
    assert c.post("/api/feedback", json={"text": "Nút AI_L nên to hơn\nchi tiết"}).status_code == 201
    other = named(ctx, "Minh", ("10.0.0.41", 1))
    assert other.post("/api/feedback", json={"text": "của Minh"}).status_code == 201
    a = admin(ctx)
    assert a.get("/api/review-items").json()["items"] == []                    # feedback has its own page
    items = a.get("/api/feedback").json()["items"]
    it = next(i for i in items if i["author"] == "Hùng")
    assert len(items) == 2 and it["status"] == "PENDING" and it["title"] == "Nút AI_L nên to hơn"
    assert it["copy_text"].startswith("GÓP Ý từ Hùng") and "chi tiết" in it["copy_text"]
    assert a.get("/api/board").json()["feedback_new"] == 2 and a.get("/api/board").json()["review_pending"] == 0
    # a user follows only their own feedback and the status Admin gave it; only Admin changes it
    assert c.patch(f"/api/feedback/{it['id']}", json={"status": "SEEN"}).status_code == 403
    assert a.patch(f"/api/feedback/{it['id']}", json={"status": "COPIED"}).status_code == 400
    assert a.patch(f"/api/feedback/{it['id']}", json={"status": "SEEN"}).json()["status"] == "SEEN"
    mine = c.get("/api/feedback").json()["items"]
    assert [(m["title"], m["status"]) for m in mine] == [("Nút AI_L nên to hơn", "SEEN")] and "copy_text" not in mine[0]
    assert client(ctx).post("/api/feedback", json={"text": "ẩn danh"}).status_code == 401


def test_admin_guide_is_admin_only_and_user_guide_has_no_admin_part(ctx):  # noqa: F811
    assert named(ctx, "Hùng").get("/api/admin/guide").status_code == 403
    g = admin(ctx).get("/api/admin/guide")
    assert g.status_code == 200 and "Làm tiếp" in g.text and "python -m luan_app.runs" in g.text
    user_guide = (Path(__file__).parents[1] / "static" / "guide.html").read_text(encoding="utf-8")
    assert "Chờ duyệt" not in user_guide and "QA" not in user_guide
