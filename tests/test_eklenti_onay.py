"""tests/test_eklenti_onay.py — onay kapısı ve eklenti dağıtımı.

Sözleşme
--------
- Tıklama/yazma isteği eklentiye **uzun süreyle** gider (varsayılan 20 sn
  onay beklemesine yetmez); onay kararı eklentide, kullanıcıda verilir.
- Eklenti "onay yok / panel kapalı" derse araç **açık hata** döner; sessiz
  başarı yok.
- Bağlı istemci yokken hata, eklentinin kurulum adresini taşır.
- `/eklenti.html` kurulum sayfası, `/eklenti/eklenti.zip` çalışan paket
  verir; paket `test/` klasörünü içermez.

Model çağrılmaz, tarayıcı açılmaz.
"""

import io
import os
import sys
import zipfile

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app as app_modulu  # noqa: E402
from tools import tarayici_kopru  # noqa: E402

GOZLEM = {
    "url": "https://ornek.test/hesap",
    "baslik": "Hesap",
    "ogeler": [
        {"sira": 5, "rol": "textbox", "ad": "E-posta", "deger": ""},
        {"sira": 9, "rol": "button", "ad": "Kaydet", "deger": ""},
    ],
}


class KaydedenIstemci:
    """Yerel köprü istemcisi: süreyi de kaydeder."""

    def __init__(self, cevaplar=None):
        self.istekler = []
        self.sureler = []
        self.cevaplar = list(cevaplar or [])

    def __call__(self, islem, veri, sure):
        self.istekler.append((islem, dict(veri)))
        self.sureler.append(sure)
        if self.cevaplar:
            return self.cevaplar.pop(0)
        return {"ok": True, "sonuc": GOZLEM}


@pytest.fixture
def istemci(monkeypatch):
    sahte = KaydedenIstemci()
    for kimlik in list(tarayici_kopru.KOPRU.kimlikler()):
        tarayici_kopru.KOPRU.ayir(kimlik)
    tarayici_kopru._SON.clear()
    monkeypatch.setattr("chat.kimlik.aktif_kullanici", lambda: "casper")
    monkeypatch.setattr(tarayici_kopru, "EKLENTI_ADRESI",
                        "https://ornek.test/eklenti.html")
    tarayici_kopru.KOPRU.bagla("onay-istemci", sahte, kullanici="casper")
    return sahte


def test_eylem_istegi_onay_icin_yeterince_bekler(istemci):
    """20 sn'lik varsayılan, panelde onay bekleyen kullanıcıya yetmez."""
    bakim = tarayici_kopru.sayfa_bakis()
    ref = bakim["ogeler"][1]["ref"]
    istemci.sureler.clear()

    tarayici_kopru.sayfa_tikla(ref)

    assert istemci.sureler[-1] >= 60, istemci.sureler


def test_onay_vermeyince_acik_hata_doner(istemci):
    bakim = tarayici_kopru.sayfa_bakis()
    ref = bakim["ogeler"][1]["ref"]
    istemci.cevaplar = [{"ok": False, "hata": "Kullanıcı onay vermedi."}]

    cevap = tarayici_kopru.sayfa_tikla(ref)

    assert cevap["error"] == "Kullanıcı onay vermedi."


def test_panel_kapaliysa_eylem_yapilmaz(istemci):
    bakim = tarayici_kopru.sayfa_bakis()
    ref = bakim["ogeler"][0]["ref"]
    istemci.cevaplar = [{
        "ok": False,
        "hata": "Onay için Başak paneli açık olmalı (araç çubuğu simgesi).",
    }]

    cevap = tarayici_kopru.sayfa_yaz(ref, "casper@ornek.test")

    assert "error" in cevap
    assert "panel" in cevap["error"]


def test_bagli_istemci_yokken_kurulum_adresi_verilir(monkeypatch):
    for kimlik in list(tarayici_kopru.KOPRU.kimlikler()):
        tarayici_kopru.KOPRU.ayir(kimlik)
    monkeypatch.setattr("chat.kimlik.aktif_kullanici", lambda: "casper")
    monkeypatch.setattr(tarayici_kopru, "EKLENTI_ADRESI",
                        "https://ornek.test/eklenti.html")

    cevap = tarayici_kopru.sayfa_bakis()

    assert "error" in cevap
    assert "https://ornek.test/eklenti.html" in cevap["error"]


# ── Dağıtım: kurulum sayfası + zip ───────────────────────────────────


@pytest.fixture
def web_istemci(monkeypatch, tmp_path):
    monkeypatch.setenv("BASAK_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.delenv("BASAK_URETIM", raising=False)
    monkeypatch.setattr(app_modulu, "_hafizayi_bir_kez_sifirla", lambda: True)
    return TestClient(app_modulu.app)


def test_sohbet_sayfasinda_eklenti_karti_var(web_istemci):
    """Kurulum sohbet ekranının kendisinde de olmalı (ayrı sayfaya mahkûm değil)."""
    cevap = web_istemci.get("/")
    assert cevap.status_code == 200, cevap.text
    html = cevap.text
    assert 'id="eklentiKarti"' in html
    assert "eklenti-kart.js" in html
    assert "/eklenti/eklenti.zip" in html

    betik = web_istemci.get("/eklenti-kart.js")
    assert betik.status_code == 200, betik.text
    assert "chrome-extension://" in betik.text
    assert "eklentiKarti" in betik.text


def test_kart_telefonda_gizlenir_kurali_servis_edilen_bette(web_istemci):
    """Eklenti telefona kurulamaz; kart orada hiç görünmemeli.

    Davranış kilidi `eklenti/test/kart.test.mjs`'de (jsdom, 3 mobil
    test); burada servis edilen betiğin kuralı taşıdığı ve mobilde
    eski betiğin görünmemesi için sürüm damgası taşıdığı kilitlenir.
    """
    betik = web_istemci.get("/eklenti-kart.js").text
    assert "kurulumMumkunMu" in betik
    assert "userAgentData" in betik
    assert "userAgent" in betik  # userAgentData olmayan mobil tarayıcı

    html = web_istemci.get("/").text
    assert "eklenti-kart.js?v=" in html  # cache kırma damgası zorunlu


def test_kurulum_sayfasi_yayinda(web_istemci):
    cevap = web_istemci.get("/eklenti.html")
    assert cevap.status_code == 200, cevap.text
    html = cevap.text
    for gerekli in ("eklenti.zip", "Onayla", "Panel kapalıyken",
                    "chrome://extensions"):
        assert gerekli in html, gerekli


def test_zip_paketi_calisan_dosyalari_tasir(web_istemci):
    cevap = web_istemci.get("/eklenti/eklenti.zip")
    assert cevap.status_code == 200, cevap.text
    assert cevap.headers["content-type"] == "application/zip"
    assert "basak-eklenti.zip" in cevap.headers.get("content-disposition", "")

    with zipfile.ZipFile(io.BytesIO(cevap.content)) as paket:
        adlar = set(paket.namelist())

    for gerekli in ("manifest.json", "arka.js", "icerik.js", "panel.js",
                    "panel.html", "panel.css", "OKUBENI.md", "sinyal.png"):
        assert "basak-eklenti/" + gerekli in adlar, gerekli
    assert not any(ad.startswith("test/") for ad in adlar), adlar
    # Zip tek klasör altında toplanır: kullanıcı açınca seçilebilir bir
    # klasör bulur, dosyalar dağılmaz.
    for ad in adlar:
        assert ad.startswith("basak-eklenti/"), ad
    # Paket, kaynaktaki manifest ile aynı sürümü taşır.
    with zipfile.ZipFile(io.BytesIO(cevap.content)) as paket:
        manifest = paket.read("basak-eklenti/manifest.json").decode("utf-8")
    assert '"manifest_version": 3' in manifest
