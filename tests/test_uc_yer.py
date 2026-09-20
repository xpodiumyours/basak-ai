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



    def test_52_arac_semasi_tam_ve_tutarlı(self):
        """Her araç JSON function şeması olarak eksiksiz ve tekil olmalı."""
        adlar = []
        for alet in TOOLS:
            assert alet.get("type") == "function", alet
            fn = alet.get("function") or {}
            ad = fn.get("name")
            assert isinstance(ad, str) and ad.strip(), alet
            adlar.append(ad)

            aciklama = fn.get("description")
            assert isinstance(aciklama, str) and aciklama.strip(), ad

            params = fn.get("parameters") or {}
            assert params.get("type") == "object", ad
            props = params.get("properties")
            assert isinstance(props, dict), ad
            required = params.get("required")
            assert isinstance(required, list), ad
            assert set(required).issubset(set(props)), (ad, required, props)

            for alan, sema in props.items():
                assert isinstance(alan, str) and alan, (ad, alan)
                assert isinstance(sema, dict), (ad, alan)
                assert sema.get("type") in (
                    "string", "integer", "number", "boolean",
                    "array", "object"
                ), (ad, alan, sema)

        assert len(adlar) == 52
        assert len(set(adlar)) == 52

    def test_bilinmeyen_reddedilir(self):
        r = calistir("yok-boyle-alet", {})
        assert "error" in r

    def test_retry_after_okunur(self):
        from brain.brain import _bekleme_suresi
        assert _bekleme_suresi(RuntimeError(
            "Rate limit reached. Please try again in 10.7s.")) == 10.7
        assert _bekleme_suresi(RuntimeError("429 too many")) is None
        assert _bekleme_suresi(RuntimeError("x")) is None
        # Saglayicinin gercek Retry-After degeri erken kesilmez; aksi halde
        # kota dolmadan once yeniden istek atilip ucretsiz hak yakilir.
        assert _bekleme_suresi(RuntimeError(
            "retry-after: 300")) == 300.0
