"""brain/nvidia.py — NVIDIA NIM bulut entegrasyonu (Nemotron).

OpenAI-uyumlu uc:
https://integrate.api.nvidia.com/v1
Anahtar: env NVIDIA_API_KEY veya ayarlar.json -> nvidia_key (nvapi-... ile baslar).

Ucretsiz deneme ucu ucundadir; kota biterse zincir hatayi atlar.
Model adi acilista /models'ten otomatik secilir.

Arayuz groq.py / gemini.py ile birebir aynidir.
"""

import json
import logging

from openai import OpenAI

logger = logging.getLogger(__name__)

BASE_URL = "https://integrate.api.nvidia.com/v1"

# Tercih sirasi: sohbet-edebilen Nemotron varyantlari
TERCIH_SIRASI = [
    "nvidia/nemotron-3-super",
    "nvidia/llama-3.3-nemotron-super",
    "nvidia/nemotron",
    "meta/llama-3.3-70b-instruct",
]


class NvidiaClient:
    """NVIDIA NIM API istemcisi."""

    def __init__(self, api_key: str, model: str = None):
        if not api_key or not api_key.strip():
            raise ValueError("NVIDIA API anahtarı boş olamaz")
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
            if not self.model:
                self.model = self._model_bul()
        except Exception as e:
            logger.warning("NVIDIA kurulamadı: %s", e)
            self.client = None

    def _model_bul(self) -> str:
        """Hesapta kullanilabilir ilk tercih edilen modeli bulur."""
        try:
            mevcutler = [m.id.lower() for m in self.client.models.list()]
        except Exception as e:
            logger.warning("NVIDIA model listesi alinamadi: %s", e)
            return TERCIH_SIRASI[0]
        for aday in TERCIH_SIRASI:
            for m in mevcutler:
                if m.startswith(aday.lower()):
                    return m
        return mevcutler[0] if mevcutler else TERCIH_SIRASI[0]

    def musait(self) -> bool:
        return self.client is not None

    def cevapla(self, messages: list, tools: list = None) -> dict:
        """NVIDIA NIM'e mesaj gönderir. Dönen şekil groq.py ile aynıdır."""
        if not self.client:
            raise RuntimeError("NVIDIA bağlı değil")

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
