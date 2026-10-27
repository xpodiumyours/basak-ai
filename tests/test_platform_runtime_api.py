"""HTTP authentication, durable observers, and explicit acceptance behavior."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from chat import kosu_deposu, platform_api
from chat.platform_runtime import RuntimeStore


@pytest.fixture
def api(tmp_path):
    store = RuntimeStore(kosu_deposu._SqliteDepo(str(tmp_path / "api.db")))
    app = FastAPI()
    onceki = (platform_api._principal, platform_api._store_factory)
    platform_api.configure(lambda request: request.headers.get("X-Test-User"), lambda: store)
    app.include_router(platform_api.router)
    yield TestClient(app), store
    platform_api._principal, platform_api._store_factory = onceki


def test_api_requires_identity_and_does_not_start_execution(api):
    client, store = api
    assert client.post("/api/kosu", json={"istek": "task"}).status_code == 401
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
