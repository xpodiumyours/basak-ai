"""brain/nvidia.py — NVIDIA NIM bulut entegrasyonu (Nemotron + DeepSeek NIM).

OpenAI-uyumlu uc:
https://integrate.api.nvidia.com/v1
Anahtar: env NVIDIA_API_KEY veya ayarlar.json -> nvidia_key (nvapi-... ile baslar).

Model secimi:
- varsayilan: TERCIH_SIRASI'ndaki ilk hesapta acik Nemotron varyanti
- ayarlar.json -> "nvidia_model" ile sabit model secilebilir
  (orn. deepseek-v4-flash). Bu model "thinking" modundadir ve yaniti
  gecikebilir; o yuzden cevapla() model duzeyinde yedegine dusen
  (Nemotron'a) geri donus yapar.

Arayuz groq.py / gemini.py ile birebir aynidir.
"""

import json
import logging

from openai import OpenAI

logger = logging.getLogger(__name__)

BASE_URL = "https://integrate.api.nvidia.com/v1"

# Tercih sirasi: guncel NVIDIA NIM modelleri (agustos 2026)
TERCIH_SIRASI = [
    "nvidia/nemotron-3.5-lightning-30b-a3b",
    "nvidia/nemotron-3-super-120b-a12b",
    "nvidia/llama-3.3-nemotron-super-49b-v1.5",
    "meta/llama-3.3-70b-instruct",
    "nvidia/nemotron-3-nano-30b-a3b",
]

DEEPSEEK_MODEL = "deepseek-ai/deepseek-v4-flash-0731"

MODELLER = {
    "varsayilan": None,          # TERCIH_SIRASI'ndan otomatik
    "deepseek": DEEPSEEK_MODEL,
}

# DeepSeek v4 Flash: dusunerek cevap verir; normal cagrilara gore cok daha yavas
_THINKING_TIMEOUT = 180.0
_NORMAL_TIMEOUT = 20.0


class NvidiaClient:
    """NVIDIA NIM API istemcisi."""

    def __init__(self, api_key: str, model: str = None):
        if not api_key or not api_key.strip():
            raise ValueError("NVIDIA API anahtarı boş olamaz")
        self.api_key = api_key.strip()
        self.model = model
        self.client = None
        self._kur()

    @staticmethod
    def _thinking_mi(model_adi: str) -> bool:
        return bool(model_adi and "deepseek" in model_adi.lower())

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
        """Hesapta kullanilabilir ilk tercih edilen modeli bulur.

        DeepSeek modeli ke sirada denenmez (cok yavas/dusunen model).
        Manuel secim icin nvidia_model ayari kullanilir.
        """
        try:
            mevcutler = [m.id.lower() for m in self.client.models.list()]
        except Exception as e:
            logger.warning("NVIDIA model listesi alinamadi: %s", e)
            return TERCIH_SIRASI[0]
        for aday in TERCIH_SIRASI:
            for m in mevcutler:
                if m.startswith(aday.lower()):
                    return m
        # Hi bir tercih yoksa ilk mevcut modeli don (DeepSeek hariç)
        for m in mevcutler:
            if 'deepseek' not in m:
                return m
        return mevcutler[0] if mevcutler else TERCIH_SIRASI[0]

    def musait(self) -> bool:
        return self.client is not None

    def _cagri_ata(self, model_adi: str, messages: list, tools: list = None) -> dict:
        """Tek model icin cagri; DeepSeek icin thinking ayarlari eklenir."""
        kwargs = {
            "model": model_adi,
            "messages": messages,
            "temperature": 0.5,
        }
        if self._thinking_mi(model_adi):
            # Dusunen modelde uzun cevap uretilir; token tavanini makul tut
            kwargs["max_tokens"] = 2048
            kwargs["extra_body"] = {
                "chat_template_kwargs": {"thinking": True}
            }
        else:
            kwargs["max_tokens"] = 1024
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

    def cevapla(self, messages: list, tools: list = None) -> dict:
        """NVIDIA NIM'e mesaj gönderir.

        Secili model basarisizsa (zaman asimi/hata) siradaki aday modele
        dusen tek seferlik geri donus vardir; boylece zincir kesilmez.
        """
        if not self.client:
            raise RuntimeError("NVIDIA bağlı değil")

        sirali = []
        if self.model and self.model not in TERCIH_SIRASI:
            sirali.append(self.model)   # secili ozel model once denenir
        sirali += TERCIH_SIRASI

        son_hata = None
        for model_adi in sirali[:4]:
            try:
                return self._cagri_ata(model_adi, messages, tools)
            except Exception as e:
                son_hata = e
                logger.warning("NVIDIA %s hatasi, siradaki modele dusuluyor: %s",
                               model_adi, str(e)[:120])
        raise RuntimeError("NVIDIA tüm modeller başarısız") from son_hata
