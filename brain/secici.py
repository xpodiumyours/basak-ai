"""brain/secici.py — teknik saglayici siralama katmani.

Basak artik kullanici mesajini kod/arastirma/hiz diye siniflandirip modele
zeka puani vermez, performans karnesiyle semantik siralama yapmaz ve
saglayicilari rastgele oynatmaz. Secim yalniz teknik nedenlerle yapilir:
mevcutluk, arac destegi ve gecici cooldown. Boylece model yeteneklerine
Basak tarafindan gorev-temelli mudahale edilmez.
"""

import time

from brain import registry


def siniflandir(text):
    """Geriye uyum icin tum isleri genel kabul eder."""
    return "genel"


def sec(text=None, gorev_tipi=None, tools=False, mevcutlar=None,
        karne_kullan=False, cooldown=None):
    """Saglayicilari yalniz teknik uygunluga gore siralar.

    - Registry sirasi sabit temel siradir.
    - Arac varsa, tool calling destekleyen saglayicilar once gelir.
    - Aktif cooldown'daki saglayicilar sona gider.
    - Mesaj icerigi, karne ve tahmini token limitleri sirayi degistirmez.
    """
    if mevcutlar is None:
        mevcutlar = list(registry.VARSAYILAN_SIRA)
    else:
        temel = [a for a in registry.VARSAYILAN_SIRA if a in mevcutlar]
        bilinmeyen = [a for a in mevcutlar if a not in registry.VARSAYILAN_SIRA]
        mevcutlar = temel + bilinmeyen

    gerekce = "teknik fallback sirasi"

    if tools:
        destekli = [a for a in mevcutlar if registry.tool_destegi_var_mi(a)]
        desteksiz = [a for a in mevcutlar
                     if not registry.tool_destegi_var_mi(a)]
        mevcutlar = destekli + desteksiz
        gerekce = "arac uyumlu teknik fallback sirasi"

    if cooldown:
        now = time.time()
        aktif = [a for a in mevcutlar if cooldown.get(a, 0) > now]
        if aktif:
            mevcutlar = [a for a in mevcutlar if a not in aktif] + aktif
            gerekce += " | cooldown: " + ", ".join(aktif)

    return list(mevcutlar), gerekce
