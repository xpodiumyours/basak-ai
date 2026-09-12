"""brain/genel.py — Genel OpenAI-uyumlu saglayici (ucretli anahtar yuvasi).

2026-09-10 (Casper karari): yarin oburgun ucretli anahtar baglaninca
HICBIR SEY degismeyecek. Bu istemci HERHANGI bir OpenAI-uyumlu adrese
(OpenAI, DeepSeek, Together, Fireworks, xAI, yerel sunucu...) ayni
dille konusur: ayni cevap bicimi, ayni arac destegi, ayni akis.

Ayarlar (ayarlar.json veya ortam):
  genel_api_url   Orn: https://api.openai.com/v1
  genel_api_key   Bilet
  genel_model     Orn: gpt-4o-mini
Ortam karsiliklari: GENEL_API_URL / GENEL_API_KEY / GENEL_MODEL.
"""

import json
import logging
import os

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None

from brain.kullanim import kullanim_ekle


class GenelClient:
    """Kullanicinin kendi (ucretli/ozel) saglayicisi."""

    def __init__(self, api_key: str, base_url: str, model: str):
        if not api_key or not api_key.strip():
            raise ValueError("Genel API anahtarı boş olamaz")
        if not base_url or not base_url.strip():
            raise ValueError("Genel API adresi boş olamaz")
        if not model or not model.strip():
            raise ValueError("Genel model adı boş olamaz")
        if OpenAI is None:
            raise RuntimeError("openai paketi kurulu değil")
        self.api_key = api_key.strip()
        self.base_url = base_url.strip().rstrip("/")
        self.model = model.strip()
        self.client = None
        self._kur()

    def _kur(self):
        try:
            self.client = OpenAI(
                api_key=self.api_key,
                timeout=20.0,
                max_retries=0,
                base_url=self.base_url,
            )
        except Exception as e:
            logger.warning("Genel saglayici kurulamadı: %s", e)
            self.client = None

    def musait(self) -> bool:
        return self.client is not None

    def cevapla(self, messages: list, tools: list = None,
                model: str = None, yapi=None) -> dict:
        """Diger istemcilerle birebir ayni sozlesme."""
        if not self.client:
            raise RuntimeError("Genel sağlayıcı bağlı değil")

        kwargs = {
            "model": model or self.model,
            "messages": messages,
            "max_tokens": 4096,
        }
        if tools:
            kwargs["tools"] = tools
        if yapi is not None:
            kwargs["response_format"] = {"type": "json_object"}

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
