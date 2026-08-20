"""brain/groq.py — Groq bulut entegrasyonu.

Tool calling destekleyen Groq modelleri:
- openai/gpt-oss-20b → Hızlı, tool calling destekli
- openai/gpt-oss-120b → Güçlü
- qwen/qwen3.6-27b → Orta hız
"""

import json
import logging

from openai import OpenAI

logger = logging.getLogger(__name__)

# Tool calling destekleyen modeller (sadece bunlar kullanılabilir)
MODELLER = {
    "hizli": "openai/gpt-oss-20b",
    "guclu": "openai/gpt-oss-120b",
    "orta": "qwen/qwen3.6-27b",
    "varsayilan": "openai/gpt-oss-20b",  # Hızlı model varsayılan
}


class GroqClient:
    """Groq API istemcisi."""

    def __init__(self, api_key: str, model: str = None):
        if not api_key or not api_key.strip():
            raise ValueError("Groq API anahtarı boş olamaz")
        self.api_key = api_key.strip()
        self.model = model or MODELLER["varsayilan"]
        self.client = None
        self._kur()

    def _kur(self):
        try:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url="https://api.groq.com/openai/v1",
            )
        except Exception as e:
            logger.warning("Groq kurulamadı: %s", e)
            self.client = None

    def musait(self) -> bool:
        return self.client is not None

    def cevapla(self, messages: list, tools: list = None) -> dict:
        """Groq'a mesaj gönderir.

        Hız için: temperature=0.5, max_tokens=1024.
        """
        if not self.client:
            raise RuntimeError("Groq bağlı değil")

        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.5,
            "max_tokens": 1024,
        }
        if tools:
            kwargs["tools"] = tools

        resp = self.client.chat.completions.create(**kwargs)
        msg = resp.choices[0].message

        if msg.tool_calls:
            tool_calls = []
            for tc in msg.tool_calls:
                args = tc.function.arguments
                if not isinstance(args, str):
                    args = json.dumps(args) if args else "{}"
                tool_calls.append({
                    "id": tc.id,
                    "function": {
                        "name": tc.function.name,
                        "arguments": args,
                    }
                })
            return {"content": msg.content or "", "tool_calls": tool_calls}

        return {"content": msg.content or ""}
