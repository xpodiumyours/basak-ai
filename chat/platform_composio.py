"""Composio Sessions gateway for separately authenticated Başak users.

The project key is used only on the server, never returned to clients or
persisted in the connection ledger. Composio OAuth credentials remain with
Composio; the local store holds only a session pointer and tool permissions.

Reference: https://docs.composio.dev/docs/sessions-via-mcp
"""
import hashlib
import hmac
import os
from urllib.parse import urlsplit

# Explicit allowlist; do not expose every Composio toolkit to an unreviewed agent.
TOOLKITS = {
    "github": "GitHub",
    "gmail": "Gmail",
    "googledrive": "Google Drive",
    "notion": "Notion",
}
COMPOSIO_ORIGIN = "https://backend.composio.dev"
CONNECT_HOST = "connect.composio.dev"


class ComposioError(RuntimeError):
    pass


def configured():
    return bool(os.environ.get("COMPOSIO_API_KEY", "").strip())


def _client():
    key = os.environ.get("COMPOSIO_API_KEY", "").strip()
    if not key:
        raise ComposioError("Composio sunucu anahtari eksik")
    from composio import Composio
    return Composio(api_key=key)


def _user_id(user_id):
    """Stable, non-reversible, per-tenant Composio identity."""
    secret = os.environ.get("BASAK_CONNECTION_KEY", "")
    if not secret:
        raise ComposioError("Baglanti kimlik anahtari eksik")
    if not isinstance(user_id, str) or not user_id.strip():
        raise ComposioError("Hesap kimligi eksik")
    return "basak_" + hmac.new(
        secret.encode("utf-8"), user_id.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def validate_mcp_url(url):
    """Only Composio's documented API origin may receive the project key."""
    try:
        u = urlsplit(url)
        if (u.scheme != "https" or u.netloc != "backend.composio.dev"
                or u.username or u.password or u.fragment
                or not u.path.startswith("/")):
            raise ValueError()
    except (TypeError, ValueError) as exc:
        raise ComposioError("Composio MCP adresi dogrulanamadi") from exc
    return url


def mcp_headers(url):
    validate_mcp_url(url)
    if not configured():
        raise ComposioError("Composio sunucu anahtari eksik")
    return {"x-api-key": os.environ["COMPOSIO_API_KEY"].strip()}


def _slug(toolkit):
    if toolkit not in TOOLKITS:
        raise ComposioError("Desteklenmeyen Composio uygulamasi")
    return toolkit


def create_session(user_id, toolkit):
    toolkit = _slug(toolkit)
    session = _client().sessions.create(
        user_id=_user_id(user_id), toolkits=[toolkit], mcp=True,
    )
    url = validate_mcp_url(session.mcp.url)
    sid = str(session.session_id)
    if not sid:
        raise ComposioError("Composio oturum kimligi eksik")
    # No API key or provider token enters this return value.
    return {"session_id": sid, "url": url, "toolkit": toolkit}


def authorize_session(session_id, toolkit, callback):
    _slug(toolkit)
    u = urlsplit(callback)
    if u.scheme != "https" or not u.hostname or u.fragment:
        raise ComposioError("Guvenli donus adresi gerekli")
    session = _client().use(session_id, mcp=True)
    validate_mcp_url(session.mcp.url)
    request = session.authorize(toolkit, callback_url=callback)
    url = str(request.redirect_url)
    target = urlsplit(url)
    if target.scheme != "https" or target.netloc != CONNECT_HOST:
        raise ComposioError("Composio yetkilendirme adresi guvenilir degil")
    return url


def _connected_account(session, toolkit):
    listing = session.toolkits(is_connected=True)
    for item in listing.items:
        conn = getattr(item, "connection", None)
        account = getattr(conn, "connected_account", None)
        if (getattr(item, "slug", None) == toolkit
                and getattr(conn, "is_active", False)
                and getattr(account, "id", None)):
            return str(account.id)
    raise ComposioError("Composio uygulama izni tamamlanmadi")


def finish_session(user_id, data):
    """Recheck Composio directly before creating an owned local connection."""
    toolkit = _slug(data.get("toolkit"))
    session_id = data.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        raise ComposioError("Composio oturum kimligi gecersiz")
    session = _client().use(session_id, mcp=True)
    url = validate_mcp_url(session.mcp.url)
    if url != data.get("url"):
        raise ComposioError("Composio oturum adresi degismis")
    # The session was created for a HMAC-derived user identifier and its ID
    # is carried only in a browser-bound, single-use, encrypted OAuth state.
    _connected_account(session, toolkit)
    return {
        "label": "Composio " + TOOLKITS[toolkit],
        "url": url,
        "transport": "http",
        "composio_session_id": session_id,
        "composio_toolkit": toolkit,
        "allowed_tools": [],
    }


def disconnect(user_id, connection):
    """Revoke the provider token at Composio before local access removal."""
    metadata = connection.get("metadata") or {}
    sid = metadata.get("composio_session_id")
    toolkit = metadata.get("composio_toolkit")
    if not sid:
        return
    _slug(toolkit)
    session = _client().use(sid, mcp=True)
    validate_mcp_url(session.mcp.url)
    if session.mcp.url != metadata.get("url"):
        raise ComposioError("Composio oturum adresi degismis")
    account_id = _connected_account(session, toolkit)
    _client().connected_accounts.delete(account_id)
