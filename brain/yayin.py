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


def akit(openai_client, model, messages, tools=None):
    """OpenAI-uyumlu istemciden metin parcasi uretir (generator).

    Yields: str parcalar. Arac cagrisi gorurse AracIstegi firlatir.

    2026-09-13: tools artik akisa da tasinir. Olculdu — groq, glm ve
    nvidia ucu de stream=True ile birlikte tools kabul ediyor. Boylece
    ARACI MODEL SECER: duz sohbette metin akitir, olcum gerekiyorsa
    arac ister (AracIstegi). Kelime listesiyle tetikleme kalkti.
    """
    ekstra = {"tools": tools} if tools else {}
    stream = openai_client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=4096,
        stream=True,
        timeout=20,
        **ekstra
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
