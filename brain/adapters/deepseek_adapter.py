"""brain/adapters/deepseek_adapter — DeepSeek yuvasi (KAPALI).

Cifte kapi: (1) ayarlarda "deepseek_acik": true, (2) veri karti
data/veri-kartlari/deepseek.md MEVCUT. Ikisi de yoksa None doner —
ayarlardaki deepseek_key TEK BASINA zincire sokmaz (ucretli cagri
varsayilan engelli + kartsiz saglayiciya hassas veri gitmez).
"""

import logging
import os

logger = logging.getLogger(__name__)

BASE = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
KART_YOLU = os.path.join(BASE, "data", "veri-kartlari", "deepseek.md")


class _DeepSeekAdapter:
    @property
    def name(self):
        return "deepseek"

    def create(self, ayar):
        from brain.deepseek import DeepSeekClient
        if not (ayar or {}).get("deepseek_acik", False):
            return None
        if not os.path.isfile(KART_YOLU):
            logger.info("DeepSeek kapali: veri karti yok")
            return None
        key = (os.environ.get("DEEPSEEK_API_KEY")
               or (ayar or {}).get("deepseek_key") or "")
        if not key:
            return None
        try:
            return DeepSeekClient(key)
        except (ValueError, RuntimeError) as e:
            logger.warning("DeepSeek başlatılamadı: %s", e)
            return None


adapter = _DeepSeekAdapter()
