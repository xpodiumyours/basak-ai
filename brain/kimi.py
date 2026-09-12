"""brain/kimi.py — Kimi (Moonshot) bulut yuvasi (KAPALI).

Kural (P0 + FAZ4 arastirmasi): saglayici veri karti olmadan hassas veri
gitmez. Kart (data/veri-kartlari/kimi.md) dolana kadar bu istemci
ZINCIRE GIRMEZ — adaptor kart + acik bayrak olmadan None doner.
Model adi uydurulmaz: ayarlardan (kimi_model) veya ortamdan
(KIMI_MODEL) acikca verilmelidir.
"""

import json
import logging

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None

BASE_URL = "https://api.moonshot.ai/v1"


class KimiClient:
    """Kimi API istemcisi (OpenAI-uyumlu uc)."""

    def __init__(self, api_key: str, model: str):
        if not api_key or not api_key.strip():
            raise ValueError("Kimi API anahtarı boş olamaz")
        if not model or not model.strip():
            raise ValueError("Kimi model adı boş olamaz")
        if OpenAI is None:
            raise RuntimeError("openai paketi kurulu değil")
        self.api_key = api_key.strip()
        self.model = model.strip()
        self.client = None
        self._kur()

    def _kur(self):
        try:
            self.client = OpenAI(
                api_key=self.api_key,
                timeout=3.0,
                max_retries=0,
                base_url=BASE_URL,
            )
        except Exception as e:
            logger.warning("Kimi kurulamadı: %s", e)
            self.client = None

    def musait(self) -> bool:
        return self.client is not None

    def cevapla(self, messages: list, tools: list = None, yapi=None) -> dict:
        """Diger istemcilerle ayni sozlesme."""
        from brain.kullanim import kullanim_ekle
        if not self.client:
            raise RuntimeError("Kimi bağlı değil")
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.5,
            "max_tokens": 2048,
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
                    "id": tc.id or "call_%d" % len(tool_calls),
                    "type": "function",
                    "function": {
                        "name": tc.function.name if tc.function else "",
                        "arguments": args,
                    },
                })
            return kullanim_ekle({"content": msg.content or "",
                                  "tool_calls": tool_calls}, resp)
        return kullanim_ekle({"content": msg.content or ""}, resp)
