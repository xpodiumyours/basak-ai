"""tests/test_kilo.py — Kilo Gateway istemcisi testleri.

Ag yok: openai istemcisi sahte nesnelerle degistirilir. Asil amac
2026-08-23'te olculen tuzaklarin bir daha geri gelmemesi:
- dusunme metni butceyi bitirince donen BOS cevap kullaniciya gitmemeli
- `reasoning` alani disari sizmamali
- tool_calls groq.py ile ayni bicime cevrilmeli
"""

import os
import sys
import types

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain import registry
from brain.kilo import KiloClient, VARSAYILAN_MODEL


def _mesaj(content=None, tool_calls=None, reasoning=None):
    m = types.SimpleNamespace(content=content, tool_calls=tool_calls)
    if reasoning is not None:
        m.reasoning = reasoning
    return m


def _yanit(message, finish_reason="stop"):
    secim = types.SimpleNamespace(message=message, finish_reason=finish_reason)
    return types.SimpleNamespace(choices=[secim])


class SahteCompletions:
    def __init__(self, yanit):
        self._yanit = yanit
        self.son_kwargs = None

    def create(self, **kwargs):
        self.son_kwargs = kwargs
        return self._yanit


def _istemci(yanit):
    c = KiloClient()
    sahte = SahteCompletions(yanit)
    c.client = types.SimpleNamespace(
        chat=types.SimpleNamespace(completions=sahte))
    return c, sahte


class TestKurulum:
    def test_anahtar_istemez(self):
        # Diger saglayicilarin aksine parametresiz kurulabilmeli.
        c = KiloClient()
        assert c.musait() is True
        assert c.model == VARSAYILAN_MODEL

    def test_baglanti_yoksa_hata(self):
        c = KiloClient()
        c.client = None
        assert c.musait() is False
        with pytest.raises(RuntimeError):
            c.cevapla([{"role": "user", "content": "selam"}])


class TestBosCevap:
    def test_bos_icerik_hata_firlatir(self):
        # Olculen tuzak: max_tokens dar kalinca content bos, finish=length.
        c, _ = _istemci(_yanit(_mesaj(content=""), finish_reason="length"))
        with pytest.raises(RuntimeError) as e:
            c.cevapla([{"role": "user", "content": "selam"}])
        assert "bos cevap" in str(e.value)
        assert "length" in str(e.value)

    def test_sadece_bosluk_da_bos_sayilir(self):
        c, _ = _istemci(_yanit(_mesaj(content="   \n  "), finish_reason="stop"))
        with pytest.raises(RuntimeError):
            c.cevapla([{"role": "user", "content": "selam"}])

    def test_bos_icerik_ama_tool_call_varsa_hata_yok(self):
        # Arac cagirirken content bos olmasi normaldir — hata sayilmamali.
        tc = types.SimpleNamespace(
            id="1", function=types.SimpleNamespace(
                name="hava_durumu", arguments='{"sehir": "Istanbul"}'))
        c, _ = _istemci(_yanit(_mesaj(content="", tool_calls=[tc])))
        sonuc = c.cevapla([{"role": "user", "content": "hava"}], tools=[{}])
        assert sonuc["tool_calls"][0]["function"]["name"] == "hava_durumu"


class TestDusunmeMetni:
    def test_reasoning_zincirde_korunur_kullaniciya_sizmaz(self):
        # P0 (2026-09-15): reasoning zincirde KORUNUR (arac turuna geri
        # verilir); UI yalniz content gosterir. Eski "tamamen at" davranisi
        # muhakeme kaybıydı.
        c, _ = _istemci(_yanit(_mesaj(
            content="Merhaba.", reasoning="Once sunu dusunmeliyim...")))
        sonuc = c.cevapla([{"role": "user", "content": "selam"}])
        assert sonuc["content"] == "Merhaba."
        assert sonuc.get("reasoning") == "Once sunu dusunmeliyim..."

    def test_uygulama_yapay_jeton_tavani_gondermez(self):
        c, sahte = _istemci(_yanit(_mesaj(content="ok")))
        c.cevapla([{"role": "user", "content": "selam"}])
        assert "max_tokens" not in sahte.son_kwargs


class TestToolCevirisi:
    def test_sozluk_argumanlar_json_string_olur(self):
        tc = types.SimpleNamespace(
            id="7", function=types.SimpleNamespace(
                name="not_yaz", arguments={"metin": "deneme"}))
        c, _ = _istemci(_yanit(_mesaj(content=None, tool_calls=[tc])))
        sonuc = c.cevapla([{"role": "user", "content": "not"}], tools=[{}])
        cagri = sonuc["tool_calls"][0]
        assert cagri["type"] == "function"
        assert isinstance(cagri["function"]["arguments"], str)
        assert "deneme" in cagri["function"]["arguments"]

    def test_tools_verilmezse_istege_eklenmez(self):
        c, sahte = _istemci(_yanit(_mesaj(content="ok")))
        c.cevapla([{"role": "user", "content": "selam"}])
        assert "tools" not in sahte.son_kwargs


class TestRegistryKarti:
    def test_kart_var_ve_ucretsiz(self):
        k = registry.kart("kilo")
        assert k["ucretsiz"] is True
        assert k["tools"] is True
        assert k["gunluk_istek"] is None  # sinir saatlik, gunluk degil

    def test_varsayilan_zincirde_yeri(self):
        sira = registry.VARSAYILAN_SIRA
        assert "kilo" in sira
        # Genis ucretsiz havuzlar once, dar gunluk/aylik yedekler sonra.
        assert sira.index("groq") < sira.index("kilo")
        assert sira.index("gemini") < sira.index("kilo")
        assert sira.index("cloudflare") < sira.index("kilo")
        assert sira.index("kilo") < sira.index("openrouter")
        assert sira.index("kilo") < sira.index("cohere")


class TestUcretsizModelFallback:
    def test_dogrudan_tool_modelleri_auto_freeden_once(self):
        from brain.kilo import TERCIH_SIRASI
        assert TERCIH_SIRASI.index("tencent/hy3:free") < (
            TERCIH_SIRASI.index("kilo-auto/free"))
        assert TERCIH_SIRASI.index("poolside/laguna-s-2.1:free") < (
            TERCIH_SIRASI.index("kilo-auto/free"))

    def test_model_gecici_hatasinda_siradaki_free_model_devralir(self):
        from brain.kilo import KiloClient

        cagrilar = []

        class Comp:
            def create(self, **kwargs):
                cagrilar.append(kwargs["model"])
                if len(cagrilar) == 1:
                    raise RuntimeError("model unavailable upstream")
                msg = types.SimpleNamespace(content="tamam", tool_calls=None)
                return types.SimpleNamespace(
                    choices=[types.SimpleNamespace(
                        message=msg, finish_reason="stop")],
                    usage=None,
                )

        istemci = KiloClient.__new__(KiloClient)
        istemci.client = types.SimpleNamespace(
            chat=types.SimpleNamespace(completions=Comp()))
        istemci.model = "stepfun/step-3.7-flash:free"

        yanit = istemci.cevapla(
            [{"role": "user", "content": "selam"}])

        assert yanit["content"] == "tamam"
        assert cagrilar[:2] == [
            "stepfun/step-3.7-flash:free",
            "tencent/hy3:free",
        ]
        # Sonraki arac turunda ayni basarili model once kullanilir.
        assert istemci.model == "tencent/hy3:free"

    def test_ip_geneli_429da_model_degistirip_kota_yakmaz(self):
        from brain.kilo import KiloClient

        cagrilar = []

        class Comp:
            def create(self, **kwargs):
                cagrilar.append(kwargs["model"])
                raise RuntimeError(
                    "Rate limit exceeded for free models. "
                    "200 requests per hour per IP")

        istemci = KiloClient.__new__(KiloClient)
        istemci.client = types.SimpleNamespace(
            chat=types.SimpleNamespace(completions=Comp()))
        istemci.model = "stepfun/step-3.7-flash:free"

        with pytest.raises(RuntimeError):
            istemci.cevapla([{"role": "user", "content": "selam"}])

        assert cagrilar == ["stepfun/step-3.7-flash:free"]

    def test_gecersiz_istekte_diger_modeller_bosuna_denenmez(self):
        from brain.kilo import KiloClient

        cagrilar = []

        class Comp:
            def create(self, **kwargs):
                cagrilar.append(kwargs["model"])
                raise RuntimeError("400 invalid request: bad messages")

        istemci = KiloClient.__new__(KiloClient)
        istemci.client = types.SimpleNamespace(
            chat=types.SimpleNamespace(completions=Comp()))
        istemci.model = "stepfun/step-3.7-flash:free"

        with pytest.raises(RuntimeError):
            istemci.cevapla([{"role": "user", "content": "selam"}])

        assert cagrilar == ["stepfun/step-3.7-flash:free"]
