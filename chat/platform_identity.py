"""Durable platform identities and revocable signed account sessions.

External subjects, not emails or display names, identify accounts. Legacy
anonymous/browser identities are deliberately not promoted to platform users.
"""
import base64
import hashlib
import hmac
import os
import secrets
import time
import uuid

from chat.platform_connections import ConnectionStore

COOKIE = "basak_platform_session"
SESSION_SECONDS = 7 * 24 * 3600


def _session_key():
    raw = os.environ.get("BASAK_OTURUM_ANAHTARI", "").encode()
    if len(raw) < 32:
        raise RuntimeError("Kalici oturum anahtari yapilandirilmadi")
    return hashlib.sha256(b"basak-platform-session-v1\0" + raw).digest()


def _signature(value):
    return base64.urlsafe_b64encode(hmac.digest(_session_key(), value.encode(), "sha256")).rstrip(b"=").decode()


class IdentityService:
    def __init__(self, store=None):
        self.store = store or ConnectionStore()

    def account(self, provider, subject, name, email=""):
        if provider not in ("github", "google", "neon") or not str(subject or "").strip():
            raise ValueError("Dogrulanmis dis hesap kimligi gerekli")
        uid = "u" + uuid.uuid4().hex[:30]
        self.store._db._calistir("INSERT INTO basak_account (id,provider,subject,name,email,created_at) VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT(provider,subject) DO NOTHING",
                                (uid, provider, str(subject), str(name or "Kullanici")[:160], str(email or "")[:320], time.time()))
        rows = self.store._db._sorgu("SELECT id,provider,name FROM basak_account WHERE provider=%s AND subject=%s", (provider, str(subject)))
        return rows[0]

    def get(self, user_id):
        rows = self.store._db._sorgu("SELECT id,provider,name FROM basak_account WHERE id=%s", (user_id,))
        return rows[0] if rows else None

    def issue_session(self, user_id):
        if not self.get(user_id):
            raise PermissionError("Hesap bulunamadi")
        sid = secrets.token_urlsafe(32)
        expiry = int(time.time()) + SESSION_SECONDS
        body = sid + "." + str(expiry)
        token = body + "." + _signature(body)
        self.store._db._calistir("INSERT INTO basak_account_session (id,user_id,expires_at,revoked) VALUES (%s,%s,%s,0)", (hashlib.sha256(sid.encode()).hexdigest(), user_id, expiry))
        return token

    def resolve_session(self, token):
        try:
            sid, expiry, sig = token.split(".")
            if int(expiry) <= time.time() or not hmac.compare_digest(sig, _signature(sid + "." + expiry)):
                return None
            rows = self.store._db._sorgu("SELECT user_id FROM basak_account_session WHERE id=%s AND revoked=0 AND expires_at>%s", (hashlib.sha256(sid.encode()).hexdigest(), time.time()))
            return self.get(rows[0]["user_id"]) if rows else None
        except (ValueError, TypeError, RuntimeError):
            return None

    def revoke_session(self, token):
        sid = str(token or "").split(".")[0]
        self.store._db._calistir("UPDATE basak_account_session SET revoked=1 WHERE id=%s", (hashlib.sha256(sid.encode()).hexdigest(),))


def authenticate(request):
    token = request.cookies.get(COOKIE, "")
    if not token:
        return None
    try:
        account = IdentityService().resolve_session(token)
        return account["id"] if account else None
    except RuntimeError:
        return None
