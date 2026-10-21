"""tests/test_eklenti_ws_bulut.py — bulut kanalı uçtan uca (gerçek WS).

Sözleşme:
- Eklenti `wss://<site>/api/eklenti`'ye bağlanır; sohbet ve sayfa isteği
  AYNI bağlantıdan gider (instance çivili kalır, yönlendirme gerekmez).
- `sayfa_bakis` çağrısı, aktif kanal varsa eklentiye `sayfa_gozlem` isteği
  yollar ve cevabı bekler.
- Panel cevabı `{id, ok, sonuc:{cevap, kaynak}}` biçimindedir.
- Boş mesaj / bilinmeyen işlem açık hatayla döner; sessiz yutma yok.

Model çağrılmaz: `app._cekirdek` ve `chat.flow.mesaj_isle` sahtelenir.
"""

import json
import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app as app_modulu  # noqa: E402
from tools import tarayici_kanal  # noqa: E402

GOZLEM = {
    "url": "https://ornek.test/sepet",
    "baslik": "Sepet",
    "ogeler": [
        {"rol": "button", "ad": "Sepete ekle", "kapali": False},
        {"rol": "link", "ad": "Anasayfa", "kapali": False},
    ],
}


@pytest.fixture
def istemci(monkeypatch):
    monkeypatch.setattr(app_modulu, "_cekirdek",
                        lambda: (object(), []))

    def sahte_mesaj_isle(metin, beyin, kisilik, ayikla, toollar,
                         misafir=False, **fazla):
        from tools.tarayici_kopru import sayfa_bakis

        sonuc = sayfa_bakis()
        if "error" in sonuc:
            ayikla("BasakUI.error(%s)" % json.dumps(sonuc["error"]))
            return
        adet = len(sonuc.get("ogeler") or [])
        ayikla("BasakUI.bitir(%s, %s)" % (
            json.dumps("Sayfa %s, %d oge" % (sonuc["sayfa"]["baslik"], adet)),
            json.dumps("kanal-prova")))

    monkeypatch.setattr("chat.flow.mesaj_isle", sahte_mesaj_isle)
    return TestClient(app_modulu.app)


def test_sayfa_gozlemi_ayni_kanaldan_gidip_gelir(istemci):
    with istemci.websocket_connect("/api/eklenti") as ws:
        ws.send_json({"id": "p1", "islem": "sohbet",
                      "veri": {"metin": "bu sayfada ne var?"}})

        istek = ws.receive_json()
        assert istek["islem"] == "sayfa_gozlem", istek

        ws.send_json({"id": istek["id"], "ok": True, "sonuc": GOZLEM})
        cevap = ws.receive_json()

    assert cevap["id"] == "p1"
    assert cevap["ok"] is True, cevap
    assert cevap["sonuc"]["kaynak"] == "kanal-prova"
    assert "Sepet" in cevap["sonuc"]["cevap"]
    assert "2 oge" in cevap["sonuc"]["cevap"]


def test_bos_mesaj_acik_hata(istemci):
    with istemci.websocket_connect("/api/eklenti") as ws:
        ws.send_json({"id": "p2", "islem": "sohbet", "veri": {"metin": "  "}})
        cevap = ws.receive_json()
    assert cevap["ok"] is False
    assert "boş" in cevap["hata"]


def test_bilinmeyen_islem_acik_hata(istemci):
    with istemci.websocket_connect("/api/eklenti") as ws:
        ws.send_json({"id": "p3", "islem": "ucurum"})
        cevap = ws.receive_json()
    assert cevap["ok"] is False
    assert "bilinmeyen" in cevap["hata"]


def test_kanal_zaman_asimi_ve_kapanis(monkeypatch):
    import asyncio
    import threading

    loop = asyncio.new_event_loop()
    is_parcacigi = threading.Thread(target=loop.run_forever, daemon=True)
    is_parcacigi.start()

    async def yut(_cid, _islem, _veri):
        return None

    kanal = tarayici_kanal.Kanal(loop, yut, "t1")
    sonuc = kanal.istek("sayfa_gozlem", {}, sure=0.2)
    assert "hata" in sonuc or "error" in sonuc

    # Kapanış: bekleyen istek askıda kalmaz, açık hata alır.
    def bekle():
        return kanal.istek("sayfa_gozlem", {}, sure=5)

    import concurrent.futures
    havuz = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    gelecek = havuz.submit(bekle)
    kanal.kapat()
    sonuc = gelecek.result(timeout=5)
    assert "kapandı" in str(sonuc.get("error") or sonuc.get("hata"))
    loop.call_soon_threadsafe(loop.stop)
    havuz.shutdown(wait=False)


def test_kanal_cevabi_eslestirir(monkeypatch):
    import asyncio
    import threading

    loop = asyncio.new_event_loop()
    threading.Thread(target=loop.run_forever, daemon=True).start()
    gonderilen = []

    async def yut(cid, islem, veri):
        gonderilen.append((cid, islem, veri))

    kanal = tarayici_kanal.Kanal(loop, yut, "t2")

    import concurrent.futures
    havuz = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    gelecek = havuz.submit(kanal.istek, "sayfa_gozlem", {}, 5)
    while not gonderilen:
        pass
    kanal.cevap_yaz({"id": gonderilen[0][0], "ok": True, "sonuc": GOZLEM})
    assert gelecek.result(timeout=5)["sonuc"] == GOZLEM
    loop.call_soon_threadsafe(loop.stop)
    havuz.shutdown(wait=False)
