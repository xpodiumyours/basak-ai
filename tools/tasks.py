"""tools/tasks.py — Görev yönetimi.

Görev ekleme, listeleme ve tamamlama fonksiyonları.
Görevler gorevler.json dosyasında saklanır.

Eşzamanlılık (2026-08-24, Casper'in bulgusu): Api.mesaj() her mesajı ayrı
thread'de koşturur; oku-değiştir-yaz döngüsü kilitsizse iki işlem aynı ID'yi
üretip birbirinin yazdığını ezebiliyordu. Artık:
- _KILIT: tüm oku-değiştir-yaz bölümlerini sarar (tek süreçte yeterli)
- ID: max(mevcut)+1 (len+1 değil)
- _atomik_yaz: önce .tmp'e yazıp os.replace — yarım dosya okunamaz
"""

import json
import logging
import os
import re
import threading
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Tek Python surecindeki tum yazicilar bu kilidi paylasir
_KILIT = threading.Lock()


def _yukle(gorevler_file):
    """BOM guvenli okuma; dosya yoksa bos liste."""
    if not os.path.exists(gorevler_file):
        return []
    with open(gorevler_file, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def _atomik_yaz(gorevler_file, gorevler):
    """Once .tmp'e yaz, sonra tek hamlede degistir.

    os.replace ayni surucude atomiktir — baska thread/dosya okuyucusu
    yarim JSON gormez. Cagranda _KILIT'i tutuyor olmali.
    """
    gecici = gorevler_file + ".tmp"
    with open(gecici, "w", encoding="utf-8") as f:
        json.dump(gorevler, f, ensure_ascii=False, indent=2)
    os.replace(gecici, gorevler_file)


def add_task(text: str, gorevler_file: str) -> dict:
    """Yeni bir görev ekler.

    Tarih tespiti yapar: "yarın" → yarının tarihi, "bu hafta" → 7 gün sonra.
    """
    if not text or not text.strip():
        return {"error": "Görev açıklaması boş olamaz"}

    try:
        # Tarih tespiti (kilitsiz — sadece metin isleme)
        bugun = datetime.now()
        tarih = bugun.strftime("%Y-%m-%d")
        text_lower = text.lower()
        if "yarın" in text_lower or "yarin" in text_lower:
            tarih = (bugun + timedelta(days=1)).strftime("%Y-%m-%d")
            text = re.sub(r"yar[ıi]n\s*", "", text, flags=re.IGNORECASE).strip()
        elif "bu hafta" in text_lower:
            tarih = (bugun + timedelta(days=7)).strftime("%Y-%m-%d")

        with _KILIT:
            gorevler = _yukle(gorevler_file)
            gorev = {
                "id": max((g.get("id", 0) for g in gorevler), default=0) + 1,
                "text": text.strip(),
                "date": tarih,
                "done": False,
                "created": bugun.strftime("%Y-%m-%d %H:%M"),
            }
            gorevler.append(gorev)
            _atomik_yaz(gorevler_file, gorevler)

        return {"result": f"Görev eklendi: {text.strip()} ({tarih})"}

    except (OSError, json.JSONDecodeError) as e:
        logger.error("Görev eklenemedi: %s", e)
        return {"error": f"Görev eklenemedi: {e}"}


def list_tasks(gorevler_file: str) -> dict:
    """Tamamlanmamış görevleri listeler.

    Args:
        gorevler_file: Görevlerin saklandığı JSON dosya yolu.

    Returns:
        {"result": str} formatında görev listesi veya
        {"result": "Henüz görev yok"} mesajı.
    """
    try:
        if not os.path.exists(gorevler_file):
            return {"result": "Henüz görev yok"}

        with open(gorevler_file, "r", encoding="utf-8-sig") as f:
            gorevler = json.load(f)

        acik_gorevler = [g for g in gorevler if not g.get("done")]

        if not acik_gorevler:
            return {"result": "Tüm görevler tamamlanmış"}

        satirlar = []
        for g in acik_gorevler:
            satirlar.append(f"- [{g['id']}] {g['text']} ({g.get('date', '?')})")

        return {"result": "\n".join(satirlar)}

    except (OSError, json.JSONDecodeError) as e:
        logger.error("Görevler listelenemedi: %s", e)
        return {"error": f"Görevler listelenemedi: {e}"}


def complete_task(task_id: int, gorevler_file: str) -> dict:
    """Bir görevi tamamlandı olarak işaretle (kilitle + atomik yaz)."""
    try:
        with _KILIT:
            gorevler = _yukle(gorevler_file)
            if not gorevler:
                return {"error": "Görev listesi boş"}

            for g in gorevler:
                if g.get("id") == task_id:
                    g["done"] = True
                    _atomik_yaz(gorevler_file, gorevler)
                    return {"result": f"Görev #{task_id} tamamlandı: {g['text']}"}

        return {"error": f"Görev #{task_id} bulunamadı"}

    except (OSError, json.JSONDecodeError) as e:
        logger.error("Görev tamamlanamadı: %s", e)
        return {"error": f"Görev tamamlanamadı: {e}"}
