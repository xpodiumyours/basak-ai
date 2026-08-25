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
        try:
            return OpenRouterClient(key)
        except ValueError as e:
            logger.warning("OpenRouter başlatılamadı: %s", e)
            return None


adapter = _OpenRouterAdapter()
