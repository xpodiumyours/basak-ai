"""brain/secici.py — Model Secim Motoru (ozgur-ajan: passthrough).

2026-09-13 Faz 1: modeli kor eden siralama artiklari silindi.
Karari ZINCIR + model verir; secici yalniz registry sirasini korur.

2026-09-15 P0 temizligi: B1 kalintisi sabitler ve siniflandirici govdesi
kaldirildi. Imza yalniz cagri uyumlulugu icin durur; siralama disi
karar verilmez. Secim yalniz teknik gerceklere birakilir: erisilebilirlik
(musaitlik), ucretsiz olma, rate-limit/cooldown atlama ve API ozelligi
(tool destegi) — hepsi brain/brain.py + registry kartinda ele alinir.
Yeni akilli router YAZILMAZ.
"""

from brain import registry


def sec(text=None, gorev_tipi=None, tools=False, mevcutlar=None,
        karne_kullan=False, cooldown=None):
    """Saglayici sirasini ve gerekceyi dondurur: (sirali_adlar, gerekce).

    Ozgu-ajan: registry.VARSAYILAN_SIRA korunur, baska karar verilmez.
    Parametreler yalniz uyumluluk icin durur (brain.py ayni sekilde
    cagirir; karne/cooldown/tools siralamayi degistirmez).
    """
    if mevcutlar is None:
        mevcutlar = list(registry.VARSAYILAN_SIRA)
    else:
        # Registry varsayilan sirasina gore sabitlenmis temel sira
        temel = [a for a in registry.VARSAYILAN_SIRA if a in mevcutlar]
        bilinmeyen = [a for a in mevcutlar if a not in registry.VARSAYILAN_SIRA]
        mevcutlar = temel + bilinmeyen

    gerekce = "genel sohbet → varsayilan sira"
    return list(mevcutlar), gerekce
