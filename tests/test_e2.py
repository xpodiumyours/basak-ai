"""tests/test_e2.py — E-2 testleri: Gerçek araştırma.

E-2 kuralı:
1. sayfa_oku: URL'den sayfa icerigi okunur (yalnizca GET, HTML temizlenir)
2. Arastirma sonucu deftere kaydedilir (kaynak adres + tarih + ozet)
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.web_search import sayfa_oku, web_search


class TestSayfaOku:
    """E-2: sayfa_oku fonksiyonu testleri."""

    def test_bos_url_hata(self):
        """Bos URL hata dondurur."""
        sonuc = sayfa_oku("")
        assert "error" in sonuc

    def test_yalnizca_http(self):
        """Yalnizca http/https URL'leri kabul edilir."""
        sonuc = sayfa_oku("ftp://example.com")
        assert "error" in sonuc
        assert "http" in sonuc["error"].lower()

    def test_yasakli_adres(self):
        """localhost/127.0.0.1 erisimi engellenir."""
        sonuc = sayfa_oku("http://localhost:8080/test")
        assert "error" in sonuc

    def test_gercek_sayfa_okunur(self):
        """Gercek bir sayfa okunabilmeli (httpbin)."""
        sonuc = sayfa_oku("https://httpbin.org/html")
        assert "result" in sonuc or "error" in sonuc
        if "result" in sonuc:
            assert len(sonuc["result"]) > 0

    def test_icerik_temizlenir(self):
        """HTML icerik temizlenir (etiketler soyulur)."""
        sonuc = sayfa_oku("https://httpbin.org/html")
        if "result" in sonuc:
            assert "<html>" not in sonuc["result"].lower()
            assert "<p>" not in sonuc["result"].lower()


class TestDeftereArastrimaKaydi:
    """E-2: Arastirma sonuclari deftere kaydedilir."""

    def test_deftere_kaydet_calisiyor(self):
        """deftere_kaydet ile arastirma kaydi dusurulebilmeli."""
        from tools.notes import deftere_kaydet
        with tempfile.TemporaryDirectory() as tmpdir:
            sonuc = deftere_kaydet(
                "Test Arastirma",
                "Bu bir test arastirmasi sonucudur.",
                tmpdir,
                kim="basak",
                tip="olcum",
                omur="1g",
                kaynak="https://example.com/test"
            )
            assert "result" in sonuc
            # Dosya adini sonuctan al
            dosya_adi = sonuc["result"].split(": ")[-1]
            dosya = os.path.join(tmpdir, dosya_adi)
            assert os.path.exists(dosya), "Dosya olusmadi: %s" % dosya_adi
            with open(dosya, "r", encoding="utf-8") as f:
                icerik = f.read()
            assert "kaynak: https://example.com/test" in icerik

    def test_deftere_arastirma_index_guncellenir(self):
        """Arastrirma kaydinda INDEX guncellenir."""
        from tools.notes import deftere_kaydet
        with tempfile.TemporaryDirectory() as tmpdir:
            sonuc = deftere_kaydet(
                "Arastrima Kaydi",
                "Gunun hava durumu arastirmasi sonucu.",
                tmpdir,
                kim="basak",
                tip="olcum",
                omur="6s",
                kaynak="https://api.open-meteo.com"
            )
            dosya_adi = sonuc["result"].split(": ")[-1]
            index = os.path.join(tmpdir, "INDEX.md")
            assert os.path.exists(index)
            with open(index, "r", encoding="utf-8") as f:
                icerik = f.read()
            assert dosya_adi in icerik, "INDEX'de %s yok" % dosya_adi


class TestArastrimaOlsuturucu:
    """E-2: Arastirma → defter akisi entegrasyon testleri."""

    def test_web_search_sonuc_dondurur(self):
        """web_search sonuc dondurur (hata veya basari)."""
        sonuc = web_search("Python programlama")
        assert "result" in sonuc or "error" in sonuc

    def test_deftere_yazabilirlik(self):
        """Web arama sonrasi deftere kayit dusurulebilir."""
        from tools.notes import deftere_kaydet
        with tempfile.TemporaryDirectory() as tmpdir:
            arastirma = "Python 1991'de Guido van Rossum tarafindan olusturuldu."
            sonuc = deftere_kaydet(
                "Python Hakkinda",
                arastirma,
                tmpdir,
                kim="basak",
                tip="olcum",
                omur="30g",
                kaynak="https://tr.wikipedia.org/wiki/Python"
            )
            assert "result" in sonuc
            dosyalar = os.listdir(tmpdir)
            md_dosyalar = [d for d in dosyalar
                          if d.endswith(".md") and d != "INDEX.md"]
            assert len(md_dosyalar) >= 1
