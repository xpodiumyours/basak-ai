"""Normal ve akan zincirde gercek SDK ile gecici HTTP arizasi provalari."""

import json
from datetime import datetime, timezone
from email.utils import format_datetime
from types import SimpleNamespace

import httpx
import openai
import pytest

from brain import brain as motor
from brain.brain import Brain
from brain.genel import GenelClient
from brain.yayin import SonHata


@pytest.fixture(autouse=True)
def temiz(monkeypatch, tmp_path):
    monkeypatch.setattr(motor, "_COOLDOWN", {})
    monkeypatch.setattr(motor, "STATE_DIR", str(tmp_path))


@pytest.fixture
def zincir(monkeypatch):
    simdi = [1800000000.0]
    monkeypatch.setattr(motor._time_mod, "time", lambda: simdi[0])
    cagrilar = []
    durum = {"kod": 503, "retry": "60"}

    def yanitla(request):
        ad = request.url.host.split(".")[0]
        cagrilar.append(ad)
        if ad == "groq" and durum["kod"]:
            return httpx.Response(durum["kod"], headers={
                "Retry-After": durum["retry"]}, json={"error": {
                    "message": "temporary failure", "type": "server_error"}})
        veri = json.loads(request.content)
        if veri.get("stream"):
            olay = {"id": "c1", "object": "chat.completion.chunk",
                    "created": 1, "model": "test", "choices": [{"index": 0,
                    "delta": {"content": "tamam"}, "finish_reason": "stop"}]}
            return httpx.Response(200, headers={"Content-Type": "text/event-stream"},
                                  text="data: " + json.dumps(olay) + "\n\n"
                                  "data: [DONE]\n\n")
        return httpx.Response(200, json={"id": "c1", "created": 1,
            "object": "chat.completion", "model": "test", "choices": [{
                "index": 0, "message": {"role": "assistant", "content": "tamam"},
                "finish_reason": "stop"}]})

    istemciler = []
    for ad in ("groq", "glm"):
        istemci = GenelClient.__new__(GenelClient)
        istemci.model = "test"
        istemci.client = openai.OpenAI(
            api_key="test", base_url="https://" + ad + ".test/v1",
            max_retries=0, http_client=httpx.Client(transport=httpx.MockTransport(yanitla)))
        istemciler.append((ad, istemci))
    beyin = Brain.__new__(Brain)
    monkeypatch.setattr(beyin, "_bulut_zinciri", lambda **kw: istemciler)
    yield beyin, durum, cagrilar, simdi
    for _, istemci in istemciler:
        istemci.client.close()


def _sor(beyin, akis):
    mesaj = [{"role": "user", "content": "selam"}]
    if akis:
        return list(beyin.cevapla_yayin(mesaj, tercih=["groq", "glm"]))[-1][0]
    return beyin.cevapla(mesaj, tercih=["groq", "glm"])[1]


@pytest.mark.parametrize("akis", [False, True])
@pytest.mark.parametrize("kod", [429, 500, 502, 503, 504])
def test_hata_aninda_yedek_sonra_bekleme_bitince_ilk_saglayici(zincir, akis, kod):
    beyin, durum, cagrilar, simdi = zincir
    durum["kod"] = kod
    assert _sor(beyin, akis) == "glm"
    assert cagrilar == ["groq", "glm"]
    assert motor._cooldown_kaldi("groq") == 60
    durum["kod"] = 0
    assert _sor(beyin, akis) == "glm"
    assert cagrilar == ["groq", "glm", "glm"]
    simdi[0] += 61
    assert _sor(beyin, akis) == "groq"
    assert cagrilar[-1] == "groq"


@pytest.mark.parametrize("akis", [False, True])
def test_http_tarihi_bekleme_suresine_donusur(zincir, akis):
    beyin, durum, _, simdi = zincir
    durum["retry"] = format_datetime(datetime.fromtimestamp(
        simdi[0] + 90, tz=timezone.utc), usegmt=True)
    assert _sor(beyin, akis) == "glm"
    assert motor._cooldown_kaldi("groq") == 90


@pytest.mark.parametrize("akis", [False, True])
@pytest.mark.parametrize("kod", [400, 401, 403, 413])
def test_istemci_hatasi_yedegi_dener_gecici_bekleme_koymaz(zincir, akis, kod):
    beyin, durum, _, _ = zincir
    durum["kod"] = kod
    assert _sor(beyin, akis) == "glm"
    assert motor._cooldown_kaldi("groq") == 0


def test_sarili_sdk_hatasi_resmi_basligini_korur():
    response = httpx.Response(503, request=httpx.Request("POST", "https://test.invalid"),
                              headers={"Retry-After": "75"})
    asil = openai.InternalServerError("unavailable", response=response, body={})
    sarili = RuntimeError("provider failed")
    sarili.__cause__ = asil
    motor._hata_sonrasi_beklet("groq", sarili)
    assert motor._cooldown_kaldi("groq") == pytest.approx(75, abs=1)


def test_sonraki_kisa_bekleme_uzun_beklemeyi_kisaltmaz():
    motor._cooldown_ekle("groq", 120)
    motor._cooldown_ekle("groq", 20)
    assert motor._cooldown_kaldi("groq") == pytest.approx(120, abs=1)


@pytest.mark.parametrize("deger", ["not a date", "NaN", "inf", "2026-10-25 nonsense"])
def test_gecersiz_baslik_sahte_sure_uretmez(deger):
    hata = RuntimeError("provider unavailable")
    hata.response = SimpleNamespace(headers={"Retry-After": deger})
    assert motor._bekleme_suresi(hata) is None


def test_akis_ortasinda_kopunca_metin_baska_saglayiciyla_birlesmez(zincir, monkeypatch):
    beyin, _, cagrilar, _ = zincir
    from brain import yayin

    def kopan(*args, **kwargs):
        yield "yarim cevap"
        raise httpx.ReadError("disconnected")

    monkeypatch.setattr(yayin, "akit", kopan)
    akis = beyin.cevapla_yayin([{"role": "user", "content": "selam"}],
                              tercih=["groq", "glm"])
    assert next(akis) == ("groq", "yarim cevap")
    with pytest.raises(SonHata, match="cevap yolda kesildi"):
        next(akis)
    assert cagrilar == []
    assert motor._cooldown_kaldi("groq") > 0
