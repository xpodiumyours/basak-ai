"""brain/kilo.py — Kilo Gateway ücretsiz model entegrasyonu.

Yalnız ücretsiz Kilo rotası/modelleri kullanılır. Başak reasoning yapan
modellerin çıktı bütçesini sabit bir max_tokens değeriyle kesmez; sağlayıcı
ve seçilen model kendi doğal sınırlarıyla çalışır.
"""

import json
import logging

from openai import OpenAI

logger = logging.getLogger(__name__)

from brain.kullanim import kullanim_ekle

BASE_URL = "https://api.kilo.ai/api/gateway/v1"
YER_TUTUCU_ANAHTAR = "anahtarsiz"

VARSAYILAN_MODEL = "kilo-auto/free"
TERCIH_SIRASI = [
    "kilo-auto/free",
    "stepfun/step-3.7-flash:free",
    "tencent/hy3:free",
    "poolside/laguna-s-2.1:free",
]


class KiloClient:
    def __init__(self, model: str = None):
        self.model = model or VARSAYILAN_MODEL
        self.client = None
        self._kur()

    def _kur(self):
        try:
            self.client = OpenAI(
                api_key=YER_TUTUCU_ANAHTAR,
                base_url=BASE_URL,
                timeout=60.0,
                max_retries=0,
                default_headers={
                    "HTTP-Referer": "http://localhost",
                    "X-Title": "Basak",
                },
            )
        except Exception as e:
            logger.warning("Kilo kurulamadı: %s", e)
            self.client = None

    def musait(self) -> bool:
        return self.client is not None

    def cevapla(self, messages: list, tools: list = None, yapi=None) -> dict:
        if not self.client:
            raise RuntimeError("Kilo bağlı değil")

        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.5,
        }
        if tools:
            kwargs["tools"] = tools

        resp = self.client.chat.completions.create(**kwargs)
        secim = resp.choices[0]
        msg = secim.message

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

        icerik = msg.content or ""
        if not icerik.strip():
            neden = getattr(secim, "finish_reason", None) or "bilinmiyor"
            raise RuntimeError(
                "Kilo bos cevap dondu (finish_reason=%s)" % neden)

        return kullanim_ekle({"content": icerik}, resp)
