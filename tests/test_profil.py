"""tests/test_profil.py — Kalici profil + konusarak ogrenme testleri.

2026-09-09 (Casper karari): hafiza kalici, tanima konusarak.
Kurallar:
- Profil meta tablosunda durur: budanmaz, episodik temizlemede silinmez.
- Ogrenme kural tabanli, ekstra model cagrisi yok.
- Hassas cumleden (sifre/TC/kart/telefon) ogrenme YOK.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory import HafizaMotoru
from memory.profil import (bos_profil, cikar, ogren, unut, blok,
                           profil_al, profil_koy)


def _motor(tmp_path):
    return HafizaMotoru(db_yolu=str(tmp_path / "profil.db"))


class TestCikar:
    def test_ad_kaliplari(self):
        assert ("ad", "Casper") in cikar("benim adım Casper")
        assert ("ad", "Casper") in cikar("adım Casper")
        assert ("ad", "Casper") in cikar("bana Casper de")

    def test_hatirla(self):
        assert ("bilgi", "yarın dişçiye gideceğim") in cikar(
            "hatırla: yarın dişçiye gideceğim")

    def test_sevme(self):
        assert ("tercih", "çayı seviyor") in cikar("ben çayı seviyorum")
        assert ("tercih", "kahve sevmiyor") in cikar("kahve sevmem")

    def test_meslek(self):
        assert ("bilgi", "mühendis") in cikar("ben mühendisim")

    def test_sehir(self):
        out = cikar("ben İstanbul'da yaşıyorum")
        assert any("yaşıyor" in d for _a, d in out)

    def test_bos_cumle_ogrenmez(self):
        assert cikar("selam naber") == []
        assert cikar("") == []

    def test_hassas_cumleden_ogrenme_yok(self):
        assert cikar("şifrem 12345 hatırla") == []
        assert cikar("benim adım Casper, kart no 1111") == []
        assert cikar("telefonum 0532 hatırla") == []


class TestProfilKalıcılık:
    def test_ogren_yazar_ve_blok_gosterir(self, tmp_path):
        m = _motor(tmp_path)
        yeniler = ogren(m, "benim adım Casper")
        assert ("ad", "Casper") in yeniler
        assert "Casper" in blok(m)

    def test_tekrar_ogrenme_kayit_acmaz(self, tmp_path):
        m = _motor(tmp_path)
        ogren(m, "benim adım Casper")
        assert ogren(m, "benim adım Casper") == []

    def test_episodik_temizleme_profile_dokunmaz(self, tmp_path):
        m = _motor(tmp_path)
        ogren(m, "benim adım Casper")
        m.episodik_temizle()
        assert profil_al(m)["ad"] == "Casper"
        assert "Casper" in blok(m)

    def test_unut_tek_kayit_siler(self, tmp_path):
        m = _motor(tmp_path)
        ogren(m, "ben çayı seviyorum")
        assert unut(m, "unut: çay") == 1
        assert "çay" not in blok(m)

    def test_unut_hepsi_sifirlar(self, tmp_path):
        m = _motor(tmp_path)
        ogren(m, "benim adım Casper")
        assert unut(m, "hakkımdaki her şeyi unut") == -1
        assert blok(m) == ""

    def test_bos_profilda_blok_bos(self, tmp_path):
        m = _motor(tmp_path)
        assert blok(m) == ""
        assert profil_al(m) == bos_profil()

    def test_profil_koy_okur(self, tmp_path):
        m = _motor(tmp_path)
        assert profil_koy(m, {"ad": "X", "tercihler": [], "bilgiler": []})
        assert profil_al(m)["ad"] == "X"
