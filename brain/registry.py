"""brain/registry.py — sağlayıcı teknik kayıtları.

Bu dosya model zekâsını veya görev uygunluğunu puanlamaz. Yalnız Başak'ın
otomatik ücretsiz zinciri için teknik/maliyet bilgisi ve sabit fallback sırası
tutar. Canlı kota ve geçici hatalar runtime cooldown ile yönetilir.
"""

SAGLAYICILAR = {
    "groq": {
        "ad": "Groq",
        "ucretsiz": True,
        "tools": True,
        "gucleri": [],  # geriye uyumluluk; semantik router kullanmaz
        "not": "Free hesapta kota aşımı hata verir; ücretli hesap katmanı uygulamadan doğrulanamaz.",
    },
    "gemini": {
        "ad": "Gemini",
        "ucretsiz": True,
        "tools": True,
        "gucleri": [],
        "not": "Free project kullanılabilir; ücretli billing bağlı project uygulamadan doğrulanamaz.",
    },
    "glm": {
        "ad": "GLM",
        "ucretsiz": True,
        "tools": True,
        "gucleri": [],
        "not": "Mevcut ücretsiz Flash entegrasyonu; kota/hata runtime fallback ile yönetilir.",
    },
    "cloudflare": {
        "ad": "Cloudflare",
        "ucretsiz": True,
        "tools": True,
        "gucleri": [],
        "not": "Workers Free günlük ücretsiz kota sağlar; Paid hesapta aşım faturalandırılabilir.",
    },
    "cohere": {
        "ad": "Cohere",
        "ucretsiz": True,
        "tools": True,
        "gucleri": [],
        "not": "Trial/evaluation anahtarı ücretsizdir; production anahtarı ücretlidir ve uygulamadan ayırt edilemez.",
    },
    "nvidia": {
        "ad": "NVIDIA NIM",
        "ucretsiz": True,
        "tools": True,
        "gucleri": [],
        "not": "Developer erişimi geliştirme/test için ücretsizdir; production koşulları ayrıdır.",
    },
    "kilo": {
        "ad": "Kilo Gateway",
        "ucretsiz": True,
        "tools": True,
        "gucleri": [],
        "saatlik_istek": 200,
        "not": "kilo-auto/free kullanılır; kredi gerektirmeyen ücretsiz rota.",
    },
    "openrouter": {
        "ad": "OpenRouter",
        "ucretsiz": True,
        "tools": True,
        "gucleri": [],
        "not": "openrouter/free veya :free model kullanılır; otomatik ücretli model seçilmez.",
    },
    "qwen": {
        "ad": "QwenCloud",
        "ucretsiz": True,
        "tools": True,
        "gucleri": [],
        "etkin": False,
        "not": "Direct API süreli ücretsiz kota sonrası ücret yazabilir; sıfır maliyet için otomatik zincirde kapalı.",
    },
    "yerel": {
        "ad": "Ollama (yerel)",
        "ucretsiz": True,
        "tools": True,
        "gucleri": [],
        "not": "Yerel ve ücretsiz; bulutlar çalışmazsa son çare.",
    },
    "deepseek": {
        "ad": "DeepSeek",
        "ucretsiz": False,
        "tools": True,
        "gucleri": [],
        "not": "Ücretli direct API; otomatik ücretsiz zincire girmez.",
    },
    "genel": {
        "ad": "Özel Sağlayıcı",
        "ucretsiz": False,
        "tools": True,
        "gucleri": [],
        "not": "Kullanıcının özel/ücretli endpoint'i; otomatik ücretsiz zincire girmez.",
    },
    "kimi": {
        "ad": "Kimi (Moonshot)",
        "ucretsiz": False,
        "tools": True,
        "gucleri": [],
        "not": "Direct ücretli API; otomatik ücretsiz zincire girmez.",
    },
}

# Sabit teknik fallback sırası. Kullanıcı mesajının içeriği bu sırayı değiştirmez.
# Cooldown/rate-limit/zaman aşımı gibi gerçek teknik durumlar runtime'da geçici
# olarak sağlayıcıyı atlatabilir. Direct Qwen ayrıca maliyet kilidiyle kapalıdır.
VARSAYILAN_SIRA = [
    "glm", "cloudflare", "groq", "nvidia", "cohere", "kilo",
    "gemini", "openrouter", "qwen",
]


def kart(ad):
    """Sağlayıcı kartını döndür; bilinmeyen kaynak otomatik ücretsiz sayılmaz."""
    return SAGLAYICILAR.get(
        ad,
        {
            "ad": ad,
            "ucretsiz": False,
            "tools": False,
            "gucleri": [],
            "not": "Registry'de kayıt yok; otomatik zincire alınmamalı.",
        },
    )


def ucretli_mi(ad):
    return not bool(kart(ad).get("ucretsiz", False))


def tool_destegi_var_mi(ad):
    return bool(kart(ad).get("tools", False))
