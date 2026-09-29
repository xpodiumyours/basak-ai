"""tests/test_gelir_zemini.py — reklam + affiliate kazanc zemini bekcileri.

Sozlesme:
- Her arac sayfasinda bos meta reklam-yerlesimi vardir; AdSense kodu
  gelince tek noktadan doldurulur. Bosken sayfa hicbir ucuncu taraf
  cagrisi yapmaz (onaysiz reklam yasagi).
- Affiliate baglantisi rel="sponsored nofollow" + acik gelir aciklamasi
  tasir; normal atifta sponsored GECMEZ.
- Ortaklik onerisi bosken sayfada "Ilgili urunler" bolumu CIKMAZ.
- Destek/cerez sayfalarinda canli baglanti yuvasi hazirdir.
- Reklam/sponsorluk sayfasi (reklam-ver.html) yayindadir: aracisiz
  dogrudan anlasma modeli anlatilir; harici kod yok; destek sayfasi oraya
  baglar.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gelir
from araclar_sayfa import ORTAKLIK_ONERILERI
from fastapi.testclient import TestClient

import app

ORNEK = "/araclar/security-tools/sha-hash-generator"


def _istemci():
    return TestClient(app.app, base_url="https://ornek.test")


class TestReklamYerlesimi:
    def test_meta_bos_ve_sabit_adres_yok(self):
        with _istemci() as c:
            h = c.get(ORNEK).text
        assert '<meta name="reklam-yerlesimi" content="">' in h

    def test_bos_meta_iken_ucuncu_taraf_kod_yok(self):
        with _istemci() as c:
            h = c.get(ORNEK).text
        assert not re.search(
            r"<(?:script|img|iframe|source|embed)\b[^>]*?"
            r"(?:src)\s*=\s*[\"']https?://", h)
        assert "reklamAlani" in h  # alan bos durur, kod yuklenmez

    def test_tum_sayfalar_meta_tasir(self):
        from tools.freetools_katalog import ARACLAR
        with _istemci() as c:
            for kat, slug in ARACLAR:
                h = c.get("/araclar/%s/%s" % (kat, slug)).text
                assert '<meta name="reklam-yerlesimi"' in h, (kat, slug)


class TestAffiliateDisiplini:
    def test_ortaklik_baglanti_sponsored_ve_aciklama(self):
        h = gelir.baglanti("urun", "https://www.trendyol.com/x")
        assert 'rel="sponsored nofollow"' in h
        assert "destek baglantisi" in h
        assert 'target="_blank"' in h

    def test_normal_atifta_sponsored_yok(self):
        h = gelir.baglanti("kaynak", "https://www.freetools.org/x")
        assert "sponsored" not in h
        assert 'rel="noopener noreferrer nofollow"' in h

    def test_gecersiz_adres_metin_kacar(self):
        h = gelir.baglanti("<b>x</b>", "javascript:alert(1)")
        assert "<b>" not in h and "javascript" not in h

    def test_bos_oneri_sayfada_iz_birakmaz(self):
        assert ORTAKLIK_ONERILERI == {}
        with _istemci() as c:
            h = c.get(ORNEK).text
        assert "Ilgili urunler" not in h
        assert "gelir-aciklama" not in h
        assert "sponsored" not in h


class TestDestekCerezYuvasi:
    def test_destek_bagis_yuvasi(self):
        from pathlib import Path
        metin = (Path(__file__).resolve().parents[1]
                 / "web" / "destek.html").read_text(encoding="utf-8")
        assert 'id="bagisAlani"' in metin

    def test_cerez_reklam_agi_yuvasi(self):
        from pathlib import Path
        metin = (Path(__file__).resolve().parents[1]
                 / "web" / "cerez.html").read_text(encoding="utf-8")
        assert 'id="reklamAgiAdi"' in metin
        assert "yoktur" in metin  # henuz tanimli ag yok — durustluk


class TestReklamVerSayfasi:
    """Uyeliksiz gelir rayi: aracisiz reklam/sponsorluk sayfasi yayinda."""

    YOL = "/reklam-ver.html"

    def test_sayfa_yayinda_ve_canonical(self):
        with _istemci() as c:
            r = c.get(self.YOL)
        assert r.status_code == 200
        h = r.text
        assert 'rel="canonical" href="/reklam-ver.html"' in h
        assert "Reklam" in h and "sponsorluk" in h

    def test_aracisiz_dogrudan_model_anlatilir(self):
        with _istemci() as c:
            h = c.get(self.YOL).text
        assert "aracı platform olmadan, doğrudan" in h
        assert "komisyon yok" in h
        # Reklam ancak ziyaretci onayindan sonra — cerez disipliniyle ayni
        assert "ziyaretçi onayından sonra" in h

    def test_harici_kod_yok_iletisim_depo_uzerinden(self):
        with _istemci() as c:
            h = c.get(self.YOL).text
        assert not re.search(
            r"<(?:script|img|iframe|source|embed)\b[^>]*?"
            r"(?:src)\s*=\s*[\"']https?://", h)
        assert "/araclar.css" in h
        assert 'href="https://github.com/xpodiumyours/basak-ai"' in h
        assert 'rel="noopener noreferrer"' in h

    def test_destek_sayfasi_reklam_ver_baglantisi(self):
        with _istemci() as c:
            h = c.get("/destek.html").text
        assert 'href="/reklam-ver.html"' in h
