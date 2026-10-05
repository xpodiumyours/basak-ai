"""brain/adapters/llm7_adapter — LLM7.io adapterı.

RESMİ KAYNAKLAR (2026-10-02 okundu):
- docs.llm7.io/api-reference/introduction.md: "## Base URL
  https://api.llm7.io/v1"; "The API uses Bearer tokens for
  authentication." OpenAPI servers alanı da aynı.
- docs.llm7.io/limits.md: Free token 1 istek/sn, 60 istek/dk,
  250 istek/saat, 100.000 token/24 saat. Gunluk ISTEK limiti yok.
  "Free-token quotas are provided at no charge and may be reduced
  without notice..." (sabit taahhüt değil).
- docs.llm7.io/guides/function-calling.md: "Function calling depends
  on the selected model. Use the Models API to find models with
  `tools_calling: true`." Belgelenen tek tool_choice değeri "auto".
- api.llm7.io/v1/models (canlı katalog): DeepSeek-V4-Flash-0731 →
  tier="turbo", tools_calling=true, context_window 400.000.
  GLM-5.3-Flash → tier="turbo", tools_calling=true.

Anahtar/hesap: dash.llm7.io üzerinden ücretsiz token alınır; resmî
metinde kart veya telefon şartı YER ALMIYOR.

Ortam: LLM7_API_KEY, LLM7_MODEL, LLM7_API_URL.
ayarlar.json: llm7_key / llm7_model. Anahtar yoksa None döner —
boş yuvadır, arıza değil (create_providers kalıbı).

NOT: tool_choice "required" gönderilmez. LLM7 resmî dokümanı
yalnız "auto" belgeler; zorunlu turda "auto" gönderilir ve model
metin yazarsa bu Brain'de başarısız sayılır (ajan_tool_mode
auto_enforced) → zincir sıradaki sağlayıcıya geçer.
"""

import logging
import os

logger = logging.getLogger(__name__)

VARSAYILAN_ADRES = "https://api.llm7.io/v1"
# api.llm7.io/v1/models katalogundan doğrulandı (2026-10-02):
# tier="turbo" (ücretsiz katmana erişilebilir), tools_calling=true.
VARSAYILAN_MODEL = "DeepSeek-V4-Flash-0731"


class _Llm7Adapter:
    @property
    def name(self):
        return "llm7"

    def create(self, ayar):
        from brain.genel import GenelClient
        key = (os.environ.get("LLM7_API_KEY")
               or ayar.get("llm7_key") or "")
        if not key:
            logger.info("LLM7 anahtari yok (LLM7_API_KEY)")
            return None
        try:
            return GenelClient(
                api_key=key,
                base_url=(os.environ.get("LLM7_API_URL")
                          or ayar.get("llm7_url") or VARSAYILAN_ADRES),
                model=(os.environ.get("LLM7_MODEL")
                       or ayar.get("llm7_model") or VARSAYILAN_MODEL),
            )
        except Exception as e:
            logger.warning("LLM7 baslatilamadi: %s", e)
            return None


adapter = _Llm7Adapter()