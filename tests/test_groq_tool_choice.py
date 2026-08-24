"""tests/test_groq_tool_choice.py — FAZ 1.4d groq aracsız-tur 400 düzeltmesi.

Canlı bulunan hata: zincirin son turunda tools sunulmazken model yine de
tool_call üretince Groq 400 döner ("Tool choice is none, but model called
a tool") — kota yanar, zincir zayıf sağlayıcıya düşer. Düzeltme: tek
nudge'lı tekrar (sahte istemcilerle, ağ yok).
"""

import os
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain.groq import GroqClient

MESAJLAR = [{"role": "user", "content": "VixRex'te durum ne?"}]
BUG = ('Error code: 400 - {"error": {"message": '
       '"Tool choice is none, but model called a tool", '
       '"type": "invalid_request_error", "code": "tool_use_failed"}}')


def _tamamlama(icerik="ok"):
    return SimpleNamespace(
        choices=[SimpleNamespace(
            message=SimpleNamespace(content=icerik, tool_calls=None))],
        usage=None)


class SenaryoluSDK:
    """Sırayla davranan sahte SDK: her çağrıda bir sonraki adım oynar."""

    def __init__(self, adimlar):
        self.adimlar = list(adimlar)
        self.kayit = []

    @property
    def chat(self):
        return SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        self.kayit.append(kwargs)
        adim = self.adimlar.pop(0)
        if isinstance(adim, Exception):
            raise adim
        return _tamamlama(adim)


def _adaptör(adimlar):
    g = GroqClient.__new__(GroqClient)
    g.client = SenaryoluSDK(adimlar)
    g.model = "openai/gpt-oss-20b"
    return g


class TestGroqToolChoice:
    def test_bug_tek_nudge_ile_tekrar_icerir(self):
        g = _adaptör([Exception(BUG), "ok"])
        yanit = g.cevapla(MESAJLAR)
        assert yanit["content"] == "ok"
        assert len(g.client.kayit) == 2
        ikinci = g.client.kayit[1]["messages"]
        assert ikinci[:-1] == MESAJLAR
        assert ikinci[-1]["role"] == "system"
        assert "arac" in ikinci[-1]["content"]

    def test_orijinal_mesajlar_bozulmaz(self):
        g = _adaptör([Exception(BUG), "ok"])
        g.cevapla(MESAJLAR)
        assert MESAJLAR == [{"role": "user", "content": "VixRex'te durum ne?"}]

    def test_ikinci_hata_yukselir(self):
        g = _adaptör([Exception(BUG), Exception("yine 400")])
        with pytest.raises(Exception, match="yine 400"):
            g.cevapla(MESAJLAR)
        assert len(g.client.kayit) == 2

    def test_ilgisiz_400_direkt_yukselir(self):
        diger = ('Error code: 400 - {"code": "invalid_api_key"}')
        g = _adaptör([Exception(diger)])
        with pytest.raises(Exception, match="invalid_api_key"):
            g.cevapla(MESAJLAR)
        assert len(g.client.kayit) == 1

    def test_timeout_direkt_yukselir(self):
        g = _adaptör([Exception("Request timed out.")])
        with pytest.raises(Exception, match="timed out"):
            g.cevapla(MESAJLAR)
        assert len(g.client.kayit) == 1

    def test_mutlu_yol_nudge_eklemez(self):
        g = _adaptör(["ok"])
        yanit = g.cevapla(MESAJLAR)
        assert yanit["content"] == "ok"
        assert len(g.client.kayit) == 1
        assert g.client.kayit[0]["messages"] == MESAJLAR

    def test_yapi_retryde_korunur(self):
        g = _adaptör([Exception(BUG), "ok"])
        yanit = g.cevapla(MESAJLAR, yapi={"type": "json_object"})
        assert yanit["content"] == "ok"
        assert g.client.kayit[0]["response_format"] == {"type": "json_object"}
        assert g.client.kayit[1]["response_format"] == {"type": "json_object"}
