"""brain/adapters/sambanova_adapter — SambaNova Cloud adapteri.

RESMI KAYNAKLAR (2026-10-01 okundu):
- docs.sambanova.ai/.../models/rate-limits: Free Tier (odeme yontemi
  OLMAYAN hesaplar): 20 istek/dk, 20 istek/gun, 200.000 token/gun
  (model basi). Developer Tier icin odeme yontemi gerekir.
- docs.sambanova.ai/.../features/function-calling: tool_choice
  auto/required/none resmen desteklenir; desteklenen modeller arasında
  Meta-Llama-3.3-70B-Instruct, DeepSeek-V3.1, gpt-oss-120b.
- docs.sambanova.ai (integrations): OpenAI uyumlu taban adres
  https://api.sambanova.ai/v1.

Ortam: SAMBANOVA_API_KEY, SAMBANOVA_MODEL. ayarlar.json:
sambanova_key / sambanova_model. Anahtar yoksa None doner (zincir
musaitlik kontroluyle eler).
"""

import logging
import os

logger = logging.getLogger(__name__)

VARSAYILAN_ADRES = "https://api.sambanova.ai/v1"
# 2026-09-30 free tier uretim listesinde + function-calling
# desteklenenler listesinde birlikte var: guclu genel model.
VARSAYILAN_MODEL = "DeepSeek-V3.1"


class _SambaNovaAdapter:
    @property
    def name(self):
        return "sambanova"

    def create(self, ayar):
        from brain.genel import GenelClient
        key = (os.environ.get("SAMBANOVA_API_KEY")
               or ayar.get("sambanova_key") or "")
        if not key:
            logger.info("SambaNova anahtari yok (SAMBANOVA_API_KEY)")
            return None
        try:
            return GenelClient(
                api_key=key,
                base_url=(os.environ.get("SAMBANOVA_API_URL")
                          or ayar.get("sambanova_url") or VARSAYILAN_ADRES),
                model=(os.environ.get("SAMBANOVA_MODEL")
                       or ayar.get("sambanova_model") or VARSAYILAN_MODEL),
            )
        except Exception as e:
            logger.warning("SambaNova baslatilamadi: %s", e)
            return None


adapter = _SambaNovaAdapter()
