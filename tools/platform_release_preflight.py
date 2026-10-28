"""Read-only release preflight for the existing Başak platform.

This is an *automated prerequisite*, not production acceptance. It never
creates tables, starts workers, changes settings, or prints secrets.
Real browser/login/child-agent/restart acceptance remains mandatory.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import time
from urllib.parse import urlsplit

REQUIRED_TABLES = (
    "basak_kosu",
    "basak_kosu_adim",
    "basak_platform_run",
    "basak_platform_chat_route",
    "basak_platform_dependency",
    "basak_platform_event",
    "basak_platform_action",
    "basak_platform_check",
    "basak_platform_artifact",
    "basak_platform_steering",
    "basak_platform_approval",
    "basak_platform_worker_presence",
    "basak_platform_workspace_file",
    "basak_connection",
    "basak_oauth_attempt",
    "basak_account",
    "basak_account_session",
)


def _target(dsn):
    """Compare host/database only; never expose credentials."""
    try:
        parsed = urlsplit(dsn or "")
        if parsed.scheme not in {"postgresql", "postgres"} or not parsed.hostname:
            return None
        return (parsed.hostname.lower(), parsed.port, parsed.path)
    except ValueError:
        return None


def _valid_key(raw):
    try:
        return len(base64.urlsafe_b64decode((raw or "").strip())) == 32
    except (ValueError, TypeError):
        return False


def _public_https(raw):
    try:
        url = urlsplit(raw or "")
        return bool(url.scheme == "https" and url.hostname and
                    not url.username and not url.password and
                    not url.query and not url.fragment and
                    url.path in {"", "/"})
    except ValueError:
        return False


def inspect(environment, role, env=None, connect=None, now=None):
    """Return secret-free checks; all SQL is SELECT on read-only connection."""
    if environment not in {"preview", "production"}:
        raise ValueError("Unsupported environment")
    if role not in {"web", "worker"}:
        raise ValueError("Unsupported role")
    env = os.environ if env is None else env
    now = time.time() if now is None else now
    checks = []

    def add(name, ok, detail):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    dsn_name = ("BASAK_PREVIEW_DATABASE_URL" if environment == "preview"
                else "DATABASE_URL")
    dsn = (env.get(dsn_name) or "").strip()
    add("database_target", bool(_target(dsn)), "Explicit PostgreSQL URL required")

    if environment == "preview":
        other_targets = [env.get(x) for x in (
            "DATABASE_URL", "POSTGRES_URL", "NEON_DATABASE_URL",
            "BASAK_ISCI_DATABASE_URL") if env.get(x)]
        distinct = _target(dsn) is not None and all(
            _target(dsn) != _target(other) for other in other_targets)
        add("preview_isolation", distinct,
            "Preview must not point at a configured production database")
    elif env.get("BASAK_PREVIEW_DATABASE_URL"):
        add("production_isolation",
            _target(dsn) != _target(env["BASAK_PREVIEW_DATABASE_URL"]),
            "Production must not point at Preview")

    add("connection_encryption", _valid_key(env.get("BASAK_CONNECTION_KEY")),
        "Valid 32-byte URL-safe base64 key required")

    if role == "web":
        add("public_https", _public_https(env.get("BASAK_PUBLIC_URL")),
            "Canonical HTTPS base URL required")
        add("session_key", bool((env.get("BASAK_OTURUM_ANAHTARI") or "").strip()),
            "Persistent web session signing key required")
        oauth = any(bool(env.get("BASAK_" + p + "_CLIENT_ID")) and
                    bool(env.get("BASAK_" + p + "_CLIENT_SECRET"))
                    for p in ("GOOGLE", "GITHUB"))
        add("login_provider", oauth,
            "At least one complete Google or GitHub OAuth client required")
        add("durable_chat_enabled",
            (env.get("BASAK_DURABLE_CHAT_ENABLED") or "").lower() == "true",
            "Durable chat must be explicitly enabled after worker acceptance")

    if not _target(dsn):
        add("database_schema", False, "Database not inspected")
        add("worker_heartbeat", False, "Worker presence not inspected")
    else:
        try:
            if connect is None:
                import psycopg
                connect = psycopg.connect
            # Server-enforced read-only transactions, independent of SQL text.
            with connect(dsn, connect_timeout=5,
                         options="-c default_transaction_read_only=on") as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT " + ",".join(
                            "to_regclass('public." + t + "')"
                            for t in REQUIRED_TABLES))
                    present = cursor.fetchone()
                    schema_ok = bool(present and all(present))
                    add("database_schema", schema_ok,
                        "Required platform/account tables must exist")
                    if schema_ok:
                        cursor.execute(
                            "SELECT count(*) FROM basak_platform_worker_presence "
                            "WHERE state='online' AND seen_at >= %s",
                            (now - 30,))
                        row = cursor.fetchone()
                        live = bool(row and row[0] > 0)
                        add("worker_heartbeat", live,
                            "At least one real heartbeat in last 30 seconds")
                    else:
                        add("worker_heartbeat", False,
                            "Worker heartbeat unavailable until schema exists")
        except Exception:
            add("database_schema", False, "Database read-only check failed")
            add("worker_heartbeat", False,
                "No authenticated recent worker heartbeat confirmed")

    return {
        "environment": environment,
        "role": role,
        "automated_preflight_passed": all(x["ok"] for x in checks),
        "checks": checks,
        "manual_acceptance_required": [
            "real account login/logout and session persistence",
            "real subagent + Chromium + artifact outcome",
            "refresh, worker restart, idempotency and approval behavior",
            "verified Preview/Production database separation and rollback",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only Başak release gate")
    parser.add_argument("--environment", choices=["preview", "production"],
                        required=True)
    parser.add_argument("--role", choices=["web", "worker"], required=True)
    args = parser.parse_args(argv)
    result = inspect(args.environment, args.role)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["automated_preflight_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
