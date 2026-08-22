"""brain/secici.py — Model Secim Motoru (P3, kural tabanli + seffaf).

Gorev turunu anahtar kelimelerle siniflandirir, saglayici sirasini
gerekcesiyle dondurur. Kurallar seffaf: hangi gorev turu hangi
saglayiciyi one aldigi acikca yazilir.

Genel sohbette saglayicilar sirayla distribute edilir — boylece
tek bir saglayicinin token limiti hici dolmaz (P3 optimizasyonu).
"""

import random
from brain import registry

# Gorev turleri ve anahtar kelimeleri (chat.py'deki eski _beyin_tercihi
# mantiginin genisletilmis hali)
_GOREV_KELIMELERI = {
    "kod": ["kod", "python", "javascript", "fonksiyon", "hata",
            "debug", "script", "regex", "yazılım", "programla",
            "css", "html", "sql", "api", "algoritma"],
    "arastirma": ["araştır", "öğren", "kaynak", "karşılaştır",
                  "nedir", "kimdir", "detaylı", "incele"],
    "hiz": ["hızlı", "çabuk", "acele", "anında", "şimdi"],
}

# Gorev turune gore one alinacak saglayicilar (registry gucleriyle uyumlu)
_TERCİHLER = {
    "kod": ["nvidia", "glm"],
    "arastirma": ["gemini", "cohere"],
    "hiz": ["groq", "cloudflare"],
}


def siniflandir(text):
    """Mesaji gorev turune ayirir: kod / arastirma / hiz / genel."""
    t = (text or "").lower()
    for tur, kelimeler in _GOREV_KELIMELERI.items():
        if any(k in t for k in kelimeler):
            return tur
    return "genel"


def sec(text=None, gorev_tipi=None, tools=False, mevcutlar=None):
    """Saglayici sirasini ve gerekceyi dondurur: (sirali_adlar, gerekce).

    - mevcutlar: su an kullanilabilir saglayici adlari (brain zinciri).
      None ise registry varsayilan sirasi kullanilir (test icin).
    - tools=True: tool destegi olmayan saglayicilar sona atilir.
    - Gerekce seffaf: "kod isi → nvidia one alindi" gibi okunabilir metin.
    """
    tip = gorev_tipi or siniflandir(text)

    if mevcutlar is None:
        mevcutlar = list(registry.VARSAYILAN_SIRA)
    else:
        # Registry varsayilan sirasina gore sabitlenmis temel sira
        temel = [a for a in registry.VARSAYILAN_SIRA if a in mevcutlar]
        bilinmeyen = [a for a in mevcutlar if a not in registry.VARSAYILAN_SIRA]
        mevcutlar = temel + bilinmeyen

    # Tool gerekiyorsa desteklemeyenler sona
    if tools:
        destekleyen = [a for a in mevcutlar if registry.tool_destegi_var_mi(a)]
        desteklemeyen = [a for a in mevcutlar
                         if not registry.tool_destegi_var_mi(a)]
        mevcutlar = destekleyen + desteklemeyen

    # Gorev turune gore one alma
    gerekce = "genel sohbet → varsayilan sira"
    onecelenen = []
    if tip in _TERCİHLER:
        tercih = [a for a in _TERCİHLER[tip] if a in mevcutlar]
        if tercih:
            kalan = [a for a in mevcutlar if a not in tercih]
            mevcutlar = tercih + kalan
            onecelenen = tercih
            gerekce = "%s isi → %s öne alındı" % (
                tip, ", ".join(registry.kart(a)["ad"] for a in tercih))
    elif tip == "genel" and len(mevcutlar) >= 3:
        # Genel sohbette ilk 3 saglayiciyi rastgele sirayla baslat.
        # Bu, tek saglayicinin token limitinin hici dolmasini onler.
        ilk_3 = mevcutlar[:3]
        kalan = mevcutlar[3:]
        random.shuffle(ilk_3)
        mevcutlar = ilk_3 + kalan
        gerekce = "genel sohbet → dagitilmis sira (" + ", ".join(
            registry.kart(a)["ad"] for a in ilk_3) + ")"

    return list(mevcutlar), gerekce
