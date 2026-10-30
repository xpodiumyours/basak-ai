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
    # Every toolkit is project-verified by Composio during session creation.
    # No hard-coded, user-visible list is necessary.
    if not isinstance(toolkit, str) or not re.fullmatch(r"[a-z][a-z0-9_]{1,79}", toolkit):
        raise ComposioError("Gecersiz Composio uygulama kimligi")
    return toolkit


def catalog(search="", cursor="", limit=40):
    """Page through only Composio-managed Connect Link capable integrations.

    Client receives display-only metadata, never auth configuration or keys.
    """
    if not isinstance(search, str) or len(search) > 100:
        raise ComposioError("Uygulama aramasi cok uzun")
    if not isinstance(cursor, str) or len(cursor) > 512:
        raise ComposioError("Uygulama sayfalama imleci gecersiz")
    limit = max(1, min(int(limit), 60))
    params = {"limit": limit, "sort_by": "usage", "include_deprecated": "false"}
    if search.strip():
        params["search"] = search.strip()
    if cursor:
        params["cursor"] = cursor
    result = _request("GET", "/api/v3.1/toolkits", params=params)
    items = result.get("items")
    if not isinstance(items, list):
        raise ComposioError("Composio uygulama katalogu gecersiz")
    available = []
    for raw in items:
        if not isinstance(raw, dict):
            continue
        slug = raw.get("slug")
        try:
            _slug(slug)
        except ComposioError:
            continue
        if (raw.get("no_auth") or raw.get("is_local_toolkit")
                or not raw.get("composio_managed_auth_schemes")):
            continue
        meta = raw.get("meta") or {}
        if not isinstance(meta, dict):
            meta = {}
        logo = meta.get("logo") or ""
        if not isinstance(logo, str):
            logo = ""
        else:
            try:
                parsed = urlsplit(logo)
                if (parsed.scheme != "https" or parsed.hostname != "assets.composio.dev"
                        or parsed.username or parsed.password or parsed.port not in (None, 443)
                        or parsed.query or parsed.fragment):
                    logo = ""
            except ValueError:
                logo = ""
        available.append({"id": slug,
                          "label": str(raw.get("name") or slug)[:90],
                          "description": str(meta.get("description") or "")[:240],
                          "logo": logo[:500]})
    next_cursor = result.get("next_cursor") or ""
    if not isinstance(next_cursor, str) or len(next_cursor) > 512:
        raise ComposioError("Composio katalog sayfalama imleci gecersiz")
    return {"toolkits": available, "next_cursor": next_cursor}


def _account_id(account_id):
    if not isinstance(account_id, str) or not re.fullmatch(r"ca_[a-zA-Z0-9_-]{4,150}", account_id):
        raise ComposioError("Composio hesap kimligi gecersiz")
    return account_id


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


def create_session(user_id, toolkit, connected_account=None):
    toolkit = _slug(toolkit)
    if connected_account is not None:
        _account_id(connected_account)
    config = {
        "user_id": _user_id(user_id),
        "toolkits": {"enabled": [toolkit]},
        # Composio Instant can incur charges if omitted; never opt in.
        "instant": False,
        # A client without interactive MCP elicitation must never silently
        # approve an upstream request.
        "experimental": {"no_elicitation_support_fallback": "deny"},
    }
    if connected_account is not None:
        config["connected_accounts"] = {toolkit: [connected_account]}
    response = _request("POST", "/api/v3.1/tool_router/session", data=config)
    sid = _sid(response.get("session_id"))
    url = validate_mcp_url((response.get("mcp") or {}).get("url"))
    session = {"session_id": sid, "url": url, "toolkit": toolkit}
    if connected_account is not None:
        session["account"] = connected_account
    return session


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
    # Do not execute on a session that could charge the project for Instant.
    # Composio reports this field as false when disabled.
    if config.get("instant") is not False:
        raise ComposioError("Composio ucretli Instant modunun kapali oldugu dogrulanamadi")
    url = validate_mcp_url((info.get("mcp") or {}).get("url"))
    if url != data.get("url"):
        raise ComposioError("Composio oturum adresi degismis")
    enabled = (config.get("toolkits") or {}).get("enabled") or []
    expected = data.get("toolkit")
    if expected and enabled != [expected]:
        raise ComposioError("Composio oturumunun uygulama yetkisi degisti")
    pinned = data.get("account")
    if pinned:
        _account_id(pinned)
        overrides = config.get("connected_accounts") or {}
        ids = overrides.get(expected) if isinstance(overrides, dict) else None
        if isinstance(ids, str):
            ids = [ids]
        if ids != [pinned]:
            raise ComposioError("Composio oturumu beklenen hesaba sabitlenmemis")
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


def complete_verified_auth(user_id, session_uri):
    """Redeem Composio's single-use identity-verification callback.

    The project must route OAuth callbacks to the verifier URL in Composio
    Settings > General. A normal callback with a state token is insufficient
    to prove which person consented at the provider.
    """
    if (not isinstance(session_uri, str) or not 10 <= len(session_uri) <= 2048
            or any(ord(ch) < 33 for ch in session_uri)):
        raise ComposioError("Composio dogrulama oturumu gecersiz")
    result = _request("POST", "/api/v3.1/connected_accounts/complete_auth",
                      data={"session_uri": session_uri, "user_id": _user_id(user_id)})
    toolkit = _slug(result.get("toolkit_slug"))
    account = result.get("connected_account_id")
    if not isinstance(account, str) or not account.startswith("ca_"):
        raise ComposioError("Dogrulanmis Composio hesap kimligi gecersiz")
    # Never use a session or account belonging to a different Başak user.
    detail = _request("GET", "/api/v3.1/connected_accounts/" + account)
    if (detail.get("id") != account
            or detail.get("user_id") != _user_id(user_id)
            or detail.get("status") != "ACTIVE"
            or (detail.get("toolkit") or {}).get("slug") != toolkit):
        raise ComposioError("Composio hesap sahipligi dogrulanamadi")
    session = create_session(user_id, toolkit, connected_account=account)
    session_id, _ = _session(user_id, session)
    if _connected_account(session_id, toolkit, user_id) != account:
        raise ComposioError("Dogrulanan Composio hesabi beklenen oturumda yok")
    return finish_session(user_id, session)


def finish_session(user_id, data):
    toolkit = _slug(data.get("toolkit"))
    sid, url = _session(user_id, data)
    connected_id = _connected_account(sid, toolkit, user_id)
    if data.get("account") and data["account"] != connected_id:
        raise ComposioError("Composio baglantisi baska hesaba yonlendirildi")
    return {
        "label": "Composio " + TOOLKITS.get(toolkit, toolkit),
        "url": url,
        "transport": "http",
        "composio_session_id": sid,
        "composio_toolkit": toolkit,
        "composio_account_id": connected_id,
        "allowed_tools": [],
    }


def _bound_account(sid, toolkit, user_id, meta):
    expected = _account_id(meta.get("composio_account_id"))
    actual = _connected_account(sid, toolkit, user_id)
    if actual != expected:
        raise ComposioError("Composio bagli hesap kimligi degisti")
    details = _request("GET", "/api/v3.1/connected_accounts/" + expected)
    if (details.get("id") != expected or details.get("user_id") != _user_id(user_id)
            or details.get("status") != "ACTIVE"
            or (details.get("toolkit") or {}).get("slug") != toolkit):
        raise ComposioError("Composio hesap sahipligi dogrulanamadi")
    return expected


def disconnect(user_id, connection):
    """Remove provider-side account before revoking the local permission."""
    meta = connection.get("metadata") or {}
    if not meta.get("composio_session_id"):
        return
    toolkit = _slug(meta.get("composio_toolkit"))
    sid, _ = _session(user_id, {"session_id": meta["composio_session_id"],
                                "url": meta.get("url"), "toolkit": toolkit,
                                "account": meta.get("composio_account_id")})
    account_id = _bound_account(sid, toolkit, user_id, meta)
    _request("DELETE", "/api/v3.1/connected_accounts/" + account_id,
             params={"revoke_on_delete": "true"})


def session_tools(user_id, connection):
    """Discover API tool schemas without sending a key to the MCP host."""
    meta = connection["metadata"]
    toolkit = _slug(meta.get("composio_toolkit"))
    sid, _ = _session(user_id, {
        "session_id": meta.get("composio_session_id"),
        "url": meta.get("url"), "toolkit": toolkit,
        "account": meta.get("composio_account_id"),
    })
    _bound_account(sid, toolkit, user_id, meta)
    from chat.platform_mcp import namespace
    result, cursor = [], None
    seen = set()
    while True:
        params = {"limit": 200}
        if cursor:
            params["cursor"] = cursor
        response = _request("GET", "/api/v3.1/tool_router/session/" + sid + "/tools",
                            params=params)
        items = response.get("items")
        if not isinstance(items, list):
            raise ComposioError("Composio arac katalogu gecersiz")
        for raw in items:
            if not isinstance(raw, dict):
                raise ComposioError("Composio arac semasi gecersiz")
            slug = raw.get("slug")
            group = raw.get("toolkit") or {}
            if (not isinstance(slug, str) or not re.fullmatch(r"[A-Z0-9_]{3,150}", slug)
                    or not isinstance(group, dict) or group.get("slug") != toolkit
                    or slug in seen):
                raise ComposioError("Composio arac kapsami gecersiz")
            seen.add(slug)
            properties = raw.get("input_parameters") or {}
            if not isinstance(properties, dict):
                raise ComposioError("Composio arac parametreleri gecersiz")
            fields, required = {}, []
            for name, schema in properties.items():
                if not isinstance(name, str) or not isinstance(schema, dict):
                    raise ComposioError("Composio arac parametresi gecersiz")
                item = {k: v for k, v in schema.items() if k != "required"}
                if schema.get("required") is True:
                    required.append(name)
                fields[name] = item
            result.append({
                "name": namespace(connection["id"], slug),
                "remote_name": slug,
                "description": str(raw.get("description") or raw.get("name") or slug)[:1500],
                "inputSchema": {"type": "object", "properties": fields,
                                "required": required, "additionalProperties": False},
                "annotations": {"readOnlyHint": False, "destructiveHint": False},
            })
            if len(result) > 1000:
                raise ComposioError("Composio arac sayisi guvenlik sinirini asti")
        next_cursor = response.get("next_cursor")
        if not next_cursor:
            return result
        if not isinstance(next_cursor, str) or next_cursor == cursor:
            raise ComposioError("Composio arac sayfalama yaniti gecersiz")
        cursor = next_cursor


def session_execute(user_id, connection, slug, arguments):
    """Use only the fixed Composio REST origin and explicitly pinned account."""
    meta = connection["metadata"]
    toolkit = _slug(meta.get("composio_toolkit"))
    sid, _ = _session(user_id, {
        "session_id": meta.get("composio_session_id"),
        "url": meta.get("url"), "toolkit": toolkit,
        "account": meta.get("composio_account_id"),
    })
    account = _bound_account(sid, toolkit, user_id, meta)
    result = _request("POST", "/api/v3.1/tool_router/session/" + sid + "/execute",
                      data={"tool_slug": slug, "arguments": arguments, "account": account})
    # v3.1 REST documents {data, error, log_id}, without result_type.
    # The SDK can additionally provide result_type. Reject explicit failure
    # in either representation, but do not require an SDK-only field.
    payload = result.get("data")
    outcome = result.get("result_type")
    if (result.get("error") is not None or not isinstance(payload, dict)
            or outcome not in (None, "completed") or result.get("instant_charge")
            or payload.get("isError") is True or payload.get("success") is False):
        return {"isError": True, "content": [{"type": "text",
                "text": "Composio araci basarisiz"}],
                "structuredContent": {"error": "Composio araci basarisiz"}}
    return {"isError": False, "content": [],
            "structuredContent": payload}
