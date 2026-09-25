"""brain/gemini.py — Google Gemini bulut entegrasyonu (yedek saglayici).

Google'in OpenAI-uyumlu ucu kullanilir:
https://generativelanguage.googleapis.com/v1beta/openai/
Boylece groq.py ile ayni arayuz ve ayni yanit sekli korunur.

Ucretsiz katman: gemini-2.5-flash (kredi karti gerekmez).
"""

import json
import logging

from openai import OpenAI

logger = logging.getLogger(__name__)

from brain.kullanim import kullanim_ekle
from brain.message_utils import reasoning_ayikla

# OpenAI uyumlu Gemini ucu + ucretsiz modeller
BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
MODELLER = {
    # 2026-09 guncellemesi: 3 Flash onerilen ucretsiz model (1M baglam,
    # 10 RPM / 250K TPM / 1500 RPD). 2.5 Flash yedek durur.
    "hizli": "gemini-3-flash-preview",
    "varsayilan": "gemini-3-flash-preview",
    "yedek": "gemini-2.5-flash",
}
# 2026-09-23 (Faz 3+5): canli probe — sirayla denenir; varsayilan basa
# kalir. 404/503 kalici oluler buraya almaz (model-probe2/3.json).
YADEK_SIRASI = [
    "gemini-3-flash-preview",
    "gemini-2.5-flash",
    "gemini-flash-lite-latest",
    "gemini-3.5-flash-lite",
    "gemini-3.6-flash",
    "gemma-4-26b-a4b-it",                 # 2026-09-23 Faz5 filtre-disi canli ~2s
    "gemini-3.1-flash-lite-preview",      # 2026-09-23 Faz5 gec geldi ~14s
]
_ICI_YEDEK_SAYISI = 6


class GeminiClient:
    """Google Gemini API istemcisi."""

    def __init__(self, api_key: str, model: str = None):
        if not api_key or not api_key.strip():
            raise ValueError("Gemini API anahtarı boş olamaz")
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
            logger.warning("Gemini kurulamadı: %s", e)
            self.client = None

    def musait(self) -> bool:
        return self.client is not None

    def cevapla(self, messages: list, tools: list = None, yapi=None,
                tool_choice=None) -> dict:
        """Gemini'ye mesaj gönderir. Dönen şekil groq.py ile aynıdır.

        yapi: sozlesme modu icin; bu saglayici su an yok sayar.
        """
        if not self.client:
            raise RuntimeError("Gemini bağlı değil")

        # Secili model basarisizsa yedek zincire dusen tek seferlik
        # geri donus (nvidia.cevapla ile ayni kalip — Faz 3).
        ilk = getattr(self, "model", None) or MODELLER["varsayilan"]
        sirali = []
        for m in [ilk] + YADEK_SIRASI:
            if m and m not in sirali:
                sirali.append(m)

        son_hata = None
        for model_adi in sirali[:_ICI_YEDEK_SAYISI]:
            try:
                yanit = self._cagri_ata(model_adi, messages, tools,
                                        tool_choice=tool_choice)
                self.model = model_adi
                return yanit
            except Exception as e:
                son_hata = e
                logger.warning(
                    "Gemini %s hatasi, siradaki modele dusuluyor: %s",
                    model_adi, str(e))
        raise RuntimeError("Gemini tüm modeller başarısız") from son_hata

    def _cagri_ata(self, model_adi: str, messages: list, tools: list = None,
                   tool_choice=None) -> dict:
        kwargs = {
            "model": model_adi,
            "messages": messages,
}
        if tools:
            kwargs["tools"] = tools
            if tool_choice is not None:
                kwargs["tool_choice"] = tool_choice

        resp = self.client.chat.completions.create(**kwargs)
        msg = resp.choices[0].message
        muhakeme = reasoning_ayikla(msg)

        if msg.tool_calls:
            tool_calls = []
            for tc in msg.tool_calls:
                args = tc.function.arguments
                if not isinstance(args, str):
                    args = json.dumps(args) if args else "{}"
                _call = {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": args,
                    }
                }
                # Gemini 3 OpenAI-uyumlu function call'larda sifreli
                # thought signature'i extra_content.google altinda verir.
                # Cok turlu tool kullaniminda aynen geri gonderilmesi
                # zorunludur; atilirsa sonraki tur 400 ile reddedilebilir.
                ekstra = getattr(tc, "extra_content", None)
                if ekstra is not None:
                    if hasattr(ekstra, "model_dump"):
                        ekstra = ekstra.model_dump(exclude_none=True)
                    elif not isinstance(ekstra, dict):
                        try:
                            ekstra = dict(ekstra)
                        except Exception:
                            ekstra = None
                    if ekstra:
                        _call["extra_content"] = ekstra
                tool_calls.append(_call)
            return kullanim_ekle({"content": msg.content or "",
                          "tool_calls": tool_calls, **muhakeme}, resp)

        return kullanim_ekle({"content": msg.content or "", **muhakeme}, resp)
