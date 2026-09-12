"""brain/nvidia.py — NVIDIA NIM bulut entegrasyonu (Nemotron + DeepSeek NIM).

OpenAI-uyumlu uc:
https://integrate.api.nvidia.com/v1
Anahtar: env NVIDIA_API_KEY veya ayarlar.json -> nvidia_key (nvapi-... ile baslar).

Model secimi:
- varsayilan: TERCIH_SIRASI'ndaki ilk hesapta acik model (GPT-OSS-20b)
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

from brain.kullanim import kullanim_ekle

BASE_URL = "https://integrate.api.nvidia.com/v1"

# Tercih sirasi: NIM katalog + chat kanitiyla tutulur.
# 2026-09-10 (FAZ4-3, canli): 80 modelli katalog cekildi; chat'te 410
# veren ve katalogdan dusenler cikarildi. Zamanasimi yiyenler yedekte.
TERCIH_SIRASI = [
    # CANLI — katalogda + chat kanitli
    "openai/gpt-oss-20b",                    # tool destekli
    "nvidia/nemotron-3-ultra-550b-a55b",     # 6.5s olculu, 1M baglam
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",  # TURKCE + multimodal
    "moonshotai/kimi-k3",                    # yavas ama canli (27.9s)
    # --- Katalogda ama 10.09.2026 chat zamanasimli (yedek) ---
    "nvidia/nemotron-3.5-lightning-30b-a3b",
    "nvidia/nemotron-3-super-120b-a12b",
    # --- Yeni adaylar (katalogda, olculmedi — en sonda denenir) ---
    "nvidia/nemotron-nano-3-30b-a3b",
    "nvidia/nemotron-4-340b-instruct",
]
# OLU (10.09.2026): katalog disi veya chat 410 Gone —
# meta/muse-glimmer-30b (katalogda gorunup 410 veriyor),
# nvidia-nemotron-nano-9b-v2, step-3.7-flash, inkling,
# nemotron-3-nano-30b-a3b, minimax-m3. Buraya donme, listeye ekleme.

DEEPSEEK_MODEL = "deepseek-ai/deepseek-v4-flash-0731"
GPTOSS_MODEL = "openai/gpt-oss-20b"

MODELLER = {
    "varsayilan": None,          # TERCIH_SIRASI'ndan otomatik
    "gptoss": GPTOSS_MODEL,
    "ultra": "nvidia/nemotron-3-ultra-550b-a55b",
    "omni": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
    "nano3": "nvidia/nemotron-nano-3-30b-a3b",
    "kimi": "moonshotai/kimi-k3",
    "deepseek": DEEPSEEK_MODEL,  # dusunen model; cok yavas (~90-180 sn)
}

# Dev thinking modelleri otomatik SECILMEZ (yavas); ayarlardan secilir.
# Otomatik secim her zaman hizli Nemotron hattini tercih eder.

# Buyuk modeller: dusunerek cevap verdikleri icin normalden yavastir;
# istemci varsayilan 20 sn timeout bunlara yetmez, cagri basina uzatilir
_THINKING_TIMEOUT = 20.0
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
    def _buyuk_model_mi(model_adi: str) -> bool:
        """Dusunen/buyuk modeller: DeepSeek, MiniMax, Ultra, Inkling."""
        ad = (model_adi or "").lower()
        return ("deepseek" in ad or "minimax" in ad
                or "ultra" in ad or "inkling" in ad)

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
        """Tek model icin cagri; buyuk modellerde timeout uzatilir."""
        kwargs = {
            "model": model_adi,
            "messages": messages,
        }
        if self._buyuk_model_mi(model_adi):
            kwargs["max_tokens"] = 4096
            kwargs["timeout"] = _THINKING_TIMEOUT
            if "deepseek" in model_adi.lower():
                # DeepSeek NIM'de dusunme modu acik olarak istenir
                kwargs["extra_body"] = {
                    "chat_template_kwargs": {"thinking": True}
                }
        else:
            kwargs["max_tokens"] = 4096
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
        """NVIDIA NIM'e mesaj gönderir.

        Secili model basarisizsa (zaman asimi/hata) siradaki aday modele
        dusen tek seferlik geri donus vardir; boylece zincir kesilmez.
        yapi: sozlesme modu icin; bu saglayici su an yok sayar.
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
