"""tools/tasks.py — Görev yönetimi.

Görev ekleme, listeleme, tamamlama ve durum güncelleme fonksiyonları.
Durum alanı (2026-10-17): pending/in_progress/paused/done — yarım kalan
iş list_tasks'ta durumuyla görünür, update_task_status ile ilerler.
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
import threading
from datetime import datetime

logger = logging.getLogger(__name__)

# Tek Python surecindeki tum yazicilar bu kilidi paylasir
_KILIT = threading.Lock()


def _yukle(gorevler_file):
    """BOM guvenli okuma; dosya yoksa bos liste."""
    if not gorevler_file:
        raise ValueError("Gorev dosyasi yolu bos olamaz")
    if not os.path.exists(gorevler_file):
        return []
    with open(gorevler_file, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def _atomik_yaz(gorevler_file, gorevler):
    """Once .tmp'e yaz, sonra tek hamlede degistir.

    os.replace ayni surucude atomiktir — baska thread/dosya okuyucusu
    yarim JSON gormez. Cagranda _KILIT'i tutuyor olmali.
    2026-09-10: bos yol yasaktir — eskiden ".tmp" adinda sahte dosya
    uretip WinError ile patliyordu.
    """
    if not gorevler_file:
        raise ValueError("Gorev dosyasi yolu bos olamaz")
    gecici = gorevler_file + ".tmp"
    with open(gecici, "w", encoding="utf-8") as f:
        json.dump(gorevler, f, ensure_ascii=False, indent=2)
    os.replace(gecici, gorevler_file)


def add_task(text: str, gorevler_file: str, date: str = None) -> dict:
    """Yeni bir görev ekler.

    P2 (2026-09-15): kullanici cumlesinden Python keyword/regex ile tarih
    cikarma KALDIRILDI ("yarin"/"bu hafta" kurallari). Tarihi AI cikarir
    ve acik `date` alaniyla verir (YYYY-MM-DD). Kod yalniz bicimi dogrular
    (guvenlik/format); niyeti tahmin etmez. `date` bossa bugun yazilir.
    """
    if not text or not text.strip():
        return {"error": "Görev açıklaması boş olamaz"}
    if not gorevler_file:
        return {"error": "Görev dosyası yolu boş olamaz"}

    try:
        # Tarih: yalniz acik `date` alani kullanilir (YYYY-MM-DD bicim
        # dogrulamasi). Cumle ici keyword tahmini YOK.
        bugun = datetime.now()
        varsayilan = bugun.strftime("%Y-%m-%d")
        tarih = varsayilan
        if date and str(date).strip():
            _d = str(date).strip()[:10]
            try:
                _t = datetime.strptime(_d, "%Y-%m-%d")
                tarih = _t.strftime("%Y-%m-%d")
            except ValueError:
                return {"error": "Tarih YYYY-MM-DD olmali."}

        with _KILIT:
            gorevler = _yukle(gorevler_file)
            gorev = {
                "id": max((g.get("id", 0) for g in gorevler), default=0) + 1,
                "text": text.strip(),
                "date": tarih,
                "done": False,
                "status": "pending",
                "created": bugun.strftime("%Y-%m-%d %H:%M"),
                "updated": bugun.strftime("%Y-%m-%d %H:%M"),
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
        if not gorevler_file:
            return {"error": "Görev dosyası yolu boş olamaz"}
        if not os.path.exists(gorevler_file):
            return {"result": "Henüz görev yok"}

        with open(gorevler_file, "r", encoding="utf-8-sig") as f:
            gorevler = json.load(f)

        acik_gorevler = [g for g in gorevler if not g.get("done")]

        if not acik_gorevler:
            return {"result": "Tüm görevler tamamlanmış"}

        satirlar = []
        for g in acik_gorevler:
            durum = g.get("status") or ("done" if g.get("done") else "pending")
            satirlar.append(f"- [{g['id']}] {durum} | {g['text']} ({g.get('date', '?')})")

        return {"result": "\n".join(satirlar)}

    except (OSError, json.JSONDecodeError) as e:
        logger.error("Görevler listelenemedi: %s", e)
        return {"error": f"Görevler listelenemedi: {e}"}


def gorev_ozeti(gorevler_file: str) -> dict:
    """Gorevlerin sayimi ve acik olanlarin listesi (salt-okunur).

    Web ekrani (/durum) "acik is var mi?" sorusunu buradan yanitlar.
    Model araci degildir; dosyaya yazmaz.
    """
    sonuc = {"toplam": 0, "acik": 0, "kapali": 0, "liste": [], "hata": None}
    try:
        if not gorevler_file or not os.path.exists(gorevler_file):
            return sonuc
        with open(gorevler_file, "r", encoding="utf-8-sig") as f:
            gorevler = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        sonuc["hata"] = "Gorevler okunamadi: %s" % e
        return sonuc

    sonuc["toplam"] = len(gorevler)
    for g in gorevler:
        bitti = bool(g.get("done")) or g.get("status") == "done"
        if bitti:
            sonuc["kapali"] += 1
            continue
        sonuc["acik"] += 1
        sonuc["liste"].append({
            "id": g.get("id"),
            "text": g.get("text", ""),
            "status": g.get("status") or "pending",
            "date": g.get("date", ""),
        })
    return sonuc


def complete_task(task_id: int, gorevler_file: str) -> dict:
    """Bir görevi tamamlandı olarak işaretle (kilitle + atomik yaz)."""
    if not gorevler_file:
        return {"error": "Görev dosyası yolu boş olamaz"}
    try:
        with _KILIT:
            gorevler = _yukle(gorevler_file)
            if not gorevler:
                return {"error": "Görev listesi boş"}

            for g in gorevler:
                if g.get("id") == task_id:
                    g["done"] = True
                    g["status"] = "done"
                    g["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                    g["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                    _atomik_yaz(gorevler_file, gorevler)
                    return {"result": f"Görev #{task_id} tamamlandı: {g['text']}"}

        return {"error": f"Görev #{task_id} bulunamadı"}

    except (OSError, json.JSONDecodeError) as e:
        logger.error("Görev tamamlanamadı: %s", e)
        return {"error": f"Görev tamamlanamadı: {e}"}


def update_task_status(task_id: int, status: str, gorevler_file: str, note: str = None) -> dict:
    """Görev durumunu günceller (pending/in_progress/paused/done)."""
    if not gorevler_file:
        return {"error": "Görev dosyası yolu boş olamaz"}
    valid = {"pending", "in_progress", "paused", "done"}
    if status not in valid:
        return {"error": f"Geçersiz durum: {status}"}
    try:
        with _KILIT:
            gorevler = _yukle(gorevler_file)
            for g in gorevler:
                if g.get("id") == task_id:
                    g["status"] = status
                    g["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                    if note:
                        g["note"] = note
                    if status == "done":
                        g["done"] = True
                        g["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                    else:
                        g["done"] = False
                        # Yeniden acilan gorevde eski kapanis ani kalmamali.
                        g.pop("completed_at", None)
                    _atomik_yaz(gorevler_file, gorevler)
                    return {"result": f"Görev #{task_id} durumu: {status}"}
        return {"error": f"Görev #{task_id} bulunamadı"}
    except (OSError, json.JSONDecodeError) as e:
        logger.error("Görev durumu güncellenemedi: %s", e)
        return {"error": f"Görev durumu güncellenemedi: {e}"}
