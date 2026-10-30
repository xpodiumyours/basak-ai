"""GitHub App user OAuth: selected repositories and no privilege elevation."""
import httpx
import pytest
from chat import platform_github_app as module


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("BASAK_GITHUB_APP_ID", "42")
    monkeypatch.setenv("BASAK_GITHUB_APP_SLUG", "basak-fixture")
    monkeypatch.setenv("BASAK_GITHUB_CLIENT_ID", "fixture-client")
    monkeypatch.setenv("BASAK_GITHUB_CLIENT_SECRET", "fixture-secret")
    monkeypatch.setattr(module.time, "time", lambda: 1700000000)


@pytest.fixture
def provider():
    return {"installations": [{"id": 77, "app_id": 42, "repository_selection": "selected",
                "account": {"id": 9, "type": "User"}, "permissions": dict(module.PERMISSIONS)}],
            "repositories": {77: [{"id": 123, "full_name": "owner/code"}]},
            "permissions": {"owner/code": {"pull": True, "push": True}},
            "profile": {"id": 9}, "calls": [],
            "refresh": {"access_token": "ghu_fixture-renewed", "refresh_token": "fixture-new-refresh", "expires_in": 28800}}


def transport_for(provider):
    def request(req):
        provider["calls"].append(req)
        if req.url.host == "github.com":
            return httpx.Response(200, json=provider["refresh"])
        if req.url.path == "/user":
            return httpx.Response(200, json=provider["profile"])
        if req.url.path == "/user/installations":
            return httpx.Response(200, json={"installations": provider["installations"]})
        if req.url.path.startswith("/user/installations/"):
            iid = int(req.url.path.split("/")[3])
            return httpx.Response(200, json={"repositories": provider["repositories"][iid]})
        if req.url.path.startswith("/repos/"):
            name = req.url.path[len("/repos/"):]
            row = next(r for rows in provider["repositories"].values() for r in rows if r["full_name"] == name)
            return httpx.Response(200, json={**row, "permissions": provider["permissions"][name]})
        raise AssertionError("Unexpected GitHub endpoint " + req.url.path)
    return httpx.MockTransport(request)


def connection(provider):
    token, meta = module.discover_connection({"access_token": "ghu_fixture-user", "refresh_token": "fixture-refresh"},
                                            {"id": 9}, transport_for(provider))
    return token, {"provider": "github", "metadata": meta}


def test_user_credentials_preserved_without_privatekey_or_repo_allowlist(app, provider):
    original = {"access_token": "ghu_fixture-user", "refresh_token": "fixture-refresh", "expires_at": 1700028800}
    token, meta = module.discover_connection(original, {"id": 9}, transport_for(provider))
    assert token == {**original, "auth_type": "github_app_user"}
    assert meta == {"auth_type": "github_app_user", "github_app_id": 42, "account_id": "9",
                    "installations": [77], "repository_ids": [123], "repositories": ["owner/code"],
                    "writable_repositories": ["owner/code"], "permissions": module.PERMISSIONS}
    assert "auth_type" not in original
    assert all(r.method == "GET" and r.headers["Authorization"] == "Bearer ghu_fixture-user" for r in provider["calls"])
    assert not any("access_tokens" in r.url.path for r in provider["calls"])
    module.validate_connection({"provider": "github", "metadata": meta})


def test_multiple_selected_repos_and_org_user_permission_intersection(app, provider):
    provider["installations"].append({"id": 88, "app_id": 42, "repository_selection": "selected",
        "account": {"id": 999, "type": "Organization"}, "permissions": dict(module.PERMISSIONS)})
    provider["repositories"][88] = [{"id": 456, "full_name": "team/other"}]
    provider["permissions"]["team/other"] = {"pull": True, "push": False}
    _, conn = connection(provider)
    assert conn["metadata"]["repositories"] == ["owner/code", "team/other"]
    assert conn["metadata"]["writable_repositories"] == ["owner/code"]
    assert conn["metadata"]["installations"] == [77, 88]


@pytest.mark.parametrize("field", ["BASAK_GITHUB_APP_ID", "BASAK_GITHUB_APP_SLUG"])
def test_configuration_requires_only_app_identity(app, monkeypatch, field):
    assert module.configured()
    monkeypatch.delenv(field)
    assert not module.configured()


@pytest.mark.parametrize("change", [
    {"repository_selection": "all"}, {"suspended_at": "2026-10-30T00:00:00Z"},
    {"permissions": {**module.PERMISSIONS, "administration": "write"}},
    {"permissions": {**module.PERMISSIONS, "workflows": "write"}},
    {"permissions": {**module.PERMISSIONS, "secrets": "read"}},
    {"permissions": {**module.PERMISSIONS, "actions": "write"}}])
def test_broad_or_suspended_installation_rejected(app, provider, change):
    provider["installations"][0].update(change)
    with pytest.raises(module.GitHubAppError):
        connection(provider)


def test_other_apps_ignored(app, provider):
    provider["installations"].append({"id": 999, "app_id": 99, "repository_selection": "all"})
    _, conn = connection(provider)
    assert conn["metadata"]["installations"] == [77]
    assert not any("999" in r.url.path for r in provider["calls"])


def test_readonly_user_does_not_receive_installation_privileges(app, provider):
    provider["permissions"]["owner/code"] = {"pull": True, "push": False}
    _, conn = connection(provider)
    assert conn["metadata"]["repositories"] == ["owner/code"]
    assert conn["metadata"]["writable_repositories"] == []
    assert all(r.method == "GET" for r in provider["calls"])


@pytest.mark.parametrize("credential", ["gho_classic-oauth", "ghs_installation", "", "ghu_"])
def test_non_user_app_credentials_rejected_before_network(app, provider, credential):
    with pytest.raises(module.GitHubAppError):
        module.discover_connection(credential, {"id": 9}, transport_for(provider))
    assert provider["calls"] == []


@pytest.mark.parametrize("change", [{"github_app_id": 43}, {"auth_type": "github_app_installation"},
    {"repository_ids": []}, {"repositories": ["owner/code", "owner/code"]},
    {"writable_repositories": ["unselected/repo"]}, {"permissions": {**module.PERMISSIONS, "administration": "write"}}])
def test_validate_rejects_stale_or_malformed_metadata(app, provider, change):
    _, conn = connection(provider)
    conn["metadata"].update(change)
    with pytest.raises(module.GitHubAppError):
        module.validate_connection(conn)


def test_refresh_preserves_account_and_rediscovers_selection(app, provider):
    token, conn = connection(provider)
    provider["repositories"][77] = [{"id": 789, "full_name": "another/selection"}]
    provider["permissions"]["another/selection"] = {"pull": True, "push": False}
    provider["calls"].clear()
    renewed, meta = module.refresh_connection(conn, token, transport_for(provider))
    assert renewed["access_token"] == "ghu_fixture-renewed"
    assert renewed["refresh_token"] == "fixture-new-refresh"
    assert renewed["expires_at"] == 1700028800
    assert meta["repositories"] == ["another/selection"]
    assert meta["writable_repositories"] == []
    assert provider["calls"][0].url == "https://github.com/login/oauth/access_token"
    assert b"grant_type=refresh_token" in provider["calls"][0].content
    assert all(r.url.host in ("github.com", "api.github.com") for r in provider["calls"])


def test_refresh_rejects_different_account(app, provider):
    token, conn = connection(provider)
    provider["profile"] = {"id": 10}
    with pytest.raises(module.GitHubAppError):
        module.refresh_connection(conn, token, transport_for(provider))


@pytest.mark.parametrize("response", [{"error": "invalid_grant"}, {},
    {"access_token": "gho_wrong-type"}, {"access_token": "ghu_new", "expires_in": 0}])
def test_failed_refresh_never_reuses_old_token(app, provider, response):
    token, conn = connection(provider)
    provider["refresh"] = response
    with pytest.raises(module.GitHubAppError):
        module.refresh_connection(conn, token, transport_for(provider))


def test_http_errors_do_not_echo_credentials(app):
    transport = httpx.MockTransport(lambda req: httpx.Response(403, json={"message": "ghu_fixture-user secret"}))
    with pytest.raises(module.GitHubAppError) as error:
        module.discover_connection("ghu_fixture-user", {"id": 9}, transport)
    assert "ghu_fixture-user" not in str(error.value)
    assert "secret" not in str(error.value)


def test_pagination_never_follows_external_link(app, provider):
    original = transport_for(provider).handler
    def handle(req):
        if req.url.path == "/user/installations" and req.url.params["page"] == "1":
            provider["calls"].append(req)
            return httpx.Response(200, json={"installations": [{"id": 1, "app_id": 99}]},
                                  headers={"link": '<https://attacker.invalid/>; rel="next"'})
        return original(req)
    _, meta = module.discover_connection("ghu_fixture-user", {"id": 9}, httpx.MockTransport(handle))
    assert meta["repository_ids"] == [123]
    calls = [r for r in provider["calls"] if r.url.path == "/user/installations"]
    assert [r.url.params["page"] for r in calls] == ["1", "2"]
    assert all(r.url.host == "api.github.com" for r in provider["calls"])
