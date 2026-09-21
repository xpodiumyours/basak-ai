"""tests/test_arac_disiplini.py — Canli probun CEVRIMDISI testleri.

Probun kendisi gercek kota harcar ve burada kosulmaz. Burada yalniz
siniflandirma mantigi ve senaryo guvenligi kilitlenir: yanlis siniflandiran
bir prob, yanlis sayi uretir; yanlis senaryo ise veriyi degistirebilir.
"""

import importlib.util
import os
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YOL = os.path.join(KOK, "tests", "live", "arac_disiplini.py")

_spec = importlib.util.spec_from_file_location("arac_disiplini", YOL)
ad_mod = importlib.util.module_from_spec(_spec)
sys.modules["arac_disiplini"] = ad_mod
_spec.loader.exec_module(ad_mod)

# Prob yalniz SALT-OKUNUR arac kosmali: Casper'in verisi degismemeli.
SALT_OKUNUR = {
    "list_files", "simdi", "hesapla", "git_gecmis", "git_durum",
    "read_file", "icerik_ara", "belge_ara",
}


class TestSiniflandirma:
    def test_arac_istenip_kosmazsa_tarif(self):
        assert ad_mod._durum_bul([], ("list_files",), "") == "TARIF"

    def test_beklenen_arac_kostuysa_arac(self):
        assert ad_mod._durum_bul(["list_files"], ("list_files",), "") == "ARAC"

    def test_beklenmeyen_arac_kostuysa_yine_tarif(self):
        assert ad_mod._durum_bul(["simdi"], ("list_files",), "") == "TARIF"

    def test_arac_gerekmezse_temiz(self):
        assert ad_mod._durum_bul([], (), "") == "TEMIZ"

    def test_gereksiz_arac_fazla_arac(self):
        assert ad_mod._durum_bul(["simdi"], (), "") == "FAZLA_ARAC"

    def test_hata_her_seyi_ezer(self):
        assert ad_mod._durum_bul([], ("list_files",), "kota bitti") == "HATA"
        assert ad_mod._durum_bul(["list_files"], (), "kota bitti") == "HATA"


class TestOlayAyiklama:
    def test_bitir_cevap_ve_kaynak(self):
        olaylar = ['BasakUI.thinking()',
                   'BasakUI.bitir("merhaba", "groq")']
        cevap, kaynak, hata = ad_mod._olaylari_ayikla(olaylar)
        assert cevap == "merhaba" and kaynak == "groq" and hata == ""

    def test_error_yakalanir(self):
        cevap, kaynak, hata = ad_mod._olaylari_ayikla(
            ['BasakUI.error("kota doldu")'])
        assert hata == "kota doldu" and cevap == ""

    def test_bozulursa_patlamaz(self):
        cevap, kaynak, hata = ad_mod._olaylari_ayikla(['BasakUI.bitir('])
        assert isinstance((cevap, kaynak, hata), tuple)


class TestSenaryoGuvenligi:
    def test_senaryolar_dolu(self):
        assert ad_mod.SENARYOLAR
        for etiket, mesaj, _ in ad_mod.SENARYOLAR:
            assert etiket.strip() and mesaj.strip()

    def test_yalniz_salt_okunur_araclar_beklenir(self):
        for etiket, _, beklenen in ad_mod.SENARYOLAR:
            fazla = set(beklenen) - SALT_OKUNUR
            assert not fazla, "%s senaryosu yazan araca bagli: %s" % (
                etiket, fazla)

    def test_aracsiz_kontrol_senaryosu_var(self):
        """En az bir 'duz sohbet' kontrolu olmali (gereksiz arac olcumu)."""
        assert any(not beklenen for _, _, beklenen in ad_mod.SENARYOLAR)
