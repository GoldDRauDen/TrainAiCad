import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from luan_app.api import create_app
from luan_app.auth import Auth
from luan_app.scheduler import Scheduler
from luan_app.slots import Slots
from luan_app.store import FINAL

FAKE = Path(__file__).with_name("fake_claude.py")
LOCAL = ("127.0.0.1", 5000)


@pytest.fixture
def ctx(store, paths, jobs_root):
    store.set_settings(allowed_roots=[str(jobs_root)])
    sched = Scheduler(store, paths, Slots(paths.repo_root, paths.slots_root),
                      exe_override=[sys.executable, str(FAKE)], extra_env={"FAKE_MODE": "ok"}, progress_s=0.2)
    auth = Auth(store)
    app = create_app(paths, store, auth, sched, serve_static=False)
    yield {"app": app, "store": store, "sched": sched, "auth": auth}
    sched.stop()


def client(ctx, host=("10.0.0.21", 5000)) -> TestClient:
    c = TestClient(ctx["app"], client=host)
    c.get("/api/me")
    c.headers["X-Luan-CSRF"] = c.cookies.get("luan_csrf")
    return c


def named(ctx, name, host=("10.0.0.21", 5000)) -> TestClient:
    c = client(ctx, host)
    assert c.post("/api/me", json={"name": name}).status_code == 200
    return c


def admin(ctx) -> TestClient:
    if not ctx["auth"].has_admin_password():
        ctx["auth"].set_admin_password("matkhau1")
    c = named(ctx, "Luân", LOCAL)
    assert c.post("/api/admin/login", json={"password": "matkhau1"}).status_code == 200
    return c


def wait_final(ctx, rid, timeout=30):
    end = time.time() + timeout
    while time.time() < end:
        ctx["sched"].tick()
        r = ctx["store"].get_run(rid)
        if r["status"] in FINAL:
            return r
        time.sleep(0.1)
    raise AssertionError("not final")


def test_name_then_board_304(ctx):
    c = client(ctx)
    assert c.get("/api/board").status_code == 401
    assert c.post("/api/me", json={"name": "Hùng"}).json()["user"]["name"] == "Hùng"
    r = c.get("/api/board")
    assert r.status_code == 200 and r.json()["me"]["name"] == "Hùng" and r.json()["slots"]["total"] == 3
    etag = r.headers["etag"]
    assert c.get("/api/board", headers={"If-None-Match": etag}).status_code == 304


def test_name_reclaim_after_cookie_lost(ctx):
    first = named(ctx, "Hùng")
    uid = first.cookies.get("luan_uid")
    c = client(ctx, ("10.0.0.22", 5000))  # new browser, no luan_uid cookie
    r = c.post("/api/me", json={"name": "hùng"})
    assert r.status_code == 200 and r.json()["user"]["name"] == "Hùng"
    assert c.cookies.get("luan_uid") == uid


def test_rename_to_taken_name_refused(ctx):
    named(ctx, "Hùng")
    c = named(ctx, "Minh", ("10.0.0.22", 5000))
    r = c.post("/api/me", json={"name": "hùng"})
    assert r.status_code == 400 and "Tên" in r.json()["error"]


def test_csrf_required(ctx):
    c = named(ctx, "Hùng")
    del c.headers["X-Luan-CSRF"]
    assert c.post("/api/me", json={"name": "Hùng2"}).status_code == 403


def test_user_cannot_qa_or_settings_or_review(ctx, job_dir):
    c = named(ctx, "Hùng")
    r = c.post("/api/runs", json={"path": str(job_dir), "kind": "QA"})
    assert r.status_code == 403
    assert c.get("/api/settings").status_code == 403
    assert c.put("/api/settings", json={"slots": 5}).status_code == 403
    assert c.get("/api/review-items").status_code == 403
    assert c.post("/api/queue/resume").status_code == 403


def test_admin_login_flow_and_lockout_423(ctx):
    ctx["auth"].set_admin_password("matkhau1")
    c = named(ctx, "X1", ("10.0.0.30", 1))
    for _ in range(4):
        assert c.post("/api/admin/login", json={"password": "sai"}).status_code == 401
    assert c.post("/api/admin/login", json={"password": "sai"}).status_code == 423   # 5th failure locks at once
    r = c.post("/api/admin/login", json={"password": "matkhau1"})
    assert r.status_code == 423 and r.json()["retry_after"] > 0
    a = admin(ctx)
    assert a.get("/api/me").json()["is_admin"] is True
    assert a.get("/api/settings").status_code == 200
    a.post("/api/admin/logout")
    assert a.get("/api/settings").status_code == 403


def test_setup_only_from_localhost(ctx):
    remote = client(ctx)
    assert remote.post("/api/admin/setup", json={"password": "matkhau1"}).status_code == 403
    local = client(ctx, LOCAL)
    r = local.post("/api/admin/setup", json={"password": "matkhau1"})
    assert r.status_code == 200 and local.get("/api/me").json()["is_admin"] is True
    assert local.post("/api/admin/setup", json={"password": "khac123"}).status_code == 409


def test_inspect_returns_codes(ctx, job_dir):
    c = named(ctx, "Hùng")
    r = c.post("/api/sources/inspect", json={"path": str(job_dir), "kind": "RUN"})
    assert r.status_code == 200 and [x["code"] for x in r.json()["codes"]][0] == "26-064689"
    r = c.post("/api/sources/inspect", json={"path": "C:\\nowhere", "kind": "RUN"})
    assert r.status_code == 400 and "được phép" in r.json()["error"]


def test_submit_duplicate_409_payload(ctx, job_dir):
    ctx["sched"].extra_env["FAKE_MODE"] = "hang"
    a = named(ctx, "Hùng")
    assert a.post("/api/runs", json={"path": str(job_dir), "kind": "RUN"}).status_code == 201
    b = named(ctx, "Minh", ("10.0.0.40", 1))
    r = b.post("/api/runs", json={"path": str(job_dir) + "\\", "kind": "RUN"})
    assert r.status_code == 409 and r.json()["run"]["user"] == "Hùng" and "Hùng" in r.json()["error"]


def test_need_confirm_then_rerun(ctx, job_dir):
    c = named(ctx, "Hùng")
    rid = c.post("/api/runs", json={"path": str(job_dir), "kind": "RUN"}).json()["id"]
    wait_final(ctx, rid)
    r = c.post("/api/runs", json={"path": str(job_dir), "kind": "RUN"})
    assert r.status_code == 409 and r.json()["error"] == "need_confirm" and r.json()["last_run"]["id"] == rid
    assert c.post("/api/runs", json={"path": str(job_dir), "kind": "RUN", "confirm_rerun": True}).status_code == 201


def test_history_scoped_to_user(ctx, jobs_root):
    a, b = named(ctx, "Hùng"), named(ctx, "Minh", ("10.0.0.41", 1))
    for c, n in ((a, "521005-01"), (b, "521005-02")):
        d = jobs_root / n
        d.mkdir()
        (d / "a.pdf").write_bytes(b"%PDF")
        c.post("/api/runs", json={"path": str(d), "kind": "RUN"})
    assert [r["job"] for r in a.get("/api/runs").json()["runs"]] == ["521005-01"]
    other_id = b.get("/api/runs").json()["runs"][0]["id"]
    # History lists only your runs, but anyone may open any run's details (DXF path, report) from the board.
    d = a.get(f"/api/runs/{other_id}")
    assert d.status_code == 200 and d.json()["mine"] is False and d.json()["can_cancel"] is False
    assert d.json()["can_rerun"] is False
    assert a.get(f"/api/runs/{other_id}/transcript").status_code == 403
    assert len(admin(ctx).get("/api/runs").json()["runs"]) == 2


def test_admin_rerun_stays_with_original_user(ctx, job_dir):
    c = named(ctx, "Phát", ("10.0.0.42", 1))
    rid = c.post("/api/runs", json={"path": str(job_dir), "kind": "RUN"}).json()["id"]
    wait_final(ctx, rid)
    new_id = admin(ctx).post(f"/api/runs/{rid}/rerun").json()["id"]
    assert ctx["store"].get_run(new_id)["user_name"] == "Phát"
    assert [r["id"] for r in c.get("/api/runs").json()["runs"]] == [new_id, rid]


def test_run_detail_has_report(ctx, job_dir):
    c = named(ctx, "Hùng")
    rid = c.post("/api/runs", json={"path": str(job_dir), "kind": "RUN"}).json()["id"]
    wait_final(ctx, rid)
    d = c.get(f"/api/runs/{rid}").json()
    assert d["status"] == "DONE" and "Báo cáo" in d["report_md"] and d["delivered"]
    assert c.get(f"/api/runs/{rid}/transcript").status_code == 403
    assert "tool_use" in admin(ctx).get(f"/api/runs/{rid}/transcript").text


def test_cancel_other_users_run_forbidden_admin_ok(ctx, job_dir):
    ctx["sched"].extra_env["FAKE_MODE"] = "hang"
    a = named(ctx, "Hùng")
    rid = a.post("/api/runs", json={"path": str(job_dir), "kind": "RUN"}).json()["id"]
    b = named(ctx, "Minh", ("10.0.0.42", 1))
    assert b.post(f"/api/runs/{rid}/cancel").status_code == 403
    assert admin(ctx).post(f"/api/runs/{rid}/cancel").status_code == 200
    assert wait_final(ctx, rid)["status"] == "CANCELLED"


def test_csv_and_bundle_admin_only(ctx, job_dir):
    c = named(ctx, "Hùng")
    rid = c.post("/api/runs", json={"path": str(job_dir), "kind": "RUN"}).json()["id"]
    wait_final(ctx, rid)
    assert c.get("/api/runs.csv").status_code == 403
    assert c.get(f"/api/runs/{rid}/bundle.zip").status_code == 403
    a = admin(ctx)
    assert a.get("/api/runs.csv").text.startswith("\ufeffid,")
    z = a.get(f"/api/runs/{rid}/bundle.zip")
    assert z.status_code == 200 and z.content[:2] == b"PK"


def test_review_items_and_attachment(ctx, job_dir):
    ctx["sched"].extra_env["FAKE_MODE"] = "preview"
    c = named(ctx, "Hùng")
    rid = c.post("/api/runs", json={"path": str(job_dir), "kind": "RUN"}).json()["id"]
    wait_final(ctx, rid)
    a = admin(ctx)
    items = a.get("/api/review-items").json()["items"]
    assert len(items) == 1 and items[0]["copy_text"].startswith("DUYỆT bài học: Kiểu gấp lạ")
    iid = items[0]["id"]
    r = a.post(f"/api/review-items/{iid}/attachment", files={"file": ("mau.txt", b"x")})
    assert r.status_code == 400
    r = a.post(f"/api/review-items/{iid}/attachment", files={"file": ("mau.dxf", b"0\nEOF\n")})
    assert r.status_code == 200 and r.json()["attachment"].endswith("mau.dxf")
    assert "mau.dxf" in a.get("/api/review-items").json()["items"][0]["copy_text"]
    assert a.patch(f"/api/review-items/{iid}", json={"status": "DONE"}).json()["status"] == "DONE"
    assert a.patch(f"/api/review-items/{iid}", json={"status": "WHAT"}).status_code == 400


def test_settings_validation(ctx):
    a = admin(ctx)
    assert a.put("/api/settings", json={"slots": 9}).status_code == 400
    s = a.put("/api/settings", json={"slots": 4, "allowed_roots": ["\\\\VietNam2025\\banve", " "]}).json()
    assert s["slots"] == 4 and s["allowed_roots"] == ["\\\\VietNam2025\\banve"] and "admin_hash" not in s


def test_notifications(ctx, job_dir):
    c = named(ctx, "Hùng")
    since = c.get("/api/me/notifications").json()["last_id"]
    rid = c.post("/api/runs", json={"path": str(job_dir), "kind": "RUN"}).json()["id"]
    wait_final(ctx, rid)
    n = c.get(f"/api/me/notifications?since={since}").json()["items"]
    assert n and n[0]["kind"] == "DONE" and n[0]["run_id"] == rid


def test_health(ctx):
    r = TestClient(ctx["app"]).get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"
