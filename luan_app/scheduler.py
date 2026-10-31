"""Queue -> slots -> one worker thread per run: prepare worktree, run Claude, archive, decide the final status."""
from __future__ import annotations

import datetime as dt
import logging
import os
import threading
import time
from dataclasses import dataclass, field

from . import archive, progress, sources, staging
from .config import SLOTS_MAX, SLOTS_MIN, USAGE_PAUSE_MIN
from .prompts import build_prompt
from .runner import NOT_LOGGED_IN, ClaudeProcess, build_command, claude_executable, kill_tree, same_program
from .store import ACTIVE, FINAL, Duplicate, now_iso

log = logging.getLogger("luan_app.scheduler")
KINDS = ("RUN", "QA")


class NeedConfirm(Exception):
    def __init__(self, last_run: dict):
        super().__init__("need_confirm")
        self.last_run = last_run


class _Cancelled(Exception):
    pass


@dataclass
class _Worker:
    run_id: int
    slot: int
    cancel: threading.Event = field(default_factory=threading.Event)
    proc: ClaudeProcess | None = None
    thread: threading.Thread | None = None


def _iso(ts: float) -> str:
    return dt.datetime.fromtimestamp(ts).isoformat(timespec="seconds")


class Scheduler:
    def __init__(self, store, paths, slots, clock=time.time, exe_override=None, extra_env=None,
                 poll_s=1.0, progress_s=2.0, on_active_change=None):
        self.store, self.paths, self.slots, self.clock = store, paths, slots, clock
        self.exe_override = exe_override
        self.extra_env = dict(extra_env or {})
        self.poll_s, self.progress_s = poll_s, progress_s
        self.on_active_change = on_active_change
        self.utilization: float | None = None
        self._workers: dict[int, _Worker] = {}     # slot -> worker
        self._lock = threading.RLock()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._loop: threading.Thread | None = None

    # -- submit / cancel / rerun -----------------------------------------
    def submit(self, user: dict, kind: str, path: str, codes, confirm_rerun: bool, is_admin: bool,
               rerun_of: int | None = None) -> int:
        if kind not in KINDS:
            raise ValueError("Loại job không hợp lệ.")
        if kind == "QA" and not is_admin:
            raise PermissionError("Chỉ Admin được chạy QA.")
        settings = self.store.get_settings()
        info = sources.inspect(path, settings["allowed_roots"], kind)
        codes = sources.validate_codes(codes, info)
        active = self.store.active_run_for(info["path_key"])
        if active:
            raise Duplicate(active)
        if not confirm_rerun:
            last = self.store.last_final_run(info["path_key"])
            if last:
                raise NeedConfirm(last)
        rid = self.store.insert_run(kind, info["path"], info["path_key"], info["job"], codes, user.get("id"), rerun_of)
        self._wake.set()
        return rid

    def cancel(self, run_id: int, by_user: dict, is_admin: bool) -> None:
        run = self.store.get_run(run_id)
        if not run:
            raise KeyError(run_id)
        if not is_admin and run["user_id"] != by_user.get("id"):
            raise PermissionError("Chỉ người chạy hoặc Admin được hủy job này.")
        by = "Admin" if is_admin else by_user.get("name")
        if run["status"] == "QUEUED" and self.store.cancel_queued(run_id, by):
            self.store.notify(run["user_id"], run_id, "CANCELLED", f"{run['job']} đã hủy")
            return
        if run["status"] in FINAL:
            raise ValueError("Job đã kết thúc.")
        self.store.update_run(run_id, cancelled_by=by)
        with self._lock:
            w = next((w for w in self._workers.values() if w.run_id == run_id), None)
        if w:
            w.cancel.set()
            if w.proc:
                w.proc.kill()

    def rerun(self, run_id: int, user: dict, is_admin: bool) -> int:
        run = self.store.get_run(run_id)
        if not run:
            raise KeyError(run_id)
        if not is_admin and run["user_id"] != user.get("id"):
            raise PermissionError("Chỉ người chạy hoặc Admin được chạy lại job này.")
        if run["status"] not in FINAL:
            raise ValueError("Job chưa kết thúc.")
        return self.submit(user, run["kind"], run["path"], run.get("codes"), True, is_admin, rerun_of=run_id)

    def resume_queue(self) -> None:
        self.store.set_settings(queue_paused_until=None)
        self._wake.set()

    # -- loop -------------------------------------------------------------
    def paused_until(self) -> str | None:
        until = self.store.get_settings().get("queue_paused_until")
        if until and dt.datetime.fromisoformat(until).timestamp() > self.clock():
            return until
        if until:
            self.store.set_settings(queue_paused_until=None)
        return None

    def active_count(self) -> int:
        with self._lock:
            return sum(1 for w in self._workers.values() if w.thread and w.thread.is_alive())

    def tick(self) -> None:
        with self._lock:
            for k in [k for k, w in self._workers.items() if not (w.thread and w.thread.is_alive())]:
                del self._workers[k]
            if self.paused_until():
                return
            total = max(SLOTS_MIN, min(SLOTS_MAX, int(self.store.get_settings()["slots"])))
            free = [k for k in range(1, total + 1) if k not in self._workers]
            if not free:
                return
            queued = self.store.queued_runs()
            for k in free:
                while queued:
                    run = queued.pop(0)
                    if self.store.claim_run(run["id"], k):
                        break
                else:
                    return
                w = _Worker(run_id=run["id"], slot=k)
                w.thread = threading.Thread(target=self._work, args=(run, w), name=f"run-{run['id']}", daemon=True)
                self._workers[k] = w
                w.thread.start()
                self._changed()

    def _changed(self) -> None:
        if self.on_active_change:
            try:
                self.on_active_change(self.active_count())
            except Exception:  # keep-awake is best effort
                log.exception("on_active_change")

    def start(self) -> None:
        if self._loop:
            return
        self._stop.clear()

        def loop():
            while not self._stop.is_set():
                try:
                    self.tick()
                except Exception:
                    log.exception("tick")
                self._wake.wait(self.poll_s)
                self._wake.clear()
        self._loop = threading.Thread(target=loop, name="scheduler", daemon=True)
        self._loop.start()

    def stop(self, kill: bool = True) -> None:
        self._stop.set()
        self._wake.set()
        if self._loop:
            self._loop.join(timeout=5)
            self._loop = None
        if kill:
            with self._lock:
                workers = list(self._workers.values())
            for w in workers:
                w.cancel.set()
                if w.proc:
                    w.proc.kill()
            for w in workers:
                if w.thread:
                    w.thread.join(timeout=15)

    def running_snapshot(self) -> dict[int, dict]:
        with self._lock:
            return {w.run_id: {"slot": w.slot, "activity": w.proc.activity if w.proc else "",
                               "activity_at": w.proc.activity_at if w.proc else None} for w in self._workers.values()}

    # -- recovery ---------------------------------------------------------
    def recover_on_start(self) -> None:
        for r in self.store.active_runs():
            if r["status"] == "QUEUED":
                continue
            if r.get("pid") and same_program(r["pid"], r.get("pid_name")):
                kill_tree(r["pid"])
            self.store.update_run(r["id"], status="ERROR", error="Bị ngắt do app khởi động lại",
                                  summary="Bị ngắt do app khởi động lại", ended_at=now_iso())
            self.store.notify(r["user_id"], r["id"], "ERROR", f"{r['job']} bị ngắt do app khởi động lại")
            if r.get("slot"):
                try:
                    self.slots.reset(r["slot"])
                except Exception:
                    log.exception("reset slot %s", r["slot"])

    # -- one run ----------------------------------------------------------
    def _exe(self, settings) -> list[str]:
        ov = self.exe_override or os.environ.get("LUAN_CLAUDE_CMD") or settings.get("claude_cmd")
        return list(ov) if isinstance(ov, (list, tuple)) else claude_executable(ov)

    def _work(self, run: dict, w: _Worker) -> None:
        rid, k = run["id"], w.slot
        rd, od = archive.run_dir(self.paths, rid), archive.out_dir(self.paths, rid)
        settings = self.store.get_settings()
        warnings: list[str] = []
        proc: ClaudeProcess | None = None
        info = None
        exit_code, timed_out, started = None, False, None
        try:
            info = sources.inspect(run["path"], settings["allowed_roots"], run["kind"])
            sha, warns = self.slots.prepare(k, settings.get("git_ref") or "origin/main")
            warnings += warns
            self.store.update_run(rid, commit=sha, warnings=warnings)
            if w.cancel.is_set():
                raise _Cancelled()
            st = staging.stage_in(sources.native(info["job_dir"]), sources.native(run["path"]), self.slots.path(k), run["job"])
            if w.cancel.is_set():
                raise _Cancelled()
            env = dict(os.environ, PYTHONUTF8="1", LUAN_RUN_DIR=str(od), **self.extra_env)
            cmd = build_command(self._exe(settings), od, str(st.local_dir), settings.get("model") or "")
            proc = ClaudeProcess()
            w.proc = proc
            started = now_iso()
            prompt = build_prompt(run["kind"], st.local_target, run.get("codes"), od,
                                  share_path=run["path"], local_job_dir=str(st.local_dir))
            proc.start(cmd, cwd=self.slots.path(k), env=env, prompt=prompt,
                       transcript=rd / "transcript.jsonl", stderr_log=rd / "stderr.log")
            self.store.update_run(rid, status="RUNNING", started_at=started, pid=proc.pid,
                                  pid_name=os.path.basename(cmd[0]))
            if w.cancel.is_set():
                proc.kill()
            deadline = self.clock() + float(settings["timeout_min"]) * 60
            last = 0.0
            while exit_code is None:
                exit_code = proc.wait(min(1.0, self.progress_s))
                now = self.clock()
                if now - last >= self.progress_s or exit_code is not None:
                    last = now
                    rows = progress.code_rows(progress.find_job_state(self.slots.path(k), run["job"]))
                    self.store.update_run(rid, activity=proc.activity,
                                          activity_at=_iso(proc.activity_at) if proc.activity_at else None,
                                          codes_status=rows)
                    if proc.utilization is not None:
                        self.utilization = proc.utilization
                if exit_code is None and (w.cancel.is_set() or now > deadline):
                    timed_out = not w.cancel.is_set()
                    proc.kill()
                    exit_code = proc.wait(15)
                    if exit_code is None:
                        exit_code = -1
            self._finish(run, w, info, proc, exit_code, timed_out, started, warnings, st)
        except _Cancelled:
            self._close(run, w, "CANCELLED", "Đã hủy", None, warnings)
        except Exception as e:  # SourceError, SlotError, RunnerError, unexpected
            msg = getattr(e, "message", None) or str(e) or e.__class__.__name__
            log.exception("run %s", rid)
            if proc and proc.poll() is None:
                proc.kill()
            self._close(run, w, "ERROR", msg, msg, warnings)
        finally:
            with self._lock:
                if self._workers.get(k) is w:
                    del self._workers[k]
            self._changed()
            self._wake.set()

    def _finish(self, run, w, info, proc, exit_code, timed_out, started, warnings, st=None) -> None:
        rid, k = run["id"], w.slot
        self.store.update_run(rid, status="FINISHING")
        rd, od = archive.run_dir(self.paths, rid), archive.out_dir(self.paths, rid)
        slot_dir = self.slots.path(k)
        try:
            archive.archive_work(slot_dir, run["job"], rd)
        except OSError as e:
            warnings.append(f"Không lưu được .work: {e}")
        if st is not None and run["kind"] == "RUN":
            try:
                staging.stage_out(st)
            except OSError as e:
                warnings.append(f"Không chép được DXF về AI_L trên server: {e}")
        state = progress.find_job_state(slot_dir, run["job"])
        rows = progress.code_rows(state)
        result = progress.read_result(od)
        delivered = progress.delivered(info["job_dir"], started) if run["kind"] == "RUN" else []
        items, warns = progress.read_review_items(od)
        warnings += warns
        cancelled = w.cancel.is_set()
        status, summary = progress.final_status(run["kind"], state, result, delivered, exit_code, cancelled)
        error = None
        if not cancelled:
            if proc.usage_limit:
                status, error = "ERROR", "Hết hạn mức Claude"
                until = proc.reset_at if proc.reset_at and proc.reset_at > self.clock() else self.clock() + USAGE_PAUSE_MIN * 60
                self.store.set_settings(queue_paused_until=_iso(until))
            elif timed_out:
                status, error = "ERROR", f"Quá thời gian ({float(self.store.get_settings()['timeout_min']):g} phút)"
            elif proc.auth_failed:
                status, error = "ERROR", NOT_LOGGED_IN + (f"\n{proc.error_text}" if proc.error_text else "")
            elif exit_code not in (0, None):
                tail = "\n".join(t for t in (proc.error_text, proc.stderr_tail()) if t)
                error = f"Claude thoát với mã {exit_code}" + (f"\n{tail}" if tail else "")
            elif status == "ERROR":
                error = summary
        touched = []
        try:
            touched = self.slots.touched(k)
            if touched:
                warnings.append("Job đã sửa file repo, đã khôi phục: " + ", ".join(t[3:] for t in touched[:5]))
                self.slots.reset(k)
        except Exception as e:
            warnings.append(f"Không kiểm tra được worktree: {e}")
        if items:
            self.store.add_review_items(rid, items)
        fields = dict(status=status, ended_at=now_iso(), exit_code=exit_code, verdict=(result or {}).get("verdict"),
                      summary=summary if not error or status != "ERROR" else (summary or error),
                      codes_status=rows, delivered=delivered, usage=proc.usage or None, error=error,
                      warnings=warnings, repo_touched=1 if touched else 0, activity=None)
        if status == "ERROR" and error and error.startswith(("Hết hạn mức", "Quá thời gian", NOT_LOGGED_IN)):
            fields["summary"] = error.splitlines()[0]
        archive.write_meta(rd, {**(self.store.get_run(rid) or run), **fields}, {})  # on disk before the run looks final
        if self.store.finish_run(rid, **fields):
            self.store.index_run(rid, progress.search_text(run, rows, result))
            self._notify(run, status, fields["summary"])
        archive.write_meta(rd, self.store.get_run(rid) or run, {})

    def _close(self, run, w, status, summary, error, warnings) -> None:
        rid = run["id"]
        fields = dict(status=status, summary=summary, error=error, ended_at=now_iso(), warnings=warnings, activity=None)
        if self.store.finish_run(rid, **fields):
            self.store.index_run(rid, progress.search_text(run, [], None) + " " + (error or ""))
            self._notify(run, status, summary)
        try:
            archive.write_meta(archive.run_dir(self.paths, rid), self.store.get_run(rid) or run, {})
        except OSError:
            pass

    def _notify(self, run, status, summary) -> None:
        words = {"DONE": "xong", "REVIEW": "cần xem", "ERROR": "lỗi", "CANCELLED": "đã hủy"}
        self.store.notify(run["user_id"], run["id"], status, f"{run['job']} {words.get(status, status)}: {summary}")
