"""tests/test_web_yeni_cekirdek.py — yeni cekirdek sozlesme testleri (kotasiz).

Sadelestirme dali icin 1 test. --live YOK, gercek API YOK (sahte beyin).
KAYNAK DOSYALARA DOKUNMAZ; yalniz davranisi olcer.

1. web kuyruk sayi + bitir garantisi: her /api/sohbet artan istek numarasi
   alir; beyin patlasa bile o istek icin 'bitir' olayi yayinlanir
   (/api/olaylar üzerinden yoklanir).

NOT: tur siniri ve gecmis kirpma testleri YOK. AGENTS.md S0-5 yasagi
geregi bu tavanlar koda giremez, o yuzden testi de yazilmaz.
"""

import json
import threading
import time
from http.server import ThreadingHTTPServer
from unittest import mock

import basak_web


def _istek(adres, yol, veri=None):
    import urllib.request
    url = adres + yol
    data = json.dumps(veri).encode() if veri is not None else None
    req = urllib.request.Request(
        url, data=data,
        method="POST" if data else "GET",
        headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as r:
        govde = r.read()
        return r.status, (json.loads(govde) if govde.startswith(b"{")
                          else govde.decode("utf-8"))


def _sunucu_ac(tmp_path, monkeypatch):
    monkeypatch.setattr(basak_web, "WEB", tmp_path)
    monkeypatch.setattr(basak_web, "AYARLAR", tmp_path / "ayarlar.json")
    monkeypatch.setattr(basak_web, "MATRIS", tmp_path / "m.json")
    (tmp_path / "index.html").write_text("<html>ekran</html>",
                                         encoding="utf-8")
    monkeypatch.setattr(basak_web, "_SAYAC", 0)
    basak_web._OLAYLAR.clear()
    basak_web._OLAY_ZAMANI.clear()
    srv = ThreadingHTTPServer(("127.0.0.1", 0), basak_web._Kopru)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv, "http://127.0.0.1:%d" % srv.server_address[1]


def _bitir_bekle(adres, istek_no, timeout=5):
    """Yoklamadan o istegin bitir olayi gelene kadar bekler."""
    son = time.time() + timeout
    while time.time() < son:
        _, d = _istek(adres, "/api/olaylar?istek=%d&son=0" % istek_no)
        for o in d["olaylar"]:
            if o.get("tur") == "bitir":
                return o
        time.sleep(0.05)
    raise AssertionError("bitir gelmedi (istek=%s)" % istek_no)


def test_web_kuyruk_sayi_ve_bitir_garantisi(tmp_path, monkeypatch):
    srv, adres = _sunucu_ac(tmp_path, monkeypatch)
    try:
        def _sahte(metin, beyin, sistem, js, tools=None,
                   misafir=False, sid=None):
            js('BasakUI.bitir("selam", "")')

        with mock.patch.object(basak_web, "mesaj_isle_cagir", _sahte):
            _, c1 = _istek(adres, "/api/sohbet", {"metin": "bir"})
            _, c2 = _istek(adres, "/api/sohbet", {"metin": "iki"})
        # Kuyruk sayisi: her istek benzersiz ve artan numara alir.
        assert c1["istek"] >= 1
        assert c2["istek"] == c1["istek"] + 1

        # Bitir garantisi: beyin patlasa bile bitir olayi gelir.
        def _patlayan(metin, beyin, sistem, js, tools=None,
                       misafir=False, sid=None):
            raise RuntimeError("boom")

        with mock.patch.object(basak_web, "mesaj_isle_cagir", _patlayan):
            _, c3 = _istek(adres, "/api/sohbet", {"metin": "uc"})
        olay = _bitir_bekle(adres, c3["istek"])
        assert "boom" in olay["cevap"], olay
    finally:
        srv.shutdown()
        basak_web._OLAYLAR.clear()
        basak_web._OLAY_ZAMANI.clear()
