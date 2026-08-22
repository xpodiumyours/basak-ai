"""brain/mistral.py — Mistral AI bulut entegrasyonu.

Özel modeller: magistral (reasoning), devstral (coding), mistral-small/large.
OpenAI-uyumlu uç: https://api.mistral.ai/v1
~1B token/ay ücretsiz, kredi kartı gerekmez.
"""

import json
import logging

from openai import OpenAI

logger = logging.getLogger(__name__)

BASE_URL = "https://api.mistral.ai/v1"

# Tercih sırası: reasoning/coding özel modelleri önce
TERCIH_SIRASI = [
    "magistral-small",      # Reasoning özel
    "devstral-small",       # Coding özel
    "mistral-small-latest", # Hızlı/genel
    "mistral-medium-latest",
    "mistral-large-latest", # Güçlü
]


class MistralClient:
    """Mistral AI API istemcisi."""

    def __init__(self, api_key: str, model: str = None):
        if not api_key or not api_key.strip():
            raise ValueError("Mistral API anahtarı boş olamaz")
        self.api_key = api_key.strip()
        self.model = model
        self.client = None
        self._kur()

    def _kur(self):
        try:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=BASE_URL,
            )
            if not self.model:
                self.model = self._model_bul()
        except Exception as e:
            logger.warning("Mistral kurulamadı: %s", e)
            self.client = None

    def _model_bul(self) -> str:
        """Hesapta kullanılabilir ilk tercih edilen modeli bulur."""
        try:
            mevcutler = [m.id for m in self.client.models.list()]
        except Exception as e:
            logger.warning("Mistral model listesi alınamadı: %s", e)
            return TERCIH_SIRASI[0]
        for aday in TERCIH_SIRASI:
            for m in mevcutler:
                if m == aday or m.startswith(aday):
                    return m
        return mevcutler[0] if mevcutler else TERCIH_SIRASI[0]

    def musait(self) -> bool:
        return self.client is not None

    def cevapla(self, messages: list, tools: list = None) -> dict:
        """Mistral'a mesaj gönderir. Dönen şekil groq.py ile aynıdır."""
        if not self.client:
            raise RuntimeError("Mistral bağlı değil")

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