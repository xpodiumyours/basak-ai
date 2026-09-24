from chat.flow import mesaj_isle


class _SahteBeyin:
    def __init__(self):
        self.mesajlar = None

    def bulut_musait(self):
        return True

    def ajan_musait(self):
        return True

    def cevapla(self, mesajlar, _model=None, tools=None, tool_choice=None, **_kwargs):
        self.mesajlar = list(mesajlar)
        return {"content": "tamam"}, "sahte"


def test_serverless_gecmis_ayni_cekirdek_akisina_girer():
    beyin = _SahteBeyin()
    olaylar = []
    mesaj_isle(
        "yeni soru",
        beyin,
        "sistem",
        olaylar.append,
        tools=[{"type": "function", "function": {"name": "x"}}],
        misafir=True,
        gecmis_override=[
            {"role": "user", "content": "onceki soru"},
            {"role": "assistant", "content": "onceki cevap"},
        ],
    )
    icerikler = [m.get("content") for m in beyin.mesajlar]
    assert "onceki soru" in icerikler
    assert "onceki cevap" in icerikler
    assert any(o.startswith("BasakUI.bitir(") for o in olaylar)


def test_vercel_koprusu_ikinci_beyin_degildir():
    metin = open("app.py", encoding="utf-8").read()
    assert "from chat.flow import mesaj_isle" in metin
    assert "from openai import" not in metin
    assert "chat.completions" not in metin


def test_vercel_yazma_alani_tmp_olur():
    metin = open("app.py", encoding="utf-8").read()
    assert "BASAK_STATE_DIR" in metin
    assert "tempfile.gettempdir()" in metin

def test_vercel_sohbet_bitir_beklemeden_stream_eder(monkeypatch):
    import asyncio
    import json
    import threading

    import app as vercel_app
    import chat.flow as flow
    import chat.kimlik as kimlik
    import chat.prompts as prompts
    from fastapi import Request
    from fastapi.responses import StreamingResponse

    devam = threading.Event()

    def _sahte_mesaj_isle(_metin, _beyin, _sistem, js_callback,
                         _tools, **_kwargs):
        js_callback("BasakUI.thinking()")
        devam.wait(timeout=2)
        js_callback('BasakUI.parca("ilk")')
        js_callback('BasakUI.bitir("ilk", "sahte")')

    monkeypatch.setattr(vercel_app, "_kimlik", lambda _request: "test-user")
    monkeypatch.setattr(vercel_app, "_cekirdek", lambda: (object(), []))
    monkeypatch.setattr(kimlik, "kullanici_kur", lambda _kid: None)
    monkeypatch.setattr(prompts, "kisilik_blogu", lambda *_a, **_k: "sistem")
    monkeypatch.setattr(flow, "mesaj_isle", _sahte_mesaj_isle)

    ham = json.dumps({"metin": "merhaba"}).encode("utf-8")
    gonderildi = False

    async def receive():
        nonlocal gonderildi
        if not gonderildi:
            gonderildi = True
            return {"type": "http.request", "body": ham, "more_body": False}
        return {"type": "http.request", "body": b"", "more_body": False}

    request = Request({
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "https",
        "path": "/api/sohbet",
        "raw_path": b"/api/sohbet",
        "query_string": b"",
        "headers": [(b"content-type", b"application/json")],
        "client": ("203.0.113.9", 4242),
        "server": ("testserver", 443),
    }, receive)

    async def _senaryo():
        response = await vercel_app.sohbet(request)
        assert isinstance(response, StreamingResponse)
        assert response.media_type == "text/event-stream"

        iterator = response.body_iterator
        ilk = await asyncio.wait_for(anext(iterator), timeout=1)
        ilk_metin = ilk.decode("utf-8").strip()
        assert ilk_metin.startswith("data: ")
        ilk_olay = json.loads(ilk_metin[6:])

        # Sahte model halen bloklu: ilk olay bitis beklenmeden geldi.
        assert not devam.is_set()
        assert ilk_olay["tur"] == "thinking"

        devam.set()
        parcalar = [ilk]
        async for parca in iterator:
            parcalar.append(parca)
        return [
            json.loads(parca.decode("utf-8").strip()[6:])
            for parca in parcalar
            if parca.strip()
        ]

    olaylar = asyncio.run(_senaryo())
    assert [o["tur"] for o in olaylar] == ["thinking", "parca", "bitir"]
    assert olaylar[-1]["cevap"] == "ilk"
    assert olaylar[-1]["kaynak"] == "sahte"


def test_vercel_web_ndjson_stream_okur():
    metin = open("web/app.js", encoding="utf-8").read()
    assert "async function ndjsonAkisiniOku" in metin
    assert "r.body.getReader()" in metin
    assert 'window.basakRuntime === "vercel"' in metin

