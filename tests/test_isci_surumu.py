"""Suresi gecmis surumle calisan isci yeni is almaz (2026-11-03).

Neden: Oracle sunucusundaki isci 30 Ekim kodunda kaldi ve yeni surumun
duzelttigi baglam patlamasini tasimiyordu; kuyruk onu "hazir" saydigi
icin her sohbet 519 bin tokenlik istekle saglayicilarda patliyordu.
Kuyruk artik yalniz kendi surumunu tasiyan isciyi hazir sayar; boyle bir
isci yoksa is eski (istek icinde calisan) yola duser.
"""
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from chat import kosu_deposu, platform_api
from chat.platform_runtime import RuntimeStore, runtime_surum


@pytest.fixture
def admission(tmp_path, monkeypatch):
    clock = [1000.0]
    store = RuntimeStore(kosu_deposu._SqliteDepo(str(tmp_path / 'surum.db')),
                         clock=lambda: clock[0])
    monkeypatch.setattr(platform_api, '_store_factory', lambda: store)
    monkeypatch.setattr(platform_api, '_principal', lambda request: 'alice')
    monkeypatch.setenv('BASAK_DURABLE_CHAT_ENABLED', 'true')
    legacy = []
    app = FastAPI()

    @app.post('/chat')
    async def chat(request: Request):
        body = await request.json()
        response = await platform_api.chat_response(request, 'alice', body, [])
        if response is not None:
            return response
        legacy.append(body['metin'])
        return {'engine': 'legacy'}

    return TestClient(app, headers={'Origin': 'http://testserver'}), store, clock, legacy


def test_kalp_atisi_surumu_yazar(tmp_path):
    store = RuntimeStore(kosu_deposu._SqliteDepo(str(tmp_path / 'kalp.db')),
                         clock=lambda: 1000.0)
    store.worker_ping('worker')
    with store.transaction(readonly=True) as tx:
        satir = tx.one('SELECT surum FROM basak_platform_worker_presence WHERE worker_id=%s',
                       ('worker',))
    assert satir['surum'] == runtime_surum()


def test_eski_surumlu_isci_yeni_is_alamaz(admission):
    client, store, _, legacy = admission
    store.worker_ping('eski-isci', surum='p2-provider-neutral-v2')
    cevap = client.post('/chat', json={'metin': 'github repolarimi listele'})
    assert cevap.json() == {'engine': 'legacy'}
    assert legacy == ['github repolarimi listele']
    assert store.list('alice') == []


def test_guncel_surumlu_isci_is_alir(admission):
    client, store, _, legacy = admission
    store.worker_ping('yeni-isci')
    cevap = client.post('/chat', json={'metin': 'merhaba'})
    assert cevap.status_code == 202
    assert legacy == []
    assert len(store.list('alice')) == 1
