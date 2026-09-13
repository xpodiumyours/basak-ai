"""brain/gemini_embed.py — Anlam vektorleri (Gemini, ucretsiz).

Hafiza motorunun `_embed_fn` yuvasina takilir: not/soru metnini
anlam vektorune cevirir, motor da benzer anlamlilari bulur.
Boyut 768 — motorun vec0 tablosuyla birebir uyar, tablo degismez.

Uyumlu uc (OpenAI bicimi) boy kisaltmadigi icin ana kapidan
(embedContent + outputDimensionality) alinir; ek paket yok
(requests zaten bagimli).

Anahtar yoksa veya hata olursa None doner; motor sessizce
kelime aramasina (BM25) duser. Asla patlamaz, kural koymaz.
"""

import logging
import os

import requests

logger = logging.getLogger(__name__)

MODEL = "gemini-embedding-001"
BOYUT = 768
_URL = ("https://generativelanguage.googleapis.com/v1beta/models/"
        "%s:embedContent" % MODEL)


def _anahtar_al():
    try:
        from brain.brain import _ayar_yukle
        ayar = _ayar_yukle()
    except Exception:
        ayar = {}
    return (os.environ.get("GEMINI_API_KEY") or ayar.get("gemini_key")
            or "").strip()


def vektor_al(metin):
    """Tek metnin anlam vektorunu dondurur; olmazsa None."""
    metin = (metin or "").strip()
    if not metin:
        return None
    key = _anahtar_al()
    if not key:
        return None
    try:
        r = requests.post(
            _URL,
            params={"key": key},
            json={"content": {"parts": [{"text": metin[:8000]}]},
                  "outputDimensionality": BOYUT},
            timeout=(5, 20),
        )
        r.raise_for_status()
        vektor = (r.json().get("embedding") or {}).get("values")
        if vektor and len(vektor) == BOYUT:
            return list(vektor)
        logger.warning("Beklenmeyen vektor boyutu: %s",
                       len(vektor) if vektor else 0)
        return None
    except requests.RequestException as e:
        logger.warning("Vektor alinamadi (BM25-only mod): %s", e)
        return None


def embed_fn(metin):
    """Motorun yuvasi: ayni sozlesme, hata yutmaz (motor yutar)."""
    return vektor_al(metin)
