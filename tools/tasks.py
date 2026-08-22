"""tools/tasks.py — Görev yönetimi.

Görev ekleme, listeleme ve tamamlama fonksiyonları.
Görevler gorevler.json dosyasında saklanır.
"""

import json
import logging
import os
import re
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def add_task(text: str, gorevler_file: str) -> dict:
    """Yeni bir görev ekler.

    Tarih tespiti yapar: "yarın" → yarının tarihi, "bu hafta" → 7 gün sonra.

    Args:
        text: Görev açıklaması.
        gorevler_file: Görevlerin saklandığı JSON dosya yolu.

    Returns:
        {"result": str} formatında başarı mesajı veya
        {"error": str} formatında hata mesajı.
    """
    if not text or not text.strip():
        return {"error": "Görev açıklaması boş olamaz"}

    try:
        # Mevcut görevleri yükle
        gorevler = []
        if os.path.exists(gorevler_file):
            with open(gorevler_file, "r", encoding="utf-8-sig") as f:
                gorevler = json.load(f)

        # Tarih tespiti
        bugun = datetime.now()
        tarih = bugun.strftime("%Y-%m-%d")
        text_lower = text.lower()
        if "yarın" in text_lower or "yarin" in text_lower:
            tarih = (bugun + timedelta(days=1)).strftime("%Y-%m-%d")
            text = re.sub(r"yar[ıi]n\s*", "", text, flags=re.IGNORECASE).strip()
        elif "bu hafta" in text_lower:
            tarih = (bugun + timedelta(days=7)).strftime("%Y-%m-%d")

        gorev = {
            "id": len(gorevler) + 1,
            "text": text.strip(),
            "date": tarih,
            "done": False,
            "created": bugun.strftime("%Y-%m-%d %H:%M"),
        }
        gorevler.append(gorev)

        with open(gorevler_file, "w", encoding="utf-8") as f:
            json.dump(gorevler, f, ensure_ascii=False, indent=2)

        return {"result": f"Görev eklendi: {text.strip()} ({tarih})"}

    except (OSError, json.JSONDecodeError) as e:
        logger.error("Görev eklenemedir: %s", e)
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
    """Bir görevi tamamlandı olarak işaretle.

    Args:
        task_id: Tamamlanacak görevin numarası.
        gorevler_file: Görevlerin saklandığı JSON dosya yolu.

    Returns:
        {"result": str} formatında başarı mesajı veya
        {"error": str} formatında hata mesajı.
    """
    try:
        if not os.path.exists(gorevler_file):
            return {"error": "Görev listesi boş"}

        with open(gorevler_file, "r", encoding="utf-8-sig") as f:
            gorevler = json.load(f)

        for g in gorevler:
            if g.get("id") == task_id:
                g["done"] = True
                with open(gorevler_file, "w", encoding="utf-8") as f:
                    json.dump(gorevler, f, ensure_ascii=False, indent=2)
                return {"result": f"Görev #{task_id} tamamlandı: {g['text']}"}

        return {"error": f"Görev #{task_id} bulunamadı"}

    except (OSError, json.JSONDecodeError) as e:
        logger.error("Görev tamamlanamadı: %s", e)
        return {"error": f"Görev tamamlanamadı: {e}"}
