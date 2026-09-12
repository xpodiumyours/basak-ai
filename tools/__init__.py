"""tools — Başak'ın tool modülleri.

Tanımlı güvenli araçların tamamı modele sunulur; seçim modele aittir. Araç
açıklamaları yalnız ne yapabildiklerini söyler, hangi cümlede kullanılacağını
dayatmaz. İzin ve yazma onayı executor/chat katmanında uygulanır.
"""

import importlib
import pkgutil
import logging

logger = logging.getLogger(__name__)

from tools import definitions as _definitions
from tools.executor import calistir

TOOLS = _definitions.TOOLS

_ALL_TOOL_NAMES = {
    t.get("function", {}).get("name")
    for t in TOOLS
    if t.get("function", {}).get("name")
}
_definitions.CORE_TOOL_NAMES = set(_ALL_TOOL_NAMES)
_definitions.SMALL_CORE_TOOL_NAMES = set(_ALL_TOOL_NAMES)
_definitions.EXTENDED_TETIKLERI = {}

# Şema açıklamaları tetikleyici/prompt değildir; yalnız kabiliyeti tarif eder.
_ARAC_ACIKLAMALARI = {
    "sayfa_oku": "Verilen web sayfasının içeriğini oku.",
    "web_search": "İnternette güncel bilgi ara.",
    "add_task": "Yeni görev ekle.",
    "list_tasks": "Mevcut görevleri listele.",
    "complete_task": "Bir görevi tamamlandı olarak işaretle.",
    "save_note": "Kalıcı not kaydet.",
    "deftere_kaydet": "Ortak deftere kayıt ekle.",
    "read_file": "Verilen dosyanın içeriğini oku.",
    "write_file_tool": "Dosyaya yaz veya yeni dosya oluştur; izin kuralları uygulama tarafından denetlenir.",
    "list_files": "Verilen klasördeki dosyaları listele.",
    "ac_uygulama": "İzin verilen yerel uygulamayı aç.",
    "get_reminders": "Hatırlatmaları ve ilgili görevleri getir.",
    "video_analyze": "Video veya ses dosyasını analiz et.",
    "image_analyze": "Görüntüyü analiz et.",
    "model_stats": "Model kullanım ve çalışma istatistiklerini getir.",
    "git_durum": "Bir projenin git durumunu ölç.",
    "belge_ara": "Proje belgelerinde metin ara.",
    "dosya_bilgi": "Bir dosyanın varlık, boyut ve değişim bilgisini getir.",
    "is_ac": "Kalıcı ve adımlı bir iş kaydı oluştur.",
    "is_liste": "Kalıcı iş kuyruğunu listele.",
    "is_onayla": "Onay bekleyen kalıcı işi onayla.",
}
for _tool in TOOLS:
    _func = _tool.get("function", {})
    _ad = _func.get("name")
    if _ad in _ARAC_ACIKLAMALARI:
        _func["description"] = _ARAC_ACIKLAMALARI[_ad]

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
