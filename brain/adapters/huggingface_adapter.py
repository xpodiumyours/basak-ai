"""brain/adapters/huggingface_adapter — Hugging Face Inference Providers.

Dogrulama: 2026-09-22 (huggingface.co/docs/inference-providers). Tek HF
jetonuyla 18+ saglayiciya yonlendiren bir "router". OpenAI-uyumlu:

    base_url = https://router.huggingface.co/v1

ONEMLI — OTOMATIK ZINCIRDE YOK: ucretsiz hesap ayda yalnizca 0,10 dolar
kredi alir (PRO 2 dolar). Bu, sinirsiz bedava saglayici degildir; bu
yuzden registry kartinda "ucretsiz": false + "otomatik_ucretsiz": false
yazilidir ve saglayici kendiliginden cagrilmaz. Kart Casper karariyla
acilmadan zincire girmez.

Model kimligine politika eki yazilabilir: ":fastest" (varsayilan) veya
":cheapest". Ornek: deepseek-ai/DeepSeek-V3-0324:cheapest
"""

import os
import logging

logger = logging.getLogger(__name__)

VARSAYILAN_ADRES = "https://router.huggingface.co/v1"
VARSAYILAN_MODEL = "deepseek-ai/DeepSeek-V3-0324:cheapest"


class _HuggingFaceAdapter:
    @property
    def name(self):
        return "huggingface"

    def create(self, ayar):
        from brain.genel import GenelClient
        ayar = ayar or {}
        # hf_token ses/kimlik katmaninda da kullanilir (voice/speaker_id.py).
        key = (os.environ.get("HF_TOKEN")
               or ayar.get("hf_token") or "")
        if not key:
            return None
        url = (os.environ.get("HF_API_URL")
               or ayar.get("hf_api_url") or VARSAYILAN_ADRES)
        model = (os.environ.get("HF_MODEL")
                 or ayar.get("hf_model") or VARSAYILAN_MODEL)
        try:
            return GenelClient(key, url, model)
        except (ValueError, RuntimeError) as e:
            logger.warning("Hugging Face başlatılamadı: %s", e)
            return None


adapter = _HuggingFaceAdapter()
