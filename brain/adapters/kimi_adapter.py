"""brain/adapters/kimi_adapter — Kimi yuvasi (KAPALI).

Cifte kapi: (1) ayarlarda "kimi_acik": true, (2) veri karti
data/veri-kartlari/kimi.md MEVCUT. Ikisi de yoksa None doner.
Model adi ayarlardan (kimi_model) acikca verilir, uydurulmaz.
"""

import logging
import os

logger = logging.getLogger(__name__)

BASE = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
KART_YOLU = os.path.join(BASE, "data", "veri-kartlari", "kimi.md")


class _KimiAdapter:
    @property
    def name(self):
        return "kimi"

    def create(self, ayar):
        from brain.kimi import KimiClient
        if not (ayar or {}).get("kimi_acik", False):
            return None
        if not os.path.isfile(KART_YOLU):
            logger.info("Kimi kapali: veri karti yok")
            return None
        key = (os.environ.get("KIMI_API_KEY")
               or (ayar or {}).get("kimi_key") or "")
        model = (os.environ.get("KIMI_MODEL")
                 or (ayar or {}).get("kimi_model") or "")
        if not (key and model):
            return None
        try:
            return KimiClient(key, model)
        except (ValueError, RuntimeError) as e:
            logger.warning("Kimi başlatılamadı: %s", e)
            return None


adapter = _KimiAdapter()
