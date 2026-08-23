"""tests/test_od1.py — OD-1 testleri: defter iki yön.

deftere_kaydet fonksiyonu ortak deftere ORTAK-DEFTER.md §3 biçiminde
kayıt yazmalı: kim/tarih/tip/ömür/kaynak frontmatter + içerik.
INDEX.md de otomatik güncellenmeli.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.notes import deftere_kaydet


class TestDeftereKaydet:
    """OD-1: deftere_kaydet fonksiyonu testleri."""

    def test_basit_kayit(self):
        """Temel kayıt yazma başarılı olmalı."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sonuc = deftere_kaydet(
                "Test Konusu", "Bu bir test kaydıdır.", tmpdir)
            assert "result" in sonuc
            assert "test-konusu.md" in sonuc["result"]
            # Dosya oluştu mu?
            dosya = os.path.join(tmpdir, "test-konusu.md")
            assert os.path.exists(dosya)
            # Frontmatter var mı?
            with open(dosya, "r", encoding="utf-8") as f:
                icerik = f.read()
            assert "kim:    basak" in icerik
            assert "tip:    alinti" in icerik
            assert "omur:   30g" in icerik
            assert "kaynak: sohbet" in icerik
            assert "---" in icerik

    def test_on_bilgilerle_kayit(self):
        """Özel kim/tip/ömür/kaynak ile kayıt."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sonuc = deftere_kaydet(
                "Olcum Sonucu", "Groq kotası dolmus.",
                tmpdir, kim="claude", tip="olcum",
                omur="6s", kaynak="data/kota-gercek.md")
            assert "result" in sonuc
            # Dosya adı title'dan türetilir
            dosya_adi = sonuc["result"].split(": ")[-1]
            dosya = os.path.join(tmpdir, dosya_adi)
            assert os.path.exists(dosya), "Dosya oluşmadı: %s" % dosya
            with open(dosya, "r", encoding="utf-8") as f:
                icerik = f.read()
            assert "kim:    claude" in icerik
            assert "tip:    olcum" in icerik
            assert "omur:   6s" in icerik
            assert "kaynak: data/kota-gercek.md" in icerik

    def test_index_guncellenir(self):
        """INDEX.md otomatik güncellenmeli."""
        with tempfile.TemporaryDirectory() as tmpdir:
            deftere_kaydet("Index Test", "Index satırı eklenecek.", tmpdir)
            index_yolu = os.path.join(tmpdir, "INDEX.md")
            assert os.path.exists(index_yolu)
            with open(index_yolu, "r", encoding="utf-8") as f:
                icerik = f.read()
            assert "ORTAK DEFTER" in icerik
            assert "index-test.md" in icerik

    def test_bos_baslik_hata(self):
        """Boş başlık hata döndürmeli."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sonuc = deftere_kaydet("", "içerik", tmpdir)
            assert "error" in sonuc

    def test_bos_icerik_hata(self):
        """Boş içerik hata döndürmeli."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sonuc = deftere_kaydet("Başlık", "", tmpdir)
            assert "error" in sonuc

    def test_gecersiz_kim_hata(self):
        """Geçersiz kim değeri hata döndürmeli."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sonuc = deftere_kaydet("Test", "İçerik", tmpdir,
                                   kim="yanlis_kişi")
            assert "error" in sonuc
            assert "kim" in sonuc["error"].lower()

    def test_gecersiz_tip_hata(self):
        """Geçersiz tip değeri hata döndürmeli."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sonuc = deftere_kaydet("Test", "İçerik", tmpdir,
                                   tip="yanlis_tip")
            assert "error" in sonuc
            assert "tip" in sonuc["error"].lower()

    def test_gecersiz_omur_hata(self):
        """Geçersiz ömür değeri hata döndürmeli."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sonuc = deftere_kaydet("Test", "İçerik", tmpdir,
                                   omur="50yil")
            assert "error" in sonuc
            assert "ömür" in sonuc["error"].lower()

    def test_tekrar_kayit_indexe_eklenmez(self):
        """Aynı dosya tekrar kaydedilirse INDEX'e tekrar eklenmemeli."""
        with tempfile.TemporaryDirectory() as tmpdir:
            deftere_kaydet("Tekrar Test", "İlk kayıt.", tmpdir)
            deftere_kaydet("Tekrar Test", "İkinci kayıt.", tmpdir)
            index_yolu = os.path.join(tmpdir, "INDEX.md")
            with open(index_yolu, "r", encoding="utf-8") as f:
                icerik = f.read()
            # Aynı dosya adı INDEX'de kaç kez geçiyor?
            sayac = icerik.count("tekrar-test.md")
            assert sayac == 1, "INDEX'de aynı dosya %d kez var" % sayac

    def test_kimlikler_tanimli_mi(self):
        """İzinli kimlikler TOOLS listesindeki enum ile uyumlu mu?"""
        from tools.definitions import TOOLS
        deftere_tool = None
        for t in TOOLS:
            if t["function"]["name"] == "deftere_kaydet":
                deftere_tool = t
                break
        assert deftere_tool is not None, "deftere_kaydet TOOLS'da yok"
        params = deftere_tool["function"]["parameters"]["properties"]
        kim_enum = params["kim"]["enum"]
        tip_enum = params["tip"]["enum"]
        omur_enum = params["omur"]["enum"]
        assert "basak" in kim_enum
        assert "claude" in kim_enum
        assert "olcum" in tip_enum
        assert "alinti" in tip_enum
        assert "30g" in omur_enum
        assert "sonsuz" in omur_enum
