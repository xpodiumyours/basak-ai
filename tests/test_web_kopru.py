"""tests/test_web_kopru.py — web koprusu sozlesme testleri (cevrimdisi).

AGENTS.md §9 + knowledge/web-kopru-plani.md:
- Kopru yalniz mesaj_isle'ye baglanir; ikinci beyin YOK (kablo testi).
- Olay eslemesi dogru: BasakUI.* -> istek-bazli HTTP polling olaylari.
- Guvenlik: yol beyaz listesi disi 404; ayarlar.json servis edilmez;
  dis erisimde token zorunlu.
"""

import json
import threading
from http.server import ThreadingHTTPServer
from unittest import mock

import pytest

import basak_web


@pytest.fixture()
def sunucu(tmp_path, monkeypatch):
    """Test sunucusu: rastgele port, izole web klasoru, sahte mesaj_isle."""
    monkeypatch.setattr(basak_web, "WEB", tmp_path)
    monkeypatch.setattr(basak_web, "AYARLAR",
                        tmp_path / "ayarlar.json")
    monkeypatch.setattr(basak_web, "MATRIS", tmp_path / "m.json")
    (tmp_path / "index.html").write_text("<html>ekran</html>",
                                         encoding="utf-8")
    srv = ThreadingHTTPServer(("127.0.0.1", 0), basak_web._Kopru)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield "http://127.0.0.1:%d" % srv.server_address[1], tmp_path
    srv.shutdown()


def _istek(sunucu_adres, yol, veri=None, baslik=None, metot=None):
    import urllib.request
    adres = sunucu_adres + yol
    data = json.dumps(veri).encode() if veri is not None else None
    req = urllib.request.Request(
        adres, data=data,
        method=metot or ("POST" if data else "GET"),
        headers={"content-type": "application/json", **(baslik or {})})
    with urllib.request.urlopen(req, timeout=5) as r:
        govde = r.read()
        return r.status, (json.loads(govde) if govde.startswith(b"{")
                          else govde.decode("utf-8"))


# ── Kablo: tek beyin ─────────────────────────────────────────────────

def test_kopru_yalniz_mesaj_isleye_baglanir():
    """§9 kablo testi: kopru dosyasi mesaj_isle cagirir; ayri ajan/
    saglayici/araç mantigi tasimaz (sapma donemi kalintilari yok)."""
    icerik = open("basak_web.py", encoding="utf-8").read()
    assert "from chat.flow import mesaj_isle" in icerik
    for yasak in ("sampleValue", "BASAK_CELL_OK", "tool_catalog.json",
                  "require_parameters", "tool_choice"):
        assert yasak not in icerik, "kopurude beyin kalintisi: %s" % yasak


def test_sohbet_mesaj_isleye_gider(sunucu, monkeypatch):
    adres, _ = sunucu
    yakalanan = {}
    nisan = object()   # TOOLS global'inin kimlik nisanesi
    monkeypatch.setattr(basak_web, "TOOLS", nisan)

    def _sahte_mesaj_isle(metin, beyin, sistem, js, tools=None):
        yakalanan["metin"] = metin
        yakalanan["tools"] = tools
        js("BasakUI.bitir(\"selam\", \"\")")

    with mock.patch.object(basak_web, "mesaj_isle_cagir",
                           _sahte_mesaj_isle):
        durum, cevap = _istek(adres, "/api/sohbet",
                              veri={"metin": "merhaba"})
    assert durum == 200 and cevap["ok"]
    assert yakalanan["metin"] == "merhaba"
    assert yakalanan["tools"] is nisan, (
        "kopru cekirdege TOOLS global'ini gecirmedi")


# ── Olay eslemesi ────────────────────────────────────────────────────

def test_olay_eslemesi_bitir(monkeypatch):
    yakalanan = []
    monkeypatch.setattr(basak_web, "_yayin", yakalanan.append)
    a = basak_web._OlayAyiklayici(7)
    a('BasakUI.bitir("Gunaydin", "hafiza")')
    assert yakalanan[-1] == {"istek": 7, "tur": "bitir",
                             "cevap": "Gunaydin", "kaynak": "hafiza"}
    assert a.bitti


def test_olay_eslemesi_tool_status_ve_parca(monkeypatch):
    yakalanan = []
    monkeypatch.setattr(basak_web, "_yayin", yakalanan.append)
    a = basak_web._OlayAyiklayici(3)
    a('BasakUI.thinking()')
    a('BasakUI.toolStatus("Saat sorgulaniyor")')
    a('BasakUI.parca("Gun")')
    turler = [o["tur"] for o in yakalanan]
    assert turler == ["thinking", "toolStatus", "parca"]
    assert yakalanan[-1]["metin"] == "Gun"


# ── Guvenlik ─────────────────────────────────────────────────────────

def test_beyaz_liste_disi_404(sunucu):
    adres, _ = sunucu
    try:
        _istek(adres, "/ayarlar.json")
        assert False, "gizli dosya servis edildi"
    except Exception as e:
        assert "404" in str(e) or "HTTP Error" in str(e)


def test_dis_erisim_token_zorunlu(sunucu):
    adres, tmp = sunucu
    (tmp / "ayarlar.json").write_text(
        json.dumps({"web_dis_erisim": True, "web_token": "gizli123"}),
        encoding="utf-8")
    try:
        _istek(adres, "/api/matris")
        assert False, "tokensuz dis istek gecti"
    except Exception as e:
        assert "401" in str(e) or "HTTP Error" in str(e)
    durum, _ = _istek(adres, "/api/matris",
                      baslik={"X-Basak-Token": "gizli123"})
    assert durum == 200


def test_mesaj_sinirlari(sunucu):
    adres, _ = sunucu
    try:
        _istek(adres, "/api/sohbet", veri={"metin": ""})
        assert False, "bos mesaj gecti"
    except Exception as e:
        assert "400" in str(e) or "HTTP Error" in str(e)
    uzun = "x" * 5000
    try:
        _istek(adres, "/api/sohbet", veri={"metin": uzun})
        assert False, "uzun mesaj gecti"
    except Exception as e:
        assert "400" in str(e) or "HTTP Error" in str(e)


def test_polling_olaylari_istek_bazli_ve_kayipsiz(sunucu, monkeypatch):
    adres, _ = sunucu
    monkeypatch.setattr(basak_web, "TOOLS", object())

    def _sahte(metin, beyin, sistem, js, tools=None):
        js("BasakUI.thinking()")
        js("BasakUI.toolStatus(\"Saat okunuyor\")")
        js("BasakUI.bitir(\"20 Eylul 2026\", \"groq\")")

    with mock.patch.object(basak_web, "mesaj_isle_cagir", _sahte):
        durum, cevap = _istek(
            adres, "/api/sohbet", veri={"metin": "saat kac"})
        assert durum == 200 and cevap["ok"]
        no = cevap["istek"]

        import time
        son = 0
        olaylar = []
        for _ in range(20):
            _, veri = _istek(adres, "/api/olaylar?istek=%d&son=%d" %
                             (no, son))
            olaylar.extend(veri["olaylar"])
            son = veri["son"]
            if veri["bitti"]:
                break
            time.sleep(0.02)

    assert [o["tur"] for o in olaylar] == [
        "thinking", "toolStatus", "bitir"]
    assert olaylar[-1]["kaynak"] == "groq"

    # Ayni olaylar ikinci kez alinmaz.
    _, tekrar = _istek(adres, "/api/olaylar?istek=%d&son=%d" % (no, son))
    assert tekrar["olaylar"] == []
    assert tekrar["bitti"] is True


def test_web_ekrani_eventsource_kullanmaz():
    icerik = open("web/app.js", encoding="utf-8").read()
    ortak = open("web/common.js", encoding="utf-8").read()
    assert "EventSource" not in icerik
    assert "basakSse" not in icerik
    assert "basakSse" not in ortak
    assert "/api/olaylar?istek=" in icerik


def test_durum_endpointi_sir_gostermeden_surumu_verir(sunucu, monkeypatch):
    adres, _ = sunucu

    class Beyin:
        def _bulut_zinciri(self, tools=False):
            return [("groq", object()), ("gemini", object())]

    monkeypatch.setattr(basak_web, "BEYIN", Beyin())
    monkeypatch.setattr(basak_web, "TOOLS", [1, 2, 3])
    monkeypatch.setattr(basak_web, "_git_commit", lambda: "abc1234")

    durum, veri = _istek(adres, "/api/durum")
    assert durum == 200
    assert veri["ok"] is True
    assert veri["commit"] == "abc1234"
    assert veri["saglayicilar"] == ["groq", "gemini"]
    assert veri["arac_sayisi"] == 3
    assert veri["tasima"] == "http-polling"
    assert [m["ad"] for m in veri["modeller"]] == ["groq", "gemini"]
    assert all(m["model"] == "dogrulanamadi" for m in veri["modeller"])
    assert "groq" in veri["beklenen_saglayicilar"]
    assert "openrouter" in veri["eksik_saglayicilar"]
    assert "gucleri" in veri["modeller"][0]
    assert "limit" in veri["modeller"][0]
    assert "kullanim" in veri["modeller"][0]
    # API anahtari/token gibi sir alanlari durum cevabinda bulunmaz.
    assert "key" not in json.dumps(veri).lower()
    assert "token" not in json.dumps(veri["modeller"][1]["limit"]).lower() or (
        "gunluk_token" in veri["modeller"][1]["limit"])
