"""tests/test_nvidia_liste.py — FAZ4-3 olu model temizligi kilidi.

2026-09-10 canli kanit: katalog disi veya chat 410 veren modeller
her acilista ve her soruda kota/zaman yiyordu. Liste yalniz
katalogdaki + chat kanitli modellere bakar; oluler donemez.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 10.09.2026 olu kanitli (katalog disi veya chat 410 Gone)
# 23.09.2026 (Faz 3 probe): 404 veren iki model daha eklendi.
OLULER = {
    "meta/muse-glimmer-30b",
    "nvidia/nvidia-nemotron-nano-9b-v2",
    "stepfun-ai/step-3.7-flash",
    "thinkingmachines/inkling",
    "nvidia/nemotron-3-nano-30b-a3b",
    "minimaxai/minimax-m3",
    "nvidia/nemotron-4-340b-instruct",
    "nvidia/nemotron-nano-3-30b-a3b",
}


class TestNvidiaListe:
    def test_oluler_tercih_sirasinda_yok(self):
        from brain.nvidia import TERCIH_SIRASI, GENIS_HAVUZ, KARA_LISTE
        for olu in OLULER:
            assert olu not in TERCIH_SIRASI, "%s listeye donmus" % olu
            assert olu not in GENIS_HAVUZ, "%s genis havuza donmus" % olu
        for k in KARA_LISTE:
            assert k not in TERCIH_SIRASI
            assert k not in GENIS_HAVUZ

    def test_sira_bos_degil_ve_duzgun(self):
        from brain.nvidia import TERCIH_SIRASI, GENIS_HAVUZ
        assert len(TERCIH_SIRASI) >= 3
        for ad in list(TERCIH_SIRASI) + list(GENIS_HAVUZ):
            assert isinstance(ad, str) and "/" in ad, "bozuk model adi: %r" % ad

    def test_tool_destekli_model_basta(self):
        from brain.nvidia import TERCIH_SIRASI, GPTOSS_MODEL
        assert GPTOSS_MODEL in TERCIH_SIRASI
        assert TERCIH_SIRASI[0] == GPTOSS_MODEL

    def test_model_kisayollari_oluye_gitmez(self):
        from brain.nvidia import MODELLER
        for kisa, tam in MODELLER.items():
            if tam is None:
                continue
            assert tam not in OLULER, "%s -> olu model %s" % (kisa, tam)

    def test_genis_havuz_korunanlari_icerir(self):
        from brain.nvidia import GENIS_HAVUZ
        # Faz 2/2b probe: hizli hat + kanitli canli aday havuzda kalmali
        for zorunlu in (
            "nvidia/nemotron-3.5-lightning-30b-a3b",
            "nvidia/nemotron-3-super-120b-a12b",
            "meta/llama-3.2-11b-vision-instruct",
        ):
            assert zorunlu in GENIS_HAVUZ, zorunlu
