"""tests/testgecmis_pencere.py — ozgur-ajan: gecmis kirpmasiz verilir.

2026-09-13 Faz 1 (AGENTS.md S0-5): kilo/adet kirpmasi kaldirildi.
gecmis_pencere() tam listeyi dondurur; imza uyumluluk icin korunur.
Kesim YOK — hafizaya yazma akistan once yapilir.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chat import GECMIS_KILO_LIMITI, gecmis_pencere


def mesaj(role, icerik):
    return {"role": role, "content": icerik}


class TestGecmisPencere:
    def test_bos_ve_none_guvenli(self):
        assert gecmis_pencere([]) == []
        assert gecmis_pencere(None) == []

    def test_kisa_sohbetin_hepsi_alinir(self):
        gecmis = [mesaj("user", "selam"), mesaj("assistant", "merhaba")]
        assert len(gecmis_pencere(gecmis)) == 2

    def test_limit_asilinca_eskiler_dusmez(self):
        # Faz 1: kirpma yok — limit parametresi yoksayilir, hepsi doner
        gecmis = ([mesaj("user", "x" * 2500),
                   mesaj("assistant", "y" * 2500),
                   mesaj("user", "son soru"),
                   mesaj("assistant", "son cevap")])
        sonuc = gecmis_pencere(gecmis, limit=4000)
        icerikler = [m["content"] for m in sonuc]
        assert "son soru" in icerikler and "son cevap" in icerikler
        assert len(sonuc) == 4

    def test_en_yeni_mesaj_her_kosulda_garanti(self):
        dev = mesaj("assistant", "z" * (GECMIS_KILO_LIMITI * 2))
        assert gecmis_pencere([dev]) == [dev]

    def test_mesaj_ortasindan_kesilmez(self):
        uzun = "A" * 3000
        gecmis = [mesaj("user", uzun), mesaj("assistant", "kisa")]
        sonuc = gecmis_pencere(gecmis, limit=3100)
        # 'uzun' butun halde ya yasar ya duser; yarim A dizisi donmez
        for m in sonuc:
            assert m["content"] in (uzun, "kisa")

    def test_kronolojik_sira_korunur(self):
        gecmis = [mesaj("user", "1"), mesaj("assistant", "2"),
                  mesaj("user", "3"), mesaj("assistant", "4")]
        sonuc = [m["content"] for m in gecmis_pencere(gecmis)]
        assert sonuc == ["1", "2", "3", "4"]

    def test_adet_siniri_uygulanmaz(self):
        from chat.context import MAX_HISTORY
        gecmis = [mesaj("user", str(i)) for i in range(MAX_HISTORY + 30)]
        assert len(gecmis_pencere(gecmis)) == MAX_HISTORY + 30

    def test_content_none_olursa_cokmez(self):
        gecmis = [{"role": "assistant", "content": None},
                  mesaj("user", "soru")]
        assert [m["content"] for m in gecmis_pencere(gecmis)] == [None, "soru"]

    def test_tool_alanlari_korunur(self):
        from chat.context import temizle_history
        gecmis = [
            {"role": "assistant", "content": "",
             "tool_calls": [{"id": "1", "function": {"name": "web_search"}}],
             "oturum": "abc"},
            {"role": "tool", "content": "sonuc",
             "tool_call_id": "1", "name": "web_search", "oturum": "abc"},
        ]
        sonuc = temizle_history(gecmis)
        assert sonuc[0]["tool_calls"][0]["function"]["name"] == "web_search"
        assert sonuc[1]["tool_call_id"] == "1"
        assert sonuc[1]["name"] == "web_search"
        assert all("oturum" not in m for m in sonuc)
