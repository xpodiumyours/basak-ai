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
        # Model kilidi yok: ayarlar.json -> glm_model veya ZAI_MODEL.
        model = (os.environ.get("ZAI_MODEL") or (ayar or {}).get("glm_model")
                 or None)
        try:
            return GLMClient(key, model=model) if model else GLMClient(key)
        except ValueError as e:
            logger.warning("GLM başlatılamadı: %s", e)
            return None


adapter = _GLMAdapter()
