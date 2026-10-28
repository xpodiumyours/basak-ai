import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from chat import kosu_deposu
from chat.platform_connections import ConnectionStore
from chat.private_access import PrivateAccess


@pytest.fixture
def access(tmp_path):
    return PrivateAccess(ConnectionStore(kosu_deposu._SqliteDepo(str(tmp_path / 'access.db'))))


def test_personal_links_have_separate_identity_and_revocation(access):
    owner = access.bootstrap_owner()
    alice = access.create('casper', 'Alice')
    bob = access.create('casper', 'Bob')
    a, b = access.redeem(alice['code']), access.redeem(bob['code'])
    assert access.resolve(a)['id'] != access.resolve(b)['id']
    assert access.resolve(access.redeem(owner['code']))['id'] == 'casper'
    with pytest.raises(PermissionError):
        access.create(alice['user_id'], 'Unauthorized')
    access.revoke('casper', alice['id'])
    assert access.resolve(a) is None
    assert access.resolve(b)['id'] == bob['user_id']
    with pytest.raises(PermissionError):
        access.redeem(alice['code'])


def test_neither_links_nor_sessions_are_saved_in_plain_text(access):
    link = access.bootstrap_owner()
    token = access.redeem(link['code'])
    dump = json.dumps(access.db._sorgu('SELECT * FROM basak_private_invite') +
                      access.db._sorgu('SELECT * FROM basak_private_session'))
    assert link['code'] not in dump
    assert token[3:] not in dump
    access.logout(token)
    assert access.resolve(token) is None


def test_link_opening_uses_existing_authentication_and_rejects_cross_origin(access, monkeypatch):
    from chat import private_access, private_access_api
    from chat.platform_identity import COOKIE, authenticate
    monkeypatch.setattr(private_access, '_service', access)
    app = FastAPI()
    app.include_router(private_access_api.router)
    link = access.bootstrap_owner()
    client = TestClient(app)
    assert client.post('/api/ozel-erisim/ac',json={'code':link['code']},
                       headers={'Origin':'https://other.test'}).status_code == 403
    response = client.post('/api/ozel-erisim/ac',json={'code':link['code']},
                           headers={'Origin':'http://testserver'})
    assert response.status_code == 200
    assert 'httponly' in response.headers['set-cookie'].lower()
    assert 'samesite=lax' in response.headers['set-cookie'].lower()
    assert COOKIE in client.cookies
    from starlette.requests import Request
    request = Request({'type':'http','headers':[(b'cookie',
        (COOKIE+'='+client.cookies[COOKIE]).encode())]})
    assert authenticate(request) == 'casper'
    assert client.get('/api/ozel-erisim/davetler').status_code == 200
    assert client.post('/api/ozel-erisim/davetler',json={'label':'Friend','role':'owner'},
                       headers={'Origin':'http://testserver'}).status_code == 400


def test_invalid_link_and_no_cookie_never_fall_back_to_owner(access, monkeypatch):
    from chat import private_access, private_access_api
    monkeypatch.setattr(private_access, '_service', access)
    app=FastAPI(); app.include_router(private_access_api.router)
    client=TestClient(app)
    assert client.get('/api/ozel-erisim/davetler').status_code == 401
    assert client.post('/api/ozel-erisim/ac',json={'code':'x'*43},
                       headers={'Origin':'http://testserver'}).status_code == 403
    assert not client.cookies


def test_private_only_does_not_create_an_anonymous_identity(monkeypatch):
    import app as host
    monkeypatch.setenv('BASAK_PRIVATE_ACCESS_ONLY','true')
    monkeypatch.setattr(host,'_platform_kimlik',lambda request: None)
    monkeypatch.setattr(host,'_token_kimligi',lambda request: None)
    response=TestClient(host.app).post('/api/kimlik')
    assert response.status_code == 401
    assert 'set-cookie' not in response.headers


def test_session_expires_and_survives_service_restart(access):
    now=[1000.0]
    access.clock=lambda:now[0]
    owner=access.bootstrap_owner()
    token=access.redeem(owner['code'])
    reopened=PrivateAccess(access.store,clock=lambda:now[0])
    assert reopened.resolve(token)['id']=='casper'
    from chat.private_access import SESSION_SECONDS
    now[0]+=SESSION_SECONDS+1
    assert reopened.resolve(token) is None


def test_distinct_private_links_cannot_read_each_others_real_tasks(access, monkeypatch):
    from chat import platform_api, private_access
    from chat.platform_identity import authenticate, COOKIE
    from chat.platform_runtime import RuntimeStore
    monkeypatch.setattr(private_access,'_service',access)
    runtime=RuntimeStore(access.db)
    access.bootstrap_owner()
    alice=access.create('casper','Alice'); bob=access.create('casper','Bob')
    a=access.redeem(alice['code']); b=access.redeem(bob['code'])
    run=runtime.create(alice['user_id'],'personal','Alice private task')
    monkeypatch.setattr(platform_api,'_principal',authenticate)
    monkeypatch.setattr(platform_api,'_store_factory',lambda:runtime)
    app=FastAPI(); app.include_router(platform_api.router)
    client=TestClient(app)
    client.cookies.set(COOKIE,b)
    assert client.get('/api/kosu/'+run['id']+'/agac').status_code==404
    client.cookies.set(COOKIE,a)
    assert client.get('/api/kosu/'+run['id']+'/agac').status_code==200


def test_account_requests_do_not_repeat_database_table_setup(tmp_path, monkeypatch):
    db=kosu_deposu._SqliteDepo(str(tmp_path/'schema.db'))
    statements=[]
    original=db._calistir
    def execute(sql,params=()):
        statements.append(sql)
        return original(sql,params)
    monkeypatch.setattr(db,'_calistir',execute)
    ConnectionStore(db)
    count=len(statements)
    assert count>0
    ConnectionStore(db)
    assert len(statements)==count


def test_private_link_reaches_real_chat_identity_and_refuses_legacy_guest_mode(access, monkeypatch):
    import app as host
    from chat import private_access
    from chat.platform_identity import COOKIE
    from starlette.requests import Request
    monkeypatch.setenv('BASAK_PRIVATE_ACCESS_ONLY','true')
    monkeypatch.setattr(private_access,'_service',access)
    owner=access.bootstrap_owner()
    token=access.redeem(owner['code'])
    request=Request({'type':'http','headers':[(b'cookie',(COOKIE+'='+token).encode())]})
    assert host._kimlik(request)=='casper'
    client=TestClient(host.app)
    client.cookies.set(COOKIE,token)
    response=client.post('/api/sohbet',json={'metin':'test','misafir':True},headers={'Origin':'http://testserver'})
    assert response.status_code==400
    assert 'Misafir' in response.json()['error']
