"""brain/registry.py — Model Registry (P3).

Her saglayicinin statik karti: ucretsiz mi, tool calling destekliyor mu,
gucleri ne, gunluk istek limiti kac. Saglik durumu (cooldown) burada degil,
kota.py'de tutulur.

Limitler gercek gozlemlerden gelir:
- Groq gpt-oss-20b: token/gun limiti 200000 (2026-08-22 429 mesajindan)
- Gemini flash ucretsiz katman: 20 istek/gun (2026-08-22 429 mesajindan)
"""

# Gucleri etiketleri secici motorunun anladigi standart degerlerdir:
# hiz, kod, arastirma, genel, uzun-baglam
SAGLAYICILAR = {
    "groq": {
        "ad": "Groq",
        "ucretsiz": True,
        "tools": True,
        "gucleri": ["hiz", "genel"],
        # B3 (2026-08-24): gercek butce token. 200000 sayisi 2026-08-22
        # 429 mesajindan ("Used 197.355 / Limit 200.000"). Eski
        # gunluk_istek=80 TAHMINIYDI — kota artik gercek tokeni sorar.
        "gunluk_token": 200000,
        "not": "Ucretsiz ve cok hizli; token/gun limiti dar.",
    },
    "gemini": {
        "ad": "Gemini",
        "ucretsiz": True,
        "tools": True,
        "gucleri": ["arastirma", "uzun-baglam"],
        "gunluk_istek": 20,   # ucretsiz katman gozlemlenen limit
        "not": "Ucretsiz katmanda gunluk 20 istek; arastirmaya saklanir.",
    },
    "glm": {
        "ad": "GLM",
        "ucretsiz": True,
        "tools": True,
        "gucleri": ["kod", "genel"],
        "gunluk_istek": None,
        "not": "Z.ai ucretsiz kontingent; limit bilinmedigi icin sayac takip eder.",
    },
    "cloudflare": {
        "ad": "Cloudflare",
        "ucretsiz": True,
        "tools": True,
        "gucleri": ["genel", "hiz"],
        "gunluk_istek": None,
        "not": "Workers AI ucretsiz Llama/Mistral; GPU kaynaklanma sinirli.",
    },
    "cohere": {
        "ad": "Cohere",
        "ucretsiz": True,
        "tools": True,
        "gucleri": ["genel", "arastirma"],
        "gunluk_istek": None,
        # Resmi belge (docs.cohere.com/docs/rate-limits): deneme bileti
        # ayda toplam 1000 soru + dakikada 20 soru. Gunluk degil AYLIK.
        "aylik_istek": 1000,
        "not": "Trial key: ayda 1000 soru; Command R hizli ve tool destekli.",
    },
    "deepseek": {
        "ad": "DeepSeek",
        "ucretsiz": False,
        "tools": True,
        "gucleri": ["kod", "genel"],
        "gunluk_istek": None,
        "not": "UCRETLI — varsayilan olarak engelli; Casper acikca izin verirse calisir.",
    },
    "qwen": {
        "ad": "QwenCloud",
        "ucretsiz": True,
        "tools": True,
        "gucleri": ["genel"],
        "gunluk_istek": None,
        # 2026-09-09: hesap etkinlesmesi bekleniyor (403). Casper
        # etkinlestirene kadar brain zincire KATMAZ (brain.py'deki
        # _QWEN_BEKLEMEDE bayragi). Kart burada durur, sira korunur.
        "etkin": False,
        "not": "UYKUDA — Model etkinlesmesi bekleniyor; canlaninca zincire girer.",
    },
    "nvidia": {
        "ad": "NVIDIA NIM",
        "ucretsiz": True,
        "tools": True,
        "gucleri": ["kod", "goruntu", "video"],
        "gunluk_istek": None,
        "not": "GPT-OSS-20b + Gemma-4 + Nemotron + Omni + Kozmos; kod/goruntu/video.",
    },
    "kilo": {
        "ad": "Kilo Gateway",
        "ucretsiz": True,
        "tools": True,
        "gucleri": ["genel", "kod"],
        "gunluk_istek": None,   # sinir saatlik (200 istek/saat/IP), gunluk degil
        # Resmi davranis: saatte 200 soru/IP. Gunluk karta islenmez.
        "saatlik_istek": 200,
        "not": "Anahtarsiz calisir; 200 istek/saat/IP. Basari dusuk "
               "(%25, 2026-09 gozlemi) — one alinmaz, yedek durur. "
               "Ucretsiz katman gonderilen yazilari kaydedebilir — "
               "Casper 2026-08-23'te bunu bilerek onayladi.",
    },
    "openrouter": {
        "ad": "OpenRouter",
        "ucretsiz": True,
        "tools": True,
        "gucleri": ["genel"],
        "gunluk_istek": 50,   # :free modeller tipik ucretsiz katman limiti
        "not": "Sadece :free modeller; son care bulut.",
    },
    "yerel": {
        "ad": "Ollama (yerel)",
        "ucretsiz": True,
        "tools": True,
        "gucleri": ["genel"],
        "gunluk_istek": None,
        "not": "Internet/kota bitse bile calisir — son care.",
    },
}

# Varsayilan oncelik sirasi (gorev turuna gore secici yeniden siralar).
# Ucretli saglayici sonda: kazayla cagrilmasin.
# 2026-09-09 (tam tespit): olcum gercegine gore dizeildi —
# GLM sinirsiz bedava + guvenilir, Cloudflare 0 hata, Groq hizli,
# Nvidia guclu, Cohere dusuk basarili, Kilo %25 ile yedek,
# Gemini gunluk 20'de biter, OpenRouter gunluk 50'de biter,
# Qwen UYKUDA (etkinlesince one alinir). Kilo-once kurali kaldirildi.
# DeepSeek karti asagida durur (ucretli oldugu bilinsin) ama zincire
# HIC girmez — adaptoru yok, testler ucretli oldugunu dogrular.
VARSAYILAN_SIRA = [
    "glm", "cloudflare", "groq", "nvidia", "cohere", "kilo",
    "gemini", "openrouter", "qwen",
]


def kart(ad):
    """Saglayici kartini dondurur; bilinmeyen isimde guvenli bos kart."""
    return SAGLAYICILAR.get(
        ad,
        {
            "ad": ad,
            "ucretsiz": True,
            "tools": True,
            "gucleri": [],
            "gunluk_istek": None,
            "not": "Registry'de kaydi yok.",
        },
    )


def ucretli_mi(ad):
    return not kart(ad)["ucretsiz"]


def tool_destegi_var_mi(ad):
    return bool(kart(ad)["tools"])
