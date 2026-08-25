"""brain/adapters/glm_adapter — GLM (Z.ai) provider adapter."""

import os
import logging

logger = logging.getLogger(__name__)


class _GLMAdapter:
    @property
    def name(self):
        return "glm"

    def create(self, ayar):
        from brain.glm import GLMClient
        key = os.environ.get("ZAI_API_KEY") or ayar.get("zai_key") or ""
        if not key:
            return None
        try:
            return GLMClient(key)
        except ValueError as e:
            logger.warning("GLM başlatılamadı: %s", e)
            return None


adapter = _GLMAdapter()
