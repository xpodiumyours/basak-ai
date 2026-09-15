"""brain/adapters/qwen_adapter — QwenCloud (DashScope) provider adapter."""

import os
import logging

logger = logging.getLogger(__name__)


class _QwenAdapter:
    @property
    def name(self):
        return "qwen"

    def create(self, ayar):
        from brain.qwen import QwenClient
        key = os.environ.get("DASHSCOPE_API_KEY") or ayar.get("dashscope_key") or ""
        if not key:
            return None
        model = (os.environ.get("QWEN_MODEL")
                 or (ayar or {}).get("qwen_model") or None)
        try:
            return QwenClient(key, model=model) if model else QwenClient(key)
        except ValueError as e:
            logger.warning("QwenCloud başlatılamadı: %s", e)
            return None


adapter = _QwenAdapter()
