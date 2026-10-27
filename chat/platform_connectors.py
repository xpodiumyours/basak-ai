"""Authenticated provider adapters; requests use fixed provider API origins.

References: GitHub REST pulls/contents/git refs, Google Drive v3/Docs v1/
Sheets v4, and Notion API 2026-03-11. No model-selected host or credential.
"""
import json
import os
import time
from urllib.parse import quote

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
    "github": {"label": "GitHub", "authorize": "https://github.com/login/oauth/authorize", "token": "https://github.com/login/oauth/access_token", "identity": "https://api.github.com/user", "scopes": ["public_repo"], "login_scopes": []},
    "notion": {"label": "Notion", "authorize": "https://api.notion.com/v1/oauth/authorize", "token": "https://api.notion.com/v1/oauth/token", "scopes": [], "login_scopes": []},
}


def provider_config(provider):
    if provider not in PROVIDERS:
        raise ConnectorError("Desteklenmeyen saglayici")
    base = dict(PROVIDERS[provider])
    prefix = "BASAK_" + provider.upper()
    base["client_id"] = os.environ.get(prefix + "_CLIENT_ID", "").strip()
    base["client_secret"] = os.environ.get(prefix + "_CLIENT_SECRET", "").strip()
    base["configured"] = bool(base["client_id"] and base["client_secret"] and os.environ.get("BASAK_PUBLIC_URL", "").strip())
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
        _schema("github_list_repositories", "Lists repositories visible to the connected GitHub user."),
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
        return [{k: v for k, v in t.items() if k != "scopes"} for t in TOOLS.get(connection["provider"], [])
                if self._scope_allowed(connection, t)]

    @staticmethod
    def _scope_allowed(connection, schema):
        scopes = set(connection["scopes"])
        # An OAuth login token with no scope may read public information
        # but MUST NOT unlock repository writes in the tool catalog.
        # OAuth 'repo' implies the public_repo permissions as well.
        if connection["provider"] == "github" and schema["name"] in {
                "github_create_branch", "github_write_file", "github_create_pr",
                "github_dispatch_workflow"}:
            if not ({"public_repo", "repo"} & scopes):
                return False
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
        if token.get("expires_at") and float(token["expires_at"]) <= time.time() + 30:
            try:
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
        if tool == "github_dispatch_workflow" and (self.cost_guard is None or not self.cost_guard(user_id, connection_id, dict(args))):
            raise ConnectorError("Actions icin ucret dogmayacagi dogrulanmadi; is baslatilmadi")
        token = self._token(user_id, connection)
        method, url, params, body = self._operation(connection, tool, dict(args))
        data = self._request(method, url, token, provider=provider, params=params, body=body)
        return {"content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False)}], "structuredContent": data if isinstance(data, dict) else {"items": data}, "isError": False}

    def _operation(self, connection, tool, a):
        provider = connection["provider"]
        params, body = None, None
        if provider == "github":
            root = "https://api.github.com"
            if tool == "github_list_repositories":
                return "GET", root + "/user/repos", {"per_page": 100, "sort": "updated"}, None
            repo = a.pop("repository")
            if repo not in connection["metadata"].get("repositories", []):
                raise ConnectorError("Depo bu baglantiya verilen yetkiler arasinda degil")
            root += "/repos/" + "/".join(quote(x, safe="") for x in repo.split("/"))
            if tool == "github_read_file":
                path = a.pop("path")
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
                return "POST", root + "/git/refs", None, {"ref": "refs/heads/" + a["branch"], "sha": a["sha"]}
            if tool == "github_write_file":
                if a["branch"] in ("main", "master", "preview"):
                    raise ConnectorError("Korunan dala dogrudan yazilamaz")
                path = a.pop("path")
                return "PUT", root + "/contents/" + quote(path, safe="/"), None, a
            if tool == "github_create_pr":
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
