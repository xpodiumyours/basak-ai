"""tests/test_canli_akis.py — app.py canli akis (NDJSON) sozlesmesi.

Olculen sorun (2026-09-23): Vercel koprusu tum olaylari tek JSON'da
donduruyordu; cevap gelene kadar ekranda hicbir sey olmuyordu ("donma").

Kilitleyen kararlar:
1. `Accept: application/x-ndjson` YOKSA davranis birebir bugunku JSON'dur
   (ok/istek/cevap/kaynak/olaylar). Eski istemci kirilmaz.
2. Akistaki satirlar cekirdegin urettigi olaylarin AYNISI ve ayni siradadir;
   ekran icin uydurma adim uretilmez.
3. Akis basladiktan sonra HTTP 500 donemez (basliklar gitmistir):
   beklenmedik istisna son satirda tur=error olarak akar, istemci asili kalmaz.
4. Akis oncesi dogrulama (bos mesaj) hala JSON 400'dur.
5. Yerel kopru (basak_web.py) http-polling olarak kalir; Vercel ucu
   "canli-ndjson" bildirir.

Mock yok: gercek uc gercek TestClient ile cagrilir. Yalniz cekirdek
(chat.flow.mesaj_isle) sahte olay yayan fonksiyonla degistirilir — boylece
"kim hangi olayi uretiyor" degil, "kopru olayi nasil tasiyor" olculur.
"""

import json
import os
import sys
from unittest import mock

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_modulu  # noqa: E402


OLAYLAR = [
    "BasakUI.thinking()",
    'BasakUI.toolStatus("İnternette aranıyor: https://vixrex.com")',
    'BasakUI.parca("Vixrex")',
    'BasakUI.parca(" incelendi.")',
    'BasakUI.bitir("Vixrex incelendi.", "groq")',
]


def _yayici(olaylar):
    """Cekirdegin yerine gecer: olaylari sirasiyla js_callback'e verir."""

    def _sahte(metin, beyin, sistem, js, tools=None, misafir=False,
               gecmis_override=None):
        for kod in olaylar:
            js(kod)

    return _sahte


def _patlayan(metin, beyin, sistem, js, tools=None, misafir=False,
              gecmis_override=None):
    raise RuntimeError("akis icinde patlama")


def _sahte_mesaj(olaylar=None, patlat=False):
    """chat.flow.mesaj_isle'yi gecici olarak degistirir."""
    return mock.patch(
        "chat.flow.mesaj_isle",
        _patlayan if patlat else _yayici(olaylar or OLAYLAR),
    )


def _istemci(monkeypatch):
    """Yerel (tek-kullanici) modda app; cekirdek sahte, gercek Brain yok."""
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.setattr(app_modulu, "_cekirdek", lambda: (object(), []))
    return TestClient(app_modulu.app)


def _satirlar(cevap):
    return [json.loads(s) for s in cevap.text.split("\n") if s.strip()]


def test_akis_istemeyen_istemci_ayni_jsonu_alir(monkeypatch):
    """1. Regresyon kilidi: Accept yoksa toplu JSON yolu birebir ayni."""
    with _istemci(monkeypatch) as istemci:
        with _sahte_mesaj():
            cevap = istemci.post("/api/sohbet", json={"metin": "vixrex"})

    assert cevap.status_code == 200
    assert "ndjson" not in cevap.headers.get("content-type", "")
    d = cevap.json()
    for anahtar in ("ok", "istek", "cevap", "kaynak", "olaylar"):
        assert anahtar in d, d
    assert [o["tur"] for o in d["olaylar"]] == [
        "thinking", "toolStatus", "parca", "parca", "bitir"]
    assert d["cevap"] == "Vixrex incelendi."
    assert d["kaynak"] == "groq"


def test_canli_akis_gercek_olay_sirasini_tasir(monkeypatch):
    """2. Akis: satirlar ayni sirada, ayni istek no, terminal satir bitir."""
    with _istemci(monkeypatch) as istemci:
        with _sahte_mesaj():
            cevap = istemci.post(
                "/api/sohbet", json={"metin": "vixrex"},
                headers={"accept": "application/x-ndjson"},
            )

    assert cevap.status_code == 200
    assert "application/x-ndjson" in cevap.headers["content-type"]

    olaylar = _satirlar(cevap)
    assert [o["tur"] for o in olaylar] == [
        "thinking", "toolStatus", "parca", "parca", "bitir"]
    assert olaylar[1]["metin"] == "İnternette aranıyor: https://vixrex.com"
    assert olaylar[-1]["cevap"] == "Vixrex incelendi."
    # Tek istek numarasi: ekran olaylari ayni balona baglar.
    assert len({o["istek"] for o in olaylar}) == 1


def test_akis_icinde_istisna_terminal_hata_satiri_uretir(monkeypatch):
    """3. Akis basladiktan sonra 500 yok; son satir gercek hatadir."""
    with _istemci(monkeypatch) as istemci:
        with _sahte_mesaj(patlat=True):
            cevap = istemci.post(
                "/api/sohbet", json={"metin": "vixrex"},
                headers={"accept": "application/x-ndjson"},
            )

    assert cevap.status_code == 200
    olaylar = _satirlar(cevap)
    assert olaylar, "akis hic satir uretmedi"
    assert olaylar[-1]["tur"] == "error"
    assert "akis icinde patlama" in olaylar[-1]["metin"]


def test_akis_oncesi_dogrulama_json_400_dondurur(monkeypatch):
    """4. Dogrulama akis baslamadan calisir: bos mesaj JSON 400."""
    with _istemci(monkeypatch) as istemci:
        cevap = istemci.post(
            "/api/sohbet", json={"metin": "   "},
            headers={"accept": "application/x-ndjson"},
        )

    assert cevap.status_code == 400
    assert "ndjson" not in cevap.headers.get("content-type", "")
    assert cevap.json()["error"] == "Bos mesaj"


def test_tasima_alani_canli_akisi_bildirir(monkeypatch):
    """5. Vercel ucu canli-ndjson; yerel kopru http-polling kalir."""
    with _istemci(monkeypatch) as istemci:
        cevap = istemci.get("/api/durum")

    assert cevap.status_code == 200
    assert cevap.json()["tasima"] == "canli-ndjson"

    yerel = open("basak_web.py", encoding="utf-8").read()
    assert '"tasima": "http-polling"' in yerel


def test_arac_durum_metni_ham_detay_tasir_kirpma_ekranin_isi():
    """Sunucu ham detayi (yol/url) yollar; kirpma app.js guvenliDurum'un isi.

    Bu test kirpmanin NEDEN gerekli oldugunu kilitler: `_durum` DURUM_ALANI
    icindeki ilk dolu alani metne ekler (chat/tools.py). Ekran yalniz etiketi
    gostermezse dosya yolu ve sorgu kullaniciya sizar.
    """
    from chat import tools as tools_modulu

    metin = tools_modulu._durum(
        "web_search", {"url": "https://vixrex.com/gizli?token=abc"})
    assert ": " in metin, metin
    assert "token=abc" in metin, metin

    ekran = open("web/app.js", encoding="utf-8").read()
    assert "guvenliDurum" in ekran
    assert "const etiket = guvenliDurum(o.metin);" in ekran
    assert "durumSatiri(b, etiket)" in ekran
    assert "durumSatiri(b, o.metin" not in ekran


def test_panel_yalniz_gercek_arac_olayinda_dogar():
    """Panel (rail) thinking'de degil, ilk toolStatus'ta kurulur.

    Casper karari (2026-09-23): sahte calisma adimi sifir; araclar
    kullanilmayan siradan sohbette dev arastirma paneli acilmaz.
    """
    ekran = open("web/app.js", encoding="utf-8").read()

    thinking = ekran.split('o.tur === "thinking"', 1)[1].split("o.tur ===", 1)[0]
    assert "rail" not in thinking, "thinking dalinda panel kuruluyor"

    arac = ekran.split('o.tur === "toolStatus"', 1)[1].split("o.tur ===", 1)[0]
    assert "railAdim(" in arac, "toolStatus paneli beslemiyor"

    # Yerel polling yolu ve EventSource yasagi aynen durur.
    assert "/api/olaylar?istek=" in ekran
    assert "EventSource" not in ekran
    assert "basak_cloud_chats_v2" in ekran
    # Tasima notu gercek: gonderim aninda ekran KENDI calisma adimini kurmaz.
    assert "Mesaj Başak’a iletiliyor" in ekran
    assert 'bubble("assistant","Düşünüyorum…")' not in ekran
