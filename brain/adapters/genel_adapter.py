"""brain/adapters/genel_adapter — Kullanicinin ozel (ucretli) saglayicisi."""

import os
import logging

logger = logging.getLogger(__name__)


class _GenelAdapter:
    """genel_api_url + genel_api_key + genel_model varsa katilir.

    Ucunden biri eksikse None doner — bedava kurulum HIC etkilenmez.
    Zincire girince EN SONDA durur (bedavalar once): secici, kayitta
    olmayan ismi listenin sonuna alir. Boylece parali anahtar takilinca
    davranis degismez, sadece saglam bir yedek eklenir.
    """

    @property
    def name(self):
        return "genel"

    def create(self, ayar):
        from brain.genel import GenelClient
        url = (os.environ.get("GENEL_API_URL") or ayar.get("genel_api_url")
               or "")
        key = (os.environ.get("GENEL_API_KEY") or ayar.get("genel_api_key")
               or "")
        model = (os.environ.get("GENEL_MODEL") or ayar.get("genel_model")
                 or "")
        if not (url and key and model):
            return None
        try:
            return GenelClient(key, url, model)
        except (ValueError, RuntimeError) as e:
            logger.warning("Genel saglayici baslatilamadi: %s", e)
            return None


adapter = _GenelAdapter()
