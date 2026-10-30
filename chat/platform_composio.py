"""Composio Sessions v3.1 gateway; no additional Python SDK dependency.

Only authenticated Başak users can obtain hosted links. The project key is
never returned to users or saved in connection metadata. Composio credentials
remain with the provider. Endpoints:
https://docs.composio.dev/reference/api-reference/tool-router
"""
import hashlib
import hmac
import os
import re
from urllib.parse import urlsplit

import httpx

TOOLKITS = {
    "github": "GitHub",
    "gmail": "Gmail",
    "googledrive": "Google Drive",
    "notion": "Notion",
}
API_ORIGIN = "https://backend.composio.dev"
MCP_HOSTS = frozenset(("backend.composio.dev", "app.composio.dev"))
LINK_HOSTS = frozenset(("connect.composio.dev", "app.composio.dev"))


class ComposioError(RuntimeError):
    pass


def configured():
    return bool(os.environ.get("COMPOSIO_API_KEY", "").strip())


def _user_id(user_id):
    """Stable, non-reversible identity in Composio's user namespace."""
    secret = os.environ.get("BASAK_CONNECTION_KEY", "")
    if not secret or not isinstance(user_id, str) or not user_id.strip():
        raise ComposioError("Baglanti kullanici kimligi veya sifreleme anahtari eksik")
    return "basak_" + hmac.new(secret.encode(), user_id.encode(),
                                hashlib.sha256).hexdigest()


def _request(method, path, *, data=None, params=None):
    if not configured():
        raise ComposioError("Composio sunucu anahtari eksik")
    if not isinstance(path, str) or not path.startswith("/api/v3.1/"):
        raise ComposioError("Composio API yolu gecersiz")
    try:
        with httpx.Client(timeout=25, follow_redirects=False, trust_env=False) as client:
            response = client.request(
                method, API_ORIGIN + path,
                headers={"x-api-key": os.environ["COMPOSIO_API_KEY"].strip(),
                         "Accept": "application/json"},
                json=data, params=params)
        if response.status_code == 204:
            return {}
        if response.status_code not in (200, 201):
            raise ComposioError("Composio API istegi basarisiz (HTTP %s)" % response.status_code)
        result = response.json()
        if not isinstance(result, dict):
            raise ValueError()
        return result
    except (httpx.HTTPError, ValueError) as exc:
        raise ComposioError("Composio yaniti alinamadi veya gecersiz") from exc


def _slug(toolkit):
    if toolkit not in TOOLKITS:
        raise ComposioError("Desteklenmeyen Composio uygulamasi")
    return toolkit


def _sid(session_id):
    if not isinstance(session_id, str) or not re.fullmatch(r"trs_[a-zA-Z0-9_-]{6,120}", session_id):
        raise ComposioError("Composio oturum kimligi gecersiz")
    return session_id


def validate_mcp_url(url):
    """Allow only exact documented Composio-owned hosts to receive the key."""
    if not isinstance(url, str):
        raise ComposioError("Composio MCP adresi gecersiz")
    try:
        u = urlsplit(url)
        if (u.scheme != "https" or u.hostname not in MCP_HOSTS
                or u.port not in (None, 443) or u.username or u.password
                or u.fragment or not u.path.startswith("/tool_router/")):
            raise ValueError()
    except ValueError as exc:
        raise ComposioError("Composio MCP adresi dogrulanamadi") from exc
    return url


def mcp_headers(url):
    validate_mcp_url(url)
    if not configured():
        raise ComposioError("Composio sunucu anahtari eksik")
    return {"x-api-key": os.environ["COMPOSIO_API_KEY"].strip()}


def create_session(user_id, toolkit):
    toolkit = _slug(toolkit)
    response = _request("POST", "/api/v3.1/tool_router/session", data={
        "user_id": _user_id(user_id),
        "toolkits": {"enabled": [toolkit]},
        # Never silently enable paid Instant actions.
        "instant": False,
    })
    sid = _sid(response.get("session_id"))
    url = validate_mcp_url((response.get("mcp") or {}).get("url"))
    return {"session_id": sid, "url": url, "toolkit": toolkit}


def authorize_session(session_id, toolkit, callback):
    toolkit, session_id = _slug(toolkit), _sid(session_id)
    u = urlsplit(callback)
    if u.scheme != "https" or not u.hostname or u.fragment:
        raise ComposioError("Guvenli donus adresi gerekli")
    result = _request("POST", "/api/v3.1/tool_router/session/" + session_id + "/link",
                      data={"toolkit": toolkit, "callback_url": callback})
    url = result.get("redirect_url")
    if not isinstance(url, str):
        raise ComposioError("Composio baglanti adresi eksik")
    t = urlsplit(url)
    if (t.scheme != "https" or t.hostname not in LINK_HOSTS or
            t.port not in (None, 443) or t.username or t.password or t.fragment):
        raise ComposioError("Composio baglanti adresi guvenilir degil")
    return url


def _session(user_id, data):
    sid = _sid(data.get("session_id"))
    info = _request("GET", "/api/v3.1/tool_router/session/" + sid)
    config = info.get("config") or {}
    if not isinstance(config, dict) or config.get("user_id") != _user_id(user_id):
        raise ComposioError("Composio oturumu baska kullaniciya ait")
    url = validate_mcp_url((info.get("mcp") or {}).get("url"))
    if url != data.get("url"):
        raise ComposioError("Composio oturum adresi degismis")
    return sid, url


def _connected_account(sid, toolkit, user_id):
    info = _request("GET", "/api/v3.1/tool_router/session/" + _sid(sid) + "/toolkits",
                    params={"is_connected": "true", "toolkits": toolkit, "limit": 20})
    for item in info.get("items", []):
        acc = item.get("connected_account") or {}
        if (item.get("slug") == toolkit and acc.get("status") == "ACTIVE"
                and acc.get("user_id") == _user_id(user_id)
                and isinstance(acc.get("id"), str) and acc.get("id").startswith("ca_")):
            return acc["id"]
    raise ComposioError("Composio hesap izni tamamlanmadi")


def finish_session(user_id, data):
    toolkit = _slug(data.get("toolkit"))
    sid, url = _session(user_id, data)
    _connected_account(sid, toolkit, user_id)
    return {
        "label": "Composio " + TOOLKITS[toolkit],
        "url": url,
        "transport": "http",
        "composio_session_id": sid,
        "composio_toolkit": toolkit,
        "allowed_tools": [],
    }


def disconnect(user_id, connection):
    """Remove provider-side account before revoking the local permission."""
    meta = connection.get("metadata") or {}
    if not meta.get("composio_session_id"):
        return
    toolkit = _slug(meta.get("composio_toolkit"))
    sid, _ = _session(user_id, {"session_id": meta["composio_session_id"],
                                "url": meta.get("url")})
    account_id = _connected_account(sid, toolkit, user_id)
    _request("DELETE", "/api/v3.1/connected_accounts/" + account_id)
