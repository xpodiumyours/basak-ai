"""brain/adapters/nvidia_adapter — NVIDIA NIM provider adapter."""

import os
import logging

logger = logging.getLogger(__name__)


class _NvidiaAdapter:
    @property
    def name(self):
        return "nvidia"

    def create(self, ayar):
        from brain.nvidia import NvidiaClient
        key = os.environ.get("NVIDIA_API_KEY") or ayar.get("nvidia_key") or ""
        if not key:
            return None
        try:
            return NvidiaClient(key, model=ayar.get("nvidia_model"))
        except ValueError as e:
            logger.warning("NVIDIA başlatılamadı: %s", e)
            return None


adapter = _NvidiaAdapter()
