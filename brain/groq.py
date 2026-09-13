"""brain/groq.py — Groq bulut entegrasyonu.

Tool calling destekleyen ücretsiz GPT-OSS modelleri kullanılır. Başak modelin
çıktı uzunluğunu 1024 ile kesmez; araç seçimi varsayılan auto davranışında
modele bırakılır.
"""

import json
import logging

from openai import OpenAI

logger = logging.getLogger(__name__)

from brain.kullanim import kullanim_ekle

MODELLER = {
    "hizli": "openai/gpt-oss-20b",
    "guclu": "openai/gpt-oss-120b",
    "varsayilan": "openai/gpt-oss-20b",
}


class GroqClient:
    _NUDGE = {"role": "system",
              "content": "Bu turda araç yok; yalnız düz metinle yanıt ver."}

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
                timeout=60.0,
                max_retries=0,
                base_url="https://api.groq.com/openai/v1",
            )
        except Exception as e:
            logger.warning("Groq kurulamadı: %s", e)
            self.client = None

    def musait(self) -> bool:
        return self.client is not None

    def cevapla(self, messages: list, tools: list = None,
                model: str = None, yapi=None) -> dict:
        if not self.client:
            raise RuntimeError("Groq bağlı değil")

        kwargs = {
            "model": model or self.model,
            "messages": messages,
            "temperature": 0.5,
        }
        if tools:
            kwargs["tools"] = tools
        if yapi is not None:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            resp = self.client.chat.completions.create(**kwargs)
        except Exception as e:
            if not self._tool_choice_hatasi_mi(e):
                raise
            kwargs = dict(kwargs)
            kwargs["messages"] = list(messages) + [self._NUDGE]
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

    @staticmethod
    def _tool_choice_hatasi_mi(hata) -> bool:
        metin = str(hata)
        return ("tool_use_failed" in metin
                and "Tool choice is none" in metin)
