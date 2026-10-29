"""Persist related model events without a transaction for each UI field."""
import contextlib

import pytest

from chat import kosu_deposu
from chat.platform_agents import _Events
from chat.platform_runtime import Control, LeaseLost, RunCancelled, RuntimeStore


def fixture_store(tmp_path):
    store = RuntimeStore(kosu_deposu._SqliteDepo(str(tmp_path / 'batch.db')))
    run = store.create('alice', 'personal', 'Hello', kind='chat')
    lease = store.claim('worker', run_id=run['id'])['lease']
    return store, run, lease


def count_transactions(store, monkeypatch):
    calls = []
    original = store.transaction
    @contextlib.contextmanager
    def measured(**kwargs):
        calls.append(kwargs)
        with original(**kwargs) as tx:
            yield tx
    monkeypatch.setattr(store, 'transaction', measured)
    return calls


def test_final_model_event_is_one_fenced_transaction(tmp_path, monkeypatch):
    store, run, lease = fixture_store(tmp_path)
    calls = count_transactions(store, monkeypatch)
    _Events(Control(store, lease))('BasakUI.bitir("Hello", "provider")')
    assert len(calls) == 1
    events = store.events('alice', run['id'])
    assert [(e['type'], e['payload']) for e in events[-2:]] == [
        ('provider', {'provider': 'provider'}),
        ('chat', {'tur': 'bitir', 'cevap': 'Hello', 'kaynak': 'provider'})]
    assert store.get('alice', run['id'])['provider'] == 'provider'


def test_batch_never_persists_after_cancel(tmp_path):
    store, run, lease = fixture_store(tmp_path)
    store.cancel('alice', run['id'])
    before = store.events('alice', run['id'])
    with pytest.raises((RunCancelled, LeaseLost)):
        _Events(Control(store, lease))('BasakUI.bitir("late", "provider")')
    assert store.events('alice', run['id']) == before


def test_answer_artifact_checks_and_completion_share_one_commit(tmp_path, monkeypatch):
    store, run, lease = fixture_store(tmp_path)
    calls = count_transactions(store, monkeypatch)
    result = store.finish(lease, {'answer': 'Full answer\n🙂', 'record_answer': True})
    assert len(calls) == 1
    assert result['durum'] == 'completed'
    assert result['answer'] == 'Full answer\n🙂'
    assert result['checks'][0]['ok'] is True
    assert result['artifacts'][0]['size'] == len(result['answer'].encode('utf-8'))
    with store.transaction(readonly=True) as tx:
        import json
        artifact = tx.one('SELECT data FROM basak_platform_artifact WHERE run_id=%s', (run['id'],))
        assert json.loads(artifact['data'])['content'] == result['answer']


def test_answer_recording_cannot_satisfy_unobserved_tool_or_human_check(tmp_path):
    store = RuntimeStore(kosu_deposu._SqliteDepo(str(tmp_path / 'custom.db')))
    run = store.create('alice', 'personal', 'Calculate', kind='chat', acceptance=[
        {'id': 'tool', 'kind': 'tool_succeeded', 'tool': 'hesapla'},
        {'id': 'human', 'kind': 'human'}])
    lease = store.claim('w', run_id=run['id'])['lease']
    result = store.finish(lease, {'answer': 'unverified', 'record_answer': True})
    assert result['durum'] == 'verifying'
    assert result['checks'] == []


def test_failed_completion_rolls_back_answer_artifact_and_check(tmp_path, monkeypatch):
    store, run, lease = fixture_store(tmp_path)
    original = store._event
    def fail_check(tx, run_id, kind, payload):
        if kind == 'check':
            raise RuntimeError('fixture interrupted commit')
        return original(tx, run_id, kind, payload)
    monkeypatch.setattr(store, '_event', fail_check)
    with pytest.raises(RuntimeError, match='interrupted commit'):
        store.finish(lease, {'answer': 'not committed', 'record_answer': True})
    result = store.get('alice', run['id'])
    assert result['durum'] == 'running'
    assert result['answer'] == ''
    assert result['artifacts'] == []
    assert result['checks'] == []
