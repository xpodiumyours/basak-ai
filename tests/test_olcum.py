"""tests/test_olcum.py — Ö-1 ölçüm aracı testleri (ağsız).

Beyaz liste dışı proje ASLA çalışmaz; git yalnız sabit okuma komutlarıyla
koşar (shell yok); belge_ara düz metin aramasıdır; dosya_bilgi yolun proje
dışına taşmasını engeller. Gerçek git ölçümü 'basak' deposuyla yapılır.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.olcum import PROJELER, git_durum, belge_ara, dosya_bilgi


class TestBeyazListe:
    def test_bilinmeyen_proje_calismaz(self):
        r = git_durum("hayali-proje")
        assert "error" in r and "basak" in r["error"]

    def test_bos_proje_calismaz(self):
        r = git_durum("")
        assert "error" in r

    def test_yol_benzeri_girdi_calismaz(self):
        # Beyaz listede anahtar degil, yol — bu yuzden tasima denemesi de duser
        r = git_durum(r"..\..\Windows")
        assert "error" in r

    def test_buyuk_kucuk_onemsiz(self):
        assert "vixrex" in PROJELER
        assert PROJELER.get("ViXReX".lower()) is not None


class TestGitDurum:
    def test_basak_gercek_olcum(self):
        r = git_durum("basak")
        assert "result" in r
        assert "Dal:" in r["result"]
        assert "Son commit:" in r["result"]
        assert "Commit edilmemis dosya:" in r["result"]

    def test_cikti_sinirli(self):
        r = git_durum("basak")
        if "result" in r:
            assert len(r["result"]) < 3000


class TestBelgeAra:
    def test_gercek_eslesme(self):
        # GOREV_LISTESI.md'de 'kanit' gecer (Turkce katlamasiyla 'kanit')
        r = belge_ara("basak", "kanit")
        assert "result" in r
        assert ".md:" in r["result"]

    def test_bulunamayan_sorgu_hata_doner(self):
        r = belge_ara("basak", "zzzqwx1239")
        assert "error" in r

    def test_bos_sorgu_hata_doner(self):
        r = belge_ara("basak", "")
        assert "error" in r


class TestDosyaBilgi:
    def test_varolan_dosya(self):
        r = dosya_bilgi("basak", "AGENTS.md")
        assert "result" in r and "var |" in r["result"]

    def test_olmayan_dosya_hata(self):
        r = dosya_bilgi("basak", "yok-boyle-dosya.md")
        assert "error" in r

    def test_disari_tasan_yol_engellenir(self):
        r = dosya_bilgi("basak", r"..\..\Windows\win.ini")
        assert "error" in r and "tasiyor" in r["error"]
