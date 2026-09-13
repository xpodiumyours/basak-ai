"""tests/test_gecmis_pencere.py — geniş ve güvenli konuşma geçmişi penceresi.

Geçmiş sabit 4000 karaktere zorla düşürülmez. Yine de tek isteğin sınırsız
büyümemesi için geniş bir teknik bütçe ve mesaj sayısı tavanı korunur.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chat import GECMIS_KILO_LIMITI, MAX_HISTORY, _gecmis_pencere


def mesaj(role, icerik):
    return {"role": role, "content": icerik}


class TestGecmisPencere:
    def test_genis_varsayilan_butce(self):
        assert GECMIS_KILO_LIMITI >= 60000
        assert MAX_HISTORY >= 40

    def test_bos_ve_none_guvenli(self):
        assert _gecmis_pencere([]) == []
        assert _gecmis_pencere(None) == []

    def test_4000_karakteri_asan_sohbet_artik_kesilmez(self):
        gecmis = [
            mesaj("user", "x" * 2500),
            mesaj("assistant", "y" * 2500),
            mesaj("user", "son soru"),
            mesaj("assistant", "son cevap"),
        ]
        assert _gecmis_pencere(gecmis) == gecmis

    def test_acik_limit_verilirse_mesajlar_butun_kalir(self):
        gecmis = [
            mesaj("user", "x" * 2500),
            mesaj("assistant", "y" * 2500),
            mesaj("user", "son soru"),
            mesaj("assistant", "son cevap"),
        ]
        sonuc = _gecmis_pencere(gecmis, limit=4000)
        icerikler = [m["content"] for m in sonuc]
        assert "son soru" in icerikler and "son cevap" in icerikler
        assert all(not c.startswith("xxx") for c in icerikler)
        assert len(sonuc) == 3

    def test_en_yeni_mesaj_her_kosulda_garanti(self):
        dev = mesaj("assistant", "z" * (GECMIS_KILO_LIMITI * 2))
        assert _gecmis_pencere([dev]) == [dev]

    def test_kronolojik_sira_korunur(self):
        gecmis = [mesaj("user", "1"), mesaj("assistant", "2"),
                  mesaj("user", "3"), mesaj("assistant", "4")]
        sonuc = [m["content"] for m in _gecmis_pencere(gecmis)]
        assert sonuc == ["1", "2", "3", "4"]

    def test_adet_siniri_yine_gecerli(self):
        gecmis = [mesaj("user", str(i)) for i in range(MAX_HISTORY + 10)]
        assert len(_gecmis_pencere(gecmis)) == MAX_HISTORY

    def test_content_none_olursa_cokmez(self):
        gecmis = [{"role": "assistant", "content": None},
                  mesaj("user", "soru")]
        assert [m["content"] for m in _gecmis_pencere(gecmis)] == [None, "soru"]
