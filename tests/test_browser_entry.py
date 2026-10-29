import hashlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def browser_store(monkeypatch, tmp_path):
    from chat.kosu_deposu import _SqliteDepo
    from chat.platform_connections import ConnectionStore
    from chat import kosu_deposu, private_access
    db=_SqliteDepo(str(tmp_path/'browser.db'))
    store=ConnectionStore(db)
    monkeypatch.setattr(kosu_deposu,'_DEPO',db)
    monkeypatch.setattr('chat.platform_identity.ConnectionStore',lambda:store)
    monkeypatch.setattr(private_access,'_service',private_access.PrivateAccess(store))
    monkeypatch.setenv('VERCEL_ENV','production')
    monkeypatch.setenv('BASAK_PRIVATE_ACCESS_ONLY','true')
    monkeypatch.delenv('BASAK_OTURUM_ANAHTARI',raising=False)
    return store


def test_plain_address_opens_existing_durable_chat_without_invitation(browser_store,monkeypatch):
    import app
    from chat.platform_runtime import RuntimeStore
    from chat import platform_api
    runtime=RuntimeStore(browser_store._db)
    monkeypatch.setattr(platform_api,'_store_factory',lambda:runtime)
    monkeypatch.setattr(platform_api,'_durable_acik',lambda:True)
    runtime.worker_ping('existing-oracle-worker')
    client=TestClient(app.app)
    r=client.post('/api/kimlik',headers={'Origin':'http://testserver'})
    assert r.status_code==200
    uid=r.json()['kullanici']
    assert uid!='casper'
    assert client.post('/api/kimlik',headers={'Origin':'http://testserver'}).json()['kullanici']==uid
    r=client.post('/api/sohbet',json={'metin':'Merhaba','gecmis':[]},
                  headers={'Origin':'http://testserver','Idempotency-Key':'hello-once'})
    assert r.status_code==202,r.text
    run=runtime.get(uid,r.json()['kosu_id'])
    assert run['kind']=='chat' and run['user_id']==uid
    assert client.get('/api/ozel-erisim').json()['enabled'] is False


def test_visitors_are_distinct_and_cookie_is_opaque_revocable(browser_store):
    import app
    from chat.platform_identity import COOKIE,IdentityService
    a,b=TestClient(app.app),TestClient(app.app)
    headers={'Origin':'http://testserver'}
    uid=a.post('/api/kimlik',headers=headers).json()['kullanici']
    other=b.post('/api/kimlik',json={'kullanici':'casper'},headers=headers).json()['kullanici']
    assert uid!=other and other!='casper'
    token=a.cookies[COOKIE]
    assert token.startswith('b1.') and len(token)==46
    stored=browser_store._db._sorgu('SELECT id FROM basak_account_session')
    assert token not in str(stored) and token[3:] not in str(stored)
    assert hashlib.sha256(token[3:].encode()).hexdigest() in [r['id'] for r in stored]
    identities=IdentityService(browser_store)
    assert identities.resolve_session(token)['id']==uid
    identities.revoke_session(token)
    assert identities.resolve_session(token) is None


def test_no_owner_fallback_and_cross_origin_rejected(browser_store,monkeypatch):
    import app
    client=TestClient(app.app)
    assert client.post('/api/kimlik',headers={'Origin':'https://other.test'}).status_code==403
    def unavailable(): raise RuntimeError('database unavailable')
    monkeypatch.setattr('chat.platform_identity.ConnectionStore',unavailable)
    r=client.post('/api/kimlik',headers={'Origin':'http://testserver'})
    assert r.status_code==503
    assert 'set-cookie' not in r.headers


def test_plain_address_in_real_desktop_and_mobile_browser(browser_store,monkeypatch,tmp_path):
    import socket
    import threading
    import time
    from pathlib import Path
    import uvicorn
    from playwright.sync_api import sync_playwright,expect
    import app
    from chat.platform_runtime import RuntimeStore
    monkeypatch.setattr('chat.platform_api._store_factory',lambda:RuntimeStore(browser_store._db))
    sock=socket.socket()
    sock.bind(('127.0.0.1',0))
    base='http://127.0.0.1:'+str(sock.getsockname()[1])
    server=uvicorn.Server(uvicorn.Config(app.app,log_level='error'))
    thread=threading.Thread(target=lambda:server.run(sockets=[sock]),daemon=True)
    thread.start()
    try:
        deadline=time.monotonic()+10
        while not server.started and time.monotonic()<deadline:
            time.sleep(.02)
        assert server.started
        with sync_playwright() as pw:
            if not Path(pw.chromium.executable_path).is_file():
                pytest.skip('Chromium not installed')
            browser=pw.chromium.launch()
            users=[]
            for width,height in [(1280,900),(390,844)]:
                context=browser.new_context(viewport={'width':width,'height':height})
                page=context.new_page()
                page.goto(base)
                page.wait_for_function('Boolean(window.basakKimlik)')
                uid=page.evaluate('window.basakKimlik.kullanici')
                users.append(uid)
                page.locator('#message').fill('Merhaba')
                expect(page.locator('#send')).to_be_enabled()
                assert 'özel bağlantıyla açmalısın' not in page.locator('body').inner_text()
                assert page.locator('dialog[open]').count()==0
                page.reload()
                page.wait_for_function('Boolean(window.basakKimlik)')
                assert page.evaluate('window.basakKimlik.kullanici')==uid
                context.close()
            assert users[0]!=users[1]
            browser.close()
    finally:
        server.should_exit=True
        thread.join(timeout=10)
        sock.close()
