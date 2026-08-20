"""tests/test_brain.py — Brain modülü testleri."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain.groq import GroqClient, MODELLER
from brain.ollama import OllamaClient


class TestGroqClient:
    def test_bos_anahtar_hata(self):
        try:
            GroqClient("")
            assert False
        except ValueError:
            pass

    def test_bosluk_anahtar_hata(self):
        try:
            GroqClient("   ")
            assert False
        except ValueError:
            pass

    def test_gecerli_anahtar_baslatma(self):
        client = GroqClient("gsk_test_key_12345")
        assert client.api_key == "gsk_test_key_12345"

    def test_model_secimi(self):
        client = GroqClient("gsk_test", model="custom-model")
        assert client.model == "custom-model"


class TestOllamaClient:
    def test_baslatma(self):
        client = OllamaClient()
        assert client.base_url == "http://127.0.0.1:11434"

    def test_custom_url(self):
        client = OllamaClient("http://localhost:9999")
        assert client.base_url == "http://localhost:9999"

    def test_url_sonu_bosluk(self):
        client = OllamaClient("http://localhost:11434/")
        assert client.base_url == "http://localhost:11434"

    def test_musait(self):
        client = OllamaClient("http://localhost:99999")
        assert client.musait() is False

    def test_modeller_bos(self):
        client = OllamaClient("http://localhost:99999")
        assert client.modeller() == []


class TestModeLler:
    def test_groq_modelleri(self):
        assert "varsayilan" in MODELLER
        assert "hizli" in MODELLER
        assert len(MODELLER) >= 3
