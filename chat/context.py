"""chat/context.py — Bağlam, geçmiş ve hafıza."""

import json
import logging
import os
import threading
import uuid

logger = logging.getLogger(__name__)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY_FILE = os.path.join(BASE, "gecmis.json")
SETTINGS_FILE = os.path.join(BASE, "ayarlar.json")
KNOWLEDGE_DIR = os.path.join(BASE, "knowledge")
OBSIDIAN_DIR = os.path.join(BASE, "Basak")

OTURUM_ID = uuid.uuid4().hex[:8]


def yukle(path, varsayilan):
    """JSON dosyasını okur; hata olursa varsayılanı döndürür."""
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return varsayilan


def kaydet(path, veri):
    """JSON dosyasına yazar."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)


def gecmis_pencere(gecmis):
    """Kaydedilmiş sohbet geçmişini ek bir karakter tavanı koymadan döndürür.

    `gecmis.json` zaten yazma tarafında son 40 mesajla sınırlıdır; burada
    model bağlamını ikinci kez daraltan kelime/karakter filtresi uygulanmaz.
    """
    return list(gecmis or [])


def temizle_history(gecmis):
    """Geçmiş mesajlarını API biçimine indirger."""
    temiz = []
    for m in gecmis:
        icerik = m.get("content") or ""
        temiz.append({"role": m.get("role"), "content": icerik})
    return temiz


def onem_puanla(_text):
    """Kelime tetiklemesi yapmadan nötr başlangıç önem puanı döndürür."""
    return 1


_hafiza = None
_hafiza_lock = threading.Lock()


def hafiza_al():
    """Motoru tek seferlik oluşturur; açılamazsa None."""
    global _hafiza
    with _hafiza_lock:
        if _hafiza is None:
            try:
                from memory import HafizaMotoru
                _hafiza = HafizaMotoru()
            except Exception as e:
                logger.warning("Hafiza motoru acilamadi: %s", e)
                _hafiza = False
    return _hafiza or None


def ilgili_anilar(sorgu, limit=8):
    """Soruyla ilgili anıları döndürür; hata durumunda boş liste."""
    motor = hafiza_al()
    if not motor:
        return []
    try:
        return motor.ara(sorgu, limit=limit)
    except Exception as e:
        logger.warning("Ani arama hatasi: %s", e)
        return []


def _gecmisi_aktar(motor):
    """gecmis.json'daki eski sohbeti bir kereye mahsus hafızaya taşır."""
    kayitlar = yukle(HISTORY_FILE, [])
    soru = None
    sayac = 0
    for m in kayitlar:
        rol = m.get("role")
        icerik = (m.get("content") or "").strip()
        if not icerik:
            continue
        if rol == "user":
            soru = icerik
        elif rol == "assistant" and soru:
            if motor.episodik_kaydet(soru, icerik):
                sayac += 1
            soru = None
    logger.info("Eski gecmis hafizaya tasindi: %d cift", sayac)


def _hafiza_hazirla():
    """Arka planda eski geçmişi aktarır ve notları indeksler."""
    motor = hafiza_al()
    if not motor:
        return
    try:
        from memory.engine import indeksle_klasor

        if not motor.meta_al("gecmis_aktarildi", False):
            _gecmisi_aktar(motor)
            motor.meta_koy("gecmis_aktarildi", True)

        n1 = indeksle_klasor(motor, KNOWLEDGE_DIR, "knowledge")
        n2 = indeksle_klasor(motor, OBSIDIAN_DIR, "obsidian")
        logger.info("Hafiza hazir: %d ani, indeksleme +%d",
                    motor.say(), n1 + n2)
    except Exception as e:
        logger.warning("Hafiza hazirlanamadi (sohbet etkilenmez): %s", e)


def init_cache():
    """Açılışta çağrılır: hafızayı arka planda hazırlar."""
    threading.Thread(target=_hafiza_hazirla, daemon=True).start()
