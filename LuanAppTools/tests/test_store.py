import concurrent.futures

import pytest

from LuanAppTools.core.store import Store


def test_sqlite_reopen_preserves_attempts_events_parts_usage_review(store, run):
    store.begin_attempt(run['id'], '26-056522')
    store.append_event(run['id'], 'progress', {'stage': 'solve'}, event_key='session:1')
    store.append_event(run['id'], 'progress', {'stage': 'solve'}, event_key='session:1')
    store.save_part(run['id'], '26-056522', 'REVIEW', {'reason': 'witness'})
    store.record_usage(run['id'], 'session', 'call:1', {'input_tokens': 100, 'output_tokens': 20})
    store.record_usage(run['id'], 'session', 'call:1', {'input_tokens': 100, 'output_tokens': 20})
    store.save_checkpoint(run['id'], {'stage': 'qa'})
    store.record_review(run['id'], 'operator', 'checked')
    reopened = Store(store.db_path)
    assert reopened.attempts(run['id'], '26-056522') == 1
    assert [e['payload'] for e in reopened.events_since(run['id'])] == [{'stage': 'solve'}]
    assert reopened.events_since(run['id'], after=1) == []
    assert reopened.parts(run['id'])[0]['status'] == 'REVIEW'
    assert reopened.usage(run['id']) == {'input_tokens': 100, 'output_tokens': 20}
    assert reopened.get_run(run['id'])['checkpoint'] == {'stage': 'qa'}
    assert reopened.reviews(run['id'])[0]['source_hash'] == 'source-one'


def test_only_one_worker_can_atomically_claim_run(store, run):
    def claim(owner):
        return Store(store.db_path).claim_run(run['id'], owner)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(claim, ['worker-a', 'worker-b']))
    assert sum(value is not None for value in results) == 1
    assert Store(store.db_path).claim_run(run['id'], 'worker-c') is None


def test_new_generation_revokes_old_lease_and_coalesces_source(store, run):
    lease = store.claim_run(run['id'], 'worker')
    newer = store.create_run(run['job_id'], 'source-two', 'e2a4161')
    duplicate = store.create_run(run['job_id'], 'source-two', 'e2a4161')
    assert newer['id'] == duplicate['id']
    assert newer['generation'] == 2
    assert store.get_run(run['id'])['status'] == 'superseded'
    with pytest.raises(ValueError, match='lease|obsolete'):
        store.assert_lease(run['id'], lease, 'source-one')
    with pytest.raises(ValueError):
        store.begin_attempt(run['id'], '26-056522')


def test_third_solver_attempt_is_rejected(store, run):
    store.begin_attempt(run['id'], '26-056522')
    store.begin_attempt(run['id'], '26-056522')
    with pytest.raises(ValueError):
        Store(store.db_path).begin_attempt(run['id'], '26-056522')


def test_cancel_revokes_publication_and_retains_history(store, run):
    lease = store.claim_run(run['id'], 'worker')
    store.set_run_status(run['id'], 'cancelled')
    with pytest.raises(ValueError):
        store.assert_lease(run['id'], lease, 'source-one')
    assert store.get_run(run['id'])['status'] == 'cancelled'


def test_cumulative_usage_uses_persisted_session_high_water_without_unknown_zeroes(store, run):
    assert store.usage(run['id']) == {}
    store.record_usage(run['id'], 'session', 'event-1', {'input_tokens': 100}, cumulative=True)
    reopened = Store(store.db_path)
    reopened.record_usage(run['id'], 'session', 'event-2', {'input_tokens': 140, 'output_tokens': 10}, cumulative=True)
    reopened.record_usage(run['id'], 'session', 'old-replayed', {'input_tokens': 100}, cumulative=True)
    reopened.record_usage(run['id'], 'session', 'event-3', {'input_tokens': 150, 'output_tokens': 20}, cumulative=True)
    assert reopened.usage(run['id']) == {'input_tokens': 150, 'output_tokens': 20}


def test_same_source_error_does_not_implicitly_open_new_attempt_budget(store, run):
    store.begin_attempt(run['id'], '26-056522')
    store.begin_attempt(run['id'], '26-056522')
    store.set_run_status(run['id'], 'error', error='provider failure')
    same = store.create_run(run['job_id'], 'source-one', 'e2a4161')
    assert same['id'] == run['id']
    explicit = store.create_run(run['job_id'], 'source-one', 'e2a4161', force=True)
    assert explicit['generation'] == 2
    assert store.attempts(explicit['id'], '26-056522') == 0


def test_reconciled_worker_release_reclaims_without_resetting_budget(store, run):
    lease = store.claim_run(run['id'], 'worker')
    store.begin_attempt(run['id'], '26-056522')
    with pytest.raises(ValueError):
        store.release_run(run['id'], 'wrong-lease')
    store.release_run(run['id'], lease)
    reclaimed = Store(store.db_path).claim_run(run['id'], 'new-worker')
    assert reclaimed is not None
    assert reclaimed != lease
    assert store.attempts(run['id'], '26-056522') == 1


def test_attempt_and_checkpoint_commit_or_rollback_together(store, run):
    checkpoint = {'parts': {'26-000001': {'phase': 'solving', 'attempt': 1}}}
    assert store.begin_attempt(run['id'], '26-000001', checkpoint=checkpoint) == 1
    reopened = Store(store.db_path)
    assert reopened.get_run(run['id'])['checkpoint'] == checkpoint
    with pytest.raises(TypeError):
        reopened.begin_attempt(run['id'], '26-000001', checkpoint={'not_json': object()})
    assert Store(store.db_path).attempts(run['id'], '26-000001') == 1
    assert Store(store.db_path).get_run(run['id'])['checkpoint'] == checkpoint
