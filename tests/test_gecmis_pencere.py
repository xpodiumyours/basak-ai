"""tests/test_gecmis_pencere.py — Baglam diyeti Adim 3: kilo limitli gecmis.

Kural: "son N mesaj" yerine en yeniden geriye dogru karakter butcesiyle
toplanma. Mesajlar butun halde tutulur, kronoloji korunur, her kosulda
en yeni mesaj gecer. Kesim YALNIZ model penceresini ilgilendirir —
hafizaya yazma bundan once yapilir (kesim = unutmak degil).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chat import GECMIS_KILO_LIMITI, _gecmis_pencere


def mesaj(role, icerik):
    return {"role": role, "content": icerik}


class TestGecmisPencere:
    def test_bos_ve_none_guvenli(self):
        assert _gecmis_pencere([]) == []
        assert _gecmis_pencere(None) == []

    def test_kisa_sohbetin_hepsi_alinir(self):
        gecmis = [mesaj("user", "selam"), mesaj("assistant", "merhaba")]
        assert len(_gecmis_pencere(gecmis)) == 2

    def test_limit_asilinca_eskiler_duser(self):
        gecmis = ([mesaj("user", "x" * 2500),
                   mesaj("assistant", "y" * 2500),
                   mesaj("user", "son soru"),
                   mesaj("assistant", "son cevap")])
        sonuc = _gecmis_pencere(gecmis, limit=4000)
        icerikler = [m["content"] for m in sonuc]
        assert "son soru" in icerikler and "son cevap" in icerikler
        assert all(not c.startswith("xxx") for c in icerikler)
        assert len(sonuc) == 3  # y mesaji butun halde kalir, x duser

    def test_en_yeni_mesaj_her_kosulda_garanti(self):
        dev = mesaj("assistant", "z" * (GECMIS_KILO_LIMITI * 2))
        assert _gecmis_pencere([dev]) == [dev]

    def test_mesaj_ortasindan_kesilmez(self):
        uzun = "A" * 3000
        gecmis = [mesaj("user", uzun), mesaj("assistant", "kisa")]
        sonuc = _gecmis_pencere(gecmis, limit=3100)
        # 'uzun' butun halde ya yasar ya duser; yarim A dizisi donmez
        for m in sonuc:
            assert m["content"] in (uzun, "kisa")

    def test_kronolojik_sira_korunur(self):
        gecmis = [mesaj("user", "1"), mesaj("assistant", "2"),
                  mesaj("user", "3"), mesaj("assistant", "4")]
        sonuc = [m["content"] for m in _gecmis_pencere(gecmis)]
        assert sonuc == ["1", "2", "3", "4"]

    def test_adet_siniri_yine_gecerli(self):
        gecmis = [mesaj("user", str(i)) for i in range(50)]
        assert len(_gecmis_pencere(gecmis)) == 20

    def test_content_none_olursa_cokmez(self):
        gecmis = [{"role": "assistant", "content": None},
                  mesaj("user", "soru")]
        assert [m["content"] for m in _gecmis_pencere(gecmis)] == [None, "soru"]
