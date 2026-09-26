"""tools/yerel_goru.py — Başak'ın kendi gözü (yerel VLM).

Ollama üzerinden koşan görü modeli (qwen2.5vl:3b) fatura fotoğrafını
okur. Bulut kotası doluysa, internet yoksa veya gizlilik istenirse
bu göz devreye girer; yoksa/kapalıysa çağrı yapılmaz, bulut yolu
çalışır (Faz 2 bağımsızlığı korunur).

Yeni ARAÇ DEĞİLDIR — katalog.py içinden çağrılan yardımcıdır;
üç-yer kuralını tetiklemez.
"""

import base64
import json
import logging
import os
import urllib.request

logger = logging.getLogger(__name__)

OLLAMA_ADRES = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
YEREL_MODEL = "qwen2.5vl:3b"

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_AYARLAR_DOSYASI = os.path.join(_BASE, "ayarlar.json")

# Büyük fiş fotoğrafını göze vermeden önce bu ene indir (PIL varsa).
# Küçük resim hem hızlı hem yeterince okunaklıdır.
AZAMI_KENAR = 1600


def _ayarlar():
    try:
        with open(_AYARLAR_DOSYASI, "r", encoding="utf-8-sig") as f:
            veri = json.load(f)
        return veri if isinstance(veri, dict) else {}
    except (OSError, ValueError):
        return {}


def acik_mi():
    """Yerel göz denensin mi? Kapalı yazılmadıkça evet.

    BASAK_YEREL_GORU=1 ayarlar dosyasındaki kapatmayı ezer —
    bulut kotası dolduğunda/imtihanda bu göz zorla denenir.
    """
    durum = os.environ.get("BASAK_YEREL_GORU", "").lower()
    if durum in ("0", "kapali"):
        return False
    if durum in ("1", "acik", "evet"):
        return True
    return not _ayarlar().get("yerel_goru_kapali", False)


def _kucult(goruntu_yolu):
    """Görüntüyü AZAMI_KENAR altına indirir, bayt döner."""
    with open(goruntu_yolu, "rb") as f:
        ham = f.read()
    try:
        from PIL import Image
        import io as _io
        resim = Image.open(_io.BytesIO(ham))
        resim.load()
        oran = min(1.0, AZAMI_KENAR / max(resim.size))
        if oran < 1.0:
            resim = resim.convert("RGB").resize(
                (int(resim.width * oran), int(resim.height * oran)))
            tampon = _io.BytesIO()
            resim.save(tampon, format="JPEG", quality=88)
            return tampon.getvalue()
    except Exception as e:
        logger.debug("Kucultme atlandi: %s", e)
    return ham


def _istek(yol, veri=None, sure=5):
    govde = json.dumps(veri or {}).encode("utf-8") if veri else None
    istek = urllib.request.Request(
        OLLAMA_ADRES + yol, data=govde,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(istek, timeout=sure) as yanit:
        return json.load(yanit)


def musait():
    """Ollama ayakta ve göz modeli inik mi? (hızlı yoklama)"""
    if not acik_mi():
        return False
    try:
        etiketler = _istek("/api/tags", sure=3)
        adlar = [m.get("name", "") for m in etiketler.get("models", [])]
        return any(a.split(":")[0] == YEREL_MODEL.split(":")[0]
                   for a in adlar)
    except Exception as e:
        logger.debug("Yerel goz yok: %s", e)
        return False


def oku(goruntu_yolu, soru):
    """Fotoğrafı yerel gözle okur. Dönüş: {"result"} / {"error"}."""
    if not goruntu_yolu or not os.path.isfile(goruntu_yolu):
        return {"error": "Dosya bulunamadı: '%s'." % (goruntu_yolu or "")}
    try:
        ham = _kucult(goruntu_yolu)
    except OSError:
        return {"error": "Dosya okunamadı."}
    if len(ham) > 10 * 1024 * 1024:
        return {"error": "Dosya çok büyük (en fazla 10MB)."}
    try:
        yanit = _istek("/api/chat", {
            "model": YEREL_MODEL,
            "stream": False,
            "messages": [{
                "role": "user",
                "content": soru or "Bu görüntüyü açıkla.",
                "images": [base64.b64encode(ham).decode("ascii")],
            }],
        }, sure=300)
    except Exception as e:
        logger.warning("Yerel goz hatasi: %s", e)
        return {"error": "Yerel göz çalışmadı: %s" % str(e)[:120]}
    metin = ((yanit.get("message") or {}).get("content", "") or "").strip()
    if not metin:
        return {"error": "Yerel göz boş döndü."}
    return {"result": metin, "model": YEREL_MODEL}
