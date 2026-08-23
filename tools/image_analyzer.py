"""tools/image_analyzer.py — Görüntü analiz aracı.

NVIDIA NIM multimodal modelleri (omni, glimmer) ile görüntü analizi yapar.
Görüntüyü base64 olarak modele gönderir, anlamlı açıklama/dÖner.

Destek: jpg, png, webp, gif (tek kare)
Model: nvidia/nemotron-3-nano-omni-30b-a3b-reasoning (varsayılan)
"""

import base64
import logging
import os
import mimetypes

logger = logging.getLogger(__name__)

# Varsayılan model (canlı testli, hızlı, Türkçe)
VARSAYILAN_MODEL = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"

# Desteklenen formatlar
DESTEKLENEN = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff")

# ayarlar.json'dan key oku
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_AYARLAR_DOSYASI = os.path.join(_BASE, "ayarlar.json")


def _nvidia_key_al() -> str:
    """NVIDIA API key'ini ayarlar.json veya environment'tan okur."""
    import json
    token = os.environ.get("NVIDIA_API_KEY", "")
    if token:
        return token
    try:
        with open(_AYARLAR_DOSYASI, "r", encoding="utf-8-sig") as f:
            ayarlar = json.load(f)
        return ayarlar.get("nvidia_key", "")
    except (OSError, json.JSONDecodeError):
        return ""


def _goruntu_b64(goruntu_yolu: str) -> tuple[str, str]:
    """Görüntüyü base64'e çevirir.

    Returns:
        (base64_string, mime_type)
    """
    if not os.path.isfile(goruntu_yolu):
        raise FileNotFoundError(f"Dosya bulunamadı: {goruntu_yolu}")

    mime, _ = mimetypes.guess_type(goruntu_yolu)
    if not mime:
        mime = "image/png"

    with open(goruntu_yolu, "rb") as f:
        icerik = f.read()

    # 10MB limit
    if len(icerik) > 10 * 1024 * 1024:
        raise ValueError("Görüntü çok büyük (maks 10MB)")

    return base64.b64encode(icerik).decode("ascii"), mime


def image_analyze(goruntu_yolu: str, soru: str = None,
                  model: str = None) -> dict:
    """Görüntüyü multimodal model ile analiz eder.

    Args:
        goruntu_yolu: Görüntü dosyasının yolu.
        soru: Görüntü hakkında sorulacak soru (varsayılan: "Bu görüntüyü açıkla").
        model: Kullanılacak model (varsayılan: omni).

    Returns:
        {"result": "açıklama", "model": "omni", "sure": "2.1s"}
    """
    # Doğrulama
    if not goruntu_yolu or not os.path.isfile(goruntu_yolu):
        return {"error": f"Dosya bulunamadı: {goruntu_yolu}"}

    uzanti = os.path.splitext(goruntu_yolu)[1].lower()
    if uzanti not in DESTEKLENEN:
        return {"error": f"Desteklenmeyen format: {uzanti}. İzin verilen: {', '.join(DESTEKLENEN)}"}

    # Key kontrolü
    nvidia_key = _nvidia_key_al()
    if not nvidia_key:
        return {"error": "NVIDIA API key bulunamadı (ayarlar.json -> nvidia_key)"}

    # Model seçimi
    kullanilacak_model = model or VARSAYILAN_MODEL

    try:
        from openai import OpenAI
        import time

        # base64 çevir
        img_b64, mime = _goruntu_b64(goruntu_yolu)

        # Prompt
        soru = (soru or "").strip()
        if not soru:
            soru = "Bu görüntüyü detaylı şekilde açıkla. Varsa metin, nesne, renk, konum bilgilerini ver. Türkçe cevap ver."

        client = OpenAI(api_key=nvidia_key, base_url="https://integrate.api.nvidia.com/v1", timeout=30.0)

        t0 = time.time()
        resp = client.chat.completions.create(
            model=kullanilacak_model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": soru},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{img_b64}"}}
                ]
            }],
            max_tokens=500,
            temperature=0.5,
        )
        sure = time.time() - t0

        icerik = (resp.choices[0].message.content or "").strip()
        if not icerik:
            return {"error": "Model boş yanıt döndü", "model": kullanilacak_model}

        return {
            "result": icerik,
            "model": kullanilacak_model,
            "sure": "%.1fs" % sure,
            "dosya": os.path.basename(goruntu_yolu),
        }

    except Exception as e:
        logger.error("Görüntü analiz hatası: %s", e)
        return {"error": str(e)[:200], "model": kullanilacak_model}


def image_analyze_url(gorsel_url: str, soru: str = None,
                      model: str = None) -> dict:
    """URL'deki görüntüyü analiz eder (base64'e çevirmez).

    Args:
        gorsel_url: Görüntü URL'si.
        soru: Görüntü hakkında soru.

    Returns:
        {"result": "açıklama", "model": "omni", "sure": "2.1s"}
    """
    nvidia_key = _nvidia_key_al()
    if not nvidia_key:
        return {"error": "NVIDIA API key bulunamadı"}

    kullanilacak_model = model or VARSAYILAN_MODEL

    try:
        from openai import OpenAI
        import time

        soru = (soru or "").strip()
        if not soru:
            soru = "Bu görüntüyü detaylı şekilde açıkla. Türkçe cevap ver."

        client = OpenAI(api_key=nvidia_key, base_url="https://integrate.api.nvidia.com/v1", timeout=30.0)

        t0 = time.time()
        resp = client.chat.completions.create(
            model=kullanilacak_model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": soru},
                    {"type": "image_url", "image_url": {"url": gorsel_url}}
                ]
            }],
            max_tokens=500,
            temperature=0.5,
        )
        sure = time.time() - t0

        icerik = (resp.choices[0].message.content or "").strip()
        return {
            "result": icerik or "Boş yanıt",
            "model": kullanilacak_model,
            "sure": "%.1fs" % sure,
        }

    except Exception as e:
        return {"error": str(e)[:200], "model": kullanilacak_model}
