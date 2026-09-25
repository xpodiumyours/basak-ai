"""Geçmişin sessiz kırpılmaması regresyon testleri."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chat import gecmis_pencere


def mesaj(role, icerik):
    return {"role": role, "content": icerik}


class TestGecmisPencere:
    def test_bos_ve_none_guvenli(self):
        assert gecmis_pencere([]) == []
        assert gecmis_pencere(None) == []

    def test_tum_gecmis_aynen_korunur(self):
        gecmis = [
            mesaj("user", "x" * 2500),
            mesaj("assistant", "y" * 2500),
            mesaj("user", "son soru"),
            mesaj("assistant", "son cevap"),
        ]
        assert gecmis_pencere(gecmis) == gecmis

    def test_uzun_tek_mesaj_kesilmez(self):
        dev = mesaj("assistant", "z" * 500000)
        assert gecmis_pencere([dev]) == [dev]

    def test_kronolojik_sira_korunur(self):
        gecmis = [mesaj("user", "1"), mesaj("assistant", "2"),
                  mesaj("user", "3"), mesaj("assistant", "4")]
        assert [m["content"] for m in gecmis_pencere(gecmis)] == [
            "1", "2", "3", "4"
        ]

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
