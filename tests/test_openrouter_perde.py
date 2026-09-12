"""tests/test_openrouter_perde.py - Sert perde tercihi testleri (2026-09-12).

Her OpenRouter istegi provider tercihleriyle gider:
data_collection=deny (saklayan partiye yonlendirme) +
require_parameters=True (arac desteklemeyene aracli istek gitmez).
"""

from types import SimpleNamespace

from brain.openrouter import OpenRouterClient


class SahteSDK:
    def __init__(self):
        self.kayit = []

    @property
    def chat(self):
        return self

    @property
    def completions(self):
        return self

    def create(self, **kwargs):
        self.kayit.append(kwargs)
        msg = SimpleNamespace(content="tamam", tool_calls=None)
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])


def _istemci():
    c = OpenRouterClient.__new__(OpenRouterClient)
    c.model = "openai/gpt-oss-20b:free"
    c.client = SahteSDK()
    return c


class TestPerdeTercihi:
    def test_aracli_istekte_perde_gider(self):
        c = _istemci()
        tools = [{"type": "function",
                  "function": {"name": "web_search"}}]
        c.cevapla([{"role": "user", "content": "selam"}], tools=tools)
        govde = c.client.kayit[0].get("extra_body", {}).get("provider", {})
        assert govde.get("data_collection") == "deny"
        assert govde.get("require_parameters") is True

    def test_aracsiz_istekte_perde_gider(self):
        c = _istemci()
        c.cevapla([{"role": "user", "content": "selam"}])
        govde = c.client.kayit[0].get("extra_body", {}).get("provider", {})
        assert govde.get("data_collection") == "deny"

    def test_model_sicaklik_tavan_degismez(self):
        c = _istemci()
        c.cevapla([{"role": "user", "content": "selam"}])
        kw = c.client.kayit[0]
        assert kw["model"] == "openai/gpt-oss-20b:free"
        assert kw["temperature"] == 0.5
        assert kw["max_tokens"] == 2048
