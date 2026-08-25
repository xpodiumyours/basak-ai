"""brain/adapters/groq_adapter — Groq provider adapter."""

import os
import logging

logger = logging.getLogger(__name__)


class _GroqAdapter:
    """Groq provider adapter — GROQ_API_KEY veya ayarlar.json'dan."""

    @property
    def name(self):
        return "groq"

    def create(self, ayar):
        from brain.groq import GroqClient, MODELLER
        key = os.environ.get("GROQ_API_KEY") or ayar.get("groq_key") or ""
        model = ayar.get("groq_model", MODELLER["varsayilan"])
        if not key:
            return None
        try:
            client = GroqClient(key, model)
            return client
        except ValueError as e:
            logger.warning("Groq başlatılamadı: %s", e)
            return None


adapter = _GroqAdapter()
