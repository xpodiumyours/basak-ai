import os

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from chat.private_access import SESSION_SECONDS, service
from chat.platform_identity import COOKIE, authenticate
from chat.platform_api import _mutation_origin_ok

router = APIRouter(prefix='/api/ozel-erisim')


def private_only():
    from chat.platform_identity import browser_access_enabled
    if browser_access_enabled():
        return False
    return os.environ.get('BASAK_PRIVATE_ACCESS_ONLY', '').lower() == 'true'


def _response(data, status=200):
    return JSONResponse(data, status_code=status, headers={'Cache-Control':'no-store'})


def _guard(request):
    if not _mutation_origin_ok(request):
        raise HTTPException(403, 'Bu işlem aynı sayfadan yapılmalı', headers={'Cache-Control':'no-store'})


def _actor(request):
    uid = authenticate(request)
    if not uid:
        raise HTTPException(401, 'Özel bağlantınla açmalısın')
    return uid


@router.get('')
def status(request: Request):
    uid = authenticate(request)
    return _response({'enabled':private_only(), 'authenticated':bool(uid),
                      'owner':bool(uid and service().owner(uid))})


@router.post('/ac')
async def redeem(request: Request):
    _guard(request)
    try:
        body = await request.json()
        if not isinstance(body, dict) or set(body) != {'code'}:
            return _response({'error':'Geçersiz bağlantı'},400)
        token = service().redeem(body['code'])
    except (PermissionError, ValueError):
        return _response({'error':'Bu özel bağlantı geçersiz veya kapatılmış'},403)
    response = _response({'ok':True})
    response.set_cookie(COOKIE,token,max_age=SESSION_SECONDS,path='/',httponly=True,
        secure=request.url.scheme=='https' or bool(os.environ.get('VERCEL') or os.environ.get('BASAK_URETIM')),
        samesite='lax')
    return response


@router.get('/davetler')
def invites(request: Request):
    uid = _actor(request)
    try:
        return _response({'invites':service().list(uid)})
    except PermissionError:
        return _response({'error':'Bu alan yalnız Başak’ın sahibine açık'},403)


@router.post('/davetler')
async def create_invite(request: Request):
    _guard(request)
    uid = _actor(request)
    try:
        body = await request.json()
        if not isinstance(body,dict) or set(body) != {'label'}:
            return _response({'error':'Yalnız kişinin adını yazmalısın'},400)
        link = service().create(uid,body['label'])
        return _response(link,201)
    except PermissionError:
        return _response({'error':'Bu alan yalnız Başak’ın sahibine açık'},403)
    except ValueError:
        return _response({'error':'Kişinin adı 1–100 karakter olmalı'},400)


@router.post('/davetler/{invite_id}/kapat')
def revoke_invite(invite_id: str, request: Request):
    _guard(request)
    uid = _actor(request)
    try:
        service().revoke(uid,invite_id)
        return _response({'ok':True})
    except PermissionError:
        return _response({'error':'Bu alan yalnız Başak’ın sahibine açık'},403)
    except ValueError:
        return _response({'error':'Bu bağlantı kapatılamaz'},400)
