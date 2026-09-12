"""brain/model_family.py — Gerçek model ailesi çözücü (P3, saf fonksiyon).

Provider adı model ailesi DEGILDIR (harness arastirmasi kritik bulgusu):
NVIDIA aynı sağlayıcı altında GPT-OSS/Nemotron/Kimi/DeepSeek barındırır,
OpenRouter/Kilo çalışma anında :free model seçer. Bu modül
(provider + istemci.model) ikilisinden harness kararları için
kullanılacak aile etiketini üretir.

Kurallar:
- Tanınmayan model ASLA "güçlü" varsayılmaz → "unknown".
- Hiçbir girdi yükseltmez (None/bos → "unknown").
- NVIDIA iç fallback'i dışarıdan görünmez; yapılandırılmış model çözülür.
"""

# Aile etiketleri (secici/harness bu kelimeleri tanır)
GPT_OSS = "gpt-oss"
LLAMA = "llama"
LLAMA_SMALL = "llama-small"
MISTRAL = "mistral"
GEMMA = "gemma"
QWEN = "qwen"
GLM = "glm"
GLM_FLASH = "glm-flash"
GEMINI_FLASH = "gemini-flash"
GEMINI_FLASH_LITE = "gemini-flash-lite"
GEMINI_PRO = "gemini-pro"
GEMINI = "gemini"
COMMAND_A = "command-a"
COMMAND_R = "command-r"
NEMOTRON = "nemotron"
KIMI = "kimi"
DEEPSEEK = "deepseek"
MINIMAX = "minimax"
KILO_AUTO = "kilo-auto"   # sunucu tarafı dinamik yönlendirme
UNKNOWN = "unknown"

# Küçük Llama göstergeleri (harness: en kısa prompt, en az araç).
# NOT: "17b" icindeki "7b" gibi alt-dizgi tuzaklarina karsi SINIR
# duyarli eslesme sarttir — _kucuk_llama_mi() kullanilir.
import re as _re

_KUCUK_BOY = _re.compile(r"(?:^|[^0-9])(1b|2b|3b|7b|8b)(?:[^0-9]|$)")
_KUCUK_AD = ("small", "mini", "tiny")


def _kucuk_llama_mi(mid):
    if any(k in mid for k in _KUCUK_AD):
        return True
    return bool(_KUCUK_BOY.search(mid))


def _jenerik_aile(mid):
    """Provider-bağımsız model-id eşleşmesi. Bulamazsa None."""
    if "nemotron" in mid:
        return NEMOTRON
    if "gpt-oss" in mid or "gpt_oss" in mid:
        return GPT_OSS
    if "deepseek" in mid:
        return DEEPSEEK
    if "kimi" in mid or "moonshot" in mid:
        return KIMI
    if "minimax" in mid:
        return MINIMAX
    if "qwen" in mid:
        return QWEN
    if "mistral" in mid or "mixtral" in mid:
        return MISTRAL
    if "gemma" in mid:
        return GEMMA
    if "llama" in mid:
        return LLAMA_SMALL if _kucuk_llama_mi(mid) else LLAMA
    if "glm" in mid or "zai" in mid:
        return GLM_FLASH if "flash" in mid else GLM
    return None


def coz(provider, model_id):
    """(provider, model_id) → aile etiketi. Asla yükseltmez."""
    mid = str(model_id or "").lower().strip()
    prov = str(provider or "").lower().strip()
    if not mid:
        return UNKNOWN

    if prov == "gemini":
        if "flash-lite" in mid or "flash_lite" in mid:
            return GEMINI_FLASH_LITE
        if "flash" in mid:
            return GEMINI_FLASH
        if "pro" in mid:
            return GEMINI_PRO
        return GEMINI if "gemini" in mid else UNKNOWN

    if prov == "cohere":
        if "command-a" in mid or "command_a" in mid:
            return COMMAND_A
        if "command-r" in mid or "command_r" in mid:
            return COMMAND_R
        return UNKNOWN

    if prov in ("kimi",):
        return KIMI
    if prov in ("deepseek",):
        return DEEPSEEK
    if prov == "qwen":
        return QWEN

    if prov == "glm":
        if "flash" in mid:
            return GLM_FLASH
        return GLM if "glm" in mid else UNKNOWN

    if prov == "kilo":
        if "kilo-auto" in mid:
            return KILO_AUTO
        return _jenerik_aile(mid) or UNKNOWN

    if prov == "openrouter":
        return _jenerik_aile(mid) or UNKNOWN

    if prov == "yerel":
        if "qwen" in mid:
            return QWEN
        if "llama" in mid:
            return LLAMA_SMALL if _kucuk_llama_mi(mid) else LLAMA
        if "mistral" in mid:
            return MISTRAL
        if "gemma" in mid:
            return GEMMA
        if "phi" in mid:
            return "phi"
        return UNKNOWN

    # groq / cloudflare / nvidia / genel: önce jenerik eşleşme
    return _jenerik_aile(mid) or UNKNOWN
