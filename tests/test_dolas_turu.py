"""tests/test_dolas_turu.py — Prompt kalip degil ilke soyler.

2026-09-10 (Casper karari): cumle-esleme kaliplari budandi. Eski
test sabit klasor listesi kilitliyordu; yeni test ILKEYI kilitler:
kesifde soru sorup beklemek yok, bakarak soylemek var. Klasor adi
saymak promptun isi degil.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestDolasTuru:
    def test_kesif_ilkesi_promptta(self):
        from chat.prompts import TOOL_YONLENDIRME
        assert "soru sorup bekleme" in TOOL_YONLENDIRME

    def test_bakarak_soyle_ilkesi(self):
        from chat.prompts import TOOL_YONLENDIRME
        assert "TAHMİN ETME, bakarak söyle" in TOOL_YONLENDIRME

    def test_cumle_esleme_kaliplari_yok(self):
        from chat.prompts import TOOL_YONLENDIRME
        assert "HEMEN ÇAĞIR" not in TOOL_YONLENDIRME
        assert "ZORUNLU KURAL" not in TOOL_YONLENDIRME

    def test_olcu_ilkesi_kisa_ve_durust(self):
        from chat.prompts import OLCU_YONLENDIRME
        assert "Bunu bilmiyorum" in OLCU_YONLENDIRME
        assert "ZORUNLU AKIŞ" not in OLCU_YONLENDIRME
