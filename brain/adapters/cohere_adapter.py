"""brain/adapters/cohere_adapter — Cohere provider adapter."""

import os
import logging

logger = logging.getLogger(__name__)


class _CohereAdapter:
    @property
    def name(self):
        return "cohere"

    def create(self, ayar):
        from brain.cohere import CohereClient
        key = os.environ.get("COHERE_API_KEY") or ayar.get("cohere_key") or ""
        if not key:
            return None
        model = (os.environ.get("COHERE_MODEL")
                 or (ayar or {}).get("cohere_model") or None)
        try:
            if model:
                return CohereClient(key, model=model)
            return CohereClient(key)
        except ValueError as e:
            logger.warning("Cohere başlatılamadı: %s", e)
            return None


adapter = _CohereAdapter()
