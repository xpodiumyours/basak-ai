"""chat/oturum.py — Eski sohbet listesi (oturumlar).

2026-09-10 (Casper): tek gecmis.json vardi, eskiler kayboluyordu.
Artik her sohbet data/<kullanici>/sohbetler/<id>.json'da durur; kenar
cubugundan acilir. Aktif sohbet yine gecmis.json aynasidir — eski
kod/testler bozulmaz.

2026-09-23: yollar kisiye gore chat.kimlik uzerinden cozulur.
DIZIN/AKTIF_DOSYA None ise dinamiktir; testler monkeypatch ile
ezer (None olmayan deger = o kullanilir).

Dosya bicimi: {"id","baslik","olustu","guncellendi","sahip","mesajlar":[...]}
"""

import json
import logging
import os
import re
import time
import uuid

logger = logging.getLogger(__name__)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# sid yalniz guvenli karakterler icerir — yol kacisi (`../`, ayraclar)
# mumkun degil. Uretimde uuid.hex[:8]; disaridan gelen sid de ayni
# denyeden gecer.
_SID_DESEN = re.compile(r"^[A-Za-z0-9_-]+$")


def _gecerli_sid(sid):
    return bool(sid) and _SID_DESEN.match(str(sid)) is not None

# None = kimlikten hesapla (uretim). Test monkeypatch ederse o deger kullanilir.
DIZIN = None
AKTIF_DOSYA = None
ESKI_DOSYA = None  # geriye uyumluluk; okuma yapilmaz


def _kullanici_koku():
    from chat.kimlik import kullanici_koku
    return kullanici_koku()


def _dizin():
    if DIZIN is not None:
        yol = DIZIN
    else:
        yol = os.path.join(_kullanici_koku(), "sohbetler")
    os.makedirs(yol, exist_ok=True)
    return yol


def _aktif_dosya():
    if AKTIF_DOSYA is not None:
        return AKTIF_DOSYA
    return os.path.join(_kullanici_koku(), "aktif_oturum")


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


def _sahip_kaydet(oturum):
    """Oturuma sahip damgası basar (yoksa aktif kişi)."""
    if "sahip" not in oturum:
        from chat.kimlik import aktif_kullanici
        oturum["sahip"] = aktif_kullanici()
    return oturum


def sahip_mi(sid, kid):
    """sid bu kişiye ait mi? Sahip alanı yoksa casper (eski kayıt)."""
    if not _gecerli_sid(sid):
        return False
    kayit = _oku(sid)
    if kayit is None:
        return False
    from chat.kimlik import VARSAYILAN_KULLANICI
    sahip = kayit.get("sahip") or VARSAYILAN_KULLANICI
    return sahip == kid


def aktif_id():
    """Su anki oturum kimligi (yoksa yeni uretilir)."""
    dosya = _aktif_dosya()
    try:
        with open(dosya, "r", encoding="utf-8") as f:
            sid = (f.read() or "").strip()
            # Bozuk/pislik dolu dosya yeni uretilir; gecersiz sid
            # sonrasi yol kacisina donusmesin.
            if sid and _gecerli_sid(sid):
                return sid
    except OSError:
        pass
    sid = uuid.uuid4().hex[:8]
    try:
        os.makedirs(os.path.dirname(dosya), exist_ok=True)
        with open(dosya, "w", encoding="utf-8") as f:
            f.write(sid)
    except OSError:
        pass
    return sid


def _aktif_koy(sid):
    dosya = _aktif_dosya()
    try:
        os.makedirs(os.path.dirname(dosya), exist_ok=True)
        with open(dosya, "w", encoding="utf-8") as f:
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
    """Aktif kisinin oturumlari: [{id, baslik, guncellendi, adet}].

    2026-09-23: sahip filtresi — dizin yolu kisiye gore olsa bile
    eski/sahipsiz kayit baska kisinin listesine dusmesin (sahipsiz =
    casper, eski kayit kurali).
    """
    from chat.kimlik import VARSAYILAN_KULLANICI, aktif_kullanici
    kid = aktif_kullanici()
    dizin = _dizin()
    out = []
    for ad in os.listdir(dizin):
        if not ad.endswith(".json"):
            continue
        o = _oku(ad[:-5])
        if not o:
            continue
        if (o.get("sahip") or VARSAYILAN_KULLANICI) != kid:
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
    _sahip_kaydet(o)
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
    if not _gecerli_sid(sid):
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
    if eskileri_ayna:
        sid = aktif_id()
        ilk = next((m.get("content", "") for m in eskileri_ayna
                    if m.get("role") == "user"
                    and (m.get("content") or "").strip()), "")
        _yaz(_sahip_kaydet(
            {"id": sid, "baslik": _baslik(ilk) or "Sohbet",
             "olustu": time.time(), "guncellendi": time.time(),
             "mesajlar": eskileri_ayna[-60:]}))
    sid = uuid.uuid4().hex[:8]
    _aktif_koy(sid)
    return sid


def sil(sid):
    """Oturumu siler."""
    if not _gecerli_sid(sid):
        return False
    try:
        os.remove(_yol(sid))
        return True
    except OSError:
        return False
