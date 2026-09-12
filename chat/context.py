"""chat/context.py — Bağlam, geçmiş ve hafıza.

2026-09-13 sadeleştirmesi: araç katmanı söküldükten sonra bu modül
`_chat_legacy.py`'ye bağlı kalmasın diye dosya yolları, JSON okuma/yazma
ve hafıza bağlantısı buraya taşındı.

Sorumluluğu:
  - dosya yolları ve ayar okuma
  - modele giden geçmiş penceresi (kilo limitli)
  - kalıcı hafıza motoruna tek giriş noktası
"""

import json
import logging
import os
import threading
import uuid

logger = logging.getLogger(__name__)

# ── Dosya yolları ───────────────────────────────────────────────────

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY_FILE = os.path.join(BASE, "gecmis.json")
SETTINGS_FILE = os.path.join(BASE, "ayarlar.json")
KNOWLEDGE_DIR = os.path.join(BASE, "knowledge")
OBSIDIAN_DIR = os.path.join(BASE, "Basak")

# Her açılışta bir oturum kimliği — kayıtlara işlenir.
OTURUM_ID = uuid.uuid4().hex[:8]

# ── Geçmiş penceresi ────────────────────────────────────────────────
# Modele giden pencere sayıyla değil KİLOYLA sınırlı: uzun cevaplar
# birikip isteği şişirmesin. Kesim hafızadan silmek değildir — her çift
# zaten hafıza motoruna yazılır, eski kısımlar aramayla geri gelir.

MAX_HISTORY = 20
GECMIS_KILO_LIMITI = 4000


def yukle(path, varsayilan):
    """JSON dosyasını okur; hata olursa varsayılanı döndürür (BOM güvenli)."""
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return varsayilan


def kaydet(path, veri):
    """JSON dosyasına yazar."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)


def gecmis_pencere(gecmis, limit=GECMIS_KILO_LIMITI, adet_siniri=MAX_HISTORY):
    """Kilo limitli geçmiş penceresi.

    En YENİ mesajdan geriye doğru ekler; limit dolunca durur. Mesajlar
    bütün halde alınır (ortasından kesilmez). Kronolojik sıra korunur.
    """
    secilen = []
    toplam = 0
    for m in reversed(gecmis or []):
        uzunluk = len(m.get("content") or "")
        if secilen and toplam + uzunluk > limit:
            break
        secilen.append(m)
        toplam += uzunluk
        if len(secilen) >= adet_siniri:
            break
    secilen.reverse()
    return secilen


def temizle_history(gecmis):
    """Geçmiş mesajlarını API biçimine indirger."""
    temiz = []
    for m in gecmis:
        icerik = m.get("content") or ""
        temiz.append({"role": m.get("role"), "content": icerik})
    return temiz


# ── Önem puanı ──────────────────────────────────────────────────────
# Puanı KOD verir, model tahmin etmez. Budama sırası önem → tarih
# olduğu için açıkça "hatırla" denen bilgi gevezeliğin altında kalmaz.

_ONEM_KELIMELERI = ("hatırla", "not al", "kaydet", "önemli", "unutma")


def onem_puanla(text):
    """Sohbet anısına başlangıç önem puanı: 3 (açık istek) veya 1."""
    t = (text or "").lower()
    if any(k in t for k in _ONEM_KELIMELERI):
        return 3
    return 1


# ── Hafıza ──────────────────────────────────────────────────────────

_hafiza = None
_hafiza_lock = threading.Lock()


def hafiza_al():
    """Motoru tek seferlik oluşturur; açılamazsa None (sohbet devam eder)."""
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


def ilgili_anilar(sorgu, limit=4):
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
    """Arka planda: eski geçmişi aktar, notları indeksle.

    Araçlar söküldü; `knowledge/` klasörüne erişim artık YALNIZ hafıza
    araması üzerinden. Bu yüzden indeksleme kritik — çalışmazsa notlar
    görünmez olur.
    """
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
