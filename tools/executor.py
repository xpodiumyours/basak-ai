"""tools/executor.py — Tool çalıştırıcı (Dispatcher Pattern).

Tool ismine göre ilgili fonksiyonu çağırır ve sonucu döndürür.
Her çalışma arac.log'a yazılır.

Yeni araç eklemek: TOOL_MAP'e entry ekle, bitti.
"""

import os

from tools.web_search import web_search, sayfa_oku
from tools.tasks import add_task, list_tasks, complete_task
from tools.notes import save_note, deftere_kaydet
from tools.file_ops import read_file, write_file_ops, list_files
from tools.app_launcher import ac_uygulama
from tools.reminders import bugunku_hatirlatmalar
from tools.video_analyzer import video_analyze
from tools.olcum import git_durum, belge_ara, dosya_bilgi
from tools.tool_logger import log_tool_call
from tools.permissions import calistirilabilir_mi


# ── Tool Context: her tool'un ihtiyac duydugu yol/bilgi ──────────────
# --- ARGUMAN SANITIZATION ---
import re as _re_mod
_IZINLI_PROJELER = {"basak", "vixrex", "numeramatch", "xses"}

def _sanitize_args(tool_name, args):
    if not isinstance(args, dict):
        return args
    # 2026-09-09: proje BEYAZ LISTE disiysa BURADA "basak"a cevrilmez.
    # Neden: test_savunma bekler ki bilinmeyen proje "Bilinmeyen proje"
    # hatasi versin; sessizce basak'a cevirmek enjeksiyonu gizler.
    # Beyaz liste kontrolu tools/olcum.py'de (_kok) zaten vardir.
    if tool_name == "dosya_bilgi":
        yol = str(args.get("yol", "")).replace("..", "")
        args["yol"] = yol
    if tool_name in ("read_file", "write_file_tool"):
        path = str(args.get("path", ""))
        if ".." in path:
            args["path"] = path.replace("..", "")
    for key in list(args.keys()):
        val = args[key]
        if isinstance(val, str) and len(val) > 200:
            args[key] = val[:200]
    return args


class ToolContext:
    """Tool çalıştırma bağlamı — dispatcher'a iletilir."""
    def __init__(self, knowledge_dir="", gorevler_file=""):
        self.knowledge_dir = knowledge_dir
        self.gorevler_file = gorevler_file
        self.base_dir = os.path.dirname(knowledge_dir) if knowledge_dir else os.getcwd()
        self.defter_dir = os.path.join(self.base_dir, "defter")


# ── TOOL_MAP: isim → (fonksiyon, argüman şablonu) ───────────────────
# Her entry: (fonksiyon, args_dict) — args_dict fonksiyona ** ile açılır.
# Değer olarak callable ise (fonksiyon,) — argümanlar context'ten gelir.
# Değer olarak dict ise (fonksiyon, {arg: (args_key, default)}) — mapping.

def _url_arg(a, _c):
    return (a.get("url", ""),)
def _query_arg(a, _c):
    return (a.get("query", ""),)
def _text_arg(a, _c):
    return (a.get("text", ""),)
def _task_id_arg(a, _c):
    return (a.get("task_id", 0),)
def _note_args(a, _c):
    return (a.get("title", ""), a.get("content", ""), _c.knowledge_dir)
def _deftere_args(a, _c):
    return (a.get("title", ""), a.get("content", ""), _c.defter_dir)
def _deftere_kwargs(a, _c):
    return (), {"kim": a.get("kim", "basak"), "tip": a.get("tip", "alinti"),
               "omur": a.get("omur", "30g"), "kaynak": a.get("kaynak", "sohbet")}
def _read_file_args(a, _c):
    return (a.get("path", ""), _c.base_dir)
def _write_file_args(a, _c):
    return (a.get("path", ""), a.get("content", ""), _c.base_dir)
def _list_files_args(a, _c):
    return (a.get("folder", ""), _c.base_dir)
def _reminders_args(a, _c):
    return (_c.knowledge_dir, _c.gorevler_file)
def _ac_uygulama_args(a, _c):
    return (a.get("uygulama", ""), a.get("parametre", ""))
def _video_args(a, _c):
    return (a.get("video_yolu", ""),)
def _image_args(a, _c):
    return (a.get("goruntu_yolu", ""),)
def _image_kwargs(a, _c):
    return (), {"soru": a.get("soru")}
def _model_stats_args(a, _c):
    return ()  # handler içinde çözülür
def _olcum_args(a, _c):
    return (a.get("proje", ""),)
def _belge_ara_args(a, _c):
    return (a.get("proje", ""), a.get("sorgu", ""))
def _dosya_bilgi_args(a, _c):
    return (a.get("proje", ""), a.get("yol", ""))


def _run_simple(fn, args_fn):
    """Basit tool: fn(*args_fn(a, c))."""
    def handler(a, c):
        return fn(*args_fn(a, c))
    return handler


def _run_with_kwargs(fn, args_fn, kwargs_fn):
    """Kwargs alan tool: fn(*args, **kwargs)."""
    def handler(a, c):
        args = args_fn(a, c)
        _, kwargs = kwargs_fn(a, c)
        return fn(*args, **kwargs)
    return handler


def _run_model_stats(a, _c):
    """model_stats özel handler: model parametresine göre dal."""
    from brain.stats import model_stats_al
    istat = model_stats_al()
    model = a.get("model")
    son_saat = a.get("son_saat", 24)
    if model:
        ozet = istat.ozet(model=model, son_saat=son_saat)
    else:
        ozet = istat.siralama(son_saat=son_saat)
    return {"result": ozet}


def _run_deftere(a, c):
    """deftere_kaydet: positional + kwargs karışımı."""
    args = _deftere_args(a, c)
    _, kwargs = _deftere_kwargs(a, c)
    return deftere_kaydet(*args, **kwargs)


def _run_image(a, c):
    """image_analyze: lazy import + kwargs."""
    from tools.image_analyzer import image_analyze
    args = _image_args(a, c)
    _, kwargs = _image_kwargs(a, c)
    return image_analyze(*args, **kwargs)


# ── TOOL_MAP: tool_name → handler(arguments, context) → dict ─────────
TOOL_MAP = {
    "sayfa_oku":       _run_simple(sayfa_oku, _url_arg),
    "web_search":      _run_simple(web_search, _query_arg),
    "add_task":        _run_simple(add_task, _text_arg),  # gorevler_file handler'da
    "list_tasks":      lambda a, c: list_tasks(c.gorevler_file),
    "complete_task":   _run_simple(complete_task, _task_id_arg),
    "save_note":       _run_simple(save_note, _note_args),
    "deftere_kaydet":  _run_deftere,
    "read_file":       _run_simple(read_file, _read_file_args),
    "write_file_tool": _run_simple(write_file_ops, _write_file_args),
    "list_files":      _run_simple(list_files, _list_files_args),
    "get_reminders":   lambda a, c: bugunku_hatirlatmalar(c.knowledge_dir, c.gorevler_file),
    "ac_uygulama":     _run_simple(ac_uygulama, _ac_uygulama_args),
    "video_analyze":   _run_simple(video_analyze, _video_args),
    "image_analyze":   _run_image,
    "model_stats":     _run_model_stats,
    "git_durum":       _run_simple(git_durum, _olcum_args),
    "belge_ara":       _run_simple(belge_ara, _belge_ara_args),
    "dosya_bilgi":     _run_simple(dosya_bilgi, _dosya_bilgi_args),
}

# add_task icin ozel handler (gorevler_file gerekli)
TOOL_MAP["add_task"] = lambda a, c: add_task(a.get("text", ""), c.gorevler_file)
TOOL_MAP["complete_task"] = lambda a, c: complete_task(a.get("task_id", 0), c.gorevler_file)


def calistir(tool_name: str, arguments: dict, knowledge_dir: str = "",
             gorevler_file: str = "") -> dict:
    """Tool'u çalıştırır ve sonucu döndürür.

    Dispatcher pattern: TOOL_MAP'ten handler'ı bul, çalıştır.
    Yeni araç eklemek: TOOL_MAP'e entry ekle, bitti.

    Args:
        tool_name: Çalıştırılacak tool'un ismi.
        arguments: Tool parametreleri (dict).
        knowledge_dir: knowledge/ klasörü yolu.
        gorevler_file: Görevler dosyası yolu.

    Returns:
        Tool sonucu (dict). Hata olursa {"error": str}.
    """
    base_dir = os.path.dirname(knowledge_dir) if knowledge_dir else os.getcwd()

    # P3 Permission Layer
    if not calistirilabilir_mi(tool_name):
        from tools.permissions import engel_sebebi
        sebep = engel_sebebi(tool_name) or "bilinmeyen engel"
        log_tool_call(tool_name, arguments,
                      {"error": "izin engeli"}, base_dir)
        return {"error": "Güvenlik engeli: " + sebep}

    # Dispatcher: TOOL_MAP'ten handler'ı bul ve çalıştır
    handler = TOOL_MAP.get(tool_name)
    if handler is None:
        return {"error": f"Tool eşleştirilemedi: {tool_name}"}

    arguments = _sanitize_args(tool_name, arguments)

    ctx = ToolContext(knowledge_dir, gorevler_file)
    try:
        sonuc = handler(arguments, ctx)
    except Exception as e:
        sonuc = {"error": f"Tool hatası ({tool_name}): {str(e)[:200]}"}

    # Loglama
    log_tool_call(tool_name, arguments, sonuc, base_dir)

    return sonuc
