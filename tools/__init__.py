"""tools — Başak'ın tool modülleri.

Araç şemaları definitions.py'de tutulur. Başak artık anahtar kelimeye göre
araç saklamaz: tanımlı araçların tamamı modele sunulur, seçimi model yapar.
İzin ve yazma onayı executor/chat katmanında uygulanmaya devam eder.
"""

import importlib
import pkgutil
import logging

logger = logging.getLogger(__name__)

from tools import definitions as _definitions
from tools.executor import calistir

TOOLS = _definitions.TOOLS

# chat/flow.py geriye uyum için bu sabitleri okumaya devam ediyor. Modül
# tamamen yüklendikten sonra hepsini aynı tam araç setine eşitliyoruz.
_ALL_TOOL_NAMES = {
    t.get("function", {}).get("name")
    for t in TOOLS
    if t.get("function", {}).get("name")
}
_definitions.CORE_TOOL_NAMES = set(_ALL_TOOL_NAMES)
_definitions.SMALL_CORE_TOOL_NAMES = set(_ALL_TOOL_NAMES)
_definitions.EXTENDED_TETIKLERI = {}

__all__ = ["TOOLS", "calistir", "TOOL_MODULES", "FUNCTION_NAME_MAP"]

TOOL_MODULES = {}
FUNCTION_NAME_MAP = {}


def initialize_tools():
    """tools/ klasöründeki çalıştırılabilir araçları dinamik yükle."""
    global TOOL_MODULES, FUNCTION_NAME_MAP
    TOOL_MODULES = {}
    FUNCTION_NAME_MAP = {}
    package = __import__('tools')
    for _importer, modname, _ispkg in pkgutil.iter_modules(package.__path__):
        try:
            mod = importlib.import_module(f'tools.{modname}')
            execute_fn = getattr(mod, 'execute', None)
            func_name = getattr(mod, 'FUNCTION_NAME', None)
            if execute_fn and not func_name:
                func_name = modname
            if execute_fn:
                FUNCTION_NAME_MAP[func_name] = execute_fn
                logger.info(f"Araç yüklendi: {modname} -> {func_name}")
            for attr_name in dir(mod):
                if attr_name.startswith('_'):
                    continue
                attr = getattr(mod, attr_name)
                if callable(attr) and attr_name not in FUNCTION_NAME_MAP:
                    FUNCTION_NAME_MAP[attr_name] = attr
        except Exception as e:
            logger.warning(f"Araç yüklenemedi: {modname} - {e}")


initialize_tools()
