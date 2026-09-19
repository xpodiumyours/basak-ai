"""Gercek ajan protokolu icin kotasiz birim testler."""

import types


def _call(ad, args="{}", cid="c1"):
    return {
        "id": cid,
        "type": "function",
        "function": {"name": ad, "arguments": args},
    }


def test_52_gercek_arac_korunur_final_kontrol_araci_ayridir():
    from tools.definitions import TOOLS, TANINMIS_TOOLLAR
    from chat.agent_protocol import ajan_araclari, SON_CEVAP_ADI

    assert len(TOOLS) == 52
    assert len(TANINMIS_TOOLLAR) == 52
    ajan = ajan_araclari(TOOLS)
    assert len(ajan) == 53
    assert ajan[-1]["function"]["name"] == SON_CEVAP_ADI
    assert SON_CEVAP_ADI not in TANINMIS_TOOLLAR


def test_ajan_sozlesmesi_kelime_routeri_degildir():
    from chat.agent_protocol import AJAN_SOZLESMESI

    for ad in ("web_search", "fatura_oku", "github_durum", "list_tasks"):
        assert ad not in AJAN_SOZLESMESI
    assert "Kelime eslestirmesi" in AJAN_SOZLESMESI


def test_son_cevap_gercek_arac_calistirmadan_donguyu_bitirir():
    from chat.tools import arac_dongusu
    from chat.agent_protocol import SON_CEVAP_ADI

    class Beyin:
        def cevapla(self, *args, **kwargs):
            raise AssertionError("finalden sonra modele donulmemeli")

    def calistir(*args, **kwargs):
        raise AssertionError("son_cevap gercek arac degil")

    cevap, kosan = arac_dongusu(
        [_call(SON_CEVAP_ADI, '{"metin":"Tamamlandi."}')],
        [{"role": "user", "content": "merhaba"}],
        Beyin(), None, lambda kod: None, calistir,
        tools=[], tool_choice="required",
    )
    assert cevap == "Tamamlandi."
    assert kosan == 0


def test_required_ajan_duz_metni_final_saymaz():
    from chat.tools import arac_dongusu

    class Beyin:
        def cevapla(self, mesajlar, model, tools=None, tool_choice=None):
            assert tool_choice == "required"
            return {"content": "Araci kullandim, bitti."}, "groq"

    cevap, kosan = arac_dongusu(
        [_call("list_tasks")],
        [{"role": "user", "content": "gorevleri kontrol et"}],
        Beyin(), None, lambda kod: None,
        lambda ad, args: {"result": "1: sut al"},
        tools=[{"type": "function",
                "function": {"name": "list_tasks"}}],
        tool_choice="required",
    )
    assert kosan == 1
    assert cevap == ""


def test_registry_required_yalniz_dogrulanmis_saglayicilar():
    from brain import registry

    assert registry.zorunlu_tool_destegi_var_mi("groq") is True
    assert registry.zorunlu_tool_destegi_var_mi("cohere") is True
    for ad in ("gemini", "openrouter", "glm", "cloudflare",
               "kilo", "nvidia", "qwen"):
        assert registry.zorunlu_tool_destegi_var_mi(ad) is False


def test_groq_required_apiye_tasinir():
    from brain.groq import GroqClient
    yakalanan = {}

    class Comp:
        def create(self, **kwargs):
            yakalanan.update(kwargs)
            msg = types.SimpleNamespace(content="x", tool_calls=None)
            return types.SimpleNamespace(
                choices=[types.SimpleNamespace(message=msg)], usage=None)

    istemci = GroqClient.__new__(GroqClient)
    istemci.client = types.SimpleNamespace(
        chat=types.SimpleNamespace(completions=Comp()))
    istemci.model = "openai/gpt-oss-120b"

    istemci.cevapla(
        [{"role": "user", "content": "s"}],
        tools=[{"type": "function", "function": {"name": "x"}}],
        tool_choice="required",
    )
    assert yakalanan["tool_choice"] == "required"


def test_cohere_required_native_apiye_tasinir():
    from brain.cohere import CohereClient
    yakalanan = {}

    class Client:
        def chat(self, **kwargs):
            yakalanan.update(kwargs)
            msg = types.SimpleNamespace(content="tamam", tool_calls=None)
            return types.SimpleNamespace(message=msg, usage=None)

    istemci = CohereClient.__new__(CohereClient)
    istemci.client = Client()
    istemci.model = "command-a-03-2025"

    istemci.cevapla(
        [{"role": "user", "content": "s"}],
        tools=[{"type": "function",
                "function": {
                    "name": "x", "description": "x",
                    "parameters": {"type": "object", "properties": {}}}}],
        tool_choice="required",
    )
    assert yakalanan["tool_choice"] == "REQUIRED"
