"""brain/kota.py — Kota / Limit Yonetimi (P3).

Saglayici basina gunluk kullanim sayaci + 429 sonrasi otomatik soguma +
ucretli cagri engeli. Durum data/provider_limits/durum.json'da tutulur.

Kurallar (GOREV_LISTESI.md Katman 6):
- Ucretli cagri varsayilan ENGELLI (ayarlar.json "ucretli_engelli": true).
- Gunluk istek limiti dolan saglayici atlanir.
- 429/rate-limit hatasi alan saglayici sureliye sogur, zincir siradakine gecer.
"""

import json
import logging
import os
import re
import threading
import time
from datetime import date

logger = logging.getLogger(__name__)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DURUM_DOSYASI = os.path.join(BASE, "data", "provider_limits", "durum.json")

SOGUMA_VARSAYILAN_SN = 600  # retry suresi okunamazsa 10 dakika

# Rate-limit benzeri hatalarin tanima desenleri
_RATE_DESENLERI = ("429", "rate limit", "rate_limit", "quota",
                   "resource_exhausted", "tpd", "too many requests")
_RETRY_DESENLERI = [
    re.compile(r"try again in\s+(?:(\d+)m)?\s*(\d+(?:\.\d+)?)s", re.I),
    re.compile(r"retry in\s+(\d+(?:\.\d+)?)s", re.I),
    re.compile(r"retrydelay['\"]?\s*:\s*['\"]?(\d+(?:\.\d+)?)s", re.I),
]


def rate_limit_hatasi_mi(hata_str):
    """Hata metni rate-limit/kota turunden mi?"""
    t = (hata_str or "").lower()
    return any(d in t for d in _RATE_DESENLERI)


def _retry_suresi_oku(hata_str):
    """Hata mesajindan 'try again in 14m4s' tarzi sureyi saniyeye cevirir."""
    for desen in _RETRY_DESENLERI:
        m = desen.search(hata_str or "")
        if not m:
            continue
        gruplar = m.groups()
        try:
            if len(gruplar) == 2:  # dakika + saniye
                dakika = int(gruplar[0]) if gruplar[0] else 0
                return dakika * 60 + int(float(gruplar[1])) + 5
            return int(float(gruplar[0])) + 5
        except (ValueError, TypeError):
            continue
    return None


class KotaYoneticisi:
    def __init__(self, dosya=None, ucretli_engelli=True):
        self.dosya = dosya or DURUM_DOSYASI
        self.ucretli_engelli = bool(ucretli_engelli)
        self._lock = threading.Lock()
        self.durum = self._yukle()

    # ---------- disk ----------

    def _yukle(self):
        try:
            with open(self.dosya, "r", encoding="utf-8-sig") as f:
                durum = json.load(f)
        except (OSError, json.JSONDecodeError):
            durum = {}
        return self._gun_kontrol(durum)

    def _gun_kontrol(self, durum):
        """Tarih degistiyse (veya yapi bozuksa) gune ait temiz durum dondurur."""
        bugun = date.today().isoformat()
        if durum.get("tarih") != bugun or not isinstance(
                durum.get("sayac"), dict):
            return {"tarih": bugun, "sayac": {}, "cooldown": {}}
        durum.setdefault("cooldown", {})
        return durum

    def _kaydet(self):
        try:
            os.makedirs(os.path.dirname(self.dosya), exist_ok=True)
            tmp = self.dosya + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.durum, f, ensure_ascii=False, indent=1)
            os.replace(tmp, self.dosya)
        except OSError as e:
            logger.warning("Kota durumu yazilamadi: %s", e)

    # ---------- sorgu ----------

    def engel_nedeni(self, ad, kart=None):
        """Saglayici simdi kullanilamazsa neden metni; kullanilabilirse None.

        kart: registry karti (ucretsiz/gunluk_istek/gunluk_token bilgisi).
        """
        kart = kart or {}
        if not kart.get("ucretsiz", True) and self.ucretli_engelli:
            return "ucretli cagri varsayilan engelli"
        with self._lock:
            self.durum = self._gun_kontrol(self.durum)
            cooldown = self.durum["cooldown"].get(ad, 0)
            if cooldown > time.time():
                kalan = int(cooldown - time.time())
                return "429 sonrasi soguma (%d sn)" % kalan
            limit = kart.get("gunluk_istek")
            sayac = self.durum["sayac"].get(ad, {}).get("istek", 0)
            if limit is not None and sayac >= limit:
                return "gunluk istek limiti doldu (%d/%d)" % (sayac, limit)

        # B3 (2026-08-24, kilitli hedef): GERCEK TOKEN BUTCESI.
        # registry'de gunluk_token tanimliysa istek sayaci yerine bugunun
        # gercek token toplami esastir (stats.py'den okunur). Olcum
        # basarisizsa engel kurulmaz — olcum sohbeti bozmasin.
        butce = kart.get("gunluk_token")
        if butce:
            try:
                from brain.stats import model_stats_al
                giris, cikis = model_stats_al().token_bugun(ad)
                harcanan = giris + cikis
                if harcanan >= butce:
                    return ("gunluk token butcesi doldu (%d/%d)"
                            % (harcanan, butce))
            except Exception as e:
                logger.warning("Token butce sorgusu atlandi (%s): %s", ad, e)
        return None

    # ---------- yazma ----------

    def harca(self, ad):
        """Basarili cagri sonrasi gunluk sayaci artirir; yeni sayiyi dondurur."""
        with self._lock:
            sayac = self.durum["sayac"].setdefault(ad, {"istek": 0})
            sayac["istek"] += 1
            self._kaydet()
            return sayac["istek"]

    def hata_isle(self, ad, hata_str):
        """Rate-limit hatasysa soguma kurar; kurulduysa True doner."""
        if not rate_limit_hatasi_mi(hata_str):
            return False
        sure = _retry_suresi_oku(hata_str) or SOGUMA_VARSAYILAN_SN
        until = time.time() + sure
        with self._lock:
            self.durum.setdefault("cooldown", {})[ad] = until
            self._kaydet()
        logger.info("%s %d sn sogumaya alindi", ad, sure)
        return True

    def soguma_temizle(self, ad):
        """Manuel temizleme (test ve ayiklama icin)."""
        with self._lock:
            self.durum.get("cooldown", {}).pop(ad, None)
            self._kaydet()
