"""tests/test_yapi_threading.py — FAZ 1.1 yapi sozlesmesi testleri.

Adaptorlerin yapi parametresi ve Brain.cevapla'nin yapi'yi zincire
tasimasi + 400/invalid_request_error sonrasi self-healing tekrari
(sahte istemcilerle, ag yok).
"""

import os
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain.groq import GroqClient
from brain.ollama import OllamaClient
from brain.gemini import GeminiClient
from brain.glm import GLMClient
from brain.nvidia import NvidiaClient
from brain.kilo import KiloClient
from brain.openrouter import OpenRouterClient
from brain.cloudflare import CloudflareClient
from brain.cohere import CohereClient
from brain.qwen import QwenClient
from brain.kota import KotaYoneticisi

MESAJ = [{"role": "user", "content": "selam"}]
YAPI = {"tip": "nesne", "ozellikler": ["ad"]}


@pytest.fixture(autouse=True)
def temiz_onbellek():
    """Self-healing onbellegi testler arasi sizmasin."""
    from brain import brain as brain_mod
    brain_mod._YAPI_DENEME.clear()
    yield
    brain_mod._YAPI_DENEME.clear()


class SahteHTTP:
    """requests.Response taklidi."""

    def __init__(self, veri):
        self._veri = veri

    def raise_for_status(self):
        pass

    def json(self):
        return self._veri


class YakalayanSDK:
    """OpenAI SDK chat.completions.create taklidi; kwarglari yakalar."""

    def __init__(self):
        self.kayit = []

    @property
    def chat(self):
        return SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        self.kayit.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(
                message=SimpleNamespace(content="tamam", tool_calls=None))],
            usage=None)


class CohereSDK:
    """Cohere native SDK chat taklidi; kwarglari yakalar."""

    def __init__(self):
        self.kayit = []

    def chat(self, **kwargs):
        self.kayit.append(kwargs)
        return SimpleNamespace(
            message=SimpleNamespace(
                tool_calls=None, content=[SimpleNamespace(text="tamam")]),
            meta=None)


def _openai_adaptoru(cls):
    """Ag/network kurmadan OpenAI-uyumlu adaptör hazirlar."""
    istemci = cls.__new__(cls)
    istemci.client = YakalayanSDK()
    istemci.model = "test-model"
    return istemci


class YapiSahteIstemci:
    """Brain.cevapla icin yapi'yi yakalayan agsiz saglayici."""

    def __init__(self, hata=None, sadece_yapi_ile=True):
        self.hata = hata
        self.sadece_yapi_ile = sadece_yapi_ile
        self.cagrildi = 0
        self.yapi_cagrildi = 0
        self.son_yapi = "__gelmedi__"

    def cevapla(self, messages, model=None, tools=None, yapi=None):
        self.cagrildi += 1
        if yapi is not None:
            self.yapi_cagrildi += 1
            self.son_yapi = yapi
        if self.hata and (not self.sadece_yapi_ile or yapi is not None):
            raise self.hata
        return {"content": "tamam"}


class TestAdaptorYapi:
    def test_groq_yapi_ile_response_format_ekler(self):
        g = _openai_adaptoru(GroqClient)
        yanit = g.cevapla(MESAJ, yapi=YAPI)
        assert yanit["content"] == "tamam"
        assert g.client.kayit[0]["response_format"] == {"type": "json_object"}

    def test_groq_yapi_siz_response_format_yok(self):
        g = _openai_adaptoru(GroqClient)
        g.cevapla(MESAJ)
        assert "response_format" not in g.client.kayit[0]
        g.cevapla(MESAJ, tools=[{}])
        assert "response_format" not in g.client.kayit[1]

    def test_ollama_yapi_ile_format_json(self, monkeypatch):
        from brain import ollama as ollama_mod
        yakalanan = {}

        monkeypatch.setattr(
            ollama_mod.requests, "get",
            lambda *a, **k: SahteHTTP({"models": [{"name": "qwen2.5:3b"}]}))

        def sahte_post(url, json=None, timeout=None):
            yakalanan["payload"] = json
            return SahteHTTP({"message": {"content": "ok"}})

        monkeypatch.setattr(ollama_mod.requests, "post", sahte_post)

        c = OllamaClient()
        c.cevapla(MESAJ, "qwen2.5:3b", yapi=YAPI)
        assert yakalanan["payload"]["format"] == "json"

    def test_ollama_yapi_siz_format_yok(self, monkeypatch):
        from brain import ollama as ollama_mod
        yakalanan = {}

        monkeypatch.setattr(
            ollama_mod.requests, "get",
            lambda *a, **k: SahteHTTP({"models": [{"name": "qwen2.5:3b"}]}))

        def sahte_post(url, json=None, timeout=None):
            yakalanan["payload"] = json
            return SahteHTTP({"message": {"content": "ok"}})

        monkeypatch.setattr(ollama_mod.requests, "post", sahte_post)

        c = OllamaClient()
        c.cevapla(MESAJ, "qwen2.5:3b")
        assert "format" not in yakalanan["payload"]

    def test_tum_adaptorlar_yapi_parametresini_kabul_eder(self):
        # Accept-and-ignore adaptorler: yapi ile de yapi'siz de calisir.
        for cls in (GeminiClient, GLMClient, NvidiaClient, KiloClient,
                    OpenRouterClient, CloudflareClient, QwenClient):
            i = _openai_adaptoru(cls)
            i.cevapla(MESAJ, yapi=YAPI)
            i.cevapla(MESAJ)
        cohere_i = CohereClient.__new__(CohereClient)
        cohere_i.client = CohereSDK()
        cohere_i.model = "command-a-03-2025"
        cohere_i.cevapla(MESAJ, yapi=YAPI)
        assert "yapi" not in cohere_i.client.kayit[0]


class TestBrainYapiTasima:
    def _brain(self, monkeypatch, zincir, tmp_path):
        from brain.brain import Brain
        b = Brain.__new__(Brain)  # __init__ anahtar/ag istemez
        b.kota = KotaYoneticisi(dosya=str(tmp_path / "kota.json"))
        b._ollama = YapiSahteIstemci()
        monkeypatch.setattr(b, "_bulut_zinciri", lambda: zincir)
        return b

    def test_brain_yapi_ilk_saglayiciya_tasinir(self, monkeypatch, tmp_path):
        ilk, sira_disi = YapiSahteIstemci(), YapiSahteIstemci()
        b = self._brain(monkeypatch, [("glm", ilk), ("cloudflare", sira_disi)],
                        tmp_path)
        yanit, kaynak = b.cevapla(
            MESAJ, "qwen2.5:3b", tercih=("glm", "cloudflare"), yapi=YAPI)
        assert yanit["content"] == "tamam"
        assert kaynak.startswith("glm")
        assert ilk.son_yapi == YAPI
        assert ilk.cagrildi == 1
        assert sira_disi.cagrildi == 0

    def test_brain_yapi_olmadiginda_kwarg_gondermez(self, monkeypatch, tmp_path):
        # Eski cagrilar hic yapi kwarg'i gormez — geriye uyumluluk.
        ilk = YapiSahteIstemci()
        b = self._brain(monkeypatch, [("glm", ilk)], tmp_path)
        b.cevapla(MESAJ, "qwen2.5:3b", tercih=("glm",))
        assert ilk.son_yapi == "__gelmedi__"

    def test_400_invalid_request_isaretler_ve_yapisiz_tekrar(
            self, monkeypatch, tmp_path):
        hata = RuntimeError(
            "Error code: 400 - {'error': {'message': \"'response_format' "
            "is not supported\", 'type': 'invalid_request_error'}}")
        ilk, sira_disi = YapiSahteIstemci(hata=hata), YapiSahteIstemci()
        b = self._brain(monkeypatch, [("glm", ilk), ("cloudflare", sira_disi)],
                        tmp_path)

        yanit, kaynak = b.cevapla(
            MESAJ, "qwen2.5:3b", tercih=("glm", "cloudflare"), yapi=YAPI)

        from brain import brain as brain_mod
        assert brain_mod._YAPI_DENEME.get("glm") is False
        # Tek saglayicida tek tekrar; zincir ilerlemedi
        assert ilk.yapi_cagrildi == 1
        assert ilk.cagrildi == 2
        assert sira_disi.cagrildi == 0
        assert kaynak.startswith("glm")
        assert yanit["content"] == "tamam"
        # Kota tek sayilir (basarisiz deneme harcama yazmaz)
        assert b.kota.durum["sayac"]["glm"]["istek"] == 1

        # Sonraki cagrida kirtilmis saglayiciya yapi HIC gitmez
        b.cevapla(MESAJ, "qwen2.5:3b", tercih=("glm", "cloudflare"), yapi=YAPI)
        assert ilk.yapi_cagrildi == 1
        assert ilk.cagrildi == 3

    def test_zaman_asimi_zincirden_duser(self, monkeypatch, tmp_path):
        # Format ile ilgisi olmayan hata: yapi'siz tekrar YOK, zincir akar.
        zaman_asimi = RuntimeError("The read operation timed out")
        ilk, sira_disi = (
            YapiSahteIstemci(hata=zaman_asimi, sadece_yapi_ile=False),
            YapiSahteIstemci())
        b = self._brain(monkeypatch, [("glm", ilk), ("cloudflare", sira_disi)],
                        tmp_path)

        yanit, kaynak = b.cevapla(
            MESAJ, "qwen2.5:3b", tercih=("glm", "cloudflare"), yapi=YAPI)

        from brain import brain as brain_mod
        assert "glm" not in brain_mod._YAPI_DENEME
        assert ilk.cagrildi == 1  # ayni saglayicida tekrar yok
        assert kaynak.startswith("cloudflare")
        assert yanit["content"] == "tamam"

    def test_yerel_fallback_yapi_alir(self, monkeypatch, tmp_path):
        # Tum bulutlar duserse yerel Ollama cagrisi da yapi tasir.
        ilk = YapiSahteIstemci(hata=RuntimeError("patladi"))
        b = self._brain(monkeypatch, [("glm", ilk)], tmp_path)
        b._ollama = YapiSahteIstemci()
        b.cevapla(MESAJ, "qwen2.5:3b", tercih=("glm",), yapi=YAPI)
        assert b._ollama.son_yapi == YAPI
