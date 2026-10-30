"""Tenant-owned accounts and encrypted OAuth connections in the existing ledger DB.

Protocol sources: Kimi MCP customization/mcp.html; Google OAuth web-server;
GitHub App user tokens; Notion public connection authorization. Secrets never
appear in public connection records. An unavailable key or database is fatal.
"""
import base64
import hashlib
import json
import os
import secrets
import time
import uuid
import threading

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_SCHEMA_LOCK = threading.Lock()


def _key():
    raw = os.environ.get("BASAK_CONNECTION_KEY", "").strip()
    try:
        key = base64.urlsafe_b64decode(raw)
    except (ValueError, TypeError):
        key = b""
    if len(key) != 32:
        raise RuntimeError("Baglanti sifreleme anahtari yapilandirilmadi")
    return key


def _seal(data, aad):
    nonce = secrets.token_bytes(12)
    body = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(nonce + AESGCM(_key()).encrypt(nonce, body, aad.encode())).decode()


def _open(data, aad):
    try:
        raw = base64.urlsafe_b64decode(data)
        return json.loads(AESGCM(_key()).decrypt(raw[:12], raw[12:], aad.encode()))
    except (ValueError, InvalidTag, UnicodeError, json.JSONDecodeError) as exc:
        raise PermissionError("Baglanti sirri dogrulanamadi") from exc


def _identity(value):
    text = str(value or "").strip()
    if not text or len(text) > 128 or any(ord(c) < 32 for c in text):
        raise ValueError("Gecerli kullanici kimligi gerekli")
    return text


def _digest(value):
    return hashlib.sha256(str(value).encode()).hexdigest()


class ConnectionStore:
    def __init__(self, db=None):
        if db is None:
            from chat.kosu_deposu import _depo
            db = _depo()
        if db is None:
            raise RuntimeError("Kalici hesap deposu kullanilamiyor")
        self._db = db
        # Account/credential data is never cached. Only unchanged table setup
        # is shared by stores using this process's same database backend.
        with _SCHEMA_LOCK:
            if not getattr(db, '_connections_schema_ready', False):
                self._prepare()
                db._connections_schema_ready = True

    def _prepare(self):
        for sql in (
            "CREATE TABLE IF NOT EXISTS basak_connection (id TEXT PRIMARY KEY, user_id TEXT NOT NULL, provider TEXT NOT NULL, label TEXT NOT NULL, status TEXT NOT NULL, scopes TEXT NOT NULL, metadata TEXT NOT NULL, secret TEXT NOT NULL, created_at DOUBLE PRECISION NOT NULL, updated_at DOUBLE PRECISION NOT NULL)",
            "CREATE INDEX IF NOT EXISTS basak_connection_owner ON basak_connection(user_id, provider)",
            "CREATE TABLE IF NOT EXISTS basak_oauth_attempt (id TEXT PRIMARY KEY, provider TEXT NOT NULL, browser_hash TEXT NOT NULL, user_id TEXT NOT NULL, purpose TEXT NOT NULL, secret TEXT NOT NULL, expires_at DOUBLE PRECISION NOT NULL, consumed INTEGER NOT NULL DEFAULT 0)",
            "CREATE TABLE IF NOT EXISTS basak_account (id TEXT PRIMARY KEY, provider TEXT NOT NULL, subject TEXT NOT NULL, name TEXT NOT NULL, email TEXT NOT NULL, created_at DOUBLE PRECISION NOT NULL, UNIQUE(provider, subject))",
            "CREATE TABLE IF NOT EXISTS basak_account_session (id TEXT PRIMARY KEY, user_id TEXT NOT NULL, expires_at DOUBLE PRECISION NOT NULL, revoked INTEGER NOT NULL DEFAULT 0)",
        ):
            self._db._calistir(sql)

    @staticmethod
    def _public(row):
        if row is None:
            return None
        return {key: json.loads(row[key]) if key in ("scopes", "metadata") else row[key]
                for key in ("id", "provider", "label", "status", "scopes", "metadata", "created_at", "updated_at")}

    def list(self, user_id):
        rows = self._db._sorgu("SELECT * FROM basak_connection WHERE user_id = %s ORDER BY created_at", (_identity(user_id),))
        return [self._public(row) for row in rows]

    def get(self, user_id, connection_id):
        rows = self._db._sorgu("SELECT * FROM basak_connection WHERE id = %s AND user_id = %s", (connection_id, _identity(user_id)))
        return self._public(rows[0]) if rows else None

    def save(self, user_id, provider, token, scopes, metadata=None, connection_id=None):
        user_id = _identity(user_id)
        if provider not in ("github", "google", "notion", "mcp"):
            raise ValueError("Desteklenmeyen baglanti saglayicisi")
        if not isinstance(token, dict) or not isinstance(scopes, (list, tuple)):
            raise ValueError("Baglanti tokeni ve yetkileri gecersiz")
        metadata = dict(metadata or {})
        allowed = {"label", "account_name", "account_id", "workspace_id", "repositories", "url", "transport", "allowed_tools", "tools", "command", "args", "image", "client_id", "authorization_server", "token_endpoint", "grant_type", "auth_type", "github_app_id", "installation_id", "repository_ids", "permissions", "installations", "writable_repositories", "composio_session_id", "composio_toolkit", "composio_account_id"}
        metadata = {k: v for k, v in metadata.items() if k in allowed}
        cid = connection_id or uuid.uuid4().hex
        if connection_id and self.get(user_id, cid) is None:
            raise PermissionError("Baglanti bulunamadi")
        secret = _seal(token, "connection:%s:%s:%s" % (user_id, cid, provider))
        now = time.time()
        label = str(metadata.get("label") or provider)[:160]
        if connection_id:
            self._db._calistir("UPDATE basak_connection SET secret=%s, scopes=%s, metadata=%s, label=%s, status='connected', updated_at=%s WHERE id=%s AND user_id=%s",
                               (secret, json.dumps(list(scopes)), json.dumps(metadata), label, now, cid, user_id))
        else:
            self._db._calistir("INSERT INTO basak_connection (id,user_id,provider,label,status,scopes,metadata,secret,created_at,updated_at) VALUES (%s,%s,%s,%s,'connected',%s,%s,%s,%s,%s)",
                               (cid, user_id, provider, label, json.dumps(list(scopes)), json.dumps(metadata), secret, now, now))
        return self.get(user_id, cid)

    def credentials(self, user_id, connection_id):
        user_id = _identity(user_id)
        rows = self._db._sorgu("SELECT * FROM basak_connection WHERE id=%s AND user_id=%s AND status='connected'", (connection_id, user_id))
        if not rows or not rows[0]["secret"]:
            raise PermissionError("Baglanti bulunamadi veya yeniden yetkilendirme gerekli")
        row = rows[0]
        return _open(row["secret"], "connection:%s:%s:%s" % (user_id, connection_id, row["provider"]))

    def mark_reauth(self, user_id, connection_id):
        self._db._calistir("UPDATE basak_connection SET status='reauth_required', updated_at=%s WHERE id=%s AND user_id=%s", (time.time(), connection_id, _identity(user_id)))

    def revoke(self, user_id, connection_id):
        return bool(self._db._calistir("UPDATE basak_connection SET status='revoked', secret='', updated_at=%s WHERE id=%s AND user_id=%s", (time.time(), connection_id, _identity(user_id))))

    def oauth_begin(self, provider, browser, user_id, purpose, return_to="/", data=None):
        if purpose not in ("login", "connect") or (purpose == "connect" and not user_id):
            raise ValueError("OAuth amaci veya oturumu gecersiz")
        if provider not in ("google", "github", "notion", "mcp"):
            raise ValueError("OAuth saglayicisi gecersiz")
        if not return_to.startswith("/") or return_to.startswith("//") or "\\" in return_to or any(ord(c) < 32 for c in return_to):
            raise ValueError("Donus yolu yerel olmali")
        state, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(48)
        sid = _digest(state)
        payload = _seal({"verifier": verifier, "return_to": return_to, "data": data or {}}, "oauth:" + sid)
        self._db._calistir("INSERT INTO basak_oauth_attempt (id,provider,browser_hash,user_id,purpose,secret,expires_at,consumed) VALUES (%s,%s,%s,%s,%s,%s,%s,0)",
                           (sid, provider, _digest(browser), user_id or "", purpose, payload, time.time() + 600))
        return state, verifier

    def oauth_consume(self, state, provider, browser):
        sid = _digest(state)
        rows = self._db._sorgu("SELECT * FROM basak_oauth_attempt WHERE id=%s AND provider=%s AND browser_hash=%s AND consumed=0 AND expires_at>%s", (sid, provider, _digest(browser), time.time()))
        if not rows:
            raise PermissionError("OAuth oturumu gecersiz veya suresi dolmus")
        if self._db._calistir("UPDATE basak_oauth_attempt SET consumed=1 WHERE id=%s AND consumed=0 AND expires_at>%s", (sid, time.time())) != 1:
            raise PermissionError("OAuth oturumu daha once kullanildi")
        row = rows[0]
        return {"user_id": row["user_id"], "purpose": row["purpose"], **_open(row["secret"], "oauth:" + sid)}
