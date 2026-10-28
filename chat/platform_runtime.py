"""Durable task graph extending the existing ``basak_kosu`` ledger.

The model chooses tasks, providers and tools. This module persists identity,
dependencies, leases, outcomes and acceptance observations; it does not inspect
user wording. The HTTP observer is independent of the execution worker.

Design references:
https://www.kimi.com/code/docs/en/kimi-code-cli/customization/agents.html
https://www.kimi.com/code/docs/en/kimi-code-desktop/task-execution-and-review.html
"""
import base64
import contextlib
import hashlib
import json
import logging
import os
import threading
import time
import uuid
from dataclasses import dataclass

from chat import kosu_deposu

logger = logging.getLogger(__name__)


STATES = frozenset((
    "queued", "running", "waiting_children", "awaiting_approval",
    "awaiting_connection", "paused", "verifying", "completed", "partial",
    "blocked", "failed", "cancelled", "uncertain",
))
TERMINAL = frozenset(("completed", "partial", "failed", "cancelled", "uncertain"))
SETTLED = TERMINAL | {"blocked"}
PREFIX = "basak_platform_"


def delegated_result(run):
    """Tool-facing results omit private executor checkpoints, not task evidence."""
    result = {key: value for key, value in run.items()
              if key not in ('context', 'continuation', 'children')}
    if 'children' in run:
        result['children'] = [delegated_result(child) for child in run['children']]
    return result


class RuntimeErrorBase(Exception):
    pass


class NotFound(RuntimeErrorBase):
    pass


class Conflict(RuntimeErrorBase):
    pass


class Unavailable(RuntimeErrorBase):
    pass


class LeaseLost(RuntimeErrorBase):
    pass


class WorkerUnavailable(Unavailable):
    """Admission failed before any task or external action was created."""


class RunSuspended(BaseException):
    """Control-flow signal, deliberately not swallowed by tool error handlers."""


class RunCancelled(BaseException):
    """Cancellation is not an ordinary recoverable provider error."""


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _read(value, default=None):
    return json.loads(value) if value else default


def _hash(value):
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _approval_preview(action, resource, arguments):
    """Persist only a minimal, non-secret summary for informed user consent.

    Arguments themselves are digested for an immutable, single-use approval;
    do not expose OAuth tokens, file content, form values, headers or passwords.
    """
    args = arguments if isinstance(arguments, dict) else {}
    result = {"action": str(action)[:64], "resource": str(resource)[:140]}
    targets = {}
    if action == "baglanti_cagir":
        result["operation"] = str(args.get("arac") or "")[:90]
        source = args.get("argumanlar")
        if isinstance(source, dict):
            for key in ("repository", "branch", "path", "workflow", "ref",
                        "document_id", "spreadsheet_id", "page_id", "block_id",
                        "file_id", "range", "data_source_id"):
                value = source.get(key)
                if isinstance(value, str) and value and len(value) <= 250:
                    targets[key] = value
    elif action == "bulut_tarayici":
        result["operation"] = str(args.get("islem") or "")[:90]
        source = args.get("argumanlar")
        if isinstance(source, dict):
            sid = source.get("session_id")
            if isinstance(sid, str) and sid and len(sid) <= 128:
                targets["session_id"] = sid
            # Never include input text, selectors or full URLs with query
            # tokens. Those still participate in the immutable digest.
    result["target"] = targets
    return result


def _key(value, name):
    value = str(value or "").strip()
    if not value or len(value) > 128 or any(ord(c) < 32 for c in value):
        raise ValueError(name + " gerekli ve en fazla 128 karakter olmalı")
    return value


@dataclass(frozen=True)
class Lease:
    run_id: str
    user_id: str
    worker_id: str
    token: str
    generation: int
    expires_at: float


class _Transaction:
    def __init__(self, conn, sqlite):
        self.conn, self.sqlite = conn, sqlite

    def execute(self, sql, values=()):
        cursor = self.conn.cursor()
        cursor.execute(sql.replace("%s", "?") if self.sqlite else sql, values)
        return cursor

    def rows(self, sql, values=()):
        cur = self.execute(sql, values)
        names = [d[0] for d in (cur.description or ())]
        return [dict(zip(names, row)) for row in cur.fetchall()]

    def one(self, sql, values=()):
        rows = self.rows(sql, values)
        return rows[0] if rows else None


class RuntimeStore:
    """Parent/child tasks in the same database and canonical run rows.

    Production never falls back to ephemeral SQLite. Constructor injection is
    used by tests and by the worker process with its existing ledger backend.
    """
    def __init__(self, depo=None, *, clock=None, max_queued_per_user=32,
                 max_children_per_parent=8, max_active_children_per_parent=3,
                 max_descendants_per_root=32):
        # Bound delegated work independently of provider context length.
        # Same values in every process; the database enforces limits atomically.
        self.max_children_per_parent = (int(max_children_per_parent)
                                        if max_children_per_parent is not None else None)
        self.max_active_children_per_parent = int(max_active_children_per_parent)
        self.max_descendants_per_root = int(max_descendants_per_root)
        if self.max_descendants_per_root < 1:
            raise ValueError('Gorev agaci kapasitesi pozitif olmali')
        if not (1 <= self.max_active_children_per_parent <= 32) or (
                self.max_children_per_parent is not None and not
                self.max_active_children_per_parent <= self.max_children_per_parent <= 32):
            raise ValueError("Alt ajan kapasitesi 1..32 ve aktif <= toplam olmali")
        self.depo = depo if depo is not None else kosu_deposu._depo()
        if self.depo is None:
            raise Unavailable("Kalıcı görev deposu hazır değil")
        self.clock = clock or time.time
        self.max_queued_per_user = (None if max_queued_per_user is None
                                    else int(max_queued_per_user))
        if self.max_queued_per_user is not None and not 1 <= self.max_queued_per_user <= 256:
            raise ValueError("Kullanici gorev kapasitesi 1..256 olmali")
        self._schema()

    @contextlib.contextmanager
    def transaction(self, *, readonly=False):
        # Only metadata transactions serialize. Model/tool execution takes place
        # outside the transaction and may run concurrently on separate workers.
        with self.depo._kilit:
            conn = self.depo._baglan()
            sqlite = self.depo.ad == "sqlite"
            try:
                if sqlite:
                    conn.execute("PRAGMA foreign_keys=ON")
                    conn.execute("BEGIN" if readonly else "BEGIN IMMEDIATE")
                    yield _Transaction(conn, True)
                    conn.commit()
                else:
                    with conn.transaction():
                        tx = _Transaction(conn, False)
                        if readonly:
                            tx.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
                        else:
                            tx.execute("SELECT pg_advisory_xact_lock(hashtext('basak_platform_ledger'))")
                        yield tx
            except BaseException:
                if sqlite:
                    conn.rollback()
                raise
            finally:
                conn.close()

    def _schema(self):
        tables = (
            "CREATE TABLE IF NOT EXISTS basak_platform_run ("
            "run_id TEXT PRIMARY KEY REFERENCES basak_kosu(id), user_id TEXT NOT NULL, "
            "workspace_id TEXT NOT NULL, parent_id TEXT REFERENCES basak_platform_run(run_id), "
            "kind TEXT NOT NULL, model_ref TEXT NOT NULL DEFAULT '', spec TEXT NOT NULL, "
            "request_key TEXT, request_hash TEXT NOT NULL, continuation TEXT, "
            "worker_id TEXT, lease_token TEXT, lease_until DOUBLE PRECISION, "
            "generation INTEGER NOT NULL DEFAULT 0, seq INTEGER NOT NULL DEFAULT 0, "
            "waiting TEXT NOT NULL DEFAULT '[]', "
            "UNIQUE(user_id, workspace_id, request_key))",
            "CREATE TABLE IF NOT EXISTS basak_platform_chat_route ("
            "user_id TEXT NOT NULL, workspace_id TEXT NOT NULL, request_key TEXT NOT NULL, "
            "request_hash TEXT NOT NULL, PRIMARY KEY(user_id,workspace_id,request_key))",
            "CREATE TABLE IF NOT EXISTS basak_platform_dependency ("
            "run_id TEXT NOT NULL REFERENCES basak_platform_run(run_id), "
            "dependency_id TEXT NOT NULL REFERENCES basak_platform_run(run_id), "
            "PRIMARY KEY(run_id, dependency_id))",
            "CREATE TABLE IF NOT EXISTS basak_platform_event ("
            "run_id TEXT NOT NULL REFERENCES basak_platform_run(run_id), "
            "seq INTEGER NOT NULL, type TEXT NOT NULL, payload TEXT NOT NULL, "
            "created_at DOUBLE PRECISION NOT NULL, PRIMARY KEY(run_id,seq))",
            "CREATE TABLE IF NOT EXISTS basak_platform_action ("
            "run_id TEXT NOT NULL REFERENCES basak_platform_run(run_id), "
            "call_id TEXT NOT NULL, tool TEXT NOT NULL, arguments TEXT NOT NULL, "
            "digest TEXT NOT NULL, side_effect INTEGER NOT NULL, status TEXT NOT NULL, "
            "result TEXT, ok INTEGER, generation INTEGER NOT NULL, "
            "PRIMARY KEY(run_id,call_id))",
            "CREATE TABLE IF NOT EXISTS basak_platform_check ("
            "run_id TEXT NOT NULL REFERENCES basak_platform_run(run_id), "
            "check_id TEXT NOT NULL, ok INTEGER NOT NULL, evidence TEXT NOT NULL, "
            "created_at DOUBLE PRECISION NOT NULL, PRIMARY KEY(run_id,check_id))",
            "CREATE TABLE IF NOT EXISTS basak_platform_artifact ("
            "run_id TEXT NOT NULL REFERENCES basak_platform_run(run_id), "
            "artifact_id TEXT NOT NULL, data TEXT NOT NULL, "
            "PRIMARY KEY(run_id,artifact_id))",
            "CREATE TABLE IF NOT EXISTS basak_platform_steering ("
            "id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES basak_platform_run(run_id), "
            "text TEXT NOT NULL, created_at DOUBLE PRECISION NOT NULL, position INTEGER NOT NULL DEFAULT 0, consumed INTEGER NOT NULL DEFAULT 0)",
            "CREATE TABLE IF NOT EXISTS basak_platform_approval ("
            "id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES basak_platform_run(run_id), "
            "action TEXT NOT NULL, resource TEXT NOT NULL, arguments_digest TEXT NOT NULL, "
            "status TEXT NOT NULL, created_at DOUBLE PRECISION NOT NULL, "
            "preview TEXT NOT NULL DEFAULT '{}')",
            "CREATE TABLE IF NOT EXISTS basak_platform_worker_presence ("
            "worker_id TEXT PRIMARY KEY, seen_at DOUBLE PRECISION NOT NULL, "
            "state TEXT NOT NULL)",
            "CREATE INDEX IF NOT EXISTS basak_platform_owner ON basak_platform_run(user_id,workspace_id)",
            "CREATE INDEX IF NOT EXISTS basak_platform_parent ON basak_platform_run(parent_id)",
            "CREATE TABLE IF NOT EXISTS basak_platform_workspace_file ("
            "user_id TEXT NOT NULL, workspace_id TEXT NOT NULL, path TEXT NOT NULL, "
            "data_base64 TEXT NOT NULL, sha256 TEXT NOT NULL, "
            "PRIMARY KEY(user_id,workspace_id,path))",
        )
        with self.transaction() as tx:
            for statement in tables:
                tx.execute(statement)
            columns = [d[0] for d in tx.execute("SELECT * FROM basak_platform_steering LIMIT 0").description]
            if "position" not in columns:
                tx.execute("ALTER TABLE basak_platform_steering ADD COLUMN position INTEGER NOT NULL DEFAULT 0")
            approval_columns = [d[0] for d in tx.execute(
                "SELECT * FROM basak_platform_approval LIMIT 0").description]
            if "preview" not in approval_columns:
                tx.execute("ALTER TABLE basak_platform_approval ADD COLUMN preview TEXT NOT NULL DEFAULT '{}'")
            file_columns = [d[0] for d in tx.execute(
                'SELECT * FROM basak_platform_workspace_file LIMIT 0').description]
            if 'deleted' not in file_columns:
                tx.execute('ALTER TABLE basak_platform_workspace_file ADD COLUMN deleted INTEGER NOT NULL DEFAULT 0')

    def worker_ping(self, worker_id):
        """Worker proves liveness independently of whether jobs are queued."""
        worker_id = _key(worker_id, "worker_id")
        with self.transaction() as tx:
            tx.execute("INSERT INTO basak_platform_worker_presence"
                       "(worker_id,seen_at,state) VALUES(%s,%s,'online') "
                       "ON CONFLICT(worker_id) DO UPDATE SET "
                       "seen_at=excluded.seen_at,state='online'",
                       (worker_id, self.clock()))

    def workspace_files(self, user_id, workspace_id, include_deleted=False):
        with self.transaction(readonly=True) as tx:
            return tx.rows('SELECT path,data_base64,sha256,deleted FROM basak_platform_workspace_file '
                           'WHERE user_id=%s AND workspace_id=%s' + ('' if include_deleted else ' AND deleted=0'),
                           (user_id, workspace_id))

    def publish_files(self, lease, workspace_id, changes):
        """Compare content versions before publishing parallel worker changes."""
        with self.transaction() as tx:
            row = self._lease(tx, lease)
            if row['workspace_id'] != workspace_id:
                raise Conflict('Calisma alani eslesmiyor')
            for item in changes:
                old = tx.one('SELECT sha256,deleted FROM basak_platform_workspace_file '
                             'WHERE user_id=%s AND workspace_id=%s AND path=%s',
                             (lease.user_id, workspace_id, item['path']))
                actual = old['sha256'] if old and not old['deleted'] else None
                same_result = bool(old and old['sha256'] == item['sha256']
                                   and bool(old['deleted']) == bool(item.get('deleted')))
                if actual != item['before_sha256'] and not same_result:
                    raise Conflict('Paralel dosya degisikligi: ' + item['path'])
            for item in changes:
                tx.execute('INSERT INTO basak_platform_workspace_file '
                           '(user_id,workspace_id,path,data_base64,sha256,deleted) VALUES(%s,%s,%s,%s,%s,%s) '
                           'ON CONFLICT(user_id,workspace_id,path) DO UPDATE SET '
                           'data_base64=excluded.data_base64,sha256=excluded.sha256,deleted=excluded.deleted',
                           (lease.user_id, workspace_id, item['path'], item['data_base64'], item['sha256'],
                            int(bool(item.get('deleted')))))

    def worker_stopped(self, worker_id):
        worker_id = _key(worker_id, "worker_id")
        with self.transaction() as tx:
            tx.execute("UPDATE basak_platform_worker_presence SET state='offline',"
                       "seen_at=%s WHERE worker_id=%s", (self.clock(), worker_id))

    def worker_health(self, stale_seconds=30):
        """No health signal means unavailable, never a simulated live worker."""
        stale_seconds = max(1, min(int(stale_seconds), 600))
        now = self.clock()
        with self.transaction(readonly=True) as tx:
            rows = tx.rows("SELECT seen_at FROM basak_platform_worker_presence "
                           "WHERE state='online' AND seen_at>=%s",
                           (now-stale_seconds,))
        return {"online": bool(rows), "live_workers": len(rows),
                "freshness_seconds": stale_seconds,
                "last_seen_age_seconds": round(now-max(x["seen_at"] for x in rows), 1)
                if rows else None}

    def _require(self, tx, user, run_id):
        row = tx.one(
            "SELECT r.*,m.user_id,m.workspace_id,m.parent_id,m.kind,m.model_ref,m.spec,"
            "m.continuation,m.worker_id,m.lease_token,m.lease_until,m.generation,m.seq,m.waiting "
            "FROM basak_kosu r JOIN basak_platform_run m ON r.id=m.run_id "
            "WHERE r.id=%s AND r.kullanici=%s AND m.user_id=%s", (run_id, user, user))
        if row is None:
            raise NotFound("Görev bulunamadı")
        return row

    def _lease(self, tx, lease, row=None):
        row = row if row is not None else self._require(tx, lease.user_id, lease.run_id)
        if (row['id'] != lease.run_id or row['user_id'] != lease.user_id
                or row["durum"] != "running" or row["lease_token"] != lease.token
                or row["generation"] != lease.generation or row["worker_id"] != lease.worker_id
                or float(row["lease_until"] or 0) <= self.clock()):
            raise LeaseLost("Görev yürütme yetkisi sona erdi")
        return row

    def _event(self, tx, run_id, type_, payload, bubble=True):
        tx.execute("UPDATE basak_platform_run SET seq=seq+1 WHERE run_id=%s", (run_id,))
        meta = tx.one("SELECT seq,parent_id FROM basak_platform_run WHERE run_id=%s", (run_id,))
        seq = meta["seq"]
        tx.execute("INSERT INTO basak_platform_event(run_id,seq,type,payload,created_at) VALUES(%s,%s,%s,%s,%s)",
                   (run_id, seq, type_, _json(payload), self.clock()))
        if bubble and meta["parent_id"]:
            data = {**payload, "origin_run_id": payload.get("origin_run_id", run_id)}
            self._event(tx, meta["parent_id"], type_, data)
        return seq

    def _status(self, tx, row, state, reason="", release=True):
        if state not in STATES:
            raise ValueError("Bilinmeyen görev durumu")
        tx.execute("UPDATE basak_kosu SET durum=%s,hata=%s,guncelleme=%s WHERE id=%s",
                   (state, reason, kosu_deposu._simdi(), row["id"]))
        if release:
            tx.execute("UPDATE basak_platform_run SET lease_token=NULL,worker_id=NULL,lease_until=NULL WHERE run_id=%s", (row["id"],))
        self._event(tx, row["id"], "status", {"durum": state, "reason": reason})

    def _project(self, tx, row, recursive=False):
        spec = _read(row["spec"], {})
        checks = [{"id": r["check_id"], "ok": bool(r["ok"]), "evidence": _read(r["evidence"], {})}
                  for r in tx.rows("SELECT * FROM basak_platform_check WHERE run_id=%s ORDER BY check_id", (row["id"],))]
        artifacts = []
        for value in tx.rows("SELECT artifact_id,data FROM basak_platform_artifact WHERE run_id=%s ORDER BY artifact_id", (row["id"],)):
            item = _read(value["data"], {})
            item['media_type'] = item.get('media_type') or item.get('mime_type') or 'application/octet-stream'
            item = {k: v for k, v in item.items() if k not in ("content", "data_base64", "path", "local_path")}
            item.update({"id": value["artifact_id"], "href": "/api/kosu/%s/artifacts/%s" % (row["id"], value["artifact_id"])})
            artifacts.append(item)
        approvals = [{**r, "preview": _read(r["preview"], {})} for r in tx.rows(
            "SELECT id,action,resource,arguments_digest,status,preview "
            "FROM basak_platform_approval WHERE run_id=%s ORDER BY created_at,id", (row["id"],))]
        child_ids = tx.rows("SELECT run_id FROM basak_platform_run WHERE parent_id=%s AND user_id=%s ORDER BY run_id", (row["id"], row["user_id"]))
        children = [self._project(tx, self._require(tx, row["user_id"], x["run_id"]), recursive=True)
                    for x in child_ids] if recursive else [x["run_id"] for x in child_ids]
        return {"id": row["id"], "kosu_id": row["id"], "user_id": row["user_id"],
                "workspace_id": row["workspace_id"], "parent_id": row["parent_id"],
                "kind": row["kind"], "model_ref": row["model_ref"], "durum": row["durum"],
                "istek": row["istek"], "answer": row.get("cevap") or "", "cevap": row.get("cevap") or "",
                "hata": row.get("hata") or "", "provider": row.get("saglayici") or "",
                "seq": row["seq"], "olustu": str(row["olustu"]), "guncelleme": str(row["guncelleme"]),
                "children": children, "artifacts": artifacts, "checks": checks, "approvals": approvals,
                "acceptance": spec.get("acceptance", []), "allowed_tools": spec.get("allowed_tools"),
                "context": spec.get("context", {}), "continuation": _read(row["continuation"]),
                "dependencies": [x["dependency_id"] for x in tx.rows("SELECT dependency_id FROM basak_platform_dependency WHERE run_id=%s", (row["id"],))]}

    def create(self, user_id, workspace_id, instruction, *, model_ref="", parent_id=None,
               dependencies=(), allowed_tools=None, acceptance=None, request_key=None,
               run_id=None, kind="agent", context=None, require_worker=False,
               allow_legacy=False, durable_enabled=True):
        user_id, workspace_id = _key(user_id, "user_id"), _key(workspace_id, "workspace_id")
        instruction = str(instruction or "").strip()
        if not instruction:
            raise ValueError("Görev açıklaması gerekli")
        acceptance = acceptance if acceptance is not None else [
            {"id": "result_verified", "kind": "execution_observed",
             "description": "Alt görevin araçları ve çıktı kaydı doğrulandı"}
            if parent_id else ({"id": "response_recorded", "kind": "message_recorded",
                               "description": "Sohbet yanıtı kaydedildi"} if kind == 'chat' else
                              {"id": "result_verified", "description": "Sonuç doğrulandı"})]
        if not isinstance(acceptance, (list, tuple)) or not acceptance:
            raise ValueError("En az bir kabul koşulu gerekli")
        if any(not isinstance(c, dict) or not c.get("id") for c in acceptance):
            raise ValueError("Kabul koşulu kimliği gerekli")
        if len({c["id"] for c in acceptance}) != len(acceptance):
            raise ValueError("Kabul koşulları benzersiz olmalı")
        kind = _key(kind, "kind")
        deps = sorted(set(dependencies or ()))
        spec = {"acceptance": list(acceptance), "allowed_tools": allowed_tools,
                "context": context or {}}
        payload = {"instruction": instruction, "parent_id": parent_id, "dependencies": deps,
                   "model_ref": model_ref, "kind": kind, **spec}
        with self.transaction() as tx:
            if request_key:
                if not tx.sqlite:
                    tx.execute("SELECT pg_advisory_xact_lock(hashtext(%s))",
                               (_hash([user_id, workspace_id, request_key]),))
                old = tx.one("SELECT run_id,request_hash FROM basak_platform_run WHERE user_id=%s AND workspace_id=%s AND request_key=%s", (user_id, workspace_id, _key(request_key, "request_key")))
                if old:
                    if old["request_hash"] != _hash(payload):
                        raise Conflict("Aynı istek kimliği farklı görevle kullanıldı")
                    return self._project(tx, self._require(tx, user_id, old["run_id"]))
                legacy = tx.one("SELECT request_hash FROM basak_platform_chat_route "
                                "WHERE user_id=%s AND workspace_id=%s AND request_key=%s",
                                (user_id, workspace_id, request_key))
                if legacy:
                    if legacy['request_hash'] != _hash(payload):
                        raise Conflict("Ayni istek kimligi farkli sohbetle kullanildi")
                    return None
            ready = not require_worker or bool(tx.one(
                    "SELECT worker_id FROM basak_platform_worker_presence "
                    "WHERE state='online' AND seen_at>=%s LIMIT 1", (self.clock()-30,)))
            if allow_legacy and (not durable_enabled or not ready):
                if request_key:
                    tx.execute("INSERT INTO basak_platform_chat_route "
                               "(user_id,workspace_id,request_key,request_hash) VALUES(%s,%s,%s,%s)",
                               (user_id, workspace_id, request_key, _hash(payload)))
                return None
            if not ready:
                raise WorkerUnavailable("Kalici calisma su anda kullanilamiyor")
            if parent_id:
                parent = self._require(tx, user_id, parent_id)
                if parent["workspace_id"] != workspace_id or parent["durum"] in TERMINAL:
                    raise Conflict("Üst görev bu çalışma alanında etkin değil")
                child_count = tx.one(
                    "SELECT COUNT(*) AS n FROM basak_platform_run WHERE parent_id=%s",
                    (parent_id,))["n"]
                if self.max_children_per_parent is not None and child_count >= self.max_children_per_parent:
                    raise Conflict("Ana gorevin alt ajan kapasitesi dolu")
                root = parent
                while root['parent_id']:
                    root = self._require(tx, user_id, root['parent_id'])
                descendants = tx.one(
                    'WITH RECURSIVE tree(run_id) AS ('
                    'SELECT run_id FROM basak_platform_run WHERE parent_id=%s AND user_id=%s '
                    'UNION ALL SELECT m.run_id FROM basak_platform_run m JOIN tree t ON m.parent_id=t.run_id '
                    'WHERE m.user_id=%s) SELECT COUNT(*) AS n FROM tree',
                    (root['id'], user_id, user_id))['n']
                if descendants >= self.max_descendants_per_root:
                    raise Conflict('Gorev agacinin toplam alt ajan kapasitesi dolu')
                parent_tools = _read(parent["spec"], {}).get("allowed_tools")
                if parent_tools is not None:
                    if allowed_tools is None:
                        spec["allowed_tools"] = list(parent_tools)
                    elif set(allowed_tools) - set(parent_tools):
                        raise Conflict("Alt görev üst görevin araç erişimini genişletemez")
            for dep in deps:
                other = self._require(tx, user_id, dep)
                if other["workspace_id"] != workspace_id:
                    raise Conflict("Bağımlılık başka çalışma alanında")
                ancestor = parent_id
                while ancestor:
                    if dep == ancestor:
                        raise Conflict("Alt görev kendi üst görevinin bitmesini bekleyemez")
                    ancestor = self._require(tx, user_id, ancestor)["parent_id"]
            if self.max_queued_per_user is not None:
                # Settled runs do not occupy a worker slot. In particular,
                # blocked and uncertain runs must not exhaust future capacity.
                # This does not make uncertain external effects retryable.
                active = tx.one(
                    "SELECT COUNT(*) AS n FROM basak_kosu r "
                    "JOIN basak_platform_run m ON m.run_id=r.id "
                    "WHERE m.user_id=%s "
                    "AND r.durum NOT IN ('completed','partial','failed',"
                    "'cancelled','uncertain','blocked')",
                    (user_id,),
                )["n"]
                if active >= self.max_queued_per_user:
                    raise Conflict("Kullanıcının görev kapasitesi dolu")
            rid = _key(run_id, "run_id") if run_id else uuid.uuid4().hex
            existing = tx.one("SELECT * FROM basak_kosu WHERE id=%s", (rid,))
            if existing and existing["kullanici"] != user_id:
                raise NotFound("Görev bulunamadı")
            if tx.one("SELECT run_id FROM basak_platform_run WHERE run_id=%s", (rid,)):
                raise Conflict("Görev zaten var")
            now = kosu_deposu._simdi()
            if existing is None:
                tx.execute("INSERT INTO basak_kosu(id,kullanici,istek,durum,tool_policy,saglayici,adim,olustu,guncelleme) VALUES(%s,%s,%s,'queued','auto','',0,%s,%s)", (rid, user_id, instruction, now, now))
            else:
                tx.execute("UPDATE basak_kosu SET durum='queued' WHERE id=%s", (rid,))
            tx.execute("INSERT INTO basak_platform_run(run_id,user_id,workspace_id,parent_id,kind,model_ref,spec,request_key,request_hash) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)", (rid, user_id, workspace_id, parent_id, kind, model_ref or "", _json(spec), request_key, _hash(payload)))
            for dep in deps:
                tx.execute("INSERT INTO basak_platform_dependency(run_id,dependency_id) VALUES(%s,%s)", (rid, dep))
            self._event(tx, rid, "status", {"durum": "queued", "parent_id": parent_id})
            return self._project(tx, self._require(tx, user_id, rid))

    def get(self, user_id, run_id):
        with self.transaction(readonly=True) as tx:
            return self._project(tx, self._require(tx, user_id, run_id))

    def tree(self, user_id, run_id):
        with self.transaction(readonly=True) as tx:
            return self._project(tx, self._require(tx, user_id, run_id), recursive=True)

    def list(self, user_id, *, workspace_id=None, after=None, limit=50):
        _key(user_id, "user_id")
        limit = max(1, min(int(limit), 200))
        with self.transaction(readonly=True) as tx:
            sql = "SELECT r.id FROM basak_kosu r JOIN basak_platform_run m ON r.id=m.run_id WHERE m.user_id=%s AND r.kullanici=%s"
            params = [user_id, user_id]
            if workspace_id is not None:
                sql += " AND m.workspace_id=%s"
                params.append(workspace_id)
            if after:
                previous = self._require(tx, user_id, after)
                sql += " AND (r.olustu<%s OR (r.olustu=%s AND r.id>%s))"
                params.extend([previous["olustu"], previous["olustu"], after])
            sql += " ORDER BY r.olustu DESC,r.id LIMIT %s"
            params.append(limit)
            return [self._project(tx, self._require(tx, user_id, r["id"])) for r in tx.rows(sql, tuple(params))]

    def request_run(self, user_id, workspace_id, request_key):
        """Find a receipt before admission; existing tasks never switch engines."""
        if not request_key:
            return None
        with self.transaction(readonly=True) as tx:
            row = tx.one("SELECT run_id FROM basak_platform_run WHERE user_id=%s "
                         "AND workspace_id=%s AND request_key=%s",
                         (user_id, workspace_id, _key(request_key, "request_key")))
            return self._project(tx, self._require(tx, user_id, row['run_id'])) if row else None

    def chat_threads(self, user_id):
        """Rebuild account chat history from durable root turns, including pending ones."""
        with self.transaction(readonly=True) as tx:
            rows = tx.rows("SELECT r.id FROM basak_kosu r JOIN basak_platform_run m ON r.id=m.run_id "
                           "WHERE m.user_id=%s AND r.kullanici=%s AND m.kind='chat' AND m.parent_id IS NULL "
                           "ORDER BY r.olustu,r.id", (user_id, user_id))
            threads = {}
            for row in rows:
                run = self._project(tx, self._require(tx, user_id, row['id']))
                context = run['context']
                cid = context.get('conversation_id') or run['id']
                thread = threads.setdefault(cid, {
                    'id': cid, 'title': context.get('conversation_title') or run['istek'],
                    'messages': list(context.get('history') or []), 'pendingRuns': [], 'runs': []})
                thread['messages'].append({'role': 'user', 'content': context.get('display_text') or run['istek']})
                if run['answer']:
                    thread['messages'].append({'role': 'assistant', 'content': run['answer']})
                if run['durum'] not in TERMINAL:
                    thread['pendingRuns'].append({'id': run['id'], 'state': run['durum']})
                thread['runs'].append({'id': run['id'], 'state': run['durum']})
                thread['updatedAt'] = run['guncelleme']
            return list(threads.values())

    def events(self, user_id, run_id, after=0, limit=200):
        with self.transaction(readonly=True) as tx:
            self._require(tx, user_id, run_id)
            rows = tx.rows("SELECT * FROM basak_platform_event WHERE run_id=%s AND seq>%s ORDER BY seq LIMIT %s", (run_id, max(0, int(after)), max(1, min(int(limit), 1000))))
            return [{**r, "payload": _read(r["payload"], {})} for r in rows]

    def append_event(self, user_id, run_id, type_, payload, *, lease=None):
        with self.transaction() as tx:
            row = self._require(tx, user_id, run_id)
            if lease is not None:
                if row['durum'] in {'cancelled', 'uncertain'}:
                    raise RunCancelled()
                self._lease(tx, lease, row=row)
            if type_ == 'provider' and payload.get('provider'):
                tx.execute('UPDATE basak_kosu SET saglayici=%s WHERE id=%s',
                           (str(payload['provider']), run_id))
            return self._event(tx, run_id, str(type_), dict(payload or {}))

    def _recover(self, tx):
        expired = tx.rows("SELECT m.run_id,m.user_id FROM basak_platform_run m JOIN basak_kosu r ON r.id=m.run_id WHERE r.durum='running' AND m.lease_until<=%s", (self.clock(),))
        for meta in expired:
            row = self._require(tx, meta["user_id"], meta["run_id"])
            effect = tx.one("SELECT call_id FROM basak_platform_action WHERE run_id=%s AND status='running' AND side_effect=1", (row["id"],))
            if effect:
                tx.execute("UPDATE basak_platform_action SET status='uncertain' WHERE run_id=%s AND status='running' AND side_effect=1", (row["id"],))
                self._status(tx, row, "uncertain", "İşçi bağlantısı kesildi; dış işlemin sonucu doğrulanmalı")
            else:
                tx.execute("UPDATE basak_platform_action SET status='retryable' WHERE run_id=%s AND status='running' AND side_effect=0", (row["id"],))
                self._status(tx, row, "queued", "İşçi bağlantısı kesildi; kalıcı kayıttan devam")
        waiting = tx.rows("SELECT m.run_id,m.user_id,m.waiting FROM basak_platform_run m JOIN basak_kosu r ON r.id=m.run_id WHERE r.durum='waiting_children'")
        for meta in waiting:
            deps = [self._require(tx, meta["user_id"], rid) for rid in _read(meta["waiting"], [])]
            if deps and all(d["durum"] in SETTLED for d in deps):
                self._status(tx, self._require(tx, meta["user_id"], meta["run_id"]), "queued")
        # Cocuklari hala calisirken biten ust gorev `verifying`te kalir.
        # Cocuklar kapandiginda burada yeniden degerlendirilir; aksi halde
        # kosu kalici olarak yarim gorunur ve UI "surdurulebilir" der.
        verifying = tx.rows(
            "SELECT m.run_id,m.user_id FROM basak_platform_run m "
            "JOIN basak_kosu r ON r.id=m.run_id WHERE r.durum='verifying'")
        for meta in verifying:
            row = self._require(tx, meta["user_id"], meta["run_id"])
            state = self._otomatik_durum(tx, row, str(row.get("cevap") or ""))
            if state != "verifying":
                self._status(tx, row, state, "")

    def claim(self, worker_id, lease_seconds=60, run_id=None):
        worker_id = _key(worker_id, "worker_id")
        lease_seconds = float(lease_seconds)
        if lease_seconds <= 0:
            raise ValueError("Lease süresi pozitif olmalı")
        with self.transaction() as tx:
            self._recover(tx)
            sql = "SELECT m.run_id,m.user_id FROM basak_platform_run m JOIN basak_kosu r ON r.id=m.run_id WHERE r.durum='queued'"
            params = []
            if run_id:
                sql += " AND m.run_id=%s"
                params.append(run_id)
            sql += " ORDER BY r.olustu,r.id"
            if self.depo.ad != "sqlite":
                sql += " FOR UPDATE OF r SKIP LOCKED"
            for candidate in tx.rows(sql, tuple(params)):
                row = self._require(tx, candidate["user_id"], candidate["run_id"])
                if row["parent_id"]:
                    parent = self._require(tx, row["user_id"], row["parent_id"])
                    if parent["durum"] in TERMINAL:
                        self._status(tx, row, "cancelled", "Üst görev kapandı")
                        continue
                    active = tx.one(
                        "SELECT COUNT(*) AS n FROM basak_platform_run m "
                        "JOIN basak_kosu r ON r.id=m.run_id "
                        "WHERE m.parent_id=%s AND r.durum='running'",
                        (row["parent_id"],))["n"]
                    if active >= self.max_active_children_per_parent:
                        continue  # Keep pending work durable, do not run a fourth sibling.
                deps = tx.rows("SELECT r.durum FROM basak_platform_dependency d JOIN basak_kosu r ON d.dependency_id=r.id WHERE d.run_id=%s", (row["id"],))
                if any(d["durum"] in SETTLED - {"completed"} for d in deps):
                    self._status(tx, row, "blocked", "Bağımlı görev tamamlanamadı")
                    continue
                if any(d["durum"] != "completed" for d in deps):
                    continue
                token, expires = uuid.uuid4().hex, self.clock() + lease_seconds
                generation = int(row["generation"]) + 1
                tx.execute("UPDATE basak_platform_run SET worker_id=%s,lease_token=%s,lease_until=%s,generation=%s WHERE run_id=%s", (worker_id, token, expires, generation, row["id"]))
                self._status(tx, row, "running", release=False)
                job = self._project(tx, self._require(tx, row["user_id"], row["id"]))
                job["lease"] = Lease(row["id"], row["user_id"], worker_id, token, generation, expires)
                return job
        return None

    def heartbeat(self, lease, lease_seconds=60):
        with self.transaction() as tx:
            self._lease(tx, lease)
            tx.execute("UPDATE basak_platform_run SET lease_until=%s WHERE run_id=%s", (self.clock() + float(lease_seconds), lease.run_id))

    def checkpoint(self, lease, continuation):
        with self.transaction() as tx:
            row = self._lease(tx, lease)
            continuation = dict(continuation)
            old = _read(row["continuation"], {})
            # Delivered direction remains recoverable until it is represented in
            # model history. Adapters deduplicate by steering_id on restoration.
            if old.get("steering_messages"):
                continuation.setdefault("steering_messages", old["steering_messages"])
            tx.execute("UPDATE basak_platform_run SET continuation=%s WHERE run_id=%s", (_json(continuation), lease.run_id))
            self._event(tx, lease.run_id, "checkpoint", {"generation": lease.generation})

    def replay_completed(self, lease, call_id, tool, args):
        """No fresh approval needed for an identical already-completed call.

        The committed record is authoritative; never re-execute its effect.
        """
        with self.transaction() as tx:
            self._lease(tx, lease)
            row = tx.one("SELECT tool,digest,status FROM basak_platform_action "
                         "WHERE run_id=%s AND call_id=%s", (lease.run_id, call_id))
            if not row:
                return False
            if row["tool"] != tool or row["digest"] != _hash({"tool": tool, "args": args}):
                raise Conflict("Araç çağrısı kimliği farklı argümanlarla kullanıldı")
            return row["status"] == "completed"

    def begin_action(self, lease, call_id, tool, args, side_effect=False):
        call_id = _key(call_id, "call_id")
        with self.transaction() as tx:
            self._lease(tx, lease)
            digest = _hash({"tool": tool, "args": args})
            old = tx.one("SELECT * FROM basak_platform_action WHERE run_id=%s AND call_id=%s", (lease.run_id, call_id))
            if old:
                if old["digest"] != digest:
                    raise Conflict("Araç çağrısı kimliği farklı argümanlarla kullanıldı")
                if old["status"] == "completed":
                    return {"result": _read(old["result"]), "ok": bool(old["ok"])}
                if old["status"] != "retryable":
                    raise Conflict("Araç çağrısı zaten sürüyor veya sonucu belirsiz")
                tx.execute("UPDATE basak_platform_action SET status='running',generation=%s WHERE run_id=%s AND call_id=%s", (lease.generation, lease.run_id, call_id))
            else:
                tx.execute("INSERT INTO basak_platform_action(run_id,call_id,tool,arguments,digest,side_effect,status,generation) VALUES(%s,%s,%s,%s,%s,%s,'running',%s)", (lease.run_id, call_id, tool, _json(args), digest, int(bool(side_effect)), lease.generation))
            self._event(tx, lease.run_id, "tool_started", {"call_id": call_id, "tool": tool, "side_effect": bool(side_effect)})
            return None

    def finish_action(self, lease, call_id, result, ok):
        with self.transaction() as tx:
            self._lease(tx, lease)
            action = tx.one("SELECT * FROM basak_platform_action WHERE run_id=%s AND call_id=%s", (lease.run_id, call_id))
            if not action or action["status"] != "running" or action["generation"] != lease.generation:
                raise Conflict("Etkin araç çağrısı bulunamadı")
            tx.execute("UPDATE basak_platform_action SET status='completed',result=%s,ok=%s WHERE run_id=%s AND call_id=%s", (_json(result), int(bool(ok)), lease.run_id, call_id))
            self._event(tx, lease.run_id, "tool_done", {"call_id": call_id, "tool": action["tool"], "ok": bool(ok)})

    def actions(self, user_id, run_id):
        """Complete observations for trusted acceptance validators and inspection."""
        with self.transaction() as tx:
            self._require(tx, user_id, run_id)
            return [{**r, "arguments": _read(r["arguments"], {}),
                     "result": _read(r["result"]), "ok": bool(r["ok"])}
                    for r in tx.rows("SELECT * FROM basak_platform_action WHERE run_id=%s ORDER BY call_id", (run_id,))]

    def reconcile_action(self, user_id, run_id, call_id, result, ok, evidence):
        """Record an externally observed uncertain effect, without retrying it."""
        if type(ok) is not bool or not isinstance(evidence, dict) or not evidence:
            raise ValueError("Uzlaştırma bağımsız gözlem kanıtı gerektirir")
        with self.transaction() as tx:
            row = self._require(tx, user_id, run_id)
            action = tx.one("SELECT * FROM basak_platform_action WHERE run_id=%s AND call_id=%s", (run_id, call_id))
            if row["durum"] != "uncertain" or not action or action["status"] != "uncertain":
                raise Conflict("Belirsiz işlem bulunamadı")
            artifact = tx.one('SELECT data FROM basak_platform_artifact WHERE run_id=%s AND artifact_id=%s',
                              (run_id, evidence.get('artifact_id', '')))
            observed = _read(artifact['data'], {}) if artifact else {}
            if (observed.get('kind') != 'external_observation' or observed.get('verified') is not True
                    or observed.get('call_id') != call_id or observed.get('arguments_digest') != action['digest']
                    or observed.get('result') != result or ok is not True):
                raise Conflict('Saglayicidan bagimsiz okunmus ve bu cagrinin hedefiyle eslesmis kanit gerekli')
            tx.execute("UPDATE basak_platform_action SET status='completed',result=%s,ok=%s WHERE run_id=%s AND call_id=%s", (_json(result), int(ok), run_id, call_id))
            self._event(tx, run_id, "reconciliation", {"call_id": call_id, "ok": ok, "evidence": evidence})
            if not tx.one("SELECT call_id FROM basak_platform_action WHERE run_id=%s AND status='uncertain'", (run_id,)):
                self._status(tx, row, "paused", "Dış işlem doğrulandı; devam kararı bekleniyor")

    def record_check(self, lease, check_id, ok, evidence):
        if type(ok) is not bool or not isinstance(evidence, dict) or not evidence:
            raise ValueError("Doğrulama gerçek gözlem referansı ve bool sonuç taşımalı")
        with self.transaction() as tx:
            self._lease(tx, lease)
            tx.execute("INSERT INTO basak_platform_check(run_id,check_id,ok,evidence,created_at) VALUES(%s,%s,%s,%s,%s) ON CONFLICT(run_id,check_id) DO UPDATE SET ok=excluded.ok,evidence=excluded.evidence,created_at=excluded.created_at", (lease.run_id, _key(check_id, "check_id"), int(ok), _json(evidence), self.clock()))
            self._event(tx, lease.run_id, "check", {"id": check_id, "ok": ok, "evidence": evidence})

    def add_artifact(self, user_id, run_id, artifact):
        item = dict(artifact)
        legacy_media = item.pop('mime_type', None)
        item['media_type'] = item.get('media_type') or legacy_media or 'application/octet-stream'
        aid = _key(item.pop("id", None) or uuid.uuid4().hex, "artifact_id")
        if "content" in item:
            data = str(item["content"]).encode("utf-8")
        elif "data_base64" in item:
            data = base64.b64decode(item["data_base64"], validate=True)
        else:
            data = None
        if data is not None:
            actual = hashlib.sha256(data).hexdigest()
            if item.get("sha256") and item["sha256"] != actual:
                raise ValueError("Çıktı özeti içeriğe uymuyor")
            item.update(sha256=actual, size=len(data))
        with self.transaction() as tx:
            self._require(tx, user_id, run_id)
            old = tx.one("SELECT data FROM basak_platform_artifact WHERE run_id=%s AND artifact_id=%s", (run_id, aid))
            if old and old["data"] != _json(item):
                raise Conflict("Çıktı kimliği farklı içerikle kullanıldı")
            tx.execute("INSERT INTO basak_platform_artifact(run_id,artifact_id,data) VALUES(%s,%s,%s) ON CONFLICT(run_id,artifact_id) DO NOTHING", (run_id, aid, _json(item)))
            self._event(tx, run_id, "artifact", {"id": aid, "kind": item.get("kind"), "title": item.get("title", "")})
        return aid

    def artifact(self, user_id, run_id, artifact_id):
        with self.transaction() as tx:
            self._require(tx, user_id, run_id)
            found = tx.one("SELECT data FROM basak_platform_artifact WHERE run_id=%s AND artifact_id=%s", (run_id, artifact_id))
            if not found:
                raise NotFound("Çıktı bulunamadı")
            return _read(found["data"], {})

    def _otomatik_durum(self, tx, row, answer):
        """Kabul kosullari ve alt gorevlere gore nihai durumu hesaplar.

        `finish` ve `_recover` ayni kurali kullanir: bir ust gorev, alt
        gorevleri hala calisirken biterse `verifying`te kalir; cocuklar
        kapandiginda yeniden degerlendirilmeden sonsuza kadar orada
        kalirdi.
        """
        required = {c["id"] for c in _read(row["spec"], {}).get("acceptance", [])}
        checks = {r["check_id"]: bool(r["ok"]) for r in tx.rows(
            "SELECT check_id,ok FROM basak_platform_check WHERE run_id=%s", (row["id"],))}
        actions = tx.rows("SELECT status,ok FROM basak_platform_action WHERE run_id=%s",
                          (row["id"],))
        children = tx.rows("SELECT r.durum FROM basak_platform_run m "
                           "JOIN basak_kosu r ON r.id=m.run_id WHERE m.parent_id=%s",
                           (row["id"],))
        if any(a["status"] == "uncertain" for a in actions):
            return "uncertain"
        if any(a["status"] != "completed" for a in actions):
            return "verifying"
        if (any(not a["ok"] for a in actions)
                or any(not value for value in checks.values())
                or any(c["durum"] in SETTLED - {"completed"} for c in children)):
            return "partial"
        if children and any(c["durum"] != "completed" for c in children):
            return "verifying"
        if answer and required and required.issubset(checks) and all(
                checks[x] for x in required):
            return "completed"
        return "verifying"

    def finish(self, lease, outcome):
        with self.transaction() as tx:
            row = self._lease(tx, lease)
            requested = outcome.get("status")
            answer = str(outcome.get("answer") or "")
            tx.execute("UPDATE basak_kosu SET cevap=%s WHERE id=%s", (answer, lease.run_id))
            actions = tx.rows("SELECT status,ok,side_effect FROM basak_platform_action WHERE run_id=%s", (lease.run_id,))
            if any(a["status"] == "uncertain" or (a["status"] == "running" and a["side_effect"]) for a in actions):
                tx.execute("UPDATE basak_platform_action SET status='uncertain' WHERE run_id=%s AND status='running' AND side_effect=1", (lease.run_id,))
                state = "uncertain"
            elif requested in {"awaiting_connection", "blocked", "paused", "failed", "partial"}:
                state = requested
            else:
                state = self._otomatik_durum(tx, row, answer)
            self._status(tx, row, state, str(outcome.get("reason") or ""))
            return self._project(tx, self._require(tx, lease.user_id, lease.run_id))

    def steer(self, user_id, run_id, text):
        text = str(text or "").strip()
        if not text:
            raise ValueError("Yönlendirme metni gerekli")
        with self.transaction() as tx:
            row = self._require(tx, user_id, run_id)
            if row["durum"] in TERMINAL:
                raise Conflict("Kapalı göreve yön verilemez")
            sid = uuid.uuid4().hex
            position = self._event(tx, run_id, "steering", {"id": sid, "text": text})
            tx.execute("INSERT INTO basak_platform_steering(id,run_id,text,created_at,position) VALUES(%s,%s,%s,%s,%s)", (sid, run_id, text, self.clock(), position))
            return position

    def drain_steering(self, lease):
        with self.transaction() as tx:
            row = self._lease(tx, lease)
            rows = tx.rows("SELECT id,text,created_at FROM basak_platform_steering WHERE run_id=%s AND consumed=0 ORDER BY position,created_at,id", (lease.run_id,))
            if rows:
                continuation = _read(row["continuation"], {})
                continuation.setdefault("steering_messages", []).extend(rows)
                tx.execute("UPDATE basak_platform_run SET continuation=%s WHERE run_id=%s", (_json(continuation), lease.run_id))
            tx.execute("UPDATE basak_platform_steering SET consumed=1 WHERE run_id=%s AND consumed=0", (lease.run_id,))
            return rows

    def accept(self, user_id, run_id, check_id="result_verified", accepted=True):
        """Authenticated human review is distinct from permission to act."""
        if type(accepted) is not bool:
            raise ValueError("Kabul bool olmalı")
        with self.transaction() as tx:
            row = self._require(tx, user_id, run_id)
            if row["durum"] not in {"verifying", "partial"}:
                raise Conflict("Görev insan incelemesi beklemiyor")
            spec = _read(row["spec"], {})
            criterion = next((c for c in spec.get("acceptance", []) if c["id"] == check_id), None)
            if criterion is None or criterion.get("kind", "human") not in {"human", "user_acceptance"}:
                raise Conflict("Makine kontrolü kullanıcı kabulüyle atlanamaz")
            evidence = {"reviewer": user_id, "kind": "user_acceptance", "accepted": accepted}
            tx.execute("INSERT INTO basak_platform_check(run_id,check_id,ok,evidence,created_at) VALUES(%s,%s,%s,%s,%s) ON CONFLICT(run_id,check_id) DO UPDATE SET ok=excluded.ok,evidence=excluded.evidence,created_at=excluded.created_at", (run_id, check_id, int(accepted), _json(evidence), self.clock()))
            self._event(tx, run_id, "check", {"id": check_id, "ok": accepted, "evidence": evidence})
            required = {c["id"] for c in spec.get("acceptance", [])}
            checks = {r["check_id"]: bool(r["ok"]) for r in tx.rows("SELECT check_id,ok FROM basak_platform_check WHERE run_id=%s", (run_id,))}
            incomplete_child = tx.one("SELECT r.id FROM basak_platform_run m JOIN basak_kosu r ON r.id=m.run_id WHERE m.parent_id=%s AND r.durum<>'completed'", (run_id,))
            bad_action = tx.one("SELECT call_id FROM basak_platform_action WHERE run_id=%s AND (status<>'completed' OR ok=0)", (run_id,))
            if accepted and row.get("cevap") and required.issubset(checks) and all(checks.values()) and not incomplete_child and not bad_action:
                state = "completed"
            else:
                state = "verifying" if accepted else "partial"
            self._status(tx, row, state)
            return self._project(tx, self._require(tx, user_id, run_id))

    def cancel(self, user_id, run_id):
        with self.transaction() as tx:
            self._require(tx, user_id, run_id)
            pending = [run_id]
            while pending:
                rid = pending.pop(0)
                row = self._require(tx, user_id, rid)
                pending.extend(x["run_id"] for x in tx.rows("SELECT run_id FROM basak_platform_run WHERE parent_id=%s AND user_id=%s", (rid, user_id)))
                if row["durum"] in TERMINAL:
                    continue
                effect = tx.one("SELECT call_id FROM basak_platform_action WHERE run_id=%s AND status='running' AND side_effect=1", (rid,))
                if effect:
                    tx.execute("UPDATE basak_platform_action SET status='uncertain' WHERE run_id=%s AND status='running' AND side_effect=1", (rid,))
                self._status(tx, row, "uncertain" if effect else "cancelled", "Kullanıcı iptal etti")
            return self._project(tx, self._require(tx, user_id, run_id))

    def resume(self, user_id, run_id):
        with self.transaction() as tx:
            row = self._require(tx, user_id, run_id)
            if row["durum"] not in {"paused", "blocked", "awaiting_connection", "verifying", "partial", "failed"}:
                raise Conflict("Görev bu durumda güvenle sürdürülemez")
            if tx.one("SELECT call_id FROM basak_platform_action WHERE run_id=%s AND status='uncertain'", (run_id,)):
                raise Conflict("Dış işlemin sonucu önce doğrulanmalı")
            tx.execute("UPDATE basak_platform_action SET status='retryable' WHERE run_id=%s AND side_effect=0 AND (status='running' OR (status='completed' AND ok=0))", (run_id,))
            self._status(tx, row, "queued")
            return self._project(tx, self._require(tx, user_id, run_id))

    def wait_for_children(self, lease, child_ids):
        child_ids = list(dict.fromkeys(child_ids))
        if not child_ids:
            raise ValueError("Alt görev kimlikleri gerekli")
        with self.transaction() as tx:
            row = self._lease(tx, lease)
            for rid in child_ids:
                child = self._require(tx, lease.user_id, rid)
                if child["parent_id"] != lease.run_id:
                    raise Conflict("Beklenen görev doğrudan alt görev değil")
            tx.execute("UPDATE basak_platform_run SET waiting=%s WHERE run_id=%s", (_json(child_ids), lease.run_id))
            self._status(tx, row, "waiting_children")

    def request_approval(self, lease, action, resource, arguments):
        with self.transaction() as tx:
            row = self._lease(tx, lease)
            aid = uuid.uuid4().hex
            data = {"id": aid, "action": str(action), "resource": str(resource),
                    "arguments_digest": _hash(arguments), "status": "pending",
                    "preview": _approval_preview(action, resource, arguments)}
            tx.execute("INSERT INTO basak_platform_approval"
                       "(id,run_id,action,resource,arguments_digest,status,created_at,preview) "
                       "VALUES(%s,%s,%s,%s,%s,'pending',%s,%s)",
                       (aid, lease.run_id, action, resource,
                        data["arguments_digest"], self.clock(), _json(data["preview"])))
            self._event(tx, lease.run_id, "approval", data)
            self._status(tx, row, "awaiting_approval")
            return data

    def approve(self, user_id, run_id, approval_id, approved):
        if type(approved) is not bool:
            raise ValueError("Onay bool olmalı")
        with self.transaction() as tx:
            row = self._require(tx, user_id, run_id)
            approval = tx.one("SELECT * FROM basak_platform_approval WHERE id=%s AND run_id=%s", (approval_id, run_id))
            if not approval:
                raise NotFound("Onay bulunamadı")
            if approval["status"] != "pending":
                raise Conflict("Bu onay zaten işlendi")
            state = "approved" if approved else "rejected"
            tx.execute("UPDATE basak_platform_approval SET status=%s WHERE id=%s", (state, approval_id))
            self._event(tx, run_id, "approval", {"id": approval_id, "status": state})
            if row["durum"] == "awaiting_approval":
                self._status(tx, row, "queued" if approved else "blocked", "" if approved else "İşlem onayı reddedildi")
            return self._project(tx, self._require(tx, user_id, run_id))

    def consume_approval(self, lease, action, resource, arguments):
        with self.transaction() as tx:
            self._lease(tx, lease)
            row = tx.one("SELECT id FROM basak_platform_approval WHERE run_id=%s AND action=%s AND resource=%s AND arguments_digest=%s AND status='approved' ORDER BY created_at,id", (lease.run_id, action, resource, _hash(arguments)))
            if not row:
                return False
            tx.execute("UPDATE basak_platform_approval SET status='consumed' WHERE id=%s", (row["id"],))
            return True


class Control:
    """Fenced handle given to a running Python-core adapter."""
    def __init__(self, store, lease):
        self.store, self.lease = store, lease

    def check_cancelled(self):
        with self.store.transaction(readonly=True) as tx:
            row = self.store._require(tx, self.lease.user_id, self.lease.run_id)
            if row["durum"] in {"cancelled", "uncertain"}:
                raise RunCancelled()
            self.store._lease(tx, self.lease, row=row)

    def event(self, type_, payload=None, **kwargs):
        return self.store.append_event(self.lease.user_id, self.lease.run_id, type_,
                                       {**(payload or {}), **kwargs}, lease=self.lease)

    def checkpoint(self, continuation):
        return self.store.checkpoint(self.lease, continuation)

    def drain_steering(self):
        return self.store.drain_steering(self.lease)

    def begin_action(self, call_id, tool, args, side_effect=False):
        return self.store.begin_action(self.lease, call_id, tool, args, side_effect)

    def finish_action(self, call_id, result, ok):
        return self.store.finish_action(self.lease, call_id, result, ok)

    def record_check(self, check_id, ok, evidence):
        return self.store.record_check(self.lease, check_id, ok, evidence)

    def artifact(self, kind, title="", uri="", **metadata):
        self.check_cancelled()
        return self.store.add_artifact(self.lease.user_id, self.lease.run_id,
                                       {"kind": kind, "title": title, "uri": uri, **metadata})

    def wait_for_children(self, child_ids):
        self.store.wait_for_children(self.lease, child_ids)
        raise RunSuspended()

    def request_approval(self, action, resource, arguments):
        self.store.request_approval(self.lease, action, resource, arguments)
        raise RunSuspended()


class Worker:
    """A durable worker; the handler is the existing Python brain adapter."""
    def __init__(self, store, handler, *, worker_id=None, lease_seconds=60):
        self.store, self.handler = store, handler
        self.worker_id = worker_id or ("platform-" + uuid.uuid4().hex[:12])
        self.lease_seconds = lease_seconds

    def tick(self, run_id=None):
        from worker.platform_browser import release_finished_sessions
        release_finished_sessions(self.store)
        job = self.store.claim(self.worker_id, self.lease_seconds, run_id)
        if job is None:
            return False
        control, stopped = Control(self.store, job["lease"]), threading.Event()
        lost = threading.Event()

        def renew():
            while not stopped.wait(max(0.1, self.lease_seconds / 3)):
                try:
                    self.store.heartbeat(job["lease"], self.lease_seconds)
                except (LeaseLost, NotFound):
                    lost.set()
                    return

        heartbeat = threading.Thread(target=renew, daemon=True)
        heartbeat.start()
        try:
            result = self.handler(job, control)
            if lost.is_set():
                raise LeaseLost("İşçi görevin yürütme yetkisini kaybetti")
            self.store.finish(job["lease"], result or {})
        except (RunSuspended, RunCancelled, LeaseLost) as exc:
            logger.debug("platform iscisi turu durdu: %s", type(exc).__name__)
        except Exception as exc:
            try:
                self.store.finish(job["lease"], {"status": "failed", "reason": str(exc)})
            except LeaseLost:
                logger.debug("platform iscisi finish lease kaybetti", exc_info=True)
        finally:
            stopped.set()
            heartbeat.join(timeout=2)
            release_finished_sessions(self.store)
        return True
