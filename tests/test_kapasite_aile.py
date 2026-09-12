"""tests/test_kapasite_aile.py - Aile-bazli kapasite testleri (P4).

Havuzdaki guclu uye turu guclu saydirmaz; karar sirasi:
gate_modu > aile > model_adi (aile cozucu) > kaynak pini >
tekduze-kucuk havuz > varsayilan (guclu — kilitli).
"""

import pytest

from brain.kapasite import mod_kapasite


class TestAileGecerlidir:
    def test_llama_small_aile_kucuk(self):
        kap = mod_kapasite(kaynaklar=["groq", "cloudflare"],
                           model_adi=None, aile="llama-small")
        assert kap.kucuk is True

    def test_guclu_aile_havuzu_gecer(self):
        kap = mod_kapasite(kaynaklar=["kilo"], aile="gpt-oss")
        assert kap.guclu is True

    def test_unknown_aile_varsayilana_duser(self):
        kap = mod_kapasite(kaynaklar=["kilo"], aile="unknown")
        # kilo tekduze-kucuk havuz → kucuk (aile karar vermedi)
        assert kap.kucuk is True
        kap2 = mod_kapasite(kaynaklar=["groq"], aile="unknown")
        assert kap2.guclu is True


class TestModelAdiAileCozucu:
    def test_17b_tuzagi_kapandi(self):
        # Eski alt-dizgi kuralı "7b" yuzunden kucuk sayiyordu.
        kap = mod_kapasite(
            model_adi="@cf/meta/llama-4-scout-17b-16e-instruct")
        assert kap.guclu is True

    def test_gpt_oss_guclu(self):
        assert mod_kapasite(model_adi="openai/gpt-oss-20b").guclu is True

    def test_glm_flash_guclu(self):
        assert mod_kapasite(model_adi="glm-4.5-flash").guclu is True

    def test_bilinmeyen_model_varsayilan_guclu(self):
        assert mod_kapasite(model_adi="yepyeni-model-2099").guclu is True


class TestHavuzKurali:
    def test_cloudflare_havuzu_artik_kucuk(self):
        # Varsayilan 3B sinifi agir sekillenmez (P4 duzeltmesi).
        assert mod_kapasite(kaynaklar=["cloudflare"]).kucuk is True

    def test_karisik_havuz_varsayilan_guclu(self):
        assert mod_kapasite(kaynaklar=["glm", "cloudflare"]).guclu is True

    def test_openrouter_havuzu_varsayilan_guclu(self):
        # Dinamik :free — varsayilan korunur.
        assert mod_kapasite(kaynaklar=["openrouter"]).guclu is True

    def test_tekduze_kucuk_havuz(self):
        assert mod_kapasite(kaynaklar=["ollama", "kilo"]).kucuk is True
