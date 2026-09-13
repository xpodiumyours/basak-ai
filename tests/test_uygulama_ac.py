"""tests/test_uygulama_ac.py — ARAC-PLANI Is 3: uygulama acma.

Sozlesme:
- ac_uygulama uc yerde bagli (sema + calistir + DURUM_METNI).
- Beyaz liste disi ad REDDEDILIR, hicbir surec baslatilmaz.
- Gercek uygulama BASLATILMAZ — beyaz liste disi + parametre
  reddi yollari test edilir (guvenlik); basari yolu monkeypatch
  ile kanitlanir.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import app_launcher, calistir
from tools.definitions import TANINMIS_TOOLLAR


class TestUcYer:
    def test_beyaz_listede(self):
        assert "ac_uygulama" in TANINMIS_TOOLLAR

    def test_durum_etiketi_var(self):
        from chat.tools import DURUM_METNI
        assert "ac_uygulama" in DURUM_METNI


class TestBeyazListe:
    def test_bilinmeyen_reddedilir(self):
        r = app_launcher.ac_uygulama("format-c")
        assert "error" in r and "beyaz liste" in r["error"]

    def test_bos_ad_reddedilir(self):
        assert "error" in app_launcher.ac_uygulama("  ")

    def test_tarayici_url_kalibi(self):
        r = app_launcher.ac_uygulama("tarayici", "file:///etc/passwd")
        assert "error" in r

    def test_kabuk_metakarakteri_reddedilir(self, monkeypatch):
        baslatildi = []
        monkeypatch.setattr(app_launcher.subprocess, "Popen",
                            lambda *a, **k: baslatildi.append(a))
        r = app_launcher.ac_uygulama("notepad", "a.txt & calc")
        assert "error" in r
        assert baslatildi == []

    def test_basari_yolu_surec_baslatir(self, monkeypatch):
        baslatildi = []

        class SahteSurec:
            pass

        monkeypatch.setattr(
            app_launcher.subprocess, "Popen",
            lambda *a, **k: (baslatildi.append(a), SahteSurec())[1])
        r = app_launcher.ac_uygulama("calculator")
        assert "result" in r, r
        assert baslatildi and baslatildi[0][0] == ["calc"]

    def test_calistir_hatti_reddi(self):
        r = calistir("ac_uygulama", {"uygulama": "yok-boyle-sey"})
        assert "error" in r
