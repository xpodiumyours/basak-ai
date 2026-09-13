"""brain/secici.py — Saglayici surekliligi.

Kullanici mesaji siniflandirilmaz. Anahtar kelime, gorev turu, arac varligi,
karne veya tahmini token butcesi saglayici sirasini degistirmez. Bu modul
yalniz mevcut saglayicilari registry'deki sabit fallback sirasinda dondurur.
"""

from brain import registry


def siniflandir(_text):
    """Eski cagri uyumlulugu; kullanici mesaji artik siniflandirilmaz."""
    return "genel"


def sec(text=None, gorev_tipi=None, tools=False, mevcutlar=None,
        karne_kullan=False, cooldown=None):
    """Mevcut saglayicilari sabit fallback sirasinda dondurur.

    Parametreler eski cagri uyumlulugu icin korunur; hicbiri kullanici
    mesajina veya arac durumuna gore siralama yapmaz.
    """
    del text, gorev_tipi, tools, karne_kullan, cooldown

    if mevcutlar is None:
        return list(registry.VARSAYILAN_SIRA), "sabit fallback sirasi"

    temel = [a for a in registry.VARSAYILAN_SIRA if a in mevcutlar]
    bilinmeyen = [a for a in mevcutlar if a not in registry.VARSAYILAN_SIRA]
    return temel + bilinmeyen, "sabit fallback sirasi"
