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

from brain.kullanim import kullanim_ekle
from brain.message_utils import reasoning_ayikla

# Ucretsiz modeller (2026-09 guncellemesi — Workers AI katalog + free plan):
# glm-4.7-flash ve gemma-4 free planda acik; llama-4-scout katalogda durur.
# Eski llama-3.x satirlari Mayis 2026'da emekli edildi, listeden cikti.
MODELLER = {
    "hizli": "@cf/google/gemma-4-26b-a4b-it",
    "guclu": "@cf/meta/llama-4-scout-17b-16e-instruct",
    "varsayilan": "@cf/zai-org/glm-4.7-flash",
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
                max_retries=0,
            )
        except Exception as e:
            logger.warning("Cloudflare kurulamadi: %s", e)
            self.client = None

    def musait(self) -> bool:
        return self.client is not None

    def cevapla(self, messages: list, tools: list = None, yapi=None,
                tool_choice=None) -> dict:
        """Cloudflare'a mesaj gonderir.

                varsayilani — 2026-09-13'te sabit 0.5 kaldirildi).
        yapi: sozlesme modu icin; bu saglayici su an yok sayar.
        """
        if not self.client:
            raise RuntimeError("Cloudflare bagli degil")

        from brain.message_utils import mesajlari_temizle
        temiz_mesajlar = mesajlari_temizle(messages)

        kwargs = {
            "model": self.model,
            "messages": temiz_mesajlar,
}
        if tools:
            kwargs["tools"] = tools
            if tool_choice is not None:
                kwargs["tool_choice"] = tool_choice

        resp = self.client.chat.completions.create(**kwargs)
        msg = resp.choices[0].message
        # Reasoning zinciri (P0): varsa korunur.
        try:
            from brain.message_utils import reasoning_ayikla as _r
            muhakeme = _r(msg)
        except Exception:
            muhakeme = {}

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
            return kullanim_ekle({"content": msg.content or "",
                          "tool_calls": tool_calls, **muhakeme}, resp)

        return kullanim_ekle({"content": msg.content or "", **muhakeme}, resp)
