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



def _kalan_sure(deadline_monotonic, varsayilan):
    """Toplam is butcesinden bu cagriya kalabilecek saniyeyi hesaplar."""
    if deadline_monotonic is None:
        return float(varsayilan)
    kalan = float(deadline_monotonic) - time.monotonic()
    return max(0.0, min(float(varsayilan), kalan))


def _goruntu_b64(goruntu_yolu: str) -> tuple[str, str]:
    """Goruntuyu tek standarda getirip base64'e cevirir."""
    if not os.path.isfile(goruntu_yolu):
        raise FileNotFoundError(f"Dosya bulunamadı: {goruntu_yolu}")
    mime, _ = mimetypes.guess_type(goruntu_yolu)
    if not mime:
        mime = "image/png"
    with open(goruntu_yolu, "rb") as f:
        icerik = f.read()
    if len(icerik) > 10 * 1024 * 1024:
        raise ValueError("Görüntü çok büyük (maks 10MB)")
    try:
        from PIL import Image, ImageOps
        import io as _io
        resim = Image.open(_io.BytesIO(icerik))
        resim.load()
        try:
            yon = resim.getexif().get(274, 1)
        except Exception:
            yon = 1
        yon_duzeltildi = yon not in (None, 1)
        if yon_duzeltildi:
            resim = ImageOps.exif_transpose(resim)
        oran = min(1.0, 1600 / max(resim.size))
        normalize = yon_duzeltildi or oran < 1.0 or len(icerik) > _NVIDIA_BUYUK_ESIK
        if normalize:
            resim = resim.convert("RGB")
            if oran < 1.0:
                resim = resim.resize(
                    (max(1, int(resim.width * oran)),
                     max(1, int(resim.height * oran))),
                    Image.Resampling.LANCZOS)
            tampon = _io.BytesIO()
            resim.save(tampon, format="JPEG", quality=88, optimize=True)
            icerik = tampon.getvalue()
            mime = "image/jpeg"
    except Exception as e:
        logger.debug("Goruntu normalizasyonu atlandi: %s", e)
    return base64.b64encode(icerik).decode("ascii"), mime


def _gemini_goru(yol, soru, deadline_monotonic=None):
    """Ikinci goz: Gemini. Cagri toplam fatura butcesini asamaz."""
    import json as _json
    try:
        anahtar = os.environ.get("GEMINI_API_KEY", "")
        if not anahtar:
            try:
                with open(_AYARLAR_DOSYASI, "r", encoding="utf-8-sig") as f:
                    ayar = _json.load(f)
            except (OSError, ValueError):
                ayar = {}
            anahtar = ayar.get("gemini_key", "") if isinstance(ayar, dict) else ""
        if not str(anahtar or "").strip():
            return {"error": "Gemini anahtari yok"}
        sure = _kalan_sure(deadline_monotonic, 35.0 if deadline_monotonic is not None else 60.0)
        if sure < 3.0:
            return {"error": "Goruntu okuma zaman butcesi doldu"}
        from openai import OpenAI as _OpenAI
        import time as _zaman
        img_b64, mime = _goruntu_b64(yol)
        soru = (soru or "").strip() or "Bu görüntüyü açıkla."
        istemci = _OpenAI(api_key=str(anahtar).strip(),
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            timeout=sure, max_retries=0)
        baslangic = _zaman.time()
        yanit = istemci.chat.completions.create(
            model="gemini-3-flash-preview",
            messages=[{"role": "user", "content": [
                {"type": "text", "text": soru},
                {"type": "image_url",
                 "image_url": {"url": "data:%s;base64,%s" % (mime, img_b64)}}]}],
            max_tokens=8192)
        metin = ((yanit.choices[0].message.content) or "").strip()
        if not metin:
            return {"error": "Gemini bos dondu", "model": "gemini-3-flash-preview"}
        return {"result": metin, "model": "gemini-3-flash-preview",
                "sure": "%.1fs" % (_zaman.time()-baslangic),
                "dosya": os.path.basename(yol)}
    except Exception as e:
        logger.warning("Gemini goru yedegi calismadi: %s", e)
        return {"error": "Gemini goru calismadi: %s" % str(e)[:200]}


def _kilo_goru(yol, soru, deadline_monotonic=None):
    """Ucuncu goz: Kilo Step 3.7 Flash. Cagri butceyle sinirlidir."""
    try:
        sure = _kalan_sure(deadline_monotonic, 25.0 if deadline_monotonic is not None else 60.0)
        if sure < 3.0:
            return {"error": "Goruntu okuma zaman butcesi doldu"}
        from brain.kilo import KiloClient
        img_b64, mime = _goruntu_b64(yol)
        soru = (soru or "").strip() or "Bu görüntüyü açıkla."
        istemci = KiloClient(model="stepfun/step-3.7-flash:free")
        yanit = istemci.goru_cevapla([{"role": "user","content": [
            {"type": "text", "text": soru},
            {"type": "image_url",
             "image_url": {"url": "data:%s;base64,%s" % (mime, img_b64)}}]}],
            timeout=sure)
        metin = (yanit.get("content") or "").strip() if isinstance(yanit, dict) else ""
        if not metin:
            return {"error": "Kilo goruntu modeli bos dondu"}
        return {"result": metin, "model": "stepfun/step-3.7-flash:free",
                "dosya": os.path.basename(yol)}
    except Exception as e:
        logger.warning("Kilo goru yedegi calismadi: %s", e)
        return {"error": "Kilo goru calismadi: %s" % str(e)[:200]}


def image_analyze(goruntu_yolu: str, soru: str = None,
                  model: str = None, deadline_monotonic=None,
                  kabul=None) -> dict:
    """Tek seferlik, butceli saglayici zinciriyle goruntu analiz eder."""
    global _NVIDIA_SERINLEME
    if not goruntu_yolu or not os.path.isfile(goruntu_yolu):
        return {"error": f"Dosya bulunamadı: {goruntu_yolu}"}
    uzanti = os.path.splitext(goruntu_yolu)[1].lower()
    if uzanti not in DESTEKLENEN:
        return {"error": f"Desteklenmeyen format: {uzanti}. İzin verilen: {', '.join(DESTEKLENEN)}"}
    hatalar = []
    def _degerlendir(ad, sonuc, yedek=False):
        if not isinstance(sonuc, dict):
            hatalar.append("%s: gecersiz yanit" % ad); return None
        if sonuc.get("error"):
            hatalar.append("%s: %s" % (ad, sonuc.get("error"))); return None
        metin = str(sonuc.get("result") or "")
        if kabul is not None:
            try:
                uygun = bool(kabul(metin))
            except Exception as e:
                logger.warning("Goruntu kalite kapisi calismadi: %s", e)
                uygun = False
            if not uygun:
                hatalar.append("%s: kalite kapisini gecemedi" % ad); return None
        if yedek:
            sonuc["yedek"] = ad
        return sonuc
    nvidia_key = _nvidia_key_al()
    if nvidia_key and time.time()-_NVIDIA_SERINLEME < _NVIDIA_SERINME_SURE:
        nvidia_key = ""
    if nvidia_key:
        kullanilacak_model = model or VARSAYILAN_MODEL
        try:
            from openai import OpenAI
            img_b64, mime = _goruntu_b64(goruntu_yolu)
            soru2 = (soru or "").strip() or "Bu görüntüyü açıkla."
            varsayilan = 25.0 if len(img_b64) > _NVIDIA_BUYUK_ESIK else 60.0
            if deadline_monotonic is not None:
                varsayilan = min(varsayilan, 35.0)
            sure = _kalan_sure(deadline_monotonic, varsayilan)
            if sure < 3.0:
                hatalar.append("nvidia: goruntu okuma zaman butcesi doldu")
            else:
                client = OpenAI(api_key=nvidia_key,
                    base_url="https://integrate.api.nvidia.com/v1",
                    timeout=sure, max_retries=0)
                t0 = time.time()
                resp = client.chat.completions.create(
                    model=kullanilacak_model,
                    messages=[{"role": "user","content": [
                        {"type": "text","text": soru2},
                        {"type": "image_url",
                         "image_url": {"url": f"data:{mime};base64,{img_b64}"}}]}],
                    max_tokens=4096)
                icerik = (resp.choices[0].message.content or "").strip()
                sonuc = ({"result": icerik, "model": kullanilacak_model,
                          "sure": "%.1fs" % (time.time()-t0),
                          "dosya": os.path.basename(goruntu_yolu)}
                         if icerik else {"error": "Model boş yanıt döndü",
                                        "model": kullanilacak_model})
                kabul_edilen = _degerlendir("nvidia", sonuc)
                if kabul_edilen is not None:
                    return kabul_edilen
        except Exception as e:
            logger.error("Görüntü analiz hatası: %s", e)
            if "timed out" in str(e).lower() or "timeout" in str(e).lower():
                _NVIDIA_SERINLEME = time.time()
            hatalar.append("nvidia: %s" % str(e)[:180])
    if _kalan_sure(deadline_monotonic, 3600.0) >= 3.0:
        sonuc = _gemini_goru(goruntu_yolu, soru, deadline_monotonic=deadline_monotonic)
        kabul_edilen = _degerlendir("gemini", sonuc, yedek=True)
        if kabul_edilen is not None:
            return kabul_edilen
    if _kalan_sure(deadline_monotonic, 3600.0) >= 3.0:
        sonuc = _kilo_goru(goruntu_yolu, soru, deadline_monotonic=deadline_monotonic)
        kabul_edilen = _degerlendir("kilo", sonuc, yedek=True)
        if kabul_edilen is not None:
            return kabul_edilen
    if not hatalar:
        hatalar.append("goruntu okuma zaman butcesi doldu")
    return {"error": "Goruntu saglayicilari sonuca ulasamadi [%s]" % " | ".join(hatalar)}

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
