"""Persistent task worker: ``python -m worker.platform``.

Runs outside the web request lifecycle. The handler is the same Python agent
adapter used by the application's subagent tools; no independent model router.
"""
import argparse
import logging
import signal
import threading
import uuid

from chat.platform_runtime import RuntimeStore, Worker


def main(argv=None):
    parser = argparse.ArgumentParser(description="Başak kalıcı görev işçisi")
    parser.add_argument("--once", action="store_true", help="En fazla bir görevi işle")
    parser.add_argument("--worker-id", default=None)
    parser.add_argument("--poll-seconds", type=float, default=1)
    parser.add_argument("--lease-seconds", type=float, default=60)
    parser.add_argument('--concurrency', type=int, default=3,
                        help='Ayni surecte gercekten calisan gorev yuvalari')
    parser.add_argument("--allow-local-sqlite", action="store_true",
                        help="Yalniz yerel test: web sitesiyle ortak veritabanini kullanmaz")
    args = parser.parse_args(argv)
    if args.poll_seconds <= 0 or args.lease_seconds <= 0 or args.concurrency < 1:
        parser.error("Bekleme ve lease süreleri pozitif olmalı")
    from chat.kosu_deposu import _dsn
    if not _dsn() and not args.allow_local_sqlite:
        parser.error("Kalici bulut iscisi icin ortak DATABASE_URL gerekli; "
                     "yerel SQLite yalniz --allow-local-sqlite ile test edilir")
    logging.basicConfig(level=logging.INFO)
    from chat.platform_agents import execute_job
    store = RuntimeStore()
    identity = args.worker_id or ('platform-' + uuid.uuid4().hex[:12])
    worker = Worker(store, execute_job, worker_id=identity,
                    lease_seconds=args.lease_seconds)
    workers = [worker]
    if not args.once:
        workers.extend(Worker(store, execute_job, worker_id=identity + '-' + str(i),
                              lease_seconds=args.lease_seconds) for i in range(1, args.concurrency))
    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())

    # Process presence is distinct from the per-job lease heartbeat. Even
    # while handling a long job, an active worker must remain observable.
    def report_presence():
        while not stop.is_set():
            try:
                for active in workers:
                    store.worker_ping(active.worker_id)
            except Exception:
                logging.exception("Ajan isci kalp atisi yazilamadi")
            stop.wait(10)

    presence = threading.Thread(target=report_presence, daemon=True,
                                name="basak-agent-presence")
    presence.start()
    def consume(active):
        while not stop.is_set():
            try:
                worked = active.tick()
            except Exception:
                logging.exception('Ajan kuyrugu okunamadi')
                worked = False
            if not worked:
                stop.wait(args.poll_seconds)

    threads = [threading.Thread(target=consume, args=(active,),
                                name='basak-task-' + str(i)) for i, active in enumerate(workers[1:])]
    for thread in threads:
        thread.start()
    try:
        if args.once:
            worker.tick()
        else:
            consume(worker)
    finally:
        stop.set()
        for thread in threads:
            thread.join()
        presence.join(timeout=3)
        try:
            for active in workers:
                store.worker_stopped(active.worker_id)
        except Exception:
            logging.exception("Ajan isci kapanisi kaydedilemedi")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
