"""Durable adapter around the existing Python model/tool loop.

There is no web-side brain or new provider routing implementation. Subtasks
use the same Brain, native tool protocol and ``arac_dongusu`` as normal chat.
https://www.kimi.com/code/docs/en/kimi-code-cli/customization/agents.html
"""
import json
from pathlib import Path

from chat.platform_context import ExecutionContext, bound


class ExecutionBlocked(BaseException):
    def __init__(self, reason, state='blocked'):
        self.reason, self.state = reason, state


# Cloud registry contains only tools whose ownership boundary is enforced.
# This is an execution capability boundary, independent of user wording.
READ_TOOLS = frozenset((
    'web_search', 'haber_ara', 'zamanli_ara', 'site_ara', 'gorsel_ara',
    'kitap_ara', 'sirket_ara', 'hava_durumu', 'derin_oku', 'sayfa_oku',
    'adres_kontrol', 'hesapla', 'simdi', 'hafiza_ara', 'read_file', 'list_files',
    'list_tasks', 'hatirlatma_listele', 'ajan_modelleri', 'alt_ajan_sonuclari',
    'baglanti_liste', 'baglanti_araclari',
))
CLOUD_TOOLS = READ_TOOLS | frozenset((
    'alt_ajan', 'baglanti_cagir', 'kod_dosya', 'kod_calistir', 'bulut_tarayici',
    'write_file_tool', 'add_task', 'complete_task', 'update_task_status',
    'hatirlatma_kur', 'hatirlatma_sil',
))


def _connection_meta(args, ctx):
    try:
        from chat.platform_connectors import tool_metadata
        return tool_metadata(ctx.user_id, args.get('baglanti_id', ''), args.get('arac', ''))
    except Exception:
        raise ExecutionBlocked('Baglanti ya da arac erisimi hazir degil', 'awaiting_connection') from None


def action_has_effect(name, args, ctx):
    if name in READ_TOOLS:
        return False
    if name == 'alt_ajan':
        return False  # create uses stable request keys; safe to reconcile/retry.
    if name == 'kod_dosya':
        return args.get('islem') == 'yaz'
    if name == 'bulut_tarayici':
        return args.get('islem') not in ('oku', 'ekran', 'dogrula', 'read', 'screenshot', 'verify')
    if name == 'baglanti_cagir':
        return not _connection_meta(args, ctx).get('annotations', {}).get('readOnlyHint', False)
    return True


def before_action(name, args, ctx):
    """Validate an immutable external effect approval before it is started."""
    ctx.control.check_cancelled()
    if ctx.allowed_tools is not None and name not in ctx.allowed_tools:
        raise PermissionError('Bu gorevin bu araca erisimi yok')
    if name == 'baglanti_cagir':
        meta = _connection_meta(args, ctx)
        annotations = meta.get('annotations', {})
        sensitive = bool(meta.get('requires_approval') or annotations.get('destructiveHint'))
        if sensitive:
            resource = str(args.get('baglanti_id', ''))
            if not ctx.control.store.consume_approval(ctx.control.lease, name, resource, args):
                ctx.control.request_approval(name, resource, args)


class _Events:
    def __init__(self, control):
        self.control, self.istek = control, control.lease.run_id

    def __call__(self, javascript):
        # Existing core UI emissions are parsed as data; never evaluated.
        self.control.check_cancelled()
        if not isinstance(javascript, str):
            return
        for prefix, event in (('BasakUI.parca(', 'piece'), ('BasakUI.toolStatus(', 'activity'),
                              ('BasakUI.error(', 'error')):
            if javascript.startswith(prefix) and javascript.endswith(')'):
                try:
                    value = json.loads(javascript[len(prefix):-1])
                except ValueError:
                    return
                self.control.event(event, {'text': value})
                return

    def olay(self, type_, **payload):
        payload.pop('_handoff', None)
        self.control.event(type_, payload)


def _path_value(value, field):
    for part in str(field or '').split('.'):
        if not part:
            continue
        if isinstance(value, dict):
            value = value.get(part)
        elif isinstance(value, list) and part.isdigit() and int(part) < len(value):
            value = value[int(part)]
        else:
            return None
    return value


def validate_acceptance(job, control, workspace):
    """Only deterministic observations satisfy a machine acceptance condition."""
    with control.store.transaction() as tx:
        control.store._lease(tx, control.lease)
        rows = tx.rows('SELECT call_id,tool,result,ok,status FROM basak_platform_action WHERE run_id=%s',
                       (control.lease.run_id,))
    for requirement in job.get('acceptance', []):
        kind, evidence, ok = requirement.get('kind'), {}, False
        if kind == 'file_exists':
            try:
                target = workspace.resolve(requirement.get('path'))
                content = target.read_bytes()
                import hashlib
                evidence = {'path': requirement['path'], 'sha256': hashlib.sha256(content).hexdigest()}
                ok = requirement.get('sha256', evidence['sha256']) == evidence['sha256']
            except (OSError, ValueError):
                evidence = {'path': str(requirement.get('path') or ''), 'missing': True}
        elif kind in ('tool_succeeded', 'json_equals', 'command_exit', 'browser_postcondition'):
            selected = [r for r in rows if r['tool'] == requirement.get('tool') and r['status'] == 'completed']
            if requirement.get('call_id'):
                selected = [r for r in selected if r['call_id'] == requirement['call_id']]
            if selected:
                row = selected[-1]
                raw = json.loads(row['result']).get('raw') or {}
                evidence = {'call_id': row['call_id'], 'tool': row['tool']}
                ok = bool(row['ok'])
                if kind == 'json_equals':
                    actual = _path_value(raw, requirement.get('field'))
                    evidence['actual'] = actual
                    ok = ok and actual == requirement.get('expected')
                elif kind == 'command_exit':
                    actual = _path_value(raw, 'result.exit_code')
                    evidence['exit_code'] = actual
                    ok = ok and actual == requirement.get('expected', 0)
                elif kind == 'browser_postcondition':
                    actual = _path_value(raw, 'result.verified')
                    evidence['verified'] = actual
                    ok = ok and actual is True
            else:
                evidence = {'tool': str(requirement.get('tool')), 'missing': True}
        elif kind is None:
            # Human acceptance remains pending; no nonempty-answer shortcut.
            continue
        else:
            evidence = {'unsupported_validator': str(kind)}
        control.record_check(requirement['id'], bool(ok), evidence)


def execute_job(job, control, brain=None):
    """Execute or resume one leased task through the shared native core loop."""
    from brain import Brain
    from brain.model_havuzu import model_selection
    from chat.agent_protocol import baslangic_araclari, acik_alan_araclari
    from chat.agent_runtime import AgentRunState, AGENT_CONTRACT
    from chat.prompts import kimlik_blogu, kisilik_blogu
    from chat.tools import arac_dongusu
    from tools import TOOLS, calistir
    from tools.platform import selection
    from worker.platform_execution import Workspace, ExecutionUnavailable
    from chat.kimlik import state_kok

    user = job['user_id']
    workspace = Workspace(state_kok(), user, job['workspace_id'])
    brain = brain or Brain()
    permissions = frozenset(job.get('allowed_tools') or CLOUD_TOOLS)
    if not permissions.issubset(CLOUD_TOOLS):
        return {'status': 'blocked', 'reason': 'Bu araclar bulut kullanici izolasyonunda desteklenmiyor'}
    ctx = ExecutionContext(user, job['workspace_id'], job['id'],
                           parent_run_id=job.get('parent_id') or '',
                           workspace_root=str(workspace.path), allowed_tools=permissions,
                           control=control, brain=brain)
    try:
        provider, model = selection(brain, job.get('model_ref'))
    except ValueError as exc:
        return {'status': 'blocked', 'reason': str(exc)}
    with bound(ctx), model_selection(provider, model):
        control.check_cancelled()
        catalog = [t for t in TOOLS if t['function']['name'] in permissions]
        saved = job.get('continuation') or {}
        history = saved.get('messages')
        if history is None:
            history = [{'role': 'system', 'content': kimlik_blogu(user)},
                       {'role': 'system', 'content': kisilik_blogu(user)},
                       {'role': 'system', 'content': AGENT_CONTRACT}]
            task_context = job.get('context', {}).get('task_context')
            if task_context:
                history.append({'role': 'user', 'content': str(task_context)})
            history.append({'role': 'user', 'content': job['istek']})
        else:
            history = list(history)
        existing_directions = {m.get('_steering_id') for m in history if isinstance(m, dict)}
        for steer in saved.get('steering_messages', []) + control.drain_steering():
            if steer['id'] not in existing_directions:
                history.append({'role': 'user', 'content': steer['text'], '_steering_id': steer['id']})
                existing_directions.add(steer['id'])
        children = control.store.tree(user, job['id']).get('children', [])
        if children and saved.get('tool_calls') is None:
            # Explicit tool result observation, not privileged instructions.
            history.append({'role': 'user', 'content': json.dumps(
                {'child_results': children}, ensure_ascii=False)})
        tools = acik_alan_araclari(catalog, saved.get('open_areas', [])) if saved.get('open_areas') else baslangic_araclari()
        preferred = saved.get('provider') or ([provider] if provider else [])
        callback, state = _Events(control), AgentRunState(job['id'])
        pending = saved.get('tool_calls')
        try:
            if not pending:
                control.checkpoint({'messages': history, 'open_areas': saved.get('open_areas', []),
                                    'tool_calls': None, 'provider': preferred})
                response, actual_provider = brain.cevapla(history, None, tools=tools,
                                                          tool_choice='auto', tercih=preferred)
                control.check_cancelled()
                control.event('provider', {'provider': actual_provider, 'requested': job.get('model_ref')})
                preferred = [actual_provider] if actual_provider else preferred
                pending = response.get('tool_calls') if isinstance(response, dict) else None
                if not pending:
                    answer = str(response.get('content') or '') if isinstance(response, dict) else str(response)
                else:
                    answer = ''
            else:
                response, answer = None, ''
            if pending:
                answer, _ = arac_dongusu(pending, history, brain, None, callback,
                    calistir, tools=tools, yanit=response, tool_choice='auto',
                    tercih=preferred, run_state=state, katalog=catalog,
                    platform_resume=saved)
            validate_acceptance(job, control, workspace)
            control.artifact('answer', title='Basak sonucu', content=answer, mime_type='text/markdown')
            return {'answer': answer}
        except ExecutionBlocked as blocked:
            return {'status': blocked.state, 'reason': blocked.reason}
        except ExecutionUnavailable as exc:
            return {'status': 'blocked', 'reason': str(exc)}
