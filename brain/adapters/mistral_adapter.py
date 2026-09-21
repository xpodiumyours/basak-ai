"""brain/adapters/mistral_adapter — Mistral (La Plateforme) saglayici adaptoru.

Ucretsiz "Experiment" plani (dogrulama: 2026-09-22, console.mistral.ai +
freellm.net): ~1 milyar token/ay, ~1 istek/sn, 500K token/dk.
Kart ISTEMEZ; TELEFON DOGRULAMASI ister. OpenAI-uyumlu, arac cagirma
(function calling) destekli.

UYARI (gizlilik): resmi belgeye gore ucretsiz katmanda veri, kullanici
panelden kapatmadan model gelistirmesi icin kullanilabilir. Kapatma yeri:
Mistral panel > Settings > Privacy.

Adres/model sabit degil: MISTRAL_API_URL / MISTRAL_MODEL ile ya da
ayarlar.json'daki mistral_api_url / mistral_model ile degistirilebilir.
Mevcut genel OpenAI-uyumlu istemci (brain/genel.py) yeniden kullanilir;
yeni bir istemci sinifi yazilmaz.
"""

import os
import logging

logger = logging.getLogger(__name__)

VARSAYILAN_ADRES = "https://api.mistral.ai/v1"
# 2026-09-22 DUZELTME: once burada "mistral-small-4" yaziyordu ama o model
# ID'si hesapta YOK ("Invalid model" verdi). Liste senin anahtarinla
# sorgulanarak cikarildi. Genel sohbet: "mistral-small-latest" (kararli
# takma ad); daha guclu: "mistral-medium-latest"; kod: "codestral-latest".
VARSAYILAN_MODEL = "mistral-small-latest"


class _MistralAdapter:
    @property
    def name(self):
        return "mistral"

    def create(self, ayar):
        from brain.genel import GenelClient
        ayar = ayar or {}
        key = os.environ.get("MISTRAL_API_KEY") or ayar.get("mistral_key") or ""
        if not key:
            # Bos yuva: anahtar yoksa saglayici zincire girmez, hata vermez.
            return None
        url = (os.environ.get("MISTRAL_API_URL")
               or ayar.get("mistral_api_url") or VARSAYILAN_ADRES)
        model = (os.environ.get("MISTRAL_MODEL")
                 or ayar.get("mistral_model") or VARSAYILAN_MODEL)
        try:
            return GenelClient(key, url, model)
        except (ValueError, RuntimeError) as e:
            logger.warning("Mistral başlatılamadı: %s", e)
            return None


adapter = _MistralAdapter()
