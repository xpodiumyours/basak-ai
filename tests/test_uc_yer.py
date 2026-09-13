"""tests/test_uc_yer.py — Uc-yer kurali bekcisi: her alet calisir durumda.

Sozlesme (AGENTS 3-yer kurali): semadaki HER alet calistir() dalina ve
DURUM_METNI etiketine bagli olmali; ucu birden yoksa alet sessizce olu
kalir. Bu test bos argumanla her dali yoklar — yan etki YOK (bos
girdiyle hepsi guvenli hata doner; ag/dosya/surec acilmaz).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import calistir
from tools.definitions import TOOLS


def _bos_args(ozellikler):
    args = {}
    for ad, sema in (ozellikler or {}).items():
        tip = sema.get("type", "string")
        if tip == "integer":
            args[ad] = 0
        elif tip == "array":
            args[ad] = []
        else:
            args[ad] = ""
    return args


class TestUcYer:
    def test_hepsi_bagli_ve_guvenli(self, tmp_path, monkeypatch):
        from chat.tools import DURUM_METNI
        import tools.matris as matris_mod
        monkeypatch.setattr(matris_mod, "MATRIS_KOK", str(tmp_path))
        for alet in TOOLS:
            fn = alet["function"]
            ad = fn["name"]
            assert ad in DURUM_METNI, ad
            r = calistir(ad, _bos_args(
                fn.get("parameters", {}).get("properties", {})))
            assert isinstance(r, dict), ad
            # Dal yoksa dusulen sentinel — artik hicbir alette olmamali
            assert r != {"error": "'%s' calistirilamadi." % ad}, ad

    def test_bilinmeyen_reddedilir(self):
        r = calistir("yok-boyle-alet", {})
        assert "error" in r

    def test_retry_after_okunur(self):
        from brain.brain import _bekleme_suresi
        assert _bekleme_suresi(RuntimeError(
            "Rate limit reached. Please try again in 10.7s.")) == 10.7
        assert _bekleme_suresi(RuntimeError("429 too many")) is None
        assert _bekleme_suresi(RuntimeError("x")) is None
        assert _bekleme_suresi(RuntimeError(
            "retry-after: 300")) == 180.0  # tavan
