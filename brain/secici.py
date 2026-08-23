"""brain/secici.py — Model Secim Motoru (P3, kural tabanli + seffaf).

Gorev turunu anahtar kelimelerle siniflandirr, saglayici sirasini
gerekcesiyle dondurur. Kurallar seffaf: hangi gorev turu hangi
saglayiciyi one aldigi acikca yazilir.

Genel sohbette saglayicilar sirayla distribute edilerek
boylece tek bir saglayicinin token limiti hici dolmaz (P3 optimizasyonu).
"""


def route_by_intent(text, available_models):
    """Kullanıcı isteğine göre en uygun modeli seçer (intent bazlı routing).

    Args:
        text: Kullanıcı mesajı.
        available_models: Kullanılabilir model listesi (brain.yerel_modeller() çıktısı).

    Returns:
        (model_adi, sebep) tuple'u - seçilen model ve Selection sebebi.

    Kurallar:
    1. Kod/software işleri → NVIDIA model (code generation optimization)
    2. Yaratıcı yazı/öneri → Qwen model (dengeli yaratıcılık)
    3. Detaylı analiz/karşılaştırma → Groq (70b versatile)
    4. Diğer tümler → Varsayılan/local model
    """
    text_lower = (text or "").lower()

    # 1. KOD İŞI → NVIDIA
    kod_kelimeler = ["kod", "function", "sınıf", "import", "debug",
                     "script", "yap", "geliştir", "program"]
    if any(k in text_lower for k in kod_kelimeler):
        for m in available_models:
            if m.lower() in ["nvidia", "glm", "nvidia-neemotron"]:
                return (m, "kod isi: NVIDIA model one alindi")
        # Eğer NVIDIA yoksa, ilk available modeli döndür
        return (available_models[0] if available_models else None,
                "kod isi: NVIDIA bulunamaya, varsayilan kullanildi")

    # 2. YARATICI YAZI -> Qwen
    yaratici_kelimeler = ["hikaye", "poe", "tavsiye", "artikel", "siri",
                          "yarat", "etikat", "kriyatif"]
    if any(k in text_lower for k in yaratici_kelimeler):
        for m in available_models:
            if "qwen" in m.lower():
                return (m, "yaratici yazı: Qwen model one alindi")
        for m in available_models:
            if m != available_models[0]:
                return (m, "yaratici yazı: Qwen yok,kinci tercih alindi")
        return (available_models[0] if available_models else None,
                "yaratici yazı: Qwen bulunamaya, varsayılan kullanildi")

    # 3. DETAİLİ ANALİZ/KAŞIF → Groq
    analiz_kelimeler = ["detaylı", "analiz", "karşılaştırma", "derin",
                        "hakkında", "karşılaştır", "derinlemesine"]
    if any(k in text_lower for k in analiz_kelimeler):
        for m in available_models:
            if "groq" in m.lower() or "llama-3" in m.lower():
                return (m, "detaylı analiz: Groq/llama-3 one alindi")
        # Groq yoksa, en güçlü available model
        return (available_models[1] if len(available_models) > 1 else available_models[0] if available_models else None,
                "detaylı analiz: Groq bulunamaya, ikinci model kullanıldı")

    # 4. DEFAULT → Varsayılan/local model
    if available_models:
        return (available_models[0], "varsayılan model kullanıldı")
    return (None, "model bulunamadı")

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
