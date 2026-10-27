"""No real credentials or infrastructure: verify the release preflight's contract."""
import base64
import json

from tools.platform_release_preflight import REQUIRED_TABLES, inspect


class FakeCursor:
    def __init__(self, *, schema=True, live=1):
        self.schema, self.live = schema, live
        self.query, self.params = "", None
        self.queries = []

    def execute(self, query, params=None):
        self.query, self.params = query, params
        self.queries.append(query)

    def fetchone(self):
        if "to_regclass" in self.query:
            return tuple("public.table" if self.schema else None for _ in REQUIRED_TABLES)
        return (self.live,)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def fake_db(cursor):
    calls = []

    def connect(dsn, **kwargs):
        calls.append((dsn, kwargs))
        return FakeConnection(cursor)
    return connect, calls


def env_for(environment="preview", role="worker"):
    key = base64.urlsafe_b64encode(b"x" * 32).decode()
    env = {"BASAK_CONNECTION_KEY": key}
    if environment == "preview":
        env["BASAK_PREVIEW_DATABASE_URL"] = "postgresql://test:fake@preview.local/test"
        env["DATABASE_URL"] = "postgresql://test:fake@prod.local/test"
    else:
        env["DATABASE_URL"] = "postgresql://test:fake@prod.local/test"
        env["BASAK_PREVIEW_DATABASE_URL"] = "postgresql://test:fake@preview.local/test"
    if role == "web":
        env.update({
            "BASAK_PUBLIC_URL": "https://basak.example",
            "BASAK_OTURUM_ANAHTARI": "synthetic-session-test-key",
            "BASAK_GITHUB_CLIENT_ID": "test-client",
            "BASAK_GITHUB_CLIENT_SECRET": "synthetic-test-secret",
            "BASAK_DURABLE_CHAT_ENABLED": "true",
        })
    return env


def failures(result):
    return {check["name"] for check in result["checks"] if not check["ok"]}


def test_preflight_rejects_missing_configuration_without_db_access():
    def forbidden(*_args, **_kwargs):
        raise AssertionError("missing DSN must not trigger connection")
    result = inspect("production", "web", env={}, connect=forbidden, now=100)
    assert result["automated_preflight_passed"] is False
    assert {"database_target", "database_schema", "worker_heartbeat",
            "public_https", "session_key", "login_provider",
            "durable_chat_enabled", "connection_encryption"} <= failures(result)


def test_preview_worker_preflight_is_read_only_and_reports_worker():
    cursor = FakeCursor()
    connector, calls = fake_db(cursor)
    result = inspect("preview", "worker", env=env_for(), connect=connector, now=100)
    assert result["automated_preflight_passed"]
    assert len(calls) == 1
    assert calls[0][1]["options"] == "-c default_transaction_read_only=on"
    assert all(query.strip().upper().startswith("SELECT") for query in cursor.queries)
    assert cursor.params == (70,)
    assert result["manual_acceptance_required"]


def test_preview_cannot_use_same_target_as_production():
    env = env_for()
    env["BASAK_PREVIEW_DATABASE_URL"] = env["DATABASE_URL"]
    connector, _ = fake_db(FakeCursor())
    result = inspect("preview", "worker", env=env, connect=connector, now=100)
    assert "preview_isolation" in failures(result)


def test_production_web_needs_login_and_durable_flag():
    env = env_for("production", "web")
    env.pop("BASAK_GITHUB_CLIENT_SECRET")
    env["BASAK_DURABLE_CHAT_ENABLED"] = "false"
    connector, _ = fake_db(FakeCursor())
    result = inspect("production", "web", env=env, connect=connector, now=100)
    assert {"login_provider", "durable_chat_enabled"} <= failures(result)


def test_worker_absence_does_not_count_as_release_success():
    connector, _ = fake_db(FakeCursor(live=0))
    result = inspect("production", "worker",
                     env=env_for("production"), connect=connector, now=100)
    assert "worker_heartbeat" in failures(result)


def test_schema_absence_blocks_worker_check():
    cursor = FakeCursor(schema=False)
    connector, _ = fake_db(cursor)
    result = inspect("preview", "worker", env=env_for(), connect=connector, now=100)
    assert {"database_schema", "worker_heartbeat"} <= failures(result)
    assert len(cursor.queries) == 1


def test_report_never_leaks_connection_secrets():
    env = env_for("production", "web")
    connector, _ = fake_db(FakeCursor())
    result = inspect("production", "web", env=env, connect=connector, now=100)
    report = json.dumps(result)
    for secret in ("synthetic-test-secret", "synthetic-session-test-key",
                   "test:fake", env["BASAK_CONNECTION_KEY"]):
        assert secret not in report
