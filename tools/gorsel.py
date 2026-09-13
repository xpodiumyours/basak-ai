"""tools/gorsel.py — Gorsel uretme (Pollinations, anahtarsiz bedava).

Guvenlik kodda sabit: adres modelden GELMEZ, asagidaki sabit hosta
gider; boyutlar 256..2048 araligina kilitlenir. Dosya data/uretilen/
altina benzersiz adla yazilir (git'e girmez).
"""

import logging
import os
import urllib.parse
import urllib.request
import uuid

logger = logging.getLogger(__name__)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URETILEN_KOK = os.path.join(BASE, "data", "uretilen")

_HOST = "image.pollinations.ai"


def gorsel_uret(aciklama, genislik=1024, yukseklik=1024,
                _acici=None):
    """Aciklamadan gorsel uretir. Donus: kaydedilen dosya yolu."""
    aciklama = (aciklama or "").strip()
    if not aciklama:
        return {"error": "Aciklama bos olamaz"}
    if len(aciklama) > 500:
        return {"error": "Aciklama cok uzun (en fazla 500 karakter)"}
    try:
        genislik = max(256, min(2048, int(genislik or 1024)))
        yukseklik = max(256, min(2048, int(yukseklik or 1024)))
    except (TypeError, ValueError):
        return {"error": "Boyut sayi olmali."}
    yol = "/prompt/%s?width=%d&height=%d&nologo=true" % (
        urllib.parse.quote(aciklama), genislik, yukseklik)
    try:
        os.makedirs(URETILEN_KOK, exist_ok=True)
        hedef = os.path.join(URETILEN_KOK,
                             "gorsel_%s.jpg" % uuid.uuid4().hex[:8])
        ac = _acici or urllib.request.urlopen
        istek = urllib.request.Request(
            "https://%s%s" % (_HOST, yol),
            headers={"User-Agent": "Basak/1.0"})
        with ac(istek, timeout=120) as yanit:
            tur = yanit.headers.get("Content-Type", "")
            if "image" not in tur:
                return {"error": "Gorsel alinamadi (tip: %s)" % tur}
            with open(hedef, "wb") as f:
                f.write(yanit.read(8 * 1024 * 1024))
        return {"result": hedef}
    except Exception as e:
        logger.warning("Gorsel uretilemedi: %s", e)
        return {"error": "Gorsel uretilemedi: %s" % e}
