"""İşçinin ortam ayarları — tek yerde okunur, sır dışa yazılmaz.

Üretimde `BASAK_ISCI_ANAHTARI` beyinle aynı olmalıdır; onay belgesi bu
anahtarla imzalanır. Kuyruk için `BASAK_ISCI_DATABASE_URL` (yoksa
`DATABASE_URL`) verilmezse yerel SQLite kullanılır — bu yalnız geliştirme
ve tek makineli kurulum içindir.
"""

import os
import re
from dataclasses import dataclass, field

_ISCI_ADI = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


class AyarHatasi(ValueError):
    """Ortam değişkeni eksik ya da geçersiz."""


@dataclass(frozen=True)
class Ayarlar:
    anahtar: str = field(repr=False)
    isci: str
    dsn: str = field(repr=False)
    aralik: float
    kalp_aralik: float
    esik: float
    zaman_asimi_ms: int
    saglik_port: int
    surum: str

    def ozet(self):
        """Log/ekran için sırsız özet."""
        return {
            "isci": self.isci,
            "surum": self.surum,
            "kuyruk": "postgres" if self.dsn else "sqlite",
            "aralik": self.aralik,
            "kalp_aralik": self.kalp_aralik,
            "esik": self.esik,
            "zaman_asimi_ms": self.zaman_asimi_ms,
            "saglik_port": self.saglik_port,
        }


def _metin(ortam, ad, varsayilan=""):
    return (ortam.get(ad) or varsayilan).strip()


def _sayi(ortam, ad, varsayilan, alt, ust, tam=False):
    ham = _metin(ortam, ad)
    if not ham:
        return varsayilan
    try:
        deger = int(ham) if tam else float(ham)
    except (TypeError, ValueError) as hata:
        raise AyarHatasi("%s sayı olmalı: %r" % (ad, ham)) from hata
    if deger < alt or deger > ust:
        raise AyarHatasi("%s %s..%s aralığında olmalı: %s"
                         % (ad, alt, ust, deger))
    return deger


def _dsn(ortam):
    if _metin(ortam, "VERCEL_ENV").lower() == "preview":
        from chat.kosu_deposu import _dsn as preview_dsn
        return preview_dsn(ortam)
    for ad in ("BASAK_ISCI_DATABASE_URL", "DATABASE_URL", "POSTGRES_URL",
               "NEON_DATABASE_URL"):
        deger = _metin(ortam, ad)
        if deger:
            return deger
    return ""


def oku(ortam=None):
    """Ortamdan ayarları okur; eksik anahtar açık hata verir."""
    ortam = os.environ if ortam is None else ortam
    anahtar = _metin(ortam, "BASAK_ISCI_ANAHTARI")
    if not anahtar:
        raise AyarHatasi(
            "BASAK_ISCI_ANAHTARI yok: onay belgesi doğrulanamaz")

    isci = _metin(ortam, "BASAK_ISCI_ADI", "basak-worker-1")
    if not _ISCI_ADI.match(isci):
        raise AyarHatasi(
            "BASAK_ISCI_ADI 1-64 karakter olmalı (harf, rakam, . _ -)")

    esik = _sayi(ortam, "BASAK_ISCI_ESIK", 90.0, 30.0, 3_600.0)
    kalp = _sayi(ortam, "BASAK_ISCI_KALP_ARALIK", 20.0, 5.0, 3_600.0)
    if kalp >= esik:
        raise AyarHatasi(
            "BASAK_ISCI_KALP_ARALIK, BASAK_ISCI_ESIK'ten küçük olmalı")

    return Ayarlar(
        anahtar=anahtar,
        isci=isci,
        dsn=_dsn(ortam),
        aralik=_sayi(ortam, "BASAK_ISCI_ARALIK", 1.0, 0.1, 60.0),
        kalp_aralik=kalp,
        esik=esik,
        zaman_asimi_ms=_sayi(
            ortam, "BASAK_ISCI_ZAMAN_ASIMI_MS", 15_000, 1_000, 120_000,
            tam=True),
        saglik_port=_sayi(
            ortam, "BASAK_ISCI_SAGLIK_PORT", 0, 0, 65_535, tam=True),
        surum=_metin(ortam, "BASAK_SURUM", "dev") or "dev",
    )
