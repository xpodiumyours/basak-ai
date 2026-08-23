"""tools/executor.py — Tool çalıştırıcı.

Tool ismine göre ilgili fonksiyonu çağırır ve sonucu döndürür.
Her çalışma arac.log'a yazılır.
"""

from tools.web_search import web_search, sayfa_oku
from tools.tasks import add_task, list_tasks, complete_task
from tools.notes import save_note, deftere_kaydet
from tools.file_ops import read_file, write_file_ops, list_files
from tools.app_launcher import ac_uygulama
from tools.reminders import bugunku_hatirlatmalar
from tools.video_analyzer import video_analyze
from tools.olcum import git_durum, belge_ara, dosya_bilgi
from tools.tool_logger import log_tool_call
from tools.permissions import izinli_mi, etiketler

# Tool isimlerini fonksiyonlara eşleştiren harita
TOOL_MAP = {
    "web_search": web_search,
    "sayfa_oku": sayfa_oku,
    "add_task": add_task,
    "list_tasks": list_tasks,
    "complete_task": complete_task,
    "save_note": save_note,
    "deftere_kaydet": deftere_kaydet,
    "read_file": read_file,
    "write_file_tool": write_file_ops,
    "list_files": list_files,
    "ac_uygulama": ac_uygulama,
    "get_reminders": lambda: None,  # placeholder, asagida calistirilacak
}


def calistir(tool_name: str, arguments: dict, knowledge_dir: str = "",
             gorevler_file: str = "") -> dict:
    """Tool'u çalıştırır ve sonucu döndürür.

    Args:
        tool_name: Çalıştırılacak tool'un ismi.
        arguments: Tool parametreleri (dict).
        knowledge_dir: knowledge/ klasörü yolu.
        gorevler_file: Görevler dosyası yolu.

    Returns:
        Tool sonucu (dict). Hata olursa {"error": str}.
    """
    # Base dir (knowledge_dir'in bir üst dizini)
    import os
    base_dir = os.path.dirname(knowledge_dir) if knowledge_dir else os.getcwd()

    # P3 Permission Layer: etiketi tanimlanmayan arac calismaz.
    # Model kendi yetkisini veremez — tablo kod olarak sabit.
    if not izinli_mi(tool_name):
        log_tool_call(tool_name, arguments,
                      {"error": "izin engeli"}, base_dir)
        return {"error": (
            f"Güvenlik engeli: '{tool_name}' aracının izin etiketi yok. "
            "Bu araç kullanılamaz.")}

    # Tool'a göre doğru parametreleri hazırla ve çalıştır
    if tool_name == "sayfa_oku":
        sonuc = sayfa_oku(arguments.get("url", ""))
    elif tool_name == "web_search":
        sonuc = web_search(arguments.get("query", ""))
    elif tool_name == "add_task":
        sonuc = add_task(arguments.get("text", ""), gorevler_file)
    elif tool_name == "list_tasks":
        sonuc = list_tasks(gorevler_file)
    elif tool_name == "complete_task":
        sonuc = complete_task(arguments.get("task_id", 0), gorevler_file)
    elif tool_name == "save_note":
        sonuc = save_note(
            arguments.get("title", ""),
            arguments.get("content", ""),
            knowledge_dir,
        )
    elif tool_name == "deftere_kaydet":
        # OD-1: defter/ klasoru knowledge_dir'in bir ustunde
        defter_dir = os.path.join(base_dir, "defter")
        sonuc = deftere_kaydet(
            arguments.get("title", ""),
            arguments.get("content", ""),
            defter_dir,
            kim=arguments.get("kim", "basak"),
            tip=arguments.get("tip", "alinti"),
            omur=arguments.get("omur", "30g"),
            kaynak=arguments.get("kaynak", "sohbet"),
        )
    elif tool_name == "read_file":
        sonuc = read_file(arguments.get("path", ""), base_dir)
    elif tool_name == "write_file_tool":
        sonuc = write_file_ops(
            arguments.get("path", ""),
            arguments.get("content", ""),
            base_dir,
        )
    elif tool_name == "list_files":
        sonuc = list_files(arguments.get("folder", ""), base_dir)
    elif tool_name == "get_reminders":
        sonuc = bugunku_hatirlatmalar(knowledge_dir, gorevler_file)
    elif tool_name == "ac_uygulama":
        sonuc = ac_uygulama(
            arguments.get("uygulama", ""),
            arguments.get("parametre", ""),
        )
    elif tool_name == "video_analyze":
        sonuc = video_analyze(arguments.get("video_yolu", ""))
    elif tool_name == "image_analyze":
        from tools.image_analyzer import image_analyze
        sonuc = image_analyze(
            arguments.get("goruntu_yolu", ""),
            soru=arguments.get("soru"),
        )
    elif tool_name == "model_stats":
        from brain.stats import model_stats_al
        istat = model_stats_al()
        model = arguments.get("model")
        son_saat = arguments.get("son_saat", 24)
        if model:
            ozet = istat.ozet(model=model, son_saat=son_saat)
        else:
            ozet = istat.siralama(son_saat=son_saat)
        sonuc = {"result": ozet}
    elif tool_name == "git_durum":
        sonuc = git_durum(arguments.get("proje", ""))
    elif tool_name == "belge_ara":
        sonuc = belge_ara(arguments.get("proje", ""),
                          arguments.get("sorgu", ""))
    elif tool_name == "dosya_bilgi":
        sonuc = dosya_bilgi(arguments.get("proje", ""),
                            arguments.get("yol", ""))
    else:
        return {"error": f"Tool eşleştirilemedi: {tool_name}"}

    # Loglama
    log_tool_call(tool_name, arguments, sonuc, base_dir)

    return sonuc
