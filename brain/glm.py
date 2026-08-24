"""brain/glm.py — GLM bulut entegrasyonu (Z.ai resmi platformu).

Ucuncu bulut saglayici. OpenAI-uyumlu uc:
https://api.z.ai/api/paas/v4/
Model: glm-4.7. Anahtar: env ZAI_API_KEY veya ayarlar.json -> zai_key.

Arayuz groq.py / gemini.py ile birebir aynidir.
"""

import json
import logging

from openai import OpenAI

logger = logging.getLogger(__name__)

from brain.kullanim import kullanim_ekle

BASE_URL = "https://api.z.ai/api/paas/v4/"
MODELLER = {
    # ucretsiz katmanda bakiyesiz calisan model (2026-08 dogrulandi)
    "hizli": "glm-4.5-flash",
    "varsayilan": "glm-4.5-flash",
}


class GLMClient:
    """Z.ai API istemcisi (GLM)."""

    def __init__(self, api_key: str, model: str = None):
        if not api_key or not api_key.strip():
            raise ValueError("GLM API anahtarı boş olamaz")
        self.api_key = api_key.strip()
        self.model = model or MODELLER["varsayilan"]
        self.client = None
        self._kur()

    def _kur(self):
        try:
            self.client = OpenAI(
                api_key=self.api_key,
                timeout=5.0,
                max_retries=0,
                base_url=BASE_URL,
            )
        except Exception as e:
            logger.warning("GLM kurulamadı: %s", e)
            self.client = None

    def musait(self) -> bool:
        return self.client is not None

    def cevapla(self, messages: list, tools: list = None) -> dict:
        """GLM'e mesaj gönderir. Dönen şekil groq.py ile aynıdır.

        Not: dusunme (thinking) modu kapatilir — sohbet icin hiz onceliklidir.
        """
        if not self.client:
            raise RuntimeError("GLM bağlı değil")

        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.5,
            "max_tokens": 1024,
            "extra_body": {"thinking": {"type": "disabled"}},
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
