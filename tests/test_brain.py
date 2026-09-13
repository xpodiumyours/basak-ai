"""tests/test_brain.py — Brain modülü testleri."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain.groq import GroqClient, MODELLER


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


class TestModeLler:
    def test_groq_modelleri(self):
        assert "varsayilan" in MODELLER
        assert "hizli" in MODELLER
        assert len(MODELLER) >= 3
