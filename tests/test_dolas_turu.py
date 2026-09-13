"""tests/test_dolas_turu.py — modelin doğal araç seçimi sözleşmesi."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestDogalAracSecimi:
    def test_arac_dayatma_promptu_yok(self):
        from chat.prompts import TOOL_YONLENDIRME
        assert TOOL_YONLENDIRME == ""

    def test_bicim_dayatma_promptu_yok(self):
        from chat.prompts import BIKIMLONDIRME_YONLENDIRME
        assert BIKIMLONDIRME_YONLENDIRME == ""

    def test_durustluk_ilkesi_korunur(self):
        from chat.prompts import OLCU_YONLENDIRME
        assert "uydurma" in OLCU_YONLENDIRME.lower()
        assert "doğrula" in OLCU_YONLENDIRME.lower()

    def test_arac_aciklamasi_gorevi_yasaklamaz(self):
        from tools import TOOLS
        web = next(
            t["function"] for t in TOOLS
            if t["function"]["name"] == "web_search")
        assert "görev için kullanma" not in web["description"].lower()
        assert "gorev icin kullanma" not in web["description"].lower()
