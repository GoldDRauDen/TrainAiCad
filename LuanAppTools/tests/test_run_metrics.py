"""Cost metrics are read back from the events a run already persists."""
from LuanAppTools.bench.run_metrics import summarize


def usage(store, run_id, request_id, *, create, read, out, inp=2):
    key = f"{request_id}:session:final"
    store.append_event(run_id, "usage", {
        "event_key": key,
        "metrics": {"input_tokens": inp, "output_tokens": out,
                    "cache_read_input_tokens": read, "cache_creation_input_tokens": create},
    }, event_key=key)


def prepared(store, run_id, request_id, stage, code, chars, shared=0):
    store.append_event(run_id, "request_prepared", {
        "stage": stage, "code": code, "request_id": request_id,
        "prompt_characters": chars, "shared_context_characters": shared,
    })


def test_one_code_run_sums_calls_and_tokens(store, run):
    rid = run["id"]
    store.append_event(rid, "worker_started", {"provider": "claude"})
    prepared(store, rid, "r0", "solve", "26-000001", 5000, shared=4000)
    usage(store, rid, "r0", create=100, read=0, out=10)
    prepared(store, rid, "r1", "solve", "26-000001", 300)
    usage(store, rid, "r1", create=20, read=100, out=30)
    store.append_event(rid, "part_complete", {"code": "26-000001", "status": "PASS", "attempts": 1})
    out = summarize(store.db_path, rid)
    row = out["by_stage_code"]["solve:26-000001"]
    assert (row["calls"], row["cache_creation"], row["cache_read"], row["output_tokens"]) == (2, 120, 100, 40)
    assert (row["prompt_characters"], row["shared_context_characters"]) == (5300, 4000)
    assert out["totals"]["calls"] == 2 and out["totals"]["cache_read"] == 100
    assert out["parts"] == {"26-000001": {"status": "PASS", "attempts": 1}}
    assert out["wall_seconds"] >= 0


def test_run_without_events_has_zero_totals(store, run):
    out = summarize(store.db_path, run["id"])
    assert out["totals"]["calls"] == 0 and out["by_stage_code"] == {} and out["wall_seconds"] == 0


def test_latest_run_is_used_when_run_id_is_omitted(store, run):
    store.append_event(run["id"], "request_prepared", {"stage": "intake", "code": None, "request_id": "x",
                                                      "prompt_characters": 7})
    assert summarize(store.db_path)["run_id"] == run["id"]
    assert "intake" in summarize(store.db_path)["by_stage_code"]


def test_repeated_validation_errors_are_counted_by_signature(store, run):
    for count in (1, 2, 3):
        store.append_event(run["id"], "validation_error", {
            "stage": "solve", "code": "26-000001", "signature": "VIEWS_ONLY requires", "count": count})
    out = summarize(store.db_path, run["id"])
    assert out["repeated_errors"] == {"26-000001: VIEWS_ONLY requires": 3}
