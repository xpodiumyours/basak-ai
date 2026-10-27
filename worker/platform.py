"""Persistent task worker: ``python -m worker.platform``.

Runs outside the web request lifecycle. The handler is the same Python agent
adapter used by the application's subagent tools; no independent model router.
"""
import argparse
import logging
import signal
import threading

from chat.platform_runtime import RuntimeStore, Worker


def main(argv=None):
    parser = argparse.ArgumentParser(description="Başak kalıcı görev işçisi")
    parser.add_argument("--once", action="store_true", help="En fazla bir görevi işle")
    parser.add_argument("--worker-id", default=None)
    parser.add_argument("--poll-seconds", type=float, default=1)
    parser.add_argument("--lease-seconds", type=float, default=60)
    parser.add_argument("--allow-local-sqlite", action="store_true",
                        help="Yalniz yerel test: web sitesiyle ortak veritabanini kullanmaz")
    args = parser.parse_args(argv)
    if args.poll_seconds <= 0 or args.lease_seconds <= 0:
        parser.error("Bekleme ve lease süreleri pozitif olmalı")
    from chat.kosu_deposu import _dsn
    if not _dsn() and not args.allow_local_sqlite:
        parser.error("Kalici bulut iscisi icin ortak DATABASE_URL gerekli; "
                     "yerel SQLite yalniz --allow-local-sqlite ile test edilir")
    logging.basicConfig(level=logging.INFO)
    from chat.platform_agents import execute_job
    store = RuntimeStore()
    worker = Worker(store, execute_job, worker_id=args.worker_id,
                    lease_seconds=args.lease_seconds)
    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())
    while not stop.is_set():
        worked = worker.tick()
        if args.once:
            return 0
        if not worked:
            stop.wait(args.poll_seconds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
