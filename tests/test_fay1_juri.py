"""tests/test_fay1_juri.py — FAY-1: Paralel jüri testleri.

Kural: çelişki sorusu birden fazla ücretsiz sağlayıcıya PARALEL gider.
- tüm geçerli oylar çelişiyor -> "kesin"
- çoğunluk çelişiyor ama bölünme var -> "bolunme" (insan kararı)
- uydurma tanık adı veren üyenin oyu SAYILMAZ
- hata veren üye diğerlerini bozmaz
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.fay import juri_carpistir

IDDIALAR = [{"tanik": "belge", "iddia": "plani tamamlandi"},
            {"tanik": "git", "iddia": "commit edilmemis 12 dosya"}]


def uyeler(*davranislar):
    """davranislar: her uye icin donen metin (veya Exception)."""
    uyeler = []
    for i, d in enumerate(davranislar):
        adi = "uye%d" % i
        if isinstance(d, Exception):
            def fn(m, d=d):
                raise d
        else:
            def fn(m, d=d):
                return {"content": d}
        uyeler.append((adi, fn))
    return uyeler


CELIS = "[CELISIYOR] belge vs git: plan bitti deniyor ama commit yok"
YOK = "[SORUN YOK]"


class TestOylama:
    def test_uc_uyeden_uc_celisiyor_kesin(self):
        sonuc = juri_carpistir(IDDIALAR,
                               uyeler(CELIS, CELIS, CELIS))
        assert sonuc["karar"] == "kesin"
        assert sonuc["celisen_cift"] == ("belge", "git")
        assert len(sonuc["oylar"]) == 3

    def test_bolunme_isaretlenir(self):
        """2/1 bölünme — asıl değerli belirsizlik sinyali."""
        sonuc = juri_carpistir(IDDIALAR,
                               uyeler(CELIS, CELIS, YOK))
        assert sonuc["karar"] == "bolunme"
        # karsi oy da kayitta
        karsilar = [o for o in sonuc["oylar"] if o["oy"] is False]
        assert len(karsilar) == 1

    def test_cogunluk_sorun_yoksa_atlanir(self):
        sonuc = juri_carpistir(IDDIALAR,
                               uyeler(YOK, YOK, CELIS))
        assert sonuc["karar"] == "yok"

    def test_uydurma_oyu_gecerli_sayilmaz(self):
        uydurma = "[CELISIYOR] canli vs hafiza: tutarsiz"
        sonuc = juri_carpistir(IDDIALAR,
                               uyeler(CELIS, uydurma, YOK))
        # uyduran üyenin oyu None -> karara katilmaz; kalan 2 oy (1-1)
        # bolunme verir
        assert sonuc["karar"] == "bolunme"
        gecersiz = [o for o in sonuc["oylar"] if o["oy"] is None]
        assert len(gecersiz) == 1
        assert all(o["oy"] is not True or o["gerekce"] != "uydurma"
                   for o in sonuc["oylar"])

    def test_hata_veren_uye_digerlerini_bozmaz(self):
        sonuc = juri_carpistir(
            IDDIALAR,
            uyeler(RuntimeError("saglayici down"), CELIS, CELIS))
        assert sonuc["karar"] == "kesin"
        hatali = [o for o in sonuc["oylar"] if o["oy"] is None]
        assert len(hatali) == 1


class TestParalellikVeGuvenlik:
    def test_az_iki_tanik_altinda_yok(self):
        tek = [{"tanik": "git", "iddia": "tek tanik yeterli degil"}]
        sonuc = juri_carpistir(tek, uyeler(CELIS, CELIS))
        assert sonuc["karar"] == "yok" and sonuc["celisen_cift"] is None

    def test_juri_boslugu_yok_karari(self):
        sonuc = juri_carpistir(IDDIALAR, [])
        assert sonuc["karar"] == "yok"
