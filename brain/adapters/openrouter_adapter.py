"""brain/adapters/openrouter_adapter — OpenRouter provider adapter."""

import os
import logging

logger = logging.getLogger(__name__)


class _OpenRouterAdapter:
    @property
    def name(self):
        return "openrouter"

    def create(self, ayar):
        from brain.openrouter import OpenRouterClient
        key = (os.environ.get("OPENROUTER_API_KEY")
               or ayar.get("openrouter_key") or "")
        if not key:
            return None
        # OpenRouter free katalog calisma aninda secilir (_model_bul);
        # sabit kilit yok: OPENROUTER_MODEL / openrouter_model ile ezilebilir.
        model = (os.environ.get("OPENROUTER_MODEL")
                 or (ayar or {}).get("openrouter_model") or None)
        try:
            return OpenRouterClient(key, model=model) if model else OpenRouterClient(key)
        except ValueError as e:
            logger.warning("OpenRouter başlatılamadı: %s", e)
            return None


adapter = _OpenRouterAdapter()
