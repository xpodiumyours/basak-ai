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
import threading
import time
import uuid

logger = logging.getLogger(__name__)

# 2026-09-21 oturum ayrimi: ayni anda iki yazici dosyayi bozmasin diye
# tum oku-degistir-yaz _KILIT altinda, yazma atomik (.tmp + os.replace,
# bkz. tools/tasks.py deseni). RLock: aktif_id icten de kilit alir.
_KILIT = threading.RLock()

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIZIN = os.path.join(BASE, "data", "sohbetler")
AKTIF_DOSYA = os.path.join(BASE, "data", "aktif_oturum")
ESKI_DOSYA = os.path.join(BASE, "gecmis.json")


def _dizin():
    os.makedirs(DIZIN, exist_ok=True)
    return DIZIN


def _sid_ok(sid):
    """Sohbet kimligi yol-guvenligi: 1-64 karakter [A-Za-z0-9_-].

    Kullanici metnine bakilmaz; yalniz dosya adinin dizinden kacmasi
    engellenir (bkz. file_ops yol cozucu deseni). Gecersizse None/False.
    """
    if not isinstance(sid, str):
        return False
    if not (1 <= len(sid) <= 64):
        return False
    for ch in sid:
        if not (("a" <= ch <= "z") or ("A" <= ch <= "Z")
                or ("0" <= ch <= "9") or ch in ("-", "_")):
            return False
    return True


def _yol(sid):
    return os.path.join(_dizin(), "%s.json" % sid)


def _oku(sid):
    if not _sid_ok(sid):
        return None
    try:
        with open(_yol(sid), "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _yaz(oturum):
    """Atomik yaz: once .tmp, sonra os.replace (yarim JSON gorunmez)."""
    try:
        with _KILIT:
            if not _sid_ok(oturum.get("id")):
                return False
            yol = _yol(oturum["id"])
            gecici = yol + ".tmp"
            with open(gecici, "w", encoding="utf-8") as f:
                json.dump(oturum, f, ensure_ascii=False)
            os.replace(gecici, yol)
        return True
    except OSError as e:
        logger.warning("Oturum yazilamadi: %s", e)
        return False


def _aktif_yaz_atomik(sid):
    """Aktif kimlik dosyasini atomik yazar (yarim okuma yok)."""
    try:
        with _KILIT:
            os.makedirs(os.path.dirname(AKTIF_DOSYA) or ".", exist_ok=True)
            gecici = AKTIF_DOSYA + ".tmp"
            with open(gecici, "w", encoding="utf-8") as f:
                f.write(sid)
            os.replace(gecici, AKTIF_DOSYA)
    except OSError:
        pass


def aktif_id():
    """Su anki oturum kimligi (yoksa yeni uretilir). Kilitli + atomik."""
    with _KILIT:
        try:
            with open(AKTIF_DOSYA, "r", encoding="utf-8") as f:
                sid = (f.read() or "").strip()
                if sid:
                    return sid
        except OSError:
            pass
        sid = uuid.uuid4().hex[:8]
        try:
            os.makedirs(os.path.dirname(AKTIF_DOSYA) or ".", exist_ok=True)
            gecici = AKTIF_DOSYA + ".tmp"
            with open(gecici, "w", encoding="utf-8") as f:
                f.write(sid)
            os.replace(gecici, AKTIF_DOSYA)
        except OSError:
            pass
        return sid


def _aktif_koy(sid):
    _aktif_yaz_atomik(sid)


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
    """Bir soru-cevap ciftini oturuma ekler.

    sid verilirse o sohbete yazar (iki kisi karismaz); verilmezse eski
    davranis: aktif oturuma. Oku-degistir-yaz kilit altinda, yazma atomik.
    """
    if sid:
        if not _sid_ok(sid):
            kayit_sid = aktif_id()
        else:
            kayit_sid = sid
    else:
        kayit_sid = aktif_id()
    with _KILIT:
        o = _oku(kayit_sid) or {"id": kayit_sid, "baslik": "",
                                "olustu": time.time(),
                                "guncellendi": time.time(), "mesajlar": []}
        o["mesajlar"] += [{"role": "user", "content": soru},
                          {"role": "assistant", "content": cevap}]
        o["mesajlar"] = o["mesajlar"][-60:]
        if not o.get("baslik") and soru:
            o["baslik"] = _baslik(soru)
        o["guncellendi"] = time.time()
        _yaz(o)
    return kayit_sid


def ac(sid):
    """Oturum mesajlarini dondurur (yoksa None)."""
    if not _sid_ok(sid):
        return None
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
    with _KILIT:
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
    if not _sid_ok(sid):
        return False
    try:
        os.remove(_yol(sid))
        return True
    except OSError:
        return False
