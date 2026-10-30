"""python -m luan_app [--port 8765] [--host 0.0.0.0] [--no-tray] [--no-browser] [--data-dir D] [--setup-password]

Runs in the background (pythonw) with a tray icon; a second start only opens the browser on the running one.
"""
from __future__ import annotations

import argparse
import getpass
import json
import logging
import logging.handlers
import socket
import sys
import threading
import urllib.request
import webbrowser

from .api import create_app
from .auth import Auth
from .config import PORT, load_paths
from .scheduler import Scheduler
from .slots import Slots
from .store import Store
from . import winutil

log = logging.getLogger("luan_app")


def already_running(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=1) as r:
            return json.loads(r.read().decode()).get("app") == "luan"
    except (OSError, ValueError):
        return False


def port_free(host: str, port: int) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind((host, port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def build(paths):
    store = Store(paths.db_path)
    auth = Auth(store)
    scheduler = Scheduler(store, paths, Slots(paths.repo_root, paths.slots_root), on_active_change=winutil.on_active_change)
    return create_app(paths, store, auth, scheduler), scheduler, store, auth


def _logging(paths) -> None:
    h = logging.handlers.RotatingFileHandler(paths.log_path, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8")
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(h)
    if sys.stderr:
        root.addHandler(logging.StreamHandler())


def _setup_password(paths) -> int:
    auth = Auth(Store(paths.db_path))
    for _ in range(3):
        pw = getpass.getpass("Mật khẩu Admin mới (tối thiểu 6 ký tự): ")
        if pw != getpass.getpass("Nhập lại: "):
            print("Hai lần nhập không khớp.")
            continue
        try:
            auth.set_admin_password(pw)
            print("Đã đặt mật khẩu Admin.")
            return 0
        except ValueError as e:
            print(e)
    return 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="luan_app")
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--data-dir")
    ap.add_argument("--no-tray", action="store_true")
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--setup-password", action="store_true")
    a = ap.parse_args(argv)
    paths = load_paths(data_dir=a.data_dir)
    if a.setup_password:
        return _setup_password(paths)
    local_url = f"http://127.0.0.1:{a.port}"
    if already_running(a.port):
        if not a.no_browser:
            webbrowser.open(local_url)
        return 0
    _logging(paths)
    if not port_free(a.host, a.port):
        msg = f"Cổng {a.port} đang bị chương trình khác dùng."
        log.error(msg)
        winutil.show_error("Luan App", msg)
        return 1

    import uvicorn
    app, scheduler, _store, _auth = build(paths)
    scheduler.recover_on_start()
    scheduler.start()
    server = uvicorn.Server(uvicorn.Config(app, host=a.host, port=a.port, log_config=None, access_log=False))
    lan_url = f"http://{winutil.lan_ip()}:{a.port}"
    log.info("Luan App on %s (LAN %s), data %s", local_url, lan_url, paths.data_dir)
    try:
        if a.no_tray:
            server.run()
            return 0
        t = threading.Thread(target=server.run, name="http", daemon=True)
        t.start()
        if not a.no_browser:
            threading.Timer(1.5, webbrowser.open, args=(local_url,)).start()
        from .tray import run_tray

        def quit_all():
            scheduler.stop(kill=True)
            server.should_exit = True
        run_tray(local_url, lan_url, scheduler, quit_all)
        t.join(10)
        return 0
    finally:
        scheduler.stop(kill=True)
        winutil.keep_awake(False)


if __name__ == "__main__":
    sys.exit(main())
