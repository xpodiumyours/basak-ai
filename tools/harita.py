"""tools/harita.py — Harita: baglanti uretimi (Z0) + konum cozumleme (Z1).

Z0 (`harita_goster`): ag cagrisi YOK, anahtar YOK, kota YOK. Yalniz Google
Maps URL semasi uretilir; kullanici tiklayinca harita kendi tarayicisinda
acilir. Kaynak (resmi): developers.google.com/maps/documentation/urls/
get-started — "Maps URLs" icin API anahtari gerekmez.

Z1 (`konum_coz`): adres/yer adi -> enlem/boylam. Once Photon (OpenStreetMap,
anahtarsiz), olmazsa Open-Meteo geocoding. SSRF savunmasi YENIDEN YAZILMAZ:
tools/web_search.py icindeki `_guvenli_adres` + `_GuvenliYonlendirme`
kullanilir (her yonlendirme adimi yeniden denetlenir). Bulunamazsa hata
doner; koordinat UYDURULMAZ.
"""

import json
import logging
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)

ARAMA_TABANI = "https://www.google.com/maps/search/?api=1&query="
YOL_TABANI = "https://www.google.com/maps/dir/?api=1&destination="

MOD_ARAMA = "ara"
MOD_YOL = "yol"
GECERLI_MODLAR = (MOD_ARAMA, MOD_YOL)

# Adres/yer adı için makul üst sınır; uzun metin hata döner, kırpılmaz.
KONUM_TAVANI = 300


def _j(veri):
    return json.dumps(veri, ensure_ascii=False)


def _konum_temizle(konum):
    """Baştaki/sondaki boşluğu atar, satır sonlarını tek boşluğa indirir."""
    return " ".join(str(konum or "").split())


def harita_goster(konum, mod=MOD_YOL):
    """Konum için Google Maps bağlantısı üretir.

    konum: adres, yer adı veya "enlem,boylam" metni.
    mod:   "yol" (yol tarifi) veya "ara" (haritada ara).

    Dönüş: {"result": JSON} — konum, mod, baglanti, kaynak.
    Boş konum, aşırı uzun konum veya bilinmeyen mod → {"error": ...}.
    Bağlantı üretilemezse uydurma bağlantı YAZILMAZ.
    """
    temiz = _konum_temizle(konum)
    if not temiz:
        return {"error": "Konum boş olamaz."}
    if len(temiz) > KONUM_TAVANI:
        return {"error": "Konum çok uzun (en fazla %d karakter)."
                         % KONUM_TAVANI}

    secilen = str(mod or "").strip().lower() or MOD_YOL
    if secilen not in GECERLI_MODLAR:
        return {"error": "Bilinmeyen mod: '%s'. Geçerli modlar: %s"
                         % (mod, ", ".join(GECERLI_MODLAR))}

    taban = YOL_TABANI if secilen == MOD_YOL else ARAMA_TABANI
    # quote(safe="") — konum metni URL parametresinden kaçamaz.
    baglanti = taban + urllib.parse.quote(temiz, safe="")

    return {"result": _j({
        "konum": temiz,
        "mod": secilen,
        "baglanti": baglanti,
        "kaynak": "Google Maps",
    })}


# ── Z1: konum çözümleme (adres -> enlem/boylam) ───────────────────
#
# Photon: OpenStreetMap tabanli, anahtarsiz, adres seviyesinde cozer.
# Open-Meteo geocoding: havada zaten kullanilan hat; SEHIR seviyesinde
# cozer (acik adres bulamaz). Uc nokta sabiti hava.py'den ALINIR,
# ag cagrisi ise SSRF korumali ortak yardimciyla yapilir.

PHOTON_TABANI = "https://photon.komoot.io/api/"
_ZAMAN_ASIMI = 10
_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Basak/1.0"


def _json_al(url):
    """Korumali tek GET; SSRF denetimi + yonlendirme denetimi uygular.

    Koruma tools/web_search.py'den cagrilir; burada yeni savunma yazilmaz.
    Donus: (veri, None) veya (None, hata_metni).
    """
    from tools.web_search import _guvenli_adres, _GuvenliYonlendirme

    engel = _guvenli_adres(url)
    if engel:
        return None, engel
    try:
        opener = urllib.request.build_opener(_GuvenliYonlendirme())
        istek = urllib.request.Request(url, headers={
            "User-Agent": _USER_AGENT,
            "Accept": "application/json",
            "Accept-Encoding": "identity",
        })
        with opener.open(istek, timeout=_ZAMAN_ASIMI) as yanit:
            return json.loads(yanit.read().decode("utf-8")), None
    except Exception as e:
        logger.info("Konum servisi okunamadi: %s", e)
        return None, "servise ulasilamadi"


def _sayi(deger):
    """JSON'dan gelen koordinat bileseni sayi mi? Degilse None."""
    try:
        s = float(deger)
    except (TypeError, ValueError):
        return None
    return s


def _gecerli_koordinat(enlem, boylam):
    if enlem is None or boylam is None:
        return False
    return -90.0 <= enlem <= 90.0 and -180.0 <= boylam <= 180.0


def _gosterim_adi(ozellik):
    """Photon ozelliklerinden insan okunur ad kurar; eksik alan atlanir."""
    parcalar = []
    ad = (ozellik.get("name") or "").strip()
    if ad:
        parcalar.append(ad)
    for anahtar in ("street", "housenumber", "district", "city", "state",
                    "postcode", "country"):
        deger = (ozellik.get(anahtar) or "")
        deger = str(deger).strip()
        if deger and deger not in parcalar:
            parcalar.append(deger)
    return ", ".join(parcalar)


def _photon_adaylari(adres):
    """Photon aday listesi dondurur; basarisizsa/engelliyse None.

    `lang` GONDERILMEZ: Photon yalniz de/en/fr/it kabul ediyor; lang=tr
    2026-10-01'de canli olculdu ve HTTP 400 dondurdu (tum birincil hat
    sessizce yedege dusuyordu). Dilsiz istek yerel adlari dondurur.
    """
    sorgu = urllib.parse.urlencode({"q": adres, "limit": 5})
    veri, _hata = _json_al(PHOTON_TABANI + "?" + sorgu)
    if not isinstance(veri, dict):
        return None
    adaylar = []
    for ozellik in (veri.get("features") or []):
        if not isinstance(ozellik, dict):
            continue
        # GeoJSON sira: coordinates = [boylam, enlem] — karistirma.
        koordinat = ((ozellik.get("geometry") or {}).get("coordinates")
                     or [])
        if len(koordinat) < 2:
            continue
        boylam = _sayi(koordinat[0])
        enlem = _sayi(koordinat[1])
        if not _gecerli_koordinat(enlem, boylam):
            continue
        oz = ozellik.get("properties") or {}
        adaylar.append({
            "enlem": round(enlem, 6),
            "boylam": round(boylam, 6),
            "gosterim_adi": _gosterim_adi(oz) or adres,
            "osm_id": oz.get("osm_id"),
            "tip": oz.get("osm_value") or oz.get("type"),
        })
    return adaylar or None


def _open_meteo_adayi(adres):
    """Sehir seviyesi yedek hat; uc nokta hava.py'den alinir."""
    from tools import hava

    sorgu = urllib.parse.urlencode(
        {"name": adres, "count": 1, "language": "tr", "format": "json"})
    veri, _hata = _json_al(hava._GEOCODING + "?" + sorgu)
    if not isinstance(veri, dict):
        return None
    sonuclar = veri.get("results") or []
    if not sonuclar:
        return None
    ilk = sonuclar[0] or {}
    enlem = _sayi(ilk.get("latitude"))
    boylam = _sayi(ilk.get("longitude"))
    if not _gecerli_koordinat(enlem, boylam):
        return None
    parcalar = [str(ilk.get("name") or adres).strip() or adres]
    for anahtar in ("admin1", "country"):
        deger = str(ilk.get(anahtar) or "").strip()
        if deger and deger not in parcalar:
            parcalar.append(deger)
    return {"enlem": round(enlem, 6), "boylam": round(boylam, 6),
            "gosterim_adi": ", ".join(parcalar),
            "osm_id": None, "tip": None}


def konum_coz(adres):
    """Adres veya yer adini enlem/boylam koordinatina cevirir.

    Once Photon (OpenStreetMap, anahtarsiz; adres seviyesi), olmazsa
    Open-Meteo geocoding (sehir seviyesi).

    Donus: {"result": JSON} — adres, enlem, boylam, gosterim_adi, kaynak,
    aday_sayisi, adaylar. Hicbir hat bulamazsa {"error": ...} doner;
    koordinat UYDURULMAZ.
    """
    temiz = _konum_temizle(adres)
    if not temiz:
        return {"error": "Adres boş olamaz."}
    if len(temiz) > KONUM_TAVANI:
        return {"error": "Adres çok uzun (en fazla %d karakter)."
                         % KONUM_TAVANI}

    adaylar = _photon_adaylari(temiz)
    if adaylar:
        en_iyi = adaylar[0]
        return {"result": _j({
            "adres": temiz,
            "enlem": en_iyi["enlem"],
            "boylam": en_iyi["boylam"],
            "gosterim_adi": en_iyi["gosterim_adi"],
            "kaynak": "photon",
            "aday_sayisi": len(adaylar),
            "adaylar": adaylar,
        })}

    yedek = _open_meteo_adayi(temiz)
    if yedek:
        return {"result": _j({
            "adres": temiz,
            "enlem": yedek["enlem"],
            "boylam": yedek["boylam"],
            "gosterim_adi": yedek["gosterim_adi"],
            "kaynak": "open-meteo",
            "aday_sayisi": 1,
            "adaylar": [],
        })}

    return {"error": "Konum bulunamadı: '%s'." % temiz}
