"""Real MCP client with owned connections and preserved structured results.

Kimi MCP reference: https://www.kimi.com/code/docs/en/kimi-code-cli/customization/mcp.html
SDK: https://github.com/modelcontextprotocol/python-sdk
stdio is supplied by an isolated worker transport, never launched on the API host.
"""
import asyncio
import copy
import hashlib
import ipaddress
import re
import socket
import time
from contextlib import asynccontextmanager
from urllib.parse import urlencode, urlsplit

import httpx

from chat.platform_connections import ConnectionStore


def validate_endpoint(url):
    try:
        parsed = urlsplit(str(url))
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.port not in (None, 443):
            raise ValueError("MCP adresi genel HTTPS kaynagi olmali")
        addresses = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(row[4][0]).is_global for row in addresses):
            raise ValueError("MCP adresi genel HTTPS kaynagi olmali")
    except (ValueError, socket.gaierror) as exc:
        raise ValueError("MCP adresi genel HTTPS kaynagi olmali") from exc
    return str(url)


def namespace(connection_id, tool_name):
    server = re.sub(r"[^A-Za-z0-9_]", "_", str(connection_id))[:32]
    name = re.sub(r"[^A-Za-z0-9_]", "_", str(tool_name))[:24]
    digest = hashlib.sha256(str(tool_name).encode()).hexdigest()[:8]
    return "mcp__%s__%s_%s" % (server, name, digest)


def normalize_result(result):
    if hasattr(result, "model_dump"):
        result = result.model_dump(mode="json", by_alias=True, exclude_none=True)
    if not isinstance(result, dict):
        raise ValueError("MCP sonuc bicimi gecersiz")
    # Do not substitute text summaries for structuredContent or embedded media.
    return copy.deepcopy(result)


def run_sync(awaitable):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable)
    awaitable.close()
    raise RuntimeError("Aktif async dongude MCP islemi await edilmeli")


class MCPOAuthError(RuntimeError):
    pass


def _oauth_request(client, method, url, **kwargs):
    validate_endpoint(url)
    response = client.request(method, url, **kwargs)
    if not 200 <= response.status_code < 300:
        raise MCPOAuthError("MCP OAuth sunucusu islemi reddetti")
    try:
        result = response.json()
    except ValueError as exc:
        raise MCPOAuthError("MCP OAuth yaniti gecersiz") from exc
    if not isinstance(result, dict):
        raise MCPOAuthError("MCP OAuth yaniti gecersiz")
    return result


def oauth_start(store, user_id, connection_id, browser, callback, *, transport=None):
    """RFC9728 resource metadata + RFC8414 authorization discovery, DCR, PKCE.

    Only public HTTPS endpoints are accepted. Resource identity and all token
    endpoint/client settings are encrypted into a browser-bound single-use state.
    """
    connection = store.get(user_id, connection_id)
    if not connection or connection["provider"] != "mcp" or connection["status"] == "revoked":
        raise PermissionError("MCP baglantisi bulunamadi")
    resource = validate_endpoint(connection["metadata"]["url"])
    parsed = urlsplit(resource)
    origin = parsed.scheme + "://" + parsed.netloc
    metadata_url = origin + "/.well-known/oauth-protected-resource" + parsed.path.rstrip("/")
    with httpx.Client(timeout=60, follow_redirects=False, trust_env=False, transport=transport) as client:
        try:
            protected = _oauth_request(client, "GET", metadata_url)
        except MCPOAuthError:
            protected = _oauth_request(client, "GET", origin + "/.well-known/oauth-protected-resource")
        configured_resource = str(protected.get("resource") or "").rstrip("/")
        if not configured_resource or not (resource.rstrip("/") == configured_resource or resource.startswith(configured_resource + "/")):
            raise MCPOAuthError("MCP OAuth kaynak kimligi eslesmiyor")
        servers = protected.get("authorization_servers") or []
        if not servers or not isinstance(servers[0], str):
            raise MCPOAuthError("MCP yetkilendirme sunucusu bildirilmedi")
        issuer = validate_endpoint(servers[0]).rstrip("/")
        auth_origin = urlsplit(issuer)
        metadata = _oauth_request(client, "GET", auth_origin.scheme + "://" + auth_origin.netloc + "/.well-known/oauth-authorization-server" + auth_origin.path.rstrip("/"))
        if str(metadata.get("issuer") or "").rstrip("/") != issuer:
            raise MCPOAuthError("MCP yetkilendirme sunucusu kimligi eslesmiyor")
        authorize = validate_endpoint(metadata.get("authorization_endpoint", ""))
        token_endpoint = validate_endpoint(metadata.get("token_endpoint", ""))
        if "S256" not in metadata.get("code_challenge_methods_supported", []):
            raise MCPOAuthError("MCP sunucusu PKCE S256 desteklemiyor")
        client_info = {"client_id": connection["metadata"].get("client_id"), "token_endpoint_auth_method": "none"}
        if not client_info["client_id"]:
            registration = metadata.get("registration_endpoint")
            if not registration:
                raise MCPOAuthError("MCP sunucusunda onceden kayitli OAuth istemci kimligi gerekli")
            client_info = _oauth_request(client, "POST", registration, json={
                "client_name": "Basak", "redirect_uris": [callback],
                "grant_types": ["authorization_code", "refresh_token"],
                "response_types": ["code"], "token_endpoint_auth_method": "none"})
            if not client_info.get("client_id"):
                raise MCPOAuthError("MCP istemci kaydi tamamlanamadi")
        scopes = protected.get("scopes_supported", [])
        if not isinstance(scopes, list) or any(not isinstance(s, str) for s in scopes):
            raise MCPOAuthError("MCP yetki kapsam listesi gecersiz")
        state, verifier = store.oauth_begin("mcp", browser, user_id, "connect", data={
            "connection_id": connection_id, "resource": resource,
            "token_endpoint": token_endpoint, "client": client_info,
            "redirect_uri": callback, "scopes": scopes,
        })
    challenge = __import__("base64").urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return authorize + "?" + urlencode({"response_type": "code", "client_id": client_info["client_id"],
        "redirect_uri": callback, "scope": " ".join(scopes), "state": state,
        "code_challenge": challenge, "code_challenge_method": "S256", "resource": resource})


def oauth_complete(store, user_id, attempt, code, *, transport=None):
    data = attempt.get("data", {})
    cid = data.get("connection_id")
    connection = store.get(user_id, cid)
    if not connection or connection["provider"] != "mcp" or connection["metadata"].get("url") != data.get("resource"):
        raise PermissionError("MCP baglantisi veya OAuth kaynak kimligi degisti")
    info = data["client"]
    payload = {"grant_type": "authorization_code", "code": code,
               "code_verifier": attempt["verifier"], "redirect_uri": data["redirect_uri"],
               "client_id": info["client_id"], "resource": data["resource"]}
    auth = None
    method = info.get("token_endpoint_auth_method", "none")
    if method == "client_secret_basic":
        auth = (info["client_id"], info["client_secret"])
    elif method == "client_secret_post":
        payload["client_secret"] = info["client_secret"]
    elif method != "none":
        raise MCPOAuthError("MCP istemci kimlik dogrulama yontemi desteklenmiyor")
    with httpx.Client(timeout=60, follow_redirects=False, trust_env=False, transport=transport) as client:
        token = _oauth_request(client, "POST", data["token_endpoint"], data=payload, auth=auth)
    if not token.get("access_token") or token.get("error"):
        raise MCPOAuthError("MCP erisim tokeni alinamadi")
    if str(token.get("token_type", "Bearer")).lower() != "bearer":
        raise MCPOAuthError("MCP token turu desteklenmiyor")
    token.update({"oauth_client": info, "token_endpoint": data["token_endpoint"], "resource": data["resource"]})
    if token.get("expires_in"):
        token["expires_at"] = time.time() + float(token["expires_in"])
    scopes = str(token.get("scope") or " ".join(data["scopes"])).split()
    return store.save(user_id, "mcp", token, scopes, connection["metadata"], cid)


class MCPService:
    def __init__(self, store=None, *, session_factory=None, isolated_stdio_factory=None):
        self.store = store or ConnectionStore()
        self.session_factory = session_factory
        self.isolated_stdio_factory = isolated_stdio_factory

    def _owned(self, user_id, connection_id):
        connection = self.store.get(user_id, connection_id)
        if not connection or connection["provider"] != "mcp" or connection["status"] != "connected":
            raise PermissionError("MCP baglantisi kullanilamiyor")
        return connection

    @asynccontextmanager
    async def _session(self, user_id, connection):
        if self.session_factory:
            async with self.session_factory(user_id, connection) as session:
                yield session
            return
        from mcp import ClientSession
        metadata = connection["metadata"]
        if metadata.get("transport") == "stdio":
            if self.isolated_stdio_factory is None:
                raise RuntimeError("stdio MCP icin izole bulut iscisi gerekli")
            async with self.isolated_stdio_factory(user_id, connection) as streams:
                async with ClientSession(*streams[:2]) as session:
                    await session.initialize()
                    yield session
            return
        from mcp.client.streamable_http import streamable_http_client
        url = validate_endpoint(metadata["url"])
        credentials = self.store.credentials(user_id, connection["id"])
        if credentials.get("expires_at") and float(credentials["expires_at"]) <= time.time() + 30:
            credentials = await asyncio.to_thread(self._refresh, user_id, connection, credentials)
        # Composio sessions use the same-origin v3.1 REST adapter in
        # discover/execute below. Never send a project key to an MCP URL.
        if metadata.get("composio_session_id"):
            raise PermissionError("Composio baglantisi dogrudan REST API ile calisir")
        headers = {}
        if credentials.get("access_token"):
            headers["Authorization"] = "Bearer " + credentials["access_token"]

        async def guard(request):
            validate_endpoint(str(request.url))
            source, target = urlsplit(url), urlsplit(str(request.url))
            if target.scheme != source.scheme or target.netloc != source.netloc:
                raise PermissionError("MCP kaynagi degistirilemez")

        async with httpx.AsyncClient(headers=headers, follow_redirects=False, timeout=60,
                                     trust_env=False, event_hooks={"request": [guard]}) as client:
            async with streamable_http_client(url, http_client=client) as streams:
                async with ClientSession(streams[0], streams[1]) as session:
                    await session.initialize()
                    yield session

    def _refresh(self, user_id, connection, token):
        try:
            if not token.get("refresh_token") or token.get("resource") != connection["metadata"].get("url"):
                raise MCPOAuthError("MCP token yenileme gerekli")
            info = token["oauth_client"]
            payload = {"grant_type": "refresh_token", "refresh_token": token["refresh_token"],
                       "client_id": info["client_id"], "resource": token["resource"]}
            auth = None
            if info.get("token_endpoint_auth_method") == "client_secret_basic":
                auth = (info["client_id"], info["client_secret"])
            elif info.get("token_endpoint_auth_method") == "client_secret_post":
                payload["client_secret"] = info["client_secret"]
            with httpx.Client(timeout=60, follow_redirects=False, trust_env=False) as client:
                new = _oauth_request(client, "POST", token["token_endpoint"], data=payload, auth=auth)
            if not new.get("access_token") or new.get("error"):
                raise MCPOAuthError("MCP token yenilenemedi")
            token = {**token, **new}
            if new.get("expires_in"):
                token["expires_at"] = time.time() + float(new["expires_in"])
            self.store.save(user_id, "mcp", token, connection["scopes"], connection["metadata"], connection["id"])
            return token
        except Exception as exc:
            self.store.mark_reauth(user_id, connection["id"])
            raise PermissionError("MCP icin yeniden yetkilendirme gerekli") from exc

    async def discover(self, user_id, connection_id):
        connection = self._owned(user_id, connection_id)
        if connection["metadata"].get("composio_session_id"):
            from chat.platform_composio import session_tools
            tools = await asyncio.to_thread(session_tools, user_id, connection)
            metadata = {**connection["metadata"], "tools": tools}
            secret = self.store.credentials(user_id, connection_id)
            self.store.save(user_id, "mcp", secret, connection["scopes"], metadata, connection_id)
            return tools
        tools, cursor = [], None
        async with self._session(user_id, connection) as session:
            while True:
                result = await session.list_tools(cursor=cursor)
                for tool in result.tools:
                    raw = tool.model_dump(mode="json", by_alias=True, exclude_none=True)
                    raw["remote_name"] = raw["name"]
                    raw["name"] = namespace(connection_id, raw["name"])
                    tools.append(raw)
                cursor = getattr(result, "nextCursor", None)
                if not cursor:
                    break
        metadata = {**connection["metadata"], "tools": tools}
        secret = self.store.credentials(user_id, connection_id)
        self.store.save(user_id, "mcp", secret, connection["scopes"], metadata, connection_id)
        return tools

    async def execute(self, user_id, connection_id, tool_name, arguments):
        connection = self._owned(user_id, connection_id)
        tools = connection["metadata"].get("tools") or await self.discover(user_id, connection_id)
        schema = next((t for t in tools if t["name"] == tool_name), None)
        if schema is None:
            raise PermissionError("MCP araci kesfedilen katalogda yok")
        allowed = connection["metadata"].get("allowed_tools", [])
        if schema["remote_name"] not in allowed and tool_name not in allowed:
            raise PermissionError("MCP araci icin yetki verilmedi")
        from jsonschema import Draft202012Validator
        try:
            Draft202012Validator(schema["inputSchema"]).validate(arguments)
        except Exception as exc:
            raise ValueError("MCP argumanlari semaya uymuyor") from exc
        if connection["metadata"].get("composio_session_id"):
            from chat.platform_composio import session_execute
            return await asyncio.to_thread(session_execute, user_id, connection,
                                           schema["remote_name"], arguments)
        async with self._session(user_id, connection) as session:
            return normalize_result(await session.call_tool(schema["remote_name"], arguments))

    def execute_sync(self, user_id, connection_id, tool_name, arguments):
        return run_sync(self.execute(user_id, connection_id, tool_name, arguments))
