"""brain/nvidia.py — NVIDIA NIM bulut entegrasyonu.

OpenAI-uyumlu NVIDIA NIM ucu kullanılır. Başak modelin çıktı uzunluğunu
sabit 1024/2048 ile kesmez. Reasoning modellerine yeterli süre tanınır ve
araç seçimi modele bırakılır.
"""

import json
import logging

from openai import OpenAI

logger = logging.getLogger(__name__)

from brain.kullanim import kullanim_ekle

BASE_URL = "https://integrate.api.nvidia.com/v1"

TERCIH_SIRASI = [
    "openai/gpt-oss-20b",
    "nvidia/nemotron-3-ultra-550b-a55b",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
    "moonshotai/kimi-k3",
    "nvidia/nemotron-3.5-lightning-30b-a3b",
    "nvidia/nemotron-3-super-120b-a12b",
    "nvidia/nemotron-nano-3-30b-a3b",
    "nvidia/nemotron-4-340b-instruct",
]

DEEPSEEK_MODEL = "deepseek-ai/deepseek-v4-flash-0731"
GPTOSS_MODEL = "openai/gpt-oss-20b"

MODELLER = {
    "varsayilan": None,
    "gptoss": GPTOSS_MODEL,
    "ultra": "nvidia/nemotron-3-ultra-550b-a55b",
    "omni": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
    "nano3": "nvidia/nemotron-nano-3-30b-a3b",
    "kimi": "moonshotai/kimi-k3",
    "deepseek": DEEPSEEK_MODEL,
}

_THINKING_TIMEOUT = 120.0
_NORMAL_TIMEOUT = 60.0


class NvidiaClient:
    def __init__(self, api_key: str, model: str = None):
        if not api_key or not api_key.strip():
            raise ValueError("NVIDIA API anahtarı boş olamaz")
        self.api_key = api_key.strip()
        self.model = model
        self.client = None
        self._kur()

    @staticmethod
    def _buyuk_model_mi(model_adi: str) -> bool:
        ad = (model_adi or "").lower()
        return ("deepseek" in ad or "minimax" in ad
                or "ultra" in ad or "inkling" in ad
                or "reasoning" in ad or "kimi" in ad)

    def _kur(self):
        try:
            self.client = OpenAI(
                api_key=self.api_key,
                timeout=_NORMAL_TIMEOUT,
                max_retries=0,
                base_url=BASE_URL,
            )
            if not self.model:
                self.model = self._model_bul()
        except Exception as e:
            logger.warning("NVIDIA kurulamadı: %s", e)
            self.client = None

    def _model_bul(self) -> str:
        try:
            mevcutler = [m.id.lower() for m in self.client.models.list()]
        except Exception as e:
            logger.warning("NVIDIA model listesi alinamadi: %s", e)
            return TERCIH_SIRASI[0]
        for aday in TERCIH_SIRASI:
            for m in mevcutler:
                if m.startswith(aday.lower()):
                    return m
        return mevcutler[0] if mevcutler else TERCIH_SIRASI[0]

    def musait(self) -> bool:
        return self.client is not None

    def _cagri_ata(self, model_adi: str, messages: list,
                   tools: list = None) -> dict:
        kwargs = {
            "model": model_adi,
            "messages": messages,
            "temperature": 0.5,
            "timeout": (_THINKING_TIMEOUT if self._buyuk_model_mi(model_adi)
                        else _NORMAL_TIMEOUT),
        }
        if "deepseek" in (model_adi or "").lower():
            kwargs["extra_body"] = {
                "chat_template_kwargs": {"thinking": True}
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

    def cevapla(self, messages: list, tools: list = None, yapi=None) -> dict:
        if not self.client:
            raise RuntimeError("NVIDIA bağlı değil")

        sirali = []
        if self.model:
            sirali.append(self.model)
        sirali += [m for m in TERCIH_SIRASI if m not in sirali]

        son_hata = None
        for model_adi in sirali:
            try:
                return self._cagri_ata(model_adi, messages, tools)
            except Exception as e:
                son_hata = e
                logger.warning("NVIDIA %s hatasi, siradaki modele dusuluyor: %s",
                               model_adi, str(e)[:120])
        raise RuntimeError("NVIDIA tüm modeller başarısız") from son_hata
