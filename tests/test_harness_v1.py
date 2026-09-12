"""Harness v1 — yalnız üç kritik kabul davranışı."""
from brain.harness import (
    CHAT_LITE, HarnessProviderProxy, harness_scope,
    resolve_model_family, task_profile_for,
)


def _tool(name):
    return {"type": "function", "function": {"name": name, "parameters": {"type": "object", "properties": {}}}}


class _FakeClient:
    def __init__(self, model):
        self.model = model
        self.last = None

    def cevapla(self, messages, tools=None, **kwargs):
        self.last = {"messages": messages, "tools": tools, "kwargs": kwargs}
        return {"content": "ok"}


def test_chat_lite_arac_gondermez():
    fake = _FakeClient("openai/gpt-oss-20b")
    proxy = HarnessProviderProxy("groq", fake)
    messages = [
        {"role": "system", "content": "KISILIK\nELİNDEKİ ARAÇLAR:\nX\nDÜRÜSTLÜK İLKEN:\nY\nCEVAP BiCiMi:\nZ"},
        {"role": "user", "content": "merhaba nasilsin"},
    ]
    with harness_scope("merhaba nasilsin"):
        proxy.cevapla(messages, tools=[_tool("web_search"), _tool("read_file")])
    assert fake.last["tools"] is None
    assert "ELİNDEKİ ARAÇLAR:" not in fake.last["messages"][0]["content"]


def test_read_lite_yalniz_gerekli_okuma_aracini_gorur():
    profile = task_profile_for("sample.txt dosyayi oku")
    assert profile.name == "read-lite"
    fake = _FakeClient("@cf/meta/llama-3.2-3b-instruct")
    proxy = HarnessProviderProxy("cloudflare", fake)
    with harness_scope("sample.txt dosyayi oku"):
        proxy.cevapla(
            [{"role": "system", "content": "SYS"}, {"role": "user", "content": "sample.txt dosyayi oku"}],
            tools=[_tool("read_file"), _tool("list_files"), _tool("web_search")],
        )
    assert [x["function"]["name"] for x in fake.last["tools"]] == ["read_file"]


def test_model_ailesi_providerdan_degil_gercek_modelden_cozulur():
    assert resolve_model_family("groq", "openai/gpt-oss-20b") == "gpt-oss"
    assert resolve_model_family("nvidia", "openai/gpt-oss-20b") == "gpt-oss"
    assert resolve_model_family("cloudflare", "@cf/meta/llama-3.2-3b-instruct") == "llama-small"
    assert resolve_model_family("glm", "glm-4.5-flash") == "glm-flash"
