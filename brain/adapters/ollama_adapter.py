"""brain/adapters/ollama_adapter — Ollama yerel model adapter.

Ollama diğer adapter'lardan farklı: anahtarsız, her zaman mevcut (çalışıyorsa).
_OLLAMA_ADAPTER singleton olarak tutulur.
"""

import logging

logger = logging.getLogger(__name__)

_ollama_client = None


class _OllamaAdapter:
    @property
    def name(self):
        return "yerel"

    def create(self, ayar):
        """Ollama client'ı döndürür (her zaman, musaitlik Kontrolü sonrası)."""
        from brain.ollama import OllamaClient
        global _ollama_client
        if _ollama_client is None:
            _ollama_client = OllamaClient()
        return _ollama_client


adapter = _OllamaAdapter()
