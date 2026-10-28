"""Model-selected cloud tools bound to an authenticated durable run."""
import json
import logging
import os

from chat.platform_context import require

logger = logging.getLogger(__name__)

NAMES = frozenset(('ajan_modelleri', 'alt_ajan', 'alt_ajan_sonuclari',
                   'baglanti_liste', 'baglanti_araclari', 'baglanti_cagir',
                   'kod_dosya', 'kod_calistir', 'bulut_tarayici'))


def models(brain):
    from brain.model_havuzu import katalog
    catalog = katalog()
    result = [{'id': 'primary', 'provider': 'automatic', 'model': '', 'tools': True}]
    for provider, client in brain._bulut_zinciri(tools=True):
        result.append({'id': provider, 'provider': provider, 'model': getattr(client, 'model', ''),
                       'tools': True})
        if getattr(getattr(client, 'client', None), 'provider', '') == provider:
            result.extend({'id': provider + ':' + m['id'], 'provider': provider,
                           'model': m['id'], 'tools': bool(m.get('tools'))}
                          for m in catalog.get(provider, []) if m.get('tools'))
    return result


def selection(brain, ref):
    """Model referansini (saglayici, model) ciftine cevirir.

    Roller ortam degiskeniyle tanimlanir; kod hangi modelin "iyi"
    olduguna karar vermez:
      BASAK_KOMUTAN_MODEL=groq:llama-...  (kok gorev / sohbet)
      BASAK_ISCI_MODEL=groq:gpt-oss-...   (alt ajanlar)
    Tanimli degilse ucretsiz havuzun varsayilan secimi kullanilir.
    """
    ref = str(ref or 'primary').strip()
    # Serbest modeller model adini kendi uydurur ("default", "auto"). Bunlar
    # "ozel model secilmedi" demektir; gecersiz sayip alt ajani kilitlemek
    # yerine havuzun varsayilan secimine donulur. Eslesme disinda model
    # kimliginin harf duyarliligi KORUNUR.
    if ref.lower() in ('', 'primary', 'default', 'auto', 'automatic',
                       'otomatik', 'varsayilan', 'varsayılan'):
        ref = 'primary'
    rol = {'komutan': 'BASAK_KOMUTAN_MODEL', 'isci': 'BASAK_ISCI_MODEL'}.get(ref)
    if rol:
        ham = (os.environ.get(rol) or '').strip()
        if not ham:
            return ('', '')
        ref = ham
    mevcut = models(brain)
    found = next((m for m in mevcut if m['id'] == ref), None)
    if found is None and rol:
        # Rol tanimli ama havuzda yok: yanlis yazilmis ortam degiskeni tum
        # alt ajanlari kilitlemesin. Sessiz degil — uyari loglanir.
        logger.warning("%s gecersiz (%r); varsayilan secime donuluyor",
                       rol, ref)
        return ('', '')
    if found is None:
        raise ValueError('Model secimi kullanilabilir ucretsiz havuzda yok')
    return ('', '') if ref == 'primary' else (found['provider'], found['model'] if ':' in ref else '')


def _workspace(ctx):
    from worker.platform_execution import Workspace
    from chat.kimlik import state_kok
    return Workspace(state_kok(), ctx.user_id, ctx.workspace_id, ctx.run_id)


def _connections():
    from chat.platform_connections import ConnectionStore
    return ConnectionStore()


def execute(name, args):
    ctx = require()
    args = dict(args or {})
    if ctx.allowed_tools is not None and name not in ctx.allowed_tools:
        raise PermissionError('Bu alt gorevin bu araca erisimi yok')
    control = ctx.control
    if control is None:
        raise PermissionError('Kalici gorev yurutme yetkisi yok')
    control.check_cancelled()
    if name == 'ajan_modelleri':
        return {'result': models(ctx.brain)}
    if name == 'alt_ajan':
        store = control.store
        jobs = args.get('isler')
        if not isinstance(jobs, list) or not jobs:
            raise ValueError('isler bos olmayan gorev listesi olmali')
        if store.max_children_per_parent is not None and len(jobs) > store.max_children_per_parent:
            raise ValueError('Tek seferde alt ajan siniri asildi')
        created = []
        for job in jobs:
            if not isinstance(job, dict) or not str(job.get('gorev') or '').strip():
                raise ValueError('Her alt gorev aciklamasi gerekli')
            selection(ctx.brain, job.get('model_ref', 'isci'))
            allowed = job.get('araclar')
            if allowed is not None and (not isinstance(allowed, list) or not all(
                    isinstance(t, str) for t in allowed)):
                raise ValueError('araclar isim listesi olmali')
            parent_tools = ctx.allowed_tools
            if parent_tools is not None and allowed is not None and set(allowed) - parent_tools:
                raise PermissionError('Alt gorev ust gorevin yetkisini genisletemez')
        for i, job in enumerate(jobs):
            request_key = '%s:%s:%s' % (ctx.run_id, ctx.tool_call_id, i)
            created.append(store.create(ctx.user_id, ctx.workspace_id, job['gorev'],
                parent_id=ctx.run_id, model_ref=job.get('model_ref', 'isci'),
                dependencies=job.get('bagimliliklar', []),
                allowed_tools=job.get('araclar'), acceptance=job.get('kabul') or None,
                context={'task_context': job.get('baglam', '')}, request_key=request_key))
        return {'result': [{'id': j['id'], 'durum': j['durum']} for j in created]}
    if name == 'alt_ajan_sonuclari':
        tree = control.store.tree(ctx.user_id, ctx.run_id)
        children = tree.get('children', [])
        pending = [c['id'] for c in children if c['durum'] not in (
            'completed', 'partial', 'failed', 'cancelled', 'uncertain', 'blocked')]
        result = {'children': children}
        if args.get('bekle') and pending:
            result['_wait_children'] = pending
        return {'result': json.dumps(result, ensure_ascii=False)}
    if name == 'baglanti_liste':
        return {'result': _connections().list(ctx.user_id)}
    if name == 'baglanti_araclari':
        from chat.platform_connectors import list_tools
        return {'result': list_tools(ctx.user_id, str(args.get('baglanti_id') or ''))}
    if name == 'baglanti_cagir':
        from chat.platform_connectors import execute as call
        result = call(ctx.user_id, str(args.get('baglanti_id') or ''),
                      str(args.get('arac') or ''), dict(args.get('argumanlar') or {}))
        if result.get('isError'):
            return {'error': 'Bagli platform islemi basarisiz', 'result': result}
        control.artifact('platform_result', title=str(args.get('arac') or ''),
                         content=json.dumps(result, ensure_ascii=False), mime_type='application/json')
        return {'result': result}
    if name == 'kod_dosya':
        workspace = _workspace(ctx)
        op = args.get('islem')
        if op == 'liste':
            result = workspace.files()
        elif op == 'oku':
            result = workspace.read(args.get('yol'), args.get('baslangic', 0))
        elif op == 'yaz':
            result = workspace.write(args.get('yol'), args.get('icerik', ''))
        else:
            raise ValueError('Dosya islemi liste, oku veya yaz olmali')
        return {'result': result}
    if name == 'kod_calistir':
        from worker.platform_execution import Sandbox
        language = str(args.get('ortam') or '')
        if language not in ('python', 'node'):
            raise ValueError('Ortam python veya node olmali; Flutter Android GitHub iscisi kullanir')
        image = os.environ.get('BASAK_SANDBOX_IMAGE_' + language.upper(), '')
        result = Sandbox(_workspace(ctx).path, image, control).run(
            args.get('komut'), timeout=args.get('sure_saniye', 900))
        control.artifact('terminal', title=' '.join(args.get('komut') or []),
                         content=result['stdout'] + '\n' + result['stderr'],
                         exit_code=result['exit_code'], mime_type='text/plain')
        return {'result': result} if result['exit_code'] == 0 else {
            'error': 'Komut basarisiz: cikis kodu %s' % result['exit_code'], 'result': result}
    if name == 'bulut_tarayici':
        from worker.platform_browser import execute_browser
        outcome = execute_browser(ctx, str(args.get('islem') or ''),
                                  dict(args.get('argumanlar') or {}))
        if outcome.get('ok') is not True:
            return {'error': 'Tarayici islemi basarisiz: ' +
                    str(outcome.get('status') or 'unknown'), 'result': outcome}
        return {'result': outcome}
    raise ValueError('Bilinmeyen platform araci')
