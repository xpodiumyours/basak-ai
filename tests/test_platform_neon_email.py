"""Managed Neon email sign-in: all provider interactions are mocked."""
import base64

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from chat import platform_accounts_api as api
from chat.kosu_deposu import _SqliteDepo
from chat.platform_connections import ConnectionStore
from chat.platform_identity import COOKIE, IdentityService
from chat.platform_neon_email import auth_base

NEON_PREVIEW = "https://ep-synthetic-test.neonauth.c-12.us-east-1.aws.neon.tech/neondb/auth"


@pytest.fixture
def configured(monkeypatch, tmp_path):
    monkeypatch.setenv("VERCEL_ENV", "preview")
    monkeypatch.setenv("BASAK_NEON_EMAIL_ENABLED", "true")
    monkeypatch.setenv("BASAK_PREVIEW_NEON_AUTH_BASE_URL", NEON_PREVIEW)
    monkeypatch.setenv("BASAK_PREVIEW_DATABASE_URL",
                       "postgresql://user:test@preview.invalid/neondb")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:test@production.invalid/neondb")
    monkeypatch.setenv("BASAK_CONNECTION_KEY",
                       base64.urlsafe_b64encode(b"k" * 32).decode())
    monkeypatch.setenv("BASAK_OTURUM_ANAHTARI", "a-test-secret-longer-than-thirty-two-bytes")
    monkeypatch.setenv("BASAK_PUBLIC_URL", "https://basak.example")
    store = ConnectionStore(_SqliteDepo(str(tmp_path / "neon-login.db")))
    monkeypatch.setattr(api, "_store_factory", lambda: store)

    def resolve(request):
        token = request.cookies.get(COOKIE, "")
        account = IdentityService(store).resolve_session(token) if token else None
        return account["id"] if account else None

    monkeypatch.setattr(api, "_authenticate", resolve)
    app = FastAPI()
    app.include_router(api.router)
    return TestClient(app, base_url="https://basak.example"), store, monkeypatch


def _fake_neon(request, *, email_verified=True, signout=200):
    if request.url.path.endswith("/sign-in/email"):
        return httpx.Response(200, json={"user": {"id": "user-neon-42",
            "email": "alice@example.test", "emailVerified": email_verified,
            "name": "Alice"}, "token": "must-not-leak"},
            headers={"set-cookie":
                     "better-auth.session_token=temp-neon-secret; Path=/neondb/auth; HttpOnly; Secure; SameSite=Lax"})
    if request.url.path.endswith("/sign-out"):
        assert "better-auth.session_token=temp-neon-secret" in request.headers.get("cookie", "")
        return httpx.Response(signout, json={"success": signout == 200})
    return httpx.Response(404)


def test_verified_login_persists_and_logout_revokes(configured):
    client, store, monkeypatch = configured
    called = []
    def remote(request):
        called.append(request.url.path)
        return _fake_neon(request)
    monkeypatch.setattr(api, "_transport", httpx.MockTransport(remote))
    resp = client.post("/api/hesap/eposta/giris",
                       json={"email": "alice@example.test", "password": "synthetic-secret"},
                       headers={"Origin": "https://basak.example"})
    assert resp.status_code == 200
    assert resp.json()["authenticated"] is True
    assert "synthetic-secret" not in str(resp.headers) + resp.text
    assert "must-not-leak" not in str(resp.headers) + resp.text
    assert any(x.endswith("/sign-out") for x in called)
    session = client.cookies.get(COOKIE)
    assert session
    assert client.get("/api/hesap").json()["authenticated"] is True
    assert store._db._sorgu("SELECT count(*) AS n FROM basak_account")[0]["n"] == 1
    assert client.post("/api/hesap/cikis",
                       headers={"Origin": "https://basak.example"}).status_code == 204
    client.cookies.set(COOKIE, session)
    assert client.get("/api/hesap").json()["authenticated"] is False


def test_unverified_email_rejected_and_neon_session_revoked(configured):
    client, store, monkeypatch = configured
    calls = []
    def remote(request):
        calls.append(request.url.path)
        return _fake_neon(request, email_verified=False)
    monkeypatch.setattr(api, "_transport", httpx.MockTransport(remote))
    resp = client.post("/api/hesap/eposta/giris",
                       json={"email": "alice@example.test", "password": "test-pass"},
                       headers={"Origin": "https://basak.example"})
    assert resp.status_code == 401
    assert any(x.endswith("/sign-out") for x in calls)
    assert store._db._sorgu("SELECT count(*) AS n FROM basak_account")[0]["n"] == 0


def test_failed_upstream_signout_never_creates_account(configured):
    client, store, monkeypatch = configured
    monkeypatch.setattr(api, "_transport",
                        httpx.MockTransport(lambda r: _fake_neon(r, signout=500)))
    resp = client.post("/api/hesap/eposta/giris",
                       json={"email": "alice@example.test", "password": "test-pass"},
                       headers={"Origin": "https://basak.example"})
    assert resp.status_code == 503
    assert store._db._sorgu("SELECT count(*) AS n FROM basak_account")[0]["n"] == 0


def test_untrusted_origin_and_disabled_feature_rejected_without_upstream(configured):
    client, store, monkeypatch = configured
    def forbidden(_):
        raise AssertionError("Provider must not be called")
    monkeypatch.setattr(api, "_transport", httpx.MockTransport(forbidden))
    resp = client.post("/api/hesap/eposta/giris",
                       json={"email": "alice@example.test", "password": "test-pass"},
                       headers={"Origin": "https://attacker.example"})
    assert resp.status_code == 403
    monkeypatch.setenv("BASAK_NEON_EMAIL_ENABLED", "false")
    assert client.post("/api/hesap/eposta/giris",
                       json={"email": "alice@example.test", "password": "test-pass"},
                       headers={"Origin": "https://basak.example"}).status_code == 503
    providers = client.get("/api/baglantilar/saglayicilar").json()["providers"]
    assert "neon_email" not in {p["id"] for p in providers}


@pytest.mark.parametrize("bad", [
    "http://ep-synthetic-test.neonauth.c-12.us-east-1.aws.neon.tech/neondb/auth",
    "https://attacker.example/neondb/auth",
    "https://ep-synthetic-test.neonauth.c-12.us-east-1.aws.neon.tech/other",
    "https://ep-synthetic-test.neonauth.c-12.us-east-1.aws.neon.tech/neondb/auth?x=1",
    "https://user:pass@ep-synthetic-test.neonauth.c-12.us-east-1.aws.neon.tech/neondb/auth",
])
def test_unsafe_neon_hosts_fail_closed(configured, bad):
    _, _, monkeypatch = configured
    monkeypatch.setenv("BASAK_PREVIEW_NEON_AUTH_BASE_URL", bad)
    assert auth_base() == ""


def test_preview_url_is_required_not_shared_production_url(configured):
    _, _, monkeypatch = configured
    monkeypatch.delenv("BASAK_PREVIEW_NEON_AUTH_BASE_URL")
    monkeypatch.setenv("BASAK_PRODUCTION_NEON_AUTH_BASE_URL", NEON_PREVIEW)
    assert auth_base() == ""


def test_fail_closed_when_neon_email_login_key_missing(configured):
    _, _, monkeypatch = configured
    monkeypatch.delenv("BASAK_CONNECTION_KEY")
    assert auth_base() == ""
