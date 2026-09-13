"""tools — Başak'ın araç çalıştırıcısı."""

import logging
import os

from tools.definitions import TOOLS, TANINMIS_TOOLLAR  # noqa: F401

logger = logging.getLogger(__name__)
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KNOWLEDGE_DIR = os.path.join(BASE, "knowledge")
GOREVLER_FILE = os.path.join(BASE, "gorevler.json")


def _knowledge_altinda_mi(yol):
    try:
        if not yol or os.path.isabs(yol):
            return False
        hedef = os.path.realpath(os.path.join(BASE, yol))
        kok = os.path.realpath(KNOWLEDGE_DIR)
        return os.path.commonpath([hedef, kok]) == kok
    except (OSError, ValueError):
        return False


def calistir(tool_name, args):
    if tool_name not in TANINMIS_TOOLLAR:
        logger.info("Taninmayan arac reddedildi: %s", tool_name)
        return {"error": "'%s' diye bir arac yok." % tool_name}
    args = args or {}
    try:
        if tool_name == "web_search":
            from tools import web_search as ws
            return ws.web_search(str(args.get("query", "")))
        if tool_name == "sayfa_oku":
            from tools import web_search as ws
            return ws.sayfa_oku(str(args.get("url", "")))
        if tool_name == "read_file":
            from tools import file_ops
            return file_ops.read_file(str(args.get("path", "")), BASE)
        if tool_name == "list_files":
            from tools import file_ops
            return file_ops.list_files(str(args.get("folder", "")), BASE)
        if tool_name == "git_durum":
            from tools import olcum
            return olcum.git_durum(str(args.get("proje", "")))
        if tool_name == "belge_ara":
            from tools import olcum
            return olcum.belge_ara(str(args.get("proje", "")), str(args.get("sorgu", "")))
        if tool_name == "dosya_bilgi":
            from tools import olcum
            return olcum.dosya_bilgi(str(args.get("proje", "")), str(args.get("yol", "")))
        if tool_name == "write_file_tool":
            from tools import file_ops
            yol = str(args.get("path", "")).strip()
            if not _knowledge_altinda_mi(yol):
                return {"error": "Yazma yalnız knowledge/ altına izinli."}
            return file_ops.write_file_ops(yol, str(args.get("content", "")), BASE)
        if tool_name == "get_reminders":
            from tools import reminders
            return reminders.bugunku_hatirlatmalar(KNOWLEDGE_DIR, GOREVLER_FILE)
        if tool_name == "add_task":
            from tools import tasks
            return tasks.add_task(str(args.get("text", "")), GOREVLER_FILE)
        if tool_name == "list_tasks":
            from tools import tasks
            return tasks.list_tasks(GOREVLER_FILE)
        if tool_name == "complete_task":
            from tools import tasks
            try:
                task_id = int(args.get("task_id"))
            except (TypeError, ValueError):
                return {"error": "Gorev numarasi gecersiz."}
            return tasks.complete_task(task_id, GOREVLER_FILE)
        if tool_name == "ac_uygulama":
            from tools import app_launcher
            return app_launcher.ac_uygulama(
                str(args.get("uygulama", "")),
                str(args.get("parametre", "") or ""))
        if tool_name == "image_analyze":
            from tools import image_analyzer
            return image_analyzer.image_analyze(str(args.get("path", "")), str(args.get("soru", "") or "") or None)
    except Exception as e:
        logger.warning("Arac hatasi (%s): %s", tool_name, e)
        return {"error": "Arac calismadi: %s" % str(e)[:150]}
    return {"error": "'%s' calistirilamadi." % tool_name}
