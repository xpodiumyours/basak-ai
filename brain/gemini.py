"""brain/gemini.py — Google Gemini bulut entegrasyonu.

Google'ın OpenAI-uyumlu ucu ortak Başak arayüzü için kullanılır. Başak
modelin çıktı uzunluğunu 1024 ile kesmez ve araç seçimini modele bırakır.
"""

import json
import logging

from openai import OpenAI

logger = logging.getLogger(__name__)

from brain.kullanim import kullanim_ekle

BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
MODELLER = {
    "hizli": "gemini-2.5-flash",
    "varsayilan": "gemini-2.5-flash",
}


class GeminiClient:
    def __init__(self, api_key: str, model: str = None):
        if not api_key or not api_key.strip():
            raise ValueError("Gemini API anahtarı boş olamaz")
        self.api_key = api_key.strip()
        self.model = model or MODELLER["varsayilan"]
        self.client = None
        self._kur()

    def _kur(self):
        try:
            self.client = OpenAI(
                api_key=self.api_key,
                timeout=60.0,
                max_retries=0,
                base_url=BASE_URL,
            )
        except Exception as e:
            logger.warning("Gemini kurulamadı: %s", e)
            self.client = None

    def musait(self) -> bool:
        return self.client is not None

    def cevapla(self, messages: list, tools: list = None, yapi=None) -> dict:
        if not self.client:
            raise RuntimeError("Gemini bağlı değil")

        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.5,
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
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": args,
                    }
                })
            return kullanim_ekle({"content": msg.content or "",
                                  "tool_calls": tool_calls}, resp)

        return kullanim_ekle({"content": msg.content or ""}, resp)
