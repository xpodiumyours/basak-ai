"""tests/test_o2.py — Ö-2 testleri: İddia defteri + bayatlama.

Ö-2 kuralı:
1. Ömür tablosu doğru çalışıyor mu?
2. Bayat kontrolü doğru sonuç döndürüyor mu?
3. DefterINDEX bayat kontrolü çalışıyor mu?
"""

import os
import sys
import tempfile
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.bayat import (
    omur_al, bayat_mi, defter_bayat_kontrol, bayat_ozet,
    OMUR_TABLOSU,
)


class TestOmurTablosu:
    """Ö-2: Ömür tablosu doğru çalışıyor mu?"""

    def test_git_omru_1_saat(self):
        """Git durumu 1 saat ömürlü olmalı."""
        omur = omur_al(tip="git")
        assert omur == timedelta(hours=1)

    def test_olcum_omru_6_saat(self):
        """Ölçüm 6 saat ömürlü olmalı."""
        omur = omur_al(tip="olcum")
        assert omur == timedelta(hours=6)

    def test_dosya_omru_6_saat(self):
        """Dosya varlığı 6 saat ömürlü olmalı."""
        omur = omur_al(tip="dosya")
        assert omur == timedelta(hours=6)

    def test_site_omru_1_gun(self):
        """Canlı site 1 gün ömürlü olmalı."""
        omur = omur_al(tip="site")
        assert omur == timedelta(days=1)

    def test_kota_omru_1_gun(self):
        """Kota 1 gün ömürlü olmalı."""
        omur = omur_al(tip="kota")
        assert omur == timedelta(days=1)

    def test_karar_omru_30_gun(self):
        """Proje kararı 30 gün ömürlü olmalı."""
        omur = omur_al(tip="karar")
        assert omur == timedelta(days=30)

    def test_sonsuz_omur(self):
        """Sonsuz tipi None döndürmeli (bayatlamaz)."""
        omur = omur_al(tip="sonsuz")
        assert omur is None

    def test_soru_omur(self):
        """Soru tipi None döndürmeli (açık soru bayatlamaz)."""
        omur = omur_al(tip="soru")
        assert omur is None

    def test_kaynak_ipucu_git(self):
        """'git log' kaynagindan git tespit edilmeli."""
        omur = omur_al(kaynak="git log -1")
        assert omur == timedelta(hours=1)

    def test_kaynak_ipucu_site(self):
        """'https://' kaynagindan site tespit edilmeli."""
        omur = omur_al(kaynak="https://example.com")
        assert omur == timedelta(days=1)

    def test_kaynak_ipucu_dosya(self):
        """'dosya' kaynagindan dosya tespit edilmeli."""
        omur = omur_al(kaynak="AGENTS.md dosyasi")
        assert omur == timedelta(hours=6)

    def test_varsayilan_olcum(self):
        """Bilinmeyen tip varsayılan olarak ölçüm (6s) olmalı."""
        omur = omur_al(tip="bilinmeyen")
        assert omur == timedelta(hours=6)


class TestBayatKontrol:
    """Ö-2: bayat_mi fonksiyonu doğru çalışıyor mu?"""

    def test_taze_kayit(self):
        """1 saat önce oluşturulmuş kayıt taze olmalı."""
        simdi = datetime(2026, 8, 22, 14, 0)
        once = datetime(2026, 8, 22, 13, 30)  # 30 dk once
        sonuc = bayat_mi(once.strftime("%Y-%m-%d"),
                         tip="olcum", simdi=simdi)
        # Tarih-gun bazli, 30 dk fark 1 gun icinde
        assert not sonuc["bayat"]

    def test_eski_kayit_bayat(self):
        """2 gun once oluşturulmuş ölçüm kaydı bayat olmalı."""
        simdi = datetime(2026, 8, 22, 14, 0)
        once = datetime(2026, 8, 20, 14, 0)  # 2 gun once
        sonuc = bayat_mi(once.strftime("%Y-%m-%d"),
                         tip="olcum", simdi=simdi)
        assert sonuc["bayat"]

    def test_git_1_saat_sonra_bayat(self):
        """Git ölçümü 1 saatten sonra bayat olmalı."""
        simdi = datetime(2026, 8, 22, 14, 0)
        # Tarih gun bazli, 1 gun once = 24 saat once -> bayat
        once = datetime(2026, 8, 21, 14, 0)
        sonuc = bayat_mi(once.strftime("%Y-%m-%d"),
                         tip="git", simdi=simdi)
        assert sonuc["bayat"]

    def test_karar_30_gun_taze(self):
        """Karar 30 gün taze olmalı."""
        simdi = datetime(2026, 8, 22)
        once = datetime(2026, 8, 1)  # 21 gun once
        sonuc = bayat_mi(once.strftime("%Y-%m-%d"),
                         tip="karar", simdi=simdi)
        assert not sonuc["bayat"]

    def test_karar_30_gun_bayat(self):
        """Karar 30 günden sonra bayat olmalı."""
        simdi = datetime(2026, 9, 22)
        once = datetime(2026, 8, 1)  # 52 gun once
        sonuc = bayat_mi(once.strftime("%Y-%m-%d"),
                         tip="karar", simdi=simdi)
        assert sonuc["bayat"]

    def test_sonsuz_asla_bayat(self):
        """Sonsuz ömürlü kayıt asla bayat olmaz."""
        simdi = datetime(2030, 1, 1)
        once = datetime(2020, 1, 1)  # 10 yil once
        sonuc = bayat_mi(once.strftime("%Y-%m-%d"),
                         tip="sonsuz", simdi=simdi)
        assert not sonuc["bayat"]
        assert sonuc["omur"] == "sonsuz"

    def test_bos_tarih(self):
        """Boş tarih bayat olmamalı."""
        sonuc = bayat_mi("")
        assert not sonuc["bayat"]

    def test_hatali_tarih(self):
        """Hatalı format bayat olmamalı."""
        sonuc = bayat_mi("22-08-2026")
        assert not sonuc["bayat"]

    def test_site_1_gun_taze(self):
        """Site ölçümü 1 gün taze olmalı."""
        simdi = datetime(2026, 8, 22, 12, 0)
        once = datetime(2026, 8, 22, 6, 0)  # 6 saat once
        sonuc = bayat_mi(once.strftime("%Y-%m-%d"),
                         tip="site", simdi=simdi)
        # Gun bazli, ayni gun -> taze
        assert not sonuc["bayat"]


class TestDefterBayatKontrol:
    """Ö-2: Defter INDEX bayat kontrolü."""

    def test_bos_defter(self):
        """Boş defter boş liste döndürmeli."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sonuclar = defter_bayat_kontrol(tmpdir)
            assert sonuclar == []

    def test_taze_kayitlar(self):
        """Taze kayıtlar bayat=False döndürmeli."""
        with tempfile.TemporaryDirectory() as tmpdir:
            index = os.path.join(tmpdir, "INDEX.md")
            bugun = datetime.now().strftime("%Y-%m-%d")
            with open(index, "w", encoding="utf-8") as f:
                f.write("# ORTAK DEFTER\n\n")
                f.write("| dosya | konu | kim | tarih | omur |\n")
                f.write("|---|---|---|---|---|\n")
                f.write("| test.md | Test | basak | %s | 30g |\n" % bugun)
            sonuclar = defter_bayat_kontrol(tmpdir)
            assert len(sonuclar) == 1
            assert not sonuclar[0]["bayat"]


class TestBayatOzet:
    """Ö-2: bayat_ozet fonksiyonu."""

    def test_bayat_yoksa_bos(self):
        """Bayat kayıt yoksa boş string dönmeli."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sonuc = bayat_ozet(tmpdir)
            assert sonuc == ""

    def test_bayat_varsa_ozet(self):
        """Bayat kayıt varsa özet dönmeli."""
        with tempfile.TemporaryDirectory() as tmpdir:
            index = os.path.join(tmpdir, "INDEX.md")
            eski = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
            with open(index, "w", encoding="utf-8") as f:
                f.write("# ORTAK DEFTER\n\n")
                f.write("| dosya | konu | kim | tarih | omur |\n")
                f.write("|---|---|---|---|---|\n")
                f.write("| eski.md | Eski | basak | %s | 6s |\n" % eski)
            sonuc = bayat_ozet(tmpdir)
            assert "BAYAT" in sonuc or "bayat" in sonuc.lower()
