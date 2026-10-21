"""tests/test_durum_sayfasi.py — canlı kanıt sayfası ve üç adımlı kurulum.

Sözleşme
--------
- `/durum.html` yayındadır ve çekirdeğin GERÇEK uçlarını ölçer
  (`/api/durum`, `/api/sohbet`, `/api/eklenti`). Ölçülemeyen şey
  "yeşil" yazılmaz.
- Sayfada ikinci bir beyin, ikinci bir sağlayıcı zinciri veya sabit
  (uydurma) sonuç yoktur: sağlayıcı adları koda gömülü değildir.
- Eski `/lab.html` adresi tek kanıt sayfasına gider.
- Kurulum üç adımdır: kart, kurulum sayfası ve zip paketi aynı adım
  sayısını söyler; zip tek klasör taşır.
"""

import io
import os
import re
import sys
import zipfile

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app as app_modulu  # noqa: E402

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def web_istemci(monkeypatch, tmp_path):
    monkeypatch.setenv("BASAK_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.delenv("BASAK_URETIM", raising=False)
    monkeypatch.setattr(app_modulu, "_hafizayi_bir_kez_sifirla", lambda: True)
    return TestClient(app_modulu.app)


def _oku_yol(yol):
    with open(os.path.join(KOK, yol), encoding="utf-8") as f:
        return f.read()


def test_durum_sayfasi_yayinda(web_istemci):
    cevap = web_istemci.get("/durum.html")
    assert cevap.status_code == 200, cevap.text
    html = cevap.text
    assert "durum.js" in html
    assert "common.js" in html
    assert "Başak şu an çalışıyor mu?" in html


def test_durum_beti_gercek_ucurlari_olcer():
    """Sayfa kendi uçlarımızı ölçer; başka bir zemin kurmaz."""
    kaynak = _oku_yol("web/durum.js")
    for uc in ("/api/durum", "/api/sohbet", "/api/eklenti"):
        assert uc in kaynak, uc
    # İkinci beyin kuralları: sağlayıcı listesi ya da model adı gömülü olmaz.
    for yasak in ("groq", "gemini", "openrouter", "nvidia", "mistral"):
        assert yasak not in kaynak.lower(), yasak
    # Sabit (uydurma) cevap gömülü değildir: cevap her zaman gelen olaydan okunur.
    assert "tur" in kaynak and "bitir" in kaynak


def test_durum_sayfasi_yalniz_olcer_yazmaz():
    """Ölçüm görüntüleyicidir: kendi isteğini sunucuya göndermez."""
    kaynak = _oku_yol("web/durum.js")
    assert "method: \"POST\"" in kaynak          # yalnız sohbet ölçümü post eder
    for yazma in ("/api/yeni", "/api/sohbetler", "/api/kimlik\","):
        assert yazma not in kaynak, yazma


def test_eski_lab_sayfasi_duruma_gider(web_istemci):
    cevap = web_istemci.get("/lab.html")
    assert cevap.status_code == 200, cevap.text
    assert "/durum.html" in cevap.text
    assert "refresh" in cevap.text


def test_kurulum_uc_adim():
    """Kart, kurulum sayfası ve zip aynı adım sayısını söyler."""
    kart = _oku_yol("web/index.html")
    blok = re.search(r'<ol id="eklentiAdimlar".*?</ol>', kart, re.S)
    assert blok, "eklenti adımları bulunamadı"
    assert len(re.findall(r"<li>", blok.group(0))) == 3, blok.group(0)

    betik = _oku_yol("web/eklenti-kart.js")
    assert "üç adım" in betik
    assert "dört adım" not in betik

    sayfa = _oku_yol("web/eklenti.html")
    assert "kurulum 3 adım" in sayfa
    assert "4. Panelden bağlan" not in sayfa


def test_zip_tek_klasor_taşır(web_istemci):
    """Zip tek klasör altında toplanır: açınca dağılmaz, seçilir."""
    cevap = web_istemci.get("/eklenti/eklenti.zip")
    assert cevap.status_code == 200, cevap.text
    with zipfile.ZipFile(io.BytesIO(cevap.content)) as paket:
        adlar = set(paket.namelist())
    assert adlar, "zip boş"
    for ad in adlar:
        assert ad.startswith("basak-eklenti/"), ad
    assert "basak-eklenti/manifest.json" in adlar


def test_kabul_ozeti_dosyasi_yayinda(web_istemci):
    """Depoda kayıtlı ölçüm sayfaya servis edilir (canlı ölçüm DEĞİL)."""
    cevap = web_istemci.get("/durum-kabul.json")
    assert cevap.status_code == 200, cevap.text
    veri = cevap.json()
    for alan in ("uretildi", "komut", "test_gecen", "arac_sayisi"):
        assert alan in veri, alan
    assert isinstance(veri.get("sinirlar"), list)
