"""tools/zamanlayici.py — E-3: Zamanlanmış iş düzeni.

Başak sorulmadan çalışır: belirli periyotlarda kontrol eder,
gerekli bilgileri toplar, tek kart olarak sunar.

Kurallar:
- Aktif saatler: 10:00-20:00 (Casper'ın kararı)
- Periyot: 2 saatte bir (Casper'ın kararı)
- Sessiz saatlerde çalışmaz
- Cevaplanmazsa dırdır etmez (tek kart, tekrar göndermez)
- Her kart saat başlarında: 10:00, 12:00, 14:00, 16:00, 18:00, 20:00
"""

import logging
import os
import threading
import time
from datetime import datetime

logger = logging.getLogger(__name__)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Casper'ın kararları (E-3 durak noktası)
AKTIF_BASLANGIC = 10   # Sabah 10:00
AKTIF_BITIS = 20       # Akşam 20:00
PERIYOT_SAAT = 2       # 2 saatte bir

# Cart gonderim zamanlari: 10:00, 12:00, 14:00, 16:00, 18:00, 20:00
KART_ZAMANLARI = [10, 12, 14, 16, 18, 20]

# Son kartın gönderildiği zaman (tekrar engelleme)
_son_kart_zamani = {}
_son_kart_lock = threading.Lock()


def aktif_saat_mi(simdi=None):
    """Şu an aktif saatler içinde miyiz? (10:00 - 20:00 dahil)"""
    if simdi is None:
        simdi = datetime.now()
    return AKTIF_BASLANGIC <= simdi.hour <= AKTIF_BITIS


def kart_zamani_mi(simdi=None):
    """Şu an bir kart gönderme zamanı mı (periyot başı)?"""
    if simdi is None:
        simdi = datetime.now()
    return simdi.hour in KART_ZAMANLARI and simdi.minute < 5


def son_kart_benzer_mi(kart_id, simdi=None):
    """Bu kart ID'si için son 2 saat içinde gönderilmiş mi?"""
    if simdi is None:
        simdi = datetime.now()
    with _son_kart_lock:
        son_zaman = _son_kart_zamani.get(kart_id)
        if son_zaman:
            gecen = (simdi - son_zaman).total_seconds()
            if gecen < PERIYOT_SAAT * 3600:
                return True
        _son_kart_zamani[kart_id] = simdi
        return False


def kart_olustur(beyin, ayarlar=None, simdi=None):
    """Günlük özet kartını oluşturur.

    İçerik:
    1. Bugünün tarihi ve selam
    2. Hatırlatmalar (varsa)
    3. Görev durumu (bitmemiş görevler)
    4. Hava durumu (basit)
    5. Proje durumu (özet)

    Returns:
        {"kart": str, "kart_id": str} veya None (kart oluşturulmazsa)
    """
    if simdi is None:
        simdi = datetime.now()

    # Aktif saat kontrolü
    if not aktif_saat_mi(simdi):
        return None

    # Kart zamanı mı?
    if not kart_zamani_mi(simdi):
        return None

    # Tekrar engelleme
    kart_id = "ozet_%s_%d" % (simdi.strftime("%Y-%m-%d"), simdi.hour)
    if son_kart_benzer_mi(kart_id, simdi):
        return None

    parcalar = []

    # 1. Tarih ve selam (saate gore)
    gunler = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
    gun = gunler[simdi.weekday()]
    saat = simdi.hour
    if saat < 12:
        selam = "Günaydın"
    elif saat < 18:
        selam = "İyi günler"
    else:
        selam = "İyi akşamlar"
    parcalar.append("%s — %s, %s" % (selam, gun, simdi.strftime("%d.%m.%Y")))

    # 2. Hatırlatmalar
    try:
        from tools.reminders import bugunku_hatirlatmalar
        gorevler_file = os.path.join(BASE, "gorevler.json")
        knowledge_dir = os.path.join(BASE, "knowledge")
        hatirlatma = bugunku_hatirlatmalar(knowledge_dir, gorevler_file)
        h_metni = hatirlatma.get("result", "")
        if h_metni and "hatırlatma yok" not in h_metni.lower():
            parcalar.append("Hatırlatmalar:\n" + h_metni)
    except Exception:
        pass

    # 3. Görev durumu
    try:
        from tools.tasks import list_tasks
        gorevler_file = os.path.join(BASE, "gorevler.json")
        gorev_sonuc = list_tasks(gorevler_file)
        g_metni = gorev_sonuc.get("result", "")
        if g_metni and "görev yok" not in g_metni.lower():
            parcalar.append("Görevler:\n" + g_metni)
    except Exception:
        pass

    # 4. Hava durumu (basit)
    try:
        from tools.web_search import web_search
        hava = web_search("Ankara hava durumu")
        h_metni = hava.get("result", "")
        if h_metni and len(h_metni) > 10:
            parcalar.append("Hava: " + h_metni[:200])
    except Exception:
        pass

    # 5. Proje durumu (özet — her projede son durum)
    try:
        from tools.olcum import git_durum
        projeler = ["basak", "vixrex", "numeramatch", "xses"]
        proje_ozet = []
        for p in projeler:
            sonuc = git_durum(p)
            r = sonuc.get("result", "")
            if r:
                # İlk 2 satırı al
                satirlar = r.strip().split("\n")[:2]
                proje_ozet.append("  " + " | ".join(satirlar))
        if proje_ozet:
            parcalar.append("Projeler:\n" + "\n".join(proje_ozet))
    except Exception:
        pass

    if len(parcalar) <= 1:
        # Sadece selam var, anlamlı içerik yok
        return None

    kart = "\n\n".join(parcalar)

    return {"kart": kart, "kart_id": kart_id}


class Zamanlayici:
    """E-3: Arka plan zamanlayıcısı.

    basak_app.py'de bir thread olarak çalışır.
    Her periyotta kart oluşturup UI'a iletir.
    """

    def __init__(self, js_callback=None, beyin=None):
        """
        Args:
            js_callback: UI'a mesaj iletmek için fonksiyon (opsiyonel)
            beyin: Brain nesnesi (opsiyonel, hava durumu için)
        """
        self.js_callback = js_callback
        self.beyin = beyin
        self._durdu = threading.Event()
        self._thread = None

    def baslat(self):
        """Zamanlayıcıyı arka plan thread'inde başlatır."""
        if self._thread and self._thread.is_alive():
            return
        self._durdu.clear()
        self._thread = threading.Thread(
            target=self._dongu, daemon=True)
        self._thread.start()
        logger.info("Zamanlayici baslatildi (periyot: %d saat)", PERIYOT_SAAT)

    def durdur(self):
        """Zamanlayıcıyı durdurur."""
        self._durdu.set()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Zamanlayici durduruldu")

    def _dongu(self):
        """Ana döngü: her dakika kontrol et, zamanı gelince kart oluştur."""
        while not self._durdu.is_set():
            try:
                simdi = datetime.now()

                if aktif_saat_mi(simdi) and kart_zamani_mi(simdi):
                    kart = kart_olustur(self.beyin)
                    if kart and self.js_callback:
                        try:
                            self.js_callback(
                                "BasakUI.kartGoster("
                                + repr(kart["kart"]) + ")")
                        except Exception as e:
                            logger.warning("Kart gonderilemedi: %s", e)

            except Exception as e:
                logger.error("Zamanlayici hatasi: %s", e)

            # 60 saniye bekle (dakika bazlı kontrol)
            self._durdu.wait(60)
