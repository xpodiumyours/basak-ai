"""Revocable per-person links and opaque sessions; no email or password flow."""
import hashlib
import re
import secrets
import time
import uuid

from chat.platform_connections import ConnectionStore

_service = None
SESSION_SECONDS = 90 * 24 * 3600


def service():
    global _service
    if _service is None:
        _service = PrivateAccess()
    return _service


def _digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


class PrivateAccess:
    def __init__(self, store=None, clock=None):
        self.store = store or ConnectionStore()
        self.db = self.store._db
        self.clock = clock or time.time
        self.db._calistir('CREATE TABLE IF NOT EXISTS basak_private_invite ('
            'id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES basak_account(id),'
            'token_hash TEXT NOT NULL UNIQUE,label TEXT NOT NULL,role TEXT NOT NULL,'
            'enabled INTEGER NOT NULL,created_at DOUBLE PRECISION NOT NULL)')
        self.db._calistir('CREATE TABLE IF NOT EXISTS basak_private_session ('
            'token_hash TEXT PRIMARY KEY,invite_id TEXT NOT NULL REFERENCES basak_private_invite(id),'
            'expires_at DOUBLE PRECISION NOT NULL,revoked INTEGER NOT NULL DEFAULT 0)')

    def owner(self, user_id):
        return bool(self.db._sorgu('SELECT id FROM basak_private_invite '
            "WHERE user_id=%s AND role='owner' AND enabled=1", (user_id,)))

    def _create(self, label, owner=False):
        label = str(label or '').strip()
        if not label or len(label) > 100:
            raise ValueError('Kişinin adı 1–100 karakter olmalı')
        uid = 'casper' if owner else 'u' + uuid.uuid4().hex[:30]
        existing = self.db._sorgu('SELECT provider FROM basak_account WHERE id=%s', (uid,))
        if existing and existing[0]['provider'] != 'private_link':
            raise RuntimeError('Sahip kimliği başka hesaba bağlı; değiştirilmedi')
        self.db._calistir('INSERT INTO basak_account '
            '(id,provider,subject,name,email,created_at) VALUES (%s,%s,%s,%s,%s,%s) '
            'ON CONFLICT(id) DO NOTHING', (uid, 'private_link', uid, label, '', self.clock()))
        invite_id, code = uuid.uuid4().hex, secrets.token_urlsafe(32)
        self.db._calistir('INSERT INTO basak_private_invite '
            '(id,user_id,token_hash,label,role,enabled,created_at) VALUES (%s,%s,%s,%s,%s,1,%s)',
            (invite_id, uid, _digest(code), label, 'owner' if owner else 'guest', self.clock()))
        return {'id': invite_id, 'user_id': uid, 'label': label, 'code': code}

    def bootstrap_owner(self, label='Casper'):
        """Operator-only provisioning; no HTTP endpoint calls this method."""
        return self._create(label, owner=True)

    def create(self, actor, label):
        if not self.owner(actor):
            raise PermissionError('Bu işlemi yalnız Başak’ın sahibi yapabilir')
        return self._create(label)

    def list(self, actor):
        if not self.owner(actor):
            raise PermissionError('Bu işlemi yalnız Başak’ın sahibi yapabilir')
        return self.db._sorgu('SELECT id,label,role,enabled,created_at FROM basak_private_invite '
                             'ORDER BY created_at,id')

    def revoke(self, actor, invite_id):
        if not self.owner(actor):
            raise PermissionError('Bu işlemi yalnız Başak’ın sahibi yapabilir')
        row = self.db._sorgu('SELECT role FROM basak_private_invite WHERE id=%s', (invite_id,))
        if not row or row[0]['role'] == 'owner':
            raise ValueError('Sahip bağlantısı bu ekrandan kapatılamaz')
        self.db._calistir('UPDATE basak_private_invite SET enabled=0 WHERE id=%s', (invite_id,))

    def redeem(self, code):
        if not isinstance(code, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}', code):
            raise PermissionError('Bu özel bağlantı geçersiz veya kapatılmış')
        rows = self.db._sorgu('SELECT id FROM basak_private_invite WHERE token_hash=%s AND enabled=1',
                              (_digest(code),))
        if not rows:
            raise PermissionError('Bu özel bağlantı geçersiz veya kapatılmış')
        sid = secrets.token_urlsafe(32)
        self.db._calistir('INSERT INTO basak_private_session '
            '(token_hash,invite_id,expires_at,revoked) VALUES (%s,%s,%s,0)',
            (_digest(sid), rows[0]['id'], self.clock() + SESSION_SECONDS))
        return 'p1.' + sid

    def resolve(self, token):
        if not isinstance(token, str) or not re.fullmatch(r'p1\.[A-Za-z0-9_-]{43}', token):
            return None
        rows = self.db._sorgu('SELECT a.id,a.provider,a.name,i.role FROM basak_private_session s '
            'JOIN basak_private_invite i ON i.id=s.invite_id JOIN basak_account a ON a.id=i.user_id '
            'WHERE s.token_hash=%s AND s.revoked=0 AND s.expires_at>%s AND i.enabled=1',
            (_digest(token[3:]), self.clock()))
        return rows[0] if rows else None

    def logout(self, token):
        if isinstance(token, str) and token.startswith('p1.'):
            self.db._calistir('UPDATE basak_private_session SET revoked=1 WHERE token_hash=%s',
                              (_digest(token[3:]),))
