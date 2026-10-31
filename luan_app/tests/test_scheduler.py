import json
import os
import sys
import time
from pathlib import Path

import pytest

from luan_app import archive
from luan_app.runner import pid_alive
from luan_app.scheduler import NeedConfirm, Scheduler
from luan_app.slots import Slots
from luan_app.sources import SourceError
from luan_app.store import FINAL, Duplicate

FAKE = Path(__file__).with_name("fake_claude.py")


@pytest.fixture
def sched(store, paths, jobs_root):
    store.set_settings(allowed_roots=[str(jobs_root)], slots=3)
    s = Scheduler(store, paths, Slots(paths.repo_root, paths.slots_root),
                  exe_override=[sys.executable, str(FAKE)], extra_env={"FAKE_MODE": "ok"}, progress_s=0.2)
    yield s
    s.stop()


@pytest.fixture
def user(store):
    return store.create_user("Hùng")


def mkjob(jobs_root, name):
    d = jobs_root / name
    d.mkdir()
    (d / "a.pdf").write_bytes(b"%PDF")
    return d


def wait_for(sched, store, rid, statuses, timeout=30):
    end = time.time() + timeout
    while time.time() < end:
        sched.tick()
        r = store.get_run(rid)
        if r["status"] in statuses:
            return r
        time.sleep(0.1)
    raise AssertionError(f"run {rid} stuck in {store.get_run(rid)['status']}")


def test_full_run_done(sched, store, user, paths, job_dir):
    rid = sched.submit(user, "RUN", str(job_dir), None, confirm_rerun=False, is_admin=False)
    r = wait_for(sched, store, rid, FINAL)
    assert r["status"] == "DONE", r
    assert r["commit"] and r["delivered"] and r["summary"] == "fake ok"
    rd = archive.run_dir(paths, rid)
    assert (rd / "transcript.jsonl").is_file() and (rd / "work" / "521030-10" / "job_state.json").is_file()
    assert (rd / "meta.json").is_file()
    assert [n["kind"] for n in store.notifications(user["id"])] == ["DONE"]
    assert Slots(paths.repo_root, paths.slots_root).touched(r["slot"]) == []


def test_preview_becomes_review_and_review_items_saved(sched, store, user, job_dir):
    sched.extra_env["FAKE_MODE"] = "preview"
    rid = sched.submit(user, "RUN", str(job_dir), ["26-064687"], confirm_rerun=False, is_admin=False)
    r = wait_for(sched, store, rid, FINAL)
    assert r["status"] == "REVIEW" and r["codes"] == ["26-064687"]
    items = store.list_review_items()
    assert len(items) == 1 and items[0]["run_id"] == rid and items[0]["status"] == "PENDING"
    assert [x["id"] for x in store.list_runs(q="Nobi")] == [rid]


def test_three_parallel_fourth_waits(sched, store, user, jobs_root):
    sched.extra_env["FAKE_MODE"] = "hang"
    ids = [sched.submit(user, "RUN", str(mkjob(jobs_root, f"52100{i}-01")), None, False, False) for i in range(4)]
    for rid in ids[:3]:
        wait_for(sched, store, rid, ("RUNNING",))
    sched.tick()
    assert store.get_run(ids[3])["status"] == "QUEUED"
    sched.cancel(ids[0], user, is_admin=False)
    wait_for(sched, store, ids[0], ("CANCELLED",))
    wait_for(sched, store, ids[3], ("RUNNING",))


def test_duplicate_path_rejected(sched, store, user, job_dir):
    sched.extra_env["FAKE_MODE"] = "hang"
    sched.submit(user, "RUN", str(job_dir), None, False, False)
    other = store.create_user("Minh")
    variant = (str(job_dir).upper() if os.name == "nt" else str(job_dir)) + "\\"  # posix paths are case-sensitive
    with pytest.raises(Duplicate) as e:
        sched.submit(other, "RUN", variant.replace("\\", "/"), None, False, False)
    assert e.value.run["user_id"] == user["id"]


def test_rerun_needs_confirm(sched, store, user, job_dir):
    rid = sched.submit(user, "RUN", str(job_dir), None, False, False)
    wait_for(sched, store, rid, FINAL)
    with pytest.raises(NeedConfirm) as e:
        sched.submit(user, "RUN", str(job_dir), None, False, False)
    assert e.value.last_run["id"] == rid
    rid2 = sched.rerun(rid, user, is_admin=False)
    assert store.get_run(rid2)["rerun_of"] == rid


def test_cancel_queued_and_running(sched, store, user, jobs_root):
    sched.extra_env["FAKE_MODE"] = "hang"
    store.set_settings(slots=1)
    a = sched.submit(user, "RUN", str(mkjob(jobs_root, "521001-01")), None, False, False)
    b = sched.submit(user, "RUN", str(mkjob(jobs_root, "521001-02")), None, False, False)
    wait_for(sched, store, a, ("RUNNING",))
    sched.cancel(b, user, is_admin=False)
    assert store.get_run(b)["status"] == "CANCELLED"
    other = store.create_user("Minh")
    with pytest.raises(PermissionError):
        sched.cancel(a, other, is_admin=False)
    sched.cancel(a, {"id": None, "name": "Admin"}, is_admin=True)
    r = wait_for(sched, store, a, FINAL, timeout=10)
    assert r["status"] == "CANCELLED" and r["cancelled_by"] == "Admin"


def test_timeout_marks_error(sched, store, user, job_dir):
    sched.extra_env["FAKE_MODE"] = "hang"
    store.set_settings(timeout_min=0.02)
    rid = sched.submit(user, "RUN", str(job_dir), None, False, False)
    r = wait_for(sched, store, rid, FINAL)
    assert r["status"] == "ERROR" and "Quá thời gian" in r["error"]


def test_usage_limit_pauses_queue(sched, store, user, jobs_root):
    store.set_settings(slots=1)
    sched.extra_env["FAKE_MODE"] = "limit"
    a = sched.submit(user, "RUN", str(mkjob(jobs_root, "521002-01")), None, False, False)
    r = wait_for(sched, store, a, FINAL)
    assert r["status"] == "ERROR" and "Hết hạn mức" in r["error"]
    assert store.get_settings()["queue_paused_until"]
    sched.extra_env["FAKE_MODE"] = "ok"
    b = sched.submit(user, "RUN", str(mkjob(jobs_root, "521002-02")), None, False, False)
    for _ in range(5):
        sched.tick()
        time.sleep(0.1)
    assert store.get_run(b)["status"] == "QUEUED"
    sched.resume_queue()
    assert wait_for(sched, store, b, FINAL)["status"] == "DONE"


def test_crash_is_error_with_stderr_tail(sched, store, user, job_dir):
    sched.extra_env["FAKE_MODE"] = "crash"
    rid = sched.submit(user, "RUN", str(job_dir), None, False, False)
    r = wait_for(sched, store, rid, FINAL)
    assert r["status"] == "ERROR" and "fake crash" in r["error"]


def test_not_logged_in_says_so(sched, store, user, job_dir):
    sched.extra_env["FAKE_MODE"] = "nologin"
    rid = sched.submit(user, "RUN", str(job_dir), None, False, False)
    r = wait_for(sched, store, rid, FINAL)
    assert r["status"] == "ERROR" and "claude auth login" in r["summary"] and "Not logged in" in r["error"]


def test_recover_on_start_kills_orphan(sched, store, user, paths, job_dir):
    sched.extra_env["FAKE_MODE"] = "hang"
    rid = sched.submit(user, "RUN", str(job_dir), None, False, False)
    r = wait_for(sched, store, rid, ("RUNNING",))
    pid = r["pid"]
    assert pid_alive(pid)
    fresh = Scheduler(store, paths, Slots(paths.repo_root, paths.slots_root), exe_override=[sys.executable, str(FAKE)])
    fresh.recover_on_start()
    r = store.get_run(rid)
    assert r["status"] == "ERROR" and "khởi động lại" in r["error"]
    for _ in range(50):
        if not pid_alive(pid):
            break
        time.sleep(0.1)
    assert not pid_alive(pid)
    time.sleep(1.5)  # the old worker finishes but must not overwrite the recovered status
    assert store.get_run(rid)["status"] == "ERROR"


def test_recover_does_not_kill_reused_pid(sched, store, user, paths, job_dir):
    """After a reboot the stored pid may belong to another program: never kill it."""
    import subprocess
    other = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    try:
        rid = store.insert_run("RUN", str(job_dir), "k-reused", "J", None, user["id"])
        store.update_run(rid, status="RUNNING", pid=other.pid, pid_name="claude.exe", slot=1)
        Scheduler(store, paths, Slots(paths.repo_root, paths.slots_root)).recover_on_start()
        assert store.get_run(rid)["status"] == "ERROR"
        time.sleep(0.5)
        assert other.poll() is None and pid_alive(other.pid)
    finally:
        other.kill()
        other.wait()


def test_repo_touched_flagged(sched, store, user, paths, job_dir):
    sched.extra_env["FAKE_MODE"] = "touch"
    rid = sched.submit(user, "RUN", str(job_dir), None, False, False)
    r = wait_for(sched, store, rid, FINAL)
    assert r["repo_touched"] == 1 and any("sửa file repo" in w for w in r["warnings"])
    assert Slots(paths.repo_root, paths.slots_root).touched(r["slot"]) == []


def test_qa_requires_admin(sched, store, user, job_dir):
    with pytest.raises(PermissionError):
        sched.submit(user, "QA", str(job_dir), None, False, False)
    rid = sched.submit(user, "QA", str(job_dir), None, False, True)
    r = wait_for(sched, store, rid, FINAL)
    assert r["status"] == "DONE" and r["kind"] == "QA"


def test_submit_rejects_bad_path(sched, user, tmp_path):
    with pytest.raises(SourceError):
        sched.submit(user, "RUN", str(tmp_path), None, False, False)
