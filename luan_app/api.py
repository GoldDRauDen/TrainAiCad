"""HTTP API (spec §11). Permissions are checked here, never only in the UI."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import secrets
import subprocess
import threading
import time
from pathlib import Path

from fastapi import FastAPI, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles

from . import archive, sources
from .config import ADMIN_SESSION_S, BOARD_CACHE_S, SLOTS_MAX, SLOTS_MIN, USER_COOKIE_S
from .runner import claude_executable
from .scheduler import NeedConfirm
from .sources import SourceError
from .store import ACTIVE, FINAL, Duplicate, NameTaken

STATIC = Path(__file__).with_name("static")
LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost"}
REVIEW_STATUSES = {"PENDING", "COPIED", "DONE", "DISMISSED"}
MAX_ATTACH = 50 * 1024 * 1024
RUN_PUBLIC = ("id", "kind", "job", "path", "status", "slot", "queued_at", "started_at", "ended_at", "summary", "error",
              "codes", "codes_status", "activity", "activity_at", "verdict", "repo_touched", "rerun_of", "cancelled_by",
              "warnings", "delivered", "commit")


class ApiError(Exception):
    def __init__(self, status: int, error: str, **extra):
        super().__init__(error)
        self.status, self.payload = status, {"error": error, **extra}


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else ""


def create_app(paths, store, auth, scheduler, serve_static: bool = True) -> FastAPI:
    app = FastAPI(title="Luan App", docs_url=None, redoc_url=None, openapi_url=None)
    board_cache: dict = {}
    board_lock = threading.Lock()
    claude_check = {"at": 0.0, "value": None}

    # -- errors -----------------------------------------------------------
    @app.exception_handler(ApiError)
    async def _api_error(_req, e: ApiError):
        return JSONResponse(e.payload, status_code=e.status)

    @app.exception_handler(SourceError)
    async def _source_error(_req, e: SourceError):
        return JSONResponse({"error": e.message}, status_code=400)

    @app.exception_handler(PermissionError)
    async def _perm(_req, e):
        return JSONResponse({"error": str(e) or "Không có quyền."}, status_code=403)

    @app.exception_handler(ValueError)
    async def _value(_req, e):
        return JSONResponse({"error": str(e)}, status_code=400)

    @app.exception_handler(KeyError)
    async def _missing(_req, _e):
        return JSONResponse({"error": "Không tìm thấy."}, status_code=404)

    # -- csrf + cookie ----------------------------------------------------
    @app.middleware("http")
    async def csrf(request: Request, call_next):
        token = request.cookies.get("luan_csrf")
        if request.url.path.startswith("/api/") and request.method not in ("GET", "HEAD", "OPTIONS"):
            if not token or not secrets.compare_digest(request.headers.get("X-Luan-CSRF", ""), token):
                return JSONResponse({"error": "Phiên làm việc hết hạn, tải lại trang."}, status_code=403)
        response = await call_next(request)
        if not token:
            response.set_cookie("luan_csrf", secrets.token_urlsafe(24), max_age=USER_COOKIE_S, samesite="strict")
        return response

    # -- identity helpers -------------------------------------------------
    def current_user(request: Request) -> dict | None:
        u = store.user_by_uid(request.cookies.get("luan_uid"))
        if u:
            store.touch_user(u["uid"])
        return u

    def is_admin(request: Request) -> bool:
        return auth.is_admin(request.cookies.get("luan_admin"))

    def need_user(request: Request) -> dict:
        u = current_user(request)
        if not u:
            raise ApiError(401, "Cần nhập tên trước.")
        return u

    def need_admin(request: Request) -> None:
        if not is_admin(request):
            raise ApiError(403, "Chỉ Admin.")

    def actor(request: Request) -> tuple[dict, bool]:
        adm = is_admin(request)
        u = current_user(request)
        if not u and not adm:
            raise ApiError(401, "Cần nhập tên trước.")
        return (u or {"id": None, "name": "Admin"}), adm

    def run_view(r: dict, user: dict | None, adm: bool) -> dict:
        v = {k: r.get(k) for k in RUN_PUBLIC}
        v["user"] = r.get("user_name")
        v["mine"] = bool(user and r.get("user_id") == user.get("id"))
        v["can_cancel"] = r["status"] in ACTIVE and (adm or v["mine"])
        v["can_rerun"] = r["status"] in FINAL and (adm or v["mine"]) and (r["kind"] != "QA" or adm)
        return v

    def get_run_checked(run_id: int, request: Request) -> tuple[dict, dict, bool]:
        user, adm = actor(request)
        r = store.get_run(run_id)
        if not r:
            raise ApiError(404, "Không tìm thấy job.")
        if not adm and r["user_id"] != user.get("id"):
            raise ApiError(403, "Không có quyền xem job này.")
        return r, user, adm

    # -- me / admin -------------------------------------------------------
    @app.get("/api/me")
    def get_me(request: Request):
        u = current_user(request)
        return {"user": {"name": u["name"], "prefs": u.get("prefs") or {}} if u else None,
                "is_admin": is_admin(request), "has_admin_password": auth.has_admin_password(),
                "is_local": _client_ip(request) in LOCAL_HOSTS}

    @app.post("/api/me")
    async def set_me(request: Request):
        name = str((await request.json()).get("name") or "")
        u = current_user(request)
        try:
            u = store.rename_user(u["uid"], name) if u else store.create_user(name)
        except NameTaken:
            raise ApiError(400, "Tên đã có người dùng hoặc không hợp lệ. Chọn tên khác.")
        resp = JSONResponse({"user": {"name": u["name"], "prefs": u.get("prefs") or {}}})
        resp.set_cookie("luan_uid", u["uid"], max_age=USER_COOKIE_S, httponly=True, samesite="strict")
        return resp

    @app.put("/api/me/prefs")
    async def set_prefs(request: Request):
        u = need_user(request)
        prefs = (await request.json()).get("prefs") or {}
        if not isinstance(prefs, dict):
            raise ApiError(400, "prefs phải là object.")
        store.set_user_prefs(u["uid"], prefs)
        return {"prefs": prefs}

    def _admin_cookie(resp: Response, token: str) -> Response:
        resp.set_cookie("luan_admin", token, max_age=ADMIN_SESSION_S, httponly=True, samesite="strict")
        return resp

    @app.post("/api/admin/setup")
    async def admin_setup(request: Request):
        if _client_ip(request) not in LOCAL_HOSTS:
            raise ApiError(403, "Chỉ đặt mật khẩu lần đầu được trên máy Admin.")
        if auth.has_admin_password():
            raise ApiError(409, "Mật khẩu Admin đã được đặt.")
        auth.set_admin_password(str((await request.json()).get("password") or ""))
        token = auth.login(str((await request.json()).get("password")), _client_ip(request))
        return _admin_cookie(JSONResponse({"ok": True}), token)

    @app.post("/api/admin/login")
    async def admin_login(request: Request):
        ip = _client_ip(request)
        if auth.locked(ip):
            raise ApiError(423, "Sai mật khẩu quá nhiều lần, thử lại sau.", retry_after=auth.locked(ip))
        token = auth.login(str((await request.json()).get("password") or ""), ip)
        if not token:
            if auth.locked(ip):
                raise ApiError(423, "Sai mật khẩu quá nhiều lần, thử lại sau.", retry_after=auth.locked(ip))
            raise ApiError(401, "Sai mật khẩu.")
        return _admin_cookie(JSONResponse({"ok": True}), token)

    @app.post("/api/admin/logout")
    def admin_logout(request: Request):
        auth.logout(request.cookies.get("luan_admin"))
        resp = JSONResponse({"ok": True})
        resp.delete_cookie("luan_admin")
        return resp

    @app.post("/api/admin/password")
    async def admin_password(request: Request):
        need_admin(request)
        auth.set_admin_password(str((await request.json()).get("password") or ""))
        return {"ok": True}

    # -- jobs -------------------------------------------------------------
    @app.post("/api/sources/inspect")
    async def inspect(request: Request):
        actor(request)
        body = await request.json()
        kind = "QA" if body.get("kind") == "QA" else "RUN"
        info = sources.inspect(str(body.get("path") or ""), store.get_settings()["allowed_roots"], kind)
        last = store.last_final_run(info["path_key"])
        info["last_run"] = {"id": last["id"], "ended_at": last["ended_at"], "status": last["status"]} if last else None
        return info

    @app.post("/api/runs", status_code=201)
    async def submit(request: Request):
        user, adm = actor(request)
        body = await request.json()
        codes = body.get("codes")
        if codes is not None and (not isinstance(codes, list) or not all(isinstance(c, str) for c in codes)):
            raise ApiError(400, "Danh sách mã không hợp lệ.")
        try:
            rid = scheduler.submit(user, str(body.get("kind") or "RUN"), str(body.get("path") or ""), codes,
                                   bool(body.get("confirm_rerun")), adm)
        except Duplicate as e:
            r = e.run
            who = (store.user_by_id(r["user_id"]) or {}).get("name") or "Admin"
            since = (r.get("started_at") or r.get("queued_at") or "")[11:16]
            raise ApiError(409, f"Job này đang được {who} chạy, bắt đầu {since}.",
                           run={"id": r["id"], "job": r["job"], "user": who, "status": r["status"], "since": since})
        except NeedConfirm as e:
            r = e.last_run
            raise ApiError(409, "need_confirm", last_run={"id": r["id"], "ended_at": r["ended_at"], "status": r["status"]})
        return {"id": rid}

    def _filters(request: Request, user: dict, adm: bool) -> dict:
        q = request.query_params
        return dict(user_id=None if adm else user.get("id"), status=q.get("status") or None, kind=q.get("kind") or None,
                    date_from=q.get("from") or None, date_to=q.get("to") or None, q=q.get("q") or None,
                    limit=min(int(q.get("limit") or 200), 1000))

    @app.get("/api/runs")
    def list_runs(request: Request):
        user, adm = actor(request)
        f = _filters(request, user, adm)
        if adm and request.query_params.get("user"):
            u = next((x for x in store._q("SELECT * FROM users WHERE name = ? COLLATE NOCASE",
                                          (request.query_params["user"],))), None)
            f["user_id"] = u["id"] if u else -1
        return {"runs": [run_view(r, user, adm) for r in store.list_runs(**f)]}

    @app.get("/api/runs.csv")
    def runs_csv(request: Request):
        need_admin(request)
        user, adm = actor(request)
        text = archive.runs_csv(store.list_runs(**_filters(request, user, True)))
        return Response(text.encode("utf-8"), media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": 'attachment; filename="luan-runs.csv"'})

    @app.get("/api/runs/{run_id}")
    def run_detail(run_id: int, request: Request):
        r, user, adm = get_run_checked(run_id, request)
        v = run_view(r, user, adm)
        od = archive.run_dir(paths, run_id) / "out"
        try:
            v["report_md"] = (od / "report.md").read_text(encoding="utf-8")[:200_000]
        except OSError:
            v["report_md"] = None
        v["usage"] = r.get("usage")
        return v

    @app.post("/api/runs/{run_id}/cancel")
    def cancel(run_id: int, request: Request):
        user, adm = actor(request)
        scheduler.cancel(run_id, user, adm)
        return {"ok": True}

    @app.post("/api/runs/{run_id}/rerun", status_code=201)
    def rerun(run_id: int, request: Request):
        user, adm = actor(request)
        try:
            return {"id": scheduler.rerun(run_id, user, adm)}
        except Duplicate as e:
            raise ApiError(409, "Job này đang chạy.", run={"id": e.run["id"]})

    @app.get("/api/runs/{run_id}/transcript")
    def transcript(run_id: int, request: Request):
        need_admin(request)
        f = archive.run_dir(paths, run_id) / "transcript.jsonl"
        try:
            lines = f.read_text(encoding="utf-8", errors="replace").splitlines()[-2000:]
        except OSError:
            lines = []
        return PlainTextResponse("\n".join(lines))

    @app.get("/api/runs/{run_id}/bundle.zip")
    def bundle(run_id: int, request: Request):
        need_admin(request)
        if not store.get_run(run_id):
            raise ApiError(404, "Không tìm thấy job.")
        z = archive.bundle_zip(archive.run_dir(paths, run_id))
        return FileResponse(z, media_type="application/zip", filename=z.name)

    @app.post("/api/open-folder")
    async def open_folder(request: Request):
        need_admin(request)
        if _client_ip(request) not in LOCAL_HOSTS:
            raise ApiError(403, "Chỉ mở được thư mục trên máy Admin.")
        r = store.get_run(int((await request.json()).get("run_id") or 0))
        if not r:
            raise ApiError(404, "Không tìm thấy job.")
        info = sources.inspect(r["path"], store.get_settings()["allowed_roots"], r["kind"])
        target = os.path.join(info["job_dir"], "AI_L")
        if not os.path.isdir(target):
            target = info["job_dir"]
        if os.name == "nt":
            os.startfile(target)  # noqa: S606 - admin-only, local request, path from an allowed root
        return {"ok": True, "path": target}

    # -- board ------------------------------------------------------------
    def _claude_status() -> dict:
        if time.time() - claude_check["at"] < 60 and claude_check["value"]:
            return claude_check["value"]
        if scheduler.exe_override or os.environ.get("LUAN_CLAUDE_CMD"):
            val = {"ok": True, "version": "override"}
        else:
            try:
                exe = claude_executable(store.get_settings().get("claude_cmd"))
                out = subprocess.run(exe + ["--version"], capture_output=True, text=True, timeout=20,
                                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                val = {"ok": out.returncode == 0, "version": out.stdout.strip() or None}
            except Exception as e:
                val = {"ok": False, "version": None, "error": str(e)}
        claude_check.update(at=time.time(), value=val)
        return val

    def _board(user: dict | None, adm: bool) -> dict:
        settings = store.get_settings()
        today = dt.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat(timespec="seconds")
        active = store.active_runs()
        running = [r for r in active if r["status"] != "QUEUED"]
        queue = [r for r in active if r["status"] == "QUEUED"]
        done_today = store.list_runs(final_only=True, date_from=today, limit=30)
        ended_today = [r for r in done_today if (r.get("ended_at") or "") >= today]
        return {
            "me": {"name": (user or {}).get("name") or "Admin", "is_admin": adm},
            "slots": {"used": len(running), "total": int(settings["slots"])},
            "paused_until": scheduler.paused_until(),
            "stats": {"running": len(running), "queued": len(queue),
                      "done_today": sum(r["status"] == "DONE" for r in ended_today),
                      "review_today": sum(r["status"] == "REVIEW" for r in ended_today),
                      "error_today": sum(r["status"] == "ERROR" for r in ended_today)},
            "running": [run_view(r, user, adm) for r in running],
            "queue": [run_view(r, user, adm) for r in queue],
            "today": [run_view(r, user, adm) for r in sorted(ended_today, key=lambda r: r.get("ended_at") or "", reverse=True)],
            "claude": _claude_status() if adm else None,
            "utilization": scheduler.utilization if adm else None,
            "review_pending": store.review_pending_count() if adm else 0,
        }

    @app.get("/api/board")
    def board(request: Request):
        user, adm = actor(request)
        key = (user.get("id"), adm)
        with board_lock:
            hit = board_cache.get(key)
            if not hit or time.time() - hit[0] > BOARD_CACHE_S:
                body = json.dumps(_board(user if user.get("id") else None, adm), ensure_ascii=False, default=str)
                hit = (time.time(), body, '"' + hashlib.sha1(body.encode()).hexdigest() + '"')
                board_cache[key] = hit
        _, body, etag = hit
        if request.headers.get("if-none-match") == etag:
            return Response(status_code=304, headers={"ETag": etag})
        return Response(body, media_type="application/json", headers={"ETag": etag, "Cache-Control": "no-cache"})

    # -- review items -----------------------------------------------------
    def _copy_text(it: dict) -> str:
        lines = [f"DUYỆT bài học: {it['title']} — job {it.get('job')}, mã {it.get('code') or '?'}, thẻ {it.get('card') or '?'}",
                 it.get("detail") or "", f"Bằng chứng: {it.get('evidence') or '?'}", f"Nguồn: {it.get('path')}"]
        if it.get("attachment"):
            lines.append(f"Mẫu DXF: {it['attachment']}")
        return "\n".join(x for x in lines if x)

    @app.get("/api/review-items")
    def review_items(request: Request):
        need_admin(request)
        items = store.list_review_items(request.query_params.get("status") or None)
        for it in items:
            it["copy_text"] = _copy_text(it)
        return {"items": items}

    @app.patch("/api/review-items/{item_id}")
    async def review_update(item_id: int, request: Request):
        need_admin(request)
        status = (await request.json()).get("status")
        if status not in REVIEW_STATUSES:
            raise ApiError(400, "Trạng thái không hợp lệ.")
        if not store.get_review_item(item_id):
            raise ApiError(404, "Không tìm thấy.")
        store.update_review_item(item_id, status=status)
        return store.get_review_item(item_id)

    @app.post("/api/review-items/{item_id}/attachment")
    async def review_attach(item_id: int, request: Request, file: UploadFile):
        need_admin(request)
        if not store.get_review_item(item_id):
            raise ApiError(404, "Không tìm thấy.")
        name = os.path.basename(file.filename or "")
        if not name.lower().endswith(".dxf"):
            raise ApiError(400, "Chỉ nhận file .dxf.")
        data = await file.read(MAX_ATTACH + 1)
        if len(data) > MAX_ATTACH:
            raise ApiError(400, "File quá 50 MB.")
        d = paths.attachments_dir / str(item_id)
        d.mkdir(parents=True, exist_ok=True)
        target = d / name
        target.write_bytes(data)
        store.update_review_item(item_id, attachment=str(target))
        return {"attachment": str(target)}

    # -- settings / queue -------------------------------------------------
    def _public_settings() -> dict:
        s = store.get_settings()
        s.pop("admin_hash", None)
        return s

    @app.get("/api/settings")
    def get_settings(request: Request):
        need_admin(request)
        return _public_settings()

    @app.put("/api/settings")
    async def put_settings(request: Request):
        need_admin(request)
        body = await request.json()
        upd = {}
        if "slots" in body:
            n = int(body["slots"])
            if not SLOTS_MIN <= n <= SLOTS_MAX:
                raise ApiError(400, f"Số suất từ {SLOTS_MIN} đến {SLOTS_MAX}.")
            upd["slots"] = n
        if "timeout_min" in body:
            t = float(body["timeout_min"])
            if not 5 <= t <= 24 * 60:
                raise ApiError(400, "Thời gian tối đa từ 5 đến 1440 phút.")
            upd["timeout_min"] = t
        if "allowed_roots" in body:
            roots = body["allowed_roots"]
            if not isinstance(roots, list):
                raise ApiError(400, "Danh sách thư mục không hợp lệ.")
            upd["allowed_roots"] = [sources.clean(r) for r in roots if isinstance(r, str) and r.strip()]
        for key in ("model", "git_ref"):
            if key in body:
                upd[key] = str(body[key] or "").strip()
        if upd.get("git_ref") == "":
            upd["git_ref"] = "origin/main"
        store.set_settings(**upd)
        scheduler._wake.set()
        return _public_settings()

    @app.post("/api/queue/resume")
    def queue_resume(request: Request):
        need_admin(request)
        scheduler.resume_queue()
        return {"ok": True}

    # -- notifications / health ------------------------------------------
    @app.get("/api/me/notifications")
    def notifications(request: Request):
        u = need_user(request)
        since = int(request.query_params.get("since") or 0)
        return {"items": store.notifications(u["id"], since), "last_id": store.last_notification_id(u["id"])}

    @app.post("/api/me/notifications/seen")
    async def notifications_seen(request: Request):
        u = need_user(request)
        store.mark_seen(u["id"], int((await request.json()).get("upto") or 0))
        return {"ok": True}

    @app.get("/api/health")
    def health():
        return {"status": "ok", "app": "luan"}

    if serve_static and STATIC.is_dir():
        app.mount("/", StaticFiles(directory=str(STATIC), html=True), name="static")
    return app
