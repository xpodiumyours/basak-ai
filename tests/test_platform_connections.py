"""Account/connection boundaries: real persistence, no real account traffic."""
import base64
import json

import pytest


@pytest.fixture
def store(monkeypatch, tmp_path):
    from chat import kosu_deposu
    monkeypatch.setattr(kosu_deposu, "_DEPO", None)
    monkeypatch.setenv("BASAK_CONNECTION_KEY", base64.urlsafe_b64encode(b"k" * 32).decode())
    monkeypatch.setenv("BASAK_OTURUM_ANAHTARI", "test-session-secret-which-is-over-32-bytes")
    from chat.platform_connections import ConnectionStore
    return ConnectionStore(kosu_deposu._SqliteDepo(str(tmp_path / "accounts.db")))


def test_tokens_encrypted_and_tenant_scoped(store):
    cid = store.save("u-alice", "github", {"access_token": "private-github-token"},
                     ["repo"], {"label": "Alice GitHub"})["id"]
    assert store.get("u-bob", cid) is None
    assert store.list("u-bob") == []
    public = json.dumps(store.list("u-alice"))
    assert "private-github-token" not in public
    assert "access_token" not in public
    rows = store._db._sorgu("SELECT secret FROM basak_connection WHERE id = %s", (cid,))
    assert "private-github-token" not in rows[0]["secret"]
    assert store.credentials("u-alice", cid)["access_token"] == "private-github-token"
    with pytest.raises(PermissionError):
        store.credentials("u-bob", cid)


def test_ciphertext_cannot_move_between_tenants(store):
    a = store.save("alice", "google", {"access_token": "a"}, [], {})["id"]
    b = store.save("bob", "google", {"access_token": "b"}, [], {})["id"]
    secret = store._db._sorgu("SELECT secret FROM basak_connection WHERE id = %s", (a,))[0]["secret"]
    store._db._calistir("UPDATE basak_connection SET secret = %s WHERE id = %s", (secret, b))
    with pytest.raises(PermissionError):
        store.credentials("bob", b)


def test_revocation_removes_secret_and_blocks_call(store):
    cid = store.save("alice", "notion", {"access_token": "x"}, [], {})["id"]
    assert store.revoke("bob", cid) is False
    assert store.revoke("alice", cid) is True
    with pytest.raises(PermissionError):
        store.credentials("alice", cid)
    assert store._db._sorgu("SELECT secret FROM basak_connection WHERE id = %s", (cid,))[0]["secret"] == ""


def test_oauth_state_bound_to_browser_provider_and_single_use(store):
    state, verifier = store.oauth_begin("github", "browser-a", "alice", "connect", "/")
    assert len(verifier) >= 43
    with pytest.raises(PermissionError):
        store.oauth_consume(state, "google", "browser-a")
    with pytest.raises(PermissionError):
        store.oauth_consume(state, "github", "browser-b")
    row = store.oauth_consume(state, "github", "browser-a")
    assert row["user_id"] == "alice"
    assert row["verifier"] == verifier
    with pytest.raises(PermissionError):
        store.oauth_consume(state, "github", "browser-a")


def test_identity_does_not_merge_equal_emails(store):
    from chat.platform_identity import IdentityService
    service = IdentityService(store)
    a = service.account("github", "42", "Alice", "same@example.test")
    b = service.account("google", "42", "Alice", "same@example.test")
    assert a["id"] != b["id"]
    assert service.account("github", "42", "new name", "different@example.test")["id"] == a["id"]
    token = service.issue_session(a["id"])
    assert service.resolve_session(token)["id"] == a["id"]
    assert service.resolve_session(token + "tamper") is None
    service.revoke_session(token)
    assert service.resolve_session(token) is None


def test_no_master_key_does_not_store_plaintext(store, monkeypatch):
    monkeypatch.delenv("BASAK_CONNECTION_KEY")
    with pytest.raises(RuntimeError, match="anahtar"):
        store.save("alice", "google", {"access_token": "secret"}, [], {})


def test_google_missing_broad_scope_rejected(store):
    from chat.platform_connectors import ConnectorService, ConnectorError
    cid = store.save("alice", "google", {"access_token": "x"},
                     ["https://www.googleapis.com/auth/drive.file"], {})["id"]
    with pytest.raises(ConnectorError, match="yetki"):
        ConnectorService(store).execute("alice", cid, "drive_search", {"query": "x"})


def test_github_call_owner_and_safe_fixed_host(store):
    import httpx
    from chat.platform_connectors import ConnectorService
    calls = []

    def transport(req):
        calls.append(req)
        return httpx.Response(200, json={"number": 1, "html_url": "https://github.com/a/b/pull/1"})

    cid = store.save("alice", "github", {"access_token": "x"}, ["public_repo"],
                     {"repositories": ["a/b"]})["id"]
    svc = ConnectorService(store, transport=httpx.MockTransport(transport))
    result = svc.execute("alice", cid, "github_create_pr", {
        "repository": "a/b", "title": "Change", "head": "feat/x", "base": "main", "body": "Evidence"})
    assert result["structuredContent"]["number"] == 1
    assert str(calls[0].url) == "https://api.github.com/repos/a/b/pulls"
    with pytest.raises(PermissionError):
        svc.execute("bob", cid, "github_create_pr", {"repository": "a/b"})


def test_refresh_error_never_reuses_expired_token(store):
    import httpx
    from chat.platform_connectors import ConnectorService, ConnectorError
    cid = store.save("alice", "google", {"access_token": "expired", "refresh_token": "r", "expires_at": 1},
                     ["https://www.googleapis.com/auth/drive.readonly"], {})["id"]
    def response(req):
        return httpx.Response(400, json={"error": "invalid_grant"})
    svc = ConnectorService(store, transport=httpx.MockTransport(response))
    with pytest.raises(ConnectorError):
        svc.execute("alice", cid, "drive_search", {"query": "name contains 'x'"})
    assert store.get("alice", cid)["status"] == "reauth_required"


def test_mcp_names_and_structured_records_preserved():
    from chat.platform_mcp import namespace, normalize_result
    assert namespace("my-server", "read_file").startswith("mcp__")
    raw = {"content": [{"type": "text", "text": "summary"}],
           "structuredContent": {"rows": [{"id": 1, "value": "full"}]}, "isError": False}
    assert normalize_result(raw) == raw


def test_mcp_private_endpoints_rejected():
    from chat.platform_mcp import validate_endpoint
    for url in ("http://127.0.0.1/mcp", "https://169.254.169.254/mcp", "https://example.com:22/mcp", "https://a:b@example.com/mcp"):
        with pytest.raises(ValueError):
            validate_endpoint(url)


@pytest.fixture
def api(store, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from chat import platform_accounts_api as api
    monkeypatch.setenv("BASAK_PUBLIC_URL", "https://basak.example")
    monkeypatch.setenv("BASAK_GITHUB_CLIENT_ID", "client")
    monkeypatch.setenv("BASAK_GITHUB_CLIENT_SECRET", "client-secret")
    monkeypatch.setattr(api, "_store_factory", lambda: store)
    monkeypatch.setattr(api, "_authenticate", lambda request: request.headers.get("x-test-user"))
    app = FastAPI()
    app.include_router(api.router)
    return TestClient(app, base_url="https://basak.example")


def test_api_connection_lists_and_revoke_are_owned(api, store):
    cid = store.save("alice", "github", {"access_token": "private"}, [], {})["id"]
    assert api.get("/api/baglantilar").status_code == 401
    assert api.get("/api/baglantilar", headers={"x-test-user": "bob"}).json() == {"connections": []}
    assert api.delete("/api/baglantilar/" + cid, headers={"x-test-user": "bob"}).status_code == 404
    assert api.delete("/api/baglantilar/" + cid, headers={"x-test-user": "alice", "origin": "https://evil.example"}).status_code == 403
    assert api.delete("/api/baglantilar/" + cid, headers={"x-test-user": "alice", "origin": "https://basak.example"}).status_code == 204


def test_api_login_flow_callback_replay_and_cookie_flags(api, store, monkeypatch):
    import httpx
    from urllib.parse import parse_qs, urlsplit
    from chat import platform_accounts_api as module
    def upstream(request):
        if request.url.host == "github.com":
            return httpx.Response(200, json={"access_token": "private-token"})
        if request.url.path == "/user":
            return httpx.Response(200, json={"id": 42, "name": "Alice"})
        return httpx.Response(200, json=[])
    monkeypatch.setattr(module, "_transport", httpx.MockTransport(upstream))
    start = api.get("/api/baglantilar/oauth/github/baslat?purpose=login", follow_redirects=False)
    query = parse_qs(urlsplit(start.headers["location"]).query)
    assert query["code_challenge_method"] == ["S256"]
    assert "httponly" in start.headers["set-cookie"].lower()
    callback = "/api/baglantilar/oauth/github/callback?state=" + query["state"][0] + "&code=code"
    response = api.get(callback, follow_redirects=False)
    assert response.status_code == 303
    cookies = response.headers.get_list("set-cookie")
    assert any("basak_platform_session=" in c and "HttpOnly" in c and "Secure" in c for c in cookies)
    assert "private-token" not in response.text + str(response.headers)
    assert api.get(callback, follow_redirects=False).status_code == 400


def test_api_connect_cannot_switch_owner_mid_oauth(api, monkeypatch):
    from urllib.parse import parse_qs, urlsplit
    start = api.get("/api/baglantilar/oauth/github/baslat?purpose=connect", headers={"x-test-user": "alice"}, follow_redirects=False)
    state = parse_qs(urlsplit(start.headers["location"]).query)["state"][0]
    response = api.get("/api/baglantilar/oauth/github/callback", params={"state": state, "code": "code"}, headers={"x-test-user": "bob"})
    assert response.status_code == 400


def test_mcp_catalog_execution_validates_owner_permissions_and_preserves_data(store):
    import asyncio
    from contextlib import asynccontextmanager
    from mcp.types import Tool, ListToolsResult, CallToolResult, TextContent
    from chat.platform_mcp import MCPService, namespace
    calls = []
    class Session:
        async def list_tools(self, cursor=None):
            return ListToolsResult(tools=[Tool(name="read", inputSchema={"type": "object", "required": ["key"], "properties": {"key": {"type": "string"}}})])
        async def call_tool(self, name, args):
            calls.append((name, args))
            return CallToolResult(content=[TextContent(type="text", text="summary")], structuredContent={"full": [1, 2, 3]})
    @asynccontextmanager
    async def factory(*args):
        yield Session()
    cid = store.save("alice", "mcp", {}, [], {"url": "https://mcp.example", "allowed_tools": ["read"]})["id"]
    service = MCPService(store, session_factory=factory)
    tools = asyncio.run(service.discover("alice", cid))
    name = namespace(cid, "read")
    assert tools[0]["name"] == name
    result = asyncio.run(service.execute("alice", cid, name, {"key": "x"}))
    assert result["structuredContent"] == {"full": [1, 2, 3]}
    with pytest.raises(PermissionError):
        asyncio.run(service.execute("bob", cid, name, {"key": "x"}))
    with pytest.raises(ValueError):
        asyncio.run(service.execute("alice", cid, name, {"key": 1}))
    assert calls == [("read", {"key": "x"})]


def test_mcp_write_without_grant_and_revoked_connection_are_rejected(store):
    import asyncio
    from contextlib import asynccontextmanager
    from mcp.types import Tool, ListToolsResult, CallToolResult, TextContent
    from chat.platform_mcp import MCPService, namespace

    class Session:
        async def list_tools(self, cursor=None):
            schema = {"type": "object", "properties": {"key": {"type": "string"}}, "required": ["key"]}
            return ListToolsResult(tools=[
                Tool(name="read", inputSchema=schema),
                Tool(name="write", inputSchema=schema),
            ])
        async def call_tool(self, name, args):
            return CallToolResult(content=[TextContent(type="text", text="ok")],
                                  structuredContent={"ok": True})

    @asynccontextmanager
    async def factory(*args):
        yield Session()

    cid = store.save("alice", "mcp", {}, [], {"url": "https://mcp.example", "allowed_tools": ["read"]})["id"]
    service = MCPService(store, session_factory=factory)
    asyncio.run(service.discover("alice", cid))
    write = namespace(cid, "write")
    with pytest.raises(PermissionError, match="yetki"):
        asyncio.run(service.execute("alice", cid, write, {"key": "x"}))
    read = namespace(cid, "read")
    store.revoke("alice", cid)
    with pytest.raises(PermissionError):
        asyncio.run(service.execute("alice", cid, read, {"key": "x"}))


def test_mcp_permission_update_checks_discovered_names(api, store):
    cid = store.save("alice", "mcp", {}, [], {"url": "https://mcp.example", "allowed_tools": [], "tools": [{"name": "mcp__x__read", "remote_name": "read", "inputSchema": {"type": "object"}}]})["id"]
    path = "/api/baglantilar/" + cid
    assert api.patch(path, json={"allowed_tools": ["write"]}, headers={"x-test-user": "alice"}).status_code == 400
    assert api.patch(path, json={"allowed_tools": ["read"]}, headers={"x-test-user": "bob"}).status_code == 404
    assert api.patch(path, json={"allowed_tools": ["read"]}, headers={"x-test-user": "alice"}).status_code == 200
    assert store.get("alice", cid)["metadata"]["allowed_tools"] == ["read"]


def test_github_oauth_connect_requests_public_repo_but_login_does_not(api):
    from chat.platform_connectors import PROVIDERS
    from urllib.parse import urlsplit, parse_qs
    assert PROVIDERS["github"]["scopes"] == ["public_repo"]
    login = api.get("/api/baglantilar/oauth/github/baslat?purpose=login",
                    follow_redirects=False)
    connect = api.get("/api/baglantilar/oauth/github/baslat?purpose=connect",
                      headers={"x-test-user": "alice"}, follow_redirects=False)
    assert "scope" not in parse_qs(urlsplit(login.headers["location"]).query)
    assert parse_qs(urlsplit(connect.headers["location"]).query)["scope"] == ["public_repo"]


def test_github_public_repo_write_requires_scope_even_with_approved_tool(store):
    import httpx
    from chat.platform_connectors import ConnectorService, ConnectorError
    requests = []

    def fake(request):
        requests.append(request)
        return httpx.Response(201, json={"ref": "refs/heads/feat/test"})

    basic = store.save("alice", "github", {"access_token": "basic"}, [],
                       {"repositories": ["a/b"]})["id"]
    private = store.save("alice", "github", {"access_token": "private"}, ["repo"],
                         {"repositories": ["a/b"]})["id"]
    public = store.save("alice", "github", {"access_token": "public"}, ["public_repo"],
                        {"repositories": ["a/b"]})["id"]
    service = ConnectorService(store, transport=httpx.MockTransport(fake))
    writes = {"github_create_branch", "github_write_file", "github_create_pr", "github_dispatch_workflow"}
    assert writes.isdisjoint({t["name"] for t in service.tools("alice", basic)})
    assert {"github_read_file"}.issubset({t["name"] for t in service.tools("alice", basic)})
    arguments = {"repository": "a/b", "branch": "feat/test", "sha": "a"*40}
    with pytest.raises(ConnectorError, match="yetki"):
        service.execute("alice", basic, "github_create_branch", arguments)
    assert requests == [], "Write without GitHub scope reached network"
    assert writes.issubset({t["name"] for t in service.tools("alice", private)})
    assert writes.issubset({t["name"] for t in service.tools("alice", public)})
    service.execute("alice", public, "github_create_branch", arguments)
    assert len(requests) == 1


@pytest.mark.parametrize('observed,should_match', [(b'expected', True), (b'wrong', False)])
def test_uncertain_github_write_uses_only_read_of_original_target(store, monkeypatch, observed, should_match):
    from chat import platform_connectors as module
    cid = store.save('alice', 'github', {'access_token': 'fixture'}, ['repo'],
                     {'repositories': ['owner/repo']})['id']
    monkeypatch.setattr(module, 'ConnectionStore', lambda: store)
    requests = []
    def get(self, method, url, token, **kwargs):
        requests.append((method, url, kwargs))
        return {'encoding': 'base64', 'content': base64.b64encode(observed).decode()}
    monkeypatch.setattr(module.ConnectorService, '_request', get)
    action = {'tool': 'baglanti_cagir', 'arguments': {'baglanti_id': cid,
        'arac': 'github_write_file', 'argumanlar': {'repository': 'owner/repo',
        'path': 'result.md', 'branch': 'feat/task', 'content': base64.b64encode(b'expected').decode()}}}
    if should_match:
        assert module.observe_uncertain_action('alice', action)['target']['ref'] == 'feat/task'
    else:
        with pytest.raises(module.ConnectorError, match='eslesmiyor'):
            module.observe_uncertain_action('alice', action)
    assert len(requests) == 1
    assert requests[0][0:2] == ('GET', 'https://api.github.com/repos/owner/repo/contents/result.md')
    assert requests[0][2]['params'] == {'ref': 'feat/task'}
    with pytest.raises(PermissionError):
        module.observe_uncertain_action('bob', action)


def test_uncertain_unsupported_mutation_never_retries_provider(monkeypatch):
    from chat import platform_connectors as module
    def forbidden(*args):
        pytest.fail('Unsupported mutation must remain uncertain without provider traffic')
    monkeypatch.setattr(module, 'execute', forbidden)
    with pytest.raises(module.ConnectorError, match='belirsiz kalir'):
        module.observe_uncertain_action('alice', {'tool': 'tarayici_kullan', 'arguments': {}})


def test_mcp_tool_cannot_impersonate_native_provider_observation(monkeypatch):
    from chat import platform_connectors as module
    monkeypatch.setattr(module, 'tool_metadata', lambda *args: {'provider': 'mcp'})
    def forbidden(*args):
        pytest.fail('MCP cannot provide trusted native GitHub evidence')
    monkeypatch.setattr(module, 'execute', forbidden)
    with pytest.raises(module.ConnectorError, match='yerel saglayici'):
        module.observe_uncertain_action('alice', {'tool': 'baglanti_cagir', 'arguments': {
            'baglanti_id': 'mcp-1', 'arac': 'github_write_file', 'argumanlar': {}}})
