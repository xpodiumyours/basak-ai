"""brain/adapters/ovh_adapter — OVHcloud AI Endpoints adapteri.

RESMI KAYNAKLAR (2026-10-01 okundu):
- docs.ovhcloud.com/.../ai-endpoints-function-calling: OpenAI SDK ile
  ornek, base_url + tools + tool_choice="auto".
- docs.ovhcloud.com/.../ai-endpoints-capabilities: anahtarlI 400
  istek/dk (proje+model basi), kullanim limiti YOK (yalniz hiz/paket
  siniri); "Data is not stored or shared during or after model use".
- docs.ovhcloud.com/.../ai-endpoints-billing: anahtarli kullanim
  pay-as-you-go (Public Cloud + odeme yontemi; $200 trial kredi).

ANAHTARSIZ ANONIM YOL (2 istek/dk, resmen var) standart OpenAI
istemcisinden ATILAMAZ — 2026-10-01 uc yontemle olcudu:
  1) Authorization basligi YOK -> sunucu anonim kabul eder (429 = kota),
  2) "Bearer " (bos kimlik) -> httpx LocalProtocolError (yasak deger),
  3) bos/dolu sahte kimlik -> 401/403.
Yani SDK her istekte baslik gonderir; bos kimlik gonderilemez. Adapter
bu yuzden yalniz GERCEK anahtarla calisir; anahtar yoksa None doner.

Ortam: OVH_AI_ENDPOINTS_ACCESS_TOKEN (resmi ornek adi), OVH_AI_ENDPOINTS_URL,
OVH_AI_ENDPOINTS_MODEL. ayarlar.json karsiliklari: ovh_key/ovh_url/ovh_model.
"""

import logging
import os

logger = logging.getLogger(__name__)

# 2026-10-01 resmi function-calling ornegindeki adres.
VARSAYILAN_ADRES = "https://oai.endpoints.kepler.ai.cloud.ovh.net/v1"
# gpt-oss-120b: resmi getting-started ornegi ve emekliye ayrilma
# listesinde degil. Mistral-Nemo 2026-11-04'te kalkiyor — secilmedi.
VARSAYILAN_MODEL = "gpt-oss-120b"


class _OvhAdapter:
    @property
    def name(self):
        return "ovh"

    def create(self, ayar):
        from brain.genel import GenelClient
        key = (os.environ.get("OVH_AI_ENDPOINTS_ACCESS_TOKEN")
               or ayar.get("ovh_key") or "")
        if not key:
            logger.info(
                "OVH anahtari yok (OVH_AI_ENDPOINTS_ACCESS_TOKEN) — "
                "ucretli servis, otomatik bedava zincire kapali")
            return None
        try:
            return GenelClient(
                api_key=key,
                base_url=(os.environ.get("OVH_AI_ENDPOINTS_URL")
                          or ayar.get("ovh_url") or VARSAYILAN_ADRES),
                model=(os.environ.get("OVH_AI_ENDPOINTS_MODEL")
                       or ayar.get("ovh_model") or VARSAYILAN_MODEL),
            )
        except Exception as e:
            logger.warning("OVH baslatilamadi: %s", e)
            return None


adapter = _OvhAdapter()
