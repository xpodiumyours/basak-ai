"""Production workers must never silently disconnect from the web task ledger."""
from types import SimpleNamespace

import pytest


def test_platform_worker_rejects_missing_shared_database(monkeypatch, capsys):
    from worker.platform import main

    monkeypatch.setattr('chat.kosu_deposu._dsn', lambda: '')
    with pytest.raises(SystemExit) as exc:
        main(['--once'])
    assert exc.value.code == 2
    assert 'DATABASE_URL' in capsys.readouterr().err


@pytest.mark.parametrize('has_dsn,local_opt_in', [
    (True, False),
    (True, True),
    (False, True),
])
def test_platform_worker_starts_only_with_postgres_or_explicit_local_fixture(
        monkeypatch, has_dsn, local_opt_in):
    from worker import platform as module

    monkeypatch.setattr(
        'chat.kosu_deposu._dsn',
        lambda: 'postgresql://localhost/test' if has_dsn else '',
    )
    events = []
    monkeypatch.setattr(
        module, 'RuntimeStore',
        lambda: events.append('store') or SimpleNamespace(),
    )

    class FakeWorker:
        def __init__(self, store, handler, **kwargs):
            events.append('worker')
        def tick(self):
            events.append('tick')
            return False

    monkeypatch.setattr(module, 'Worker', FakeWorker)
    args = ['--once']
    if local_opt_in:
        args.append('--allow-local-sqlite')
    assert module.main(args) == 0
    assert events == ['store', 'worker', 'tick']
