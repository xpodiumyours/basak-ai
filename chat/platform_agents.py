"""Durable adapter around the existing Python model/tool loop.

There is no web-side brain or new provider routing implementation. Subtasks
use the same Brain, native tool protocol and ``arac_dongusu`` as normal chat.
https://www.kimi.com/code/docs/en/kimi-code-cli/customization/agents.html
"""
import json
import time
import copy

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
    'image_analyze',
))
CLOUD_TOOLS = READ_TOOLS | frozenset((
    'alt_ajan', 'baglanti_cagir', 'kod_dosya', 'kod_calistir', 'bulut_tarayici',
    'write_file_tool', 'add_task', 'complete_task', 'update_task_status',
    'hatirlatma_kur', 'hatirlatma_sil',
))


def execution_catalog(permissions):
    """Expose real callable tool names in the delegated-tool parameter schema."""
    from tools import TOOLS
    catalog = [copy.deepcopy(t) for t in TOOLS if t['function']['name'] in permissions]
    names = sorted(t['function']['name'] for t in catalog)
    for declaration in catalog:
        if declaration['function']['name'] == 'alt_ajan':
            fields = declaration['function']['parameters']['properties']['isler']['items']['properties']
            fields['araclar']['items']['enum'] = names
            fields['kabul']['items']['properties']['tool']['enum'] = names
    return catalog


def _connection_meta(args, ctx):
    try:
        from chat.platform_connectors import tool_metadata
        return tool_metadata(ctx.user_id, args.get('baglanti_id', ''), args.get('arac', ''))
    except Exception:
        raise ExecutionBlocked('Baglanti ya da arac erisimi hazir degil', 'awaiting_connection') from None


def effective_permissions(allowed_tools):
    """None inherits the owner's cloud registry; [] explicitly denies tools."""
    return frozenset(CLOUD_TOOLS if allowed_tools is None else allowed_tools)


def job_permissions(job):
    """Delegated work inherits the explicit owner capability boundary."""
    return effective_permissions(job.get('allowed_tools'))


def action_has_effect(name, args, ctx):
    if name in READ_TOOLS:
        return False
    if name == 'alt_ajan':
        return False  # create uses stable request keys; safe to reconcile/retry.
    if name == 'kod_dosya':
        return args.get('islem') == 'yaz'
    if name == 'bulut_tarayici':
        # Browser click/keyboard/upload/download can modify a third-party
        # service even when the DOM does not reveal that effect beforehand.
        # Fail closed on unknown operations; reading, scrolling and an
        # ordinary GET navigation are not considered mutations.
        return args.get('islem') not in (
            'ac', 'oku', 'ekran', 'dogrula', 'kaydir', 'devral', 'birak')
    if name == 'baglanti_cagir':
        meta = _connection_meta(args, ctx)
        # Remote MCP annotations are advisory, not an execution guarantee.
        return meta.get('provider') == 'mcp' or meta.get('side_effect', True)
    return True


def before_action(name, args, ctx):
    """Validate an immutable external effect approval before it is started."""
    ctx.control.check_cancelled()
    if name == 'image_analyze':
        from chat.platform_context import workspace_path
        workspace_path(args.get('path', ''))
    if ctx.allowed_tools is not None and name not in ctx.allowed_tools:
        raise PermissionError('Bu gorevin bu araca erisimi yok')
    # The action ledger is authoritative: an identical completed call must
    # replay its result without requiring another approval. Unknown or altered
    # calls never bypass the consent gate.
    if ctx.tool_call_id and ctx.control.store.replay_completed(
            ctx.control.lease, ctx.tool_call_id, name, args):
        return
    if name == 'baglanti_cagir':
        meta = _connection_meta(args, ctx)
        # Built-in writes require approval. MCP tools are untrusted even if
        # their remote server claims readOnlyHint: consent before each call.
        # Fail closed when side-effect metadata is missing.
        sensitive = bool(
            meta.get('requires_approval')
            or meta.get('side_effect', True)
            or meta.get('provider') == 'mcp'
        )
        if sensitive:
            resource = str(args.get('baglanti_id', ''))
            if not ctx.control.store.consume_approval(ctx.control.lease, name, resource, args):
                ctx.control.request_approval(name, resource, args)
    elif name == 'bulut_tarayici' and action_has_effect(name, args, ctx):
        # Browser actions are untrusted external mutations, not local writes.
        # Consent is bound to the exact operation, session and arguments
        # digest. Do not allocate a running action until consent is consumed.
        details = args.get('argumanlar')
        details = details if isinstance(details, dict) else {}
        session_id = str(details.get('session_id') or '')
        resource = 'browser:' + (session_id or 'unknown-session')
        if not ctx.control.store.consume_approval(ctx.control.lease, name, resource, args):
            ctx.control.request_approval(name, resource, args)


class _Events:
    def __init__(self, control):
        self.control, self.istek = control, control.lease.run_id
        self.answer, self.provider, self.error = '', '', ''
        self._pieces, self._piece_size = [], 0
        self._piece_started = None
        self._cancel_checked = None

    def _check_text_cancel(self):
        now = time.monotonic()
        if self._cancel_checked is None or now - self._cancel_checked >= 0.25:
            self.control.check_cancelled()
            self._cancel_checked = time.monotonic()

    def flush(self):
        if not self._pieces:
            return
        self.control.check_cancelled()
        self._cancel_checked = time.monotonic()
        self.control.event('chat', {'tur': 'parca', 'metin': ''.join(self._pieces)})
        self._pieces, self._piece_size, self._piece_started = [], 0, None

    def __call__(self, javascript):
        # Existing core UI emissions are parsed as data; never evaluated.
        if not isinstance(javascript, str):
            return
        if not javascript.startswith('BasakUI.') or not javascript.endswith(')'):
            return
        name, raw = javascript[8:-1].split('(', 1)
        values = json.loads('[' + raw + ']')
        if name == 'parca' and len(values) == 1 and isinstance(values[0], str):
            self._check_text_cancel()
            if self._piece_started is None:
                self._piece_started = time.monotonic()
            self._pieces.append(values[0])
            self._piece_size += len(values[0])
            if self._piece_size >= 1024 or time.monotonic() - self._piece_started >= 0.15:
                self.flush()
            return
        self.flush()
        self.control.check_cancelled()
        payload = {'tur': name}
        if name == 'bitir':
            self.answer = values[0] if values else ''
            self.provider = values[1] if len(values) > 1 else ''
            payload.update(cevap=self.answer, kaynak=self.provider)
            self.control.event('provider', {'provider': self.provider})
        elif values:
            payload['metin'] = values[0]
            if name == 'error':
                self.error = str(values[0])
        self.control.event('chat', payload)

    def olay(self, type_, **payload):
        self.flush()
        self.control.check_cancelled()
        payload.pop('_handoff', None)
        self.control.event(type_, payload)
        if type_ == 'runState' and payload.get('provider'):
            self.control.event('provider', {'provider': payload['provider']})


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
        if kind in ('execution_observed', 'message_recorded'):
            completed = [r for r in rows if r['status'] == 'completed' and r['ok']]
            artifacts = control.store.get(job['user_id'], job['id'])['artifacts']
            answers = [a for a in artifacts if a.get('kind') == 'answer' and a.get('size', 0)]
            evidence = {'call_ids': [r['call_id'] for r in completed],
                        'artifacts': [a['id'] for a in answers]}
            # Arac kullanmayan bir alt gorev de gecerli olabilir: yanit
            # kaydi varsa ve kaydedilmis hicbir eylem basarisiz degilse
            # "gozlemlendi" sayilir. Arac beklentisi varsa model bunu
            # tool_succeeded gibi ayri bir kabul kosuluyla belirtir.
            ok = bool(answers) and all(
                r['status'] == 'completed' and r['ok'] for r in rows)
        elif kind == 'file_exists':
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
        elif kind in (None, 'human', 'user_acceptance'):
            # Human acceptance remains pending; no nonempty-answer shortcut.
            continue
        else:
            evidence = {'unsupported_validator': str(kind)}
        control.record_check(requirement['id'], bool(ok), evidence)


def execute_job(job, control, brain=None):
    """Execute or resume one leased task through the shared native core loop."""
    from brain import Brain
    from brain.model_havuzu import model_selection
    from chat.flow import mesaj_isle
    from chat.ayar import sistem_blogu
    from tools import TOOLS
    from tools.platform import selection
    from worker.platform_execution import Workspace, ExecutionUnavailable
    from chat.kimlik import state_kok

    user = job['user_id']
    workspace = Workspace(state_kok(), user, job['workspace_id'], job['id'])
    workspace.restore(control.store, user, job['workspace_id'])
    brain = brain or Brain()
    permissions = job_permissions(job)
    if not permissions.issubset(CLOUD_TOOLS):
        return {'status': 'blocked', 'reason': 'Bu araclar bulut kullanici izolasyonunda desteklenmiyor'}
    ctx = ExecutionContext(user, job['workspace_id'], job['id'],
                           parent_run_id=job.get('parent_id') or '',
                           workspace_root=str(workspace.path), allowed_tools=permissions,
                           control=control, brain=brain)
    try:
        # Rol -> model eslemesi ortamdan gelir (BASAK_KOMUTAN_MODEL /
        # BASAK_ISCI_MODEL). Bos model_ref "otomatik" demektir; alt ajanlar
        # isci rolune, kok gorevler komutan rolune duser.
        ref = job.get('model_ref') or ('isci' if job.get('parent_id')
                                       else 'komutan')
        provider, model = selection(brain, ref)
    except ValueError as exc:
        return {'status': 'blocked', 'reason': str(exc)}
    with bound(ctx), model_selection(provider, model):
        control.check_cancelled()
        catalog = execution_catalog(permissions)
        saved = job.get('continuation') or {}
        callback = _Events(control)
        context = job.get('context') or {}
        try:
            # Both chat and delegated jobs enter the existing Python flow.
            # Child history is explicit and independent from the owner's chat.
            history = context.get('history', [] if job.get('parent_id') else None)
            task_context = context.get('task_context')
            if job.get('parent_id') and job.get('acceptance'):
                # These are the parent's actual delegated requirements, not
                # instructions invented by the executor. Preserve all fields.
                task_context = json.dumps({'task_context': task_context,
                                           'acceptance': job['acceptance']},
                                          ensure_ascii=False)
            if task_context and not saved.get('messages'):
                history = [*(history or []), {'role': 'user', 'content': str(task_context)}]
            children = control.store.tree(user, job['id']).get('children', [])
            if children and saved.get('messages') and not saved.get('tool_calls'):
                from chat.platform_runtime import delegated_result
                saved = {**saved, 'messages': [dict(m) for m in saved['messages']]}
                for message in reversed(saved['messages']):
                    if message.get('role') == 'tool' and message.get('name') == 'alt_ajan_sonuclari':
                        message['content'] = json.dumps({'children': [delegated_result(child) for child in children]}, ensure_ascii=False)
                        break
            instruction = job['istek']
            attachment = context.get('attachment')
            if attachment and not saved.get('messages'):
                import base64
                data_url = str(attachment.get('data_url') or '')
                header, encoded = data_url.split(',', 1)
                suffix = {'data:image/png;base64': '.png', 'data:image/jpeg;base64': '.jpg',
                          'data:image/webp;base64': '.webp', 'data:image/gif;base64': '.gif'}.get(header)
                if not suffix:
                    raise ValueError('Gecersiz fotograf verisi')
                data = base64.b64decode(encoded, validate=True)
                if len(data) > 10 * 1024 * 1024:
                    raise ValueError('Fotograf 10 MB sinirini asiyor')
                before_files = workspace.snapshot()
                relative = 'attachments/' + job['id'] + suffix
                target = workspace.resolve(relative)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                workspace.publish(ctx, before_files)
                instruction += '\n\n' + json.dumps({'attachment': {'path': relative,
                    'ad': str(attachment.get('ad') or 'fotograf')}}, ensure_ascii=False)
            from chat.agent_runtime import AgentRunState
            state = AgentRunState(job['id'])
            mesaj_isle(instruction, brain, sistem_blogu(user), callback,
                       tools=catalog, gecmis_override=history,
                       run_state=state, platform_resume=saved,
                       tool_policy=context.get('tool_policy', 'auto'),
                       tercih=saved.get('provider') or ([provider] if provider else None),
                       tazele=bool(context.get('tazele')))
            callback.flush()
            if callback.error:
                return {'status': 'failed', 'reason': callback.error}
            control.artifact('answer', title='Basak sonucu', content=callback.answer,
                             media_type='text/markdown')
            validate_acceptance(job, control, workspace)
            return {'answer': callback.answer,
                    **({'status': 'partial', 'reason': state.truncated_reason}
                       if state.truncated_reason else {})}
        except ExecutionBlocked as blocked:
            return {'status': blocked.state, 'reason': blocked.reason}
        except ExecutionUnavailable as exc:
            return {'status': 'blocked', 'reason': str(exc)}
