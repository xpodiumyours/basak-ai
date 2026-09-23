"""tools/saglik.py — Hat saglik raporu (salt-okunur, ag yok).

Kendi olcumlerimizden tablo: son 24 saatte her hat kac kez denendi,
kaci tuttu, ortalama sure, bugunku jeton. Ayrica denetim gunlugunun
kuyrugundaki hata tipleri (kota mi, zaman asimi mi?).
Karar vermez, sira degistirmez — yalniz gosterir.
"""

import logging
import os
from collections import Counter

from chat.kimlik import durum_yolu

logger = logging.getLogger(__name__)

# 2026-09-23 olcumu: bu modul BASE/data/audit/audit.log okuyordu,
# brain/brain.py ise durum koku altina YAZIYORDU — saglik raporu
# gercek kaydi hic gormuyordu. Artik ikisi ayni yer.
# None = durum kokunun audit/audit.log dosyasi; test patch edebilir.
AUDIT_DOSYASI = None


def audit_dosyasi():
    """Denetim gunlugu: brain/brain.py'nin yazdigi dosyanin ta kendisi."""
    return AUDIT_DOSYASI or os.path.join(durum_yolu("audit"), "audit.log")


_GROQ_GUNLUK_JETON = 200000  # olculmus gunluk butce (429 mesajindan)


def _hata_ozeti(audit_yolu, adet=300):
    """Kuyruktaki HATA satirlarini tiplerine gore sayar."""
    try:
        with open(audit_yolu, "r", encoding="utf-8") as f:
            satirlar = f.read().splitlines()[-adet:]
    except OSError:
        return {}
    tipler = Counter()
    for s in satirlar:
        if "HATA" not in s:
            continue
        kucuk = s.lower()
        if "429" in kucuk or "rate" in kucuk or "limit" in kucuk:
            tipler["kota-doldu"] += 1
        elif "timed out" in kucuk or "timeout" in kucuk:
            tipler["zaman-asimi"] += 1
        else:
            tipler["diger-hata"] += 1
    return dict(tipler)


def saglik_raporu(audit_yolu=None, saat=24):
    """Zincir sagligini olcer. Donus: okunabilir tablo metni."""
    try:
        from brain.stats import model_stats_al
        ozetler = model_stats_al().ozet(son_saat=saat)
    except Exception as e:
        return {"error": "Istatistik okunamadi: %s" % e}
    cikti = ["Son %d saat — hat sagligi:" % saat]
    toplam_cagri = 0
    for o in ozetler:
        toplam_cagri += o.get("toplam", 0) or 0
        cikti.append("%s: %d cagri, %%%s basari, ort %ss" % (
            o.get("model", "?"), o.get("toplam", 0),
            o.get("basari_orani", 0),
            round((o.get("ortalama_ms", 0) or 0) / 1000, 1)))
    if not ozetler:
        cikti.append("(henuz kayit yok)")
    try:
        from brain.stats import model_stats_al as _al
        giris, _ = _al().token_bugun("groq")
        cikti.append("groq bugun: %d/%d jeton (%%%d dolu)" % (
            giris, _GROQ_GUNLUK_JETON,
            min(99, int(giris * 100 / _GROQ_GUNLUK_JETON))))
    except Exception:
        pass
    hatalar = _hata_ozeti(audit_yolu or audit_dosyasi())
    if hatalar:
        cikti.append("Hata dagilimi: " + ", ".join(
            "%s=%d" % (k, v) for k, v in sorted(hatalar.items())))
    cikti.append("Toplam cagri: %d" % toplam_cagri)
    return {"result": "\n".join(cikti)}
