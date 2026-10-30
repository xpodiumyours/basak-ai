"""Account/connection boundaries: real persistence, no real account traffic."""
import base64
import json

import pytest


@pytest.fixture
def store(monkeypatch, tmp_path):
    from chat import kosu_deposu
    monkeypatch.setattr(kosu_deposu, "_DEPO", None)
    monkeypatch.setenv("BASAK_GITHUB_APP_ID", "1")
    monkeypatch.setenv("BASAK_GITHUB_APP_SLUG", "basak-fixture")
    monkeypatch.setenv("BASAK_CONNECTION_KEY", base64.urlsafe_b64encode(b"k" * 32).decode())
    monkeypatch.setenv("BASAK_OTURUM_ANAHTARI", "test-session-secret-which-is-over-32-bytes")
    from chat.platform_connections import ConnectionStore
    return ConnectionStore(kosu_deposu._SqliteDepo(str(tmp_path / "accounts.db")))


def _github_connection(store, repository="a/b", user="alice", token=None, metadata=None):
    from chat.platform_github_app import AUTH_TYPE, PERMISSIONS
    details = {"auth_type": AUTH_TYPE, "repositories": [repository], "repository_ids": [3],
               "github_app_id": 1, "account_id": "42",
               "installations": [2],
               "writable_repositories": [repository], "permissions": dict(PERMISSIONS)}
    details.update(metadata or {})
    return store.save(user, "github", token or {"access_token": "ghu_fixture", "auth_type": AUTH_TYPE},
                      [], details)["id"]


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
        if req.method == "GET" and req.url.path == "/repos/a/b":
            return httpx.Response(200, json={"default_branch": "main", "permissions": {"push": True}})
        if req.method == "GET" and "/branches/" in req.url.path:
            return httpx.Response(200, json={"protected": False})
        return httpx.Response(200, json={"number": 1, "html_url": "https://github.com/a/b/pull/1"})

    cid = _github_connection(store)
    svc = ConnectorService(store, transport=httpx.MockTransport(transport))
    result = svc.execute("alice", cid, "github_create_pr", {
        "repository": "a/b", "title": "Change", "head": "basak/" + cid[:12] + "/change",
        "base": "main", "body": "Evidence"})
    assert result["structuredContent"]["number"] == 1
    assert [req.method for req in calls] == ["GET", "GET", "POST"]
    assert str(calls[-1].url) == "https://api.github.com/repos/a/b/pulls"
    assert json.loads(calls[-1].content)["draft"] is True
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
    from chat import platform_github_app
    monkeypatch.setenv("BASAK_PUBLIC_URL", "https://basak.example")
    monkeypatch.setenv("BASAK_GITHUB_CLIENT_ID", "client")
    monkeypatch.setenv("BASAK_GITHUB_CLIENT_SECRET", "client-secret")
    monkeypatch.setattr(api, "_store_factory", lambda: store)
    monkeypatch.setattr(api, "_authenticate", lambda request: request.headers.get("x-test-user"))
    monkeypatch.setattr(platform_github_app, "configured", lambda: True)
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


def test_github_app_oauth_never_requests_account_repository_scopes(api):
    from chat.platform_connectors import PROVIDERS
    from urllib.parse import urlsplit, parse_qs
    assert PROVIDERS["github"]["scopes"] == []
    for purpose in ("login", "connect"):
        response = api.get("/api/baglantilar/oauth/github/baslat?purpose=" + purpose,
                           headers={"x-test-user": "alice"}, follow_redirects=False)
        assert response.status_code == 302
        assert "scope" not in parse_qs(urlsplit(response.headers["location"]).query)


@pytest.mark.parametrize("scopes", [[], ["repo"], ["public_repo"]])
def test_legacy_github_oauth_connection_cannot_list_or_execute_tools(store, monkeypatch, scopes):
    from chat.platform_connectors import ConnectorService, ConnectorError
    cid = store.save("alice", "github", {"access_token": "legacy"}, scopes,
                     {"repositories": ["a/b"]})["id"]
    service = ConnectorService(store)
    assert service.tools("alice", cid) == []
    def forbidden(*args, **kwargs):
        pytest.fail("Legacy OAuth must be rejected before credential or network access")
    monkeypatch.setattr(store, "credentials", forbidden)
    monkeypatch.setattr(service, "_request", forbidden)
    for tool, args in (
        ("github_read_file", {"repository": "a/b", "path": "README.md"}),
        ("github_create_branch", {"repository": "a/b", "branch": "feat/task", "sha": "a" * 40}),
        ("github_dispatch_workflow", {"repository": "a/b", "workflow": "release.yml", "ref": "main"}),
    ):
        with pytest.raises(ConnectorError, match="yetki"):
            service.execute("alice", cid, tool, args)


@pytest.mark.parametrize('observed,should_match', [(b'expected', True), (b'wrong', False)])
def test_uncertain_github_write_uses_only_read_of_original_target(store, monkeypatch, observed, should_match):
    from chat import platform_connectors as module
    cid = _github_connection(store, repository='owner/repo')
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


def test_github_repository_metadata_uses_connected_owner_and_fixed_origin(store):
    import httpx
    from chat.platform_connectors import ConnectorService
    calls = []
    def transport(request):
        calls.append(request)
        return httpx.Response(200, json={"default_branch": "develop", "permissions": {"push": True}})
    cid = _github_connection(store)
    service = ConnectorService(store, transport=httpx.MockTransport(transport))
    result = service.execute("alice", cid, "github_get_repository", {"repository": "a/b"})
    assert result["structuredContent"]["default_branch"] == "develop"
    assert str(calls[0].url) == "https://api.github.com/repos/a/b"
    with pytest.raises(PermissionError):
        service.execute("bob", cid, "github_get_repository", {"repository": "a/b"})


def test_github_branch_commit_and_repository_pagination(store):
    import httpx
    from chat.platform_connectors import ConnectorService
    calls = []
    def transport(request):
        calls.append(request)
        return httpx.Response(200, json={"commit": {"sha": "a" * 40}})
    cid = _github_connection(store)
    service = ConnectorService(store, transport=httpx.MockTransport(transport))
    result = service.execute("alice", cid, "github_get_branch", {"repository": "a/b", "branch": "feat/start"})
    assert result["structuredContent"]["commit"]["sha"] == "a" * 40
    assert calls[-1].url.raw_path == b"/repos/a/b/branches/feat%2Fstart"
    result = service.execute("alice", cid, "github_list_repositories", {"page": 1})
    assert result["structuredContent"]["repositories"] == [{"full_name": "a/b", "writable": True}]
    assert result["structuredContent"]["total_count"] == 1
    result = service.execute("alice", cid, "github_list_repositories", {"page": 2})
    assert result["structuredContent"]["repositories"] == []
    assert len(calls) == 1, "Repository listing must use only revalidated connection selection"


@pytest.mark.parametrize("discovery_fails", [False, True])
def test_github_connect_stores_verified_app_user_credential_and_refresh(api, store, monkeypatch, discovery_fails):
    import httpx
    from urllib.parse import parse_qs, urlsplit
    from chat import platform_accounts_api as module, platform_github_app as github
    discovery = []
    def upstream(request):
        if request.url.host == "github.com":
            return httpx.Response(200, json={"access_token": "ghu_userfixture", "refresh_token": "ghr_refreshfixture", "scope": ""})
        assert request.url.path == "/user", "Repository discovery belongs to the verified GitHub App helper"
        return httpx.Response(200, json={"id": 42, "login": "alice"})
    def discover(user_token, profile, transport=None):
        discovery.append((dict(user_token), profile))
        if discovery_fails:
            raise github.GitHubAppError("Installation permissions do not match")
        return ({**user_token, "auth_type": github.AUTH_TYPE},
                {"auth_type": github.AUTH_TYPE, "github_app_id": 1,
                 "installations": [2],
                 "repositories": ["a/b"], "repository_ids": [3], "writable_repositories": ["a/b"],
                 "permissions": dict(github.PERMISSIONS)})
    monkeypatch.setattr(module, "_transport", httpx.MockTransport(upstream))
    monkeypatch.setattr(github, "discover_connection", discover)
    start = api.get("/api/baglantilar/oauth/github/baslat?purpose=connect",
                    headers={"x-test-user": "alice"}, follow_redirects=False)
    state = parse_qs(urlsplit(start.headers["location"]).query)["state"][0]
    result = api.get("/api/baglantilar/oauth/github/callback", params={"state": state, "code": "fixture"},
                     headers={"x-test-user": "alice"}, follow_redirects=False)
    assert discovery == [({"access_token": "ghu_userfixture", "refresh_token": "ghr_refreshfixture", "scope": ""},
                          {"id": 42, "login": "alice"})]
    rows = store.list("alice")
    if discovery_fails:
        assert result.status_code == 503
        assert rows == []
    else:
        assert result.status_code == 303
        assert len(rows) == 1
        assert rows[0]["metadata"]["repositories"] == ["a/b"]
        assert rows[0]["metadata"]["permissions"] == github.PERMISSIONS
        assert store.credentials("alice", rows[0]["id"]) == {
            "access_token": "ghu_userfixture", "refresh_token": "ghr_refreshfixture", "scope": "",
            "auth_type": github.AUTH_TYPE}
        assert "ghu_userfixture" not in json.dumps(rows) + result.text


@pytest.mark.parametrize("tool,path", [
    ("github_read_file", "../collaborators/example-user"),
    ("github_write_file", "../../other/contents/result.md"),
    ("github_write_file", "%252e%252e/collaborators/example-user"),
    ("github_read_file", ".env.production"),
    ("github_write_file", "config/secret.pem"),
    ("github_write_file", ".github/workflows/release.yml"),
    ("github_write_file", "AGENTS.md"),
    ("github_write_file", "chat/platform_connectors.py"),
    ("github_write_file", "deploy/oracle/setup.sh"),
])
def test_github_unsafe_paths_are_rejected_before_credentials_or_network(store, monkeypatch, tool, path):
    from chat.platform_connectors import ConnectorService
    cid = _github_connection(store)
    service = ConnectorService(store)
    def forbidden(*args, **kwargs):
        pytest.fail("Unsafe GitHub path reached credentials or transport")
    monkeypatch.setattr(service, "_token", forbidden)
    monkeypatch.setattr(service, "_request", forbidden)
    args = {"repository": "a/b", "path": path}
    if tool == "github_write_file":
        args.update(branch="basak/" + cid[:12] + "/change", message="Change", content="eA==")
    with pytest.raises(ValueError):
        service.execute("alice", cid, tool, args)


def test_github_selected_repository_is_enforced_before_credentials(store, monkeypatch):
    from chat.platform_connectors import ConnectorService, ConnectorError
    cid = _github_connection(store)
    service = ConnectorService(store)
    def forbidden(*args, **kwargs):
        pytest.fail("Other repository reached credentials or transport")
    monkeypatch.setattr(service, "_token", forbidden)
    monkeypatch.setattr(service, "_request", forbidden)
    with pytest.raises(ConnectorError, match="Depo"):
        service.execute("alice", cid, "github_read_file", {"repository": "a/other", "path": "README.md"})


def test_github_actions_are_denied_even_when_cost_guard_would_allow(store, monkeypatch):
    from chat.platform_connectors import ConnectorService, ConnectorError
    cid = _github_connection(store)
    service = ConnectorService(store, cost_guard=lambda *args: True)
    assert not any(t["name"].startswith(("github_get_run", "github_list_run", "github_list_artifact", "github_dispatch"))
                   for t in service.tools("alice", cid))
    def forbidden(*args, **kwargs):
        pytest.fail("Actions reached credentials or transport despite connection scope")
    monkeypatch.setattr(service, "_token", forbidden)
    monkeypatch.setattr(service, "_request", forbidden)
    with pytest.raises(ConnectorError, match="yetki"):
        service.execute("alice", cid, "github_dispatch_workflow",
                        {"repository": "a/b", "workflow": "release.yml", "ref": "main"})


@pytest.mark.parametrize("tool", ["github_create_branch", "github_write_file", "github_create_pr"])
def test_github_writes_require_connection_owned_branch_even_for_direct_call(store, monkeypatch, tool):
    from chat.platform_connectors import ConnectorService, ConnectorError
    cid = _github_connection(store)
    service = ConnectorService(store)
    def forbidden(*args, **kwargs):
        pytest.fail("Foreign branch reached credentials or transport")
    monkeypatch.setattr(service, "_token", forbidden)
    monkeypatch.setattr(service, "_request", forbidden)
    if tool == "github_create_branch":
        args = {"branch": "basak/another-owner/change", "sha": "a" * 40}
    elif tool == "github_write_file":
        args = {"branch": "main", "path": "README.md", "message": "Change", "content": "eA=="}
    else:
        args = {"head": "basak/another-owner/change", "base": "main", "title": "Change"}
    with pytest.raises(ConnectorError, match="gelistirme"):
        service.execute("alice", cid, tool, {"repository": "a/b", **args})


@pytest.mark.parametrize("protected", [True, None])
def test_github_protected_or_unknown_branch_never_receives_write(store, protected):
    import httpx
    from chat.platform_connectors import ConnectorService, ConnectorError
    cid = _github_connection(store)
    calls = []
    def transport(request):
        calls.append(request)
        assert request.method == "GET", "Protected branch received a mutation"
        return httpx.Response(200, json={"protected": protected} if "/branches/" in request.url.path
                              else {"default_branch": "main", "permissions": {"push": True}})
    service = ConnectorService(store, transport=httpx.MockTransport(transport))
    with pytest.raises(ConnectorError, match="Korunan"):
        service.execute("alice", cid, "github_write_file", {"repository": "a/b", "path": "README.md",
                        "branch": "basak/" + cid[:12] + "/change", "message": "Change", "content": "eA=="})
    assert len(calls) == 2


def test_github_custom_default_branch_cannot_be_written_even_in_owned_namespace(store):
    import httpx
    from chat.platform_connectors import ConnectorService, ConnectorError
    cid = _github_connection(store)
    branch = "basak/" + cid[:12] + "/default"
    calls = []
    def transport(request):
        calls.append(request)
        assert request.method == "GET"
        return httpx.Response(200, json={"default_branch": branch, "permissions": {"push": True}})
    service = ConnectorService(store, transport=httpx.MockTransport(transport))
    with pytest.raises(ConnectorError, match="Varsayilan"):
        service.execute("alice", cid, "github_write_file", {"repository": "a/b", "path": "README.md",
                        "branch": branch, "message": "Change", "content": "eA=="})
    assert len(calls) == 1


def test_github_new_branch_uses_owned_prefix_and_read_only_default_branch_preflight(store):
    import httpx
    from chat.platform_connectors import ConnectorService
    cid = _github_connection(store)
    branch = "basak/" + cid[:12] + "/change"
    calls = []
    def transport(request):
        calls.append(request)
        return httpx.Response(200 if request.method == "GET" else 201,
                              json={"default_branch": "main", "permissions": {"push": True}} if request.method == "GET"
                              else {"ref": "refs/heads/" + branch})
    service = ConnectorService(store, transport=httpx.MockTransport(transport))
    result = service.execute("alice", cid, "github_create_branch",
                             {"repository": "a/b", "branch": branch, "sha": "a" * 40})
    assert result["structuredContent"]["ref"] == "refs/heads/" + branch
    assert [r.method for r in calls] == ["GET", "POST"]
    assert calls[-1].url.path == "/repos/a/b/git/refs"
    assert json.loads(calls[-1].content) == {"ref": "refs/heads/" + branch, "sha": "a" * 40}


def test_github_non_draft_pr_is_denied_before_credentials(store, monkeypatch):
    from chat.platform_connectors import ConnectorService, ConnectorError
    cid = _github_connection(store)
    service = ConnectorService(store)
    def forbidden(*args, **kwargs):
        pytest.fail("Non-draft PR reached credentials or transport")
    monkeypatch.setattr(service, "_token", forbidden)
    monkeypatch.setattr(service, "_request", forbidden)
    with pytest.raises(ConnectorError, match="taslak"):
        service.execute("alice", cid, "github_create_pr", {"repository": "a/b", "title": "Change",
                        "head": "basak/" + cid[:12] + "/change", "base": "main", "draft": False})


def test_github_pr_must_target_verified_default_branch(store):
    import httpx
    from chat.platform_connectors import ConnectorService, ConnectorError
    cid = _github_connection(store)
    calls = []
    def transport(request):
        calls.append(request)
        assert request.method == "GET"
        return httpx.Response(200, json={"default_branch": "main", "permissions": {"push": True}})
    service = ConnectorService(store, transport=httpx.MockTransport(transport))
    with pytest.raises(ConnectorError, match="varsayilan"):
        service.execute("alice", cid, "github_create_pr", {"repository": "a/b", "title": "Change",
                        "head": "basak/" + cid[:12] + "/change", "base": "production"})
    assert len(calls) == 1


def test_github_app_metadata_cannot_make_a_legacy_token_usable(store, monkeypatch):
    from chat.platform_connectors import ConnectorService, ConnectorError
    cid = _github_connection(store, token={"access_token": "legacy"})
    service = ConnectorService(store)
    def forbidden(*args, **kwargs):
        pytest.fail("Legacy token reached HTTP transport")
    monkeypatch.setattr(service, "_request", forbidden)
    with pytest.raises(ConnectorError, match="uygulama"):
        service.execute("alice", cid, "github_get_repository", {"repository": "a/b"})


def test_github_provider_exposes_app_installation_selection_without_repo_scope(api):
    providers = api.get("/api/baglantilar/saglayicilar").json()["providers"]
    github = next(p for p in providers if p["id"] == "github")
    assert github["configured"] is True
    assert github["scopes"] == []
    assert github["installation_url"] == "https://github.com/apps/basak-fixture/installations/new"


def test_multiple_user_selected_repositories_support_reads_and_writes(store):
    import httpx
    from chat.platform_connectors import ConnectorService
    repositories = ["a/project-one", "team-b/project-two"]
    cid = _github_connection(store, metadata={"repositories": repositories, "repository_ids": [3, 4],
                                             "writable_repositories": repositories})
    calls = []
    def transport(request):
        calls.append(request)
        if "/branches/" in request.url.path:
            return httpx.Response(200, json={"protected": False})
        if request.method == "GET" and "/contents/" not in request.url.path:
            return httpx.Response(200, json={"default_branch": "develop", "permissions": {"push": True}})
        return httpx.Response(200, json={"content": {"sha": "a" * 40}})
    service = ConnectorService(store, transport=httpx.MockTransport(transport))
    listed = service.execute("alice", cid, "github_list_repositories", {})["structuredContent"]
    assert listed["repositories"] == [{"full_name": name, "writable": True} for name in repositories]
    assert calls == []
    for repository in repositories:
        service.execute("alice", cid, "github_read_file", {"repository": repository, "path": "README.md"})
        service.execute("alice", cid, "github_write_file", {"repository": repository, "path": "README.md",
                        "branch": "basak/" + cid[:12] + "/change", "message": "Change", "content": "eA=="})
    assert [r.url.path for r in calls if r.method == "PUT"] == [
        "/repos/" + repository + "/contents/README.md" for repository in repositories]


def test_live_repository_permission_revocation_blocks_write_but_keeps_read(store):
    import httpx
    from chat.platform_connectors import ConnectorService, ConnectorError
    cid = _github_connection(store)
    calls = []
    def transport(request):
        calls.append(request)
        assert request.method == "GET", "Read-only user received a repository mutation"
        if "/contents/" in request.url.path:
            return httpx.Response(200, json={"encoding": "base64", "content": "eA=="})
        return httpx.Response(200, json={"default_branch": "main", "permissions": {"push": False}})
    service = ConnectorService(store, transport=httpx.MockTransport(transport))
    assert service.execute("alice", cid, "github_read_file", {"repository": "a/b", "path": "README.md"})["isError"] is False
    # Stored writable selection may be stale; the live user's permission wins.
    with pytest.raises(ConnectorError, match="yazma yetkisi"):
        service.execute("alice", cid, "github_write_file", {"repository": "a/b", "path": "README.md",
                        "branch": "basak/" + cid[:12] + "/change", "message": "Change", "content": "eA=="})
    assert len(calls) == 2


def test_github_readonly_selected_repository_is_listed_as_readonly(store, monkeypatch):
    from chat.platform_connectors import ConnectorService
    cid = _github_connection(store, metadata={"writable_repositories": []})
    service = ConnectorService(store)
    monkeypatch.setattr(service, "_request", lambda *args, **kwargs: pytest.fail("Listing leaked into broad provider listing"))
    rows = service.execute("alice", cid, "github_list_repositories", {})["structuredContent"]["repositories"]
    assert rows == [{"full_name": "a/b", "writable": False}]
