"""chat/onbellek.py — Ayni mesajin tekrarini kotaya yazmama.

Neden var: kullanici mesaji kisa sure icinde IKINCI kez gonderirse (cift
tik, tekrar deneme, baglanti tekrari) ayni cevabi yeniden satin almak
bosuna kota harcamaktir. Butun bedava kota sayili oldugu icin bu dogrudan
kayiptir.

KURAL — bu bir davranis katmani DEGILDIR:
- Karar kullanicinin metninin ANLAMI uzerinden verilmez; yalniz TAM
  ESITLIK aranir (bosluk/buyuk-kucuk harf disinda hicbir normalizasyon
  yoktur, kelime listesi yoktur).
- Devreye girmesi icin bir ONCEKI kullanici mesajinin ayni olmasi sarttir;
  yani yalniz "ayni seyi arka arkaya iki kez yazdim" durumunu yakalar.
- Omur cok kisadir (OMUR_SN). Baska konudan sonra ayni soru sorulursa
  onbellek devreye GIRMEZ, model yeniden cagirilir.
- Yalniz arac KOSMAYAN turlar saklanir; arac kosan turun yan etkisi
  olabilecegi icin sonucu yeniden kullanilmaz.
"""

import re
import threading
import time

OMUR_SN = 120
TAVAN = 200

_KILIT = threading.Lock()
_KAYIT = {}          # {anahtar: (cevap, zaman)}


def anahtar(metin):
    """Tam esitlik icin sade anahtar: kirp + bosluklari tek + kucult.

    Kelime ayiklama/es anlam arama YOKTUR; yalniz yazim farkini (fazla
    bosluk, buyuk harf) esitler.
    """
    metin = (metin or "").strip()
    if not metin:
        return ""
    metin = re.sub(r"\s+", " ", metin)
    return metin.casefold()


def _son_kullanici(gecmis):
    for m in reversed(gecmis or []):
        if isinstance(m, dict) and m.get("role") == "user":
            return m.get("content") or ""
    return ""


def al(text, gecmis):
    """Onceki kullanici mesaji ayniysa ve kayit taze ise cevabi doner."""
    k = anahtar(text)
    if not k:
        return ""
    if anahtar(_son_kullanici(gecmis)) != k:
        return ""
    with _KILIT:
        kayit = _KAYIT.get(k)
    if not kayit:
        return ""
    cevap, zaman = kayit
    if time.time() - zaman > OMUR_SN:
        with _KILIT:
            _KAYIT.pop(k, None)
        return ""
    return cevap


def koy(text, cevap):
    """Arac kosmayan bir turun cevabini saklar. Bos deger saklanmaz."""
    k = anahtar(text)
    if not k or not cevap:
        return False
    simdi = time.time()
    with _KILIT:
        # Suresi dolmus kayitlari temizle; tavan asilirsa en eskiler gider.
        for anahtar_ in [a for a, (_, z) in _KAYIT.items()
                         if simdi - z > OMUR_SN]:
            _KAYIT.pop(anahtar_, None)
        if len(_KAYIT) >= TAVAN:
            for anahtar_ in sorted(_KAYIT, key=lambda a: _KAYIT[a][1])[
                    :len(_KAYIT) - TAVAN + 1]:
                _KAYIT.pop(anahtar_, None)
        _KAYIT[k] = (cevap, simdi)
    return True


def temizle():
    """Testler ve 'yeni sohbet' icin."""
    with _KILIT:
        _KAYIT.clear()
