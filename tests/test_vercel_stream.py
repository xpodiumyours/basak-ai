"""Vercel canli akis sozlesmesi — gercek beyne/ag'a cikmadan."""

import asyncio
import json
import threading

from fastapi import Request
from fastapi.responses import StreamingResponse

import app as app_modulu


def _request(veri, accept=""):
    ham = json.dumps(veri).encode("utf-8")
    gonderildi = False

    async def receive():
        nonlocal gonderildi
        if not gonderildi:
            gonderildi = True
            return {"type": "http.request", "body": ham, "more_body": False}
        return {"type": "http.request", "body": b"", "more_body": False}

    headers = [(b"content-type", b"application/json")]
    if accept:
        headers.append((b"accept", accept.encode("ascii")))

    return Request({
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "https",
        "path": "/api/sohbet",
        "raw_path": b"/api/sohbet",
        "query_string": b"",
        "headers": headers,
        "client": ("203.0.113.9", 4242),
        "server": ("testserver", 443),
    }, receive)


def _hazirla(monkeypatch, mesaj_isle):
    import chat.flow as flow
    import chat.kimlik as kimlik
    import chat.prompts as prompts

    monkeypatch.setattr(app_modulu, "_kimlik", lambda _r: "test-user")
    monkeypatch.setattr(app_modulu, "_cekirdek", lambda: (object(), []))
    monkeypatch.setattr(kimlik, "kullanici_kur", lambda _kid: None)
    monkeypatch.setattr(prompts, "kisilik_blogu", lambda *_a, **_k: "sistem")
    monkeypatch.setattr(flow, "mesaj_isle", mesaj_isle)


def _json_satir(parca):
    if isinstance(parca, bytes):
        parca = parca.decode("utf-8")
    return json.loads(parca.strip())


def test_stream_ilk_olayi_worker_bitmeden_verir(monkeypatch):
    devam = threading.Event()

    def sahte(_metin, _beyin, _sistem, js, _tools, **_kwargs):
        js("BasakUI.thinking()")
        js('BasakUI.toolStatus("İnternette aranıyor: deneme")')
        devam.wait(timeout=2)
        js('BasakUI.bitir("tamam", "sahte")')

    _hazirla(monkeypatch, sahte)

    async def senaryo():
        cevap = await app_modulu.sohbet(
            _request({"metin": "ara"}, "application/x-ndjson")
        )
        assert isinstance(cevap, StreamingResponse)
        it = cevap.body_iterator

        ilk = _json_satir(await asyncio.wait_for(anext(it), timeout=1))
        ikinci = _json_satir(await asyncio.wait_for(anext(it), timeout=1))
        assert not devam.is_set()
        assert ilk["tur"] == "thinking"
        assert ikinci["tur"] == "toolStatus"

        devam.set()
        kalan = []
        async for parca in it:
            kalan.append(_json_satir(parca))
        return kalan

    kalan = asyncio.run(senaryo())
    assert any(o.get("tur") == "bitir" and o.get("cevap") == "tamam"
               for o in kalan)


def test_bitir_gorunur_ama_worker_bitmeden_stream_kapanmaz(monkeypatch):
    son_is = threading.Event()
    bitirebilir = threading.Event()

    def sahte(_metin, _beyin, _sistem, js, _tools, **_kwargs):
        js("BasakUI.thinking()")
        js('BasakUI.bitir("cevap", "sahte")')
        son_is.set()
        bitirebilir.wait(timeout=2)

    _hazirla(monkeypatch, sahte)

    async def senaryo():
        cevap = await app_modulu.sohbet(
            _request({"metin": "x"}, "application/x-ndjson")
        )
        it = cevap.body_iterator
        assert _json_satir(await anext(it))["tur"] == "thinking"
        bitis = _json_satir(await anext(it))
        assert bitis["tur"] == "bitir"
        assert son_is.is_set()

        sonraki = asyncio.create_task(anext(it))
        await asyncio.sleep(0.05)
        assert not sonraki.done(), "worker bitmeden stream kapandi"
        bitirebilir.set()
        try:
            await asyncio.wait_for(sonraki, timeout=1)
        except StopAsyncIteration:
            pass

    asyncio.run(senaryo())


def test_stream_worker_hatasi_error_olayi_olur(monkeypatch):
    def patla(*_a, **_k):
        raise RuntimeError("deneme patlamasi")

    _hazirla(monkeypatch, patla)

    async def senaryo():
        cevap = await app_modulu.sohbet(
            _request({"metin": "x"}, "application/x-ndjson")
        )
        return [_json_satir(p) async for p in cevap.body_iterator]

    olaylar = asyncio.run(senaryo())
    assert olaylar[-1]["tur"] == "error"
    assert "deneme patlamasi" in olaylar[-1]["metin"]


def test_accept_yoksa_eski_toplu_json_korunur(monkeypatch):
    def sahte(_metin, _beyin, _sistem, js, _tools, **_kwargs):
        js("BasakUI.thinking()")
        js('BasakUI.bitir("eski yol", "sahte")')

    _hazirla(monkeypatch, sahte)
    cevap = asyncio.run(app_modulu.sohbet(_request({"metin": "x"})))
    assert isinstance(cevap, dict)
    assert cevap["ok"] is True
    assert cevap["cevap"] == "eski yol"
    assert [o["tur"] for o in cevap["olaylar"]] == ["thinking", "bitir"]


def test_vercel_suresi_300():
    veri = json.load(open("vercel.json", encoding="utf-8"))
    assert veri["functions"]["app.py"]["maxDuration"] == 300


def test_web_stream_sozlesmesi_ve_gecmis_ham_cevabi_korur():
    ekran = open("web/app.js", encoding="utf-8").read()
    assert '"accept":"application/x-ndjson"' in ekran
    assert "r.body.getReader()" in ekran
    assert "new TextDecoder()" in ekran
    assert "canliYanitiOku" in ekran
    assert "olayiIsle(o)" in ekran
    assert 'content:sonuc.cevap' in ekran
    assert "Mesaj Başak’a iletiliyor…" in ekran
    assert "Düşünüyorum…" in ekran
