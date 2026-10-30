import threading

import pytest

from luan_app.store import Duplicate, NameTaken, Store


def test_settings_defaults_and_override(store):
    assert store.get_settings()["slots"] == 3
    store.set_settings(slots=2)
    assert store.get_settings()["slots"] == 2
    assert store.get_settings()["timeout_min"] == 120


def test_create_user_unique_case_insensitive(store):
    u = store.create_user("Hùng")
    assert store.user_by_uid(u["uid"])["name"] == "Hùng"
    with pytest.raises(NameTaken):
        store.create_user("hùng")
    with pytest.raises(NameTaken):
        store.create_user("Admin")
    with pytest.raises(NameTaken):
        store.create_user("   ")


def _run(store, user, key="\\\\s\\a"):
    return store.insert_run("RUN", "\\\\s\\A", key, "521030-10", None, user["id"])


def test_insert_run_blocks_duplicate_active(store):
    u1, u2 = store.create_user("A1"), store.create_user("B1")
    rid = _run(store, u1)
    with pytest.raises(Duplicate) as e:
        _run(store, u2)
    assert e.value.run["user_id"] == u1["id"]
    store.update_run(rid, status="DONE")
    assert _run(store, u2) != rid


def test_concurrent_insert_one_wins(paths):
    users = Store(paths.db_path)
    u = users.create_user("C1")
    ids, dups = [], []
    barrier = threading.Barrier(2)

    def go():
        s = Store(paths.db_path)
        barrier.wait()
        try:
            ids.append(_run(s, u))
        except Duplicate:
            dups.append(1)

    ts = [threading.Thread(target=go) for _ in range(2)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert len(ids) == 1 and len(dups) == 1


def test_list_runs_filters_and_fts(store):
    u1, u2 = store.create_user("D1"), store.create_user("D2")
    a = store.insert_run("RUN", "p1", "p1", "J1", ["26-061247"], u1["id"])
    b = store.insert_run("RUN", "p2", "p2", "J2", None, u2["id"])
    store.index_run(a, "J1 26-061247 FLAG Nobi chưa rõ")
    store.index_run(b, "J2 PASS")
    assert [r["id"] for r in store.list_runs(q="Nobi")] == [a]
    assert [r["id"] for r in store.list_runs(user_id=u2["id"])] == [b]
    assert store.get_run(a)["codes"] == ["26-061247"]


def test_notifications_since(store):
    u = store.create_user("E1")
    rid = store.insert_run("RUN", "p", "p", "J", None, u["id"])
    first = store.notify(u["id"], rid, "DONE", "xong")
    store.notify(u["id"], rid, "ERROR", "lỗi")
    got = store.notifications(u["id"], since_id=first)
    assert [n["text"] for n in got] == ["lỗi"]
