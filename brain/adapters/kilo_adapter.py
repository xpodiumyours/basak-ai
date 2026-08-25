"""brain/adapters/kilo_adapter — Kilo Gateway provider adapter (anahtarsız)."""

import logging

logger = logging.getLogger(__name__)


class _KiloAdapter:
    @property
    def name(self):
        return "kilo"

    def create(self, ayar):
        from brain.kilo import KiloClient
        try:
            return KiloClient(model=ayar.get("kilo_model"))
        except Exception as e:
            logger.warning("Kilo başlatılamadı: %s", e)
            return None


adapter = _KiloAdapter()
