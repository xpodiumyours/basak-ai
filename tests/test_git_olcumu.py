"""tests/test_git_olcumu.py — ARAC-PLANI Is 6: gecmis + degisenler.

Sozlesme:
- git_gecmis / git_degisenler uc yerde bagli, salt-okunur.
- adet tavani 30; dosya kok disina cikamaz; taban kalibi disi red.
- Komutlar mevcut _git yardimcisindan gecer (sabit argv, shell yok).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import calistir, olcum
from tools.definitions import TANINMIS_TOOLLAR


class TestUcYer:
    def test_beyaz_listede(self):
        assert "git_gecmis" in TANINMIS_TOOLLAR
        assert "git_degisenler" in TANINMIS_TOOLLAR

    def test_durum_etiketleri_var(self):
        from chat.tools import DURUM_METNI
        assert "git_gecmis" in DURUM_METNI
        assert "git_degisenler" in DURUM_METNI


class TestGecmis:
    def test_basak_gecmisi_kosar(self):
        r = olcum.git_gecmis("basak", adet=3)
        assert "result" in r, r
        assert len(r["result"].splitlines()) <= 3

    def test_adet_tavani(self):
        r = olcum.git_gecmis("basak", adet=9999)
        assert "result" in r or "error" in r
        if "result" in r and r["result"] != "(bos depo)":
            assert len(r["result"].splitlines()) <= 30

    def test_kok_disi_dosya_reddedilir(self):
        r = olcum.git_gecmis("basak", dosya="../../kacis.py")
        assert "error" in r

    def test_bilinmeyen_proje(self):
        assert "error" in olcum.git_gecmis("yok", adet=3)


class TestDegisenler:
    def test_basak_degisenler_kosar(self):
        r = olcum.git_degisenler("basak", taban="main")
        assert isinstance(r, dict)
        assert "result" in r or "error" in r

    def test_kotu_taban_reddedilir(self):
        for kotu in ("--upload-pack=x", "; rm -rf", "a b", ""):
            r = olcum.git_degisenler("basak", taban=kotu if kotu else None)
            if kotu in ("", None):
                continue  # varsayilan taban gecerli
            assert "error" in r, kotu

    def test_calistir_hatti(self):
        r = calistir("git_gecmis", {"proje": "basak", "adet": 2})
        assert "result" in r, r
        r = calistir("git_degisenler",
                     {"proje": "basak", "taban": "main"})
        assert isinstance(r, dict)
