"""Durable platform behavior; tests use real SQLite transactions and threads."""
import concurrent.futures

import pytest

from chat import kosu_deposu
from chat.platform_runtime import (
    Conflict, LeaseLost, NotFound, RuntimeStore, Worker,
)


@pytest.fixture
def store(tmp_path):
    return RuntimeStore(kosu_deposu._SqliteDepo(str(tmp_path / "runs.db")))


def create(store, user="alice", **kw):
    return store.create(user, "personal", "Do the actual task", **kw)


def test_chat_work_flag_uses_actions_and_children_not_message_text(store):
    run = create(store, kind='chat')
    answer_id = store.add_artifact('alice', run['id'], {'kind': 'answer', 'title': 'Basak sonucu', 'content': 'Merhaba'})
    assert answer_id != 'answer'
    assert store.tree('alice', run['id'])['has_work'] is False
    assert store.chat_threads('alice')[0]['runs'][0]['has_work'] is False
    create(store, parent_id=run['id'])
    assert store.tree('alice', run['id'])['has_work'] is True
    assert store.chat_threads('alice')[0]['runs'][0]['has_work'] is True


def test_chat_work_flag_records_real_tool_execution(store):
    run = create(store, kind='chat')
    lease = store.claim('worker')['lease']
    store.begin_action(lease, 'protocol', 'son_cevap', {})
    assert store.get('alice', run['id'])['has_work'] is False
    store.begin_action(lease, 'calculation', 'hesapla', {'ifade': '2+2'})
    assert store.get('alice', run['id'])['has_work'] is True


def test_tenant_isolation_in_every_read_and_mutation(store):
    run = create(store)
    for operation in (
        lambda: store.get("bob", run["id"]),
        lambda: store.tree("bob", run["id"]),
        lambda: store.events("bob", run["id"]),
        lambda: store.cancel("bob", run["id"]),
        lambda: store.steer("bob", run["id"], "change"),
    ):
        with pytest.raises(NotFound):
            operation()
    assert store.list("bob") == []


def test_events_are_fenced_at_the_same_transaction_that_writes_them(store):
    from chat.platform_runtime import Control, RunCancelled
    now=[1000.0]
    store.clock=lambda:now[0]
    run=create(store)
    old=store.claim('old',lease_seconds=10)['lease']
    now[0]+=11
    current=store.claim('new',lease_seconds=60)['lease']
    with pytest.raises(LeaseLost):
        store.append_event('alice',run['id'],'late',{'text':'stale output'},lease=old)
    assert not any(e['type']=='late' for e in store.events('alice',run['id']))
    Control(store,current).event('current',{'text':'full output'})
    assert store.events('alice',run['id'])[-1]['type']=='current'
    store.cancel('alice',run['id'])
    with pytest.raises(RunCancelled):
        Control(store,current).event('late',{'text':'after cancellation'})


def test_idempotent_submit_rejects_changed_payload(store):
    first = create(store, request_key="r1")
    assert create(store, request_key="r1")["id"] == first["id"]
    with pytest.raises(Conflict):
        store.create("alice", "personal", "different", request_key="r1")


def test_concurrent_claim_has_one_owner(store):
    run = create(store)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        leases = list(pool.map(lambda i: store.claim("w%d" % i), range(8)))
    assert sum(x is not None for x in leases) == 1
    assert next(x for x in leases if x)["id"] == run["id"]


def test_restart_retains_events_and_continuation(store):
    run = create(store)
    job = store.claim("w1")
    store.checkpoint(job["lease"], {"messages": [{"role": "tool", "content": "done"}]})
    store.steer("alice", run["id"], "one")
    store.steer("alice", run["id"], "two")
    reopened = RuntimeStore(store.depo)
    assert reopened.get("alice", run["id"])["continuation"]["messages"][0]["content"] == "done"
    assert [x["text"] for x in reopened.drain_steering(job["lease"])] == ["one", "two"]
    assert reopened.drain_steering(job["lease"]) == []
    events = reopened.events("alice", run["id"])
    assert [e["seq"] for e in events] == list(range(1, len(events) + 1))
    assert reopened.events("alice", run["id"], after=events[-1]["seq"]) == []


def test_plain_answer_cannot_complete_task(store):
    run = create(store)
    lease = store.claim("w1")["lease"]
    store.finish(lease, {"answer": "Done!"})
    assert store.get("alice", run["id"])["durum"] == "verifying"


def test_failed_required_check_prevents_acceptance(store):
    run = create(store, acceptance=[{"id": "test", "description": "Tests pass"}])
    lease = store.claim("w1")["lease"]
    store.record_check(lease, "test", False, {"exit_code": 1})
    store.finish(lease, {"answer": "Done!"})
    assert store.get("alice", run["id"])["durum"] == "partial"


def test_completed_requires_actual_check_records(store):
    run = create(store)
    lease = store.claim("w1")["lease"]
    store.record_check(lease, "result_verified", True, {"resource_id": "real-id"})
    store.finish(lease, {"answer": "Delivered"})
    assert store.get("alice", run["id"])["durum"] == "completed"


def test_dependencies_wait_and_parent_cannot_finish_before_children(store):
    parent = create(store)
    a = create(store, parent_id=parent["id"])
    b = create(store, parent_id=parent["id"], dependencies=[a["id"]])
    assert store.claim("w", run_id=b["id"]) is None
    lease = store.claim("w", run_id=parent["id"])["lease"]
    store.record_check(lease, "result_verified", True, {"resource_id": "p"})
    store.finish(lease, {"answer": "Wait"})
    assert store.get("alice", parent["id"])["durum"] == "verifying"
    alease = store.claim("w", run_id=a["id"])["lease"]
    store.record_check(alease, "result_verified", True, {"resource_id": "a"})
    store.finish(alease, {"answer": "a"})
    assert store.claim("w", run_id=b["id"]) is not None


def test_cross_tenant_or_workspace_dependencies_rejected(store):
    parent = create(store)
    with pytest.raises(NotFound):
        create(store, user="bob", parent_id=parent["id"])
    with pytest.raises(Conflict):
        store.create("alice", "other", "x", dependencies=[parent["id"]])


def test_expired_lease_is_fenced_and_read_job_requeues(store):
    now = [100.0]
    store.clock = lambda: now[0]
    run = create(store)
    old = store.claim("w1", lease_seconds=5)["lease"]
    now[0] = 106
    new = store.claim("w2", run_id=run["id"])["lease"]
    with pytest.raises(LeaseLost):
        store.finish(old, {"answer": "stale"})
    assert new.generation > old.generation


def test_inflight_external_effect_is_uncertain_and_never_blindly_retried(store):
    now = [100.0]
    store.clock = lambda: now[0]
    run = create(store)
    lease = store.claim("w1", lease_seconds=5)["lease"]
    store.begin_action(lease, "c1", "submit", {"value": 1}, side_effect=True)
    now[0] = 106
    assert store.claim("w2", run_id=run["id"]) is None
    assert store.get("alice", run["id"])["durum"] == "uncertain"
    with pytest.raises(Conflict):
        store.resume("alice", run["id"])


def test_action_replay_checks_arguments_and_returns_original_result(store):
    create(store)
    lease = store.claim("w")["lease"]
    assert store.begin_action(lease, "c1", "get", {"id": 1}) is None
    store.finish_action(lease, "c1", {"result": "one"}, True)
    assert store.begin_action(lease, "c1", "get", {"id": 1})["result"] == {"result": "one"}
    with pytest.raises(Conflict):
        store.begin_action(lease, "c1", "get", {"id": 2})


def test_cancel_parent_cancels_descendants_and_fences_worker(store):
    parent = create(store)
    child = create(store, parent_id=parent["id"])
    lease = store.claim("w", run_id=child["id"])["lease"]
    store.cancel("alice", parent["id"])
    assert store.get("alice", child["id"])["durum"] == "cancelled"
    with pytest.raises(LeaseLost):
        store.finish(lease, {"answer": "too late"})


def test_permissions_do_not_expand_in_children(store):
    parent = create(store, allowed_tools=["web_search"])
    with pytest.raises(Conflict):
        create(store, parent_id=parent["id"], allowed_tools=["write_file_tool"])


def test_approval_bound_to_action_and_user(store):
    run = create(store)
    lease = store.claim("w")["lease"]
    approval = store.request_approval(lease, "publish", "repo/main", {"sha": "a"})
    with pytest.raises(NotFound):
        store.approve("bob", run["id"], approval["id"], True)
    store.approve("alice", run["id"], approval["id"], True)
    resumed = store.claim("w", run_id=run["id"])["lease"]
    assert store.consume_approval(resumed, "publish", "repo/main", {"sha": "a"})
    assert not store.consume_approval(resumed, "publish", "repo/main", {"sha": "a"})


def test_worker_uses_persisted_context_and_returns_to_verification(store):
    run = create(store)
    def handler(job, control):
        assert job["user_id"] == "alice"
        control.check_cancelled()
        control.event("tool_done", {"ok": True})
        return {"answer": "done"}
    assert Worker(store, handler, worker_id="test-worker").tick()
    assert store.get("alice", run["id"])["durum"] == "verifying"


def test_user_acceptance_is_explicit_record_not_side_effect_permission(store):
    run = create(store)
    lease = store.claim("w")["lease"]
    store.finish(lease, {"answer": "A report to review"})
    with pytest.raises(NotFound):
        store.accept("bob", run["id"])
    result = store.accept("alice", run["id"])
    assert result["durum"] == "completed"
    assert result["checks"][0]["evidence"]["reviewer"] == "alice"
    assert result["approvals"] == []


def test_human_review_cannot_override_machine_criterion(store):
    run = create(store, acceptance=[{"id": "test", "kind": "command_exit"}])
    store.finish(store.claim("w")["lease"], {"answer": "Done"})
    with pytest.raises(Conflict):
        store.accept("alice", run["id"], "test")


def test_waiting_parent_requeues_after_all_children_settle(store):
    from chat.platform_runtime import Control, RunSuspended
    parent = create(store)
    child = create(store, parent_id=parent["id"])
    lease = store.claim("w", run_id=parent["id"])["lease"]
    with pytest.raises(RunSuspended):
        Control(store, lease).wait_for_children([child["id"]])
    assert store.claim("w", run_id=parent["id"]) is None
    clease = store.claim("c", run_id=child["id"])["lease"]
    store.record_check(clease, "result_verified", True, {"resource_id": "child-output"})
    store.finish(clease, {"answer": "Child delivered"})
    assert store.claim("w", run_id=parent["id"]) is not None


def test_worker_crash_after_external_effect_intent_is_uncertain(store):
    run = create(store)
    def handler(job, control):
        control.begin_action("c1", "submit", {}, side_effect=True)
        raise RuntimeError("Connection dropped after submit")
    Worker(store, handler).tick()
    assert store.get("alice", run["id"])["durum"] == "uncertain"
    assert store.claim("second") is None
    with pytest.raises(Conflict):
        store.reconcile_action("alice", run["id"], "c1", {"resource_id": "observed-id"},
                               True, {"source": "GET /resource/observed-id"})
    action = store.actions("alice", run["id"])[0]
    result = {"resource_id": "observed-id"}
    aid = store.add_artifact("alice", run["id"], {
        "kind": "external_observation", "verified": True, "call_id": "c1",
        "arguments_digest": action['digest'], "result": result, "content": "provider observation"})
    store.reconcile_action("alice", run["id"], "c1", result, True, {"artifact_id": aid})
    assert store.get("alice", run["id"])["durum"] == "paused"
    store.resume("alice", run["id"])
    lease = store.claim("second")["lease"]
    assert store.begin_action(lease, "c1", "submit", {}, True)["ok"]


def test_steering_order_and_recovery_when_clock_has_not_advanced(store):
    store.clock = lambda: 1234.0
    run = create(store)
    lease = store.claim("w")["lease"]
    store.checkpoint(lease, {"messages": []})
    for text in ["one", "two", "three"]:
        store.steer("alice", run["id"], text)
    assert [x["text"] for x in store.drain_steering(lease)] == ["one", "two", "three"]
    store.checkpoint(lease, {"messages": [{"role": "assistant", "content": "x"}]})
    saved = store.get("alice", run["id"])["continuation"]
    assert [x["text"] for x in saved["steering_messages"]] == ["one", "two", "three"]


def test_artifacts_are_hashed_and_tenant_protected(store):
    run = create(store)
    aid = store.add_artifact("alice", run["id"], {"kind": "log", "content": "all output", "title": "stdout.txt"})
    artifact = store.artifact("alice", run["id"], aid)
    assert len(artifact["sha256"]) == 64
    assert artifact["content"] == "all output"
    assert "content" not in store.get("alice", run["id"])["artifacts"][0]
    with pytest.raises(NotFound):
        store.artifact("bob", run["id"], aid)


def test_configured_capacity_rejects_without_losing_existing_jobs(store):
    store.max_queued_per_user = 1
    first = create(store)
    with pytest.raises(Conflict):
        create(store)
    assert store.get("alice", first["id"])["durum"] == "queued"


@pytest.mark.parametrize("settled_state", ["blocked", "uncertain"])
def test_settled_runs_release_capacity_without_replaying_effects(store, settled_state):
    store.max_queued_per_user = 1
    old = create(store)
    lease = store.claim("worker-old", run_id=old["id"])["lease"]
    if settled_state == "blocked":
        store.finish(lease, {"status": "blocked", "reason": "Connection unavailable"})
    else:
        store.begin_action(lease, "call-1", "external_write", {"value": 1},
                           side_effect=True)
        store.cancel("alice", old["id"])

    assert store.get("alice", old["id"])["durum"] == settled_state
    new = create(store)
    assert new["durum"] == "queued"
    with pytest.raises(Conflict):
        create(store)  # A genuinely queued run still occupies capacity.
    if settled_state == "uncertain":
        assert store.claim("worker-new", run_id=old["id"]) is None


def test_three_independent_children_claimed_in_parallel(store):
    from chat.platform_runtime import Control, RunSuspended
    parent = create(store)
    children = [create(store, parent_id=parent["id"]) for _ in range(3)]
    parent_lease = store.claim("parent", run_id=parent["id"])["lease"]
    with pytest.raises(RunSuspended):
        Control(store, parent_lease).wait_for_children([c["id"] for c in children])
    assert store.get("alice", parent["id"])["durum"] == "waiting_children"
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        leases = list(pool.map(lambda i: store.claim("w%d" % i), range(6)))
    claimed = [x["id"] for x in leases if x]
    assert sorted(claimed) == sorted(c["id"] for c in children)
    assert parent["id"] not in claimed


def test_parent_verifying_settles_when_children_finish(store):
    """Ust gorev cocuk bitmeden biterse `verifying`te kilitli kalmamali."""
    parent = create(store)
    child = create(store, parent_id=parent["id"])
    parent_lease = store.claim("parent", run_id=parent["id"])["lease"]
    store.add_artifact("alice", parent["id"], {
        "kind": "answer", "title": "yanit", "content": "parent answer"})
    store.record_check(parent_lease, "result_verified", True,
                       {"artifact_id": "answer"})
    store.finish(parent_lease, {"answer": "parent answer"})
    assert store.get("alice", parent["id"])["durum"] == "verifying"

    child_lease = store.claim("child", run_id=child["id"])["lease"]
    store.add_artifact("alice", child["id"], {
        "kind": "answer", "title": "yanit", "content": "child answer"})
    store.record_check(child_lease, "result_verified", True,
                       {"artifact_id": "answer"})
    store.finish(child_lease, {"answer": "child answer"})
    assert store.get("alice", child["id"])["durum"] == "completed"

    assert store.claim("idle") is None  # Herhangi bir claim kurtarmayi tetikler.
    assert store.get("alice", parent["id"])["durum"] == "completed"


def test_failed_sibling_keeps_other_child_artifact(store):
    parent = create(store)
    ok_child = create(store, parent_id=parent["id"])
    fail_child = create(store, parent_id=parent["id"])
    ok_lease = store.claim("ok", run_id=ok_child["id"])["lease"]
    aid = store.add_artifact("alice", ok_child["id"], {
        "kind": "file", "title": "out.txt", "content": "kept-output",
    })
    store.record_check(ok_lease, "result_verified", True, {"resource_id": "ok"})
    store.finish(ok_lease, {"answer": "ok"})
    fail_lease = store.claim("fail", run_id=fail_child["id"])["lease"]
    store.finish(fail_lease, {"status": "failed", "reason": "tool error"})
    parent_lease = store.claim("p", run_id=parent["id"])["lease"]
    store.finish(parent_lease, {"answer": "parent done"})
    assert store.get("alice", parent["id"])["durum"] == "partial"
    assert store.get("alice", ok_child["id"])["durum"] == "completed"
    assert store.artifact("alice", ok_child["id"], aid)["content"] == "kept-output"


def test_worker_killed_before_during_and_after_action(store):
    before = create(store)
    assert store.get("alice", before["id"])["durum"] == "queued"
    assert store.claim("later", run_id=before["id"]) is not None

    now = [100.0]
    store.clock = lambda: now[0]
    during = create(store)
    lease = store.claim("w1", lease_seconds=5, run_id=during["id"])["lease"]
    store.checkpoint(lease, {"messages": [{"role": "assistant", "content": "mid"}]})
    store.begin_action(lease, "c1", "web_search", {"q": "x"}, side_effect=False)
    now[0] = 106
    resumed = store.claim("w2", run_id=during["id"])
    assert resumed is not None
    assert store.get("alice", during["id"])["durum"] == "running"
    assert store.get("alice", during["id"])["continuation"]["messages"][0]["content"] == "mid"
    assert store.begin_action(resumed["lease"], "c1", "web_search", {"q": "x"}, False) is None

    after = create(store)
    done = store.claim("done", run_id=after["id"])["lease"]
    store.record_check(done, "result_verified", True, {"resource_id": "done"})
    store.finish(done, {"answer": "Delivered"})
    assert store.get("alice", after["id"])["durum"] == "completed"
    now[0] = 200
    assert store.claim("ghost", run_id=after["id"]) is None
    assert store.get("alice", after["id"])["durum"] == "completed"


def test_failed_tool_cannot_complete_even_with_human_accept(store):
    run = create(store)
    lease = store.claim("w")["lease"]
    store.begin_action(lease, "c1", "baglanti_cagir", {"arac": "write"}, True)
    store.finish_action(lease, "c1", {"error": "API 403"}, False)
    store.finish(lease, {"answer": "Wrote the report anyway"})
    assert store.get("alice", run["id"])["durum"] == "partial"
    accepted = store.accept("alice", run["id"])
    assert accepted["durum"] != "completed"
    assert accepted["durum"] in {"partial", "verifying"}


def test_empty_parent_permissions_remain_denied_on_implicit_child(store):
    parent = create(store, allowed_tools=[])
    child = create(store, parent_id=parent['id'])
    assert store.get('alice', child['id'])['allowed_tools'] == []


def test_subagent_caps_enforced_atomically_and_replay_remains_idempotent(store):
    store.max_children_per_parent = 8  # Explicit resource configuration, not a model depth limit.
    parent = create(store)
    created = [create(store, parent_id=parent["id"], request_key="agent:%d" % i)
               for i in range(8)]
    assert len({r["id"] for r in created}) == 8
    assert create(store, parent_id=parent["id"], request_key="agent:0")["id"] == created[0]["id"]
    with pytest.raises(Conflict, match="kapasitesi"):
        create(store, parent_id=parent["id"], request_key="agent:8")


def test_only_three_siblings_run_at_once_and_queued_fourth_resumes(store):
    parent = create(store)
    children = [create(store, parent_id=parent["id"]) for _ in range(4)]
    from chat.platform_runtime import Control, RunSuspended
    parent_lease = store.claim("parent", run_id=parent["id"])["lease"]
    with pytest.raises(RunSuspended):
        Control(store, parent_lease).wait_for_children([r["id"] for r in children])
    leases = [store.claim("worker-%d" % i) for i in range(4)]
    assert sum(job is not None for job in leases) == 3
    assert len({job["id"] for job in leases if job}) == 3
    # Jobs with the same creation timestamp are ordered by ID, not by the
    # order of this Python list. Verify the remaining job, whichever ID it has.
    queued = [child for child in children
              if store.get("alice", child["id"])["durum"] == "queued"]
    assert len(queued) == 1
    first = next(job for job in leases if job)
    store.record_check(first["lease"], "result_verified", True, {"id": "ok"})
    store.finish(first["lease"], {"answer": "done"})
    resumed = store.claim("next")
    assert resumed is not None
    assert resumed["id"] == queued[0]["id"]


def test_subagent_can_delegate_without_expanding_owner_tools(store):
    root = create(store)
    child = create(store, parent_id=root["id"])
    grandchild = create(store, parent_id=child["id"])
    assert grandchild['parent_id'] == child['id']
    with pytest.raises(Conflict, match='bekleyemez'):
        create(store, parent_id=child['id'], dependencies=[root['id']])


def test_subagent_capacity_configuration_is_valid(tmp_path):
    depo = kosu_deposu._SqliteDepo(str(tmp_path / "bad.db"))
    with pytest.raises(ValueError, match="kapasitesi"):
        RuntimeStore(depo, max_children_per_parent=2, max_active_children_per_parent=3)


def test_three_independent_worker_handlers_run_concurrently_without_fourth(store):
    import threading
    from chat.platform_runtime import Control, RunSuspended

    parent = create(store)
    children = [create(store, parent_id=parent["id"]) for _ in range(4)]
    lease = store.claim("parent", run_id=parent["id"])["lease"]
    with pytest.raises(RunSuspended):
        Control(store, lease).wait_for_children([child["id"] for child in children])

    started = threading.Semaphore(0)
    release = threading.Event()

    def handler(job, control):
        started.release()
        assert release.wait(timeout=8), "Concurrent worker handler never released"
        control.record_check("result_verified", True, {"run_id": job["id"]})
        return {"answer": "verified"}

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            futures = [pool.submit(Worker(store, handler, worker_id="agent-%s" % i).tick)
                       for i in range(3)]
            for _ in range(3):
                assert started.acquire(timeout=8), "Three workers did not begin concurrently"
            queued = [child for child in children
                      if store.get("alice", child["id"])["durum"] == "queued"]
            assert len(queued) == 1
            assert store.claim("fourth-worker", run_id=queued[0]["id"]) is None
            assert sum(store.get("alice", r["id"])["durum"] == "running" for r in children) == 3
            release.set()
            assert all(f.result(timeout=10) for f in futures)
        last = store.claim("fourth-worker", run_id=queued[0]["id"])
        assert last is not None and last["id"] == queued[0]["id"]
    finally:
        release.set()


def test_approval_preview_survives_restart_and_never_exposes_secret_content(tmp_path):
    from chat.platform_runtime import RuntimeStore
    from chat import kosu_deposu
    filename = str(tmp_path / "approvals.db")
    first = RuntimeStore(kosu_deposu._SqliteDepo(filename))
    run = first.create("alice", "personal", "Review file update")
    lease = first.claim("first", run_id=run["id"])["lease"]
    arguments = {
        "baglanti_id": "conn-1", "arac": "github_write_file",
        "argumanlar": {"repository": "a/b", "branch": "feat/safe", "path": "src/app.py",
                       "content": "BASE64_PRIVATE_SECRET_DO_NOT_DISPLAY"}}
    first.request_approval(lease, "baglanti_cagir", "conn-1", arguments)
    second = RuntimeStore(kosu_deposu._SqliteDepo(filename))
    approval = second.get("alice", run["id"])["approvals"][0]
    assert approval["preview"]["operation"] == "github_write_file"
    assert approval["preview"]["target"] == {
        "repository": "a/b", "branch": "feat/safe", "path": "src/app.py"}
    assert "BASE64_PRIVATE_SECRET_DO_NOT_DISPLAY" not in str(approval)
    assert "BASE64_PRIVATE_SECRET_DO_NOT_DISPLAY" not in str(
        second.events("alice", run["id"]))


def test_browser_approval_preview_does_not_leak_form_values(store):
    run = create(store)
    lease = store.claim("worker", run_id=run["id"])["lease"]
    approval = store.request_approval(lease, "bulut_tarayici", "browser:one",
        {"islem": "yaz", "argumanlar": {"session_id": "one",
          "selector": "input[type=password]", "text": "PRIVATE_PASSPHRASE"}})
    assert approval["preview"]["operation"] == "yaz"
    assert approval["preview"]["target"] == {"session_id": "one"}
    assert "PRIVATE_PASSPHRASE" not in str(store.get("alice", run["id"]))
    assert "PRIVATE_PASSPHRASE" not in str(store.events("alice", run["id"]))


def test_worker_health_requires_recent_independent_process_heartbeat(tmp_path):
    from chat.platform_runtime import RuntimeStore
    from chat import kosu_deposu
    now = [100.0]
    location = str(tmp_path / "presence.db")
    store = RuntimeStore(kosu_deposu._SqliteDepo(location), clock=lambda: now[0])
    assert store.worker_health()["online"] is False
    store.worker_ping("worker-one")
    again = RuntimeStore(kosu_deposu._SqliteDepo(location), clock=lambda: now[0])
    assert again.worker_health() == {
        "online": True, "live_workers": 1, "freshness_seconds": 30,
        "last_seen_age_seconds": 0.0}
    now[0] = 125.0
    assert again.worker_health()["online"] is True
    now[0] = 131.0
    assert again.worker_health()["online"] is False
    again.worker_ping("worker-one")
    again.worker_ping("worker-two")
    assert store.worker_health()["live_workers"] == 2
    again.worker_stopped("worker-one")
    assert store.worker_health()["live_workers"] == 1


def test_worker_presence_does_not_claim_or_complete_tasks(store):
    pending = create(store)
    store.worker_ping("idle-worker")
    assert store.worker_health()["online"] is True
    assert store.get("alice", pending["id"])["durum"] == "queued"


def test_default_user_task_quota_rejects_unbounded_work(store):
    assert store.max_queued_per_user == 32
    tasks = [create(store, request_key="bounded-%d" % i) for i in range(32)]
    assert len({x["id"] for x in tasks}) == 32
    with pytest.raises(Conflict, match="kapasitesi"):
        create(store)
    assert create(store, request_key="bounded-0")["id"] == tasks[0]["id"]
    assert create(store, user="bob")["durum"] == "queued"
    store.cancel("alice", tasks[0]["id"])
    assert create(store)["durum"] == "queued"


def test_root_budget_covers_nested_and_completed_subagents(store):
    store.max_descendants_per_root = 3
    root = create(store)
    child = create(store, parent_id=root['id'])
    grandchild = create(store, parent_id=child['id'])
    lease = store.claim('w', run_id=grandchild['id'])['lease']
    store.record_check(lease, 'result_verified', True, {'test': 'observed'})
    store.finish(lease, {'answer': 'done'})
    create(store, parent_id=root['id'])
    with pytest.raises(Conflict, match='toplam alt ajan'):
        create(store, parent_id=child['id'])
