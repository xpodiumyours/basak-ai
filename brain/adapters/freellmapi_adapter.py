"""FreeLLMAPI ortak adresi ve anahtari; saglayici anahtarlari gateway'dedir.

Kaynak: tashfeenahmed/freellmapi docs/en/api/01-rest-api.md.
FREELLMAPI_URL + FREELLMAPI_API_KEY birlikte verilince etkinlesir.
FREELLMAPI_MODEL, gateway'de kurulmus ucretsiz bir model/zinciri secer.
"""

import logging
import os
from urllib.parse import urlsplit

logger = logging.getLogger(__name__)


def gateway_adresi(url):
    """HTTPS adresini /v1 ile bitirir; yerel HTTP yalniz gelistirmede."""
    parcalar = urlsplit(url.strip())
    yerel = parcalar.hostname in ("localhost", "127.0.0.1", "::1")
    uretim = bool(os.environ.get("VERCEL") or os.environ.get("BASAK_URETIM"))
    if (not parcalar.hostname or parcalar.username or parcalar.password
            or parcalar.query or parcalar.fragment
            or (parcalar.scheme != "https"
                and not (parcalar.scheme == "http" and yerel and not uretim))):
        raise ValueError("FreeLLMAPI icin kimlik bilgisi icermeyen HTTPS adresi gerekli")
    temiz = url.strip().rstrip("/")
    return temiz if parcalar.path.rstrip("/").endswith("/v1") else temiz + "/v1"


class _FreeLLMAPIAdapter:
    @property
    def name(self):
        return "freellmapi"

    def create(self, ayar):
        from brain.genel import GenelClient

        ayar = ayar or {}
        url = (os.environ.get("FREELLMAPI_URL") or ayar.get("freellmapi_url") or "").strip()
        key = (os.environ.get("FREELLMAPI_API_KEY") or ayar.get("freellmapi_key") or "").strip()
        # Deployment-scoped smart-routing override; the existing gateway
        # model configuration stays intact for instant rollback.
        model = (os.environ.get("BASAK_FREELLMAPI_ROUTING_MODEL")
                 or os.environ.get("FREELLMAPI_MODEL")
                 or ayar.get("freellmapi_model") or "auto:smart").strip()
        if not url and not key:
            return None
        if not url or not key:
            raise ValueError("FreeLLMAPI adresi ve ortak anahtari birlikte gerekli")
        try:
            return GenelClient(key, gateway_adresi(url), model)
        except (ValueError, RuntimeError):
            # URL veya anahtar hata metnine girebilir: sirli istisnayi loglama.
            logger.warning("FreeLLMAPI baglantisi baslatilamadi; adres ve ortak anahtari kontrol edin")
            return None


adapter = _FreeLLMAPIAdapter()
