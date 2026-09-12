"""brain/yayin.py — Kelime kelime akan cevap (streaming) yardimcilari.

2026-09-10: cevap tek parca geliyordu ("dondu mu?" sikayeti). Tum
bulut istemciler OpenAI-uyumlu oldugu icin tek jenerik akitici yeter:
`stream=True` ile parca parca alir, arac cagrisi gorurse AracIstegi
firlatir (cagiran tam yola duser — arac + akis karismaz).

Kurallar:
- Arac isteyen akis YARIDA kesilir, parcasi COPtur (UI'ya ulasmadan).
  Bu yuzden akitici parcayi SADECE metin oldugunda verir.
- Kota/429 hatasi istek BASINDA gelirse (parca yok) siradakine gecilir.
  Akis ORTASINDA koparsa SonHata degil, kirik akis doner — cagiran
  kismi metni "kesildi" notuyla bitirir (nadir durum).
"""

import logging

logger = logging.getLogger(__name__)


class AracIstegi(Exception):
    """Model duz metin yerine arac cagirmak istedi — tam yol gerekli."""


class SonHata(Exception):
    """Hicbir saglayici akis acamadi. args[0]: kisa hata ozeti."""

    def __init__(self, ozet):
        super().__init__(ozet)
        self.ozet = ozet


def akit(openai_client, model, messages):
    """OpenAI-uyumlu istemciden metin parcasi uretir (generator).

    Yields: str parcalar. Arac cagrisi gorurse AracIstegi firlatir.
    """
    # Harness v1: read-lite turu toolsuz streaming'e hic sokulmaz; dogrudan
    # tam tool-calling yoluna duser. Chat-lite ise gereksiz system bloklari
    # ayiklanarak daha hafif gonderilir. Model ailesi model id'den cozulur.
    from brain.harness import prepare_stream
    messages, stream_allowed, spec = prepare_stream(messages, model)
    if not stream_allowed:
        raise AracIstegi()
    if spec.active:
        logger.info("Stream harness task=%s family=%s", spec.task, spec.family)

    stream = openai_client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.5,
        max_tokens=2048,
        stream=True,
        timeout=60,
    )
    for chunk in stream:
        try:
            delta = chunk.choices[0].delta
        except (AttributeError, IndexError):
            continue
        if getattr(delta, "tool_calls", None):
            raise AracIstegi()
        parca = getattr(delta, "content", None) or ""
        if parca:
            yield parca


def ollama_akit(base_url, model, messages):
    """Yerel Ollama'dan akan cevap (requests streaming)."""
    import json as _json

    import requests

    from brain.harness import prepare_stream
    messages, stream_allowed, spec = prepare_stream(messages, model, provider="yerel")
    if not stream_allowed:
        raise AracIstegi()
    if spec.active:
        logger.info("Yerel stream harness task=%s family=%s", spec.task, spec.family)

    r = requests.post(
        "%s/api/chat" % base_url.rstrip("/"),
        json={"model": model, "messages": messages, "stream": True},
        stream=True,
        timeout=(3, 60),
    )
    r.raise_for_status()
    for satir in r.iter_lines(decode_unicode=True):
        if not satir:
            continue
        try:
            veri = _json.loads(satir)
        except ValueError:
            continue
        if veri.get("done"):
            break
        msg = veri.get("message", {}) or {}
        if msg.get("tool_calls"):
            raise AracIstegi()
        parca = msg.get("content", "") or ""
        if parca:
            yield parca
