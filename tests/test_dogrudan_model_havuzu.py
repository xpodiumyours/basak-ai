from types import SimpleNamespace

import pytest

from brain.model_havuzu import ModelHavuzuSDK, bagla, katalog


class ApiHatasi(Exception):
    def __init__(self, status):
        self.status_code = status


def sdk(create):
    return SimpleNamespace(chat=SimpleNamespace(
        completions=SimpleNamespace(create=create)))


MODELS = [{"id": "large", "tools": True},
          {"id": "chat-only", "tools": False},
          {"id": "backup", "tools": True}]


def test_model_404_yedeklenir_native_arac_imzasi_aynen_kalir():
    calls = []
    response = object()
    messages = [{"role": "assistant", "tool_calls": [],
                 "extra_content": {"google": {"thought_signature": "signed"}}}]

    def create(**kwargs):
        calls.append(kwargs)
        if kwargs["model"] == "large":
            raise ApiHatasi(404)
        return response

    pool = ModelHavuzuSDK(sdk(create), MODELS)
    result = pool.chat.completions.create(
        model="large", messages=messages, tools=[{"type": "function"}],
        tool_choice="required")
    assert result is response
    assert [c["model"] for c in calls] == ["large", "backup"]
    assert all(c["messages"] is messages for c in calls)
    assert all(c["tool_choice"] == "required" for c in calls)
    assert pool.son_model == "backup"


@pytest.mark.parametrize("status", [400, 401, 402, 403, 422])
def test_ortak_hesap_hatasinda_diger_modellerle_kota_yakilmaz(status):
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        raise ApiHatasi(status)

    pool = ModelHavuzuSDK(sdk(create), MODELS)
    with pytest.raises(ApiHatasi):
        pool.chat.completions.create(model="large", messages=[])
    assert len(calls) == 1


def test_429_ayni_saglayicinin_baska_modeline_gecer():
    calls = []

    def create(**kwargs):
        calls.append(kwargs["model"])
        if len(calls) == 1:
            raise ApiHatasi(429)
        return "ok"

    pool = ModelHavuzuSDK(sdk(create), MODELS)
    assert pool.chat.completions.create(model="large", messages=[]) == "ok"
    assert calls == ["large", "chat-only"]


def test_ortak_organizasyon_kotasinda_yeni_model_denenmez():
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        raise ApiHatasi(429)

    pool = ModelHavuzuSDK(sdk(create), MODELS, ortak_kota=True)
    with pytest.raises(ApiHatasi):
        pool.chat.completions.create(model="large", messages=[])
    assert len(calls) == 1


def test_cohere_v2_http_arac_zarfi_korunur():
    from brain.cohere import CohereClient
    seen = []

    def chat(**kwargs):
        seen.append(kwargs)
        return SimpleNamespace(message=SimpleNamespace(content=[], tool_calls=[]))

    client = CohereClient.__new__(CohereClient)
    client.model = "command-a-03-2025"
    client.client = SimpleNamespace(chat=chat)
    tool = {"type": "function", "function": {"name": "hesapla", "parameters": {
        "type": "object", "properties": {}}}}
    client.cevapla([{"role": "user", "content": "test"}], tools=[tool],
                  tool_choice="required")
    assert seen[0]["tools"] == [tool]
    assert seen[0]["tool_choice"] == "REQUIRED"


def test_akisin_ilk_parcasindan_once_yedeklenir_sonrasinda_birlestirilmez():
    calls = []
    closed = []

    def create(**kwargs):
        calls.append(kwargs["model"])

        def stream():
            try:
                if kwargs["model"] == "large":
                    raise ApiHatasi(503)
                yield "first"
                raise ApiHatasi(503)
            finally:
                closed.append(kwargs["model"])
        return stream()

    pool = ModelHavuzuSDK(sdk(create), MODELS)
    stream = pool.chat.completions.create(model="large", messages=[], stream=True)
    assert next(stream) == "first"
    with pytest.raises(ApiHatasi):
        next(stream)
    assert calls == ["large", "chat-only"]
    assert closed == calls


def test_cohere_native_chat_ayni_sozlesmeyle_yedeklenir():
    calls = []

    def native_chat(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            raise ApiHatasi(404)
        return "native"

    pool = ModelHavuzuSDK(SimpleNamespace(chat=native_chat), MODELS)
    assert pool.chat(model="large", messages=[], tool_choice="REQUIRED",
                     tools=[{}]) == "native"
    assert [c["model"] for c in calls] == ["large", "backup"]
    assert calls[-1]["tool_choice"] == "REQUIRED"


def test_ozel_model_ve_openrouter_ayarlari_korunur(monkeypatch):
    monkeypatch.delenv("NVIDIA_MODEL", raising=False)
    client = SimpleNamespace(model="custom", client=sdk(lambda **kw: None))
    assert bagla("nvidia", client, {"nvidia_model": "custom"}) is client
    assert not isinstance(client.client, ModelHavuzuSDK)
    assert bagla("openrouter", client, {}) is client
    assert not isinstance(client.client, ModelHavuzuSDK)


def test_katalog_anahtar_sunucu_ve_bagimli_model_icermez():
    data = katalog()
    assert set(data) == {"groq", "gemini", "nvidia", "cloudflare", "cohere", "glm", "mistral"}
    for models in data.values():
        assert len({m["id"] for m in models}) == len(models)
        assert all(set(m) == {"id", "tools"} for m in models)


def test_rate_limited_model_is_not_retried_on_next_tool_turn(monkeypatch):
    import brain.model_havuzu as module
    clock = [100.0]
    monkeypatch.setattr(module.time, 'monotonic', lambda: clock[0])
    calls = []
    def create(**kwargs):
        calls.append(kwargs['model'])
        if kwargs['model'] == 'large':
            raise ApiHatasi(429)
        return 'ok'
    pool = ModelHavuzuSDK(sdk(create), MODELS)
    options = {'model': 'large', 'messages': [], 'tools': [{}]}
    assert pool.chat.completions.create(**options) == 'ok'
    assert pool.chat.completions.create(**options) == 'ok'
    assert calls == ['large', 'backup', 'backup']
    clock[0] += 61
    assert pool.chat.completions.create(**options) == 'ok'
    assert calls[-2:] == ['large', 'backup']


def test_router_owns_retry_instead_of_nested_sdk_retry(monkeypatch):
    options = []
    class SDK:
        api_key = 'test'
        base_url = 'https://fixture.invalid'
        chat = SimpleNamespace(completions=SimpleNamespace(create=lambda **kw: 'ok'))
        def with_options(self, **kwargs):
            options.append(kwargs)
            return self
    monkeypatch.delenv('GROQ_MODEL', raising=False)
    client = SimpleNamespace(model='large', client=SDK())
    bagla('groq', client, {})
    assert options == [{'max_retries': 0}]


def test_retry_after_is_shared_by_account_but_not_other_accounts(monkeypatch):
    import brain.model_havuzu as module
    monkeypatch.setattr(module.time, 'monotonic', lambda: 100.0)
    def native(key):
        client = sdk(lambda **kwargs: 'ok')
        client.api_key = key
        client.base_url = 'https://quota.invalid'
        return client
    first = ModelHavuzuSDK(native('a'), MODELS, provider='fixture')
    same = ModelHavuzuSDK(native('a'), MODELS, provider='fixture')
    other = ModelHavuzuSDK(native('b'), MODELS, provider='fixture')
    error = ApiHatasi(429)
    error.response = SimpleNamespace(headers={'Retry-After': '120'})
    first._note_failure('large', error)
    first._note_failure('large', ApiHatasi(429))
    assert first._availability['large'][0] == 220.0
    assert same.adaylar({'tools': [{}]}) == ['backup']
    assert other.adaylar({'tools': [{}]}) == ['large', 'backup']
