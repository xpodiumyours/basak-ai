"""brain/openrouter.py — OpenRouter ücretsiz model geçidi.

`openrouter/free` sıfır fiyatlı modeller arasından isteğin ihtiyaç duyduğu
yetenekleri (ör. tool calling) destekleyen modeli sunucu tarafında seçer.
Başak ücretli model seçmez, düşük çıktı tavanı koymaz ve araç seçimini modele bırakır.
"""

import json
import logging

from openai import OpenAI

logger = logging.getLogger(__name__)

from brain.kullanim import kullanim_ekle

BASE_URL = "https://openrouter.ai/api/v1"
VARSAYILAN_MODEL = "openrouter/free"


class OpenRouterClient:
    def __init__(self, api_key: str, model: str = None):
        if not api_key or not api_key.strip():
            raise ValueError("OpenRouter API anahtarı boş olamaz")
        self.api_key = api_key.strip()
        # Kullanıcı açıkça model verirse yalnız :free veya free router kabul et.
        if model and model != VARSAYILAN_MODEL and not model.endswith(":free"):
            raise ValueError("OpenRouter otomatik zincirde yalnız ücretsiz model kullanır")
        self.model = model or VARSAYILAN_MODEL
        self.client = None
        self._kur()

    def _kur(self):
        try:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=BASE_URL,
                timeout=60.0,
                max_retries=0,
                default_headers={
                    "HTTP-Referer": "http://localhost",
                    "X-Title": "Basak",
                },
            )
        except Exception as e:
            logger.warning("OpenRouter kurulamadı: %s", e)
            self.client = None

    def musait(self) -> bool:
        return self.client is not None

    def cevapla(self, messages: list, tools: list = None, yapi=None) -> dict:
        if not self.client:
            raise RuntimeError("OpenRouter bağlı değil")

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
