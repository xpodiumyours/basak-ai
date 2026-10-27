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


def test_empty_cloud_permissions_never_expand_to_default_registry():
    from chat.platform_agents import CLOUD_TOOLS, effective_permissions
    assert effective_permissions(None) == CLOUD_TOOLS
    assert effective_permissions([]) == frozenset()
    assert effective_permissions(['web_search']) == frozenset({'web_search'})


def test_sensitive_platform_tool_blocks_until_exact_owner_approval(tmp_path, monkeypatch):
    from dataclasses import replace
    from chat import kosu_deposu
    from chat.platform_agents import before_action, action_has_effect
    from chat.platform_context import ExecutionContext
    from chat.platform_runtime import Control, RunSuspended, RuntimeStore

    store = RuntimeStore(kosu_deposu._SqliteDepo(str(tmp_path / 'approval.db')))
    job = store.create('alice', 'personal', 'Review workflow', allowed_tools=['baglanti_cagir'])
    lease = store.claim('worker-a')['lease']
    ctx = ExecutionContext('alice', 'personal', job['id'],
                           allowed_tools=frozenset(['baglanti_cagir']),
                           control=Control(store, lease))
    args = {'baglanti_id': 'connection-1', 'arac': 'github_dispatch_workflow',
            'argumanlar': {'repository': 'team/app', 'workflow': 'deploy.yml'}}
    monkeypatch.setattr('chat.platform_agents._connection_meta',
                        lambda *_: {'provider': 'github', 'read_only': False,
                                    'side_effect': True, 'requires_approval': False})
    assert action_has_effect('baglanti_cagir', args, ctx)
    with pytest.raises(RunSuspended):
        before_action('baglanti_cagir', args, ctx)
    assert store.get('alice', job['id'])['durum'] == 'awaiting_approval'
    assert store.actions('alice', job['id']) == []
    approval = store.get('alice', job['id'])['approvals'][0]
    store.approve('alice', job['id'], approval['id'], True)
    next_lease = store.claim('worker-a', run_id=job['id'])['lease']
    next_ctx = replace(ctx, control=Control(store, next_lease))
    before_action('baglanti_cagir', args, next_ctx)
    with pytest.raises(RunSuspended):
        before_action('baglanti_cagir', args, next_ctx)  # approval was single-use


def test_platform_tool_loop_invokes_pre_action_gate_before_external_call(monkeypatch):
    import json
    from types import SimpleNamespace
    from chat.platform_context import ExecutionContext, bound
    from chat.platform_runtime import RunSuspended
    from chat.tools import arac_dongusu
    from tools.definitions import TOOLS

    class Control:
        def check_cancelled(self):
            pass
        def checkpoint(self, state):
            pass
        def begin_action(self, *args, **kwargs):
            pytest.fail('an action began before owner authorization')

    def suspend(*args):
        raise RunSuspended()

    monkeypatch.setattr('chat.platform_agents.before_action', suspend)
    name = 'baglanti_cagir'
    schema = next(x for x in TOOLS if x['function']['name'] == name)
    call = {'id': 'sensitive-1', 'function': {'name': name, 'arguments': json.dumps({
        'baglanti_id': 'any', 'arac': 'github_dispatch_workflow', 'argumanlar': {}})}}
    ctx = ExecutionContext('alice', 'personal', 'run-1', control=Control(),
                           allowed_tools=frozenset([name]))
    with bound(ctx), pytest.raises(RunSuspended):
        arac_dongusu([call], [], SimpleNamespace(), None, lambda *_: None,
                     lambda *_: pytest.fail('external tool unexpectedly ran'),
                     tools=[schema], yanit={'tool_calls': [call]})

@pytest.mark.parametrize("provider,tool,side_effect", [
    ('github', 'github_write_file', True),
    ('github', 'github_create_branch', True),
    ('google', 'docs_update', True),
    ('google', 'sheets_write', True),
    ('notion', 'notion_update_page', True),
    ('mcp', 'untrusted_readonly_claim', False),
])
def test_all_remote_mutations_require_owner_approval(monkeypatch, provider, tool, side_effect):
    from chat.platform_agents import before_action, action_has_effect
    from chat.platform_context import ExecutionContext
    from chat.platform_runtime import RunSuspended

    def suspend(*_args):
        raise RunSuspended()

    control = SimpleNamespace(
        check_cancelled=lambda: None,
        store=SimpleNamespace(consume_approval=lambda *_args: False),
        lease=SimpleNamespace(),
        request_approval=suspend,
    )
    ctx = ExecutionContext('alice', 'personal', 'run-1', control=control,
                           allowed_tools=frozenset(['baglanti_cagir']))
    monkeypatch.setattr('chat.platform_agents._connection_meta',
                        lambda *_: {'provider': provider, 'read_only': not side_effect,
                                    'side_effect': side_effect, 'requires_approval': False})
    args = {'baglanti_id': 'sandbox-connection', 'arac': tool, 'argumanlar': {}}
    assert action_has_effect('baglanti_cagir', args, ctx) is True
    with pytest.raises(RunSuspended):
        before_action('baglanti_cagir', args, ctx)


def test_builtin_connection_reads_do_not_request_approval(monkeypatch):
    from chat.platform_agents import before_action, action_has_effect
    from chat.platform_context import ExecutionContext

    def forbidden(*_args):
        pytest.fail('readonly built-in tool requested approval')

    control = SimpleNamespace(check_cancelled=lambda: None, request_approval=forbidden)
    ctx = ExecutionContext('alice', 'personal', 'run-1', control=control,
                           allowed_tools=frozenset(['baglanti_cagir']))
    monkeypatch.setattr('chat.platform_agents._connection_meta',
                        lambda *_: {'provider': 'google', 'read_only': True,
                                    'side_effect': False, 'requires_approval': False})
    args = {'baglanti_id': 'sandbox-connection', 'arac': 'drive_get_file',
            'argumanlar': {'file_id': 'test'}}
    assert action_has_effect('baglanti_cagir', args, ctx) is False
    before_action('baglanti_cagir', args, ctx)


def test_unavailable_browser_is_a_failed_tool_not_a_success(monkeypatch):
    from chat.platform_context import ExecutionContext, bound
    from chat.tools import sonucu_donustur
    from tools.platform import execute

    monkeypatch.delenv('BASAK_BROWSER_ISOLATED', raising=False)
    control = SimpleNamespace(check_cancelled=lambda: None)
    ctx = ExecutionContext('alice', 'personal', 'run-1', control=control,
                           allowed_tools=frozenset(['bulut_tarayici']))
    with bound(ctx):
        outcome = execute('bulut_tarayici',
                          {'islem': 'ac', 'argumanlar': {'url': 'https://example.com'}})
    assert outcome['result']['status'] == 'browser_unavailable'
    assert sonucu_donustur(outcome).startswith('Hata:')


def test_child_model_never_sees_delegation_tool_even_when_parent_allows_it():
    from chat.platform_agents import CLOUD_TOOLS, job_permissions
    assert job_permissions({'parent_id': None, 'allowed_tools': None}) == CLOUD_TOOLS
    assert job_permissions({'parent_id': 'parent-id', 'allowed_tools': None}) == CLOUD_TOOLS - {'alt_ajan'}
    assert job_permissions({'parent_id': 'parent-id', 'allowed_tools': ['web_search', 'alt_ajan']}) == frozenset({'web_search'})
    assert job_permissions({'parent_id': 'parent-id', 'allowed_tools': []}) == frozenset()


@pytest.mark.parametrize("provider", ["deepseek", "mimo"])
def test_thinking_tool_reply_survives_owner_approval_and_worker_restart(
        tmp_path, monkeypatch, provider):
    """Kotasiz fixture: preserve full assistant thinking metadata on replay."""
    from dataclasses import replace
    from chat import kosu_deposu
    from chat.platform_context import ExecutionContext, bound
    from chat.platform_runtime import RuntimeStore, Control, RunSuspended
    from chat.tools import arac_dongusu
    from brain.message_utils import mesajlari_temizle
    from tools.definitions import TOOLS

    store = RuntimeStore(kosu_deposu._SqliteDepo(str(tmp_path / 'reasoning.db')))
    job = store.create('alice', 'personal', 'Verify one approved write',
                       allowed_tools=['baglanti_cagir'])
    lease = store.claim('first-worker', run_id=job['id'])['lease']
    ctx = ExecutionContext('alice', 'personal', job['id'],
                           allowed_tools=frozenset(['baglanti_cagir']),
                           control=Control(store, lease))
    args = {'baglanti_id': 'connection-test', 'arac': 'github_write_file',
            'argumanlar': {'path': 'test.txt'}}
    import json
    call = {'id': 'call_once', 'type': 'function',
            'function': {'name': 'baglanti_cagir',
                         'arguments': json.dumps(args)}}
    reply = {'content': 'One approved change requested',
             'reasoning_content': 'synthetic-thinking-state-for-replay',
             'tool_calls': [call]}
    tool = next(t for t in TOOLS if t['function']['name'] == 'baglanti_cagir')
    monkeypatch.setattr('chat.platform_agents._connection_meta',
                        lambda *_: {'provider': 'github', 'side_effect': True,
                                    'requires_approval': True})

    # First process is halted BEFORE executing an unapproved remote mutation.
    with bound(ctx), pytest.raises(RunSuspended):
        arac_dongusu([call], [{'role': 'user', 'content': 'update test'}],
                     SimpleNamespace(), None, lambda *_: None,
                     lambda *_: pytest.fail('unauthorized external write'),
                     tools=[tool], yanit=reply, tercih=[provider])
    saved = store.get('alice', job['id'])['continuation']
    assert saved['pending_reply']['reasoning_content'] == reply['reasoning_content']
    assert saved['pending_reply']['content'] == reply['content']
    assert saved['tool_calls'] == [call]
    approval = store.get('alice', job['id'])['approvals'][0]
    store.approve('alice', job['id'], approval['id'], True)

    second_lease = store.claim('new-worker', run_id=job['id'])['lease']
    replay_ctx = replace(ctx, control=Control(store, second_lease))
    seen, executed = [], []

    class MockBrain:
        def cevapla_yayin(self, *a, **k):
            from brain.yayin import SonHata
            raise SonHata('test stream disabled')
            yield
        def cevapla(self, messages, model, tools=None, **kwargs):
            seen.extend(messages)
            return {'content': 'done'}, provider

    with bound(replay_ctx):
        answer, count = arac_dongusu(saved['tool_calls'], saved['messages'],
            MockBrain(), None, lambda *_: None,
            lambda name, params: executed.append(name) or {'result': 'written'},
            tools=[tool], yanit=saved.get('pending_reply'), tercih=[provider],
            platform_resume=saved)
    assert answer == 'done' and count == 1
    assert executed == ['baglanti_cagir']
    assistant = next(m for m in seen if m['role'] == 'assistant')
    assert assistant['reasoning_content'] == reply['reasoning_content']
    assert assistant['content'] == reply['content']
    assert assistant['tool_calls'][0]['id'] == 'call_once'
    assert mesajlari_temizle([assistant], provider=provider)[0][
        'reasoning_content'] == reply['reasoning_content']
    assert 'reasoning_content' not in mesajlari_temizle(
        [assistant], provider='other-provider')[0]


@pytest.mark.parametrize("operation", ["tikla", "yaz", "tus", "yukle", "indir", "unknown_operation"])
def test_browser_external_mutations_require_exact_single_use_approval(
        tmp_path, operation):
    from dataclasses import replace
    from chat import kosu_deposu
    from chat.platform_context import ExecutionContext
    from chat.platform_agents import before_action, action_has_effect
    from chat.platform_runtime import Control, RunSuspended, RuntimeStore

    store = RuntimeStore(kosu_deposu._SqliteDepo(str(tmp_path / ('browser-' + operation + '.db'))))
    job = store.create('alice', 'personal', 'Approved browser action',
                       allowed_tools=['bulut_tarayici'])
    lease = store.claim('browser-worker', run_id=job['id'])['lease']
    ctx = ExecutionContext('alice', 'personal', job['id'],
                           allowed_tools=frozenset(['bulut_tarayici']),
                           control=Control(store, lease))
    args = {'islem': operation,
            'argumanlar': {'session_id': 'owned-browser', 'selector': '#submit'}}
    assert action_has_effect('bulut_tarayici', args, ctx)
    with pytest.raises(RunSuspended):
        before_action('bulut_tarayici', args, ctx)
    assert store.actions('alice', job['id']) == []
    approval = store.get('alice', job['id'])['approvals'][0]
    assert approval['resource'] == 'browser:owned-browser'
    store.approve('alice', job['id'], approval['id'], True)
    next_lease = store.claim('resumed-browser-worker', run_id=job['id'])['lease']
    next_ctx = replace(ctx, control=Control(store, next_lease))
    # An approved selector/session cannot authorize another target.
    tampered = {'islem': operation,
                'argumanlar': {'session_id': 'other-browser', 'selector': '#submit'}}
    with pytest.raises(RunSuspended):
        before_action('bulut_tarayici', tampered, next_ctx)
    # A suspended request needs its own approval; resume via the owner.
    other = store.get('alice', job['id'])['approvals'][-1]
    store.approve('alice', job['id'], other['id'], False)
    with pytest.raises(Conflict):
        store.claim('worker', run_id=job['id'])
    # Resume explicitly; the first approval remains available and single-use.
    store.resume('alice', job['id'])
    approved_lease = store.claim('worker', run_id=job['id'])['lease']
    approved_ctx = replace(ctx, control=Control(store, approved_lease))
    before_action('bulut_tarayici', args, approved_ctx)
    with pytest.raises(RunSuspended):
        before_action('bulut_tarayici', args, approved_ctx)


@pytest.mark.parametrize("operation", ["ac", "oku", "ekran", "dogrula", "kaydir", "devral", "birak"])
def test_browser_navigation_read_and_scroll_do_not_prompt_for_write_consent(operation):
    from chat.platform_agents import action_has_effect, before_action
    from chat.platform_context import ExecutionContext
    control = SimpleNamespace(
        check_cancelled=lambda: None,
        request_approval=lambda *_: pytest.fail('Read-only browser operation demanded write consent'))
    ctx = ExecutionContext('alice', 'personal', 'run-1',
                           allowed_tools=frozenset(['bulut_tarayici']), control=control)
    args = {'islem': operation, 'argumanlar': {'url': 'https://example.com'}}
    assert not action_has_effect('bulut_tarayici', args, ctx)
    before_action('bulut_tarayici', args, ctx)
