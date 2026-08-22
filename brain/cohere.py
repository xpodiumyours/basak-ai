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

MODELLER = {
    "hizli": "command-r",
    "guclu": "command-r-plus",
    "varsayilan": "command-r",
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

    def cevapla(self, messages: list, tools: list = None) -> dict:
        """Cohere'a mesaj gonderir.

        Cohere v2 API: chat metodu, tool parsing.
        """
        if not self.client:
            raise RuntimeError("Cohere bagli degil")

        # Mesajlari Cohere formatina cevir
        cohere_messages = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if not content:
                continue
            if role == "system":
                cohere_messages.append({"role": "system", "content": content})
            elif role == "user":
                cohere_messages.append({"role": "user", "content": content})
            elif role == "assistant":
                cohere_messages.append({"role": "assistant", "content": content})
            elif role == "tool":
                # Tool sonuclarini user mesaji olarak ekle
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
            "max_tokens": 1024,
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
            raise RuntimeError("Cohere API hatasi: %s" % str(e)[:200]) from e

        # Yaniti OpenAI formatinda don
        if not resp.message:
            return {"content": ""}

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
            return {"content": resp.message.content or "", "tool_calls": tool_calls}

        # Icerik
        icerik = ""
        if resp.message.content:
            if isinstance(resp.message.content, list):
                icerik = "".join(
                    c.text for c in resp.message.content if hasattr(c, "text")
                )
            else:
                icerik = str(resp.message.content)

        return {"content": icerik}
