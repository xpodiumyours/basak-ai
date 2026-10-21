"""tools/gorsel.py — Gorsel uretme (Pollinations, anahtarsiz bedava).

Guvenlik kodda sabit: adres modelden GELMEZ, asagidaki sabit hosta
gider; boyutlar 256..2048 araligina kilitlenir. Dosya durum kokunun
uretilen/ altina benzersiz adla yazilir (git'e girmez).

Donus: {"result": "/gorsel/<ad>.jpg"} — uygulamanin servis ettigi goreli
adres. Yerel disk yolu tarayiciya verilmez (acilamaz).
"""

import logging
import os
import re
import urllib.parse
import urllib.request
import uuid

from chat.kimlik import durum_yolu

logger = logging.getLogger(__name__)

# None = durum_yolu("uretilen"); test/cagiran patch edebilir.
URETILEN_KOK = None

_GORSEL_AD = re.compile(r"^gorsel_[0-9a-f]{8}\.jpg$")


def uretilen_kok():
    """Uretilen gorsellerin klasoru: durum kokunun uretilen/ alti."""
    return URETILEN_KOK or durum_yolu("uretilen")


def gorsel_yolu_coz(ad):
    """Yalniz uretilen/ altindaki gorsel dosyasinin yolu; degilse None."""
    if not isinstance(ad, str) or not _GORSEL_AD.match(ad):
        return None
    return os.path.join(uretilen_kok(), ad)


_HOST = "image.pollinations.ai"


def gorsel_uret(aciklama, genislik=1024, yukseklik=1024,
                _acici=None):
    """Aciklamadan gorsel uretir. Donus: {"result": "/gorsel/<ad>"}."""
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
        kok = uretilen_kok()
        os.makedirs(kok, exist_ok=True)
        ad = "gorsel_%s.jpg" % uuid.uuid4().hex[:8]
        hedef = os.path.join(kok, ad)
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
        return {"result": "/gorsel/" + ad}
    except Exception as e:
        logger.warning("Gorsel uretilemedi: %s", e)
        return {"error": "Gorsel uretilemedi: %s" % e}
