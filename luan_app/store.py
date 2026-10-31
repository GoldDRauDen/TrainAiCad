"""SQLite state: users, runs, review items, notifications, settings, admin sessions.

One connection per thread (WAL); every method returns plain dicts.
"""
from __future__ import annotations

import datetime as dt
import json
import secrets
import sqlite3
import threading
import time
from pathlib import Path

from .config import DEFAULT_SETTINGS

ACTIVE = ("QUEUED", "PREPARING", "RUNNING", "FINISHING")
FINAL = ("DONE", "REVIEW", "ERROR", "CANCELLED")
RESERVED_NAMES = {"admin", "administrator", "quản trị"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY, uid TEXT UNIQUE NOT NULL, name TEXT UNIQUE NOT NULL COLLATE NOCASE,
  created_at TEXT, last_seen TEXT, prefs_json TEXT DEFAULT '{}');
CREATE TABLE IF NOT EXISTS runs(
  id INTEGER PRIMARY KEY, kind TEXT NOT NULL, path TEXT NOT NULL, path_key TEXT NOT NULL, job TEXT,
  codes_json TEXT, user_id INTEGER, status TEXT NOT NULL DEFAULT 'QUEUED', slot INTEGER, pid INTEGER,
  "commit" TEXT, queued_at TEXT, started_at TEXT, ended_at TEXT, exit_code INTEGER, error TEXT,
  verdict TEXT, summary TEXT, codes_status_json TEXT, repo_touched INTEGER DEFAULT 0,
  cancelled_by TEXT, rerun_of INTEGER, activity TEXT, activity_at TEXT, delivered_json TEXT,
  usage_json TEXT, warnings_json TEXT, pid_name TEXT, result_json TEXT, job_dir TEXT, resume_of INTEGER);
CREATE INDEX IF NOT EXISTS runs_key_status ON runs(path_key, status);
CREATE VIRTUAL TABLE IF NOT EXISTS run_search USING fts5(run_id UNINDEXED, search_text);
CREATE TABLE IF NOT EXISTS review_items(
  id INTEGER PRIMARY KEY, run_id INTEGER, type TEXT, code TEXT, card TEXT, title TEXT, detail TEXT,
  evidence TEXT, status TEXT DEFAULT 'PENDING', attachment TEXT, created_at TEXT, updated_at TEXT, author TEXT, author_id INTEGER);
CREATE TABLE IF NOT EXISTS notifications(
  id INTEGER PRIMARY KEY, user_id INTEGER, run_id INTEGER, kind TEXT, text TEXT, created_at TEXT, seen_at TEXT);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value_json TEXT);
CREATE TABLE IF NOT EXISTS admin_sessions(token_hash TEXT PRIMARY KEY, created_at REAL, expires_at REAL, ip TEXT);
"""

JSON_COLS = {"codes_json": "codes", "codes_status_json": "codes_status", "delivered_json": "delivered",
             "usage_json": "usage", "warnings_json": "warnings", "prefs_json": "prefs", "result_json": "result"}


class NameTaken(Exception):
    pass


class Duplicate(Exception):
    def __init__(self, run: dict):
        super().__init__("duplicate active run")
        self.run = run


def now_iso() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def _row(r: sqlite3.Row | None) -> dict | None:
    if r is None:
        return None
    d = dict(r)
    for col, key in JSON_COLS.items():
        if col in d:
            raw = d.pop(col)
            d[key] = json.loads(raw) if raw else None
    return d


class Store:
    def __init__(self, db_path: Path):
        self.db_path = str(db_path)
        self._local = threading.local()
        self._conn().executescript(SCHEMA)  # executescript commits on its own
        for table, cols in (("runs", ("pid_name", "result_json", "job_dir", "resume_of")), ("review_items", ("author", "author_id"))):
            have = {r[1] for r in self._conn().execute(f"PRAGMA table_info({table})")}
            for col in cols:  # columns added after a database was created
                if col not in have:
                    self._conn().execute(f"ALTER TABLE {table} ADD COLUMN {col} TEXT")

    # -- connection -------------------------------------------------------
    def _conn(self) -> sqlite3.Connection:
        c = getattr(self._local, "conn", None)
        if c is None:
            c = sqlite3.connect(self.db_path, timeout=10, isolation_level=None)
            c.row_factory = sqlite3.Row
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("PRAGMA busy_timeout=10000")
            self._local.conn = c
        return c

    class _Tx:
        def __init__(self, conn, immediate):
            self.c, self.immediate = conn, immediate

        def __enter__(self):
            self.c.execute("BEGIN IMMEDIATE" if self.immediate else "BEGIN")
            return self.c

        def __exit__(self, et, ev, tb):
            self.c.execute("COMMIT" if et is None else "ROLLBACK")
            return False

    def _tx(self, immediate=True):
        return Store._Tx(self._conn(), immediate)

    def _q(self, sql, args=()) -> list[dict]:
        return [_row(r) for r in self._conn().execute(sql, args).fetchall()]

    def _one(self, sql, args=()) -> dict | None:
        return _row(self._conn().execute(sql, args).fetchone())

    # -- settings ---------------------------------------------------------
    def get_settings(self) -> dict:
        s = dict(DEFAULT_SETTINGS)
        for r in self._conn().execute("SELECT key, value_json FROM settings"):
            s[r["key"]] = json.loads(r["value_json"])
        return s

    def set_settings(self, **kv) -> None:
        with self._tx() as c:
            for k, v in kv.items():
                c.execute("INSERT INTO settings(key, value_json) VALUES(?, ?) "
                          "ON CONFLICT(key) DO UPDATE SET value_json = excluded.value_json",
                          (k, json.dumps(v, ensure_ascii=False)))

    # -- users ------------------------------------------------------------
    @staticmethod
    def _check_name(name: str) -> str:
        n = " ".join((name or "").split())
        if not n or len(n) > 40 or n.casefold() in RESERVED_NAMES:
            raise NameTaken(n)
        return n

    def create_user(self, name: str) -> dict:
        n = self._check_name(name)
        uid = secrets.token_urlsafe(24)
        try:
            with self._tx() as c:
                c.execute("INSERT INTO users(uid, name, created_at, last_seen) VALUES(?, ?, ?, ?)",
                          (uid, n, now_iso(), now_iso()))
        except sqlite3.IntegrityError as e:
            raise NameTaken(n) from e
        return self.user_by_uid(uid)

    def user_by_uid(self, uid: str | None) -> dict | None:
        return self._one("SELECT * FROM users WHERE uid = ?", (uid,)) if uid else None

    def user_by_name(self, name: str | None) -> dict | None:
        n = " ".join((name or "").split())
        return self._one("SELECT * FROM users WHERE name = ?", (n,)) if n else None

    def user_by_id(self, user_id: int | None) -> dict | None:
        return self._one("SELECT * FROM users WHERE id = ?", (user_id,)) if user_id else None

    def rename_user(self, uid: str, name: str) -> dict:
        n = self._check_name(name)
        try:
            with self._tx() as c:
                c.execute("UPDATE users SET name = ? WHERE uid = ?", (n, uid))
        except sqlite3.IntegrityError as e:
            raise NameTaken(n) from e
        return self.user_by_uid(uid)

    def touch_user(self, uid: str) -> None:
        self._conn().execute("UPDATE users SET last_seen = ? WHERE uid = ?", (now_iso(), uid))

    def set_user_prefs(self, uid: str, prefs: dict) -> None:
        self._conn().execute("UPDATE users SET prefs_json = ? WHERE uid = ?", (json.dumps(prefs, ensure_ascii=False), uid))

    # -- runs -------------------------------------------------------------
    def insert_run(self, kind, path, path_key, job, codes, user_id, rerun_of=None, job_dir=None, resume_of=None) -> int:
        with self._tx() as c:
            hit = c.execute(f"SELECT * FROM runs WHERE path_key = ? AND status IN ({','.join('?' * len(ACTIVE))})",
                            (path_key, *ACTIVE)).fetchone()
            if hit is not None:
                raise Duplicate(_row(hit))
            cur = c.execute("INSERT INTO runs(kind, path, path_key, job, codes_json, user_id, status, queued_at, rerun_of, job_dir, resume_of) "
                            "VALUES(?, ?, ?, ?, ?, ?, 'QUEUED', ?, ?, ?, ?)",
                            (kind, path, path_key, job, json.dumps(codes) if codes else None, user_id, now_iso(), rerun_of,
                             job_dir, resume_of))
            return cur.lastrowid

    def get_run(self, run_id: int) -> dict | None:
        return self._one("SELECT r.*, u.name AS user_name FROM runs r LEFT JOIN users u ON u.id = r.user_id WHERE r.id = ?",
                         (run_id,))

    def update_run(self, run_id: int, **fields) -> None:
        if not fields:
            return
        cols, vals = [], []
        for k, v in fields.items():
            col = next((c for c, key in JSON_COLS.items() if key == k), k)
            if col in JSON_COLS:
                v = json.dumps(v, ensure_ascii=False) if v is not None else None
            cols.append(f'"{col}" = ?')
            vals.append(v)
        self._conn().execute(f"UPDATE runs SET {', '.join(cols)} WHERE id = ?", (*vals, run_id))

    def active_run_for(self, path_key: str) -> dict | None:
        rows = self._runs(f"r.path_key = ? AND r.status IN ({','.join('?' * len(ACTIVE))})", (path_key, *ACTIVE), limit=1)
        return rows[0] if rows else None

    def claim_run(self, run_id: int, slot: int) -> bool:
        """QUEUED -> PREPARING on a slot; False if someone cancelled it first."""
        cur = self._conn().execute("UPDATE runs SET status = 'PREPARING', slot = ? WHERE id = ? AND status = 'QUEUED'",
                                   (slot, run_id))
        return cur.rowcount == 1

    def cancel_queued(self, run_id: int, by: str) -> bool:
        cur = self._conn().execute("UPDATE runs SET status = 'CANCELLED', cancelled_by = ?, ended_at = ?, "
                                   "summary = 'Đã hủy khi đang chờ' WHERE id = ? AND status = 'QUEUED'",
                                   (by, now_iso(), run_id))
        return cur.rowcount == 1

    def finish_run(self, run_id: int, **fields) -> bool:
        """Write a final state only while the run is still active (recovery may have closed it already)."""
        with self._tx():
            r = self._conn().execute("SELECT status FROM runs WHERE id = ?", (run_id,)).fetchone()
            if not r or r[0] not in ACTIVE:
                return False
            self.update_run(run_id, **fields)
            return True

    def _runs(self, where="1=1", args=(), order="r.id DESC", limit=200) -> list[dict]:
        return self._q(f"SELECT r.*, u.name AS user_name FROM runs r LEFT JOIN users u ON u.id = r.user_id "
                       f"WHERE {where} ORDER BY {order} LIMIT {int(limit)}", args)

    def active_runs(self) -> list[dict]:
        return self._runs(f"r.status IN ({','.join('?' * len(ACTIVE))})", ACTIVE, order="r.id ASC")

    def queued_runs(self) -> list[dict]:
        return self._runs("r.status = 'QUEUED'", order="r.id ASC")

    def last_final_run(self, path_key: str) -> dict | None:
        rows = self._runs(f"r.path_key = ? AND r.status IN ({','.join('?' * len(FINAL))})", (path_key, *FINAL), limit=1)
        return rows[0] if rows else None

    def list_runs(self, user_id=None, status=None, kind=None, date_from=None, date_to=None, q=None,
                  limit=200, final_only=False, ended_from=None) -> list[dict]:
        where, args = ["1=1"], []
        if user_id is not None:
            where.append("r.user_id = ?"); args.append(user_id)
        if status:
            where.append("r.status = ?"); args.append(status)
        if kind:
            where.append("r.kind = ?"); args.append(kind)
        if final_only:
            where.append(f"r.status IN ({','.join('?' * len(FINAL))})"); args.extend(FINAL)
        if date_from:
            where.append("r.queued_at >= ?"); args.append(date_from)
        if date_to:
            where.append("r.queued_at < ?"); args.append(date_to)
        if ended_from:
            where.append("r.ended_at >= ?"); args.append(ended_from)
        if q:
            terms = " ".join('"' + t.replace('"', '') + '"*' for t in q.split() if t.replace('"', ''))
            if terms:
                where.append("r.id IN (SELECT run_id FROM run_search WHERE run_search MATCH ?)"); args.append(terms)
        return self._runs(" AND ".join(where), args, limit=limit)

    def index_run(self, run_id: int, text: str) -> None:
        with self._tx() as c:
            c.execute("DELETE FROM run_search WHERE run_id = ?", (run_id,))
            c.execute("INSERT INTO run_search(run_id, search_text) VALUES(?, ?)", (run_id, text))

    # -- review items -----------------------------------------------------
    def add_review_items(self, run_id: int, items: list[dict]) -> list[int]:
        ids = []
        with self._tx() as c:
            for it in items:
                cur = c.execute("INSERT INTO review_items(run_id, type, code, card, title, detail, evidence, created_at, updated_at) "
                                "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                (run_id, it.get("type"), it.get("code"), it.get("card"), it.get("title"),
                                 it.get("detail"), it.get("evidence"), now_iso(), now_iso()))
                ids.append(cur.lastrowid)
        return ids

    def add_feedback(self, author: str, text: str, run_id: int | None = None, code: str | None = None,
                     author_id: int | None = None) -> int:
        """A user's suggestion: only stored; Admin reads it on the Góp ý page (Mới / Đã xem / Đã làm / Bỏ qua)."""
        title = text.strip().splitlines()[0][:120]
        cur = self._conn().execute("INSERT INTO review_items(run_id, type, code, title, detail, author, author_id, created_at, "
                                   "updated_at) VALUES(?, 'FEEDBACK', ?, ?, ?, ?, ?, ?, ?)",
                                   (run_id, code, title, text.strip(), author, author_id, now_iso(), now_iso()))
        return cur.lastrowid

    def list_feedback(self, author_id: int | None = None) -> list[dict]:
        sql = "SELECT i.*, r.job FROM review_items i LEFT JOIN runs r ON r.id = i.run_id WHERE i.type = 'FEEDBACK'"
        if author_id is not None:
            return self._q(sql + " AND i.author_id = ? ORDER BY i.id DESC", (author_id,))
        return self._q(sql + " ORDER BY i.id DESC")

    def feedback_new_count(self) -> int:
        return self._conn().execute("SELECT COUNT(*) FROM review_items WHERE type = 'FEEDBACK' AND status = 'PENDING'").fetchone()[0]

    def list_review_items(self, status=None) -> list[dict]:
        """Lessons and sample-DXF requests from runs (feedback has its own page)."""
        sql = ("SELECT i.*, r.job, r.path, r.kind FROM review_items i LEFT JOIN runs r ON r.id = i.run_id "
               "WHERE i.type != 'FEEDBACK'")
        if status:
            return self._q(sql + " AND i.status = ? ORDER BY i.id DESC", (status,))
        return self._q(sql + " ORDER BY i.id DESC")

    def get_review_item(self, item_id: int) -> dict | None:
        return self._one("SELECT i.*, r.job, r.path FROM review_items i LEFT JOIN runs r ON r.id = i.run_id WHERE i.id = ?",
                         (item_id,))

    def update_review_item(self, item_id: int, **fields) -> None:
        fields["updated_at"] = now_iso()
        cols = ", ".join(f"{k} = ?" for k in fields)
        self._conn().execute(f"UPDATE review_items SET {cols} WHERE id = ?", (*fields.values(), item_id))

    def review_pending_count(self) -> int:
        return self._conn().execute("SELECT COUNT(*) FROM review_items WHERE status IN ('PENDING', 'COPIED') "
                                    "AND type != 'FEEDBACK'").fetchone()[0]

    # -- notifications ----------------------------------------------------
    def notify(self, user_id, run_id, kind, text) -> int:
        cur = self._conn().execute("INSERT INTO notifications(user_id, run_id, kind, text, created_at) VALUES(?, ?, ?, ?, ?)",
                                   (user_id, run_id, kind, text, now_iso()))
        return cur.lastrowid

    def notifications(self, user_id, since_id=0) -> list[dict]:
        return self._q("SELECT * FROM notifications WHERE user_id = ? AND id > ? ORDER BY id", (user_id, since_id))

    def last_notification_id(self, user_id) -> int:
        return self._conn().execute("SELECT COALESCE(MAX(id), 0) FROM notifications WHERE user_id = ?", (user_id,)).fetchone()[0]

    def mark_seen(self, user_id, upto_id) -> None:
        self._conn().execute("UPDATE notifications SET seen_at = ? WHERE user_id = ? AND id <= ? AND seen_at IS NULL",
                             (now_iso(), user_id, upto_id))

    # -- admin sessions ---------------------------------------------------
    def add_admin_session(self, token_hash: str, ip: str, ttl_s: float, now: float | None = None) -> None:
        t = time.time() if now is None else now
        self._conn().execute("INSERT INTO admin_sessions VALUES(?, ?, ?, ?)", (token_hash, t, t + ttl_s, ip))

    def admin_session_valid(self, token_hash: str, now: float | None = None) -> bool:
        t = time.time() if now is None else now
        r = self._conn().execute("SELECT expires_at FROM admin_sessions WHERE token_hash = ?", (token_hash,)).fetchone()
        return bool(r and r[0] > t)

    def drop_admin_session(self, token_hash: str) -> None:
        self._conn().execute("DELETE FROM admin_sessions WHERE token_hash = ?", (token_hash,))
