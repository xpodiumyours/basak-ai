"""brain/adapters/glhf_adapter — glhf.chat saglayici adaptoru.

Dogrulama: 2026-09-22 (freellm.net / glhf.chat). Ucretsiz modeller icin
"sinirsiz" cagri, kart istemez, OpenAI-uyumlu, function calling destekli.
Yalniz 2 model var: meta-llama/Meta-Llama-3.1-70B-Instruct ve
mistralai/Mixtral-8x7B-Instruct-v0.1.

NOT: kucuk ve bagimsiz bir saglayici — resmi limit yayinlanmiyor, haber
vermeden degisebilir. Yedek olarak durur; sirasi olcumle belirlenir.

Adres/model sabit degil: GLHF_API_URL / GLHF_MODEL ya da ayarlar.json'daki
glhf_api_url / glhf_model alanlariyla degistirilebilir.
Mevcut genel OpenAI-uyumlu istemci (brain/genel.py) yeniden kullanilir.
"""

import os
import logging

logger = logging.getLogger(__name__)

VARSAYILAN_ADRES = "https://glhf.chat/api/openai/v1"
VARSAYILAN_MODEL = "meta-llama/Meta-Llama-3.1-70B-Instruct"


class _GlhfAdapter:
    @property
    def name(self):
        return "glhf"

    def create(self, ayar):
        from brain.genel import GenelClient
        ayar = ayar or {}
        key = os.environ.get("GLHF_API_KEY") or ayar.get("glhf_key") or ""
        if not key:
            # Bos yuva: anahtar yoksa saglayici zincire girmez, hata vermez.
            return None
        url = (os.environ.get("GLHF_API_URL")
               or ayar.get("glhf_api_url") or VARSAYILAN_ADRES)
        model = (os.environ.get("GLHF_MODEL")
                 or ayar.get("glhf_model") or VARSAYILAN_MODEL)
        try:
            return GenelClient(key, url, model)
        except (ValueError, RuntimeError) as e:
            logger.warning("glhf.chat başlatılamadı: %s", e)
            return None


adapter = _GlhfAdapter()
