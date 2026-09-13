"""tools/hafiza.py — Hafizada derin arama (salt-okunur).

Sohbette sonuclar otomatik gelir (ilk 20); bu alet modelin
"o konuyu daha derin ara" demesidir. Motor ayni (kelime + anlam),
yazinca degil okuyunca calisir. Yan etki yok.
"""

import logging

logger = logging.getLogger(__name__)

_DERINLIK = 5


def hafiza_ara(sorgu):
    """Hafizada arar. Donus: en ilgili en fazla 5 kayit (metin)."""
    sorgu = (sorgu or "").strip()
    if not sorgu:
        return {"error": "Arama metni bos olamaz"}
    try:
        from chat import context as ctx
        motor = ctx.hafiza_al()
    except Exception as e:
        return {"error": "Hafiza acilamadi: %s" % e}
    if not motor:
        return {"error": "Hafiza su an kapali."}
    try:
        sonuclar = motor.ara(sorgu, limit=_DERINLIK)
    except Exception as e:
        return {"error": "Arama basarisiz: %s" % e}
    if not sonuclar:
        return {"result": "Hafizada bulunamadi: '%s'" % sorgu}
    satirlar = []
    for s in sonuclar:
        metin = (s.get("text") or "").strip()
        satirlar.append("- %s" % metin)
    return {"result": "\n".join(satirlar)}
