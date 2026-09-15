"""brain/gemini_embed.py — Anlam vektorleri (Gemini, ucretsiz).

Hafiza motorunun `_embed_fn` yuvasina takilir: not/soru metnini
anlam vektorune cevirir, motor da benzer anlamlilari bulur.
Boyut 768 — motorun vec0 tablosuyla birebir uyar, tablo degismez.

Resmi API ayrimi (P1): indekslenen belge RETRIEVAL_DOCUMENT, sorgu
RETRIEVAL_QUERY taskType ile alinir. 768 Matryoshka kisaltmasinda
L2 normalizasyonu uygulanir (uzaklik karsilastirmasi icin).

Anahtar yoksa veya hata olursa None doner; motor sessizce
kelime aramasina (BM25) duser. Asla patlamaz, kural koymaz.
"""

import logging
import math
import os

import requests

logger = logging.getLogger(__name__)

MODEL = "gemini-embedding-001"
BOYUT = 768
_URL = ("https://generativelanguage.googleapis.com/v1beta/models/"
        "%s:embedContent" % MODEL)

_BELGE = "RETRIEVAL_DOCUMENT"
_SORGU = "RETRIEVAL_QUERY"


def _anahtar_al():
    try:
        from brain.brain import _ayar_yukle
        ayar = _ayar_yukle()
    except Exception:
        ayar = {}
    return (os.environ.get("GEMINI_API_KEY") or ayar.get("gemini_key")
            or "").strip()


def _normalize(vektor):
    """L2 normalizasyonu (Matryoshka 768 kisaltmasi icin)."""
    try:
        norm = math.sqrt(sum(float(x) * float(x) for x in vektor))
    except Exception:
        return list(vektor)
    if norm <= 0:
        return list(vektor)
    return [float(x) / norm for x in vektor]


def vektor_al(metin, gorev=_BELGE):
    """Tek metnin anlam vektorunu dondurur; olmazsa None.

    gorev: RETRIEVAL_DOCUMENT (indeks) veya RETRIEVAL_QUERY (sorgu).
    Bilinmeyen deger belge sayilir (guvenli varsayilan).
    """
    metin = (metin or "").strip()
    if not metin:
        return None
    if gorev not in (_BELGE, _SORGU):
        gorev = _BELGE
    key = _anahtar_al()
    if not key:
        return None
    try:
        r = requests.post(
            _URL,
            params={"key": key},
            json={"content": {"parts": [{"text": metin[:8000]}]},
                  "taskType": gorev,
                  "outputDimensionality": BOYUT},
            timeout=(5, 20),
        )
        r.raise_for_status()
        vektor = (r.json().get("embedding") or {}).get("values")
        if vektor and len(vektor) == BOYUT:
            return _normalize(list(vektor))
        logger.warning("Beklenmeyen vektor boyutu: %s",
                       len(vektor) if vektor else 0)
        return None
    except requests.RequestException as e:
        logger.warning("Vektor alinamadi (BM25-only mod): %s", e)
        return None


def sorgu_vektoru(metin):
    """Sorgu metni icin vektor (RETRIEVAL_QUERY)."""
    return vektor_al(metin, gorev=_SORGU)


def embed_fn(metin, gorev=_BELGE):
    """Motorun yuvasi: ayni sozlesme, hata yutmaz (motor yutar)."""
    return vektor_al(metin, gorev=gorev)
