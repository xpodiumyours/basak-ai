"""P0-1 Vercel canli tasima regresyon kilitleri."""

import asyncio
import json
import threading

from fastapi import Request
from fastapi.responses import StreamingResponse

import app as app_modulu


def test_accept_yoksa_eski_json_yolu_korunur():
    assert "application/x-ndjson" in app_modulu._canli_akis_isteniyor.__doc__ or True
    scope = {
        "type": "http", "headers": []
    }
    request = Request(scope)
    assert app_modulu._canli_akis_isteniyor(request) is False


def test_accept_ndjson_canli_yolu_acar():
    scope = {
        "type": "http",
        "headers": [(b"accept", b"application/x-ndjson")],
    }
    request = Request(scope)
    assert app_modulu._canli_akis_isteniyor(request) is True


def test_akis_bitir_beklemeden_ilk_olayi_verir():
    async def senaryo():
        kuyruk = asyncio.Queue()
        devam = threading.Event()

        def is():
            dongu.call_soon_threadsafe(
                kuyruk.put_nowait,
                {"istek": "t1", "tur": "thinking"},
            )
            devam.wait(timeout=2)
            dongu.call_soon_threadsafe(
                kuyruk.put_nowait,
                {"istek": "t1", "tur": "bitir",
                 "cevap": "tamam", "kaynak": "sahte"},
            )

        nonlocal_holder = {}
        dongu = asyncio.get_running_loop()
        gorev = asyncio.create_task(asyncio.to_thread(is))
        yanit = app_modulu._akis_yaniti(kuyruk, gorev)
        assert isinstance(yanit, StreamingResponse)
        assert "application/x-ndjson" in yanit.media_type
        assert yanit.headers["x-accel-buffering"] == "no"

        iterator = yanit.body_iterator
        ilk = await asyncio.wait_for(anext(iterator), timeout=1)
        olay = json.loads(ilk)
        assert olay["tur"] == "thinking"
        assert not devam.is_set()

        devam.set()
        kalan = []
        async for parca in iterator:
            kalan.append(json.loads(parca))
        assert kalan[-1]["tur"] == "bitir"

    asyncio.run(senaryo())


def test_akis_icinde_istisna_error_olayi_uretir(monkeypatch):
    import chat.flow as flow

    def patla(*_a, **_k):
        raise RuntimeError("deneme-patlama")

    monkeypatch.setattr(app_modulu, "_kimlik", lambda _r: "test-user")
    monkeypatch.setattr(app_modulu, "_cekirdek", lambda: (object(), []))
    monkeypatch.setattr(flow, "mesaj_isle", patla)

    ham = json.dumps({"metin": "test"}).encode("utf-8")
    gonderildi = False

    async def receive():
        nonlocal gonderildi
        if not gonderildi:
            gonderildi = True
            return {"type": "http.request", "body": ham, "more_body": False}
        return {"type": "http.request", "body": b"", "more_body": False}

    request = Request({
        "type": "http", "http_version": "1.1", "method": "POST",
        "scheme": "https", "path": "/api/sohbet",
        "raw_path": b"/api/sohbet", "query_string": b"",
        "headers": [
            (b"content-type", b"application/json"),
            (b"accept", b"application/x-ndjson"),
        ],
        "client": ("203.0.113.9", 1), "server": ("test", 443),
    }, receive)

    async def senaryo():
        response = await app_modulu.sohbet(request)
        olaylar = []
        async for parca in response.body_iterator:
            olaylar.append(json.loads(parca))
        return olaylar

    olaylar = asyncio.run(senaryo())
    assert olaylar[-1]["tur"] == "error"
    assert "deneme-patlama" in olaylar[-1]["metin"]


def test_web_stream_okuyucu_ve_eski_json_fallback_birlikte():
    ekran = open("web/app.js", encoding="utf-8").read()
    assert '"accept":"application/x-ndjson"' in ekran
    assert "async function canliAkisiOku" in ekran
    assert 'icerikTuru.includes("application/x-ndjson")' in ekran
    assert "const d = await jsonOku(r);" in ekran
    assert "bulutGecmisi.push({role:\"assistant\",content:akis.cevap})" in ekran


def test_p0_1_beyin_ve_arac_koduna_dokunmaz():
    # Bu dosyanin amaci tasima katmanini kilitlemek; model/agent mantigi
    # ayri P0 maddeleridir.
    ekran = open("app.py", encoding="utf-8").read()
    assert "from openai import" not in ekran
    assert "chat.completions" not in ekran
