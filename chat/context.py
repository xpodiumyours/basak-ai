"""chat/context.py — Bağlam hazırlığı modülü.

Knowledge yükleme, hafıza entegrasyonu ve geçmiş yönetimi.
Her sorudan önce ilgili bağlam hazırlanır.

Bağımlılıklar: os, json, threading (standart), memory (proje içi)
DI Container: ContextConfig (knowledge_dir, history_file, settings_file)
"""

import json
import logging
import os
import threading

logger = logging.getLogger(__name__)


# ── Knowledge yükleme ───────────────────────────────────────────────

KNOWLEDGE_EMBED_CHARS = 2000  # Sadece bu kadar direkt embed edilir


def load_knowledge(knowledge_dir, base_dir=None):
    """Knowledge/ klasöründeki dosyaları okur ve birleştirir.

    Dönüş: str (birleştirilmiş knowledge metni)
    """
    if base_dir is None:
        base_dir = os.path.dirname(knowledge_dir)

    try:
        dosyalar = sorted(
            ad for ad in os.listdir(knowledge_dir)
            if ad.lower().endswith((".md", ".txt")) and ad != "README.md"
        )
    except OSError:
        return ""

    parcalar = []
    kalan = KNOWLEDGE_EMBED_CHARS

    if "INDEX.md" in dosyalar:
        dosyalar.remove("INDEX.md")
        dosyalar.insert(0, "INDEX.md")

    # Proje dokümanları da hafızaya karışsın
    for ad_ek in ("defter/INDEX.md", "GOREV_LISTESI.md", "AGENTS.md"):
        tam_yol = os.path.join(base_dir, ad_ek)
        if os.path.exists(tam_yol) and ad_ek not in dosyalar:
            dosyalar.append(ad_ek)

    for ad in dosyalar:
        if kalan <= 0:
            break
        try:
            dosya_yolu = os.path.join(knowledge_dir, ad)
            if not os.path.exists(dosya_yolu):
                dosya_yolu = os.path.join(base_dir, ad)
            with open(dosya_yolu, "r",
                       encoding="utf-8", errors="replace") as f:
                icerik = f.read().strip()
        except OSError:
            continue
        if not icerik:
            continue
        if len(icerik) > kalan:
            icerik = icerik[:kalan].rstrip() + "..."
        parcalar.append("### " + ad + "\n" + icerik)
        kalan -= len(icerik)

    return "\n\n".join(parcalar)


# ── Geçmiş yönetimi ─────────────────────────────────────────────────

def yukle(path, varsayilan):
    """JSON dosyasını okur, hata olursa varsayılanı döndürür."""
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return varsayilan


def kaydet(path, veri):
    """JSON dosyasına yazar."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)


def gecmis_pencere(gecmis, limit=4000, adet_siniri=20):
    """Kilo limitli geçmiş penceresi.

    En YENİ mesajdan geriye doğru ekler; limit dolunca durur.
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
    """Geçmiş mesajlarını API formatına temizler."""
    import re as _re
    temiz = []
    for m in gecmis:
        icerik = m.get("content", "") or ""
        # Eski badge::Ö:: işaretlerini temizle
        if isinstance(icerik, str) and 'badge::' in icerik:
            eslesen = _re.search(r'badge::[^\"]*\"([^\"]+)\"', icerik)
            if eslesen:
                icerik = eslesen.group(1)
            else:
                icerik = _re.sub(r'badge::[^\n]*', '', icerik).strip()
        # None content → boş string
        if icerik is None:
            icerik = ""
        if m.get("role") == "assistant" and m.get("tool_calls"):
            temiz.append({"role": "assistant", "content": icerik or ""})
        else:
            temiz.append({"role": m.get("role"), "content": icerik})
    return temiz


# ── Hafıza entegrasyonu ─────────────────────────────────────────────

_hafiza = None
_hafiza_lock = threading.Lock()


def hafiza_al():
    """Motoru tek seferlik oluşturur; açılamazsa None döner."""
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
    """Soruyla ilgili anıları döndürür; motor/hata durumunda boş liste."""
    motor = hafiza_al()
    if not motor:
        return []
    try:
        return motor.ara(sorgu, limit=limit)
    except Exception as e:
        logger.warning("Anı arama hatası: %s", e)
        return []


# ── ContextConfig (DI Container için) ───────────────────────────────

class ContextConfig:
    """Bağlam yapılandırma ayarları."""

    def __init__(self, base_dir, knowledge_dir=None, history_file=None,
                 settings_file=None, gorevler_file=None):
        self.base_dir = base_dir
        self.knowledge_dir = knowledge_dir or os.path.join(base_dir, "knowledge")
        self.history_file = history_file or os.path.join(base_dir, "gecmis.json")
        self.settings_file = settings_file or os.path.join(base_dir, "ayarlar.json")
        self.gorevler_file = gorevler_file or os.path.join(base_dir, "gorevler.json")
        self.knowledge_cache = None
        self.knowledge_lock = threading.Lock()

    def load_and_cache_knowledge(self):
        """Knowledge'ı yükle ve önbelleğe al."""
        with self.knowledge_lock:
            self.knowledge_cache = load_knowledge(self.knowledge_dir, self.base_dir)
        return self.knowledge_cache

    def get_cached_knowledge(self):
        """Önbellekteki knowledge'ı döndür."""
        with self.knowledge_lock:
            return self.knowledge_cache
