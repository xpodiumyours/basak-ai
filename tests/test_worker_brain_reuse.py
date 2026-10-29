"""Worker transport clients are reused without sharing a Brain across threads."""
import concurrent.futures
import threading


def test_jobs_reuse_brain_per_thread_and_keep_job_context_separate():
    from worker.platform import thread_handler
    created = []
    def factory():
        brain = object()
        created.append(brain)
        return brain
    def execute(job, control, *, brain):
        return job, control, brain
    handler = thread_handler(execute, factory)
    a, b = {'user_id': 'a'}, {'user_id': 'b'}
    assert handler(a, 'control-a')[:2] == (a, 'control-a')
    assert handler(b, 'control-b')[:2] == (b, 'control-b')
    assert len(created) == 1
    barrier = threading.Barrier(2)
    def other_thread(_):
        first = handler(a, 'child')
        barrier.wait(timeout=5)
        assert handler(b, 'next')[2] is first[2]
        return first[2]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(other_thread, range(2)))
    assert results[0] is not results[1]
    assert all(result is not created[0] for result in results)
    assert len(created) == 3


def test_foreground_jobs_reuse_clients_without_sharing_context(monkeypatch):
    import worker.platform as module
    import brain
    created = []
    def factory():
        result = object()
        created.append(result)
        return result
    monkeypatch.setattr(brain, 'Brain', factory)
    monkeypatch.setattr(module, '_provider_clients', threading.local())
    assert module.reused_brain() is module.reused_brain()
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        other = pool.submit(module.reused_brain).result()
    assert other is not module.reused_brain()
    assert len(created) == 2
