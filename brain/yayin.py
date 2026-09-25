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
    """Model duz metin yerine arac cagirmak istedi.

    P0 (cift dusunme kaldirma): akis sirasinda modelin sectigi arac ve
    argumanlar burada tasinir; cagiran ayni soruyu ikinci kez modele
    dusundurmeden dogrudan calistirir.
    """

    def __init__(self, tool_calls=None, muhakeme=None, kaynak=""):
        super().__init__("arac-istegi")
        self.tool_calls = tool_calls or []
        self.muhakeme = muhakeme or {}
        self.kaynak = str(kaynak or "")


class SonHata(Exception):
    """Hicbir saglayici akis acamadi. args[0]: kisa hata ozeti."""

    def __init__(self, ozet):
        super().__init__(ozet)
        self.ozet = ozet


class CikisKesildi(Exception):
    """Provider stream'i teknik cikti/context sinirinda bitti."""

    def __init__(self, neden, kaynak=""):
        super().__init__(str(neden or "limit"))
        self.neden = str(neden or "limit")
        self.kaynak = str(kaynak or "")


def akit(openai_client, model, messages, tools=None):
    """OpenAI-uyumlu istemciden metin parcasi uretir (generator).

    Yields: str parcalar. Arac cagrisi gorurse AracIstegi firlatir.

    2026-09-13: tools artik akisa da tasinir. Olculdu — groq, glm ve
    nvidia ucu de stream=True ile birlikte tools kabul ediyor. Boylece
    ARACI MODEL SECER: duz sohbette metin akitir, olcum gerekiyorsa
    arac ister (AracIstegi). Kelime listesiyle tetikleme kalkti.

    P0 (2026-09-15): streaming tool_call parcalari biriktirilir ve
    AracIstegi ile birlikte tasinir. Cagiran ayni soruyu ikinci kez
    modele sormaz; ilk modelin sectigi arac dogrudan calisir.
    """
    ekstra = {"tools": tools} if tools else {}
    stream = openai_client.chat.completions.create(
        model=model,
        messages=messages,
stream=True,
        timeout=20,
        **ekstra
    )
    # Streaming tool_call parcalari (OpenAI delta formati: index bazli).
    _arac_parcalar = {}  # index -> {"id","name","arguments"}
    _muhakeme_parcalar = []
    _bitis_nedeni = ""
    for chunk in stream:
        try:
            secim = chunk.choices[0]
            _fr = getattr(secim, "finish_reason", None)
            if _fr:
                _bitis_nedeni = str(_fr)
            delta = secim.delta
        except (AttributeError, IndexError):
            continue
        # Reasoning delta varsa biriktir (GLM/DeepSeek tarzi).
        for _alan in ("reasoning_content", "reasoning",
                      "reasoning_details", "reasoning_text",
                      "thinking"):
            _rd = getattr(delta, _alan, None)
            if _rd:
                _muhakeme_parcalar.append((_alan, str(_rd)))
        _delta_tools = getattr(delta, "tool_calls", None)
        if _delta_tools:
            for _tc in _delta_tools:
                try:
                    _idx = getattr(_tc, "index", 0) or 0
                except Exception:
                    _idx = 0
                _g = _arac_parcalar.setdefault(
                    _idx, {"id": "", "name": "", "arguments": ""})
                _tc_id = getattr(_tc, "id", None)
                if _tc_id:
                    _g["id"] = _tc_id
                _fn = getattr(_tc, "function", None)
                if _fn is not None:
                    _n = getattr(_fn, "name", None)
                    if _n:
                        _g["name"] = (_g["name"] or "") + str(_n)
                    _a = getattr(_fn, "arguments", None)
                    if _a:
                        _g["arguments"] = (_g["arguments"] or "") + str(_a)
                elif isinstance(_tc, dict):
                    _f2 = (_tc.get("function") or {})
                    if _tc.get("id"):
                        _g["id"] = _tc.get("id")
                    if _f2.get("name"):
                        _g["name"] += str(_f2.get("name"))
                    if _f2.get("arguments"):
                        _g["arguments"] += str(_f2.get("arguments"))
            continue
        parca = getattr(delta, "content", None) or ""
        if parca:
            yield parca
    if _arac_parcalar:
        tool_calls = []
        for _idx in sorted(_arac_parcalar):
            _g = _arac_parcalar[_idx]
            if not _g["name"]:
                continue
            tool_calls.append({
                "id": _g["id"] or ("call_%d" % _idx),
                "type": "function",
                "function": {
                    "name": _g["name"],
                    "arguments": _g["arguments"] or "{}",
                },
            })
        if tool_calls:
            muhakeme = {}
            if _muhakeme_parcalar:
                _birlesik = {}
                for _alan, _txt in _muhakeme_parcalar:
                    _birlesik[_alan] = (_birlesik.get(_alan, "")
                                        + _txt)
                muhakeme = _birlesik
            raise AracIstegi(tool_calls=tool_calls, muhakeme=muhakeme)

    if _bitis_nedeni.lower() in (
            "length", "max_tokens", "model_context_window_exceeded"):
        raise CikisKesildi(_bitis_nedeni)
