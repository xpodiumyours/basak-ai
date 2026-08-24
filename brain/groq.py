"""brain/groq.py — Groq bulut entegrasyonu.

Tool calling destekleyen Groq modelleri:
- openai/gpt-oss-20b → Hızlı, tool calling destekli
- openai/gpt-oss-120b → Güçlü
"""

import json
import logging

from openai import OpenAI

logger = logging.getLogger(__name__)

from brain.kullanim import kullanim_ekle

# Tool calling destekleyen modeller (sadece bunlar kullanılabilir)
MODELLER = {
    "hizli": "openai/gpt-oss-20b",
    "guclu": "openai/gpt-oss-120b",
    "varsayilan": "openai/gpt-oss-20b",  # Hızlı model varsayılan
}


class GroqClient:
    """Groq API istemcisi."""

    # FAZ 1.4d: aracsız turda model yine de tool_call üretirse Groq 400 döner
    # ("Tool choice is none, but model called a tool"). Tek nudge'lı tekrar.
    _NUDGE = {"role": "system",
              "content": "Bu turda arac yok; yalniz duz metinle yanit ver."}

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
                timeout=20.0,
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
        """Groq'a mesaj gönderir.

        Hız için: temperature=0.5, max_tokens=1024.
        model: geçici model override (orn: openai/gpt-oss-120b).
        yapi: sozlesme modu — verildiginde JSON yanit zorlanir
        (response_format={"type": "json_object"}).
        """
        if not self.client:
            raise RuntimeError("Groq bağlı değil")

        kwargs = {
            "model": model or self.model,
            "messages": messages,
            "temperature": 0.5,
            "max_tokens": 1024,
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
            logger.warning(
                "groq aracsız turda tool_call üretti (%s) — "
                "metin-nudge ile tek tekrar", str(e)[:120])
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
        """Groq'un 'tools yokken model tool_call üretti' 400'unu tanir."""
        metin = str(hata)
        return ("tool_use_failed" in metin
                and "Tool choice is none" in metin)
