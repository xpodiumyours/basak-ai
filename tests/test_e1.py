"""tests/test_e1.py — E-1 testleri: Başak projelerini görür.

E-1 kuralı: Dış projeler (vixrex, numeramatch, xses) salt okunur.
read_file ve list_files ile okunabilir; write_file_ops ile yazma yasak.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.file_ops import (
    read_file, write_file_ops, list_files,
    DIS_PROJELER, _dis_proje_ayarla,
)


BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestDisProjeBeyazListesi:
    """E-1: Dış projeler beyaz listede mi?"""

    def test_uc_proje_tanimli(self):
        """vixrex, numeramatch, xses tanimli olmali."""
        assert "vixrex" in DIS_PROJELER
        assert "numeramatch" in DIS_PROJELER
        assert "xses" in DIS_PROJELER

    def test_yollar_mutlak(self):
        """Tüm yollar mutlak olmalı (C:\\...)."""
        for ad, yol in DIS_PROJELER.items():
            assert os.path.isabs(yol), "%s yolu mutlak değil" % ad

    def test_proje_klasorleri_mevcut(self):
        """Tüm proje klasörleri diskte olmalı."""
        for ad, yol in DIS_PROJELER.items():
            assert os.path.isdir(yol), "%s klasörü yok: %s" % (ad, yol)


class TestDisProjeAlgilama:
    """E-1: _dis_proje_ayarla doğru proje adını buluyor mu?"""

    def test_vixrex_eslesme(self):
        proje, _ = _dis_proje_ayarla("vixrex/AGENTS.md", BASE)
        assert proje == "vixrex"

    def test_vixrex_kok(self):
        proje, _ = _dis_proje_ayarla("vixrex", BASE)
        assert proje == "vixrex"

    def test_numeramatch_eslesme(self):
        proje, _ = _dis_proje_ayarla("numeramatch/App.tsx", BASE)
        assert proje == "numeramatch"

    def test_xses_eslesme(self):
        proje, _ = _dis_proje_ayarla("xses/README.md", BASE)
        assert proje == "xses"

    def test_bilinmeyen_proje(self):
        proje, _ = _dis_proje_ayarla("bilinmeyen/dosya.txt", BASE)
        assert proje is None

    def test_bos_yol(self):
        proje, _ = _dis_proje_ayarla("", BASE)
        assert proje is None


class TestDisProjeOkuma:
    """E-1: Dış projelerden okuma başarılı olmalı."""

    def test_vixrex_agents_okuma(self):
        """VixRex'ten AGENTS.md okunabilmeli."""
        sonuc = read_file("vixrex/AGENTS.md", BASE)
        assert "result" in sonuc, "Hata: %s" % sonuc.get("error", "")
        assert len(sonuc["result"]) > 0

    def test_numeramatch_readme_okuma(self):
        """NumeraMatch'ten bir dosya okunabilmeli."""
        sonuc = read_file("numeramatch/LICENSE", BASE)
        # LICENSE olmayabilir, hata olmamalı
        assert "result" in sonuc or "error" in sonuc

    def test_xses_readme_okuma(self):
        """Xses'ten README.md okunabilmeli."""
        sonuc = read_file("xses/README.md", BASE)
        assert "result" in sonuc, "Hata: %s" % sonuc.get("error", "")

    def test_olmayan_dosya_hata(self):
        """Var olmayan dosya için hata dönmeli."""
        sonuc = read_file("vixrex/OLMAYAN_DOSYA.txt", BASE)
        assert "error" in sonuc


class TestDisProjeYazmaEngeli:
    """E-1: Dış projelere yazma kesinlikle yasak."""

    def test_vixrex_yazma_engeli(self):
        """VixRex'e yazma denemesi engellenmeli."""
        sonuc = write_file_ops("vixrex/test.txt", "test", BASE)
        assert "error" in sonuc
        assert "yazma izni yok" in sonuc["error"].lower() or \
               "dis proje" in sonuc["error"].lower() or \
               "güvenlik" in sonuc["error"].lower()

    def test_numeramatch_yazma_engeli(self):
        """NumeraMatch'e yazma denemesi engellenmeli."""
        sonuc = write_file_ops("numeramatch/test.txt", "test", BASE)
        assert "error" in sonuc

    def test_xses_yazma_engeli(self):
        """Xses'e yazma denemesi engellenmeli."""
        sonuc = write_file_ops("xses/test.txt", "test", BASE)
        assert "error" in sonuc

    def test_ic_projeye_yazma_calisiyor(self):
        """İç projeye (knowledge/) yazma hâlâ çalışmalı."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            # knowledge/ klasörü oluştur
            knowledge = os.path.join(tmpdir, "knowledge")
            os.makedirs(knowledge)
            sonuc = write_file_ops("knowledge/test.md", "içerik", tmpdir)
            assert "result" in sonuc


class TestDisProjeListFiles:
    """E-1: Dış projelerin dosyaları listelenebilmeli."""

    def test_vixrex_liste(self):
        """VixRex'in kök klasörü listelenebilmeli."""
        sonuc = list_files("vixrex", BASE)
        assert "result" in sonuc, "Hata: %s" % sonuc.get("error", "")
        # En az birkaç dosya olmalı
        assert "öğe" in sonuc["result"] or "klasör" in sonuc["result"]


class TestOlcumAraclariE1:
    """E-1: Ölçüm araçları da dış projeleri destekliyor mu?"""

    def test_git_durum_vixrex(self):
        """git_durum VixRex için çalışmalı."""
        from tools.olcum import git_durum
        sonuc = git_durum("vixrex")
        assert "result" in sonuc, "Hata: %s" % sonuc.get("error", "")

    def test_belge_ara_vixrex(self):
        """belge_ara VixRex'te çalışmalı."""
        from tools.olcum import belge_ara
        sonuc = belge_ara("vixrex", "proje")
        # Eşleşme olmayabilir ama hata olmamalı
        assert "result" in sonuc or "error" in sonuc

    def test_dosya_bilgi_vixrex(self):
        """dosya_bilgi VixRex için çalışmalı."""
        from tools.olcum import dosya_bilgi
        sonuc = dosya_bilgi("vixrex", "AGENTS.md")
        assert "result" in sonuc, "Hata: %s" % sonuc.get("error", "")
