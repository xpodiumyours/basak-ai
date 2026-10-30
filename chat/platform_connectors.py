"""Authenticated provider adapters; requests use fixed provider API origins.

References: GitHub REST pulls/contents/git refs, Google Drive v3/Docs v1/
Sheets v4, and Notion API 2026-03-11. No model-selected host or credential.
"""
import base64
import json
import os
import re
import time
from urllib.parse import quote, urlsplit

import httpx

from chat.platform_connections import ConnectionStore


class ConnectorError(RuntimeError):
    pass


DRIVE_READ = "https://www.googleapis.com/auth/drive.readonly"
DRIVE_WRITE = "https://www.googleapis.com/auth/drive"
DOCS_WRITE = "https://www.googleapis.com/auth/documents"
SHEETS_WRITE = "https://www.googleapis.com/auth/spreadsheets"

PROVIDERS = {
    "google": {"label": "Google Drive / Docs / Sheets", "authorize": "https://accounts.google.com/o/oauth2/v2/auth", "token": "https://oauth2.googleapis.com/token", "identity": "https://openidconnect.googleapis.com/v1/userinfo", "scopes": ["openid", "email", "profile", DRIVE_READ, DOCS_WRITE, SHEETS_WRITE], "login_scopes": ["openid", "email", "profile"]},
    "github": {"label": "GitHub", "authorize": "https://github.com/login/oauth/authorize", "token": "https://github.com/login/oauth/access_token", "identity": "https://api.github.com/user", "scopes": [], "login_scopes": []},
    "notion": {"label": "Notion", "authorize": "https://api.notion.com/v1/oauth/authorize", "token": "https://api.notion.com/v1/oauth/token", "scopes": [], "login_scopes": []},
}


def _oauth_prerequisites_ready():
    """Reject OAuth links that cannot complete a durable, secure login.

    This is only a fail-closed configuration gate; a real provider callback
    and persisted session remain mandatory acceptance evidence.
    """
    raw = os.environ.get("BASAK_PUBLIC_URL", "").strip()
    try:
        url = urlsplit(raw)
        local = (url.hostname in {"localhost", "127.0.0.1"}
                 and not (os.environ.get("VERCEL") or os.environ.get("BASAK_URETIM")))
        valid_url = (bool(url.hostname) and not url.username and not url.password
                     and not url.query and not url.fragment and url.path in {"", "/"}
                     and (url.scheme == "https" or (local and url.scheme == "http")))
        if not valid_url:
            return False
    except ValueError:
        return False

    if len(os.environ.get("BASAK_OTURUM_ANAHTARI", "").encode()) < 32:
        return False
    try:
        key = base64.urlsafe_b64decode(
            os.environ.get("BASAK_CONNECTION_KEY", "").strip())
        if len(key) != 32:
            return False
    except (ValueError, TypeError):
        return False

    # Local injected SQLite is supported by offline tests. Real Vercel/worker
    # environments must use their explicitly chosen persistent PostgreSQL.
    if os.environ.get("VERCEL") or os.environ.get("BASAK_URETIM"):
        from chat.kosu_deposu import _dsn
        try:
            if not _dsn():
                return False
        except RuntimeError:
            return False
    return True


def provider_config(provider):
    if provider not in PROVIDERS:
        raise ConnectorError("Desteklenmeyen saglayici")
    base = dict(PROVIDERS[provider])
    prefix = "BASAK_" + provider.upper()
    base["client_id"] = os.environ.get(prefix + "_CLIENT_ID", "").strip()
    base["client_secret"] = os.environ.get(prefix + "_CLIENT_SECRET", "").strip()
    base["configured"] = bool(
        base["client_id"] and base["client_secret"] and _oauth_prerequisites_ready())
    if provider == "github":
        from chat.platform_github_app import configured
        base["configured"] = base["configured"] and configured()
    return base


def _schema(name, description, properties=None, required=None, write=False, scopes=()):
    return {"name": name, "description": description,
            "inputSchema": {"type": "object", "properties": properties or {}, "required": required or [], "additionalProperties": False},
            "annotations": {"readOnlyHint": not write, "destructiveHint": False}, "scopes": list(scopes)}


S = {"type": "string"}
OBJ = {"type": "object"}
A = {"type": "array"}
TOOLS = {
    "github": [
        _schema("github_list_repositories", "Lists repositories selected for this GitHub App connection; page selects the result page.", {"page": {"type": "integer", "minimum": 1}}),
        _schema("github_get_repository", "Reads repository metadata including default branch and permissions.", {"repository": S}, ["repository"]),
        _schema("github_get_branch", "Reads a repository branch including its current commit SHA and protection status.", {"repository": S, "branch": S}, ["repository", "branch"]),
        _schema("github_read_file", "Reads a repository file or directory at a ref.", {"repository": S, "path": S, "ref": S}, ["repository", "path"]),
        _schema("github_list_prs", "Lists repository pull requests.", {"repository": S, "state": {"type": "string", "enum": ["open", "closed", "all"]}}, ["repository"]),
        _schema("github_get_pr", "Reads pull request details.", {"repository": S, "number": {"type": "integer", "minimum": 1}}, ["repository", "number"]),
        _schema("github_get_checks", "Reads check runs for a commit ref.", {"repository": S, "ref": S}, ["repository", "ref"]),
        _schema("github_list_runs", "Lists Actions workflow runs for a repository branch.", {"repository": S, "branch": S}, ["repository"]),
        _schema("github_get_run", "Reads an Actions workflow run including conclusion.", {"repository": S, "run_id": {"type": "integer", "minimum": 1}}, ["repository", "run_id"]),
        _schema("github_list_artifacts", "Lists artifacts produced by an Actions workflow run.", {"repository": S, "run_id": {"type": "integer", "minimum": 1}}, ["repository", "run_id"]),
        _schema("github_create_branch", "Creates a repository branch from a commit SHA.", {"repository": S, "branch": S, "sha": S}, ["repository", "branch", "sha"], True),
        _schema("github_write_file", "Creates or updates a file on a development branch; content is base64.", {"repository": S, "path": S, "branch": S, "message": S, "content": S, "sha": S}, ["repository", "path", "branch", "message", "content"], True),
        _schema("github_create_pr", "Creates a pull request between repository branches.", {"repository": S, "title": S, "head": S, "base": S, "body": S, "draft": {"type": "boolean"}}, ["repository", "title", "head", "base"], True),
        _schema("github_dispatch_workflow", "Dispatches an existing Actions workflow at a ref.", {"repository": S, "workflow": S, "ref": S, "inputs": OBJ}, ["repository", "workflow", "ref"], True),
    ],
    "google": [
        _schema("drive_search", "Searches the connected user's entire Google Drive using Drive query syntax.", {"query": S, "page_token": S}, ["query"], scopes=[DRIVE_READ]),
        _schema("drive_get_file", "Reads Google Drive file metadata.", {"file_id": S}, ["file_id"], scopes=[DRIVE_READ]),
        _schema("drive_export", "Exports a Google document as text, Markdown, CSV, PDF, or office format; binary is base64.", {"file_id": S, "mime_type": S}, ["file_id", "mime_type"], scopes=[DRIVE_READ]),
        _schema("docs_get", "Reads a Google Docs document.", {"document_id": S}, ["document_id"], scopes=[DOCS_WRITE]),
        _schema("docs_create", "Creates a Google Docs document.", {"title": S}, ["title"], True, [DOCS_WRITE]),
        _schema("docs_update", "Applies Google Docs batchUpdate requests, optionally against a required revision.", {"document_id": S, "requests": A, "revision_id": S}, ["document_id", "requests"], True, [DOCS_WRITE]),
        _schema("sheets_get", "Reads spreadsheet metadata and sheet properties.", {"spreadsheet_id": S}, ["spreadsheet_id"], scopes=[SHEETS_WRITE]),
        _schema("sheets_read", "Reads an A1 range from a Google spreadsheet.", {"spreadsheet_id": S, "range": S}, ["spreadsheet_id", "range"], scopes=[SHEETS_WRITE]),
        _schema("sheets_write", "Writes values to an A1 range and returns the resulting values.", {"spreadsheet_id": S, "range": S, "values": A}, ["spreadsheet_id", "range", "values"], True, [SHEETS_WRITE]),
        _schema("sheets_create", "Creates a Google spreadsheet.", {"title": S}, ["title"], True, [SHEETS_WRITE]),
    ],
    "notion": [
        _schema("notion_search", "Searches Notion pages and data sources shared with this connection.", {"query": S, "start_cursor": S}),
        _schema("notion_get_page", "Reads a Notion page's properties.", {"page_id": S}, ["page_id"]),
        _schema("notion_read_blocks", "Reads child blocks of a Notion page or block.", {"block_id": S, "start_cursor": S}, ["block_id"]),
        _schema("notion_create_page", "Creates a Notion page under an accessible parent.", {"parent": OBJ, "properties": OBJ, "children": A}, ["parent", "properties"], True),
        _schema("notion_update_page", "Updates a Notion page's properties.", {"page_id": S, "properties": OBJ}, ["page_id", "properties"], True),
        _schema("notion_append_blocks", "Appends content blocks to a Notion page.", {"block_id": S, "children": A}, ["block_id", "children"], True),
        _schema("notion_query_database", "Queries a Notion data source using filters and sorts.", {"data_source_id": S, "filter": OBJ, "sorts": A, "start_cursor": S}, ["data_source_id"]),
    ],
}


def _validated_args(schema, args):
    from jsonschema import Draft202012Validator
    try:
        Draft202012Validator(schema["inputSchema"]).validate(args)
    except Exception as exc:
        raise ConnectorError("Arac argumanlari semaya uymuyor") from exc


class ConnectorService:
    def __init__(self, store=None, transport=None, cost_guard=None):
        self.store = store or ConnectionStore()
        self.transport = transport
        self.cost_guard = cost_guard

    def tools(self, user_id, connection_id):
        connection = self.store.get(user_id, connection_id)
        if not connection or connection["status"] != "connected":
            raise PermissionError("Baglanti kullanilamiyor")
        result = [{k: v for k, v in t.items() if k != "scopes"} for t in TOOLS.get(connection["provider"], [])
                  if self._scope_allowed(connection, t)]
        if connection["provider"] == "github":
            import copy
            result = copy.deepcopy(result)
            prefix = self._branch_prefix(connection)
            for tool in result:
                field = {"github_create_branch": "branch", "github_write_file": "branch",
                         "github_create_pr": "head"}.get(tool["name"])
                if field:
                    tool["inputSchema"]["properties"][field].update(
                        {"pattern": "^" + re.escape(prefix) + ".+", "description": "Connection branch prefix: " + prefix})
                if tool["name"] == "github_create_pr":
                    tool["inputSchema"]["properties"]["draft"] = {"type": "boolean", "const": True, "default": True}
        return result

    @staticmethod
    def _scope_allowed(connection, schema):
        scopes = set(connection["scopes"])
        # An OAuth login token with no scope may read public information
        # but MUST NOT unlock repository writes in the tool catalog.
        # OAuth 'repo' implies the public_repo permissions as well.
        if connection["provider"] == "github":
            metadata = connection["metadata"]
            if metadata.get("auth_type") != "github_app_user":
                return False
            allowed = {"github_list_repositories", "github_get_repository", "github_get_branch",
                       "github_read_file", "github_list_prs", "github_get_pr",
                       "github_create_branch", "github_write_file", "github_create_pr"}
            return schema["name"] in allowed
        return all(s in scopes or (s == DRIVE_READ and DRIVE_WRITE in scopes)
                   for s in schema.get("scopes", []))

    def _request(self, method, url, token, *, provider, params=None, body=None):
        headers = {"Authorization": "Bearer " + str(token), "Accept": "application/json"}
        if provider == "github":
            headers.update({"X-GitHub-Api-Version": "2022-11-28", "Accept": "application/vnd.github+json"})
        if provider == "notion":
            headers["Notion-Version"] = "2026-03-11"
        try:
            with httpx.Client(timeout=60, follow_redirects=False, transport=self.transport, trust_env=False) as client:
                response = client.request(method, url, headers=headers, params=params, json=body)
        except httpx.HTTPError as exc:
            raise ConnectorError("Platforma baglanilamadi") from exc
        if response.status_code in (401, 403):
            raise ConnectorError("Platform yetkisi gecersiz veya yetersiz")
        if not 200 <= response.status_code < 300:
            raise ConnectorError("Platform islemi basarisiz (HTTP %s)" % response.status_code)
        if response.status_code == 204:
            return {"accepted": True}
        if "json" in response.headers.get("content-type", ""):
            return response.json()
        import base64
        return {"mime_type": response.headers.get("content-type", "application/octet-stream"), "base64": base64.b64encode(response.content).decode()}

    def _token(self, user_id, connection):
        token = self.store.credentials(user_id, connection["id"])
        if connection["provider"] == "github":
            from chat.platform_github_app import validate_connection
            validate_connection(connection)
            if (token.get("auth_type") != "github_app_user"
                    or not str(token.get("access_token") or "").startswith("ghu_")):
                raise ConnectorError("GitHub icin secili depo uygulama baglantisi gerekli")
        if token.get("expires_at") and float(token["expires_at"]) <= time.time() + 30:
            try:
                if connection["provider"] == "github":
                    from chat.platform_github_app import refresh_connection
                    token, metadata = refresh_connection(connection, token, transport=self.transport)
                    connection = {**connection, "metadata": {**connection["metadata"], **metadata}}
                else:
                    token = refresh_token(connection["provider"], token, transport=self.transport)
                self.store.save(user_id, connection["provider"], token, connection["scopes"], connection["metadata"], connection["id"])
            except Exception as exc:
                self.store.mark_reauth(user_id, connection["id"])
                raise ConnectorError("Baglanti icin yeniden yetkilendirme gerekli") from exc
        if not token.get("access_token"):
            raise ConnectorError("Baglanti icin yeniden yetkilendirme gerekli")
        return token["access_token"]

    def execute(self, user_id, connection_id, tool, args):
        connection = self.store.get(user_id, connection_id)
        if not connection or connection["status"] != "connected":
            raise PermissionError("Baglanti bulunamadi veya etkin degil")
        provider = connection["provider"]
        schema = next((t for t in TOOLS.get(provider, []) if t["name"] == tool), None)
        if schema is None:
            raise ConnectorError("Bu baglantida arac yok")
        if not self._scope_allowed(connection, schema):
            raise ConnectorError("Bu islem icin gerekli yetki verilmedi")
        _validated_args(schema, args)
        if provider == "github" and tool == "github_list_repositories":
            self._token(user_id, connection)
            current = self.store.get(user_id, connection_id)
            metadata = current["metadata"]
            repositories = metadata.get("repositories", [])
            writable = set(metadata.get("writable_repositories", []))
            offset = (args.get("page", 1) - 1) * 100
            data = {"total_count": len(repositories), "repositories": [
                {"full_name": name, "writable": name in writable}
                for name in repositories[offset:offset + 100]]}
            return {"content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False)}],
                    "structuredContent": data, "isError": False}
        if tool == "github_dispatch_workflow" and (self.cost_guard is None or not self.cost_guard(user_id, connection_id, dict(args))):
            raise ConnectorError("Actions icin ucret dogmayacagi dogrulanmadi; is baslatilmadi")
        method, url, params, body = self._operation(connection, tool, dict(args))
        token = self._token(user_id, connection)
        if provider == "github":
            connection = self.store.get(user_id, connection_id)
            method, url, params, body = self._operation(connection, tool, dict(args))
            self._github_preflight(connection, tool, args, token)
        data = self._request(method, url, token, provider=provider, params=params, body=body)
        return {"content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False)}], "structuredContent": data if isinstance(data, dict) else {"items": data}, "isError": False}

    @staticmethod
    def _branch_prefix(connection):
        return "basak/" + connection["id"][:12] + "/"

    @classmethod
    def _own_branch(cls, connection, branch):
        from chat.platform_github_paths import validate_branch
        validate_branch(branch)
        if not branch.startswith(cls._branch_prefix(connection)):
            raise ConnectorError("Dal bu baglantinin gelistirme alani disinda")

    def _github_preflight(self, connection, tool, args, token):
        if tool not in {"github_create_branch", "github_write_file", "github_create_pr"}:
            return
        repo = args["repository"]
        root = "https://api.github.com/repos/" + "/".join(quote(x, safe="") for x in repo.split("/"))
        info = self._request("GET", root, token, provider="github")
        default = info.get("default_branch")
        branch = args.get("head") if tool == "github_create_pr" else args["branch"]
        if not (info.get("permissions") or {}).get("push"):
            raise ConnectorError("Bu depoda kullanicinin yazma yetkisi yok")
        if not default or branch == default:
            raise ConnectorError("Varsayilan dala dogrudan yazilamaz")
        if tool == "github_create_pr" and args["base"] != default:
            raise ConnectorError("Taslak PR varsayilan dala yonelik olmali")
        if tool in {"github_write_file", "github_create_pr"}:
            info = self._request("GET", root + "/branches/" + quote(branch, safe=""), token, provider="github")
            if info.get("protected") is not False:
                raise ConnectorError("Korunan veya koruma durumu bilinmeyen dala yazilamaz")

    def _operation(self, connection, tool, a):
        provider = connection["provider"]
        params, body = None, None
        if provider == "github":
            root = "https://api.github.com"
            from chat.platform_github_paths import validate_repository, validate_file_path, validate_branch
            repo = validate_repository(a.pop("repository"))
            if repo not in connection["metadata"].get("repositories", []):
                raise ConnectorError("Depo bu baglantiya verilen yetkiler arasinda degil")
            root += "/repos/" + "/".join(quote(x, safe="") for x in repo.split("/"))
            if tool == "github_get_repository":
                return "GET", root, None, None
            if tool == "github_get_branch":
                return "GET", root + "/branches/" + quote(validate_branch(a["branch"]), safe=""), None, None
            if tool == "github_read_file":
                path = validate_file_path(a.pop("path"))
                if a.get("ref"):
                    validate_branch(a["ref"])
                return "GET", root + "/contents/" + quote(path, safe="/"), a, None
            if tool == "github_list_prs":
                return "GET", root + "/pulls", {"per_page": 100, **a}, None
            if tool == "github_get_pr":
                return "GET", root + "/pulls/" + str(a["number"]), None, None
            if tool == "github_get_checks":
                return "GET", root + "/commits/" + quote(a["ref"], safe="") + "/check-runs", None, None
            if tool == "github_list_runs":
                return "GET", root + "/actions/runs", {"per_page": 100, **a}, None
            if tool == "github_get_run":
                return "GET", root + "/actions/runs/" + str(a["run_id"]), None, None
            if tool == "github_list_artifacts":
                return "GET", root + "/actions/runs/" + str(a["run_id"]) + "/artifacts", {"per_page": 100}, None
            if tool == "github_create_branch":
                self._own_branch(connection, a["branch"])
                return "POST", root + "/git/refs", None, {"ref": "refs/heads/" + a["branch"], "sha": a["sha"]}
            if tool == "github_write_file":
                self._own_branch(connection, a["branch"])
                path = validate_file_path(a.pop("path"), write=True)
                return "PUT", root + "/contents/" + quote(path, safe="/"), None, a
            if tool == "github_create_pr":
                self._own_branch(connection, a["head"])
                validate_branch(a["base"])
                if a.get("draft") is False:
                    raise ConnectorError("Bu baglanti yalniz taslak PR olusturabilir")
                a["draft"] = True
                return "POST", root + "/pulls", None, a
            if tool == "github_dispatch_workflow":
                workflow = a.pop("workflow")
                return "POST", root + "/actions/workflows/" + quote(workflow, safe="") + "/dispatches", None, a
        elif provider == "google":
            if tool == "drive_search":
                return "GET", "https://www.googleapis.com/drive/v3/files", {"q": a["query"], "pageSize": 100, "fields": "nextPageToken,files(id,name,mimeType,modifiedTime,webViewLink)", **({"pageToken": a["page_token"]} if a.get("page_token") else {})}, None
            if tool == "drive_get_file":
                return "GET", "https://www.googleapis.com/drive/v3/files/" + quote(a["file_id"], safe=""), {"fields": "id,name,mimeType,modifiedTime,webViewLink,version"}, None
            if tool == "drive_export":
                return "GET", "https://www.googleapis.com/drive/v3/files/" + quote(a["file_id"], safe="") + "/export", {"mimeType": a["mime_type"]}, None
            if tool == "docs_get":
                return "GET", "https://docs.googleapis.com/v1/documents/" + quote(a["document_id"], safe=""), None, None
            if tool == "docs_create":
                return "POST", "https://docs.googleapis.com/v1/documents", None, {"title": a["title"]}
            if tool == "docs_update":
                body = {"requests": a["requests"]}
                if a.get("revision_id"):
                    body["writeControl"] = {"requiredRevisionId": a["revision_id"]}
                return "POST", "https://docs.googleapis.com/v1/documents/" + quote(a["document_id"], safe="") + ":batchUpdate", None, body
            if tool == "sheets_create":
                return "POST", "https://sheets.googleapis.com/v4/spreadsheets", None, {"properties": {"title": a["title"]}}
            root = "https://sheets.googleapis.com/v4/spreadsheets/" + quote(a["spreadsheet_id"], safe="")
            if tool == "sheets_get":
                return "GET", root, None, None
            if tool in ("sheets_read", "sheets_write"):
                url = root + "/values/" + quote(a["range"], safe="")
                if tool == "sheets_read":
                    return "GET", url, None, None
                return "PUT", url, {"valueInputOption": "RAW", "includeValuesInResponse": "true"}, {"range": a["range"], "values": a["values"]}
        elif provider == "notion":
            root = "https://api.notion.com/v1"
            if tool == "notion_search":
                return "POST", root + "/search", None, a
            if tool == "notion_get_page":
                return "GET", root + "/pages/" + quote(a["page_id"], safe=""), None, None
            if tool == "notion_read_blocks":
                bid = a.pop("block_id")
                return "GET", root + "/blocks/" + quote(bid, safe="") + "/children", a, None
            if tool == "notion_create_page":
                return "POST", root + "/pages", None, a
            if tool == "notion_update_page":
                pid = a.pop("page_id")
                return "PATCH", root + "/pages/" + quote(pid, safe=""), None, a
            if tool == "notion_append_blocks":
                bid = a.pop("block_id")
                return "PATCH", root + "/blocks/" + quote(bid, safe="") + "/children", None, a
            if tool == "notion_query_database":
                sid = a.pop("data_source_id")
                return "POST", root + "/data_sources/" + quote(sid, safe="") + "/query", None, a
        raise ConnectorError("Desteklenmeyen islem")


def refresh_token(provider, token, transport=None):
    cfg = provider_config(provider)
    if not cfg["client_id"] or not cfg["client_secret"] or not token.get("refresh_token"):
        raise ConnectorError("Yenileme yetkisi yapilandirilmadi")
    payload = {"grant_type": "refresh_token", "refresh_token": token["refresh_token"], "client_id": cfg["client_id"], "client_secret": cfg["client_secret"]}
    with httpx.Client(timeout=60, follow_redirects=False, transport=transport, trust_env=False) as client:
        if provider == "notion":
            response = client.post(cfg["token"], json={"grant_type": "refresh_token", "refresh_token": token["refresh_token"]}, auth=(cfg["client_id"], cfg["client_secret"]))
        else:
            response = client.post(cfg["token"], data=payload, headers={"Accept": "application/json"})
    if response.status_code != 200:
        raise ConnectorError("Baglanti yenilenemedi")
    new = response.json()
    if not new.get("access_token") or new.get("error"):
        raise ConnectorError("Baglanti yenilenemedi")
    merged = {**token, **new}
    if new.get("expires_in"):
        merged["expires_at"] = time.time() + float(new["expires_in"])
    return merged


def list_tools(user_id, connection_id):
    store = ConnectionStore()
    connection = store.get(user_id, connection_id)
    if not connection:
        raise PermissionError("Baglanti bulunamadi")
    if connection["provider"] == "mcp":
        from chat.platform_mcp import MCPService, run_sync
        return run_sync(MCPService(store).discover(user_id, connection_id))
    return ConnectorService(store).tools(user_id, connection_id)


def tool_metadata(user_id, connection_id, tool):
    store = ConnectionStore()
    connection = store.get(user_id, connection_id)
    if not connection:
        raise PermissionError("Baglanti bulunamadi")
    catalog = connection["metadata"].get("tools", []) if connection["provider"] == "mcp" else TOOLS.get(connection["provider"], [])
    schema = next((t for t in catalog if t["name"] == tool), None)
    if schema is None:
        raise PermissionError("Arac baglanti katalogunda yok")
    hints = schema.get("annotations") or {}
    # Remote MCP annotations are advisory; unknown tools are treated as writes.
    return {"read_only": hints.get("readOnlyHint") is True,
            "side_effect": hints.get("readOnlyHint") is not True,
            "requires_approval": hints.get("destructiveHint") is True,
            "cost_gate": tool == "github_dispatch_workflow",
            "connection_id": connection_id, "provider": connection["provider"]}


def execute(user_id, connection_id, tool, args):
    store = ConnectionStore()
    connection = store.get(user_id, connection_id)
    if not connection:
        raise PermissionError("Baglanti bulunamadi")
    if connection["provider"] == "mcp":
        from chat.platform_mcp import MCPService
        return MCPService(store).execute_sync(user_id, connection_id, tool, args)
    return ConnectorService(store).execute(user_id, connection_id, tool, args)


def observe_uncertain_action(user_id, action):
    """Read the original target; an uncertain mutation is never executed again."""
    import base64
    arguments = action.get('arguments') or {}
    if action.get('tool') != 'baglanti_cagir':
        raise ConnectorError('Bu islem icin bagimsiz saglayici dogrulamasi desteklenmiyor; sonuc belirsiz kalir')
    connection = str(arguments.get('baglanti_id') or '')
    operation = arguments.get('arac')
    original = arguments.get('argumanlar') or {}
    expected_provider = {'github_write_file': 'github', 'sheets_write': 'google'}.get(operation)
    if expected_provider is None:
        raise ConnectorError('Bu islem icin bagimsiz saglayici dogrulamasi desteklenmiyor; sonuc belirsiz kalir')
    if tool_metadata(user_id, connection, operation).get('provider') != expected_provider:
        raise ConnectorError('Dogrulama yalniz bu islemin yerel saglayici baglantisiyla yapilabilir')
    if operation == 'github_write_file':
        observation_tool = 'github_read_file'
        target = {'repository': original['repository'], 'path': original['path'], 'ref': original['branch']}
        response = execute(user_id, connection, observation_tool, target)
        observed = response.get('structuredContent') or {}
        if response.get('isError') or observed.get('encoding') != 'base64':
            raise ConnectorError('Saglayici dosya icerigini dogrulanabilir bicimde dondurmedi')
        actual = base64.b64decode(''.join(str(observed.get('content') or '').split()), validate=True)
        expected = base64.b64decode(original['content'], validate=True)
        matches = actual == expected
    elif operation == 'sheets_write':
        observation_tool = 'sheets_read'
        target = {'spreadsheet_id': original['spreadsheet_id'], 'range': original['range']}
        response = execute(user_id, connection, observation_tool, target)
        observed = response.get('structuredContent') or {}
        matches = not response.get('isError') and observed.get('values') == original['values']
    else:
        raise ConnectorError('Bu islem icin bagimsiz saglayici dogrulamasi desteklenmiyor; sonuc belirsiz kalir')
    if not matches:
        raise ConnectorError('Saglayicidan okunan durum istenen degisiklikle eslesmiyor; sonuc belirsiz kalir')
    return {'observation_tool': observation_tool, 'target': target, 'response': response,
            'result': {'raw': {'result': response}, 'net': json.dumps(response, ensure_ascii=False)}}
