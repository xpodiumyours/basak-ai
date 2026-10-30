"""Offline contract tests for the new Composio Sessions adapter.

No Composio secret, provider token, or network call is used in CI.
"""
import base64
from types import SimpleNamespace as NS
from urllib.parse import urlsplit, parse_qs

import pytest


@pytest.fixture
def gateway(monkeypatch):
    from chat import platform_composio as module
    monkeypatch.setenv("COMPOSIO_API_KEY", "test-project-key-not-real")
    monkeypatch.setenv("BASAK_CONNECTION_KEY", base64.urlsafe_b64encode(b"x" * 32).decode())
    return module


def _session(toolkit="github", connected=True):
    account = NS(id="ca_fixture") if connected else None
    item = NS(slug=toolkit, connection=NS(is_active=connected, connected_account=account))
    session = NS(
        session_id="sess_fixture",
        mcp=NS(url="https://backend.composio.dev/tool_router/session/sess_fixture/mcp"),
        toolkits=lambda **kwargs: NS(items=[item] if connected else []),
        authorize=lambda *args, **kwargs: NS(redirect_url="https://connect.composio.dev/link/ln_fixture"),
    )
    return session


def test_user_ids_distinct_and_non_reversible(gateway):
    a = gateway._user_id("alice")
    b = gateway._user_id("bob")
    assert a != b and a == gateway._user_id("alice")
    assert "alice" not in a
    assert len(a) == len("basak_") + 64


@pytest.mark.parametrize("url", [
    "http://backend.composio.dev/mcp",
    "https://evil.example/mcp",
    "https://backend.composio.dev.evil.example/mcp",
    "https://u:p@backend.composio.dev/mcp",
    "https://backend.composio.dev:444/mcp",
    "https://backend.composio.dev/mcp#bad",
])
def test_project_key_never_sent_elsewhere(gateway, url):
    with pytest.raises(gateway.ComposioError):
        gateway.mcp_headers(url)


def test_key_header_stays_server_side(gateway):
    url = "https://backend.composio.dev/tool_router/session/test/mcp"
    assert gateway.mcp_headers(url) == {"x-api-key": "test-project-key-not-real"}


def test_session_create_scoped_to_one_toolkit(gateway, monkeypatch):
    calls = []
    session = _session()
    fake = NS(sessions=NS(create=lambda **kw: (calls.append(kw), session)[1]))
    monkeypatch.setattr(gateway, "_client", lambda: fake)
    result = gateway.create_session("alice", "github")
    assert result == {"session_id": "sess_fixture", "url": session.mcp.url, "toolkit": "github"}
    assert calls[0]["mcp"] is True and calls[0]["toolkits"] == ["github"]
    assert calls[0]["user_id"] == gateway._user_id("alice")
    with pytest.raises(gateway.ComposioError):
        gateway.create_session("alice", "unapproved-app")


def test_link_and_verified_finish(gateway, monkeypatch):
    session = _session()
    monkeypatch.setattr(gateway, "_client", lambda: NS(use=lambda *a, **k: session))
    link = gateway.authorize_session("sess_fixture", "github", "https://basak.example/callback")
    assert link == "https://connect.composio.dev/link/ln_fixture"
    metadata = gateway.finish_session("alice", {
        "session_id": "sess_fixture", "toolkit": "github", "url": session.mcp.url
    })
    assert metadata["label"] == "Composio GitHub"
    assert metadata["allowed_tools"] == []
    assert "test-project-key-not-real" not in str(metadata)


def test_unconnected_session_not_accepted(gateway, monkeypatch):
    session = _session(connected=False)
    monkeypatch.setattr(gateway, "_client", lambda: NS(use=lambda *a, **k: session))
    with pytest.raises(gateway.ComposioError):
        gateway.finish_session("alice", {
            "session_id": "sess_fixture", "toolkit": "github", "url": session.mcp.url
        })


def test_revoke_calls_provider_before_local_delete(gateway, monkeypatch):
    calls = []
    session = _session()
    fake = NS(use=lambda *a, **kw: session,
              connected_accounts=NS(delete=lambda aid: calls.append(aid)))
    monkeypatch.setattr(gateway, "_client", lambda: fake)
    gateway.disconnect("alice", {"metadata": {
        "composio_session_id": "sess_fixture", "composio_toolkit": "github",
        "url": session.mcp.url
    }})
    assert calls == ["ca_fixture"]


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
    return TestClient(app, base_url="https://basak.example"), store, api


def test_browser_bound_connect_and_owner_visibility(api_client, gateway, monkeypatch):
    client, store, api = api_client
    session = _session()
    monkeypatch.setattr(gateway, "create_session",
                        lambda uid, toolkit: {"session_id": session.session_id,
                                               "url": session.mcp.url, "toolkit": toolkit})
    saved = {}
    def redirect(_sid, _toolkit, callback):
        saved["callback"] = callback
        return "https://connect.composio.dev/link/ln_fixture"
    monkeypatch.setattr(gateway, "authorize_session", redirect)
    monkeypatch.setattr(gateway, "finish_session", lambda uid, data: {
        "label": "Composio GitHub", "url": data["url"], "transport": "http",
        "composio_session_id": data["session_id"], "composio_toolkit": "github",
        "allowed_tools": []})
    start = client.get("/api/baglantilar/composio/baslat?toolkit=github",
                       headers={"x-test-user": "alice"}, follow_redirects=False)
    assert start.status_code == 302
    assert start.headers["location"].startswith("https://connect.composio.dev/")
    assert store.list("alice") == []
    callback = urlsplit(saved["callback"])
    cb = client.get(callback.path + "?" + callback.query,
                    headers={"x-test-user": "alice"}, follow_redirects=False)
    assert cb.status_code == 303
    assert len(store.list("alice")) == 1
    assert store.list("bob") == []
    listing = client.get("/api/baglantilar", headers={"x-test-user": "alice"}).json()
    assert "test-project-key-not-real" not in str(listing)
    assert client.get("/api/baglantilar", headers={"x-test-user": "bob"}).json() == {"connections": []}


def test_no_composio_key_keeps_connect_closed(api_client, monkeypatch):
    client, _, _ = api_client
    monkeypatch.delenv("COMPOSIO_API_KEY")
    info = client.get("/api/baglantilar/saglayicilar").json()
    provider = next(p for p in info["providers"] if p["id"] == "composio")
    assert provider["configured"] is False
    start = client.get("/api/baglantilar/composio/baslat?toolkit=github",
                       headers={"x-test-user": "alice"})
    assert start.status_code == 503
