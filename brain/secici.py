"""brain/secici.py — Model Secim Motoru (ozgur-ajan: passthrough).

2026-09-13 Faz 1: modeli kor eden siralama artiklari silindi.
Karari ZINCIR + model verir; secici yalniz registry sirasini korur.

Silinenler (AGENTS.md S0):
- _TOOL_IYILERI one-almasi (tanimiszdi, tools=True yolunda NameError)
- token-tahmini sona-atma (groq>180k, diger>50k)
- karne sona-atma (B1)
- ilk-3 random.shuffle dagitma
- cooldown yeniden-siralama (atlama brain/brain.py'de yapilir)

Imza korunur (test/uretim uyumlulugu): sec(text, gorev_tipi, tools,
mevcutlar, karne_kullan, cooldown) ayni parametreleri alir ama
siralama disi karar vermez.
"""

from brain import registry

# --- B1 kalintilari: imza/test uyumlulugu icin durur, sec() kullanmaz ---
_MIN_ORNEKLEM = 5
_BASARI_ESIK = 50.0


def _karne_ozetleri(mevcutlar):
    """Kullanim disi — geriye uyumluluk icin durur."""
    return {}


# Gorev turleri ve anahtar kelimeleri (2026-09-10: gunluk konusma
# kaliplari eklendi — noktasiz/harf eksik yazimlar da yakalanir)
def siniflandir(text):
    """Kelimeye gore gorev turu ayirma KALDIRILDI (2026-09-13)."""
    return "genel"


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
