"""HTTP authentication, durable observers, and explicit acceptance behavior."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from chat import kosu_deposu, platform_api
from chat.platform_runtime import RuntimeStore


@pytest.fixture
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("BASAK_DURABLE_CHAT_ENABLED", "true")
    store = RuntimeStore(kosu_deposu._SqliteDepo(str(tmp_path / "api.db")))
    app = FastAPI()
    onceki = (platform_api._principal, platform_api._store_factory)
    platform_api.configure(lambda request: request.headers.get("X-Test-User"), lambda: store)
    app.include_router(platform_api.router)
    yield TestClient(app, headers={"Origin": "http://testserver"}), store
    platform_api._principal, platform_api._store_factory = onceki


def test_api_requires_identity_and_does_not_start_execution(api):
    client, store = api
    assert client.post("/api/kosu", json={"istek": "task"}).status_code == 401
    store.worker_ping("fixture-ready")
    response = client.post("/api/kosu", headers={"X-Test-User": "alice"}, json={"istek": "task"})
    assert response.status_code == 202
    run = response.json()["kosu"]
    assert run["durum"] == "queued"
    assert store.get("alice", run["id"])["durum"] == "queued"


def test_api_rejects_privileged_forged_fields(api):
    client, store = api
    for body in (["task"], {"istek": "task", "user_id": "casper"},
                 {"istek": "task", "checks": [{"ok": True}]}, {"istek": 1}):
        response = client.post("/api/kosu", headers={"X-Test-User": "alice"}, json=body)
        assert response.status_code == 400
    assert store.list("alice") == []


def test_api_cross_user_views_and_mutations_are_not_found(api):
    client, store = api
    rid = store.create("alice", "personal", "task")["id"]
    for suffix, method, body in (("agac", "get", None), ("olaylar", "get", None),
                                 ("iptal", "post", {}), ("devam", "post", {}),
                                 ("yon", "post", {"metin": "change"}),
                                 ("kabul", "post", {"accepted": True})):
        response = client.request(method, "/api/kosu/%s/%s" % (rid, suffix),
                                  headers={"X-Test-User": "bob"}, json=body)
        assert response.status_code == 404


def test_api_event_cursor_replays_without_duplicates(api):
    client, store = api
    rid = store.create("alice", "personal", "task")["id"]
    headers = {"X-Test-User": "alice"}
    first = client.get("/api/kosu/%s/olaylar" % rid, headers=headers).json()
    assert first["olaylar"][0]["seq"] == 1
    assert client.get("/api/kosu/%s/olaylar?after=%s" % (rid, first["cursor"]), headers=headers).json()["olaylar"] == []
    assert client.post("/api/kosu/%s/yon" % rid, headers=headers, json={"metin": "new direction"}).status_code == 200
    later = client.get("/api/kosu/%s/olaylar?after=%s" % (rid, first["cursor"]), headers=headers).json()
    assert later["olaylar"][0]["payload"]["text"] == "new direction"


def test_human_acceptance_and_safe_artifact_download(api):
    client, store = api
    rid = store.create("alice", "personal", "report")["id"]
    aid = store.add_artifact("alice", rid, {"kind": "log", "title": "out.html", "content": "<script>bad()</script>", "media_type": "text/html"})
    store.finish(store.claim("w")["lease"], {"answer": "Review report"})
    headers = {"X-Test-User": "alice"}
    result = client.post("/api/kosu/%s/kabul" % rid, headers=headers, json={"accepted": True})
    assert result.json()["kosu"]["durum"] == "completed"
    response = client.get("/api/kosu/%s/artifacts/%s" % (rid, aid), headers=headers)
    assert response.text == "<script>bad()</script>"
    assert "attachment" in response.headers["content-disposition"]
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "sandbox" in response.headers["content-security-policy"]
    assert client.get("/api/kosu/%s/artifacts/%s" % (rid, aid), headers={"X-Test-User": "bob"}).status_code == 404


def test_live_app_mounts_platform_observer_and_account_routes():
    import app as app_modulu
    paths = {getattr(route, "path", "") for route in app_modulu.app.routes}
    assert "/api/kosu" in paths
    assert "/api/kosu/{run_id}/iptal" in paths
    assert "/api/hesap" in paths
    assert "/api/baglantilar" in paths


def test_worker_health_endpoint_requires_login_and_reflects_live_heartbeats(api):
    client, store = api
    assert client.get("/api/kosu/isciler").status_code == 401
    headers = {"X-Test-User": "alice"}
    assert client.get("/api/kosu/isciler", headers=headers).json()["online"] is False
    store.worker_ping("ci-real-worker")
    state = client.get("/api/kosu/isciler", headers=headers).json()
    assert state["online"] is True and state["live_workers"] == 1
    store.worker_stopped("ci-real-worker")
    assert client.get("/api/kosu/isciler", headers=headers).json()["online"] is False


def test_cookie_task_mutations_reject_cross_origin_and_missing_origin(api):
    client, store = api
    url = "/api/kosu"
    payload = {"istek": "Should not execute"}
    headers = {"X-Test-User": "alice"}
    bad = [
        {"Origin": "https://evil.example"},
        {"Origin": "null"},
        {"Origin": "http://testserver", "Sec-Fetch-Site": "same-site"},
        {"Origin": "http://testserver", "Sec-Fetch-Site": "cross-site"},
    ]
    for extra in bad:
        response = client.post(url, headers={**headers, **extra}, json=payload)
        assert response.status_code == 403
    missing = client.post(url, headers={**headers, "Origin": ""}, json=payload)
    assert missing.status_code == 403
    assert store.list("alice") == []
    store.worker_ping("fixture-ready")
    good = client.post(url, headers={**headers,
                                   "Origin": "http://testserver",
                                   "Sec-Fetch-Site": "same-origin"}, json=payload)
    assert good.status_code == 202
    rid = good.json()["kosu"]["id"]
    assert client.post("/api/kosu/" + rid + "/iptal",
                       headers={**headers, "Origin": "http://evil.example"},
                       json={}).status_code == 403
    assert store.get("alice", rid)["durum"] == "queued"


def test_account_chat_uses_same_identity_and_durable_queue(tmp_path, monkeypatch):
    import app as host
    from chat.platform_identity import IdentityService, COOKIE
    from chat.platform_connections import ConnectionStore
    monkeypatch.setenv('BASAK_OTURUM_ANAHTARI', 'local-integration-session-key-' * 2)
    monkeypatch.setenv('BASAK_DURABLE_CHAT_ENABLED', 'true')
    db = kosu_deposu._SqliteDepo(str(tmp_path / 'account.db'))
    store = RuntimeStore(db)
    store.worker_ping('fixture-ready')
    accounts = IdentityService(ConnectionStore(db))
    user = accounts.account('github', 'fixture-subject', 'Fixture User')['id']
    monkeypatch.setattr('chat.platform_identity.IdentityService', lambda: accounts)
    monkeypatch.setattr(platform_api, '_store_factory', lambda: store)
    monkeypatch.setattr(host, '_kota_kapisi', lambda *args: (True, 10))
    client = TestClient(host.app, headers={'Origin': 'http://testserver'})
    client.cookies.set(COOKIE, accounts.issue_session(user))
    identity = client.post('/api/kimlik').json()
    assert identity['kullanici'] == user
    payload = {'metin': 'Continue my work', 'gecmis': [
        {'role': 'system', 'content': 'forged'}, {'role': 'user', 'content': 'earlier turn'}]}
    headers = {'Idempotency-Key': 'one-turn'}
    first = client.post('/api/sohbet', json=payload, headers=headers)
    assert first.status_code == 202
    rid = first.json()['kosu_id']
    assert client.post('/api/sohbet', json=payload, headers=headers).json()['kosu_id'] == rid
    job = store.get(user, rid)
    assert job['kind'] == 'chat'
    assert job['context']['history'] == [{'role': 'user', 'content': 'earlier turn'}]
    assert job['acceptance'][0]['kind'] == 'message_recorded'
    assert len(store.list(user)) == 1
    assert client.post('/api/sohbet', json=payload, headers={'Origin': 'https://other.example'}).status_code == 403


def test_reconciliation_requires_provider_observation_and_never_replays_write(api, monkeypatch):
    import base64
    from chat import platform_connectors
    client, store = api
    rid = store.create('alice', 'personal', 'external write')['id']
    lease = store.claim('w')['lease']
    args = {'baglanti_id': 'github-1', 'arac': 'github_write_file', 'argumanlar': {
        'repository': 'owner/repo', 'path': 'result.md', 'branch': 'feat/task',
        'content': base64.b64encode(b'delivered').decode()}}
    store.begin_action(lease, 'external-1', 'baglanti_cagir', args, side_effect=True)
    store.cancel('alice', rid)
    url = '/api/kosu/' + rid + '/uzlastir'
    headers = {'X-Test-User': 'alice'}
    assert client.post(url, headers=headers, json={'call_id': 'external-1', 'ok': True}).status_code == 400
    assert client.post(url, headers={'X-Test-User': 'bob'}, json={'call_id': 'external-1'}).status_code == 404
    observations = []
    def read(user, connection, tool, target):
        observations.append((user, connection, tool, target))
        return {'structuredContent': {'encoding': 'base64', 'content': base64.b64encode(b'delivered').decode()}}
    monkeypatch.setattr(platform_connectors, 'execute', read)
    monkeypatch.setattr(platform_connectors, 'tool_metadata', lambda *args: {'provider': 'github'})
    response = client.post(url, headers=headers, json={'call_id': 'external-1'})
    assert response.status_code == 200, response.text
    assert response.json()['kosu']['durum'] == 'paused'
    assert observations == [('alice', 'github-1', 'github_read_file', {
        'repository': 'owner/repo', 'path': 'result.md', 'ref': 'feat/task'})]
    store.resume('alice', rid)
    next_lease = store.claim('replacement')['lease']
    replay = store.begin_action(next_lease, 'external-1', 'baglanti_cagir', args, side_effect=True)
    assert replay['ok'] is True and replay['result']['raw']['result']['structuredContent']
    assert len(observations) == 1


def test_legacy_mime_artifact_is_downloaded_as_real_image(api):
    client, store = api
    import base64
    rid = store.create('alice', 'personal', 'screenshot')['id']
    aid = store.add_artifact('alice', rid, {'kind': 'browser', 'title': 'screen.png',
        'mime_type': 'image/png', 'data_base64': base64.b64encode(b'png fixture bytes').decode()})
    projection = store.get('alice', rid)['artifacts'][0]
    assert projection['media_type'] == 'image/png'
    response = client.get('/api/kosu/' + rid + '/artifacts/' + aid, headers={'X-Test-User': 'alice'})
    assert response.headers['content-type'] == 'image/png'
    assert response.content == b'png fixture bytes'


def test_account_chat_stream_observes_worker_final_after_commit(api, monkeypatch):
    monkeypatch.setenv('BASAK_FOREGROUND_CHAT', 'false')
    import threading
    import time
    import json
    import app as host
    from chat.platform_agents import execute_job
    from chat.platform_runtime import Worker
    _, store = api
    store.worker_ping('fixture-ready')
    monkeypatch.setattr(host, '_platform_kimlik', lambda request: 'alice')
    monkeypatch.setattr(host, '_kota_kapisi', lambda *args: (True, 10))
    monkeypatch.setattr(platform_api, '_store_factory', lambda: store)
    class Brain:
        def bulut_musait(self): return True
        def ajan_musait(self): return True
        def _bulut_zinciri(self, **kwargs): return []
        def cevapla(self, *args, **kwargs): return {'content': 'Durable response'}, 'native'
    def work():
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            rows = store.list('alice')
            if rows:
                Worker(store, lambda job, control: execute_job(job, control, Brain())).tick(rows[0]['id'])
                return
            time.sleep(0.01)
    worker = threading.Thread(target=work)
    worker.start()
    try:
        response = TestClient(host.app).post('/api/sohbet', json={'metin': 'hello'}, headers={
            'Origin': 'http://testserver', 'X-Test-User': 'alice',
            'Accept': 'application/x-ndjson', 'Idempotency-Key': 'stream-turn'})
    finally:
        worker.join(timeout=12)
    assert response.status_code == 200
    events = [json.loads(line) for line in response.text.splitlines()]
    rid = response.headers['X-Basak-Run-ID']
    assert events[0] == {'istek': rid, 'tur': 'durableRun', 'kosu_id': rid,
                         'conversation_id': rid, 'conversation_title': None, 'display_text': 'hello'}
    assert [e['cevap'] for e in events if e['tur'] == 'bitir'] == ['Durable response']
    assert store.get('alice', rid)['durum'] == 'completed'
    assert not any(e['tur'] in ('checkpoint', 'error') for e in events)


def test_account_stream_runs_on_web_without_oracle_worker(api, monkeypatch):
    import json
    import app as host
    from chat import platform_agents
    client, store = api
    monkeypatch.setenv('BASAK_FOREGROUND_CHAT', 'true')
    monkeypatch.setattr(host, '_platform_kimlik', lambda request: 'alice')
    monkeypatch.setattr(host, '_kota_kapisi', lambda *args: (True, 10))
    monkeypatch.setattr(platform_api, '_store_factory', lambda: store)
    executed = []
    def direct(job, control):
        executed.append(job['id'])
        control.record_check('response_recorded', True, {'observed': True})
        return {'answer': 'Direct response'}
    monkeypatch.setattr(platform_agents, 'execute_job', direct)
    response = TestClient(host.app).post('/api/sohbet',
        json={'metin': 'hello', 'conversation_id': 'thread-direct'},
        headers={'Origin': 'http://testserver', 'X-Test-User': 'alice',
                 'Accept': 'application/x-ndjson',
                 'Idempotency-Key': 'direct-turn'})
    assert response.status_code == 200
    rid = response.headers['X-Basak-Run-ID']
    events = [json.loads(line) for line in response.text.splitlines()]
    assert executed == [rid]
    assert [e['cevap'] for e in events if e['tur'] == 'bitir'] == ['Direct response']
    assert store.get('alice', rid)['durum'] == 'completed'
    assert store.chat_threads('alice')[0]['messages'][-1]['content'] == 'Direct response'
    assert store.worker_health()['live_workers'] == 0


def test_chat_threads_restore_title_pending_turn_and_tenant_boundary(api):
    client, store = api
    context = {'conversation_id': 'thread-1', 'conversation_title': 'Original title',
               'history': [{'role': 'user', 'content': 'earlier'}, {'role': 'assistant', 'content': 'reply'}],
               'display_text': 'Long task'}
    first = store.create('alice', 'personal', 'Long task', kind='chat', context=context)
    reopened = RuntimeStore(store.depo)
    data = client.get('/api/kosu/sohbetler', headers={'X-Test-User': 'alice'}).json()['chats']
    assert len(data) == 1 and data[0]['title'] == 'Original title'
    assert data[0]['messages'][-1] == {'role': 'user', 'content': 'Long task'}
    assert data[0]['pendingRuns'] == [{'id': first['id'], 'state': 'queued'}]
    assert client.get('/api/kosu/sohbetler', headers={'X-Test-User': 'bob'}).json()['chats'] == []
    assert reopened.chat_threads('alice')[0]['id'] == 'thread-1'
