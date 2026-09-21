"""brain/adapters/chutes_adapter — Chutes.ai saglayici adaptoru.

Dogrulama: 2026-09-22 (chutes.ai/docs — The Chutes Starter Guide).
OpenAI-uyumlu, arac cagirma destekli:

    base_url = https://llm.chutes.ai/v1

ONEMLI — UCRETLI: Chutes kullanim basina odeme ile calisir (en ucuz model
1M token icin 0,0245 dolar giris / 0,0978 dolar cikis). "Kalici ucretsiz
katman" yoktur; bakiye yuklenmezse istek gecmez. Bu yuzden registry
kartinda "ucretsiz": false yazilidir ve saglayici otomatik bedava zincire
GIRMEZ — bedava duzen degismez.

Anahtar "cpk_" onekiyle baslar. Ayrim: CHUTES_API_KEY / chutes_key.

AYRI NOT (gizlilik): modeller donanim dogrulamali TEE icinde calisir ve
uclar arasi sifreleme vardir; veri saglayicinin duz diskine yazilmaz.
Ileride ucretli omurga secilecekse bu bir ustunluktur.
"""

import os
import logging

logger = logging.getLogger(__name__)

VARSAYILAN_ADRES = "https://llm.chutes.ai/v1"
VARSAYILAN_MODEL = "deepseek-ai/DeepSeek-V4-Flash-0731-TEE"


class _ChutesAdapter:
    @property
    def name(self):
        return "chutes"

    def create(self, ayar):
        from brain.genel import GenelClient
        ayar = ayar or {}
        key = os.environ.get("CHUTES_API_KEY") or ayar.get("chutes_key") or ""
        if not key:
            # Anahtar yoksa saglayici yok: ucretli saglayici kazayla cagrilmaz.
            return None
        url = (os.environ.get("CHUTES_API_URL")
               or ayar.get("chutes_api_url") or VARSAYILAN_ADRES)
        model = (os.environ.get("CHUTES_MODEL")
                 or ayar.get("chutes_model") or VARSAYILAN_MODEL)
        try:
            return GenelClient(key, url, model)
        except (ValueError, RuntimeError) as e:
            logger.warning("Chutes başlatılamadı: %s", e)
            return None


adapter = _ChutesAdapter()
