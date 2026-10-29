"""PostgreSQL-only acceptance: real transactions across independent worker stores.

Runs only against an ephemeral, LOCAL database named basak_platform_ci.
No OAuth credentials, model calls or remote services are used.
"""
import concurrent.futures
import os
import uuid
from urllib.parse import urlsplit

import pytest

from chat import kosu_deposu
from chat.platform_runtime import Conflict, RuntimeStore


@pytest.fixture(scope="module")
def postgres_url():
    url = os.environ.get("BASAK_TEST_POSTGRES_URL", "")
    if not url:
        pytest.skip("Isolated PostgreSQL CI service not configured")
    parsed = urlsplit(url)
    if (parsed.scheme not in ("postgres", "postgresql")
            or parsed.hostname not in ("localhost", "127.0.0.1", "::1")
            or parsed.path != "/basak_platform_ci"):
        pytest.fail("PostgreSQL acceptance tests require local basak_platform_ci; refusing external DB")
    return url


def new_store(url, *, clock=None):
    return RuntimeStore(kosu_deposu._PostgresDepo(url), clock=clock)


def test_identity_schema_and_legacy_queries_return_connections_to_pool(postgres_url):
    """Identity setup executes more statements than the pool's capacity."""
    from chat.platform_connections import ConnectionStore
    db = kosu_deposu._PostgresDepo(postgres_url)
    db._pool.timeout = 0.2
    try:
        ConnectionStore(db)
        for _ in range(12):
            assert db._sorgu('SELECT 1 AS value')[0]['value'] == 1
            db._calistir('SELECT 1')
        assert db._pool.get_stats()['requests_waiting'] == 0
    finally:
        db.close()


def new_user():
    return "pg-ci-" + uuid.uuid4().hex


def test_ledger_reuses_connection_and_rolls_back_before_reuse(postgres_url):
    store = new_store(postgres_url)
    pids = []
    with store.transaction(readonly=True) as tx:
        pids.append(tx.one('SELECT pg_backend_pid() AS pid')['pid'])
    with pytest.raises(RuntimeError, match='rollback probe'):
        with store.transaction() as tx:
            pids.append(tx.one('SELECT pg_backend_pid() AS pid')['pid'])
            tx.execute('CREATE TEMP TABLE rollback_probe(value INTEGER)')
            raise RuntimeError('rollback probe')
    # A pool may alternate between several healthy connections. Check reuse
    # and rollback across enough checkouts to revisit every pooled connection.
    for _ in range(12):
        with store.transaction(readonly=True) as tx:
            pids.append(tx.one('SELECT pg_backend_pid() AS pid')['pid'])
            assert tx.one("SELECT to_regclass('pg_temp.rollback_probe') AS relation")['relation'] is None
    assert len(set(pids)) <= store.depo._pool.max_size
    assert len(set(pids)) < len(pids)
    store.depo.close()


def test_stale_pooled_connection_is_replaced_before_query(postgres_url):
    store = new_store(postgres_url)
    # Simulate an idle socket closed by the server, without replaying a write.
    conn = store.depo._baglan()
    stale = conn.info.backend_pid
    conn.pgconn.finish()
    conn.close()
    for _ in range(12):
        with store.transaction(readonly=True) as tx:
            assert tx.one('SELECT pg_backend_pid() AS pid')['pid'] != stale
    store.depo.close()


def test_three_siblings_claim_across_independent_postgres_workers(postgres_url):
    coordinator = new_store(postgres_url)
    user = new_user()
    parent = coordinator.create(user, "ci", "Delegate the work")
    children = [
        coordinator.create(user, "ci", "Independent work " + str(i),
                           parent_id=parent["id"])
        for i in range(4)
    ]
    parent_lease = coordinator.claim("orchestrator", run_id=parent["id"])["lease"]
    coordinator.wait_for_children(parent_lease, [child["id"] for child in children])

    # Each RuntimeStore has its own depo and database connections, like real workers.
    stores = [new_store(postgres_url) for _ in range(4)]

    def claim(index):
        return stores[index].claim("worker-" + str(index), run_id=children[index]["id"])

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        jobs = list(pool.map(claim, range(3)))

    assert [job["id"] for job in jobs] == [child["id"] for child in children[:3]]
    assert claim(3) is None
    assert coordinator.get(user, children[3]["id"])["durum"] == "queued"

    # Completing one sibling frees precisely one slot for the queued fourth.
    coordinator.record_check(jobs[0]["lease"], "result_verified", True, {"ci": True})
    coordinator.finish(jobs[0]["lease"], {"answer": "verified"})
    fourth = claim(3)
    assert fourth is not None and fourth["id"] == children[3]["id"]


def test_request_idempotency_is_atomic_across_postgres_connections(postgres_url):
    stores = [new_store(postgres_url) for _ in range(6)]
    user = new_user()

    def submit(index):
        return stores[index].create(
            user, "ci", "One submission", request_key="same-operation"
        )["id"]

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        ids = list(pool.map(submit, range(6)))

    assert len(set(ids)) == 1
    with pytest.raises(Conflict):
        stores[0].create(user, "ci", "Changed submission",
                         request_key="same-operation")


def test_uncertain_external_effect_is_never_replayed_by_second_postgres_worker(postgres_url):
    user = new_user()
    first = new_store(postgres_url, clock=lambda: 100.0)
    second = new_store(postgres_url, clock=lambda: 106.0)
    run = first.create(user, "ci", "Perform a sensitive write")
    lease = first.claim("worker-before-restart", run_id=run["id"],
                        lease_seconds=5)["lease"]
    first.begin_action(lease, "call-1", "external_write", {"value": 1},
                       side_effect=True)

    assert second.claim("worker-after-restart", run_id=run["id"]) is None
    assert second.get(user, run["id"])["durum"] == "uncertain"


def test_idle_worker_heartbeat_visible_to_independent_postgres_store(postgres_url):
    """A worker that has not claimed a job must still be observable."""
    first = new_store(postgres_url)
    observer = new_store(postgres_url)
    worker_id = "pg-ci-worker-" + uuid.uuid4().hex
    first.worker_ping(worker_id)
    health = observer.worker_health()
    assert health["online"] is True and health["live_workers"] >= 1
    assert health["last_seen_age_seconds"] is not None
    first.worker_stopped(worker_id)
    # Other CI workers can exist in the same test DB; inspect exact row.
    with observer.transaction() as tx:
        row = tx.one("SELECT state FROM basak_platform_worker_presence "
                     "WHERE worker_id=%s", (worker_id,))
    assert row["state"] == "offline"


def test_root_lifetime_budget_is_atomic_across_postgres_connections(postgres_url):
    coordinator = new_store(postgres_url)
    user = new_user()
    root = coordinator.create(user, 'ci', 'bounded delegation')
    parents = [coordinator.create(user, 'ci', 'delegate', parent_id=root['id']) for _ in range(2)]
    stores = [new_store(postgres_url) for _ in range(6)]
    for store in stores:
        store.max_descendants_per_root = 4
    def create(index):
        try:
            return stores[index].create(user, 'ci', 'nested', parent_id=parents[index % 2]['id'])['id']
        except Conflict:
            return None
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(create, range(6)))
    assert len([result for result in results if result]) == 2
    assert sum(len(child['children']) for child in coordinator.tree(user, root['id'])['children']) == 2
