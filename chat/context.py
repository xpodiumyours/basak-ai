"""chat/context.py — Bağlam hazırlığı modülü.

Knowledge yükleme, hafıza entegrasyonu ve geçmiş yönetimi.
Her sorudan önce ilgili bağlam hazırlanır.

Bağımlılıklar: os, json, threading (standart), memory (proje içi)
"""

import json
import logging
import os
import threading

logger = logging.getLogger(__name__)


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
