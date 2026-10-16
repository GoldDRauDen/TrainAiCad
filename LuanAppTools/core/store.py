"""SQLite durability and publication leases for one application machine."""
from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
import time
import uuid

from .sources import folder_identity


_STATUSES = {'queued', 'running', 'pause_requested', 'paused', 'waiting_usage', 'waiting_fallback', 'publication_pending', 'completed', 'cancelled', 'error', 'superseded'}
_TERMINAL = {'cancelled', 'error', 'superseded', 'completed'}


class Store:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY, folder TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
                    tracked INTEGER NOT NULL DEFAULT 0, generation INTEGER NOT NULL DEFAULT 0,
                    current_run TEXT);
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY, job_id TEXT NOT NULL REFERENCES jobs(id),
                    generation INTEGER NOT NULL, source_hash TEXT NOT NULL, repo_commit TEXT NOT NULL,
                    snapshot_dir TEXT, status TEXT NOT NULL, lease TEXT, owner TEXT,
                    checkpoint TEXT NOT NULL DEFAULT '{}', publication TEXT NOT NULL DEFAULT '{}',
                    error TEXT, created REAL NOT NULL, updated REAL NOT NULL,
                    UNIQUE(job_id,generation));
                CREATE TABLE IF NOT EXISTS attempts (
                    run_id TEXT NOT NULL REFERENCES runs(id), code TEXT NOT NULL, count INTEGER NOT NULL,
                    PRIMARY KEY(run_id,code));
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL REFERENCES runs(id),
                    kind TEXT NOT NULL, payload TEXT NOT NULL, event_key TEXT,
                    created REAL NOT NULL, UNIQUE(run_id,event_key));
                CREATE TABLE IF NOT EXISTS parts (
                    run_id TEXT NOT NULL REFERENCES runs(id), code TEXT NOT NULL,
                    status TEXT NOT NULL, data TEXT NOT NULL, PRIMARY KEY(run_id,code));
                CREATE TABLE IF NOT EXISTS usage (
                    run_id TEXT NOT NULL REFERENCES runs(id), session_id TEXT NOT NULL,
                    event_key TEXT NOT NULL, metrics TEXT NOT NULL, PRIMARY KEY(run_id,event_key));
                CREATE TABLE IF NOT EXISTS usage_cursors (
                    run_id TEXT NOT NULL, session_id TEXT NOT NULL, metrics TEXT NOT NULL,
                    PRIMARY KEY(run_id,session_id));
                CREATE TABLE IF NOT EXISTS reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL REFERENCES runs(id),
                    source_hash TEXT NOT NULL, outputs TEXT NOT NULL, reviewer TEXT NOT NULL,
                    note TEXT NOT NULL, created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS outputs (
                    path TEXT NOT NULL, job_id TEXT NOT NULL REFERENCES jobs(id),
                    run_id TEXT NOT NULL REFERENCES runs(id), sha256 TEXT NOT NULL,
                    status TEXT NOT NULL, archive_path TEXT, PRIMARY KEY(path,run_id));
            ''')

    def _connect(self):
        db = sqlite3.connect(self.db_path, timeout=30, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('PRAGMA busy_timeout=30000')
        return db

    @contextmanager
    def transaction(self):
        db = self._connect()
        try:
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _run(row):
        if row is None:
            raise KeyError('Run not found')
        result = dict(row)
        for field in ('checkpoint', 'publication'):
            result[field] = json.loads(result[field])
        if result['snapshot_dir']:
            result['snapshot_dir'] = Path(result['snapshot_dir'])
        return result

    @staticmethod
    def _job(row):
        if row is None:
            raise KeyError('Job not found')
        result = dict(row)
        result['folder'] = Path(result['folder'])
        result['tracked'] = bool(result['tracked'])
        return result

    def register_job(self, folder: Path, *, tracked: bool = False) -> dict:
        folder = Path(folder).resolve(strict=True)
        if not folder.is_dir():
            raise ValueError('Job folder must be a directory')
        identity = folder_identity(folder)
        with self.transaction() as db:
            db.execute('INSERT INTO jobs(id,folder,name,tracked) VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET tracked=MAX(jobs.tracked,excluded.tracked)', (identity, str(folder), folder.name, int(tracked)))
            return self._job(db.execute('SELECT * FROM jobs WHERE id=?', (identity,)).fetchone())

    def get_job(self, job_id: str) -> dict:
        with self._connect() as db:
            return self._job(db.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone())

    def list_jobs(self, *, tracked_only: bool = False) -> list[dict]:
        with self._connect() as db:
            return [self._job(row) for row in db.execute('SELECT * FROM jobs WHERE tracked>=? ORDER BY folder', (int(tracked_only),))]

    def set_tracked(self, job_id: str, tracked: bool) -> None:
        with self.transaction() as db:
            if not db.execute('UPDATE jobs SET tracked=? WHERE id=?', (int(tracked), job_id)).rowcount:
                raise KeyError(job_id)

    def create_run(self, job_id: str, source_hash: str, repo_commit: str, *, snapshot_dir: Path | None = None, force: bool = False) -> dict:
        if not source_hash or not repo_commit:
            raise ValueError('Source hash and repository commit are required')
        with self.transaction() as db:
            job = self._job(db.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone())
            current = db.execute('SELECT * FROM runs WHERE id=?', (job['current_run'],)).fetchone()
            if current and current['source_hash'] == source_hash and current['repo_commit'] == repo_commit and not force:
                return self._run(current)
            if current:
                db.execute("UPDATE runs SET status='superseded',lease=NULL,updated=? WHERE id=?", (time.time(), current['id']))
            identity = uuid.uuid4().hex
            generation = job['generation'] + 1
            now = time.time()
            db.execute('INSERT INTO runs(id,job_id,generation,source_hash,repo_commit,snapshot_dir,status,created,updated) VALUES(?,?,?,?,?,?,?,?,?)', (identity, job_id, generation, source_hash, repo_commit, str(Path(snapshot_dir).resolve()) if snapshot_dir else None, 'queued', now, now))
            db.execute('UPDATE jobs SET generation=?,current_run=? WHERE id=?', (generation, identity, job_id))
            return self._run(db.execute('SELECT * FROM runs WHERE id=?', (identity,)).fetchone())

    def get_run(self, run_id: str) -> dict:
        with self._connect() as db:
            return self._run(db.execute('SELECT * FROM runs WHERE id=?', (run_id,)).fetchone())

    def list_runs(self, *, statuses=None, job_id: str | None = None) -> list[dict]:
        with self._connect() as db:
            rows = [self._run(row) for row in db.execute('SELECT * FROM runs ORDER BY created')]
        return [row for row in rows if (statuses is None or row['status'] in statuses) and (job_id is None or row['job_id'] == job_id)]

    def claim_run(self, run_id: str, owner: str) -> str | None:
        if not owner:
            raise ValueError('Worker owner is required')
        with self.transaction() as db:
            lease = uuid.uuid4().hex
            changed = db.execute("UPDATE runs SET lease=?,owner=?,status='running',updated=? WHERE id=? AND status='queued' AND lease IS NULL AND id=(SELECT current_run FROM jobs WHERE jobs.id=runs.job_id)", (lease, owner, time.time(), run_id)).rowcount
            return lease if changed else None

    def release_run(self, run_id: str, lease: str, *, status: str = 'queued') -> None:
        """After reconciling/stopping the prior worker, release its lease without resetting budgets."""
        if status not in {'queued', 'paused', 'waiting_usage', 'waiting_fallback'}:
            raise ValueError('Invalid released run status')
        with self.transaction() as db:
            row = self._assert_current(db, run_id)
            if not lease or row['lease'] != lease:
                raise ValueError('Invalid worker lease')
            db.execute('UPDATE runs SET status=?,lease=NULL,owner=NULL,updated=? WHERE id=?', (status, time.time(), run_id))

    @staticmethod
    def _assert_current(db, run_id, lease=None, source_hash=None):
        row = db.execute('SELECT r.*,j.current_run FROM runs r JOIN jobs j ON j.id=r.job_id WHERE r.id=?', (run_id,)).fetchone()
        if row is None:
            raise KeyError(run_id)
        if row['current_run'] != run_id or row['status'] in _TERMINAL:
            raise ValueError('Run is obsolete or terminal')
        if lease is not None and (not lease or row['lease'] != lease or row['status'] not in {'running', 'publication_pending'}):
            raise ValueError('Invalid publication lease')
        if source_hash is not None and row['source_hash'] != source_hash:
            raise ValueError('Source hash does not match lease')
        return row

    def assert_lease(self, run_id: str, lease: str, source_hash: str) -> dict:
        with self._connect() as db:
            return self._run(self._assert_current(db, run_id, lease, source_hash))

    @contextmanager
    def publication_guard(self, run_id: str, lease: str, source_hash: str):
        """Serialize publication with generation changes, including across processes."""
        with self.transaction() as db:
            self._assert_current(db, run_id, lease, source_hash)
            yield db

    def set_run_status(self, run_id: str, status: str, *, error: str | None = None) -> dict:
        if status not in _STATUSES:
            raise ValueError('Unknown run status')
        with self.transaction() as db:
            self._assert_current(db, run_id)
            db.execute('UPDATE runs SET status=?,error=?,updated=?,lease=CASE WHEN ? THEN NULL ELSE lease END WHERE id=?', (status, error, time.time(), int(status in _TERMINAL), run_id))
            return self._run(db.execute('SELECT * FROM runs WHERE id=?', (run_id,)).fetchone())

    def begin_attempt(self, run_id: str, code: str, *, checkpoint: dict | None = None) -> int:
        if not code:
            raise ValueError('Part code is required')
        with self.transaction() as db:
            self._assert_current(db, run_id)
            current = db.execute('SELECT count FROM attempts WHERE run_id=? AND code=?', (run_id, code)).fetchone()
            count = current['count'] if current else 0
            if count >= 2:
                raise ValueError('Two solver attempts already consumed')
            db.execute('INSERT INTO attempts VALUES(?,?,?) ON CONFLICT(run_id,code) DO UPDATE SET count=excluded.count', (run_id, code, count + 1))
            if checkpoint is not None:
                db.execute('UPDATE runs SET checkpoint=?,updated=? WHERE id=?', (json.dumps(checkpoint), time.time(), run_id))
            return count + 1

    def attempts(self, run_id: str, code: str) -> int:
        with self._connect() as db:
            row = db.execute('SELECT count FROM attempts WHERE run_id=? AND code=?', (run_id, code)).fetchone()
            return row['count'] if row else 0

    def append_event(self, run_id: str, kind: str, payload: dict, *, event_key: str | None = None) -> int:
        with self.transaction() as db:
            db.execute('INSERT INTO events(run_id,kind,payload,event_key,created) VALUES(?,?,?,?,?) ON CONFLICT(run_id,event_key) DO NOTHING', (run_id, kind, json.dumps(payload), event_key, time.time()))
            if event_key is not None:
                return db.execute('SELECT id FROM events WHERE run_id=? AND event_key=?', (run_id, event_key)).fetchone()['id']
            return db.execute('SELECT last_insert_rowid()').fetchone()[0]

    def events_since(self, run_id: str, after: int = 0, *, limit: int = 1000) -> list[dict]:
        with self._connect() as db:
            result = [dict(row) for row in db.execute('SELECT * FROM events WHERE run_id=? AND id>? ORDER BY id LIMIT ?', (run_id, after, limit))]
        for item in result:
            item['payload'] = json.loads(item['payload'])
        return result

    def save_checkpoint(self, run_id: str, checkpoint: dict) -> None:
        with self.transaction() as db:
            self._assert_current(db, run_id)
            db.execute('UPDATE runs SET checkpoint=?,updated=? WHERE id=?', (json.dumps(checkpoint), time.time(), run_id))

    def save_part(self, run_id: str, code: str, status: str, data: dict) -> None:
        with self.transaction() as db:
            self._assert_current(db, run_id)
            db.execute('INSERT INTO parts VALUES(?,?,?,?) ON CONFLICT(run_id,code) DO UPDATE SET status=excluded.status,data=excluded.data', (run_id, code, status, json.dumps(data)))

    def parts(self, run_id: str) -> list[dict]:
        with self._connect() as db:
            result = [dict(row) for row in db.execute('SELECT * FROM parts WHERE run_id=? ORDER BY code', (run_id,))]
        for item in result:
            item['data'] = json.loads(item['data'])
            item['attempts'] = self.attempts(run_id, item['code'])
        return result

    def record_usage(self, run_id: str, session_id: str, event_key: str, metrics: dict, *, cumulative: bool = False) -> None:
        if any(type(value) is not int or value < 0 for value in metrics.values()):
            raise ValueError('Usage counters must be nonnegative integers; omit unknown counters')
        with self.transaction() as db:
            if db.execute('SELECT 1 FROM usage WHERE run_id=? AND event_key=?', (run_id, event_key)).fetchone():
                return
            delta = metrics
            if cumulative:
                previous = db.execute('SELECT metrics FROM usage_cursors WHERE run_id=? AND session_id=?', (run_id, session_id)).fetchone()
                old = json.loads(previous['metrics']) if previous else {}
                delta = {key: max(0, value - old.get(key, 0)) for key, value in metrics.items()}
                high_water = {**old, **{key: max(value, old.get(key, 0)) for key, value in metrics.items()}}
                db.execute('INSERT INTO usage_cursors VALUES(?,?,?) ON CONFLICT(run_id,session_id) DO UPDATE SET metrics=excluded.metrics', (run_id, session_id, json.dumps(high_water)))
            db.execute('INSERT INTO usage VALUES(?,?,?,?)', (run_id, session_id, event_key, json.dumps(delta)))

    def usage(self, run_id: str) -> dict:
        result = {}
        with self._connect() as db:
            for row in db.execute('SELECT metrics FROM usage WHERE run_id=?', (run_id,)):
                for key, value in json.loads(row['metrics']).items():
                    result[key] = result.get(key, 0) + value
        return result

    def record_review(self, run_id: str, reviewer: str, note: str = '') -> int:
        with self.transaction() as db:
            run = self._run(db.execute('SELECT * FROM runs WHERE id=?', (run_id,)).fetchone())
            outputs = [dict(row) for row in db.execute('SELECT path,sha256 FROM outputs WHERE run_id=? AND status=? ORDER BY path', (run_id, 'current'))]
            cursor = db.execute('INSERT INTO reviews(run_id,source_hash,outputs,reviewer,note,created) VALUES(?,?,?,?,?,?)', (run_id, run['source_hash'], json.dumps(outputs), reviewer, note, time.time()))
            return cursor.lastrowid

    def reviews(self, run_id: str) -> list[dict]:
        with self._connect() as db:
            result = [dict(row) for row in db.execute('SELECT * FROM reviews WHERE run_id=? ORDER BY id', (run_id,))]
        for row in result:
            row['outputs'] = json.loads(row['outputs'])
        return result

    def outputs(self, run_id: str | None = None, *, job_id: str | None = None, current_only: bool = True) -> list[dict]:
        with self._connect() as db:
            rows = [dict(row) for row in db.execute('SELECT * FROM outputs ORDER BY path')]
        return [row for row in rows if (run_id is None or row['run_id'] == run_id) and (job_id is None or row['job_id'] == job_id) and (not current_only or row['status'] in {'current', 'pending'})]
