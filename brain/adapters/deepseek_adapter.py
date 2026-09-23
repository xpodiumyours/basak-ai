"""brain/adapters/deepseek_adapter — DeepSeek yuvasi (KAPALI).

Cifte kapi: (1) ayarlarda "deepseek_acik": true, (2) veri karti
<durum>/veri-kartlari/deepseek.md MEVCUT. Ikisi de yoksa None doner —
ayarlardaki deepseek_key TEK BASINA zincire sokmaz (ucretli cagri
varsayilan engelli + kartsiz saglayiciya hassas veri gitmez).
"""

import logging
import os

from chat.kimlik import durum_yolu

logger = logging.getLogger(__name__)

# None = durum kokunun veri-kartlari/deepseek.md dosyasi; test patch
# edebilir. Modul yuklenirken sabitlenmez (BASAK_STATE_DIR degisiyor).
KART_YOLU = None


def kart_yolu():
    """Veri karti dosyasi: durum kokunun veri-kartlari/ alti."""
    return KART_YOLU or os.path.join(
        durum_yolu("veri-kartlari", olustur=False), "deepseek.md")


class _DeepSeekAdapter:
    @property
    def name(self):
        return "deepseek"

    def create(self, ayar):
        from brain.deepseek import DeepSeekClient
        if not (ayar or {}).get("deepseek_acik", False):
            return None
        if not os.path.isfile(kart_yolu()):
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
