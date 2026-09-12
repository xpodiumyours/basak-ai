"""chat — Sohbet paketi.

2026-09-13: araç katmanı söküldü, `_chat_legacy.py` kaldırıldı. Paket
artık dört küçük modülden oluşur:

  chat.prompts  → modele verilen sabit metinler
  chat.context  → dosya yolları, geçmiş penceresi, kalıcı hafıza
  chat.gate     → cevap temizliği ve dil kontrolü
  chat.flow     → ana akış (mesaj_isle)
  chat.oturum   → eski sohbetlerin listesi/arşivi
"""

from chat.flow import mesaj_isle  # noqa: F401
from chat.gate import temizle, dil_kontrol, ingilizce_sizinti_mi  # noqa: F401
from chat.context import (  # noqa: F401
    BASE,
    HISTORY_FILE,
    SETTINGS_FILE,
    KNOWLEDGE_DIR,
    OBSIDIAN_DIR,
    OTURUM_ID,
    MAX_HISTORY,
    GECMIS_KILO_LIMITI,
    yukle,
    kaydet,
    gecmis_pencere,
    temizle_history,
    onem_puanla,
    hafiza_al,
    ilgili_anilar,
    init_cache,
)
from chat import oturum  # noqa: F401

__all__ = [
    "mesaj_isle",
    "temizle", "dil_kontrol", "ingilizce_sizinti_mi",
    "BASE", "HISTORY_FILE", "SETTINGS_FILE", "KNOWLEDGE_DIR",
    "OBSIDIAN_DIR", "OTURUM_ID", "MAX_HISTORY", "GECMIS_KILO_LIMITI",
    "yukle", "kaydet", "gecmis_pencere", "temizle_history",
    "onem_puanla", "hafiza_al", "ilgili_anilar", "init_cache",
    "oturum",
]
