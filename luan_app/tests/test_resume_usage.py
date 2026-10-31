"""Model + effort + quota per run, resume of a broken E2E run, the runs finder, Sonnet/high defaults."""
import json

from luan_app import archive
from luan_app import runs as runs_cli
from luan_app.prompts import build_prompt
from luan_app.store import FINAL
from luan_app.tests.test_api import admin, ctx, named, wait_final  # noqa: F401 (fixtures)
from luan_app.tests.test_scheduler import sched, user, wait_for  # noqa: F401 (fixtures)


def test_run_records_model_effort_and_quota(sched, store, user, job_dir):  # noqa: F811
    rid = sched.submit(user, "RUN", str(job_dir), None, confirm_rerun=False, is_admin=False)
    u = wait_for(sched, store, rid, FINAL)["usage"]
    assert u["model"] == "fake" and u["effort"] == "high" and u["num_turns"] == 3 and u["cost_usd"] == 0.0
    assert u["five_hour"] == [0.42, 0.42] and u["parallel"] is False
    assert u["input_tokens"] == 10                                   # the CLI's own usage is kept as well


def test_old_empty_model_setting_means_sonnet(sched, store, user, job_dir, monkeypatch):  # noqa: F811
    store.set_settings(model="")                                     # saved by an older version of the app
    seen = {}
    real = __import__("luan_app.scheduler", fromlist=["build_command"]).build_command

    def spy(exe, out_dir, job_dir_, model, effort=""):
        seen.update(model=model, effort=effort)
        return real(exe, out_dir, job_dir_, model, effort)
    monkeypatch.setattr("luan_app.scheduler.build_command", spy)
    rid = sched.submit(user, "RUN", str(job_dir), None, confirm_rerun=False, is_admin=False)
    wait_for(sched, store, rid, FINAL)
    assert seen == {"model": "sonnet", "effort": "high"}


def test_resume_only_broken_e2e_and_restores_work(sched, store, user, paths, job_dir):  # noqa: F811
    rid = sched.submit(user, "RUN", str(job_dir), None, confirm_rerun=False, is_admin=False)
    run = wait_for(sched, store, rid, FINAL)
    assert run["status"] == "DONE" and not archive.resumable(paths, run)   # finished runs are rerun, not resumed
    store.update_run(rid, status="ERROR", error="Quá thời gian (120 phút)")
    marker = archive.run_dir(paths, rid) / "work" / "521030-10" / "make" / "marker.txt"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("half done", encoding="utf-8")
    assert archive.resumable(paths, store.get_run(rid))
    new = sched.resume(rid, user, is_admin=False)
    r = wait_for(sched, store, new, FINAL)
    assert int(r["resume_of"]) == rid and r["rerun_of"] == rid
    assert (archive.run_dir(paths, new) / "work" / "521030-10" / "make" / "marker.txt").read_text(encoding="utf-8") == "half done"


def test_resume_prompt_says_continue():
    t = build_prompt("RUN", "C:\\s\\.work\\J\\source", None, archive.Path("C:/o"), job="521030-10", resume_of=7)
    assert "LÀM TIẾP lượt #7" in t and "job.py status 521030-10" in t and "Không chạy lại job.py init" in t


def test_qa_prompt_is_qa_only_and_lean():
    t = build_prompt("QA", "C:\\s\\.work\\J\\source", None, archive.Path("C:/o"), job="521030-10")
    assert "Chỉ QA, không làm make" in t and "QA\\, không để trong make" in t
    assert "--help" in t and "không quét cả repo" in t


def test_resume_api_permissions_and_settings(ctx, job_dir):  # noqa: F811
    c, other = named(ctx, "Hùng"), named(ctx, "Minh", ("10.0.0.41", 1))
    rid = c.post("/api/runs", json={"path": str(job_dir), "kind": "RUN"}).json()["id"]
    wait_final(ctx, rid)
    assert c.get(f"/api/runs/{rid}").json()["can_resume"] is False
    ctx["store"].update_run(rid, status="CANCELLED")
    assert c.get(f"/api/runs/{rid}").json()["can_resume"] is True
    assert other.get(f"/api/runs/{rid}").json()["can_resume"] is False
    assert other.post(f"/api/runs/{rid}/resume").status_code == 403
    assert c.post(f"/api/runs/{rid}/resume").status_code == 201
    a = admin(ctx)
    assert a.put("/api/settings", json={"effort": "extreme"}).status_code == 400
    s = a.put("/api/settings", json={"effort": "xhigh", "model": ""}).json()
    assert s["effort"] == "xhigh" and s["model"] == "sonnet"


def test_runs_cli_lists_and_shows(sched, store, user, paths, job_dir, capsys, monkeypatch):  # noqa: F811
    rid = sched.submit(user, "RUN", str(job_dir), None, confirm_rerun=False, is_admin=False)
    wait_for(sched, store, rid, FINAL)
    monkeypatch.setenv("LUAN_DATA_DIR", str(paths.data_dir))
    assert runs_cli.main(["521030-10"]) == 0
    out = capsys.readouterr().out
    assert f"#{rid}" in out and str(paths.runs_dir) in out
    assert runs_cli.main(["--id", str(rid)]) == 0
    d = json.loads(capsys.readouterr().out)
    assert d["files"]["job_state"].endswith("job_state.json") and d["usage"]["model"] == "fake"
