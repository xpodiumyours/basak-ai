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
from brain.message_utils import reasoning_ayikla

BASE_URL = "https://openrouter.ai/api/v1"

# Sadece ücretsiz modeller (":free" suffix'li) - paid modeller KULLANILMAZ
# 2026-09-13 olcumu (canli katalog, 19 model): sirf katalogda OLANLAR.
# Oluler cikarildi (gpt-oss, llama-3.3, mistral-7b, qwen-2.5, glm-4.5-air,
# nano-9b/12b). lightning:free olculdu — 105 sn + dusunce sizdiriyor,
# varsayilan DEGIL (ultra ispatli, listede durur).
TERCIH_SIRASI = [
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "google/gemma-4-31b-it:free",
    "poolside/laguna-s-2.1:free",
    "poolside/laguna-xs-2.1:free",
    "cohere/north-mini-code:free",
    "thinkingmachines/inkling-small:free",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
    "inclusionai/ling-3.0-flash-fin:free",
    "nex-n2.5-mini:free",
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
            modeller = list(self.client.models.list())
        except Exception as e:
            logger.warning("OpenRouter model listesi alınamadı: %s", e)
            return TERCIH_SIRASI[0]

        # Ajan varsayilani yalniz ucretsiz + tools + tool_choice destekli
        # modelden secilir. OpenRouter bu yetenekleri model kartinda
        # supported_parameters olarak yayinlar.
        free_modeller = []
        for m in modeller:
            mid = getattr(m, "id", "")
            if not mid.endswith(":free"):
                continue
            destek = set(getattr(m, "supported_parameters", []) or [])
            if {"tools", "tool_choice"}.issubset(destek):
                free_modeller.append(mid)
        
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

    def ajan_musait(self) -> bool:
        """Secili modelin OpenRouter katalogunda tools+tool_choice destegi."""
        onbellek = getattr(self, "_ajan_destek_cache", None)
        if (isinstance(onbellek, tuple) and len(onbellek) == 2
                and onbellek[0] == self.model):
            return bool(onbellek[1])
        if not self.client or not self.model or not self.model.endswith(":free"):
            self._ajan_destek_cache = (self.model, False)
            return False
        try:
            for m in self.client.models.list():
                if getattr(m, "id", "") != self.model:
                    continue
                destek = set(getattr(m, "supported_parameters", []) or [])
                sonuc = {"tools", "tool_choice"}.issubset(destek)
                self._ajan_destek_cache = (self.model, sonuc)
                return sonuc
        except Exception as e:
            logger.warning("OpenRouter ajan yetenegi dogrulanamadi: %s", e)
        self._ajan_destek_cache = (self.model, False)
        return False

    def cevapla(self, messages: list, tools: list = None, yapi=None,
                tool_choice=None) -> dict:
        """OpenRouter'a mesaj gönderir. Dönen şekil groq.py ile aynıdır.

        yapi: sozlesme modu icin; bu saglayici su an yok sayar.
        """
        if not self.client:
            raise RuntimeError("OpenRouter bağlı değil")

        kwargs = {
            "model": self.model,
            "messages": messages,
}
        if tools:
            kwargs["tools"] = tools
            if tool_choice is not None:
                kwargs["tool_choice"] = tool_choice
            # OpenRouter resmi provider-routing davranisi: aracli istegi
            # yalniz gonderilen parametreleri gercekten destekleyen uclara
            # yonlendir. Model secimini veya cevabini kisitlamaz.
            kwargs["extra_body"] = {
                "provider": {"require_parameters": True}
            }

        resp = self.client.chat.completions.create(**kwargs)
        secimler = getattr(resp, "choices", None) or []
        if not secimler:
            # Bazi free yonlendiriciler 200 ile bos choices dondurebiliyor
            # (olcum 2026-09-20: sayfa_oku hucresi 'NoneType' cokmesi).
            # Cokme degil anlasilir hata: zincirin zarif hata yolu devreye
            # girsin (AGENTS.md §5: hata yollarini es gecme).
            raise RuntimeError(
                "OpenRouter bos yanit dondu (choices yok), model=%s"
                % self.model)
        msg = secimler[0].message
        # Reasoning zinciri (P0): OpenRouter reasoning / reasoning_details
        # alanlari korunur; arac turunda modele geri verilir.
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