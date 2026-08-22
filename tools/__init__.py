"""tools — Başak'ın tool modülleri.

Her tool ayrı dosyada tanımlıdır:
- definitions.py: JSON schema tool tanımları
- web_search.py: DuckDuckGo araması
- tasks.py: Görev yönetimi
- notes.py: Not yönetimi

TOOLS listesi ve calistir fonksiyonu buradan import edilir.
Araçlar dinamically olarak tools/ klasöründeki *.py dosyalarıyla yüklenir.
"""

import importlib
import pkgutil
import logging

logger = logging.getLogger(__name__)

from tools.definitions import TOOLS
from tools.executor import calistir

__all__ = ["TOOLS", "calistir", "TOOL_MODULES", "FUNCTION_NAME_MAP"]

# --- Dinamik tool yükleme başlatı ---
TOOL_MODULES = {}
FUNCTION_NAME_MAP = {}  # function_name -> execute function mapping


def initialize_tools():
    """tools/ klasöründeki tüm modülleri dinamik yükle."""
    global TOOL_MODULES, FUNCTION_NAME_MAP
    TOOL_MODULES = {}
    FUNCTION_NAME_MAP = {}
    package = __import__('tools')
    for importer, modname, ispkg in pkgutil.iter_modules(package.__path__):
        try:
            mod = importlib.import_module(f'tools.{modname}')
            # Modülden execute fonksiyonunu ve isim bul
            execute_fn = getattr(mod, 'execute', None)
            func_name = getattr(mod, 'FUNCTION_NAME', None)
            # Eğer execute fn varsa ama NAME yoksa, mod adını kullan
            if execute_fn and not func_name:
                func_name = modname
            # Her iki durumdaFUNCTION_NAME_MAP'e ekle
            if execute_fn:
                FUNCTION_NAME_MAP[func_name] = execute_fn
                logger.info(f"Araç yüklendi: {modname} -> {func_name}")
            # Ayrıca modüldeki tüm fonksiyonları da tanı
            for attr_name in dir(mod):
                if attr_name.startswith('_'):
                    continue
                attr = getattr(mod, attr_name)
                if callable(attr) and attr_name not in FUNCTION_NAME_MAP:
                    FUNCTION_NAME_MAP[attr_name] = attr
        except Exception as e:
            logger.warning(f"Araç yüklenemedi: {modname} - {e}")


# Uygulama başlatıldığında otomatik çalıştır
initialize_tools()
