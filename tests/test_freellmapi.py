"""Tek gateway, toplu bilet aktarimi, native arac dongusu ve SSE sozlesmesi."""

import json
import os
import stat
from types import SimpleNamespace

import httpx
import openai
import pytest

from brain import brain as motor
from brain.adapters.freellmapi_adapter import adapter, gateway_adresi
from brain.genel import GenelClient
from scripts.freellmapi_kurulum import guvenli_yaz, yapilandirma


@pytest.fixture(autouse=True)
def temiz(monkeypatch, tmp_path):
    for ad in ("FREELLMAPI_URL", "FREELLMAPI_API_KEY", "FREELLMAPI_MODEL",
               "BASAK_FREELLMAPI_ROUTING_MODEL", "VERCEL", "BASAK_URETIM"):
        monkeypatch.delenv(ad, raising=False)
    monkeypatch.setattr(motor, "_COOLDOWN", {})
    monkeypatch.setattr(motor, "STATE_DIR", str(tmp_path))


def test_anahtar_yokken_yeni_baglanti_yok():
    assert adapter.create({}) is None


def test_eksik_baglanti_hata_verir(monkeypatch):
    monkeypatch.setenv("FREELLMAPI_URL", "https://gateway.test")
    with pytest.raises(ValueError):
        adapter.create({})


@pytest.mark.parametrize("adres", ["http://remote.test", "https://user:password@gateway.test",
                                   "https://gateway.test?token=secret", "https://gateway.test#secret"])
def test_anahtar_tls_disina_ve_url_icine_konmaz(adres):
    with pytest.raises(ValueError):
        gateway_adresi(adres)


def test_vercelde_localhost_http_kabul_edilmez(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    with pytest.raises(ValueError):
        gateway_adresi("http://127.0.0.1:3001")


def test_adres_tekrar_v1_eklemez():
    assert gateway_adresi("https://gateway.test/v1/") == "https://gateway.test/v1"
    assert gateway_adresi("https://gateway.test") == "https://gateway.test/v1"


def test_mevcut_dokuz_bilet_tek_yapilandirmada_env_oncelikli():
    ortam = {"GROQ_API_KEY": "groq-env", "GEMINI_API_KEY": "google-test",
             "ZAI_API_KEY": "zhipu-test", "COHERE_API_KEY": "cohere-test",
             "NVIDIA_API_KEY": "nvidia-test", "KILO_API_KEY": "kilo-test",
             "OPENROUTER_API_KEY": "router-test", "MISTRAL_API_KEY": "mistral-test",
             "CLOUDFLARE_ACCOUNT_ID": "account-test", "CLOUDFLARE_API_TOKEN": "cf-test"}
    veri = yapilandirma({"groq_key": "eski"}, ortam)
    assert len(veri["keys"]) == 9
    biletler = {k["platform"]: k["key"] for k in veri["keys"]}
    assert biletler["groq"] == "groq-env"
    assert biletler["cloudflare"] == "account-test:cf-test"
    assert biletler["google"] == "google-test"
    assert biletler["zhipu"] == "zhipu-test"


def test_eksik_cloudflare_ve_bos_havuz_reddedilir():
    with pytest.raises(ValueError):
        yapilandirma({}, {})
    with pytest.raises(ValueError):
        yapilandirma({}, {"CLOUDFLARE_API_TOKEN": "token"})


def test_yazim_mevcut_dosyayi_ezmez_ve_gizlidir(tmp_path):
    yol = tmp_path / ".env.freellmapi-config.json"
    veri = yapilandirma({"groq_key": "test-key"}, {})
    guvenli_yaz(yol, veri)
    assert json.loads(yol.read_text()) == veri
    if os.name != "nt":
        assert stat.S_IMODE(yol.stat().st_mode) == 0o600
    with pytest.raises(FileExistsError):
        guvenli_yaz(yol, {"keys": []})
    assert json.loads(yol.read_text()) == veri
    with pytest.raises(ValueError):
        guvenli_yaz(tmp_path / "public.json", veri)


def _brain(monkeypatch, gateway, dogrudan=False):
    """Kismi Brain: gateway ve bagimsiz dogrudan Groq yedegi."""
    beyin = motor.Brain.__new__(motor.Brain)
    beyin._freellmapi = gateway
    beyin._freellmapi_isteniyor = True
    beyin._groq = SimpleNamespace(musait=lambda: bool(dogrudan))
    return beyin


def test_ortak_baglanti_bozuksa_dogrudan_saglayiciya_kacmaz(monkeypatch):
    beyin = _brain(monkeypatch, None)
    assert beyin._bulut_zinciri() == []
    with pytest.raises(motor.ZincirHatasi):
        beyin.cevapla([{"role": "user", "content": "test"}])


def test_gateway_dogrudan_saglayicidan_once_gelir(monkeypatch):
    """Gateway yapilandirilmis olsa da dogrudan hat once denenir."""
    giden = []

    def gateway(request):
        giden.append(request)
        return httpx.Response(200, json={"id": "c", "created": 1,
            "model": "auto", "object": "chat.completion", "choices": [{
                "index": 0, "finish_reason": "stop",
                "message": {"role": "assistant", "content": "gateway"}}]})

    sdk = openai.OpenAI(api_key="test-unified", base_url="https://gateway.test/v1",
                        max_retries=0, http_client=httpx.Client(
                            transport=httpx.MockTransport(gateway)))
    client = GenelClient.__new__(GenelClient)
    client.client, client.model = sdk, "auto"
    beyin = _brain(monkeypatch, client, dogrudan=True)
    adlar = [ad for ad, _ in beyin._bulut_zinciri()]
    assert adlar[0] == "freellmapi"
    assert adlar[-1] == "groq"


def test_tek_adres_ortak_bilet_native_arac_sonucu_ve_akis(monkeypatch):
    giden = []
    def gateway(request):
        assert request.url.host == "gateway.test"
        assert request.headers["authorization"] == "Bearer test-unified"
        veri = json.loads(request.content)
        giden.append(veri)
        if veri.get("stream"):
            parca = {"id": "c1", "created": 1, "model": "auto", "choices": [{
                "index": 0, "delta": {"content": "sonuc"}, "finish_reason": "stop"}]}
            return httpx.Response(200, headers={"Content-Type": "text/event-stream"},
                                  text="data: " + json.dumps(parca) + "\n\ndata: [DONE]\n\n")
        return httpx.Response(200, json={"id": "c1", "created": 1, "model": "auto",
            "object": "chat.completion", "choices": [{"index": 0,
            "finish_reason": "tool_calls", "message": {"role": "assistant", "content": None,
            "tool_calls": [{"id": "call1", "type": "function", "function": {
                "name": "deneme", "arguments": "{}"}}]}}]})

    sdk = openai.OpenAI(api_key="test-unified", base_url="https://gateway.test/v1",
                        max_retries=0, http_client=httpx.Client(transport=httpx.MockTransport(gateway)))
    client = GenelClient.__new__(GenelClient)
    client.client, client.model = sdk, "auto:smart"
    beyin = _brain(monkeypatch, client)
    assert [ad for ad, _ in beyin._bulut_zinciri(tools=True, tool_required=True)] == ["freellmapi"]
    tools = [{"type": "function", "function": {"name": "deneme",
              "parameters": {"type": "object", "properties": {}}}}]
    yanit, ad = beyin.cevapla([{"role": "user", "content": "test"}], tools=tools, tool_choice="required")
    assert ad == "freellmapi"
    assert yanit["tool_calls"][0]["function"]["name"] == "deneme"
    mesajlar = [{"role": "user", "content": "test"},
                {"role": "assistant", "content": "", "tool_calls": yanit["tool_calls"]},
                {"role": "tool", "tool_call_id": "call1", "content": "gercek arac sonucu"}]
    assert list(beyin.cevapla_yayin(mesajlar)) == [("freellmapi", "sonuc")]
    assert giden[0]["tool_choice"] == "auto"
    assert giden[0]["model"] == "auto:smart"
    assert giden[1]["messages"][-1]["content"] == "gercek arac sonucu"
    sdk.close()



def test_yeni_gateway_v2_modeli_akilli_secim_varsayilani(monkeypatch):
    from brain.adapters.freellmapi_adapter import adapter as gateway_adapter
    from brain import genel
    captured = []
    monkeypatch.setenv("FREELLMAPI_URL", "https://gateway.test")
    monkeypatch.setenv("FREELLMAPI_API_KEY", "unified-test")
    monkeypatch.setattr(genel, "GenelClient",
                        lambda key, url, model: captured.append((key, url, model)) or
                        SimpleNamespace(model=model))
    assert gateway_adapter.create({}).model == "auto:smart"
    assert captured == [("unified-test", "https://gateway.test/v1", "auto:smart")]
    monkeypatch.setenv("FREELLMAPI_MODEL", "auto:reliable")
    assert gateway_adapter.create({}).model == "auto:reliable"
    monkeypatch.setenv("BASAK_FREELLMAPI_ROUTING_MODEL", "auto:smart")
    assert gateway_adapter.create({}).model == "auto:smart"
    monkeypatch.delenv("BASAK_FREELLMAPI_ROUTING_MODEL")
    assert gateway_adapter.create({}).model == "auto:reliable"


def test_smart_gateway_first_even_when_old_local_scores_prefer_groq(monkeypatch):
    requests = []
    def gateway(req):
        requests.append(json.loads(req.content))
        return httpx.Response(200, json={"id": "c", "created": 1,
            "model": "real-model", "object": "chat.completion", "choices": [{
                "index": 0, "finish_reason": "stop",
                "message": {"role": "assistant", "content": "Model cevabi"}}]})
    sdk = openai.OpenAI(api_key="unified-test", base_url="https://gateway.test/v1",
                        max_retries=0, http_client=httpx.Client(
                            transport=httpx.MockTransport(gateway)))
    client = GenelClient.__new__(GenelClient)
    client.client, client.model = sdk, "auto:smart"
    brain = _brain(monkeypatch, client, dogrudan=True)
    monkeypatch.setattr(motor, "_kota_ongorulu_sira",
                        lambda entries, stats: (list(reversed(entries)), "old score"))
    output, provider = brain.cevapla([{"role": "user", "content": "test"}])
    assert (provider, output["content"]) == ("freellmapi", "Model cevabi")
    assert requests[0]["model"] == "auto:smart"
    sdk.close()


def test_gateway_real_http_failure_falls_back_without_changing_response(monkeypatch):
    def gateway(req):
        return httpx.Response(503, json={"error": {"message": "unavailable",
                                                  "type": "service_unavailable"}})
    sdk = openai.OpenAI(api_key="unified-test", base_url="https://gateway.test/v1",
                        max_retries=0, http_client=httpx.Client(
                            transport=httpx.MockTransport(gateway)))
    client = GenelClient.__new__(GenelClient)
    client.client, client.model = sdk, "auto:smart"
    brain = _brain(monkeypatch, client, dogrudan=True)
    calls = []
    brain._groq = SimpleNamespace(musait=lambda: True,
          cevapla=lambda messages, tools=None, **kwargs:
              calls.append((messages, tools)) or {"content": "Groq cevap"})
    output, provider = brain.cevapla([{"role": "user", "content": "test"}])
    assert (provider, output["content"]) == ("groq", "Groq cevap")
    assert len(calls) == 1
    sdk.close()


def test_gateway_is_first_choice_in_streamed_chat(monkeypatch):
    requests = []
    def gateway(req):
        requests.append(json.loads(req.content))
        chunk = {"id": "c1", "created": 1, "model": "real",
                 "choices": [{"index": 0, "delta": {"content": "Akilli cevap"},
                              "finish_reason": "stop"}]}
        return httpx.Response(200, headers={"Content-Type": "text/event-stream"},
                              text="data: " + json.dumps(chunk) + "\n\ndata: [DONE]\n\n")
    sdk = openai.OpenAI(api_key="unified-test", base_url="https://gateway.test/v1",
                        max_retries=0, http_client=httpx.Client(
                            transport=httpx.MockTransport(gateway)))
    client = GenelClient.__new__(GenelClient)
    client.client, client.model = sdk, "auto:smart"
    brain = _brain(monkeypatch, client, dogrudan=True)
    assert list(brain.cevapla_yayin([{"role": "user", "content": "test"}])) == [
        ("freellmapi", "Akilli cevap")]
    assert requests[0]["model"] == "auto:smart"
    sdk.close()
