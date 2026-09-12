"""tests/test_model_family.py - Model ailesi cozucu testleri (P3).

Provider adi model ailesi degildir: coz() (provider, model_id) ikilisinden
harness kararlarinda kullanilacak aile etiketini uretir. Taninmayan model
ASLA guclu varsayilmaz ("unknown"), hicbir girdi yukseltmez.
"""

import pytest

from brain.model_family import coz


@pytest.fixture(autouse=True)
def _temiz():
    yield


class TestAileTablosu:
    @pytest.mark.parametrize("provider,model,beklenen", [
        ("groq", "openai/gpt-oss-20b", "gpt-oss"),
        ("groq", "openai/gpt-oss-120b", "gpt-oss"),
        ("nvidia", "openai/gpt-oss-20b", "gpt-oss"),
        ("nvidia", "nvidia/nemotron-3-ultra-550b-a55b", "nemotron"),
        ("nvidia", "deepseek-ai/deepseek-v4-flash-0731", "deepseek"),
        ("nvidia", "moonshotai/kimi-k2.6", "kimi"),
        ("cloudflare", "@cf/meta/llama-3.2-3b-instruct", "llama-small"),
        ("cloudflare", "@cf/meta/llama-3.1-8b-instruct", "llama-small"),
        ("cloudflare", "@cf/meta/llama-4-scout-17b-16e-instruct", "llama"),
        ("cloudflare", "@cf/mistralai/mistral-7b-instruct-v0.2", "mistral"),
        ("glm", "glm-4.5-flash", "glm-flash"),
        ("glm", "glm-4.6", "glm"),
        ("gemini", "gemini-2.5-flash", "gemini-flash"),
        ("cohere", "command-a-03-2025", "command-a"),
        ("kilo", "kilo-auto/free", "kilo-auto"),
        ("openrouter", "nvidia/nemotron-3-ultra-550b-a55b:free", "nemotron"),
        ("openrouter", "meta-llama/llama-3.3-70b:free", "llama"),
        ("qwen", "qwen-turbo", "qwen"),
        ("kimi", "kimi-k2", "kimi"),
        ("deepseek", "deepseek-chat", "deepseek"),
        ("yerel", "qwen2.5:7b", "qwen"),
        ("yerel", "llama3.1:8b", "llama-small"),
    ])
    def test_bilinen_esyalar(self, provider, model, beklenen):
        assert coz(provider, model) == beklenen


class TestBilinmeyenGuvenligi:
    @pytest.mark.parametrize("provider,model", [
        ("groq", "yepyeni-model-2099"),
        ("cloudflare", "@cf/bilinmeyen/model-x"),
        ("openrouter", "sahte/model:free"),
        ("genel", "ozel-model"),
        ("yerel", "rastgele-model:13b"),
        ("groq", ""),
        ("groq", None),
        ("", ""),
        (None, None),
    ])
    def test_taninmayan_unknown_doner_yukseltmez(self, provider, model):
        assert coz(provider, model) == "unknown"

    def test_bos_girdi_patlamaz(self):
        assert coz(None, None) == "unknown"
        assert coz("groq", None) == "unknown"
