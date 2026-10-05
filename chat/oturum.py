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
import threading
import time
import uuid

logger = logging.getLogger(__name__)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# sid yalniz guvenli karakterler icerir — yol kacisi (`../`, ayraclar)
# mumkun degil. Uretimde uuid.hex[:8]; disaridan gelen sid de ayni
# denyeden gecer.
_SID_DESEN = re.compile(r"^[A-Za-z0-9_-]+$")

# 2026-10-03: ayni oturuma eszamanli yazma korumasi.
#
# Web sunucusu istekleri paralel isler: app.py her mesaji
# asyncio.to_thread ile ayri thread'de kosturur. kaydet_cift bir
# oku-degistir-yaz dongusuydu, yazma da "w" modunda (once kirpar,
# sonra yazar) — iki istek ayni dosyayi ayni anda islerse ikisi de
# ayni durumu okur ve biri digerinin ciftini EZER (kayip mesaj);
# bir okuyucu yarim JSON gormezdi.
# Ayni desen tools/tasks.py'de uygulanmis ve test edilmistir; burada
# ayni koruma uygulanir. RLock: aktif_id/_aktif_koy icten tekrar
# kilit alabilir.
_KILIT = threading.RLock()

# Windows'ta os.replace, dosya baska thread'de acikken gecici olarak
# PermissionError verir. Sinirli sayida yeniden denemek yeter;
# hepsi basarisiz olursa yazma kaybi _yaz icinde loglanir.
_REPLACE_DENEME = 5
_REPLACE_BEKLE = 0.01


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


class Okunmadi(Exception):
    """Dosya var ama su an okunamadi (Windows paylasim kilidi).

    `_oku` bunu None TUTMAZ: None "bu sohbet yok" demektir. Yok
    sanilip uzerine yazilirsa mevcut gecmis SILINIR.
    """


def _oku(sid):
    """Oturumu okur. Dosya yoksa None, okunamıyorsa Okunmadi.

    WINDOWS NOTU: dosya baska thread'de os.replace ile degistirilirken
    `open(...,"r")` gecici PermissionError verir. Onceki surum bunu
    None sayiyordu; `kaydet_cift` "yeni sohbet" diye basip MEVCUT
    GECMISI EZERDI. Simdi okunamayan dosya ayri durumdur.
    """
    son_hata = None
    for deneme in range(_REPLACE_DENEME):
        try:
            with open(_yol(sid), "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return None
        except PermissionError as e:
            son_hata = e
            time.sleep(_REPLACE_BEKLE * (deneme + 1))
        except (OSError, ValueError):
            return None
    raise Okunmadi("oturum okunamadi: %s" % _yol(sid)) from son_hata


def _atomik_yaz(yol, metin):
    """Once .tmp'e yaz, sonra tek hamlede degistir.

    os.replace ayni surucude atomiktir — baska thread/dosya okuyucusu
    yarim dosya gormez. Cagranda _KILIT'i tutuyor olmali.

    METIN yazilir, JSON degil: aktif oturum dosyasi ham sid okur,
    JSON'a cevrilirse tirnak isareti kacar ve her acilista yeni
    oturum uretilir.

    WINDOWS NOTU: dosya baska bir thread'de ACILIKken os.replace
    PermissionError verir (Windows'ta dosya silmek/degistirmek icin
    paylasimli acilis gerekir; Linux'ta bu sorun yok). Bu gecicidir,
    o yuzden sinirli sayida yeniden denenir: yoksa yazma sessizce
    kaybolur.
    """
    if not yol:
        raise ValueError("Oturum dosyasi yolu bos olamaz")
    gecici = yol + ".tmp"
    with open(gecici, "w", encoding="utf-8") as f:
        f.write(metin)
    son_hata = None
    for deneme in range(_REPLACE_DENEME):
        try:
            os.replace(gecici, yol)
            return
        except PermissionError as e:
            son_hata = e
            time.sleep(_REPLACE_BEKLE * (deneme + 1))
    raise son_hata


def _yaz(oturum):
    try:
        _atomik_yaz(_yol(oturum["id"]),
                    json.dumps(oturum, ensure_ascii=False))
        return True
    except (OSError, ValueError) as e:
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
    try:
        kayit = _oku(sid)
    except Okunmadi:
        # Geci kilit: kimlik DOGRULANAMAZ. Kirpilmis yol (fail-closed)
        # tercih edilir — sahipsiz sohbete erismekten iyi.
        return False
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
        # Dosya yok/okunamaz: yeni uretilir (ilk calistirma da boyledir).
        logger.debug("aktif oturum okunamadi, yeni uretiliyor: %s", dosya,
                     exc_info=True)
    sid = uuid.uuid4().hex[:8]
    try:
        os.makedirs(os.path.dirname(dosya), exist_ok=True)
        with _KILIT:
            _atomik_yaz(dosya, sid)
    except (OSError, ValueError):
        # Yazilamadi: bu oturum bellekte calisir, yeniden acilista kaybolur.
        logger.warning("aktif oturum yazilamadi: %s", dosya, exc_info=True)
    return sid


def _aktif_koy(sid):
    dosya = _aktif_dosya()
    try:
        os.makedirs(os.path.dirname(dosya), exist_ok=True)
        with _KILIT:
            _atomik_yaz(dosya, sid)
    except (OSError, ValueError):
        logger.warning("aktif oturum isaretlenemedi: %s", dosya,
                       exc_info=True)


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
        try:
            o = _oku(ad[:-5])
        except Okunmadi:
            # Tek bir sohbet kilitliyse listeyi bozmak yerine atlanir.
            logger.debug("liste: oturum okunamadi, atlandi: %s", ad,
                         exc_info=True)
            continue
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
    """Bir soru-cevap ciftini aktif oturuma ekler.

    2026-10-03: oku-degistir-yaz dongusunun tamami _KILIT altinda.
    Kilit kulani degil, MODELIN gorusunu degistirmez; yalniz iki
    thread'in ayni dosyayi ayni anda ezip birbirinin ciftini
    kaybetmesini engeller.
    """
    sid = sid or aktif_id()
    with _KILIT:
        try:
            mevcut = _oku(sid)
        except Okunmadi:
            # Dosya var ama kilitli: UZERINE YAZMA. Yazilamayan bir
            # cift, silinen bir gecmisten iyidir — sessiz veri kaybi
            # olusmaz.
            logger.warning("oturum okunamadi, cift kaydedilmedi: %s", sid)
            return sid
        o = mevcut or {"id": sid, "baslik": "", "olustu": time.time(),
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
    try:
        o = _oku(sid)
    except Okunmadi:
        # Gecici kilit: kullaniciya bos sohbet gostermek, hata vermekten
        # iyi. Dosya silinmedi — sonraki istekte tekrar okunur.
        logger.debug("ac: oturum kilitli, gecici olarak gosterilmedi: %s", sid)
        return None
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
