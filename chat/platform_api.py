"""Authenticated HTTP observer for the durable Python task runtime.

The app supplies its principal resolver. Streamed chats may be claimed
by the HTTP host; persistent subagents remain on independent workers.
"""
import asyncio
import base64
import inspect
import json
import logging
import os
import re
from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

from chat.platform_runtime import Conflict, NotFound, RuntimeStore, TERMINAL, Unavailable, WorkerUnavailable
from chat.kosu_deposu import platform_store
import time


router = APIRouter(prefix="/api/kosu", tags=["tasks"])
_principal = None
_store_factory = platform_store


def configure(principal, store_factory=None):
    """Install the host app's authenticated identity dependency."""
    global _principal, _store_factory
    _principal = principal
    _store_factory = store_factory or platform_store


def _mutation_origin_ok(request):
    """Cookie-authenticated writes must come from the exact same origin.

    Sec-Fetch-Site 'same-site' is not sufficient when another subdomain can
    submit a request. Origin is required even when fetch metadata is absent.
    """
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return True
    site = request.headers.get("sec-fetch-site", "").lower()
    if site and site != "same-origin":
        return False
    origin = request.headers.get("origin", "")
    if not origin:
        return False
    source, target = urlsplit(origin), urlsplit(str(request.url))
    return bool(source.scheme in ("https", "http") and source.netloc
                and source.scheme == target.scheme
                and source.netloc == target.netloc
                and source.path in ("", "/") and not source.query
                and not source.fragment and not source.username
                and not source.password)


async def _user(request):
    if not _mutation_origin_ok(request):
        raise HTTPException(403, "Bu hesap islemi ayni kaynaktan yapilmali")
    if _principal is None:
        raise HTTPException(503, "Görev kimlik doğrulaması yapılandırılmadı")
    user = _principal(request)
    if inspect.isawaitable(user):
        user = await user
    if isinstance(user, dict):
        user = user.get("user_id") or user.get("id")
    if not isinstance(user, str) or not user.strip():
        raise HTTPException(401, "Bu işlem için hesabınla giriş yapmalısın")
    return user


def _store():
    try:
        return _store_factory()
    except Unavailable as exc:
        raise HTTPException(503, str(exc)) from exc


async def _body(request):
    try:
        value = await request.json()
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(400, "Geçersiz JSON") from exc
    if not isinstance(value, dict):
        raise HTTPException(400, "İstek bir JSON nesnesi olmalı")
    return value


def _call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except NotFound as exc:
        raise HTTPException(404, str(exc)) from exc
    except Conflict as exc:
        raise HTTPException(409, str(exc)) from exc
    except (TypeError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc
    except Unavailable as exc:
        raise HTTPException(503, str(exc)) from exc


def _durable_acik():
    """Kalici sohbet varsayilan olarak acik mi?

    Once yalniz `BASAK_DURABLE_CHAT_ENABLED=true` ile aciliyordu; sonuc:
    Postgres varken bile sahip hesabi her zaman eski (ExecutionContext'suz)
    yola dusuyor, `alt_ajan` bu yuzden hic calismiyordu. Artik karar
    ortamdan degil, kalici deponun GERCEKTEN hazir olmasindan gelir;
    acikca "false" yazilirsa kapatilir. Isci yoksa `allow_legacy` ayni
    istegi eski yola dondurur (davranis degismez, is kaybolmaz).
    """
    ham = os.environ.get('BASAK_DURABLE_CHAT_ENABLED')
    if ham is not None:
        return ham.strip().lower() == 'true'
    try:
        from chat import veritabani
        return veritabani.hazir()
    except Exception:
        return False


def _json(value, status=200):
    return JSONResponse(value, status_code=status, headers={"Cache-Control": "no-store"})


async def chat_response(request, user, body, history):
    """Persist an account chat turn; HTTP only observes the existing worker."""
    from chat.private_access_api import private_only
    from chat.platform_identity import browser_access_enabled
    strict = private_only() or browser_access_enabled()
    if not _mutation_origin_ok(request):
        raise HTTPException(403, 'Bu hesap islemi ayni kaynaktan yapilmali')
    enabled = _durable_acik()
    # Transport only, never text or model-name classification.
    foreground = (enabled
                  and 'application/x-ndjson' in request.headers.get('accept', '')
                  and os.environ.get('BASAK_FOREGROUND_CHAT', 'true').lower() != 'false')
    key = request.headers.get('Idempotency-Key')
    if not enabled and not key:
        if strict:
            raise HTTPException(503, 'Kalici gorev sistemi kapali; is baslatilmadi')
        return None
    # A database failure cannot prove that a previously submitted write did
    # not happen. Propagate it; never replay an ambiguous request in legacy.
    store = _store()
    previous = _call(store.request_run, user, 'personal', key)
    if not previous and (body.get('kosu_id') or body.get('yonlendirme_baglami')):
        if strict:
            raise HTTPException(409, 'Bu eski gorev otomatik yeniden baslatilamaz; onceki sonucu kontrol edin')
        return None  # Continue an existing legacy run in its original engine.
    from chat.agent_runtime import normalize_tool_policy
    text = str(body.get('metin') or '').strip()
    if body.get('belge'):
        from chat.belge import istemciden_blogu, BelgeHatasi
        try:
            text = (text + '\n\n' + istemciden_blogu(body['belge'])).strip()
        except BelgeHatasi as exc:
            raise HTTPException(400, str(exc)) from exc
    if not text and not body.get('ek'):
        raise HTTPException(400, 'Bos mesaj')
    if body.get('ek'):
        attachment = body['ek']
        if not isinstance(attachment, dict) or attachment.get('tur') != 'image':
            raise HTTPException(400, 'Gecersiz fotograf verisi')
        try:
            header, encoded = str(attachment.get('data_url') or '').split(',', 1)
            if header not in {'data:image/png;base64', 'data:image/jpeg;base64',
                              'data:image/webp;base64', 'data:image/gif;base64'}:
                raise ValueError('Gecersiz fotograf verisi')
            if len(base64.b64decode(encoded, validate=True)) > 10 * 1024 * 1024:
                raise ValueError('Fotograf 10 MB sinirini asiyor')
        except ValueError as exc:
            raise HTTPException(400, 'Gecersiz veya cok buyuk fotograf') from exc
    conversation_id = body.get('conversation_id')
    if conversation_id is not None and (not isinstance(conversation_id, str)
            or not re.fullmatch(r'[A-Za-z0-9_.-]{1,128}', conversation_id)):
        raise HTTPException(400, 'Gecersiz sohbet kimligi')
    title = body.get('conversation_title')
    if title is not None and (not isinstance(title, str) or len(title) > 256):
        raise HTTPException(400, 'Gecersiz sohbet basligi')
    display_text = str(body.get('metin') or ('Belge gönderildi' if body.get('belge') else 'Fotoğraf gönderildi'))
    context = {'conversation_id': conversation_id, 'conversation_title': title,
               'display_text': display_text, 'history': history, 'tool_policy': _call(normalize_tool_policy, body.get('tool_policy')),
               'tazele': bool(body.get('tazele')), 'attachment': body.get('ek')}
    try:
        run = store.create(user, 'personal', text or 'Bu goruntuyu acikla.',
                           kind='chat', context=context, request_key=key,
                           require_worker=not foreground,
                           allow_legacy=not strict and not foreground,
                           durable_enabled=enabled)
    except WorkerUnavailable:
        if strict:
            raise HTTPException(503, 'Gorev iscisine ulasilamiyor; is baslatilmadi')
        return None  # Transaction rolled back; no durable work has started.
    except Conflict as exc:
        raise HTTPException(409, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Unavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    if run is None:
        if strict:
            raise HTTPException(503, 'Kalici gorev baslatilamadi')
        return None
    rid = run['id']
    durable_event = {'istek': rid, 'tur': 'durableRun', 'kosu_id': rid,
                     'conversation_id': conversation_id or rid,
                     'conversation_title': title, 'display_text': display_text}

    async def observe():
        cursor, started = 0, time.monotonic()
        # A previous submission can persist the run and lose the HTTP stream
        # before the generator starts. Replaying the same Idempotency-Key must
        # still start that queued run. Atomic claim(run_id) prevents doubles;
        # a running/completed run is only observed, never re-executed.
        if foreground and run['durum'] == 'queued':
            from chat.platform_agents import execute_job
            from chat.platform_runtime import Worker
            worker = Worker(store, execute_job, worker_id='web-' + rid,
                            lease_seconds=90)
            running = asyncio.create_task(
                asyncio.to_thread(worker.tick, rid))
            def completed(task):
                try:
                    task.result()
                except Exception:
                    logging.getLogger(__name__).exception('Web sohbet calismasi hata verdi')
            running.add_done_callback(completed)
        yield json.dumps(durable_event, ensure_ascii=False) + '\n'
        while not await request.is_disconnected():
            try:
                if await _user(request) != user:
                    raise HTTPException(401, 'Oturum degisti')
            except HTTPException:
                yield json.dumps({'istek': rid, 'tur': 'error', 'metin': 'Hesap oturumu sona erdi'}) + '\n'
                break
            batch = await asyncio.to_thread(store.events, user, rid, after=cursor)
            for event in batch:
                cursor = event['seq']
                # Only root chat emissions belong in this conversation.
                if event['payload'].get('origin_run_id'):
                    continue
                if event['type'] == 'chat' and event['payload'].get('tur') == 'bitir':
                    continue  # Publish final only after the durable outcome commits.
                if event['type'] == 'chat':
                    yield json.dumps({'istek': rid, **event['payload']}, ensure_ascii=False) + '\n'
                elif event['type'] not in {'status', 'checkpoint', 'artifact', 'provider'}:
                    yield json.dumps({'istek': rid, 'tur': event['type'], **event['payload']}, ensure_ascii=False) + '\n'
            current = await asyncio.to_thread(store.get, user, rid)
            state = current['durum']
            if state in TERMINAL or state == 'verifying':
                if current['answer']:
                    yield json.dumps({'istek': rid, 'tur': 'bitir', 'cevap': current['answer'],
                                      'kaynak': current['provider']}, ensure_ascii=False) + '\n'
                else:
                    yield json.dumps({'istek': rid, 'tur': 'error',
                                      'metin': current['hata'] or state}, ensure_ascii=False) + '\n'
                break
            if state in {'awaiting_approval', 'awaiting_connection', 'paused'} or time.monotonic() - started >= 240:
                # Closing an observer never pauses/cancels the worker.
                yield json.dumps({'istek': rid, 'tur': 'checkpoint', 'kosu_id': rid}) + '\n'
                break
            yield json.dumps({'istek': rid, 'tur': 'ping'}) + '\n'
            await asyncio.sleep(1)
    if 'application/x-ndjson' in request.headers.get('accept', ''):
        return StreamingResponse(observe(), media_type='application/x-ndjson',
                                 headers={'Cache-Control': 'no-store', 'X-Basak-Run-ID': rid})
    return _json({'ok': True, 'kosu_id': rid, 'olaylar': [
        durable_event,
        {'istek': rid, 'tur': 'checkpoint', 'kosu_id': rid}]}, 202)


@router.get('/sohbetler')
async def chat_threads(request: Request):
    return _json({'chats': _call(_store().chat_threads, await _user(request))})


@router.get('/{run_id}/islemler')
async def actions(run_id: str, request: Request):
    user = await _user(request)
    return _json({'actions': _call(_store().actions, user, run_id)})


@router.post('/{run_id}/uzlastir')
async def reconcile(run_id: str, request: Request):
    user, body = await _user(request), await _body(request)
    if set(body) != {'call_id'}:
        raise HTTPException(400, 'Yalniz cagri kimligi kabul edilir; sonuc saglayicidan okunur')
    store = _store()
    run = _call(store.get, user, run_id)
    action = next((a for a in _call(store.actions, user, run_id) if a['call_id'] == body['call_id']), None)
    if run['durum'] != 'uncertain' or action is None or action['status'] != 'uncertain':
        raise HTTPException(409, 'Belirsiz islem bulunamadi')
    from chat.platform_connectors import observe_uncertain_action, ConnectorError
    try:
        observation = await asyncio.to_thread(observe_uncertain_action, user, action)
    except (ConnectorError, PermissionError, ValueError, KeyError) as exc:
        raise HTTPException(409, str(exc)) from exc
    aid = _call(store.add_artifact, user, run_id, {
        'kind': 'external_observation', 'title': 'Saglayici dogrulamasi',
        'content': json.dumps(observation, ensure_ascii=False), 'media_type': 'application/json',
        'call_id': action['call_id'], 'arguments_digest': action['digest'],
        'verified': True, 'result': observation['result']})
    _call(store.reconcile_action, user, run_id, action['call_id'], observation['result'], True,
          {'artifact_id': aid, 'reviewer': user, 'kind': 'provider_read'})
    return _json({'ok': True, 'kosu': _call(store.tree, user, run_id)})


@router.get("/isciler")
async def workers_status(request: Request):
    await _user(request)
    return _json(_call(_store().worker_health))


@router.post("")
async def submit(request: Request):
    user, body = await _user(request), await _body(request)
    allowed = {"istek", "instruction", "workspace_id", "model_ref", "request_key", "acceptance"}
    if set(body) - allowed:
        raise HTTPException(400, "Desteklenmeyen görev alanı")
    for key in ("istek", "instruction", "workspace_id", "model_ref", "request_key"):
        if key in body and not isinstance(body[key], str):
            raise HTTPException(400, key + " metin olmalı")
    store = _store()
    if not _durable_acik():
        raise HTTPException(503, 'Kalici calisma henuz etkin degil')
    run = _call(store.create, user, body.get("workspace_id", "personal"),
                body.get("istek", body.get("instruction", "")),
                model_ref=body.get("model_ref", ""), acceptance=body.get("acceptance"),
                request_key=request.headers.get("Idempotency-Key") or body.get("request_key"),
                require_worker=True)
    return _json({"ok": True, "kosu": run}, 202)


@router.get("")
async def list_runs(request: Request, workspace_id: str | None = None,
                    after: str | None = None, limit: int = 50):
    user = await _user(request)
    rows = _call(_store().list, user, workspace_id=workspace_id, after=after, limit=limit)
    return _json({"kosular": rows, "next_cursor": rows[-1]["id"] if len(rows) >= min(limit, 200) else None})


@router.get("/{run_id}/agac")
async def run_tree(run_id: str, request: Request):
    return _json({"kosu": _call(_store().tree, await _user(request), run_id)})


@router.get("/{run_id}/olaylar")
async def events(run_id: str, request: Request, after: int = 0, stream: bool = False):
    user, store = await _user(request), _store()
    row = _call(store.get, user, run_id)
    try:
        cursor = max(after, int(request.headers.get("Last-Event-ID") or 0))
    except ValueError as exc:
        raise HTTPException(400, "Geçersiz olay imleci") from exc
    if not stream:
        batch = _call(store.events, user, run_id, after=cursor)
        return _json({"olaylar": batch, "cursor": batch[-1]["seq"] if batch else cursor,
                      "durum": row["durum"]})

    async def feed():
        nonlocal cursor
        while not await request.is_disconnected():
            batch = await asyncio.to_thread(store.events, user, run_id, after=cursor)
            for event in batch:
                cursor = event["seq"]
                yield "id: %d\nevent: %s\ndata: %s\n\n" % (
                    cursor, event["type"], json.dumps(event, ensure_ascii=False))
            current = await asyncio.to_thread(store.get, user, run_id)
            if current["durum"] in TERMINAL and cursor >= current["seq"]:
                break
            yield ": heartbeat\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(feed(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})


@router.post("/{run_id}/iptal")
async def cancel(run_id: str, request: Request):
    return _json({"ok": True, "kosu": _call(_store().cancel, await _user(request), run_id)})


@router.post("/{run_id}/devam")
async def resume(run_id: str, request: Request):
    return _json({"ok": True, "kosu": _call(_store().resume, await _user(request), run_id)})


@router.post("/{run_id}/yon")
async def steer(run_id: str, request: Request):
    user, body = await _user(request), await _body(request)
    if not isinstance(body.get("metin"), str):
        raise HTTPException(400, "Yönlendirme metni gerekli")
    return _json({"ok": True, "seq": _call(_store().steer, user, run_id, body["metin"])})


@router.post("/{run_id}/onay")
async def approve(run_id: str, request: Request):
    user, body = await _user(request), await _body(request)
    return _json({"ok": True, "kosu": _call(_store().approve, user, run_id,
                                               body.get("approval_id"), body.get("approved"))})


@router.post("/{run_id}/kabul")
async def accept(run_id: str, request: Request):
    user, body = await _user(request), await _body(request)
    return _json({"ok": True, "kosu": _call(_store().accept, user, run_id,
                                               body.get("check_id", "result_verified"),
                                               body.get("accepted"))})


@router.get("/{run_id}/artifacts/{artifact_id}")
async def artifact(run_id: str, artifact_id: str, request: Request):
    item = _call(_store().artifact, await _user(request), run_id, artifact_id)
    if "content" in item:
        content = str(item["content"]).encode("utf-8")
    elif "data_base64" in item:
        content = base64.b64decode(item["data_base64"], validate=True)
    else:
        return _json({"artifact": {k: v for k, v in item.items() if k not in ("path", "local_path")}})
    name = re.sub(r"[^A-Za-z0-9._-]", "_", item.get("title") or artifact_id)
    return Response(content, media_type=item.get("media_type") or item.get('mime_type') or "application/octet-stream",
                    headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
                             "Content-Security-Policy": "default-src 'none'; sandbox",
                             "Content-Disposition": 'attachment; filename="%s"' % name})
