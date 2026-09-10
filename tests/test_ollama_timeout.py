"""Ollama yerel yol zaman aşımı — qwen2.5:7b soğuk yükleme düzeltmesi.

Canlı bulgu (2026-09-10): qwen2.5:7b işlemcide soğuk yükleme ~18-20 sn
sürüyor; OllamaClient 10 sn okuma zaman aşımı kullandığı için son çare
yerel yol soğuk yüklemede her seferinde 'Read timed out' ile düşüyordu.
Yerel model internet yokken de çalışmalı (kilitli hedef) — okuma zaman
aşımı bu modeli kaldıracak kadar geniş olmalı.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_ollama_okuma_zaman_asimi_qwen_soguk_yuklemeyi_kaldirir(monkeypatch):
    from brain import ollama as ollama_mod
    from brain.ollama import OllamaClient

    yakalanan = {}

    class SahteGet:
        def __init__(self, url, timeout=3):
            yakalanan["get_timeout"] = timeout

        def raise_for_status(self):
            pass

        def json(self):
            return {"models": [{"name": "qwen2.5:7b"}]}

    class SahtePost:
        def __init__(self, url, json=None, timeout=None):
            yakalanan["post_timeout"] = timeout

        def raise_for_status(self):
            pass

        def json(self):
            return {"message": {"content": "ok"}}

    c = OllamaClient.__new__(OllamaClient)
    c.base_url = "http://127.0.0.1:11434"
    monkeypatch.setattr(ollama_mod.requests, "get", SahteGet)
    monkeypatch.setattr(ollama_mod.requests, "post", SahtePost)

    c.cevapla([{"role": "user", "content": "merhaba"}], "qwen2.5:7b")

    read_timeout = yakalanan["post_timeout"][1]
    # qwen2.5:7b işlemci soğuk yükleme (~18-20 sn) zaman aşımına takılmamalı.
    assert read_timeout >= 60, "okuma zaman aşımı %s sn — qwen soğuk yüklemesi için yetersiz" % read_timeout