"""tests/test_o3.py — Ö-3 testleri: Kendi kendine gelişme.

Ö-3 kuralı:
1. Açık iddialar defterden çekilebilmeli
2. Yeni ölçümle iddia doğrulanabilmeli/çürütülebilmeli
3. İddia durumu güncellenebilmeli
4. Karne güncellenebilmeli
"""

import json
import os
import sys
import tempfile
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.bayat import (
    acik_iddialari_cek, yeniden_sinav, iddia_guncelle,
    karnayi_guncelle, karne_ozet,
    _karne_yukle, _karne_kaydet, _frontmatter_oku,
)


class TestAcikIddialar:
    """Ö-3: Açık iddiaları çekme."""

    def test_bos_defter(self):
        """Boş defter boş liste döndürmeli."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sonuc = acik_iddialari_cek(tmpdir)
            assert sonuc == []

    def test_acik_iddia_var(self):
        """Açık iddia (tip: olcum, durum yok) çekilmeli."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dosya = os.path.join(tmpdir, "test-iddia.md")
            with open(dosya, "w", encoding="utf-8") as f:
                f.write("---\n")
                f.write("kim: basak\n")
                f.write("tarih: 2026-08-22\n")
                f.write("konu: test konusu\n")
                f.write("tip: olcum\n")
                f.write("kaynak: git log\n")
                f.write("---\n\n")
                f.write("Bu bir test iddiasi.\n")
            iddialar = acik_iddialari_cek(tmpdir)
            assert len(iddialar) == 1
            assert iddialar[0]["konu"] == "test konusu"
            assert iddialar[0]["tip"] == "olcum"

    def test_kapali_iddia_cekilmez(self):
        """Durum: confirm veya refute olan iddia çekilmemeli."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dosya = os.path.join(tmpdir, "kapali.md")
            with open(dosya, "w", encoding="utf-8") as f:
                f.write("---\n")
                f.write("kim: basak\n")
                f.write("tip: olcum\n")
                f.write("durum: confirm\n")
                f.write("---\n\n")
                f.write("Kapali iddia.\n")
            iddialar = acik_iddialari_cek(tmpdir)
            assert len(iddialar) == 0

    def test_soru_tipi_cekilmez(self):
        """tip: soru olan iddia çekilmemeli."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dosya = os.path.join(tmpdir, "soru.md")
            with open(dosya, "w", encoding="utf-8") as f:
                f.write("---\n")
                f.write("kim: casper\n")
                f.write("tip: soru\n")
                f.write("---\n\n")
                f.write("Bu bir soru.\n")
            iddialar = acik_iddialari_cek(tmpdir)
            assert len(iddialar) == 0

    def test_index_cekilmez(self):
        """INDEX.md çekilmemeli."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dosya = os.path.join(tmpdir, "INDEX.md")
            with open(dosya, "w", encoding="utf-8") as f:
                f.write("# INDEX\n")
            iddialar = acik_iddialari_cek(tmpdir)
            assert len(iddialar) == 0


class TestYenidenSinav:
    """Ö-3: Yeni ölçümle iddia karşılaştırma."""

    def test_destek(self):
        """Ortak kelime fazlaysa confirm dönmeli."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dosya = os.path.join(tmpdir, "iddia.md")
            with open(dosya, "w", encoding="utf-8") as f:
                f.write("---\nkonu: test\n---\n\n")
                f.write("Basak calisiyor ve Groq kullaniliyor.\n")
            sonuc = yeniden_sinav(dosya,
                                  "Basak calisiyor Groq ile baglanti kuruldu")
            assert sonuc["sonuc"] == "confirm"

    def test_caturutme(self):
        """Ortak kelime azsa refute dönmeli."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dosya = os.path.join(tmpdir, "iddia.md")
            with open(dosya, "w", encoding="utf-8") as f:
                f.write("---\nkonu: test\n---\n\n")
                f.write("Groq kotasini dolmus.\n")
            sonuc = yeniden_sinav(dosya,
                                  "Tamamen farkli bir konu hakkinda yazdim")
            assert sonuc["sonuc"] == "refute"

    def test_belirsiz(self):
        """Ortak kelime ortadaysa unknown dönmeli."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dosya = os.path.join(tmpdir, "iddia.md")
            with open(dosya, "w", encoding="utf-8") as f:
                f.write("---\nkonu: test\n---\n\n")
                f.write("Groq ve Gemini kullaniliyor.\n")
            sonuc = yeniden_sinav(dosya,
                                  "Groq ile ilgili bir sorun var")
            assert sonuc["sonuc"] in ("confirm", "unknown")

    def test_bos_olcum(self):
        """Boş ölçüm metni unknown döndürmeli."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dosya = os.path.join(tmpdir, "iddia.md")
            with open(dosya, "w", encoding="utf-8") as f:
                f.write("---\nkonu: test\n---\n\n")
                f.write("Icerik var.\n")
            sonuc = yeniden_sinav(dosya, "")
            assert sonuc["sonuc"] == "unknown"


class TestIddiaGuncelle:
    """Ö-3: İddia durumu güncelleme."""

    def test_confirm(self):
        """confirm ile durum güncellenebilmeli."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dosya = os.path.join(tmpdir, "iddia.md")
            with open(dosya, "w", encoding="utf-8") as f:
                f.write("---\nkonu: test\ntip: olcum\n---\n\n")
                f.write("Icerik.\n")
            assert iddia_guncelle(dosya, "confirm")
            with open(dosya, "r", encoding="utf-8") as f:
                icerik = f.read()
            assert "durum: confirm" in icerik

    def test_refute(self):
        """refute ile durum güncellenebilmeli."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dosya = os.path.join(tmpdir, "iddia.md")
            with open(dosya, "w", encoding="utf-8") as f:
                f.write("---\nkonu: test\n---\n\n")
                f.write("Icerik.\n")
            assert iddia_guncelle(dosya, "refute")
            with open(dosya, "r", encoding="utf-8") as f:
                icerik = f.read()
            assert "durum: refute" in icerik

    def test_mevcut_durum_guncelle(self):
        """Mevcut durum alanı güncellenmeli (yenisini eklememeli)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dosya = os.path.join(tmpdir, "iddia.md")
            with open(dosya, "w", encoding="utf-8") as f:
                f.write("---\nkonu: test\ndurum: acik\n---\n\n")
                f.write("Icerik.\n")
            iddia_guncelle(dosya, "confirm")
            with open(dosya, "r", encoding="utf-8") as f:
                icerik = f.read()
            # "durum: acik" olmamalı, "durum: confirm" olmalı
            assert "durum: acik" not in icerik
            assert "durum: confirm" in icerik


class TestKarne:
    """Ö-3: Karne güncelleme ve özet."""

    def test_karnayi_guncelle(self):
        """Karne güncellenebilmeli."""
        with tempfile.TemporaryDirectory() as tmpdir:
            karne_yolu = os.path.join(tmpdir, "data", "karne.json")
            # Geçici olarak karne yolunu değiştir
            import tools.bayat as bayat_modulu
            eski = bayat_modulu._KARNE_DOSYASI
            bayat_modulu._KARNE_DOSYASI = karne_yolu
            try:
                sonuc = karnayi_guncelle("test_kaynak", "test_konu", dogru=True)
                assert sonuc["toplam"] == 1
                assert sonuc["dogru"] == 1
                assert sonuc["yanlis"] == 0

                karnayi_guncelle("test_kaynak", "test_konu", dogru=False)
                sonuc = karnayi_guncelle("test_kaynak", "test_konu", dogru=True)
                assert sonuc["toplam"] == 3
                assert sonuc["dogru"] == 2
                assert sonuc["yanlis"] == 1
            finally:
                bayat_modulu._KARNE_DOSYASI = eski

    def test_karne_ozet(self):
        """Karne özeti okunabilir olmalı."""
        with tempfile.TemporaryDirectory() as tmpdir:
            karne_yolu = os.path.join(tmpdir, "data", "karne.json")
            import tools.bayat as bayat_modulu
            eski = bayat_modulu._KARNE_DOSYASI
            bayat_modulu._KARNE_DOSYASI = karne_yolu
            try:
                karnayi_guncelle("kaynak1", "konu1", dogru=True)
                karnayi_guncelle("kaynak1", "konu1", dogru=False)
                ozet = karne_ozet("kaynak1")
                assert "kaynak1" in ozet
                assert "dogru" in ozet
            finally:
                bayat_modulu._KARNE_DOSYASI = eski

    def test_bos_karne(self):
        """Boş karne uygun mesaj döndürmeli."""
        with tempfile.TemporaryDirectory() as tmpdir:
            karne_yolu = os.path.join(tmpdir, "data", "karne.json")
            import tools.bayat as bayat_modulu
            eski = bayat_modulu._KARNE_DOSYASI
            bayat_modulu._KARNE_DOSYASI = karne_yolu
            try:
                ozet = karne_ozet()
                assert "bos" in ozet.lower() or "yok" in ozet.lower()
            finally:
                bayat_modulu._KARNE_DOSYASI = eski


class TestOtomatikSinavAkisi:
    """Ö-3: Tam otomatik sınav akışı entegrasyon testi."""

    def test_iddia_olustur_sinav_guncelle(self):
        """Açık iddia → ölçüm → çürütme → karne güncellemesi akışı."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. İddia oluştur
            dosya = os.path.join(tmpdir, "test-akisi.md")
            with open(dosya, "w", encoding="utf-8") as f:
                f.write("---\n")
                f.write("kim: basak\n")
                f.write("tarih: 2026-08-20\n")
                f.write("konu: groq kota\n")
                f.write("tip: olcum\n")
                f.write("kaynak: data/kota-gercek.md\n")
                f.write("---\n\n")
                f.write("Groq gunluk 1000 istek sinirinda.\n")

            # 2. Açık iddia çek
            iddialar = acik_iddialari_cek(tmpdir)
            assert len(iddialar) == 1
            assert iddialar[0]["dosya"] == "test-akisi.md"

            # 3. Yeni ölçümle çürüt
            sonuc = yeniden_sinav(dosya,
                                  "Tamamen farkli bir konu hakkinda konustum.")
            assert sonuc["sonuc"] == "refute"

            # 4. Durumu güncelle
            iddia_guncelle(dosya, "refute")
            with open(dosya, "r", encoding="utf-8") as f:
                assert "durum: refute" in f.read()

            # 5. Açık iddia artık çekilmemeli
            iddialar2 = acik_iddialari_cek(tmpdir)
            assert len(iddialar2) == 0
