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
import time

logger = logging.getLogger(__name__)

# Varsayılan model (canlı testli, hızlı, Türkçe)
VARSAYILAN_MODEL = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"

# 2026-09-26 ölçümü: ~2 MB fatura fotoğrafları NVIDIA'da 60 sn'de
# zaman aşımına uğruyor (6/6 çağrı). Zaman aşımından sonra 5 dk
# NVIDIA atlanır (Gemini/Kilo devralır); büyük görselde istek
# timeout'u 25 sn'ye iner. Serinleme başarısızlıkla tetiklenir,
# tercihle değil.
_NVIDIA_SERINLEME = 0.0
_NVIDIA_SERINME_SURE = 300.0
_NVIDIA_BUYUK_ESIK = 700 * 1024

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

    2026-09-26 ölçümü: ~2 MB fatura fotoğrafları NVIDIA'da zaman
    aşımına çarpıyordu. 700 KB'ı aşan görseller 1600 px'e indirilip
    JPEG'e çevrilir; OCR için fazlasıyla yeterli, tüm sağlayıcılara
    aynı küçük gider.

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

    if len(icerik) > _NVIDIA_BUYUK_ESIK:
        try:
            from PIL import Image
            import io as _io
            resim = Image.open(_io.BytesIO(icerik))
            resim.load()
            oran = min(1.0, 1600 / max(resim.size))
            if oran < 1.0:
                resim = resim.convert("RGB").resize(
                    (int(resim.width * oran), int(resim.height * oran)))
            tampon = _io.BytesIO()
            resim.save(tampon, format="JPEG", quality=88)
            icerik = tampon.getvalue()
            mime = "image/jpeg"
        except Exception as e:
            logger.debug("Kucultme atlandi: %s", e)

    return base64.b64encode(icerik).decode("ascii"), mime


def _gemini_goru(yol, soru):
    """Ikinci goz: Gemini ucretsiz katmanla fatura fotorafi okuma.

    NVIDIA dusmus olabilir (timeout/kota/429): ayni soru ikinci
    buluta sorulur (katalog hatti yedekligi). Donus image_analyzer
    ile ayni sekil: {"result"} / {"error"}. Anahtar yoksa hata
    doner, cagiran mevcut akisa devam eder.
    """
    import json as _json
    try:
        with open(_AYARLAR_DOSYASI, "r", encoding="utf-8-sig") as f:
            ayar = _json.load(f)
        anahtar = (os.environ.get("GEMINI_API_KEY") or ""
                   if isinstance(os.environ.get("GEMINI_API_KEY"), str)
                   else "")
        if not anahtar:
            anahtar = (ayar.get("gemini_key", "")
                       if isinstance(ayar, dict) else "")
        if not anahtar or not str(anahtar).strip():
            return {"error": "Gemini anahtari yok"}
        from openai import OpenAI as _OpenAI
        import time as _zaman
        img_b64, mime = _goruntu_b64(yol)
        soru = (soru or "").strip() or "Bu görüntüyü açıkla."
        istemci = _OpenAI(
            api_key=str(anahtar).strip(),
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            timeout=60.0, max_retries=0)
        baslangic = _zaman.time()
        yanit = istemci.chat.completions.create(
            model="gemini-3-flash-preview",
            messages=[{"role": "user", "content": [
                {"type": "text", "text": soru},
                {"type": "image_url",
                 "image_url": {"url": "data:%s;base64,%s" % (mime, img_b64)}},
            ]}],
            max_tokens=8192,
        )
        metin = ((yanit.choices[0].message.content) or "").strip()
        if not metin:
            return {"error": "Gemini bos dondu",
                    "model": "gemini-3-flash-preview"}
        return {"result": metin, "model": "gemini-3-flash-preview",
                "sure": "%.1fs" % (_zaman.time() - baslangic),
                "dosya": os.path.basename(yol)}
    except Exception as e:
        logger.warning("Gemini goru yedegi calismadi: %s", e)
        return {"error": "Gemini goru calismadi: %s" % str(e)[:200]}


def _kilo_goru(yol, soru):
    """Anahtarsiz ucuncu goz: mevcut Kilo Step 3.7 Flash goruntu modeli."""
    try:
        from brain.kilo import KiloClient
        img_b64, mime = _goruntu_b64(yol)
        soru = (soru or "").strip() or "Bu görüntüyü açıkla."
        istemci = KiloClient(model="stepfun/step-3.7-flash:free")
        yanit = istemci.goru_cevapla([{
            "role": "user",
            "content": [
                {"type": "text", "text": soru},
                {"type": "image_url",
                 "image_url": {"url": "data:%s;base64,%s" % (mime, img_b64)}},
            ],
        }])
        metin = (yanit.get("content") or "").strip() if isinstance(yanit, dict) else ""
        if not metin:
            return {"error": "Kilo goruntu modeli bos dondu"}
        return {
            "result": metin,
            "model": "stepfun/step-3.7-flash:free",
            "dosya": os.path.basename(yol),
        }
    except Exception as e:
        logger.warning("Kilo goru yedegi calismadi: %s", e)
        return {"error": "Kilo goru calismadi: %s" % str(e)[:200]}


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
    global _NVIDIA_SERINLEME
    # Doğrulama
    if not goruntu_yolu or not os.path.isfile(goruntu_yolu):
        return {"error": f"Dosya bulunamadı: {goruntu_yolu}"}

    uzanti = os.path.splitext(goruntu_yolu)[1].lower()
    if uzanti not in DESTEKLENEN:
        return {"error": f"Desteklenmeyen format: {uzanti}. İzin verilen: {', '.join(DESTEKLENEN)}"}

    # Key kontrolü. NVIDIA yoksa mevcut Gemini yedegi, o da yoksa
    # anahtarsiz Kilo Step 3.7 Flash denenir; fotograf yolu kapanmaz.
    # Serinleme suresince de NVIDIA atlanir (zaman asimi olcumu).
    nvidia_key = _nvidia_key_al()
    if nvidia_key and time.time() - _NVIDIA_SERINLEME < _NVIDIA_SERINME_SURE:
        nvidia_key = ""
    if not nvidia_key:
        yedek = _gemini_goru(goruntu_yolu, soru)
        if not yedek.get("error"):
            yedek["yedek"] = "gemini"
            return yedek
        kilo = _kilo_goru(goruntu_yolu, soru)
        if not kilo.get("error"):
            kilo["yedek"] = "kilo"
            return kilo
        return {
            "error": "Goruntu saglayicisi kullanilamadi [gemini: %s] [kilo: %s]"
                     % (yedek.get("error", ""), kilo.get("error", ""))
        }

    # Model seçimi
    kullanilacak_model = model or VARSAYILAN_MODEL

    try:
        from openai import OpenAI

        # base64 çevir
        img_b64, mime = _goruntu_b64(goruntu_yolu)

        # Prompt: soru yoksa notr varsayilan (model nasil anlatacagina
        # kendisi karar verir; davranis dayatma yok).
        soru = (soru or "").strip()
        if not soru:
            soru = "Bu görüntüyü açıkla."

        istek_zamani = (25.0 if len(img_b64) > _NVIDIA_BUYUK_ESIK
                        else 60.0)
        client = OpenAI(api_key=nvidia_key, base_url="https://integrate.api.nvidia.com/v1", timeout=istek_zamani, max_retries=0)

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
            max_tokens=4096,
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
        if "timed out" in str(e).lower() or "timeout" in str(e).lower():
            _NVIDIA_SERINLEME = time.time()
        # NVIDIA donmedi: ayni soru ikinci buluta sorulur
        # (katalog hatti yedekligi).
        yedek = _gemini_goru(goruntu_yolu, soru)
        if not yedek.get("error"):
            yedek["yedek"] = "gemini"
            return yedek
        kilo = _kilo_goru(goruntu_yolu, soru)
        if not kilo.get("error"):
            kilo["yedek"] = "kilo"
            return kilo
        return {
            "error": "%s [gemini: %s] [kilo: %s]"
                     % (str(e), yedek.get("error", ""), kilo.get("error", "")),
            "model": kullanilacak_model,
        }


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

        soru = (soru or "").strip()
        if not soru:
            soru = "Bu görüntüyü açıkla."

        client = OpenAI(api_key=nvidia_key, base_url="https://integrate.api.nvidia.com/v1", timeout=60.0, max_retries=0)

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
            max_tokens=4096,
        )
        sure = time.time() - t0

        icerik = (resp.choices[0].message.content or "").strip()
        return {
            "result": icerik or "Boş yanıt",
            "model": kullanilacak_model,
            "sure": "%.1fs" % sure,
        }

    except Exception as e:
        return {"error": str(e), "model": kullanilacak_model}
