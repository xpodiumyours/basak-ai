"""Release gates: preserve legacy chat, durable receipts and Preview isolation."""
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from chat import kosu_deposu, platform_api
from chat.platform_runtime import RuntimeStore, Unavailable


@pytest.fixture
def admission(tmp_path, monkeypatch):
    clock = [1000.0]
    store = RuntimeStore(kosu_deposu._SqliteDepo(str(tmp_path / 'gate.db')),
                         clock=lambda: clock[0])
    monkeypatch.setattr(platform_api, '_store_factory', lambda: store)
    monkeypatch.setattr(platform_api, '_principal', lambda request: 'alice')
    monkeypatch.setenv('BASAK_DURABLE_CHAT_ENABLED', 'true')
    legacy = []
    app = FastAPI()

    @app.post('/chat')
    async def chat(request: Request):
        body = await request.json()
        response = await platform_api.chat_response(request, 'alice', body, [])
        if response is not None:
            return response
        legacy.append(body['metin'])
        return {'engine': 'legacy'}

    return TestClient(app, headers={'Origin': 'http://testserver'}), store, clock, legacy


@pytest.mark.parametrize('enabled,worker', [(False, True), (True, False)])
def test_new_chat_uses_legacy_without_creating_a_durable_job(admission, monkeypatch, enabled, worker):
    client, store, _, legacy = admission
    monkeypatch.setenv('BASAK_DURABLE_CHAT_ENABLED', str(enabled).lower())
    if worker:
        store.worker_ping('worker')
    response = client.post('/chat', json={'metin': 'hello'}, headers={'Idempotency-Key': 'new'})
    assert response.json() == {'engine': 'legacy'}
    assert legacy == ['hello']
    assert store.list('alice') == []


def test_stale_worker_cannot_admit_new_work(admission):
    client, store, clock, legacy = admission
    store.worker_ping('worker')
    clock[0] += 31
    assert client.post('/chat', json={'metin': 'hello'}).json() == {'engine': 'legacy'}
    assert store.list('alice') == [] and legacy == ['hello']


@pytest.mark.parametrize('enabled',[False,True])
def test_private_access_never_silently_falls_back_to_request_only_execution(admission,monkeypatch,enabled):
    client,store,_,legacy=admission
    monkeypatch.setenv('BASAK_PRIVATE_ACCESS_ONLY','true')
    monkeypatch.setenv('BASAK_DURABLE_CHAT_ENABLED',str(enabled).lower())
    result=client.post('/chat',json={'metin':'long work'})
    assert result.status_code==503
    assert legacy==[] and store.list('alice')==[]


@pytest.mark.parametrize('continuation', [{'kosu_id': 'legacy-run'},
                                         {'yonlendirme_baglami': {'token': 'legacy-handoff'}}])
def test_existing_legacy_turn_does_not_change_engines(admission, continuation):
    client, store, _, legacy = admission
    store.worker_ping('worker')
    assert client.post('/chat', json={'metin': 'continue', **continuation}).json() == {'engine': 'legacy'}
    assert store.list('alice') == [] and legacy == ['continue']


def test_real_host_route_preserves_legacy_python_flow_without_worker(admission, monkeypatch):
    import app as host
    _, store, _, _ = admission
    calls = []
    monkeypatch.setattr(host, '_kimlik', lambda request: 'alice')
    monkeypatch.setattr(host, '_platform_kimlik', lambda request: 'alice')
    monkeypatch.setattr(host, '_cekirdek', lambda: (object(), []))
    monkeypatch.setattr(host, '_kota_kapisi', lambda *args: (True, 10))
    monkeypatch.setattr(host, '_handoff_anahtari', lambda kid: b'fixture-signing-key')
    monkeypatch.setattr('chat.ayar.sistem_blogu', lambda *args, **kwargs: '')
    def existing_flow(text, brain, system, callback, tools, **kwargs):
        calls.append((text, kwargs.get('gecmis_override')))
        callback('BasakUI.bitir("Legacy response", "native")')
    monkeypatch.setattr('chat.flow.mesaj_isle', existing_flow)
    response = TestClient(host.app).post('/api/sohbet', json={'metin': 'hello',
        'gecmis': [{'role': 'user', 'content': 'earlier'}]}, headers={'Origin': 'http://testserver'})
    assert response.status_code == 200, response.text
    assert response.json()['cevap'] == 'Legacy response'
    assert calls == [('hello', [{'role': 'user', 'content': 'earlier'}])]
    assert store.list('alice') == []


def test_durable_receipt_survives_worker_loss_and_disabled_rollout(admission, monkeypatch):
    client, store, _, legacy = admission
    store.worker_ping('worker')
    headers = {'Idempotency-Key': 'external-write'}
    first = client.post('/chat', json={'metin': 'write report'}, headers=headers)
    assert first.status_code == 202
    rid = first.json()['kosu_id']
    lease = store.claim('worker')['lease']
    store.begin_action(lease, 'write', 'baglanti_cagir', {'path': 'report.md'}, side_effect=True)
    store.worker_stopped('worker')
    monkeypatch.setenv('BASAK_DURABLE_CHAT_ENABLED', 'false')
    again = client.post('/chat', json={'metin': 'write report'}, headers=headers)
    assert again.status_code == 202 and again.json()['kosu_id'] == rid
    assert len(store.list('alice')) == 1 and legacy == []
    changed = client.post('/chat', json={'metin': 'different report'}, headers=headers)
    assert changed.status_code == 409 and legacy == []


def test_legacy_receipt_does_not_become_durable_when_worker_returns(admission):
    client, store, _, legacy = admission
    headers = {'Idempotency-Key': 'offline-turn'}
    assert client.post('/chat', json={'metin': 'hello'}, headers=headers).json() == {'engine': 'legacy'}
    store.worker_ping('worker')
    assert client.post('/chat', json={'metin': 'hello'}, headers=headers).json() == {'engine': 'legacy'}
    assert store.list('alice') == [] and legacy == ['hello', 'hello']


def test_ambiguous_database_failure_never_replays_in_legacy(admission, monkeypatch):
    client, _, _, legacy = admission
    def unavailable():
        raise Unavailable('database unavailable')
    monkeypatch.setattr(platform_api, '_store_factory', unavailable)
    response = client.post('/chat', json={'metin': 'write'}, headers={'Idempotency-Key': 'receipt'})
    assert response.status_code == 503 and legacy == []


@pytest.mark.parametrize('generic', ['DATABASE_URL', 'POSTGRES_URL', 'NEON_DATABASE_URL', 'BASAK_ISCI_DATABASE_URL'])
def test_preview_never_uses_generic_database(generic, monkeypatch):
    from worker import ayar, kuyruk
    env = {'VERCEL_ENV': 'preview', generic: 'postgresql://prod.example/main'}
    assert kosu_deposu._dsn(env) == ''
    assert ayar._dsn(env) == ''
    for key in ('DATABASE_URL', 'POSTGRES_URL', 'NEON_DATABASE_URL', 'BASAK_ISCI_DATABASE_URL', 'BASAK_PREVIEW_DATABASE_URL'):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    assert kuyruk._dsn() == ''
    env['BASAK_PREVIEW_DATABASE_URL'] = 'postgres://other:password@prod.example:5432/main'
    with pytest.raises(RuntimeError, match='Preview'):
        kosu_deposu._dsn(env)
    with pytest.raises(RuntimeError, match='Preview'):
        ayar._dsn(env)
    env['BASAK_PREVIEW_DATABASE_URL'] = 'postgresql://preview.example/preview'
    assert kosu_deposu._dsn(env) == env['BASAK_PREVIEW_DATABASE_URL']


def test_ready_worker_admission_is_transactional(admission):
    _, store, _, _ = admission
    from chat.platform_runtime import WorkerUnavailable
    with pytest.raises(WorkerUnavailable):
        store.create('alice', 'personal', 'task', require_worker=True)
    assert store.list('alice') == []
    store.worker_ping('worker')
    assert store.create('alice', 'personal', 'task', require_worker=True)['durum'] == 'queued'
