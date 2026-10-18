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

Her cagri `denenen_hatlar` alanini doner: hangi hat denendi, kac aday verdi
ya da NEDEN basarisiz oldu. Bu alan 2026-10-01'de yasanan sessiz bozulmaya
karsi eklendi: Photon'a gonderilen gecersiz `lang=tr` parametresi HTTP 400
uretiyordu ve hata sebebi yutuldugu icin birincil hat bozuk oldugu halde
aylarca gorunmedi.
"""

import json
import logging
import urllib.error
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

_HAT_PHOTON = "photon"
_HAT_OPEN_METEO = "open-meteo"


def _json_al(url):
    """Korumali tek GET; SSRF denetimi + yonlendirme denetimi uygular.

    Koruma tools/web_search.py'den cagrilir; burada yeni savunma yazilmaz.
    Donus: (veri, None) veya (None, hata_metni).

    Hata metni artik SEBEBI tasir: 2026-10-01'de Photon `lang=tr` yuzunden
    HTTP 400 dondururken hata "servise ulasilamadi" diye yutuldugu icin
    birincil hattin bozuk oldugu aylarca gorunmedi.
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
    except urllib.error.HTTPError as e:
        logger.info("Konum servisi HTTP hatasi: %s", e)
        return None, "HTTP %s %s" % (e.code, str(e.reason)[:60])
    except Exception as e:
        logger.info("Konum servisi okunamadi: %s", e)
        return None, "%s: %s" % (type(e).__name__,
                                 str(getattr(e, "reason", e))[:80])


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


def _posta_kodu(kaynak_sozluk, anahtar):
    """Posta kodu tek deger ya da liste gelebilir; metne indirir."""
    deger = kaynak_sozluk.get(anahtar)
    if isinstance(deger, list):
        deger = deger[0] if deger else ""
    return str(deger or "").strip()


def _hat_kaydi(kaynak, adaylar=None, hata=None):
    """Bir denenen hattin durum kaydi (olcum/teshis icin).

    Basarili hatta aday sayisi, basarisiz hatta HATA SEBEBI yazilir; boylece
    birincil hattin sessizce bozulmasi (2026-10-01 lang=tr olayi) bir daha
    gorunmez kalmaz.
    """
    if hata:
        return {"kaynak": kaynak, "durum": "hata", "hata": hata}
    return {"kaynak": kaynak, "durum": "ok",
            "aday_sayisi": len(adaylar or [])}


def _photon_adaylari(adres):
    """Photon adaylari + bu hattin deneme kaydi.

    `lang` GONDERILMEZ: Photon yalniz de/en/fr/it kabul ediyor; lang=tr
    2026-10-01'de canli olculdu ve HTTP 400 dondurdu (tum birincil hat
    sessizce yedege dusuyordu). Dilsiz istek yerel adlari dondurur.
    """
    sorgu = urllib.parse.urlencode({"q": adres, "limit": 5})
    veri, hata = _json_al(PHOTON_TABANI + "?" + sorgu)
    if not isinstance(veri, dict):
        return [], _hat_kaydi(_HAT_PHOTON, hata=hata or "beklenmeyen yanit")
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
            "posta_kodu": str(oz.get("postcode") or "").strip(),
            "ulke_kodu": str(oz.get("countrycode") or "").strip(),
        })
    return adaylar, _hat_kaydi(_HAT_PHOTON, adaylar=adaylar)


def _open_meteo_adaylari(adres):
    """Sehir seviyesi yedek hat; uc nokta hava.py'den alinir.

    Photon ile ayni bicimde bir ADAY LISTESI doner (eskiden tek aday
    donuyordu); boylece model iki hatta da ayni sekli gorur.
    """
    from tools import hava

    sorgu = urllib.parse.urlencode(
        {"name": adres, "count": 5, "language": "tr", "format": "json"})
    veri, hata = _json_al(hava._GEOCODING + "?" + sorgu)
    if not isinstance(veri, dict):
        return [], _hat_kaydi(_HAT_OPEN_METEO,
                              hata=hata or "beklenmeyen yanit")
    adaylar = []
    for ilk in (veri.get("results") or []):
        if not isinstance(ilk, dict):
            continue
        enlem = _sayi(ilk.get("latitude"))
        boylam = _sayi(ilk.get("longitude"))
        if not _gecerli_koordinat(enlem, boylam):
            continue
        parcalar = [str(ilk.get("name") or adres).strip() or adres]
        for anahtar in ("admin1", "country"):
            deger = str(ilk.get(anahtar) or "").strip()
            if deger and deger not in parcalar:
                parcalar.append(deger)
        adaylar.append({
            "enlem": round(enlem, 6),
            "boylam": round(boylam, 6),
            "gosterim_adi": ", ".join(parcalar),
            "osm_id": None,
            "tip": str(ilk.get("feature_code") or "").strip() or None,
            "posta_kodu": _posta_kodu(ilk, "postcodes"),
            "ulke_kodu": str(ilk.get("country_code") or "").strip(),
        })
    return adaylar, _hat_kaydi(_HAT_OPEN_METEO, adaylar=adaylar)


def _deneme_ozeti(denenen):
    """Hata mesajina hatlarin durumunu kisa metin olarak ekler."""
    parcalar = []
    for k in denenen or ():
        if k.get("durum") == "ok":
            parcalar.append("%s: %d aday" % (k.get("kaynak"),
                                              k.get("aday_sayisi") or 0))
        else:
            parcalar.append("%s: %s" % (k.get("kaynak"),
                                         k.get("hata") or "basarisiz"))
    return "; ".join(parcalar)


def konum_coz(adres):
    """Adres veya yer adini enlem/boylam koordinatina cevirir.

    Once Photon (OpenStreetMap, anahtarsiz; adres seviyesi), olmazsa
    Open-Meteo geocoding (sehir seviyesi).

    Donus: {"result": JSON} — adres, enlem, boylam, gosterim_adi, kaynak,
    aday_sayisi, adaylar (gosterim_adi, tip, osm_id, posta_kodu, ulke_kodu),
    denenen_hatlar (her hattin durumu ve hata sebebi). Hicbir hat sonuc
    bulamazsa {"error": ...} doner ve hata mesaji denenen hatlari soyler;
    koordinat UYDURULMAZ.
    """
    temiz = _konum_temizle(adres)
    if not temiz:
        return {"error": "Adres boş olamaz."}
    if len(temiz) > KONUM_TAVANI:
        return {"error": "Adres çok uzun (en fazla %d karakter)."
                         % KONUM_TAVANI}

    denenen = []
    adaylar, kayit = _photon_adaylari(temiz)
    denenen.append(kayit)
    kaynak = _HAT_PHOTON if adaylar else ""

    if not adaylar:
        adaylar, kayit = _open_meteo_adaylari(temiz)
        denenen.append(kayit)
        if adaylar:
            kaynak = _HAT_OPEN_METEO

    if not adaylar:
        return {"error": "Konum bulunamadı: '%s'. Denenen hatlar: %s"
                         % (temiz, _deneme_ozeti(denenen))}

    en_iyi = adaylar[0]
    return {"result": _j({
        "adres": temiz,
        "enlem": en_iyi["enlem"],
        "boylam": en_iyi["boylam"],
        "gosterim_adi": en_iyi["gosterim_adi"],
        "kaynak": kaynak,
        "aday_sayisi": len(adaylar),
        "adaylar": adaylar,
        "denenen_hatlar": denenen,
    })}


# ── Z3: yakin cevre arama (Overpass) + mesafe/sure (OSRM) ─────────
#
# Para kapisi olcumu (2026-10-18, RESMI kaynaklardan):
# - Overpass API (overpass-api.de/overpass-doc/en/preface/commons.html):
#   anahtarsiz, kartsiz; genis guvenlik siniri ~10.000 istek/gun ve
#   ~1 GB indirme/gun. Kisiye ozel dusuk trafikli kullanim icin yetar.
#   Yedek hat: overpass.kumi.systems (anahtarsiz public instance).
# - OSRM demo (project-osrm.org): kullanım politikası "yalinizca hafif
#   kullanim" (heavy usage yasak; OSM forum 03.06.2024, lonvia/OSM).
#   Yedek hat: FOSSGIS routing.openstreetmap.de (routed-car/bike/foot,
#   anahtarsiz).
# - Google Routes/Directions/Places KURULMAZ: bedava katman kart ister
#   (para kapisi). Buyutme ihtiyaci olursa Casper karari gerektirir.

import math
import time

_HAT_OVERPASS = "overpass"
_OVERPASS_TABANLARI = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)
_OVERPASS_SORGU_TAVAN_SANIYE = 25
_YARICAP_ALT_M = 50
_YARICAP_TAVAN_M = 10000
_YARICAP_VARSAYILAN_M = 1000
_ADET_TAVANI = 15
_ONBELLEK_TTL_S = 600.0
_ONBELLEK_KAPASITE = 100
_OKUMA_TAVANI_BAYT = 2 * 1024 * 1024
# Overpass sorgusu kendisi [timeout:25] ister; genis zaman asimi bunlari
# degil. Genel _ZAMAN_ASIMI=10 Z1 (geocoding) davranisha  dokunulmadi;
# Overpass kendi tavanini tasir.
_OVERPASS_ZAMAN_ASIMI_S = 25

# Aranan tabiri -> Overpass tag filtreleri. Liste sabit ve kapalidir;
# listede olmayan kelime UYDURULMAZ, hata desteklenenleri yazar.
_TAG_TABIRLERI = {
    "market": ("shop=supermarket", "shop=convenience"),
    "eczane": ("amenity=pharmacy",),
    "hastane": ("amenity=hospital",),
    "banka": ("amenity=bank",),
    "bankamatik": ("amenity=atm", "amenity=bank"),
    "restoran": ("amenity=restaurant", "amenity=fast_food"),
    "kafe": ("amenity=cafe",),
    "benzinlik": ("amenity=fuel",),
    "firin": ("shop=bakery",),
    "okul": ("amenity=school",),
    "otopark": ("amenity=parking",),
    "polis": ("amenity=police",),
    "durak": ("highway=bus_stop",),
    "park": ("leisure=park",),
}

# OSRM: seyahat sekli -> hatlar. Araba profili iki hatti deneyebilir;
# bisiklet/piyade profilleri resmi olarak yalniz FOSSGIS demo
# sunucusunda yayinlidir (denenen_hatlar bunu acik yazar).
_HAT_OSRM = "osrm"
_OSRM_HATLARI = {
    "araba": (
        "https://router.project-osrm.org/route/v1/driving",
        "https://routing.openstreetmap.de/routed-car/route/v1/driving",
    ),
    "bisiklet": (
        "https://routing.openstreetmap.de/routed-bike/route/v1/driving",
    ),
    "piyade": (
        "https://routing.openstreetmap.de/routed-foot/route/v1/driving",
    ),
}

_ONBELLEK = {}


def _mesafe_m(en1, boy1, en2, boy2):
    """Iki koordinat arasi haversine mesafe; metre cinsinden doner."""
    en1, en2 = math.radians(en1), math.radians(en2)
    en_fark = en2 - en1
    boy_fark = math.radians(boy2 - boy1)
    a = (math.sin(en_fark / 2.0) ** 2
         + math.cos(en1) * math.cos(en2) * math.sin(boy_fark / 2.0) ** 2)
    return 2.0 * 6371000.0 * math.asin(math.sqrt(a))


def _koordinat_metni(metin):
    """'enlem,boylam' yazimini cozer; uymazsa None doner (uydurma yok)."""
    parcalar = [p.strip() for p in str(metin or "").split(",")]
    if len(parcalar) != 2:
        return None
    en = _sayi(parcalar[0])
    boy = _sayi(parcalar[1])
    if not _gecerli_koordinat(en, boy):
        return None
    return en, boy


def _merkezi_coz(metin):
    """Merkez girisini koordinata baglar.

    'enlem,boylam' yazimi dogrudan alinir; diger metin icin Z1
    (konum_coz) cagrilir. Donus: (sozluk, None) veya (None, sebep).
    Cozumleme yapilamazsa koordinat UYDURULMAZ."""
    koordinat = _koordinat_metni(metin)
    if koordinat:
        return ({"enlem": koordinat[0], "boylam": koordinat[1],
                 "gosterim_adi": " ".join(str(metin).split()),
                 "kaynak": "girilen koordinat"}, None)
    cozum = konum_coz(metin)
    if "error" in cozum:
        return None, cozum["error"]
    veri = json.loads(cozum["result"])
    return ({"enlem": veri["enlem"], "boylam": veri["boylam"],
             "gosterim_adi": veri.get("gosterim_adi") or metin,
             "kaynak": veri.get("kaynak") or ""}, None)


def _overpass_json_al(sorgu):
    """Overpass'i POST ile sorar; tabanlari sirayla dener.

    SSRF savunmasi YENIDEN YAZILMAZ: tools/web_search.py'deki
    _guvenli_adres + _GuvenliYonlendirme KULLANILIR. Donus:
    (veri, hat, None) veya (None, hat, sebep). Okuma 2 MB ile
    tavanlidir; dev yanit bellek sulmuyor."""
    from tools.web_search import _guvenli_adres, _GuvenliYonlendirme

    sorgu_bayt = urllib.parse.urlencode({"data": sorgu}).encode()
    son_hata = None
    for taban in _OVERPASS_TABANLARI:
        engel = _guvenli_adres(taban)
        if engel:
            return None, taban, engel
        try:
            opener = urllib.request.build_opener(_GuvenliYonlendirme())
            istek = urllib.request.Request(
                taban,
                data=sorgu_bayt,
                headers={
                    "User-Agent": _USER_AGENT,
                    "Accept": "application/json",
                    "Accept-Encoding": "identity",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
            with opener.open(istek,
                             timeout=_OVERPASS_ZAMAN_ASIMI_S) as yanit:
                veri = json.loads(
                    yanit.read(_OKUMA_TAVANI_BAYT).decode("utf-8"))
            if not isinstance(veri, dict):
                return None, taban, "beklenmeyen yanit (JSON degil)"
            return veri, taban, None
        except urllib.error.HTTPError as e:
            son_hata = "HTTP %s %s" % (e.code, str(e.reason)[:60])
            logger.info("Overpass HTTP hatasi (%s): %s", taban, e)
        except Exception as e:
            son_hata = "%s: %s" % (type(e).__name__,
                                   str(getattr(e, "reason", e))[:80])
            logger.info("Overpass hatasi (%s): %s", taban, e)
    return None, _HAT_OVERPASS, son_hata or "basarisiz"


def _overpass_sorgusu(tabir, enlem, boylam, yaricap):
    """Overpass QL sorgu dizesini kurar: nwr[tag](around:...); out center."""
    koordinat = "%s,%s" % (enlem, boylam)
    satirlar = ["[out:json][timeout:%d];" % _OVERPASS_SORGU_TAVAN_SANIYE]
    for tag in _TAG_TABIRLERI[tabir]:
        satirlar.append("nwr[%s](around:%d,%s);"
                        % (tag, yaricap, koordinat))
    satirlar.append("out center %d;" % (_ADET_TAVANI * 3))
    return "\n".join(satirlar)


def _onbellek_oku(anahtar):
    """Taze kayit varsa doneer; bayat kayit silinir ve None doner."""
    kayit = _ONBELLEK.get(anahtar)
    if not kayit:
        return None
    zaman, adaylar = kayit
    if time.monotonic() - zaman > _ONBELLEK_TTL_S:
        _ONBELLEK.pop(anahtar, None)
        return None
    return adaylar


def _onbellege_yaz(anahtar, adaylar):
    """Onbellek kapasite dolarken en eski kaydi atilir (FIFO)."""
    if len(_ONBELLEK) >= _ONBELLEK_KAPASITE:
        en_eski = min(_ONBELLEK, key=lambda k: _ONBELLEK[k][0])
        _ONBELLEK.pop(en_eski, None)
    _ONBELLEK[anahtar] = (time.monotonic(), adaylar)


def _overpass_adaylari(veri, enlem, boylam):
    """Overpass elemanlarini aday listesine cevirir.

    Yalniz ISIMLI elemanlar alinir; isimsiz atlanir. Kopyalar (ayni
    yaklasik koordinat + ayni ad) tekillestirilir; mesafeye gore
    yakindan uzaga siralanir ve _ADET_TAVANI ile kesilir."""
    adaylar = []
    gorulen = set()
    for oge in (veri.get("elements") or []):
        if not isinstance(oge, dict):
            continue
        etiket = oge.get("tags") or {}
        ad = str(etiket.get("name") or "").strip()
        if not ad:
            continue
        en = _sayi(oge.get("lat"))
        boy = _sayi(oge.get("lon"))
        merkez = oge.get("center") or {}
        if en is None or boy is None:
            en = _sayi(merkez.get("lat"))
            boy = _sayi(merkez.get("lon"))
        if not _gecerli_koordinat(en, boy):
            continue
        kopya = (round(en, 5), round(boy, 5), ad.lower())
        if kopya in gorulen:
            continue
        gorulen.add(kopya)
        tip = ""
        for anahtar in ("amenity", "shop", "leisure", "highway"):
            tip = str(etiket.get(anahtar) or "").strip()
            if tip:
                break
        sonuc_g = harita_goster(konum="%s, %s" % (en, boy), mod=MOD_ARAMA)
        baglanti = ""
        if "result" in sonuc_g:
            baglanti = str(json.loads(sonuc_g["result"]).get("baglanti")
                           or "")
        adaylar.append({
            "ad": ad,
            "tip": tip,
            "osm": "%s/%s" % (oge.get("type") or "",
                              oge.get("id") or ""),
            "enlem": round(en, 6),
            "boylam": round(boy, 6),
            "mesafe_m": int(round(_mesafe_m(enlem, boylam, en, boy), 0)),
            "baglanti": baglanti,
        })
    adaylar.sort(key=lambda a: a["mesafe_m"])
    return adaylar[:_ADET_TAVANI]


def yakin_ara(merkez, aranan, yaricap_m=None):
    """Merkezin cevresinde istenen turdeki yerleri OSM'de (Overpass) arar.

    merkez: adres, yer adi veya 'enlem,boylam'; koordinat degilse Z1
    (konum_coz) devreye girer.
    aranan: sabit tabir listesinden biri (market, eczane, hastane,
    banka, bankamatik, restoran, kafe, benzinlik, firin, okul,
    otopark, polis, durak, park).
    yaricap_m: 50-10000 m; bos -> 1000; aralik disi hata doner.

    Donus: {"result": JSON} — merkez (enlem/boylam/gosterim_adi/kaynak),
    aranan, yaricap_m, sonuclar (ad/tip/osm/mesafe_m/enlem/boylam/
    baglanti; yakindan uzaga sirali, en fazla 15), denenen_hatlar.
    Sonuc bulunamazsa {"error": ...} doner; mesafe UYDURULMAZ."""
    temiz_merkez = _konum_temizle(merkez)
    temiz_aranan = _konum_temizle(aranan)
    if not temiz_merkez:
        return {"error": "Merkez bos olamaz."}
    if len(temiz_merkez) > KONUM_TAVANI:
        return {"error": "Merkez cok uzun (en fazla %d karakter)."
                         % KONUM_TAVANI}
    if not temiz_aranan:
        return {"error": "Aranan bos olamaz. Desteklenenler: %s"
                         % ", ".join(sorted(_TAG_TABIRLERI))}
    tabir = temiz_aranan.lower().replace("ı", "i").replace("İ", "i").replace("I", "i")
    if tabir not in _TAG_TABIRLERI:
        return {"error": "Bilinmeyen aranan: '%s'. Desteklenenler: %s"
                         % (temiz_aranan,
                            ", ".join(sorted(_TAG_TABIRLERI)))}
    try:
        yaricap = int(str(yaricap_m).strip()
                      if yaricap_m not in (None, "") else 0)
    except (TypeError, ValueError):
        return {"error": "Yaricap sayi olmali, gelen: '%s'." % yaricap_m}
    if not yaricap:
        yaricap = _YARICAP_VARSAYILAN_M
    if yaricap < _YARICAP_ALT_M or yaricap > _YARICAP_TAVAN_M:
        return {"error": "Yaricap %d-%d m arasinda olmali; gelen %d."
                         % (_YARICAP_ALT_M, _YARICAP_TAVAN_M, yaricap)}

    merkez_bilgi, sebep = _merkezi_coz(temiz_merkez)
    if merkez_bilgi is None:
        return {"error": "Merkez cozulemedi: %s" % sebep}

    sorgu = _overpass_sorgusu(tabir, merkez_bilgi["enlem"],
                              merkez_bilgi["boylam"], yaricap)
    anahtar = "%s,%s|%d|%s" % (merkez_bilgi["enlem"],
                               merkez_bilgi["boylam"], yaricap, tabir)
    hazir = _onbellek_oku(anahtar)
    if hazir is not None:
        adaylar = hazir
        hatlar = [{"kaynak": _HAT_OVERPASS, "durum": "onbellek"}]
    else:
        hatlar = []
        veri, hat, hata = _overpass_json_al(sorgu)
        if hata:
            hatlar.append(_hat_kaydi(_HAT_OVERPASS, hata=hata))
            return {"error": "Overpass hatti yanit vermedi: %s"
                             % _deneme_ozeti(hatlar)}
        hatlar.append(_hat_kaydi(_HAT_OVERPASS, adaylar=[]))
        adaylar = _overpass_adaylari(veri, merkez_bilgi["enlem"],
                                     merkez_bilgi["boylam"])
        if adaylar:
            _onbellege_yaz(anahtar, adaylar)

    if not adaylar:
        return {"error": "Sonuc bulunamadi: '%s' (%s), yaricap %d m. "
                         "denenen hatlar: %s"
                         % (temiz_aranan,
                            merkez_bilgi.get("gosterim_adi") or temiz_merkez,
                            yaricap, _deneme_ozeti(hatlar))}

    return {"result": _j({
        "merkez": {
            "gosterim_adi": merkez_bilgi["gosterim_adi"],
            "enlem": merkez_bilgi["enlem"],
            "boylam": merkez_bilgi["boylam"],
            "kaynak": merkez_bilgi["kaynak"],
        },
        "aranan": tabir,
        "yaricap_m": yaricap,
        "sonuc_sayisi": len(adaylar),
        "sonuclar": adaylar,
        "denenen_hatlar": hatlar,
    })}


def mesafe_sure(nereden, nereye, seyahat="araba"):
    """Iki konum arasi karayolu mesafesini ve sureyi OSRM'le hesaplar.

    nereden/nereye: adres, yer adi veya 'enlem,boylam'; koordinat
    degilse Z1 (konum_coz) kullanilir.
    seyahat: araba (bos/varsayilan), bisiklet, piyade. Baska deger
    hata doner; araba demoyu iki hat, bisiklet/piyade resmi olarak
    yalniz FOSSGIS hattiyla denir (denenen_hatlar bunu soyler).

    Donus: {"result": JSON} — nereden/nereye (gosterim_adi + koordinat),
    seyahat, mesafe_km, sure_dk, kaynak, baglanti (Google Maps yol
    tarifi), denenen_hatlar. Karayolu uzerindeki gercek rota tabanlidir;
    kus-bagisi mesafe DEGILDIR. Cozulemezse {"error": ...} doner,
    sayi UYDURULMAZ."""
    temiz_nereden = _konum_temizle(nereden)
    temiz_nereye = _konum_temizle(nereye)
    if not temiz_nereden or not temiz_nereye:
        return {"error": "nereden ve nereye bos olamaz."}
    if len(temiz_nereden) > KONUM_TAVANI or len(temiz_nereye) > KONUM_TAVANI:
        return {"error": "Konum metni cok uzun (en fazla %d karakter)."
                         % KONUM_TAVANI}
    profil = str(seyahat or "araba").strip().lower() or "araba"
    if profil not in _OSRM_HATLARI:
        return {"error": "Bilinmeyen seyahat sekli: '%s'. Desteklenenler: %s"
                         % (seyahat, ", ".join(sorted(_OSRM_HATLARI)))}

    baslangic, sebep_bas = _merkezi_coz(temiz_nereden)
    bitis, sebep_bit = _merkezi_coz(temiz_nereye)
    if baslangic is None:
        return {"error": "nereden cozulemedi: %s" % sebep_bas}
    if bitis is None:
        return {"error": "nereye cozulemedi: %s" % sebep_bit}

    # OSRM API sirasi lon,lat (yani boylam,enlem) — karistirma.
    yol_metni = "%s,%s;%s,%s" % (baslangic["boylam"], baslangic["enlem"],
                                 bitis["boylam"], bitis["enlem"])
    hatlar = []
    rota = None
    isim = None
    for taban in _OSRM_HATLARI[profil]:
        url = "%s/%s?overview=false&alternatives=false" % (taban, yol_metni)
        veri, hata = _json_al(url)
        if hata or not isinstance(veri, dict):
            hatlar.append(_hat_kaydi(_HAT_OSRM, hata=hata
                                      or "beklenmeyen yanit"))
            continue
        if str(veri.get("code") or "") != "Ok" or not veri.get("routes"):
            sebep = "OSRM code=%s" % veri.get("code")
            hatlar.append(_hat_kaydi(_HAT_OSRM, hata=sebep))
            continue
        rota = (veri.get("routes") or [])[0] or {}
        hatlar.append(_hat_kaydi(_HAT_OSRM, adaylar=[rota]))
        isim = str(taban).split("/")[2]
        break

    if rota is None:
        return {"error": "Mesafe hesaplanamadi: %s"
                         % (_deneme_ozeti(hatlar) or "hat yanit vermedi")}

    mesafe_m = _sayi(rota.get("distance"))
    sure_s = _sayi(rota.get("duration"))
    if mesafe_m is None or sure_s is None:
        return {"error": "OSRM yanitinda mesafe/sure alanlari yok: %s"
                         % _deneme_ozeti(hatlar)}

    sonuc_g = harita_goster(konum=temiz_nereye, mod=MOD_YOL)
    baglanti = ""
    if "result" in sonuc_g:
        baglanti = str(json.loads(sonuc_g["result"]).get("baglanti") or "")

    return {"result": _j({
        "nereden": {
            "gosterim_adi": baslangic["gosterim_adi"],
            "enlem": baslangic["enlem"],
            "boylam": baslangic["boylam"],
            "kaynak": baslangic["kaynak"],
        },
        "nereye": {
            "gosterim_adi": bitis["gosterim_adi"],
            "enlem": bitis["enlem"],
            "boylam": bitis["boylam"],
            "kaynak": bitis["kaynak"],
        },
        "seyahat": profil,
        "mesafe_km": round(mesafe_m / 1000.0, 1),
        "sure_dk": round(sure_s / 60.0, 1),
        "kaynak": _HAT_OSRM,
        "hat": isim,
        "baglanti": baglanti,
        "denenen_hatlar": hatlar,
    })}


