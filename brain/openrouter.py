"""brain/openrouter.py — OpenRouter bulut entegrasyonu.

300+ modele tek key ile erişim. Auto-failover router.
OpenAI-uyumlu uç: https://openrouter.ai/api/v1
:free etiketli modeller ücretsiz.
"""

import json
import logging

from openai import OpenAI

logger = logging.getLogger(__name__)

from brain.kullanim import kullanim_ekle

BASE_URL = "https://openrouter.ai/api/v1"

# Sadece ücretsiz modeller (":free" suffix'li) - paid modeller KULLANILMAZ
TERCIH_SIRASI = [
    # Ücretsiz modeller (free tier) - öncelikli
    "openai/gpt-oss-20b:free",
    "openai/gpt-oss-120b:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemma-2-27b-it:free",
    "mistralai/mistral-7b-instruct:free",
    "qwen/qwen-2.5-72b-instruct:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "z-ai/glm-4.5-air:free",
    "google/gemma-4-31b-it:free",
    "nvidia/nemotron-3-nano-30b-a3b:free",
    "nvidia/nemotron-nano-9b-v2:free",
    "nvidia/nemotron-nano-12b-v2-vl:free",
    "cohere/north-mini-code:free",
    "poolside/laguna-s-2.1:free",
    "poolside/laguna-xs-2.1:free",
    "thinkingmachines/inkling:free",
    "thinkingmachines/inkling-small:free",
    "dots-studio/dots-3-note-preview:free",
    "liquid/lfm-2.5-2.6b:free",
    "openrouter/free",
]


class OpenRouterClient:
    """OpenRouter API istemcisi."""

    def __init__(self, api_key: str, model: str = None):
        if not api_key or not api_key.strip():
            raise ValueError("OpenRouter API anahtarı boş olamaz")
        self.api_key = api_key.strip()
        self.model = model
        self.client = None
        self._kur()

    def _kur(self):
        try:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=BASE_URL,
                timeout=20.0,
                max_retries=0,
                default_headers={
                    "HTTP-Referer": "http://localhost",
                    "X-Title": "Basak",
                },
            )
            if not self.model:
                self.model = self._model_bul()
        except Exception as e:
            logger.warning("OpenRouter kurulamadı: %s", e)
            self.client = None

    def _model_bul(self) -> str:
        """Hesapta kullanılabilir ilk ücretsiz modeli bulur.
        SADECE :free suffix'li modeller seçilir. Paid modeller asla seçilmez.
        """
        try:
            mevcutler = [m.id for m in self.client.models.list()]
        except Exception as e:
            logger.warning("OpenRouter model listesi alınamadı: %s", e)
            return TERCIH_SIRASI[0]
        
        # Sadece :free olan modelleri filtrele
        free_modeller = [m for m in mevcutler if m.endswith(":free")]
        
        # Tercih sırasına göre ilk bulunan free model
        for aday in TERCIH_SIRASI:
            if aday in free_modeller:
                return aday
        
        # Prefix match sadece free modeller içinde
        for aday in TERCIH_SIRASI:
            for m in free_modeller:
                if m == aday or m.startswith(aday.replace(":free", "") + ":"):
                    return m
        
        # Hiç free model yoksa (olmamalı) ilk free model
        if free_modeller:
            return free_modeller[0]
        
        logger.warning("Hiç :free model bulunamadı!")
        return TERCIH_SIRASI[0]

    def musait(self) -> bool:
        return self.client is not None

    def cevapla(self, messages: list, tools: list = None, yapi=None) -> dict:
        """OpenRouter'a mesaj gönderir. Dönen şekil groq.py ile aynıdır.

        yapi: sozlesme modu icin; bu saglayici su an yok sayar.
        """
        if not self.client:
            raise RuntimeError("OpenRouter bağlı değil")

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
            return kullanim_ekle({"content": msg.content or "",
                          "tool_calls": tool_calls}, resp)

        return kullanim_ekle({"content": msg.content or ""}, resp)