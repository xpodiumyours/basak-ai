"""tests/test_web_kimlik_sizintisi.py — "Casper'ın asistanıyım" dışarı sızmasın.

Ölçülen olay (2026-10-21): barındırılan önizlemede giriş yapmamış ziyaretçi
"Merhaba" dedi ve yanıt "Ben Başak, Casper'ın kişisel asistanıyım" oldu.
Neden: `_aktif_kimlik` çerez yokken tek-kişi modunu (casper) döndürüyordu;
bu mod yalnız yerel masaüstü açılışı için doğru.

Sözleşme:
- Yerel sunucu (127.0.0.1): kimlik yoksa casper — masaüstü davranışı aynı.
- Dışarı açık sunucu (0.0.0.0): kimlik yoksa KİMLİK UYDURULMAZ; sohbet
  nötr misafir kimliğiyle sürer ve kişisel köke düşmez.
"""

import json
import os
import socket
import sys
import threading

import pytest
from http.server import ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import basak_web
from chat.prompts import kisilik_blogu


class _BasitIstek:
    def __init__(self, adres):
        self.headers = {}
        self.server = type("S", (), {"server_address": (adres, 1)})()


@pytest.fixture(autouse=True)
def _giris_zorunlu_degil(monkeypatch, tmp_path):
    import kullanici as kullanici_modulu
    monkeypatch.setattr(kullanici_modulu, "giris_zorunlu_mu", lambda: False)
    # Test gercek ayarlar.json'dan bagimsiz kosar: gelistirici makinesinde
    # "web_dis_erisim": true ise /api/sohbet token ister ve test 401'e
    # iner — o, bu testin olctugu davranis degildir (Ayarsiz = yerel mod).
    monkeypatch.setattr(basak_web, "AYARLAR", tmp_path / "ayarlar.json")
    monkeypatch.delenv("BASAK_WEB_DIS", raising=False)


def test_yerel_sunucuda_tek_kisi_modu_korunur():
    assert basak_web._aktif_kimlik(_BasitIstek("127.0.0.1")) == "casper"


def test_disari_acik_sunucuda_kimlik_uydurulmaz():
    assert basak_web._aktif_kimlik(_BasitIstek("0.0.0.0")) is None


def test_misafir_kisiligi_casper_adini_tasimaz():
    for kid in (None, ""):
        metin = kisilik_blogu(kid, misafir=True)
        assert "Casper" not in metin, metin
        assert "Başak" in metin or "Basak" in metin, metin


def _govde_post(port, yol, govde):
    bas = (
        "POST %s HTTP/1.1\r\nHost: localhost\r\n"
        "Content-Type: application/json\r\nContent-Length: %d\r\n"
        "Connection: close\r\n\r\n" % (yol, len(govde))
    ).encode("ascii")
    with socket.create_connection(("127.0.0.1", port), timeout=10) as s:
        s.sendall(bas + govde)
        parcalar = []
        while True:
            parca = s.recv(4096)
            if not parca:
                break
            parcalar.append(parca)
    return b"".join(parcalar)


@pytest.mark.parametrize("adres,beklenen_misafir", [
    ("0.0.0.0", True),      # önizleme/sunucu: nötr kimlik
    ("127.0.0.1", False),   # masaüstü: casper
])
def test_sohbet_kimligi_sunucu_adresine_gore(monkeypatch, adres,
                                             beklenen_misafir):
    """Gerçek soket: yakalanan kişilik bloğunda 'Casper' kararı ölçülür."""
    yakalanan = {}

    def sahte_mesaj(metin, beyin, kisilik, ayiklayici, toollar, misafir=False):
        yakalanan["kisilik"] = kisilik
        yakalanan["misafir"] = misafir
        yakalanan["kimlik"] = __import__("chat.kimlik",
                                        fromlist=["x"]).aktif_kullanici()

    monkeypatch.setattr(basak_web, "mesaj_isle_cagir", sahte_mesaj)
    monkeypatch.setattr(basak_web, "BEYIN", object())
    monkeypatch.setattr(basak_web, "TOOLS", [])

    sunucu = ThreadingHTTPServer((adres, 0), basak_web._Kopru)
    threading.Thread(target=sunucu.serve_forever, daemon=True).start()
    try:
        govde = json.dumps({"metin": "Merhaba"}).encode("utf-8")
        cevap = _govde_post(sunucu.server_address[1], "/api/sohbet", govde)
    finally:
        sunucu.shutdown()
        sunucu.server_close()

    assert b"200" in cevap.split(b"\r\n")[0], cevap
    assert yakalanan["misafir"] is beklenen_misafir, yakalanan
    if beklenen_misafir:
        assert "Casper" not in yakalanan["kisilik"], yakalanan["kisilik"]
        assert yakalanan["kimlik"] == "misafir", yakalanan
    else:
        assert "Casper" in yakalanan["kisilik"], yakalanan["kisilik"]
