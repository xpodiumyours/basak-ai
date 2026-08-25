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
        try:
            return CohereClient(key)
        except ValueError as e:
            logger.warning("Cohere başlatılamadı: %s", e)
            return None


adapter = _CohereAdapter()
