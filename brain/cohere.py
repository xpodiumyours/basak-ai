"""brain/cohere.py — Cohere bulut entegrasyonu.

Cohere native API kullanılır. Başak modelin çıktı uzunluğunu 1024 ile kesmez;
araç seçimini modelin native tool-calling davranışına bırakır.
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
        if not self.client:
            raise RuntimeError("Cohere bagli degil")

        cohere_messages = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if not content:
                continue
            if role in ("system", "user", "assistant"):
                cohere_messages.append({"role": role, "content": content})
            elif role == "tool":
                cohere_messages.append({
                    "role": "user",
                    "content": "Araç sonucu: %s" % content,
                })

        if not cohere_messages:
            raise RuntimeError("Gecerli mesaj yok")

        kwargs = {
            "model": self.model,
            "messages": cohere_messages,
            "temperature": 0.5,
        }

        if tools:
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
            raise RuntimeError("Cohere API hatasi: %s" % str(e)[:200]) from e

        if not resp.message:
            return {"content": ""}

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
                                  "tool_calls": tool_calls}, resp)

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

        return kullanim_ekle({"content": icerik}, resp)
