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
    monkeypatch.setenv("BASAK_COMPOSIO_VERIFIER_READY", "1")
    return module


def _fake_api(gateway, user="alice", connected=True):
    requests = []
    url = "https://backend.composio.dev/tool_router/v3/trs_fixture99/mcp"
    def call(method, path, *, data=None, params=None):
        requests.append((method, path, data, params))
        if method == "GET" and path == "/api/v3.1/toolkits":
            return {"items": [
                {"slug": "github", "name": "GitHub",
                 "composio_managed_auth_schemes": ["oauth2"],
                 "meta": {"description": "Repository access"}},
                {"slug": "slack", "name": "Slack",
                 "composio_managed_auth_schemes": ["oauth2"],
                 "meta": {"description": "Team messages"}},
                {"slug": "private_key", "name": "Bring your key",
                 "composio_managed_auth_schemes": [],
                 "meta": {}}],
                 "next_cursor": None}
        if method == "POST" and path == "/api/v3.1/connected_accounts/complete_auth":
            if data["user_id"] != gateway._user_id(user):
                return {"connected_account_id": "ca_wrong_user", "toolkit_slug": "github"}
            return {"connected_account_id": "ca_fixture", "toolkit_slug": "github"}
        if method == "GET" and path == "/api/v3.1/connected_accounts/ca_fixture":
            return {"id": "ca_fixture", "user_id": gateway._user_id(user),
                    "status": "ACTIVE" if connected else "FAILED",
                    "toolkit": {"slug": "github"}}
        if method == "GET" and path == "/api/v3.1/connected_accounts/ca_wrong_user":
            return {"id": "ca_wrong_user", "user_id": gateway._user_id("mallory"),
                    "status": "ACTIVE", "toolkit": {"slug": "github"}}
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
                               "toolkits": {"enabled": ["github"]},
                               "connected_accounts": {"github": ["ca_fixture"]},
                               "instant": False},
                    "mcp": {"url": url}}
        if method == "GET" and path.endswith("/tools"):
            return {"items": [{"slug": "GITHUB_GET_REPO",
                               "toolkit": {"slug": "github"},
                               "description": "Read a repository",
                               "input_parameters": {
                                   "repository": {"type": "string", "required": True}
                               }}], "next_cursor": None}
        if method == "POST" and path.endswith("/execute"):
            return {"result_type": "completed", "data": {"ok": True, "repository": data["arguments"]["repository"]}}
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
        "instant": False,
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
        "composio_account_id": "ca_fixture", "url": url}})
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


def test_verified_oauth_callback_and_user_isolation(api_client, gateway, monkeypatch):
    client, store = api_client
    call, requests, _ = _fake_api(gateway)
    monkeypatch.setattr(gateway, "_request", call)
    # The old callback without provider-identity verification is retired.
    assert client.get("/api/baglantilar/composio/callback?state=x",
                      headers={"x-test-user": "alice"}).status_code == 410
    start = client.get("/api/baglantilar/composio/baslat?toolkit=github",
                       headers={"x-test-user": "alice"}, follow_redirects=False)
    assert start.status_code == 302
    assert start.headers["location"].startswith("https://app.composio.dev/link/")
    assert store.list("alice") == []
    assert requests[1][2]["callback_url"] == "https://basak.example/api/baglantilar/composio/dogrula"
    # Composio's verifier, unlike the redirect query state, verifies the
    # identity of the person who actually consented at the provider.
    callback = client.get("/api/baglantilar/composio/dogrula?session_uri=uri_fixture_123456",
                          headers={"x-test-user": "alice"}, follow_redirects=False)
    assert callback.status_code == 303
    assert len(store.list("alice")) == 1
    assert store.list("bob") == []
    assert client.get("/api/baglantilar", headers={"x-test-user": "bob"}).json() == {"connections": []}
    assert "test-project-key-not-real" not in str(store.list("alice"))


def test_catalog_has_managed_oauth_and_no_secret(api_client, gateway, monkeypatch):
    client, _ = api_client
    call, _, _ = _fake_api(gateway)
    monkeypatch.setattr(gateway, "_request", call)
    response = client.get("/api/baglantilar/composio/katalog?search=git",
                          headers={"x-test-user": "alice"})
    assert response.status_code == 200
    assert {x["id"] for x in response.json()["toolkits"]} == {"github", "slack"}
    assert "test-project-key-not-real" not in response.text
    assert client.get("/api/baglantilar/composio/katalog").status_code == 401
    assert client.get("/api/baglantilar/composio/katalog?search=" + "x" * 110,
                      headers={"x-test-user": "alice"}).status_code == 502


def test_legacy_github_connection_is_retired_but_sign_in_preserved(api_client):
    client, _ = api_client
    url = "/api/baglantilar/oauth/github/baslat"
    assert client.get(url + "?purpose=connect", headers={"x-test-user": "alice"}).status_code == 410
    assert client.get(url + "?purpose=login", headers={"x-test-user": "alice"}).status_code != 410


def test_identity_verifier_is_mandatory(api_client, monkeypatch):
    client, _ = api_client
    monkeypatch.delenv("BASAK_COMPOSIO_VERIFIER_READY")
    assert client.get("/api/baglantilar/composio/baslat?toolkit=github",
                      headers={"x-test-user": "alice"}).status_code == 503
    assert client.get("/api/baglantilar/composio/dogrula?session_uri=uri_fixture_123456",
                      headers={"x-test-user": "alice"}).status_code == 503


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


def test_callback_rejects_cross_user_connected_account(gateway, monkeypatch):
    call, calls, _ = _fake_api(gateway, user="bob")
    monkeypatch.setattr(gateway, "_request", call)
    with pytest.raises(gateway.ComposioError):
        gateway.complete_verified_auth("alice", "uri_identity_mismatch")
    # Never even create a session when account ownership cannot be proven.
    assert not any(path == "/api/v3.1/tool_router/session" for _, path, _, _ in calls)



def test_documented_v31_rest_execute_response_succeeds(gateway, monkeypatch):
    call, _, url = _fake_api(gateway)
    def documented(method, path, *, data=None, params=None):
        result = call(method, path, data=data, params=params)
        if method == "POST" and path.endswith("/execute"):
            return {"data": result["data"], "error": None,
                    "log_id": "log_accepted"}
        return result
    monkeypatch.setattr(gateway, "_request", documented)
    result = gateway.session_execute("alice", {"metadata": {
        "composio_toolkit": "github", "composio_session_id": "trs_fixture99",
        "composio_account_id": "ca_fixture", "url": url
    }}, "GITHUB_GET_REPO", {"repository": "owner/repo"})
    assert result["isError"] is False
    assert result["structuredContent"]["repository"] == "owner/repo"


def test_failed_execute_response_never_reports_success(gateway, monkeypatch):
    call, requests, url = _fake_api(gateway)
    def failed(method, path, *, data=None, params=None):
        if path.endswith("/execute"):
            return {"result_type": "failed", "data": {"success": True}}
        return call(method, path, data=data, params=params)
    monkeypatch.setattr(gateway, "_request", failed)
    result = gateway.session_execute("alice", {"metadata": {
        "composio_toolkit": "github", "composio_session_id": "trs_fixture99", "composio_account_id": "ca_fixture", "url": url
    }}, "GITHUB_GET_REPO", {"repository": "owner/repo"})
    assert result["isError"] is True
    assert result["structuredContent"] == {"error": "Composio araci basarisiz"}


def test_instant_must_remain_disabled_when_reloading_session(gateway, monkeypatch):
    call, _, url = _fake_api(gateway)
    def charge_enabled(method, path, *, data=None, params=None):
        result = call(method, path, data=data, params=params)
        if method == "GET" and path.endswith("/trs_fixture99"):
            result["config"]["instant"] = {}
        return result
    monkeypatch.setattr(gateway, "_request", charge_enabled)
    with pytest.raises(gateway.ComposioError, match="Instant"):
        gateway.finish_session("alice", {
            "session_id": "trs_fixture99", "url": url, "toolkit": "github"})


def test_pinned_account_is_not_switchable_by_another_composio_account(gateway, monkeypatch):
    call, requests, url = _fake_api(gateway)
    monkeypatch.setattr(gateway, "_request", call)
    meta = gateway.finish_session("alice", {
        "session_id": "trs_fixture99", "url": url, "toolkit": "github"})
    assert meta["composio_account_id"] == "ca_fixture"
    wrong = dict(meta, composio_account_id="ca_other_account")
    with pytest.raises(gateway.ComposioError):
        gateway.session_execute("alice", {"metadata": wrong},
                                "GITHUB_GET_REPO", {"repository": "owner/repo"})
    assert not any(path.endswith("/execute") for _, path, _, _ in requests)
    with pytest.raises(gateway.ComposioError):
        gateway.disconnect("alice", {"metadata": wrong})
    assert not any(method == "DELETE" for method, _, _, _ in requests)


def test_verified_auth_creates_account_pinned_session(gateway, monkeypatch):
    call, requests, url = _fake_api(gateway)
    monkeypatch.setattr(gateway, "_request", call)
    meta = gateway.complete_verified_auth("alice", "uri_fixture_123456")
    assert meta["composio_account_id"] == "ca_fixture"
    create = [data for method, path, data, _ in requests
              if method == "POST" and path == "/api/v3.1/tool_router/session"]
    assert create[-1]["connected_accounts"] == {"github": ["ca_fixture"]}
    assert create[-1]["instant"] is False


def test_missing_or_changed_pinned_account_disables_execution(gateway, monkeypatch):
    call, requests, url = _fake_api(gateway)
    monkeypatch.setattr(gateway, "_request", call)
    with pytest.raises(gateway.ComposioError):
        gateway.session_execute("alice", {"metadata": {
            "composio_session_id": "trs_fixture99", "composio_toolkit": "github",
            "url": url
        }}, "GITHUB_GET_REPO", {"repository": "owner/repo"})
    assert not any(path.endswith("/execute") for _, path, _, _ in requests)


@pytest.mark.parametrize("execute_body", [
    {"data": {"repository": "owner/repo"}, "error": {"message": "Denied"}},
    {"data": {"success": False}, "error": None},
    {"data": {"isError": True}, "error": None},
    {"data": {"repository": "owner/repo"}, "result_type": "failed", "error": None},
    {"data": {}, "instant_charge": True, "error": None},
])
def test_session_execute_rejects_documented_failure_shapes(gateway, monkeypatch,
                                                          execute_body):
    call, _, url = _fake_api(gateway)
    def failing(method, path, *, data=None, params=None):
        if path.endswith("/execute"):
            return execute_body
        return call(method, path, data=data, params=params)
    monkeypatch.setattr(gateway, "_request", failing)
    result = gateway.session_execute("alice", {"metadata": {
        "composio_toolkit": "github", "composio_session_id": "trs_fixture99",
        "composio_account_id": "ca_fixture", "url": url,
    }}, "GITHUB_GET_REPO", {"repository": "owner/repo"})
    assert result["isError"] is True
