"""Authenticated HTTP observer for the durable Python task runtime.

The app supplies its principal resolver. Routes never start an in-request
execution thread; ``python -m worker.platform`` consumes the persisted queue.
"""
import asyncio
import base64
import inspect
import json
import re
from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

from chat.platform_runtime import Conflict, NotFound, RuntimeStore, TERMINAL, Unavailable
from chat.kosu_deposu import platform_store


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


def _json(value, status=200):
    return JSONResponse(value, status_code=status, headers={"Cache-Control": "no-store"})


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
    run = _call(store.create, user, body.get("workspace_id", "personal"),
                body.get("istek", body.get("instruction", "")),
                model_ref=body.get("model_ref", ""), acceptance=body.get("acceptance"),
                request_key=request.headers.get("Idempotency-Key") or body.get("request_key"))
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
    return Response(content, media_type=item.get("media_type") or "application/octet-stream",
                    headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
                             "Content-Security-Policy": "default-src 'none'; sandbox",
                             "Content-Disposition": 'attachment; filename="%s"' % name})
