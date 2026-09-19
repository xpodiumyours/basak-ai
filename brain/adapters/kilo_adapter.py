"""brain/adapters/kilo_adapter — Kilo Gateway provider adapter (anahtarsız)."""

import logging
import os

logger = logging.getLogger(__name__)


class _KiloAdapter:
    @property
    def name(self):
        return "kilo"

    def create(self, ayar):
        from brain.kilo import KiloClient
        key = os.environ.get("KILO_API_KEY") or ayar.get("kilo_key") or ""
        try:
            return KiloClient(model=ayar.get("kilo_model"), api_key=key)
        except Exception as e:
            logger.warning("Kilo başlatılamadı: %s", e)
            return None


adapter = _KiloAdapter()
