"""brain/deepseek.py — DeepSeek bulut entegrasyonu (dorduncu saglayici).

Ucuncu taraf OpenAI-uyumlu uc:
https://api.deepseek.com/v1
Model: deepseek-chat. Anahtar: env DEEPSEEK_API_KEY veya ayarlar.json -> deepseek_key.

NOT: DeepSeek ucretli platformdur — hesapta bakiye yoksa API 402 doner;
zincir bu hatayi sessizce atlar (bir sonraki saglayici devralir).

Arayuz groq.py / gemini.py ile birebir aynidir.
"""

import json
import logging

from openai import OpenAI

logger = logging.getLogger(__name__)

BASE_URL = "https://api.deepseek.com/v1"
MODELLER = {
    "hizli": "deepseek-chat",
    "varsayilan": "deepseek-chat",
}


class DeepSeekClient:
    """DeepSeek API istemcisi."""

    def __init__(self, api_key: str, model: str = None):
        if not api_key or not api_key.strip():
            raise ValueError("DeepSeek API anahtarı boş olamaz")
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
                base_url=BASE_URL,
            )
        except Exception as e:
            logger.warning("DeepSeek kurulamadı: %s", e)
            self.client = None

    def musait(self) -> bool:
        return self.client is not None

    def cevapla(self, messages: list, tools: list = None) -> dict:
        """DeepSeek'e mesaj gönderir. Dönen şekil groq.py ile aynıdır."""
        if not self.client:
            raise RuntimeError("DeepSeek bağlı değil")

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
