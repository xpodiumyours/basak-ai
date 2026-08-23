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
from brain.kilo import KiloClient, VARSAYILAN_JETON, VARSAYILAN_MODEL


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
    def test_reasoning_disari_sizmaz(self):
        c, _ = _istemci(_yanit(_mesaj(
            content="Merhaba.", reasoning="Once sunu dusunmeliyim...")))
        sonuc = c.cevapla([{"role": "user", "content": "selam"}])
        assert sonuc == {"content": "Merhaba."}
        assert "reasoning" not in sonuc

    def test_jeton_butcesi_genis(self):
        # Butce daraltilirsa bos cevap tuzagi geri gelir.
        assert VARSAYILAN_JETON >= 1500
        c, sahte = _istemci(_yanit(_mesaj(content="ok")))
        c.cevapla([{"role": "user", "content": "selam"}])
        assert sahte.son_kwargs["max_tokens"] >= 1500


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
        assert sira.index("nvidia") < sira.index("kilo") < sira.index("openrouter")
