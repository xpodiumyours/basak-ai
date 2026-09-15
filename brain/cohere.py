"""brain/cohere.py — Cohere bulut entegrasyonu.

Ucretsiz modeller (Trial key ile):
- command-r — Hizli, tool calling destekli
- command-r-plus — Guclu, genis baglam

Cohere native API kullanir (OpenAI-uyumlu degil).
"""

import json
import logging

import cohere

logger = logging.getLogger(__name__)

from brain.kullanim import kullanim_ekle

MODELLER = {
    "hizli": "command-a-03-2025",
    "guclu": "command-a-03-2025",
    "varsayilan": "command-a-03-2025",
}


class CohereClient:
    """Cohere API istemcisi (native SDK)."""

    def __init__(self, api_key: str, model: str = None):
        if not api_key or not api_key.strip():
            raise ValueError("Cohere API anahtari bos olamaz")
        self.api_key = api_key.strip()
        self.model = model or MODELLER["varsayilan"]
        self.client = None
        self._kur()

    def _kur(self):
        try:
            self.client = cohere.ClientV2(api_key=self.api_key)
        except Exception as e:
            logger.warning("Cohere kurulamadi: %s", e)
            self.client = None

    def musait(self) -> bool:
        return self.client is not None

    def cevapla(self, messages: list, tools: list = None, yapi=None) -> dict:
        """Cohere'a mesaj gonderir.

        Cohere V2 native tool-use protokolu (P1): assistant tool-call
        mesaji ve tool_call_id korunur; role=tool -> user cevrilmez.
        Cok turlu arac zinciri boylece native devam eder.
        yapi: sozlesme modu icin; bu saglayici su an yok sayar.
        """
        if not self.client:
            raise RuntimeError("Cohere bagli degil")

        # Mesajlari Cohere V2 formatina cevir (native tool destegi).
        cohere_messages = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if content is None:
                content = ""
            if not isinstance(content, str):
                content = str(content)
            if role == "system":
                if not content.strip():
                    continue
                cohere_messages.append({"role": "system",
                                        "content": content})
            elif role == "user":
                if not content.strip() and "tool_calls" not in m:
                    continue
                cohere_messages.append({"role": "user",
                                        "content": content or ""})
            elif role == "assistant":
                _asistan = {"role": "assistant",
                            "content": content or ""}
                _tc = m.get("tool_calls")
                if _tc:
                    # OpenAI formati -> Cohere V2 ToolCallV2 formati.
                    _ct = []
                    for _c in (_tc or []):
                        try:
                            _f = (_c.get("function") or {})
                            _args = _f.get("arguments", "{}")
                            if not isinstance(_args, str):
                                _args = json.dumps(_args or {})
                            _ct.append({
                                "id": _c.get("id") or "",
                                "type": "function",
                                "function": {
                                    "name": _f.get("name", ""),
                                    "arguments": _args,
                                },
                            })
                        except Exception:
                            continue
                    if _ct:
                        _asistan["tool_calls"] = _ct
                cohere_messages.append(_asistan)
            elif role == "tool":
                # Native tool sonucu: tool_call_id korunur.
                _tid = m.get("tool_call_id") or ""
                if not _tid:
                    continue
                cohere_messages.append({
                    "role": "tool",
                    "tool_call_id": _tid,
                    "content": content or "",
                })
            else:
                if not content.strip():
                    continue
                cohere_messages.append({"role": "user",
                                        "content": content})

        if not cohere_messages:
            raise RuntimeError("Gecerli mesaj yok")

        kwargs = {
            "model": self.model,
            "messages": cohere_messages,
            "max_tokens": 4096,
        }

        if tools:
            # Cohere formatinda tool tanimlarina cevir
            cohere_tools = []
            for t in tools:
                if isinstance(t, dict) and t.get("type") == "function":
                    func = t.get("function", {})
                    cohere_tools.append({
                        "name": func.get("name", ""),
                        "description": func.get("description", ""),
                        "parameters": func.get("parameters", {}),
                    })
            if cohere_tools:
                kwargs["tools"] = cohere_tools

        try:
            resp = self.client.chat(**kwargs)
        except Exception as e:
            # Cohere hata formatini OpenAI uyumlu cevir
            raise RuntimeError("Cohere API hatasi: %s" % str(e)) from e

        # Yaniti OpenAI formatinda don
        if not resp.message:
            return {"content": ""}

        # Reasoning zinciri (P0): varsa korunur.
        try:
            from brain.message_utils import reasoning_ayikla as _r
            muhakeme = _r(resp.message)
        except Exception:
            muhakeme = {}

        # Tool call var mi kontrol et
        if resp.message.tool_calls:
            tool_calls = []
            for tc in resp.message.tool_calls:
                args = "{}"
                if tc.function and tc.function.arguments:
                    if isinstance(tc.function.arguments, str):
                        args = tc.function.arguments
                    else:
                        args = json.dumps(tc.function.arguments)
                tool_calls.append({
                    "id": tc.id or "call_%d" % len(tool_calls),
                    "type": "function",
                    "function": {
                        "name": tc.function.name if tc.function else "",
                        "arguments": args,
                    },
                })
            return kullanim_ekle({"content": resp.message.content or "",
                          "tool_calls": tool_calls, **muhakeme}, resp)

        # Icerik (2026-09-10: blok "text" her zaman string DEGILDIR —
        # sayi/None karisik blok join'i patlatiyordu; message_utils.py
        # ile ayni kural: hepsi zorla stringe cevrilir.)
        icerik = ""
        if resp.message.content:
            if isinstance(resp.message.content, list):
                parcalar = []
                for c in resp.message.content:
                    t = getattr(c, "text", "")
                    parcalar.append(t if isinstance(t, str)
                                    else str(t) if t is not None else "")
                icerik = "".join(parcalar)
            else:
                icerik = str(resp.message.content)

        return kullanim_ekle({"content": icerik, **muhakeme}, resp)
