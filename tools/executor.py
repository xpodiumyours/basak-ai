"""tools/executor.py — Tool çalıştırıcı.

Tool ismine göre ilgili fonksiyonu çağırır ve sonucu döndürür.
Tek bir sorumluluk: tool ismini fonksiyona eşleştirmek.
"""

from tools.web_search import web_search
from tools.tasks import add_task, list_tasks, complete_task
from tools.notes import save_note

# Tool isimlerini fonksiyonlara eşleştiren harita
TOOL_MAP = {
    "web_search": web_search,
    "add_task": add_task,
    "list_tasks": list_tasks,
    "complete_task": complete_task,
    "save_note": save_note,
}


def calistir(tool_name: str, arguments: dict, knowledge_dir: str = "",
             gorevler_file: str = "") -> dict:
    """Tool'u çalıştırır ve sonucu döndürür.

    Args:
        tool_name: Çalıştırılacak tool'un ismi.
        arguments: Tool parametreleri (dict).
        knowledge_dir: knowledge/ klasörü yolu (sadece save_note için gerekli).
        gorevler_file: Görevler dosyası yolu (görev tool'ları için gerekli).

    Returns:
        Tool sonucu (dict). Hata olursa {"error": str}.
    """
    if tool_name not in TOOL_MAP:
        return {"error": f"Bilinmeyen tool: {tool_name}"}

    # Tool'a göre doğru parametreleri hazırla
    if tool_name == "web_search":
        return web_search(arguments.get("query", ""))
    elif tool_name == "add_task":
        return add_task(arguments.get("text", ""), gorevler_file)
    elif tool_name == "list_tasks":
        return list_tasks(gorevler_file)
    elif tool_name == "complete_task":
        return complete_task(arguments.get("task_id", 0), gorevler_file)
    elif tool_name == "save_note":
        return save_note(
            arguments.get("title", ""),
            arguments.get("content", ""),
            knowledge_dir,
        )

    return {"error": f"ToolworkEşleştirilemedi: {tool_name}"}
