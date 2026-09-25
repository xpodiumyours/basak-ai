"""brain/secici.py — Teknik sağlayıcı fallback sırası.

Kullanıcı metni, görev türü, karne veya araç alanı burada yorumlanmaz.
Yalnız registry.VARSAYILAN_SIRA korunur; erişilebilirlik, kota ve gerçek
API yetenekleri Brain katmanında teknik filtre olarak uygulanır.
"""

from brain import registry


def sec(mevcutlar=None):
    """Mevcut sağlayıcıları sabit teknik registry sırasına dizer."""
    if mevcutlar is None:
        mevcutlar = list(registry.VARSAYILAN_SIRA)
    else:
        temel = [a for a in registry.VARSAYILAN_SIRA if a in mevcutlar]
        bilinmeyen = [
            a for a in mevcutlar if a not in registry.VARSAYILAN_SIRA
        ]
        mevcutlar = temel + bilinmeyen
    return list(mevcutlar), "teknik registry sirasi"
