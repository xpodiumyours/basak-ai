"""Account and connection HTTP boundary. External app setup is explicit.

OAuth tokens remain server-side, every attempt is browser/provider bound,
single-use, and scoped to login or one authenticated connection owner.
"""
import asyncio
import base64
import hashlib
import logging
import os
import secrets
import time
from urllib.parse import quote, urlencode, urlsplit

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response

from chat.platform_connections import ConnectionStore
from chat.platform_composio import (ComposioError, TOOLKITS as COMPOSIO_TOOLKITS,
                                   configured as composio_configured)
from chat.platform_connectors import ConnectorError, ConnectorService, PROVIDERS, provider_config
from chat.platform_identity import COOKIE, SESSION_SECONDS, IdentityService, authenticate
from chat.platform_mcp import MCPService, MCPOAuthError, validate_endpoint

logger = logging.getLogger(__name__)

router = APIRouter()
_authenticate = authenticate
_store_factory = ConnectionStore
_transport = None
BROWSER_COOKIE = "basak_oauth_browser"


def configure(authenticate=None, store_factory=None, transport=None):
    global _authenticate, _store_factory, _transport
    if authenticate is not None:
        _authenticate = authenticate
    if store_factory is not None:
        _store_factory = store_factory
    _transport = transport


def _error(message, code=400):
    return JSONResponse({"error": message}, status_code=code, headers={"Cache-Control": "no-store"})


def _public_base():
    base = os.environ.get("BASAK_PUBLIC_URL", "").strip().rstrip("/")
    parsed = urlsplit(base)
    local = parsed.hostname in ("localhost", "127.0.0.1") and not (os.environ.get("BASAK_URETIM") or os.environ.get("VERCEL"))
    if not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/") or (parsed.scheme != "https" and not (local and parsed.scheme == "http")):
        raise RuntimeError("Genel uygulama HTTPS adresi yapilandirilmadi")
    return base


def _origin_ok(request):
    origin = request.headers.get("origin")
    # Non-browser bearer/internal clients have no Origin; cookie CSRF requests do.
    if not origin:
        return request.headers.get("sec-fetch-site") not in ("cross-site",)
    try:
        return origin.rstrip("/") == _public_base()
    except RuntimeError:
        return False


def _owner(request):
    uid = _authenticate(request)
    if not uid:
        raise PermissionError("Hesap girisi gerekli")
    return uid


def _secure(request):
    return request.url.scheme == "https" or bool(os.environ.get("VERCEL") or os.environ.get("BASAK_URETIM"))


@router.get("/api/hesap")
async def account_status(request: Request):
    uid = _authenticate(request)
    if not uid:
        return JSONResponse({"authenticated": False, "user": None}, headers={"Cache-Control": "no-store"})
    try:
        user = IdentityService(_store_factory()).get(uid)
        return JSONResponse({"authenticated": bool(user), "user": user}, headers={"Cache-Control": "no-store"})
    except RuntimeError:
        return _error("Hesap deposu kullanilamiyor", 503)


@router.post("/api/hesap/cikis")
async def account_logout(request: Request):
    from chat.platform_api import _mutation_origin_ok
    private = (request.cookies.get(COOKIE) or '').startswith('p1.')
    if not (_mutation_origin_ok(request) if private else _origin_ok(request)):
        return _error("Istek kaynagi gecersiz", 403)
    try:
        token = request.cookies.get(COOKIE)
        if token:
            IdentityService(_store_factory()).revoke_session(token)
    except RuntimeError:
        return _error("Oturum kapatilamadi", 503)
    response = Response(status_code=204)
    response.delete_cookie(COOKIE, path="/", secure=_secure(request), httponly=True, samesite="lax")
    return response


@router.get("/api/baglantilar/saglayicilar")
async def connection_providers():
    providers = []
    # Existing GitHub/Google OAuth is retained only as an identity sign-in
    # route. All new third-party account connections use Composio.
    for provider, info in PROVIDERS.items():
        if provider not in ("google", "github"):
            continue
        cfg = provider_config(provider)
        providers.append({"id": provider, "label": info["label"], "configured": cfg["configured"], "reason": None if cfg["configured"] else "oauth_not_configured", "login": provider in ("google", "github"), "scopes": info["login_scopes"], "login_only": True, "verification_required": provider == "google"})
    # Two distinct prerequisites: the project key and the dashboard-side
    # callback verifier. Reporting both as one reason hides which one is
    # actually missing, so the panel names the failing one.
    if composio_configured():
        composio_ok = _composio_verifier_ready()
        composio_reason = None if composio_ok else "identity_verifier_not_ready"
    else:
        composio_ok = False
        composio_reason = "composio_api_key_missing"
    providers.append({"id": "composio", "label": "Composio", "configured": composio_ok,
                      "reason": composio_reason,
                      "login": False, "scopes": [], "toolkits": []})
    providers.append({"id": "mcp", "label": "MCP", "configured": True, "reason": None, "login": False, "scopes": []})
    return JSONResponse({"providers": providers}, headers={"Cache-Control": "no-store"})


@router.get("/api/baglantilar")
async def connections(request: Request):
    try:
        uid = _owner(request)
        return JSONResponse({"connections": _store_factory().list(uid)}, headers={"Cache-Control": "no-store"})
    except PermissionError:
        return _error("Hesap girisi gerekli", 401)
    except RuntimeError:
        return _error("Baglanti deposu kullanilamiyor", 503)


@router.delete("/api/baglantilar/{connection_id}")
async def connection_revoke(connection_id: str, request: Request):
    if not _origin_ok(request):
        return _error("Istek kaynagi gecersiz", 403)
    try:
        uid = _owner(request)
        store = _store_factory()
        connection = store.get(uid, connection_id)
        if connection is None:
            return _error("Baglanti bulunamadi", 404)
        if connection["provider"] == "mcp" and connection["metadata"].get("composio_session_id"):
            from chat.platform_composio import disconnect
            await asyncio.to_thread(disconnect, uid, connection)
        if not store.revoke(uid, connection_id):
            return _error("Baglanti bulunamadi", 404)
        return Response(status_code=204, headers={"Cache-Control": "no-store"})
    except PermissionError:
        return _error("Hesap girisi gerekli", 401)
    except ComposioError:
        return _error("Composio yetkisi kaldirilamadi; tekrar deneyin", 502)
    except RuntimeError:
        return _error("Baglanti kaldirilamadi", 503)


@router.patch("/api/baglantilar/{connection_id}")
async def connection_permissions(connection_id: str, request: Request):
    if not _origin_ok(request):
        return _error("Istek kaynagi gecersiz", 403)
    try:
        uid = _owner(request)
        store = _store_factory()
        connection = store.get(uid, connection_id)
        if not connection:
            return _error("Baglanti bulunamadi", 404)
        body = await request.json()
        allowed = body.get("allowed_tools") if isinstance(body, dict) else None
        enabled = body.get("enabled") if isinstance(body, dict) else None
        if connection["provider"] != "mcp":
            return _error("Gecerli MCP arac izinleri gerekli")
        if allowed is not None and (not isinstance(allowed, list)
                                    or any(not isinstance(x, str) for x in allowed)):
            return _error("Gecerli MCP arac izinleri gerekli")
        if allowed is None and enabled is None:
            return _error("Gecerli MCP arac izinleri gerekli")
        if enabled is not None and not isinstance(enabled, bool):
            return _error("Gecerli baglanti durumu gerekli")
        catalog = connection["metadata"].get("tools", [])
        known = {value for tool in catalog for value in (tool.get("name"), tool.get("remote_name"))}
        if allowed is not None and not set(allowed).issubset(known):
            return _error("Izinler kesfedilmis araclarla sinirli olmali")
        metadata = {**connection["metadata"]}
        selected = list(dict.fromkeys(allowed)) if allowed is not None else list(metadata.get("allowed_tools") or [])
        if enabled is False:
            # Closing a connector keeps the chosen tools but grants none: the
            # executor only reads allowed_tools, so an empty list is fail-closed.
            metadata.update({"enabled": False, "disabled_tools": selected, "allowed_tools": []})
        elif enabled is True:
            restored = selected
            saved = metadata.get("disabled_tools")
            if allowed is None and isinstance(saved, list) and saved \
                    and all(isinstance(x, str) and x in known for x in saved):
                restored = list(dict.fromkeys(saved))
            metadata.pop("disabled_tools", None)
            metadata.update({"enabled": True, "allowed_tools": restored})
        elif allowed is not None:
            metadata["allowed_tools"] = selected
        row = store.save(uid, "mcp", store.credentials(uid, connection_id), connection["scopes"], metadata, connection_id)
        return JSONResponse(row, headers={"Cache-Control": "no-store"})
    except PermissionError:
        return _error("Hesap girisi gerekli", 401)
    except (ValueError, TypeError):
        return _error("Gecersiz baglanti istegi")
    except RuntimeError:
        return _error("Baglanti guncellenemedi", 503)


@router.get("/api/baglantilar/composio/katalog")
async def composio_catalog(request: Request, search: str = "", cursor: str = ""):
    """Project-scoped, paginated catalogue for signed-in users."""
    if not composio_configured():
        return _error("Composio projesi yapilandirilmadi", 503)
    try:
        _owner(request)
        from chat.platform_composio import catalog
        data = await asyncio.to_thread(catalog, search, cursor)
        return JSONResponse(data, headers={"Cache-Control": "private, no-store"})
    except PermissionError:
        return _error("Hesap girisi gerekli", 401)
    except ComposioError:
        return _error("Composio uygulama katalogu alinamadi", 502)


def _composio_verifier_ready():
    # Composio callback identity verification must be enabled on the project.
    # A value in Vercel by itself does not configure the Composio dashboard.
    return os.environ.get("BASAK_COMPOSIO_VERIFIER_READY") == "1"


@router.get("/api/baglantilar/composio/baslat")
async def composio_start(request: Request, toolkit: str = "github"):
    """Authorize an app through Composio, not through a custom GitHub App."""
    from chat.platform_composio import _slug, create_session, authorize_session
    try:
        _slug(toolkit)
    except ComposioError:
        return _error("Gecersiz Composio uygulamasi")
    if not composio_configured() or not _composio_verifier_ready():
        return _error("Composio proje anahtari ve OAuth kimlik dogrulamasi gerekli", 503)
    try:
        uid = _owner(request)
        store = _store_factory()
        # Each verified OAuth return is pinned to its own connected_account_id,
        # so an owner may connect several accounts of the same toolkit.
        data = await asyncio.to_thread(create_session, uid, toolkit)
        callback = _public_base() + "/api/baglantilar/composio/dogrula"
        target = await asyncio.to_thread(authorize_session, data["session_id"], toolkit, callback)
        return RedirectResponse(target, status_code=302, headers={
            "Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})
    except PermissionError:
        return _error("Hesap girisi gerekli", 401)
    except ComposioError:
        return _error("Composio baglantisi baslatilamadi", 502)
    except RuntimeError:
        return _error("Baglanti deposu veya donus adresi kullanilamiyor", 503)


@router.get("/api/baglantilar/composio/dogrula")
async def composio_verify(request: Request, session_uri: str = ""):
    """Composio calls this browser endpoint after OAuth consent.

    The caller must have a Başak login. Composio enforces that the account
    created by the original link is owned by that exact signed-in user.
    """
    if not _composio_verifier_ready() or not composio_configured():
        return _error("Composio OAuth kimlik dogrulama ayari eksik", 503)
    try:
        from chat.platform_composio import complete_verified_auth
        uid = _owner(request)
        store = _store_factory()
        meta = await asyncio.to_thread(complete_verified_auth, uid, session_uri)
        for conn in store.list(uid):
            existing = conn.get("metadata") or {}
            if (conn["status"] != "revoked"
                    and existing.get("composio_account_id") == meta.get("composio_account_id")):
                return RedirectResponse("/", status_code=303, headers={
                    "Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})
        row = store.save(uid, "mcp", {}, [], meta)
        # Connecting an app prepares its actions automatically. Actual
        # agent execution still passes the immutable per-call approval gate,
        # and users can narrow the discovered allowlist in Connections.
        try:
            tools = await MCPService(store).discover(uid, row["id"])
            refreshed = store.get(uid, row["id"])
            updated = {**refreshed["metadata"],
                       "allowed_tools": [tool["name"] for tool in tools]}
            store.save(uid, "mcp", store.credentials(uid, row["id"]),
                       refreshed["scopes"], updated, row["id"])
        except (ComposioError, RuntimeError, ValueError, PermissionError) as exc:
            # OAuth is single-use; keep the successfully linked account
            # so the user can retry discovery without repeating consent.
            logger.warning("Composio arac kesfi basarisiz (baglanti korundu): %s",
                           type(exc).__name__)
        return RedirectResponse("/", status_code=303, headers={
            "Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})
    except PermissionError:
        return _error("Bu Composio baglantisi icin hesap girisi gerekli", 401)
    except ComposioError:
        return _error("Composio OAuth kimligi dogrulanamadi", 502)
    except RuntimeError:
        return _error("Baglanti deposu kullanilamiyor", 503)


@router.get("/api/baglantilar/composio/callback")
async def composio_callback(request: Request, state: str = "", error: str = ""):
    """Reject the old state-only callback: it does not prove provider identity."""
    return _error("Eski Composio OAuth donusu guvenlik icin kapatildi", 410)


@router.post("/api/baglantilar/mcp")
async def mcp_create(request: Request):
    if not _origin_ok(request):
        return _error("Istek kaynagi gecersiz", 403)
    try:
        uid = _owner(request)
        body = await request.json()
        if not isinstance(body, dict):
            raise ValueError()
        url = await asyncio.to_thread(validate_endpoint, body.get("url", ""))
        allowed = body.get("allowed_tools", [])
        if not isinstance(allowed, list) or any(not isinstance(x, str) for x in allowed):
            raise ValueError()
        metadata = {"label": str(body.get("label") or "MCP"), "url": url, "transport": "http", "allowed_tools": allowed}
        if body.get("client_id"):
            metadata["client_id"] = str(body["client_id"])
        connection = _store_factory().save(uid, "mcp", {}, [], metadata)
        return JSONResponse(connection, status_code=201, headers={"Cache-Control": "no-store"})
    except PermissionError:
        return _error("Hesap girisi gerekli", 401)
    except (ValueError, TypeError):
        return _error("Gecerli HTTPS MCP adresi ve arac listesi gerekli")
    except RuntimeError:
        return _error("Baglanti deposu veya sifreleme anahtari hazir degil", 503)


@router.get("/api/baglantilar/{connection_id}/oauth/baslat")
async def mcp_oauth_start(connection_id: str, request: Request):
    try:
        from chat.platform_mcp import oauth_start
        uid = _owner(request)
        browser = request.cookies.get(BROWSER_COOKIE) or secrets.token_urlsafe(32)
        callback = _public_base() + "/api/baglantilar/mcp/oauth/callback"
        target = await asyncio.to_thread(oauth_start, _store_factory(), uid, connection_id, browser, callback, transport=_transport)
        response = RedirectResponse(target, status_code=302, headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})
        response.set_cookie(BROWSER_COOKIE, browser, max_age=600, httponly=True, secure=_secure(request), samesite="lax", path="/api/baglantilar")
        return response
    except PermissionError:
        return _error("Hesap girisi veya MCP baglantisi gerekli", 401)
    except (ValueError, MCPOAuthError, httpx.HTTPError):
        return _error("MCP OAuth baslatilamadi; sunucu metadata, PKCE veya istemci kaydi eksik", 502)
    except RuntimeError:
        return _error("OAuth oturum deposu veya anahtarlari hazir degil", 503)


@router.get("/api/baglantilar/mcp/oauth/callback")
async def mcp_oauth_callback(request: Request, state: str = "", code: str = "", error: str = ""):
    try:
        from chat.platform_mcp import oauth_complete
        uid = _owner(request)
        browser = request.cookies.get(BROWSER_COOKIE, "")
        if not state or not browser:
            raise PermissionError()
        store = _store_factory()
        attempt = store.oauth_consume(state, "mcp", browser)
        if attempt["user_id"] != uid:
            raise PermissionError()
        if error or not code:
            return _error("MCP yetkilendirmesi tamamlanmadi")
        await asyncio.to_thread(oauth_complete, store, uid, attempt, code, transport=_transport)
        response = RedirectResponse("/", status_code=303, headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})
        response.delete_cookie(BROWSER_COOKIE, path="/api/baglantilar", secure=_secure(request), httponly=True, samesite="lax")
        return response
    except PermissionError:
        return _error("MCP OAuth oturumu gecersiz veya suresi dolmus", 400)
    except (ValueError, MCPOAuthError, httpx.HTTPError):
        return _error("MCP yetkilendirmesi tamamlanamadi", 502)
    except RuntimeError:
        return _error("MCP OAuth deposu veya anahtarlari hazir degil", 503)


@router.post("/api/baglantilar/{connection_id}/kesfet")
async def connection_discover(connection_id: str, request: Request):
    if not _origin_ok(request):
        return _error("Istek kaynagi gecersiz", 403)
    try:
        uid = _owner(request)
        store = _store_factory()
        connection = store.get(uid, connection_id)
        if not connection:
            return _error("Baglanti bulunamadi", 404)
        if connection["provider"] == "mcp":
            tools = await MCPService(store).discover(uid, connection_id)
        else:
            tools = ConnectorService(store).tools(uid, connection_id)
        return JSONResponse({"tools": tools}, headers={"Cache-Control": "no-store"})
    except PermissionError:
        return _error("Baglanti icin yeniden yetkilendirme gerekli", 401)
    except Exception:
        return _error("Baglanti kesfi basarisiz; yetkilendirme veya sunucu durumu kontrol edilmeli", 502)


@router.get("/api/baglantilar/oauth/{provider}/baslat")
async def oauth_start(provider: str, request: Request, purpose: str = "connect"):
    if purpose == "connect" and provider in ("github", "google", "notion"):
        return _error("Yeni platform baglantilari Composio uzerinden kurulur", 410)
    try:
        cfg = provider_config(provider)
        if not cfg["configured"]:
            return _error("OAuth uygulamasi yapilandirilmadi", 503)
        if purpose == "login" and provider not in ("google", "github"):
            return _error("Bu saglayici hesap girisi icin kullanilamaz")
        uid = _owner(request) if purpose == "connect" else None
        if purpose not in ("login", "connect"):
            return _error("OAuth amaci gecersiz")
        browser = request.cookies.get(BROWSER_COOKIE) or secrets.token_urlsafe(32)
        store = _store_factory()
        state, verifier = store.oauth_begin(provider, browser, uid, purpose)
        callback = _public_base() + "/api/baglantilar/oauth/" + provider + "/callback"
        scopes = cfg["login_scopes"] if purpose == "login" else cfg["scopes"]
        params = {"client_id": cfg["client_id"], "redirect_uri": callback, "response_type": "code", "state": state}
        if scopes:
            params["scope"] = " ".join(scopes)
        if provider in ("google", "github"):
            params.update({"code_challenge": base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode(), "code_challenge_method": "S256"})
        if provider == "google":
            params.update({"access_type": "offline", "prompt": "consent"})
        if provider == "notion":
            params["owner"] = "user"
        response = RedirectResponse(cfg["authorize"] + "?" + urlencode(params), status_code=302, headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})
        response.set_cookie(BROWSER_COOKIE, browser, max_age=600, httponly=True, secure=_secure(request), samesite="lax", path="/api/baglantilar")
        return response
    except PermissionError:
        return _error("Hesap girisi gerekli", 401)
    except (ValueError, ConnectorError):
        return _error("OAuth saglayicisi veya istek gecersiz")
    except RuntimeError:
        return _error("OAuth oturum deposu veya anahtarlari hazir degil", 503)


def _exchange(provider, cfg, code, verifier, callback, purpose="connect"):
    with httpx.Client(timeout=60, follow_redirects=False, trust_env=False, transport=_transport) as client:
        payload = {"grant_type": "authorization_code", "code": code, "redirect_uri": callback}
        if provider == "notion":
            response = client.post(cfg["token"], json=payload, auth=(cfg["client_id"], cfg["client_secret"]))
        else:
            payload.update({"client_id": cfg["client_id"], "client_secret": cfg["client_secret"], "code_verifier": verifier})
            response = client.post(cfg["token"], data=payload, headers={"Accept": "application/json"})
        if response.status_code != 200:
            raise ConnectorError("OAuth kodu degistirilemedi")
        token = response.json()
        if token.get("error") or not token.get("access_token"):
            raise ConnectorError("OAuth yetkilendirmesi tamamlanamadi")
        if token.get("expires_in"):
            token["expires_at"] = time.time() + float(token["expires_in"])
        headers = {"Authorization": "Bearer " + token["access_token"], "Accept": "application/json"}
        if provider == "notion":
            owner = token.get("owner", {}).get("user", {})
            profile = {"id": owner.get("id") or token.get("bot_id"), "name": token.get("workspace_name") or "Notion"}
            metadata = {"workspace_id": token.get("workspace_id", "")}
        else:
            identity = client.get(cfg["identity"], headers=headers)
            if identity.status_code != 200:
                raise ConnectorError("Dis hesap kimligi dogrulanamadi")
            profile = identity.json()
            metadata = {}
        if provider == "google" and not profile.get("sub"):
            raise ConnectorError("Google hesap kimligi eksik")
        if provider == "github":
            if not isinstance(profile.get("id"), int):
                raise ConnectorError("GitHub hesap kimligi eksik")
            if purpose == "connect":
                from chat.platform_github_app import discover_connection
                token, metadata = discover_connection(token, profile, transport=_transport)
        return token, profile, metadata


@router.get("/api/baglantilar/oauth/{provider}/callback")
async def oauth_callback(provider: str, request: Request, state: str = "", code: str = "", error: str = ""):
    # Do not complete an already-issued legacy account-link attempt.
    # Sign-in attempts remain valid to avoid logging people out.
    try:
        cfg = provider_config(provider)
        browser = request.cookies.get(BROWSER_COOKIE, "")
        if not state or not browser:
            raise PermissionError()
        store = _store_factory()
        attempt = store.oauth_consume(state, provider, browser)
        if attempt["purpose"] == "connect" and provider in ("github", "google", "notion"):
            return _error("Eski OAuth baglanti akisi kapatildi", 410)
        if attempt["purpose"] == "connect" and _authenticate(request) != attempt["user_id"]:
            raise PermissionError()
        if error or not code or not cfg["configured"]:
            return _error("Yetkilendirme tamamlanmadi")
        callback = _public_base() + "/api/baglantilar/oauth/" + provider + "/callback"
        token, profile, metadata = await asyncio.to_thread(_exchange, provider, cfg, code, attempt["verifier"], callback, attempt["purpose"])
        identity = IdentityService(store)
        response = RedirectResponse(attempt["return_to"], status_code=303, headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})
        if attempt["purpose"] == "login":
            account = identity.account(provider, str(profile.get("sub") or profile.get("id")), profile.get("name") or profile.get("login"), profile.get("email", ""))
            response.set_cookie(COOKIE, identity.issue_session(account["id"]), max_age=SESSION_SECONDS, httponly=True, secure=_secure(request), samesite="lax", path="/")
        else:
            uid = attempt["user_id"]
            scopes = str(token.get("scope") or "").replace(",", " ").split()
            data_scopes = {s for s in cfg["scopes"] if s.startswith("https://")}
            if provider == "google" and not data_scopes.issubset(set(scopes)):
                return _error("Istenen Google Drive, Docs ve Sheets yetkileri tam verilmedi", 403)
            label = cfg["label"] + " — " + str(profile.get("name") or profile.get("login") or "Hesap")
            store.save(uid, provider, token, scopes, {**metadata, "label": label, "account_id": str(profile.get("sub") or profile.get("id") or "")})
        response.delete_cookie(BROWSER_COOKIE, path="/api/baglantilar", secure=_secure(request), httponly=True, samesite="lax")
        return response
    except PermissionError:
        return _error("OAuth oturumu gecersiz, suresi dolmus veya daha once kullanilmis", 400)
    except (ValueError, ConnectorError, httpx.HTTPError):
        return _error("Platform yetkilendirmesi tamamlanamadi", 502)
    except RuntimeError:
        return _error("OAuth depo veya anahtar yapilandirmasi eksik", 503)
