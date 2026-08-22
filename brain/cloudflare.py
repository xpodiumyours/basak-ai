"""brain/cloudflare.py — Cloudflare Workers AI bulut entegrasyonu.

Ucretsiz modeller (tool calling destekli):
- @cf/meta/llama-3.1-8b-instruct — Hizli, genel amacli
- @cf/mistralai/mistral-7b-instruct-v0.2 — Alternatif
- @cf/google/gemma-2b-it — Kucuk ve hizli

API: OpenAI-uyumlu (chat/completions)
"""

import json
import logging

from openai import OpenAI

logger = logging.getLogger(__name__)

# Ucretsiz modeller (tool calling destekli)
MODELLER = {
    "hizli": "@cf/meta/llama-3.2-3b-instruct",
    "guclu": "@cf/meta/llama-4-scout-17b-16e-instruct",
    "varsayilan": "@cf/meta/llama-3.2-3b-instruct",
}


class CloudflareClient:
    """Cloudflare Workers AI istemcisi (OpenAI-uyumlu)."""

    def __init__(self, account_id: str, api_token: str, model: str = None):
        if not account_id or not account_id.strip():
            raise ValueError("Cloudflare Account ID bos olamaz")
        if not api_token or not api_token.strip():
            raise ValueError("Cloudflare API Token bos olamaz")
        self.account_id = account_id.strip()
        self.api_token = api_token.strip()
        self.model = model or MODELLER["varsayilan"]
        self.client = None
        self._kur()

    def _kur(self):
        try:
            base_url = (
                f"https://api.cloudflare.com/client/v4/accounts/"
                f"{self.account_id}/ai/v1"
            )
            self.client = OpenAI(
                api_key=self.api_token,
                base_url=base_url,
                timeout=30.0,
                max_retries=0,
            )
        except Exception as e:
            logger.warning("Cloudflare kurulamadi: %s", e)
            self.client = None

    def musait(self) -> bool:
        return self.client is not None

    def cevapla(self, messages: list, tools: list = None) -> dict:
        """Cloudflare'a mesaj gonderir.

        Hiz icin: temperature=0.5, max_tokens=1024.
        """
        if not self.client:
            raise RuntimeError("Cloudflare bagli degil")

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
                    },
                })
            return {"content": msg.content or "", "tool_calls": tool_calls}

        return {"content": msg.content or ""}
