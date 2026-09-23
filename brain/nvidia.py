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
from brain.message_utils import reasoning_ayikla

BASE_URL = "https://integrate.api.nvidia.com/v1"

# Tercih sirasi: NIM katalog + chat kanitiyla tutulur.
# 2026-09-10 (FAZ4-3, canli): 80 modelli katalog cekildi; chat'te 410
# veren ve katalogdan dusenler cikarildi. Zamanasimi yiyenler yedekte.
# 2026-09-16 (Casper karari): HIZLI HAT once. Etkilesimli kullanimda
# cevap 90 sn'de ekrana dusmeli; ultra-550b fatura akisinin 4. turunda
# dakikalardir dusunup ekrani zamanasina soktu. Dusunen devler yedekte.
# 2026-09-23 (Faz 3 genis havuz): models.list 82 model; probe ile
# 404/410 oluler TERCIH_SIRASI'ndan cikti; kanitli canli aday eklendi.
TERCIH_SIRASI = [
    # HIZLI HAT — ilk 4, _ICI_YEDEK_SAYISI kapsar
    "openai/gpt-oss-20b",                    # hizli
    "nvidia/nemotron-3.5-lightning-30b-a3b",  # hizli
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",  # TURKCE + multimodal
    "nvidia/nemotron-3-super-120b-a12b",     # 120b
    # --- Yavas yedekler: hizli hat duserse denenir ---
    "moonshotai/kimi-k3",                    # yavas ama canli (27.9s)
    "meta/llama-3.2-11b-vision-instruct",    # 2026-09-23 probe canli ~0.3s
    # --- Yedekler (olcu, en sonda denenir) ---
    "nvidia/nemotron-3-ultra-550b-a55b",     # 550b dev, en son yedek
]
# 2026-09-23 probe: TERCIH_SIRASI tukendikten sonra denenir (katalogda
# gorunup chat'te yasayan adaylar). Oluler buraya almaz.
GENIS_HAVUZ = [
    "meta/llama-3.2-11b-vision-instruct",
    "nvidia/nemotron-3.5-lightning-30b-a3b",
    "nvidia/nemotron-3-super-120b-a12b",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
]
# 2026-09-23 canli probe: katalogda var ama chat 404/410 — listeye
# geri gelmez; _model_bul bunlari atlar.
KARA_LISTE = {
    "nvidia/nemotron-4-340b-instruct",       # 404 (2026-09-23)
    "nvidia/nemotron-nano-3-30b-a3b",        # 404 (2026-09-23)
    "nvidia/nemotron-3-nano-30b-a3b",        # 410 (10.09.2026)
}
# Model-ici geri donus adedi: secili + listedeki ilk adaylar denenir.
# 4 degeri 2026-09 gozleminden (ilk 4 CANLI + yedek kapsar); buyutme
# her basarisizlikta kota/zaman yer. Faz 3: genis havuz icin 6.
_ICI_YEDEK_SAYISI = 6
# OLU (10.09.2026): katalog disi veya chat 410 Gone —
# meta/muse-glimmer-30b (katalogda gorunup 410 veriyor),
# nvidia-nemotron-nano-9b-v2, step-3.7-flash, inkling,
# nemotron-3-nano-30b-a3b, minimax-m3. Buraya donme, listeye ekleme.
# 2026-09-23: nvidia/nemotron-4-340b-instruct + nemotron-nano-3-30b-a3b
# ayrica 404 — KARA_LISTE + tests/test_nvidia_liste.py OLULER.

DEEPSEEK_MODEL = "deepseek-ai/deepseek-v4-flash-0731"
GPTOSS_MODEL = "openai/gpt-oss-20b"

MODELLER = {
    "varsayilan": None,          # TERCIH_SIRASI'ndan otomatik
    "gptoss": GPTOSS_MODEL,
    "ultra": "nvidia/nemotron-3-ultra-550b-a55b",
    "omni": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
    "kimi": "moonshotai/kimi-k3",
    "llama11b": "meta/llama-3.2-11b-vision-instruct",
    "deepseek": DEEPSEEK_MODEL,  # dusunen model; cok yavas (~90-180 sn)
}

# Dev thinking modelleri otomatik SECILMEZ (yavas); ayarlardan secilir.
# Otomatik secim her zaman hizli Nemotron hattini tercih eder.

# Buyuk modeller: dusunerek cevap verdikleri icin normalden yavastir;
# model-odakli istisna: dusunen hatta jeton/zaman genis tutulur
# (ARAC-PLANI S5 cizgisi normal hat icin 4096/20.0).
# 2026-09-16 (Casper karari): 600 sn ekrani kilitliyordu (UI 90 sn'de
# pes eder); yedek dev hatta tek hak 180 sn.
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

        Siras: TERCIH_SIRASI -> GENIS_HAVUZ -> katalogda kara liste
        disindaki ilk model. DeepSeek modeli ke sirada denenmez
        (cok yavas/dusunen model). Manuel secim nvidia_model ayaridir.
        """
        try:
            mevcutler = [m.id.lower() for m in self.client.models.list()]
        except Exception as e:
            logger.warning("NVIDIA model listesi alinamadi: %s", e)
            return TERCIH_SIRASI[0]
        kara = {k.lower() for k in KARA_LISTE}
        for aday in list(TERCIH_SIRASI) + list(GENIS_HAVUZ):
            if aday.lower() in kara:
                continue
            for m in mevcutler:
                if m.startswith(aday.lower()) and m not in kara:
                    return m
        # Hi bir tercih yoksa kara liste disindaki ilk modeli don
        # (DeepSeek hariç)
        for m in mevcutler:
            if m in kara or "deepseek" in m:
                continue
            return m
        return TERCIH_SIRASI[0]

    def musait(self) -> bool:
        return self.client is not None

    def _cagri_ata(self, model_adi: str, messages: list, tools: list = None,
                   tool_choice=None) -> dict:
        """Tek model icin cagri; buyuk modellerde timeout uzatilir."""
        kwargs = {
            "model": model_adi,
            "messages": messages,
        }
        if self._buyuk_model_mi(model_adi):
            kwargs["max_tokens"] = 32768
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

    def cevapla(self, messages: list, tools: list = None, yapi=None,
                tool_choice=None) -> dict:
        """NVIDIA NIM'e mesaj gönderir.

        Secili model basarisizsa (zaman asimi/hata) siradaki aday modele
        dusen tek seferlik geri donus vardir; boylece zincir kesilmez.
        yapi: sozlesme modu icin; bu saglayici su an yok sayar.
        """
        if not self.client:
            raise RuntimeError("NVIDIA bağlı değil")

        # NVIDIA NIM guncel dokumani required degerini desteklemiyor.
        # Ajan modunda Brain buraya "auto" gonderir ve duz metni disarida
        # basari saymaz. Tool-calling'i resmi olarak destekledigi acik olan
        # GPT-OSS-20B ajan hattinda kullanilir.
        if tools and tool_choice is not None:
            sirali = [GPTOSS_MODEL]
        else:
            gorulen = []
            if self.model and self.model not in TERCIH_SIRASI:
                gorulen.append(self.model)
            gorulen += TERCIH_SIRASI + GENIS_HAVUZ
            kara = {k.lower() for k in KARA_LISTE}
            sirali = []
            for m in gorulen:
                if m.lower() in kara or m in sirali:
                    continue
                sirali.append(m)

        son_hata = None
        for model_adi in sirali[:_ICI_YEDEK_SAYISI]:
            try:
                return self._cagri_ata(
                    model_adi, messages, tools, tool_choice=tool_choice)
            except Exception as e:
                son_hata = e
                logger.warning("NVIDIA %s hatasi, siradaki modele dusuluyor: %s",
                               model_adi, str(e))
        raise RuntimeError("NVIDIA tüm modeller başarısız") from son_hata
