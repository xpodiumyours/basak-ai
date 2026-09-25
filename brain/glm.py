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
from brain.message_utils import reasoning_ayikla

BASE_URL = "https://api.z.ai/api/paas/v4/"
MODELLER = {
    # Ucretsiz katmanda bakiyesiz calisan modeller (2026-09 dogrulandi):
    # glm-4.7-flash ~200K baglam, kod+ajan islerinde guclu; glm-4.5-flash
    # hafif genel isler icin yedek. Eski tek-model kilidi kaldirildi.
    "hizli": "glm-4.7-flash",
    "varsayilan": "glm-4.7-flash",
    "hafif": "glm-4.5-flash",
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
                # 2026-09-19: 20.0 -> 8.0. Olcum (hiz_olcum.py): bu uc
                # kisa soruya 20.62 sn'de "Request timed out" dondu —
                # yani 20 sn tavani hep bosa harcaniyordu. 8 sn, cevap
                # veren bir uc icin fazlasiyla comert; vermeyeni de
                # zinciri 12 sn bekletmeden eler.
                max_retries=0,
                base_url=BASE_URL,
            )
        except Exception as e:
            logger.warning("GLM kurulamadı: %s", e)
            self.client = None

    def musait(self) -> bool:
        return self.client is not None

    def cevapla(self, messages: list, tools: list = None, yapi=None,
                tool_choice=None) -> dict:
        """GLM'e mesaj gönderir. Dönen şekil groq.py ile aynıdır.

        Not: dusunme (thinking) modu ACIK — modelin kendi muhakemesi kesilmez.
        yapi: sozlesme modu icin; bu saglayici su an yok sayar.
        """
        if not self.client:
            raise RuntimeError("GLM bağlı değil")

        kwargs = {
            "model": self.model,
            "messages": messages,
"extra_body": {"thinking": {"type": "enabled"}},
        }
        if tools:
            kwargs["tools"] = tools
            if tool_choice is not None:
                kwargs["tool_choice"] = tool_choice

        resp = self.client.chat.completions.create(**kwargs)
        msg = resp.choices[0].message
        # Reasoning zinciri (P0): thinking acikken gelen muhakeme
        # tur boyunca korunur; arac turunda modele geri verilir.
        muhakeme = reasoning_ayikla(msg)

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
                          "tool_calls": tool_calls, **muhakeme}, resp)

        return kullanim_ekle({"content": msg.content or "", **muhakeme}, resp)
