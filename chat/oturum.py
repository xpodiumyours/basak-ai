"""chat/oturum.py — Eski sohbet listesi (oturumlar).

2026-09-10 (Casper): tek gecmis.json vardi, eskiler kayboluyordu.
Artik her sohbet data/sohbetler/<id>.json'da durur; kenar cubugundan
acilir. Aktif sohbet yine gecmis.json aynasidir — eski kod/testler
bozulmaz.

Dosya bicimi: {"id","baslik","olustu","guncellendi","mesajlar":[{"role","content"}]}
"""

import json
import logging
import os
import time
import uuid

logger = logging.getLogger(__name__)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIZIN = os.path.join(BASE, "data", "sohbetler")
AKTIF_DOSYA = os.path.join(BASE, "data", "aktif_oturum")
ESKI_DOSYA = os.path.join(BASE, "gecmis.json")


def _dizin():
    os.makedirs(DIZIN, exist_ok=True)
    return DIZIN


def _yol(sid):
    return os.path.join(_dizin(), "%s.json" % sid)


def _oku(sid):
    try:
        with open(_yol(sid), "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _yaz(oturum):
    try:
        with open(_yol(oturum["id"]), "w", encoding="utf-8") as f:
            json.dump(oturum, f, ensure_ascii=False)
        return True
    except OSError as e:
        logger.warning("Oturum yazilamadi: %s", e)
        return False


def aktif_id():
    """Su anki oturum kimligi (yoksa yeni uretilir)."""
    try:
        with open(AKTIF_DOSYA, "r", encoding="utf-8") as f:
            sid = (f.read() or "").strip()
            if sid:
                return sid
    except OSError:
        pass
    sid = uuid.uuid4().hex[:8]
    try:
        with open(AKTIF_DOSYA, "w", encoding="utf-8") as f:
            f.write(sid)
    except OSError:
        pass
    return sid


def _aktif_koy(sid):
    try:
        with open(AKTIF_DOSYA, "w", encoding="utf-8") as f:
            f.write(sid)
    except OSError:
        pass


def _baslik(metin):
    metin = re_temizle(metin)
    return metin or "Sohbet"


def re_temizle(metin):
    import re as _re
    return _re.sub(r"\s+", " ", str(metin or "")).strip()


def liste():
    """Tum oturumlar: [{id, baslik, guncellendi, adet}] (yeniden eskiye)."""
    _dizin()
    out = []
    for ad in os.listdir(DIZIN):
        if not ad.endswith(".json"):
            continue
        o = _oku(ad[:-5])
        if not o:
            continue
        out.append({
            "id": o.get("id", ad[:-5]),
            "baslik": o.get("baslik") or "Sohbet",
            "guncellendi": o.get("guncellendi", 0),
            "adet": len(o.get("mesajlar", [])),
        })
    out.sort(key=lambda x: x["guncellendi"], reverse=True)
    return out


def kaydet_cift(soru, cevap, sid=None):
    """Bir soru-cevap ciftini aktif oturuma ekler."""
    sid = sid or aktif_id()
    o = _oku(sid) or {"id": sid, "baslik": "", "olustu": time.time(),
                      "guncellendi": time.time(), "mesajlar": []}
    o["mesajlar"] += [{"role": "user", "content": soru},
                      {"role": "assistant", "content": cevap}]
    o["mesajlar"] = o["mesajlar"][-60:]
    if not o.get("baslik") and soru:
        o["baslik"] = _baslik(soru)
    o["guncellendi"] = time.time()
    _yaz(o)
    return sid


def ac(sid):
    """Oturum mesajlarini dondurur (yoksa None)."""
    o = _oku(sid)
    if not o:
        return None
    _aktif_koy(sid)
    return o.get("mesajlar", [])


def yeni(eskileri_ayna=None):
    """Yeni bos sohbet baslatir; mevcut aynayi arsive kaldirir.

    eskileri_ayna: su anki gecmis.json icerigi (liste). Bossa arsiv yok.
    Donus: yeni oturum kimligi.
    """
    eskileri_ayna = eskileri_ayna or []
    if eskileri_ayna:
        sid = aktif_id()
        ilk = next((m.get("content", "") for m in eskileri_ayna
                    if m.get("role") == "user"
                    and (m.get("content") or "").strip()), "")
        _yaz({"id": sid, "baslik": _baslik(ilk) or "Sohbet",
              "olustu": time.time(), "guncellendi": time.time(),
              "mesajlar": eskileri_ayna[-60:]})
    sid = uuid.uuid4().hex[:8]
    _aktif_koy(sid)
    return sid


def sil(sid):
    """Oturumu siler."""
    try:
        os.remove(_yol(sid))
        return True
    except OSError:
        return False
