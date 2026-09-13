"""brain/glm.py — GLM bulut entegrasyonu (Z.ai resmi platformu).

OpenAI-uyumlu uç: https://api.z.ai/api/paas/v4/
Varsayılan model resmî fiyat tablosunda giriş/çıkışı ücretsiz olan
GLM-4.7-Flash'tır. Başak düşünme veya çıktı bütçesini zorla kapatmaz.
Z.AI'nin ücretli built-in web araması bu adaptörde açılmaz.
"""

import json
import logging

from openai import OpenAI

logger = logging.getLogger(__name__)

from brain.kullanim import kullanim_ekle

BASE_URL = "https://api.z.ai/api/paas/v4/"
MODELLER = {
    "hizli": "glm-4.7-flash",
    "varsayilan": "glm-4.7-flash",
}


class GLMClient:
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
                timeout=60.0,
                max_retries=0,
                base_url=BASE_URL,
            )
        except Exception as e:
            logger.warning("GLM kurulamadı: %s", e)
            self.client = None

    def musait(self) -> bool:
        return self.client is not None

    def cevapla(self, messages: list, tools: list = None, yapi=None) -> dict:
        if not self.client:
            raise RuntimeError("GLM bağlı değil")

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
