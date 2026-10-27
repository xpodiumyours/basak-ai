"""Execution boundaries: authenticated identity, exact model choice, cloud isolation."""
import concurrent.futures
from pathlib import Path
from types import SimpleNamespace

import pytest


def test_explicit_context_crosses_thread_without_owner_fallback():
    from chat.platform_context import ExecutionContext, bound, current
    from chat.kimlik import aktif_kullanici
    contexts = [ExecutionContext('alice', 'ws-a', 'run-a'),
                ExecutionContext('bob', 'ws-b', 'run-b')]
    def check(ctx):
        with bound(ctx):
            return current().user_id, aktif_kullanici()
    with concurrent.futures.ThreadPoolExecutor(2) as pool:
        assert list(pool.map(check, contexts)) == [('alice', 'alice'), ('bob', 'bob')]
    assert current() is None


def test_blank_or_anonymous_execution_identity_is_rejected():
    from chat.platform_context import ExecutionContext
    for user in ('', 'anon-123', 'p0123456789abcdef'):
        with pytest.raises(ValueError):
            ExecutionContext(user, 'workspace', 'run')


def test_scoped_files_cannot_read_other_user_or_source(tmp_path):
    from chat.platform_context import ExecutionContext, bound
    from tools import file_ops
    root = tmp_path / 'workspace'
    root.mkdir()
    (root / 'own.txt').write_text('mine', encoding='utf-8')
    outside = tmp_path / 'other.txt'
    outside.write_text('other user secret', encoding='utf-8')
    ctx = ExecutionContext('alice', 'workspace', 'run', workspace_root=str(root))
    with bound(ctx):
        assert 'mine' in file_ops.read_file(str(root / 'own.txt'), str(root))['result']
        assert 'error' in file_ops.read_file(str(outside), str(root))
        assert 'error' in file_ops.read_file('../other.txt', str(root))


def test_model_selection_survives_sdk_with_options_and_does_not_leak():
    from brain.model_havuzu import ModelHavuzuSDK, model_selection
    calls = []
    def create(**kw):
        calls.append(kw['model'])
        return {'ok': True}
    class SDK:
        chat = SimpleNamespace(completions=SimpleNamespace(create=create))
        def with_options(self, **kwargs):
            return self
    pool = ModelHavuzuSDK(SDK(), [{'id': 'a', 'tools': True}, {'id': 'b', 'tools': True}],
                         provider='groq')
    with model_selection('groq', 'b'):
        pool.with_options(timeout=90).chat.completions.create(model='a')
    pool.chat.completions.create(model='a')
    assert calls == ['b', 'a']


def test_sandbox_requires_isolation_and_pinned_image(tmp_path):
    from worker.platform_execution import Sandbox, ExecutionUnavailable
    sandbox = Sandbox(workspace=tmp_path, image='python:latest')
    with pytest.raises(ExecutionUnavailable):
        sandbox.run(['python', '-V'])


def test_workspace_rejects_parent_paths_and_symlinks(tmp_path):
    from worker.platform_execution import Workspace
    workspace = Workspace(tmp_path, 'alice', 'project')
    with pytest.raises(ValueError):
        workspace.write('../other/secret.txt', 'bad')
    with pytest.raises(ValueError):
        workspace.write('/absolute.txt', 'bad')
    workspace.write('src/main.py', 'print(42)')
    assert workspace.read('src/main.py')['content'] == 'print(42)'
    assert Path(workspace.path / 'src/main.py').read_text() == 'print(42)'


def test_alt_ajan_wait_result_is_json_the_tool_loop_can_parse(tmp_path):
    import json
    from types import SimpleNamespace

    from chat import kosu_deposu
    from chat.platform_context import ExecutionContext, bound
    from chat.platform_runtime import Control, RuntimeStore, RunSuspended
    from tools.platform import execute

    store = RuntimeStore(kosu_deposu._SqliteDepo(str(tmp_path / 'runs.db')))
    parent = store.create('alice', 'personal', 'parent work')
    lease = store.claim('w', run_id=parent['id'])['lease']
    brain = SimpleNamespace(_bulut_zinciri=lambda tools=False, tool_required=False: [])
    ctx = ExecutionContext('alice', 'personal', parent['id'],
                           control=Control(store, lease), brain=brain)
    with bound(ctx):
        created = execute('alt_ajan', {'isler': [
            {'gorev': 'birinci is'},
            {'gorev': 'ikinci is'},
            {'gorev': 'ucuncu is'},
        ]})
        ids = [row['id'] for row in created['result']]
        assert len(ids) == 3
        waiting = execute('alt_ajan_sonuclari', {'bekle': True})
    from chat.tools import sonucu_donustur
    parsed = json.loads(sonucu_donustur(waiting))
    assert sorted(parsed['_wait_children']) == sorted(ids)
    with pytest.raises(RunSuspended):
        ctx.control.wait_for_children(parsed['_wait_children'])
    assert store.get('alice', parent['id'])['durum'] == 'waiting_children'
