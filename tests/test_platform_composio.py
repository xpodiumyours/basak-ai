"""Offline acceptance tests for Composio Sessions v3.1.

No live Composio API key or third-party account access is required.
"""
import base64
from urllib.parse import urlsplit

import pytest


@pytest.fixture
def gateway(monkeypatch):
    from chat import platform_composio as module
    monkeypatch.setenv("COMPOSIO_API_KEY", "test-project-key-not-real")
    monkeypatch.setenv("BASAK_CONNECTION_KEY", base64.urlsafe_b64encode(b"x" * 32).decode())
    return module


def _fake_api(gateway, user="alice", connected=True):
    requests = []
    url = "https://backend.composio.dev/tool_router/v3/trs_fixture99/mcp"
    def call(method, path, *, data=None, params=None):
        requests.append((method, path, data, params))
        if method == "POST" and path == "/api/v3.1/tool_router/session":
            return {"session_id": "trs_fixture99", "mcp": {"url": url}}
        if method == "POST" and path.endswith("/link"):
            return {"redirect_url": "https://app.composio.dev/link/lt_fixture"}
        if method == "GET" and path.endswith("/toolkits"):
            return {"items": [{
                "slug": "github",
                "connected_account": {
                    "status": "ACTIVE" if connected else "FAILED",
                    "user_id": gateway._user_id(user),
                    "id": "ca_fixture",
                }
            }]}
        if method == "GET" and path.endswith("/trs_fixture99"):
            return {"config": {"user_id": gateway._user_id(user),
                               "toolkits": {"enabled": ["github"]}},
                    "mcp": {"url": url}}
        if method == "GET" and path.endswith("/tools"):
            return {"items": [{"slug": "GITHUB_GET_REPO",
                               "toolkit": {"slug": "github"},
                               "description": "Read a repository",
                               "input_parameters": {
                                   "repository": {"type": "string", "required": True}
                               }}], "next_cursor": None}
        if method == "POST" and path.endswith("/execute"):
            return {"data": {"ok": True, "repository": data["arguments"]["repository"]}}
        if method == "DELETE":
            return {}
        raise AssertionError((method, path))
    return call, requests, url


def test_tenant_ids_are_distinct(gateway):
    a, b = gateway._user_id("alice"), gateway._user_id("bob")
    assert a != b and a == gateway._user_id("alice")
    assert len(a) == 70 and "alice" not in a


@pytest.mark.parametrize("url", [
    "http://backend.composio.dev/tool_router/v3/mcp",
    "https://evil.example/tool_router/v3/mcp",
    "https://backend.composio.dev.evil.example/tool_router/v3/mcp",
    "https://u:p@backend.composio.dev/tool_router/v3/mcp",
    "https://backend.composio.dev:444/tool_router/v3/mcp",
    "https://backend.composio.dev/tool_router/v3/mcp#bad",
    "https://backend.composio.dev/private",
])
def test_project_key_is_origin_restricted(gateway, url):
    with pytest.raises(gateway.ComposioError):
        gateway.validate_mcp_url(url)


def test_project_key_stays_in_server_headers(gateway):
    url = "https://backend.composio.dev/tool_router/v3/trs_12345/mcp"
    assert gateway.validate_mcp_url(url) == url
    assert gateway.validate_mcp_url("https://app.composio.dev/tool_router/v3/trs_12345/mcp")

def test_session_create_and_oauth_link(gateway, monkeypatch):
    call, requests, url = _fake_api(gateway)
    monkeypatch.setattr(gateway, "_request", call)
    result = gateway.create_session("alice", "github")
    assert result == {"session_id": "trs_fixture99", "url": url, "toolkit": "github"}
    assert requests[0][2] == {
        "user_id": gateway._user_id("alice"),
        "toolkits": {"enabled": ["github"]},
        "experimental": {"no_elicitation_support_fallback": "deny"},
    }
    assert gateway.authorize_session("trs_fixture99", "github", "https://basak.example/callback") == (
        "https://app.composio.dev/link/lt_fixture")
    assert requests[1][2]["callback_url"] == "https://basak.example/callback"
    with pytest.raises(gateway.ComposioError):
        gateway.create_session("alice", "unapproved-app")


def test_finish_checks_identity_and_live_connection(gateway, monkeypatch):
    call, requests, url = _fake_api(gateway)
    monkeypatch.setattr(gateway, "_request", call)
    result = gateway.finish_session("alice", {
        "session_id": "trs_fixture99", "url": url, "toolkit": "github"})
    assert result["composio_toolkit"] == "github" and result["allowed_tools"] == []
    assert "test-project-key-not-real" not in str(result)
    with pytest.raises(gateway.ComposioError):
        gateway.finish_session("bob", {
            "session_id": "trs_fixture99", "url": url, "toolkit": "github"})


def test_unconnected_account_is_rejected(gateway, monkeypatch):
    call, _, url = _fake_api(gateway, connected=False)
    monkeypatch.setattr(gateway, "_request", call)
    with pytest.raises(gateway.ComposioError):
        gateway.finish_session("alice", {
            "session_id": "trs_fixture99", "url": url, "toolkit": "github"})


def test_provider_account_deleted_on_disconnect(gateway, monkeypatch):
    call, requests, url = _fake_api(gateway)
    monkeypatch.setattr(gateway, "_request", call)
    gateway.disconnect("alice", {"metadata": {
        "composio_session_id": "trs_fixture99", "composio_toolkit": "github",
        "url": url}})
    assert requests[-1][:2] == ("DELETE", "/api/v3.1/connected_accounts/ca_fixture")


@pytest.fixture
def api_client(gateway, monkeypatch, tmp_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from chat import platform_accounts_api as api
    from chat import kosu_deposu
    from chat.platform_connections import ConnectionStore
    monkeypatch.setenv("BASAK_PUBLIC_URL", "https://basak.example")
    store = ConnectionStore(kosu_deposu._SqliteDepo(str(tmp_path / "composio.db")))
    monkeypatch.setattr(api, "_store_factory", lambda: store)
    monkeypatch.setattr(api, "_authenticate", lambda req: req.headers.get("x-test-user"))
    app = FastAPI()
    app.include_router(api.router)
    return TestClient(app, base_url="https://basak.example"), store


def test_browser_bound_callback_and_user_isolation(api_client, gateway, monkeypatch):
    client, store = api_client
    call, _, url = _fake_api(gateway)
    monkeypatch.setattr(gateway, "_request", call)
    saved = {}
    original = gateway.authorize_session
    def redirect(sid, tk, callback):
        saved["callback"] = callback
        return original(sid, tk, callback)
    monkeypatch.setattr(gateway, "authorize_session", redirect)
    start = client.get("/api/baglantilar/composio/baslat?toolkit=github",
                       headers={"x-test-user": "alice"}, follow_redirects=False)
    assert start.status_code == 302
    assert start.headers["location"].startswith("https://app.composio.dev/link/")
    assert store.list("alice") == []
    callback = urlsplit(saved["callback"])
    cb = client.get(callback.path + "?" + callback.query,
                    headers={"x-test-user": "alice"}, follow_redirects=False)
    assert cb.status_code == 303
    assert len(store.list("alice")) == 1
    assert store.list("bob") == []
    visible = client.get("/api/baglantilar", headers={"x-test-user": "alice"}).json()
    assert "test-project-key-not-real" not in str(visible)
    assert client.get("/api/baglantilar", headers={"x-test-user": "bob"}).json() == {"connections": []}
    assert store.list("alice")[0]["metadata"]["url"] == url


def test_missing_key_fails_closed(api_client, monkeypatch):
    client, _ = api_client
    monkeypatch.delenv("COMPOSIO_API_KEY")
    info = client.get("/api/baglantilar/saglayicilar").json()
    item = next(p for p in info["providers"] if p["id"] == "composio")
    assert item["configured"] is False
    response = client.get("/api/baglantilar/composio/baslat?toolkit=github",
                          headers={"x-test-user": "alice"})
    assert response.status_code == 503


def test_direct_rest_tools_are_tenant_scoped_and_never_use_mcp_host(
        gateway, monkeypatch):
    from chat.platform_mcp import MCPService
    from chat.platform_connections import ConnectionStore
    from chat.kosu_deposu import _SqliteDepo
    import tempfile
    call, calls, url = _fake_api(gateway)
    monkeypatch.setattr(gateway, "_request", call)
    with tempfile.TemporaryDirectory() as folder:
        store = ConnectionStore(_SqliteDepo(folder + "/composio.db"))
        meta = gateway.finish_session("alice", {
            "session_id": "trs_fixture99", "url": url, "toolkit": "github"})
        cid = store.save("alice", "mcp", {}, [], meta)["id"]
        service = MCPService(store)
        # Discover via REST and do not expose any tool until user enables it.
        tools = __import__("asyncio").run(
            service.discover("alice", cid))
        assert len(tools) == 1
        t = tools[0]
        assert t["remote_name"] == "GITHUB_GET_REPO"
        assert t["inputSchema"]["required"] == ["repository"]
        with pytest.raises(PermissionError):
            service.execute_sync("alice", cid, t["name"], {"repository": "owner/repo"})
        with pytest.raises(PermissionError):
            service.execute_sync("bob", cid, t["name"], {"repository": "owner/repo"})
        meta["tools"] = tools
        meta["allowed_tools"] = [t["name"]]
        store.save("alice", "mcp", {}, [], meta, cid)
        result = service.execute_sync("alice", cid, t["name"], {"repository": "owner/repo"})
        assert result["structuredContent"] == {"ok": True, "repository": "owner/repo"}
        assert all(path.startswith("/api/v3.1/") for _, path, _, _ in calls)
        assert ("POST", "/api/v3.1/tool_router/session/trs_fixture99/execute",
                {"tool_slug": "GITHUB_GET_REPO",
                 "arguments": {"repository": "owner/repo"},
                 "account": "ca_fixture"}, None) in calls
