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
        "gunluk_istek": 80,   # ~200K token/gun / ~2.5K token istek tahmini
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
        "not": "Trial key ile ucretsiz; Command R hizli ve tool destekli.",
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
        "not": "Model etkinlesmesi bekleniyor; canlaninca zincire girer.",
    },
    "nvidia": {
        "ad": "NVIDIA NIM",
        "ucretsiz": True,
        "tools": True,
        "gucleri": ["kod", "goruntu", "video"],
        "gunluk_istek": None,
        "not": "GPT-OSS-20b + Gemma-4 + Nemotron + Omni + Kozmos; kod/goruntu/video.",
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
# cloudflare cikarildi: 401 Authentication error (anahtar gecersiz, 2026-08-23 olculdu)
VARSAYILAN_SIRA = [
    "groq", "glm", "cohere", "nvidia",
    "openrouter", "qwen", "gemini",
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
