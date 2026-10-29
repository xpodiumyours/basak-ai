"""Manus-reference acceptance gate: one real model call, real native tools.

The product contract covers fast route selection without nine sequential
providers; it never creates fake answers or chooses tools by keywords.
"""
from types import SimpleNamespace

import pytest

from brain import brain as motor
from brain.brain import Brain, ZincirHatasi
from brain.model_route import one_eligible
from brain.model_havuzu import ModelHavuzuSDK, model_selection
from brain.yayin import SonHata
from chat.output_control import akan_ajan_adimi


@pytest.fixture(autouse=True)
def isolate(monkeypatch, tmp_path):
    monkeypatch.setenv("BASAK_MODEL_ROUTING_MODE", "single")
    monkeypatch.setattr(motor, "STATE_DIR", str(tmp_path))
    monkeypatch.setattr(motor, "_COOLDOWN", {})
    monkeypatch.setattr(motor, "_yerel_kota_doldu", lambda p, s: "")
    monkeypatch.setattr(motor, "_cooldown_kaldi", lambda p: 0)
    monkeypatch.setattr(motor, "_kota_ongorulu_sira",
                        lambda providers, stats: (providers, "stable"))


def make_brain(monkeypatch, providers):
    brain = Brain.__new__(Brain)
    monkeypatch.setattr(brain, "_bulut_zinciri", lambda **kwargs: providers)
    return brain


def test_only_eligible_existing_provider_is_selected():
    assert one_eligible(["groq", "gemini", "glm"], None,
                        lambda p, s: "full" if p == "groq" else "",
                        lambda p: 60 if p == "gemini" else 0) == ["glm"]
    assert one_eligible(["groq"], None, lambda p, s: "full",
                        lambda p: 0) == []


def test_single_route_does_not_call_second_provider_after_failure(monkeypatch):
    calls = []
    def failed(messages, **kwargs):
        calls.append("groq")
        raise RuntimeError("provider unavailable")
    def should_not_run(messages, **kwargs):
        calls.append("gemini")
        return {"content": "other answer"}
    brain = make_brain(monkeypatch, [
        ("groq", SimpleNamespace(cevapla=failed)),
        ("gemini", SimpleNamespace(cevapla=should_not_run)),
    ])
    with pytest.raises(ZincirHatasi):
        brain.cevapla([{"role": "user", "content": "Merhaba"}])
    assert calls == ["groq"]


def test_single_route_keeps_native_tools_and_reports_real_provider(monkeypatch):
    calls, status = [], []
    def call(messages, tools=None, **kwargs):
        calls.append((messages, tools))
        return {"content": "", "tool_calls": [{
            "id": "call-1", "type": "function",
            "function": {"name": "yetenek_ac", "arguments": '{"alanlar":["internet_oku"]}'}
        }]}
    brain = make_brain(monkeypatch, [
        ("groq", SimpleNamespace(cevapla=call)),
        ("glm", SimpleNamespace(cevapla=lambda *a, **k: pytest.fail("second called")))
    ])
    tools = [{"type": "function", "function": {"name": "yetenek_ac"}}]
    answer, source = brain.cevapla(
        [{"role": "user", "content": "Siteyi incele"}],
        tools=tools, durum=status.append)
    assert source == "groq"
    assert answer["tool_calls"][0]["function"]["name"] == "yetenek_ac"
    assert calls[0][1] is tools
    assert status == ["Model baglantisi: groq"]


def test_stream_failure_does_not_start_second_provider(monkeypatch):
    calls = []
    def fail_stream(**kwargs):
        calls.append("groq")
        raise RuntimeError("not responding")
    def second_stream(**kwargs):
        calls.append("glm")
        return iter([])
    def sdk(fn):
        return SimpleNamespace(chat=SimpleNamespace(
            completions=SimpleNamespace(create=fn)))
    brain = make_brain(monkeypatch, [
        ("groq", SimpleNamespace(client=sdk(fail_stream), model="m1")),
        ("glm", SimpleNamespace(client=sdk(second_stream), model="m2"))
    ])
    with pytest.raises(SonHata):
        list(brain.cevapla_yayin([{"role": "user", "content": "Merhaba"}]))
    assert calls == ["groq"]


def test_native_model_pool_is_not_an_invisible_inner_queue():
    candidates = [{"id": "m1", "tools": True}, {"id": "m2", "tools": True}]
    sdk = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
        create=lambda **kw: None)))
    pool = ModelHavuzuSDK(sdk, candidates, provider="groq")
    assert pool.adaylar({"model": "m1"}) == ["m1"]
    with model_selection("groq", "m2"):
        assert pool.adaylar({"model": "m1", "tools": [{"type": "function"}]}) == ["m2"]


def test_legacy_chain_remains_reversible(monkeypatch):
    monkeypatch.setenv("BASAK_MODEL_ROUTING_MODE", "legacy")
    from brain.model_route import single_route
    assert not single_route()
    candidates = [{"id": "m1", "tools": True}, {"id": "m2", "tools": True}]
    sdk = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
        create=lambda **kw: None)))
    assert ModelHavuzuSDK(sdk, candidates, provider="groq").adaylar({}) == [
        "m1", "m2"]


def test_stream_failure_cannot_be_followed_by_hidden_synchronous_retry():
    class FailedStream:
        def cevapla_yayin(self, *args, **kwargs):
            raise SonHata("unavailable")
            yield
    emitted = []
    answer, provider, ok = akan_ajan_adimi(
        FailedStream(), None, [{"role": "user", "content": "Merhaba"}],
        emitted.append, [{"type": "function"}])
    assert answer == {"_route_error": "unavailable"}
    assert provider == "" and not ok


def test_manus_reference_tools_remain_model_discoverable():
    from chat.agent_protocol import YETENEK_ALANLARI
    assert {"ajanlar", "baglantilar", "tarayici", "internet_oku",
            "bulut_calisma", "projeler"} <= set(YETENEK_ALANLARI)
    assert {"alt_ajan", "alt_ajan_sonuclari"} <= set(YETENEK_ALANLARI["ajanlar"])
    assert "baglanti_cagir" in YETENEK_ALANLARI["baglantilar"]
    assert "bulut_tarayici" in YETENEK_ALANLARI["bulut_calisma"]
