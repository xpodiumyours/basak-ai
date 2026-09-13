"""brain/registry.py — Sağlayıcı kartları ve sabit fallback sırası.

Kullanıcı mesajına, anahtar kelimeye veya görev türüne göre sıralama yapılmaz.
Sıra yalnız ücretsiz sağlayıcılar arasında genel kalite/fallback önceliğidir.
"""

SAGLAYICILAR = {
    "groq": {
        "ad": "Groq",
        "ucretsiz": True,
        "tools": True,
        "gucleri": ["hiz", "genel"],
        "gunluk_token": 200000,
        "not": "Ucretsiz ve cok hizli; token/gun limiti dar.",
    },
    "gemini": {
        "ad": "Gemini",
        "ucretsiz": True,
        "tools": True,
        "gucleri": ["arastirma", "uzun-baglam"],
        "gunluk_istek": 20,
        "not": "Ucretsiz katmanda gunluk 20 istek.",
    },
    "glm": {
        "ad": "GLM",
        "ucretsiz": True,
        "tools": True,
        "gucleri": ["kod", "genel"],
        "gunluk_istek": None,
        "not": "Z.ai ucretsiz kontingent.",
    },
    "cloudflare": {
        "ad": "Cloudflare",
        "ucretsiz": True,
        "tools": True,
        "gucleri": ["genel", "hiz"],
        "gunluk_istek": None,
        "not": "Workers AI ucretsiz katman.",
    },
    "cohere": {
        "ad": "Cohere",
        "ucretsiz": True,
        "tools": True,
        "gucleri": ["genel", "arastirma"],
        "gunluk_istek": None,
        "aylik_istek": 1000,
        "not": "Trial key: ayda 1000 soru.",
    },
    "deepseek": {
        "ad": "DeepSeek",
        "ucretsiz": False,
        "tools": True,
        "gucleri": ["kod", "genel"],
        "gunluk_istek": None,
        "not": "Ucretli; varsayilan zincirde degil.",
    },
    "genel": {
        "ad": "Ozel Saglayici",
        "ucretsiz": False,
        "tools": True,
        "gucleri": ["genel"],
        "gunluk_istek": None,
        "not": "Kullanicinin ozel saglayicisi; varsa en sonda yedek.",
    },
    "kimi": {
        "ad": "Kimi (Moonshot)",
        "ucretsiz": False,
        "tools": True,
        "gucleri": ["genel", "kod"],
        "gunluk_istek": None,
        "not": "Ucretli; varsayilan zincirde degil.",
    },
    "qwen": {
        "ad": "QwenCloud",
        "ucretsiz": True,
        "tools": True,
        "gucleri": ["genel"],
        "gunluk_istek": None,
        "etkin": False,
        "not": "Saglayici erisilebilirse fallback zincirine katilir.",
    },
    "nvidia": {
        "ad": "NVIDIA NIM",
        "ucretsiz": True,
        "tools": True,
        "gucleri": ["kod", "goruntu", "video"],
        "gunluk_istek": None,
        "not": "NVIDIA NIM ucretsiz modelleri.",
    },
    "kilo": {
        "ad": "Kilo Gateway",
        "ucretsiz": True,
        "tools": True,
        "gucleri": ["genel", "kod"],
        "gunluk_istek": None,
        "saatlik_istek": 200,
        "not": "Anahtarsiz ucretsiz gateway; 200 istek/saat/IP.",
    },
    "openrouter": {
        "ad": "OpenRouter",
        "ucretsiz": True,
        "tools": True,
        "gucleri": ["genel"],
        "gunluk_istek": 50,
        "not": "Sadece :free modeller.",
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

# Mesaj içeriğinden bağımsız sabit fallback sırası.
# Cloudflare'ın varsayılan 3B modeli güçlü ücretsiz sağlayıcıların ardındadır.
VARSAYILAN_SIRA = [
    "glm", "cohere", "gemini", "groq", "nvidia", "openrouter",
    "cloudflare", "kilo", "qwen",
]


def kart(ad):
    """Sağlayıcı kartını döndürür; bilinmeyen isimde güvenli boş kart."""
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
