"""OAuth startup readiness: do not invite users into a broken login flow."""
import base64

import pytest


@pytest.fixture
def oauth_env(monkeypatch):
    for name in ("VERCEL", "BASAK_URETIM", "VERCEL_ENV",
                 "DATABASE_URL", "POSTGRES_URL", "NEON_DATABASE_URL",
                 "BASAK_PREVIEW_DATABASE_URL", "BASAK_ISCI_DATABASE_URL"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("BASAK_PUBLIC_URL", "https://basak.example")
    monkeypatch.setenv("BASAK_GITHUB_CLIENT_ID", "synthetic-client-id")
    monkeypatch.setenv("BASAK_GITHUB_CLIENT_SECRET", "synthetic-client-secret")
    monkeypatch.setenv("BASAK_OTURUM_ANAHTARI", "synthetic-secret-longer-than-32-bytes")
    monkeypatch.setenv(
        "BASAK_CONNECTION_KEY", base64.urlsafe_b64encode(b"x" * 32).decode())
    return monkeypatch


def test_provider_configuration_requires_signed_session_and_encryption(oauth_env):
    from chat.platform_connectors import provider_config

    assert provider_config("github")["configured"] is True
    oauth_env.delenv("BASAK_OTURUM_ANAHTARI")
    assert provider_config("github")["configured"] is False
    oauth_env.setenv("BASAK_OTURUM_ANAHTARI", "synthetic-secret-longer-than-32-bytes")
    oauth_env.setenv("BASAK_CONNECTION_KEY", "not-a-32-byte-key")
    assert provider_config("github")["configured"] is False


@pytest.mark.parametrize("url", [
    "https://basak.example/other",
    "https://basak.example/?x=1",
    "https://user:password@basak.example",
    "http://basak.example",
    "https://basak.example/#fragment",
    "https://",
])
def test_provider_configuration_rejects_invalid_public_origins(oauth_env, url):
    from chat.platform_connectors import provider_config

    oauth_env.setenv("BASAK_PUBLIC_URL", url)
    assert provider_config("github")["configured"] is False


def test_live_host_requires_persistent_database_before_oauth(oauth_env):
    from chat.platform_connectors import provider_config

    oauth_env.setenv("VERCEL", "1")
    assert provider_config("github")["configured"] is False
    oauth_env.setenv("DATABASE_URL", "postgresql://test:pass@prod.example/basak")
    assert provider_config("github")["configured"] is True


def test_preview_oauth_rejects_shared_database_with_production(oauth_env):
    from chat.platform_connectors import provider_config

    oauth_env.setenv("VERCEL", "1")
    oauth_env.setenv("VERCEL_ENV", "preview")
    oauth_env.setenv("DATABASE_URL", "postgresql://test:pass@prod.example/basak")
    assert provider_config("github")["configured"] is False
    oauth_env.setenv("BASAK_PREVIEW_DATABASE_URL",
                     "postgresql://test:pass@prod.example/basak")
    assert provider_config("github")["configured"] is False
    oauth_env.setenv("BASAK_PREVIEW_DATABASE_URL",
                     "postgresql://test:pass@preview.example/basak")
    assert provider_config("github")["configured"] is True


def test_api_refuses_oauth_start_before_creating_state(oauth_env):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from chat import platform_accounts_api as endpoints

    oauth_env.delenv("BASAK_CONNECTION_KEY")

    def forbidden():
        raise AssertionError("OAuth state persisted despite missing encryption key")

    oauth_env.setattr(endpoints, "_store_factory", forbidden)
    app = FastAPI()
    app.include_router(endpoints.router)
    client = TestClient(app, base_url="https://basak.example")
    resp = client.get("/api/baglantilar/oauth/github/baslat?purpose=login",
                      follow_redirects=False)
    assert resp.status_code == 503
    providers = client.get("/api/baglantilar/saglayicilar").json()["providers"]
    assert next(p for p in providers if p["id"] == "github")["configured"] is False
    assert "synthetic-client-secret" not in resp.text


def test_mock_oauth_session_survives_new_database_connection_and_revokes(
        oauth_env, tmp_path):
    """No network secrets: prove the real cookie-backed account ledger persists."""
    import httpx
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from urllib.parse import parse_qs, urlsplit
    from chat import platform_accounts_api as endpoints
    from chat import kosu_deposu
    from chat.platform_connections import ConnectionStore
    from chat.platform_identity import COOKIE, IdentityService

    database = str(tmp_path / "durable-login.sqlite")
    store = ConnectionStore(kosu_deposu._SqliteDepo(database))
    oauth_env.setattr(endpoints, "_store_factory", lambda: store)

    def authenticated(request):
        account = IdentityService(endpoints._store_factory()).resolve_session(
            request.cookies.get(COOKIE, ""))
        return account["id"] if account else None

    oauth_env.setattr(endpoints, "_authenticate", authenticated)

    def fake_provider(request):
        if request.url.host == "github.com":
            return httpx.Response(200, json={"access_token": "synthetic-provider-token"})
        if request.url.host == "api.github.com" and request.url.path == "/user":
            return httpx.Response(200, json={"id": 13579, "name": "Durable user"})
        return httpx.Response(404)

    oauth_env.setattr(endpoints, "_transport",
                      httpx.MockTransport(fake_provider))
    app = FastAPI()
    app.include_router(endpoints.router)
    client = TestClient(app, base_url="https://basak.example")
    start = client.get("/api/baglantilar/oauth/github/baslat?purpose=login",
                       follow_redirects=False)
    assert start.status_code == 302
    state = parse_qs(urlsplit(start.headers["location"]).query)["state"][0]
    callback = client.get("/api/baglantilar/oauth/github/callback",
                          params={"state": state, "code": "synthetic-code"},
                          follow_redirects=False)
    assert callback.status_code == 303
    session = client.cookies.get(COOKIE)
    assert session
    before = client.get("/api/hesap").json()
    assert before["authenticated"] is True
    user_id = before["user"]["id"]

    # Equivalent to another serverless process loading the same durable DB.
    fresh_store = ConnectionStore(kosu_deposu._SqliteDepo(database))
    oauth_env.setattr(endpoints, "_store_factory", lambda: fresh_store)
    fresh_client = TestClient(app, base_url="https://basak.example")
    fresh_client.cookies.set(COOKIE, session)
    after = fresh_client.get("/api/hesap").json()
    assert after["authenticated"] is True
    assert after["user"]["id"] == user_id
    assert "synthetic-provider-token" not in str(after)

    assert fresh_client.post("/api/hesap/cikis",
                             headers={"Origin": "https://basak.example"}).status_code == 204
    fresh_client.cookies.set(COOKIE, session)
    assert fresh_client.get("/api/hesap").json()["authenticated"] is False
