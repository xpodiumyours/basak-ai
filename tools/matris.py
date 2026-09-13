"""tools/matris.py — Yasayan agac: fikir -> arastirma -> dal -> adim -> detay.

Casper karari: sayi HICBIR yerde gecmez (sema, kod, aciklama).
Agac fikre gore buyur/kucultur: ekle, sil (arsivlenir), tasi,
birlestir. Satir kanitsiz kapanmaz; skor = kanitli / canli toplam.
Onay sohbette olur — koda onay kurali konmaz.

Saklama: data/matris/matris_<id>.json. Kilit + atomik yazma
(tasks.py duzeni aynen). Dosya yoksa bos doner, asla patlamaz.
"""

import json
import logging
import os
import threading
from datetime import datetime

logger = logging.getLogger(__name__)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MATRIS_KOK = os.path.join(BASE, "data", "matris")

_KILIT = threading.Lock()

TURLER = ("arastirma", "katman", "adim", "detay")
DURUMLAR = ("acik", "yapiliyor", "kanitli", "askida")

_ISARET = {"acik": "[ ]", "yapiliyor": "[~]",
           "kanitli": "[x]", "askida": "[||]"}


def _dosya(matris_id):
    try:
        no = int(matris_id)
    except (TypeError, ValueError):
        return None
    if no < 1:
        return None
    return os.path.join(MATRIS_KOK, "matris_%d.json" % no)


def _yukle(matris_id):
    yol = _dosya(matris_id)
    if yol is None or not os.path.exists(yol):
        return None
    with open(yol, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def _atomik_yaz(matris_id, veri):
    yol = _dosya(matris_id)
    if yol is None:
        raise ValueError("Gecersiz tablo numarasi")
    os.makedirs(MATRIS_KOK, exist_ok=True)
    gecici = yol + ".tmp"
    with open(gecici, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)
    os.replace(gecici, yol)


def _simdi():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _satir_bul(veri, satir_id):
    try:
        sid = int(satir_id)
    except (TypeError, ValueError):
        return None
    for s in veri.get("satirlar", []):
        if s.get("id") == sid and not s.get("arsiv"):
            return s
    return None


def _cocuklar(veri, ust_id):
    cocuk = [s for s in veri.get("satirlar", [])
             if not s.get("arsiv") and s.get("ust") == ust_id]
    # Arastirma satirlari once: tablo arastirmayla acar, dallanma sonra.
    cocuk.sort(key=lambda s: (0 if s.get("tur") == "arastirma" else 1,
                              s.get("id", 0)))
    return cocuk


def _soydan_mi(veri, aday_id, kok_id):
    """aday, kok'un altinda mi? (dongu kontrolu icin yukari yurur)."""
    gorulen = set()
    cur = aday_id
    while cur is not None and cur not in gorulen:
        gorulen.add(cur)
        if cur == kok_id:
            return True
        satir = _satir_bul(veri, cur)
        cur = satir.get("ust") if satir else None
    return False


def matris_ac(baslik, fikir=""):
    """Yeni fikir tablosu acar. Donus: tablo numarasi + ozet."""
    baslik = (baslik or "").strip()
    if not baslik:
        return {"error": "Tablo basligi bos olamaz"}
    with _KILIT:
        try:
            os.makedirs(MATRIS_KOK, exist_ok=True)
            mevcut = []
            for ad in os.listdir(MATRIS_KOK):
                if ad.startswith("matris_") and ad.endswith(".json"):
                    try:
                        mevcut.append(int(ad[7:-5]))
                    except ValueError:
                        continue
            yeni = max(mevcut, default=0) + 1
            veri = {"id": yeni, "baslik": baslik,
                    "fikir": (fikir or "").strip(),
                    "olustu": _simdi(), "satirlar": []}
            _atomik_yaz(yeni, veri)
        except OSError as e:
            return {"error": "Tablo acilamadi: %s" % e}
    return {"result": "Tablo acildi (#%d): %s" % (yeni, baslik),
            "matris": yeni}


def matris_liste():
    """Tum tablolari skorlariyla doner."""
    try:
        os.makedirs(MATRIS_KOK, exist_ok=True)
        ids = []
        for ad in sorted(os.listdir(MATRIS_KOK)):
            if ad.startswith("matris_") and ad.endswith(".json"):
                try:
                    ids.append(int(ad[7:-5]))
                except ValueError:
                    continue
    except OSError as e:
        return {"error": "Tablolar okunamadi: %s" % e}
    satirlar = []
    for i in ids:
        veri = _yukle(i)
        if veri is None:
            continue
        canli = [s for s in veri.get("satirlar", []) if not s.get("arsiv")]
        biten = [s for s in canli if s.get("durum") == "kanitli"]
        satirlar.append("#%d %s — %d/%d kanitli" % (
            i, veri.get("baslik", ""), len(biten), len(canli)))
    if not satirlar:
        return {"result": "Henuz tablo yok"}
    return {"result": "\n".join(satirlar)}


def satir_ekle(matris, tur, metin, ust=None, neden="", bagli=None):
    """Agaca satir ekler. tur: arastirma|katman|adim|detay.

    ust: baglanacagi satir numarasi (yoksa kok). neden: ustteki hangi
    ise yaradigi (bos birakilabilir). bagli: once bitmesi gereken
    satir numaralari listesi.
    """
    tur = (tur or "").strip().lower()
    if tur not in TURLER:
        return {"error": "Gecersiz tur: '%s'. Gecerli: %s"
                         % (tur, ", ".join(TURLER))}
    metin = (metin or "").strip()
    if not metin:
        return {"error": "Satir metni bos olamaz"}
    with _KILIT:
        veri = _yukle(matris)
        if veri is None:
            return {"error": "Tablo bulunamadi: %s" % matris}
        uid = None
        if ust is not None and str(ust).strip() not in ("", "0"):
            ana = _satir_bul(veri, ust)
            if ana is None:
                return {"error": "Ust satir bulunamadi: %s" % ust}
            uid = ana["id"]
        baglilar = []
        for b in (bagli or []):
            try:
                bid = int(b)
            except (TypeError, ValueError):
                return {"error": "Baglanti numarasi sayi olmali: %s" % b}
            if _satir_bul(veri, bid) is None:
                return {"error": "Bagli satir bulunamadi: %s" % bid}
            baglilar.append(bid)
        try:
            satirlar = veri.get("satirlar", [])
            yeni = max([s.get("id", 0) for s in satirlar
                        ] + [0]) + 1
            satirlar.append({"id": yeni, "tur": tur, "metin": metin,
                             "ust": uid, "neden": (neden or "").strip(),
                             "durum": "acik", "kanitlar": [],
                             "bagli": baglilar, "arsiv": False,
                             "olustu": _simdi()})
            veri["satirlar"] = satirlar
            _atomik_yaz(veri["id"], veri)
        except (OSError, ValueError) as e:
            return {"error": "Satir eklenemedi: %s" % e}
    return {"result": "Satir eklendi (#%d)" % yeni, "satir": yeni}


def kanit_ekle(matris, satir, kanit):
    """Satira kanit notu duser (kapatmanin sarti)."""
    kanit = (kanit or "").strip()
    if not kanit:
        return {"error": "Kanit metni bos olamaz"}
    with _KILIT:
        veri = _yukle(matris)
        if veri is None:
            return {"error": "Tablo bulunamadi: %s" % matris}
        hedef = _satir_bul(veri, satir)
        if hedef is None:
            return {"error": "Satir bulunamadi: %s" % satir}
        try:
            hedef["kanitlar"].append({"metin": kanit, "zaman": _simdi()})
            _atomik_yaz(veri["id"], veri)
        except OSError as e:
            return {"error": "Kanit yazilamadi: %s" % e}
    return {"result": "Kanit eklendi (#%d)" % hedef["id"]}


def satir_kapat(matris, satir):
    """Satiri kanitli kapatir. Kanitsiz veya baglilari bitmemis kapanmaz."""
    with _KILIT:
        veri = _yukle(matris)
        if veri is None:
            return {"error": "Tablo bulunamadi: %s" % matris}
        hedef = _satir_bul(veri, satir)
        if hedef is None:
            return {"error": "Satir bulunamadi: %s" % satir}
        if not hedef.get("kanitlar"):
            return {"error": ("Satir #%d kapanmaz: kanit yok. Once kanit "
                              "ekle.") % hedef["id"]}
        acik_bagli = []
        for bid in hedef.get("bagli", []):
            b = _satir_bul(veri, bid)
            if b is not None and b.get("durum") != "kanitli":
                acik_bagli.append(str(bid))
        if acik_bagli:
            return {"error": ("Satir #%d kapanmaz: bagli satirlar bitmemis "
                              "(%s).") % (hedef["id"], ", ".join(acik_bagli))}
        try:
            hedef["durum"] = "kanitli"
            _atomik_yaz(veri["id"], veri)
        except OSError as e:
            return {"error": "Kapatilamadi: %s" % e}
    return {"result": "Satir kanitli kapandi (#%d)" % hedef["id"]}


def satir_ac(matris, satir):
    """Kapanmis/askidaki satiri yeniden acar."""
    with _KILIT:
        veri = _yukle(matris)
        if veri is None:
            return {"error": "Tablo bulunamadi: %s" % matris}
        hedef = _satir_bul(veri, satir)
        if hedef is None:
            return {"error": "Satir bulunamadi: %s" % satir}
        try:
            hedef["durum"] = "acik"
            _atomik_yaz(veri["id"], veri)
        except OSError as e:
            return {"error": "Acilamadi: %s" % e}
    return {"result": "Satir yeniden acildi (#%d)" % hedef["id"]}


def satir_sil(matris, satir):
    """Satiri arsive kaldirir (geri donulebilir, skor disi)."""
    with _KILIT:
        veri = _yukle(matris)
        if veri is None:
            return {"error": "Tablo bulunamadi: %s" % matris}
        hedef = _satir_bul(veri, satir)
        if hedef is None:
            return {"error": "Satir bulunamadi: %s" % satir}
        try:
            for cocuk in _cocuklar(veri, hedef["id"]):
                cocuk["ust"] = hedef.get("ust")
            hedef["arsiv"] = True
            hedef["durum"] = "askida"
            _atomik_yaz(veri["id"], veri)
        except OSError as e:
            return {"error": "Silinemedi: %s" % e}
    return {"result": "Satir arsive kaldirildi (#%d)" % hedef["id"]}


def satir_tasi(matris, satir, yeni_ust):
    """Satiri baska dalin altina tasir (dongu kurulamaz)."""
    with _KILIT:
        veri = _yukle(matris)
        if veri is None:
            return {"error": "Tablo bulunamadi: %s" % matris}
        hedef = _satir_bul(veri, satir)
        if hedef is None:
            return {"error": "Satir bulunamadi: %s" % satir}
        if yeni_ust is None or str(yeni_ust).strip() in ("", "0"):
            uid = None
        else:
            ana = _satir_bul(veri, yeni_ust)
            if ana is None:
                return {"error": "Yeni ust bulunamadi: %s" % yeni_ust}
            if ana["id"] == hedef["id"] or _soydan_mi(
                    veri, ana["id"], hedef["id"]):
                return {"error": "Tasima dongu kurar: %s" % yeni_ust}
            uid = ana["id"]
        try:
            hedef["ust"] = uid
            _atomik_yaz(veri["id"], veri)
        except OSError as e:
            return {"error": "Tasinamadi: %s" % e}
    return {"result": "Satir tasindi (#%d)" % hedef["id"]}


def _agac_yaz(veri, ust_id, derinlik, cikti):
    for s in _cocuklar(veri, ust_id):
        isaret = _ISARET.get(s.get("durum"), "[?]")
        satir = "%s%s #%d [%s] %s" % ("  " * derinlik, isaret, s["id"],
                                      s.get("tur", ""), s.get("metin", ""))
        if s.get("bagli"):
            satir += "  <- once: %s" % ",".join(
                "#%d" % b for b in s["bagli"])
        if s.get("kanitlar"):
            satir += "  (kanit: %d)" % len(s["kanitlar"])
        cikti.append(satir)
        _agac_yaz(veri, s["id"], derinlik + 1, cikti)


def matris_durum(matris):
    """Tabloyu agac + skor olarak doner. Budama yok, tamami cikar."""
    veri = _yukle(matris)
    if veri is None:
        return {"error": "Tablo bulunamadi: %s" % matris}
    canli = [s for s in veri.get("satirlar", []) if not s.get("arsiv")]
    biten = [s for s in canli if s.get("durum") == "kanitli"]
    askidaki = [s for s in canli if s.get("durum") == "askida"]
    cikti = ["#%d %s" % (veri.get("id"), veri.get("baslik", ""))]
    if veri.get("fikir"):
        cikti.append("Fikir: %s" % veri["fikir"])
    _agac_yaz(veri, None, 0, cikti)
    cikti.append("skor: %d/%d kanitli" % (len(biten), len(canli)))
    if askidaki:
        cikti.append("askida: %d" % len(askidaki))
    arsivli = len(veri.get("satirlar", [])) - len(canli)
    if arsivli:
        cikti.append("arsivde: %d" % arsivli)
    return {"result": "\n".join(cikti)}
