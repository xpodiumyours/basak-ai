"""brain/adapters/gemini_adapter — Gemini provider adapter."""

import os
import logging

logger = logging.getLogger(__name__)


class _GeminiAdapter:
    @property
    def name(self):
        return "gemini"

    def create(self, ayar):
        from brain.gemini import GeminiClient
        key = os.environ.get("GEMINI_API_KEY") or ayar.get("gemini_key") or ""
        if not key:
            return None
        try:
            return GeminiClient(key)
        except ValueError as e:
            logger.warning("Gemini başlatılamadı: %s", e)
            return None


adapter = _GeminiAdapter()
