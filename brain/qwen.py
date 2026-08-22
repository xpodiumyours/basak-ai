"""brain/qwen.py — Qwen bulut entegrasyonu (QwenCloud/DashScope).

Besinci bulut saglayici. OpenAI-uyumlu uc (uluslararasi):
https://dashscope-intl.aliyuncs.com/compatible-mode/v1
Anahtar: env DASHSCOPE_API_KEY veya ayarlar.json -> dashscope_key.

Model adi platform tarafinda degisebildigi icin acilista /models'ten
otomatik secilir (tercih sirasiyla).

Arayuz groq.py / gemini.py ile birebir aynidir.
"""

import json
import logging

from openai import OpenAI

logger = logging.getLogger(__name__)

BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"

# Tercih sirasi: hizli/ucuz → guclu. Ilk bulunan kullanilir.
TERCIH_SIRASI = [
    "qwen3.7-plus",
    "qwen-plus",
    "qwen-turbo",
    "qwen-flash",
    "qwen3-max",
]


class QwenClient:
    """QwenCloud (DashScope) API istemcisi."""

    def __init__(self, api_key: str, model: str = None):
        if not api_key or not api_key.strip():
            raise ValueError("Qwen API anahtarı boş olamaz")
        self.api_key = api_key.strip()
        self.model = model
        self.client = None
        self._kur()

    def _kur(self):
        try:
            self.client = OpenAI(
                api_key=self.api_key,
                timeout=20.0,
                max_retries=0,
                base_url=BASE_URL,
            )
            self.model = self._model_bul()
        except Exception as e:
            logger.warning("Qwen kurulamadı: %s", e)
            self.client = None

    def _model_bul(self) -> str:
        """Hesapta acik olan ilk tercih edilen modeli bulur."""
        try:
            mevcutler = [m.id for m in self.client.models.list()]
        except Exception as e:
            logger.warning("Qwen model listesi alinamadi: %s", e)
            return TERCIH_SIRASI[0]
        for aday in TERCIH_SIRASI:
            for m in mevcutler:
                if m == aday or m.startswith(aday):
                    return m
        # Hicbiri yoksa listedeki ilki dondurulur (cagri zaten zincire dusmez)
        return mevcutler[0] if mevcutler else TERCIH_SIRASI[0]

    def musait(self) -> bool:
        return self.client is not None

    def cevapla(self, messages: list, tools: list = None) -> dict:
        """Qwen'e mesaj gönderir. Dönen şekil groq.py ile aynıdır."""
        if not self.client:
            raise RuntimeError("Qwen bağlı değil")

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
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": args,
                    }
                })
            return {"content": msg.content or "", "tool_calls": tool_calls}

        return {"content": msg.content or ""}
