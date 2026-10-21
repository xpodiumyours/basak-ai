"""tools/harita.py — Harita: baglanti (Z0), konum (Z1), sube bulma (Z3).

Z0 (`harita_goster`): ag cagrisi YOK, anahtar YOK, kota YOK. Yalniz Google
Maps URL semasi uretilir; kullanici tiklayinca harita kendi tarayicisinda
acilir. Kaynak (resmi): developers.google.com/maps/documentation/urls/
get-started — "Maps URLs" icin API anahtari gerekmez.

Z1 (`konum_coz`): adres/yer adi -> enlem/boylam. Once Photon (OpenStreetMap,
anahtarsiz), olmazsa Open-Meteo geocoding. SSRF savunmasi YENIDEN YAZILMAZ:
tools/web_search.py icindeki `_guvenli_adres` + `_GuvenliYonlendirme`
kullanilir (her yonlendirme adimi yeniden denetlenir). Bulunamazsa hata
doner; koordinat UYDURULMAZ.

Z3 (`sube_bul`): marka + merkez + yaricap -> OpenStreetMap Overpass uzerinden
markanin kayitli subeleri. Anahtar YOK, kota YOK (makul kullanim); OSM acik
verisi ODbL'dir, sonuc kaydinda `atif` alani tasir. Sonuc 0 ise sube YOK
degil, OSM'de KAYITLI DEGIL demektir; bu ayrim sonucta acikca yazilir.

Her cagri `denenen_hatlar` alanini doner: hangi hat denendi, kac aday verdi
ya da NEDEN basarisiz oldu. Bu alan 2026-10-01'de yasanan sessiz bozulmaya
karsi eklendi: Photon'a gonderilen gecersiz `lang=tr` parametresi HTTP 400
uretiyordu ve hata sebebi yutuldugu icin birincil hat bozuk oldugu halde
aylarca gorunmedi.
"""

import json
import logging
import math
import re
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


def _json_al(url, sure=None):
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
        with opener.open(istek, timeout=sure or _ZAMAN_ASIMI) as yanit:
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


# ── Z3: sube bulma (marka + bolge -> kayitli subeler) ───────────────
#
# OpenStreetMap Overpass API: anahtar YOK, kota YOK (makul kullanim),
# ODbL atfi zorunlu. Sorgu tek istektir; marka regex olarak kacirilir,
# yaricap ve sonuc sayisi sinirlidir (Overpass genel sunucusu icin
# nazik davranis). `sube_sayisi == 0` subenin YOLDA olmadigi anlamina
# GELMEZ — yalnizca OSM'de kayitli olmadigi anlamina gelir; bu ayrim
# sonucta `not` alaninda acikca yazilir.

OVERPASS_TABANI = "https://overpass-api.de/api/interpreter"
# Yedek aynalar: ana sunucu bakimda olabilir ya da belirli IP araliklarini
# engelleyebilir (2026-10-20: bulut IP'sinden nginx 406 olculdu). Sira
# onemli: ana sunucu once, topluluk aynalari sonra denenir; her deneme
# `denenen_hatlar` kaydina hata sebebiyle yazilir (Z1'deki desen).
OVERPASS_AYNALAR = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.osm.ch/api/interpreter",
)
_SUBE_ZAMAN_ASIMI = 20
_SUBE_SONUC_TAVANI = 50
_YARICAP_VARSAYILAN = 5.0     # km
_YARICAP_TAVANI = 25.0        # km — genel Overpass sunucusu icin ust sinir
_ATFI = "Veri: © OpenStreetMap katkıda bulunanlar (ODbL)"


_PHOTON_TABANI = "https://photon.komoot.io/api/?"


def _sade(metin):
    """Marka karşılaştırması için Türkçe-duyarsız küçük harf."""
    tablo = str.maketrans({"ç": "c", "Ç": "c", "ğ": "g", "Ğ": "g",
                           "ı": "i", "İ": "i", "ö": "o", "Ö": "o",
                           "ş": "s", "Ş": "s", "ü": "u", "Ü": "u"})
    return " ".join(str(metin or "").translate(tablo).lower().split())


def _photon_adresi(marka, enlem, boylam):
    """Photon POI araması — Overpass'a ulaşılamadığında yedek hat."""
    return _PHOTON_TABANI + urllib.parse.urlencode({
        "q": marka,
        "lat": "%.6f" % enlem,
        "lon": "%.6f" % boylam,
        "limit": 50,
    })


def _photon_subeleri(veri, marka, enlem, boylam, yaricap_km):
    """Photon yanıtını şube kayıtlarına çevirir (ağ yok, saf dönüşüm).

    Yalnız adı markayı içeren ve yarıçap içinde kalan kayıtlar alınır;
    eşleşmeyen kayıt şube sayılmaz (uydurma yok).
    """
    if not isinstance(veri, dict):
        return []
    ozellikler = veri.get("features")
    if not isinstance(ozellikler, list):
        return []
    aranan = _sade(marka)
    tipler = {"N": "node", "W": "way", "R": "relation"}
    subeler = []
    for ozellik in ozellikler:
        if not isinstance(ozellik, dict):
            continue
        p = ozellik.get("properties") or {}
        geometri = ozellik.get("geometry") or {}
        koordinat = geometri.get("coordinates") or []
        if not isinstance(p, dict) or len(koordinat) < 2:
            continue
        boy = _sayi(koordinat[0])
        en = _sayi(koordinat[1])
        if not _gecerli_koordinat(en, boy):
            continue
        ad = str(p.get("name") or "").strip()
        if aranan and aranan not in _sade(ad):
            continue
        mesafe = _mesafe_km(enlem, boylam, en, boy)
        if mesafe > yaricap_km:
            continue
        adres_parcalari = []
        for anahtar in ("street", "housenumber", "district", "city",
                        "postcode"):
            deger = str(p.get(anahtar) or "").strip()
            if deger and deger not in adres_parcalari:
                adres_parcalari.append(deger)
        subeler.append({
            "ad": ad or marka,
            "enlem": round(en, 6),
            "boylam": round(boy, 6),
            "adres": ", ".join(adres_parcalari),
            "tip": str(p.get("osm_value") or "").strip(),
            "telefon": str(p.get("phone") or "").strip(),
            "website": str(p.get("website") or "").strip(),
            "mesafe_km": round(mesafe, 2),
            "osm_id": p.get("osm_id"),
            "osm_tip": tipler.get(str(p.get("osm_type") or "").upper(), ""),
        })
    subeler.sort(key=lambda k: k["mesafe_km"])
    return subeler[:_SUBE_SONUC_TAVANI]


def _ayna_adi(url):
    """Hata mesajinda kisa ayna adi (host) gorunur, tam URL degil."""
    try:
        return urllib.parse.urlsplit(str(url or "")).hostname or str(url)
    except ValueError:
        return str(url)


def _mesafe_km(en1, boylam1, en2, boylam2):
    """Iki nokta arasi kus ucusu mesafesi (haversine, km)."""
    p1, p2 = math.radians(en1), math.radians(en2)
    dp = math.radians(en2 - en1)
    db = math.radians(boylam2 - boylam1)
    a = (math.sin(dp / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(db / 2) ** 2)
    return 2 * 6371.0 * math.asin(math.sqrt(a))


def _merkez_coz(konum):
    """'enlem,boylam' dogrudan okunur; degilse konum_coz'e devredilir.

    Donus: (enlem, boylam, gosterim_adi, kaynak) ya da (None, None, "", hata).
    """
    temiz = _konum_temizle(konum)
    if not temiz:
        return None, None, "", "Konum boş olamaz."
    parcalar = [p.strip() for p in temiz.split(",")]
    if len(parcalar) == 2:
        enlem = _sayi(parcalar[0])
        boylam = _sayi(parcalar[1])
        if _gecerli_koordinat(enlem, boylam):
            return enlem, boylam, temiz, "koordinat"
    sonuc = konum_coz(temiz)
    if "result" in sonuc:
        veri = json.loads(sonuc["result"])
        return (veri["enlem"], veri["boylam"],
                veri["gosterim_adi"], veri["kaynak"])
    return None, None, "", sonuc.get("error") or "Konum bulunamadı."


def _overpass_sorgusu(enlem, boylam, yaricap_m, marka_deseni):
    """Overpass QL — marka adi brand/name etiketlerinde aranir, tek istek."""
    merkez = "%.6f,%.6f" % (enlem, boylam)
    etiketler = ("brand", "name")
    dallar = []
    for etiket in etiketler:
        for tip in ("node", "way"):
            dallar.append('%s(around:%d,%s)["%s"~"%s",i];'
                          % (tip, yaricap_m, merkez, etiket, marka_deseni))
    return ("[out:json][timeout:%d];(\n%s\n);\nout center %d;"
            % (_SUBE_ZAMAN_ASIMI, "\n".join(dallar), _SUBE_SONUC_TAVANI))


def _sube_kaydi(eleman, enlem, boylam):
    """Overpass elemanindan sube kaydi; merkezi olmayan eleman atlanir."""
    if not isinstance(eleman, dict):
        return None
    if eleman.get("type") == "node":
        en = _sayi(eleman.get("lat"))
        boy = _sayi(eleman.get("lon"))
    else:
        merkez = eleman.get("center") or {}
        en = _sayi(merkez.get("lat"))
        boy = _sayi(merkez.get("lon"))
    if not _gecerli_koordinat(en, boy):
        return None
    etiket = eleman.get("tags") or {}
    if not isinstance(etiket, dict):
        etiket = {}
    adres_parcalari = []
    for anahtar in ("addr:street", "addr:housenumber", "addr:district",
                    "addr:city", "addr:postcode"):
        deger = str(etiket.get(anahtar) or "").strip()
        if deger and deger not in adres_parcalari:
            adres_parcalari.append(deger)
    return {
        "ad": str(etiket.get("name") or etiket.get("brand") or "").strip(),
        "enlem": round(en, 6),
        "boylam": round(boy, 6),
        "adres": ", ".join(adres_parcalari),
        "tip": str(etiket.get("shop") or etiket.get("amenity")
                    or etiket.get("office") or "").strip(),
        "telefon": str(etiket.get("phone") or etiket.get("contact:phone")
                       or "").strip(),
        "website": str(etiket.get("website") or etiket.get("contact:web")
                       or "").strip(),
        "mesafe_km": round(_mesafe_km(enlem, boylam, en, boy), 2),
        "osm_id": eleman.get("id"),
        "osm_tip": eleman.get("type"),
    }


def sube_bul(marka, konum, yaricap_km=None):
    """Markanin bir bolgedeki kayitli subelerini OpenStreetMap'te bulur.

    marka:     aranacak marka adi (regex olarak kacirilir).
    konum:     merkez — 'enlem,boylam' ya da adres/yer adi (konum_coz).
    yaricap_km: arama yaricapi (varsayilan 5, en fazla 25).

    Donus: {"result": JSON} — marka, merkez, yaricap_km, sube_sayisi,
    subeler (ad, enlem, boylam, adres, tip, telefon, website, mesafe_km,
    osm_id, osm_tip; en yakin ilk), atif, denenen_hatlar. Sonuc 0 ise hata
    DEGILDIR — OSM'de kayitli oldugu anlamina gelmez:
    OSM'de kayitli olmadigi `not` alaninda belirtilir. Ag/servis hatasi
    ya da bulunamayan merkez {"error": ...} doner; sube UYDURULMAZ.
    """
    temiz_marka = _konum_temizle(marka)
    if not temiz_marka:
        return {"error": "Marka boş olamaz."}
    if len(temiz_marka) > 120:
        return {"error": "Marka çok uzun (en fazla 120 karakter)."}

    try:
        yaricap = float(yaricap_km) if yaricap_km not in (None, "") \
            else _YARICAP_VARSAYILAN
    except (TypeError, ValueError):
        return {"error": "yaricap_km sayı olmalı (km)."}
    if yaricap <= 0:
        return {"error": "yaricap_km sıfırdan büyük olmalı."}
    yaricap = min(yaricap, _YARICAP_TAVANI)

    enlem, boylam, gosterim_adi, merkez_kaynak = _merkez_coz(konum)
    if enlem is None:
        return {"error": "Merkez bulunamadı: %s" % merkez_kaynak}

    # Overpass regex RE2'dir; kullanici girdisi desen olamaz — kacirilir.
    marka_deseni = re.escape(temiz_marka)
    sorgu = _overpass_sorgusu(enlem, boylam, int(yaricap * 1000),
                              marka_deseni)
    sorgu_metni = urllib.parse.urlencode({"data": sorgu})

    veri = None
    denenen = []
    for ayna in OVERPASS_AYNALAR:
        aday_veri, hata = _json_al(ayna + "?" + sorgu_metni,
                                   sure=_SUBE_ZAMAN_ASIMI)
        if isinstance(aday_veri, dict):
            veri = aday_veri
            denenen.append({"ayna": ayna, "durum": "ok"})
            break
        denenen.append({"ayna": ayna, "durum": "hata",
                        "hata": hata or "beklenmeyen yanıt"})
    subeler = []
    gorulen = set()
    if isinstance(veri, dict):
        for eleman in (veri.get("elements") or []):
            kayit = _sube_kaydi(eleman, enlem, boylam)
            if not kayit:
                continue
            anahtar = (kayit["osm_tip"], kayit["osm_id"])
            if anahtar in gorulen:
                continue
            gorulen.add(anahtar)
            if kayit["mesafe_km"] <= yaricap:
                subeler.append(kayit)
        subeler.sort(key=lambda k: k["mesafe_km"])
        subeler = subeler[:_SUBE_SONUC_TAVANI]

    kaynak_veri = "overpass" if subeler else ""

    # 2. hat (2026-10-21 olcumu): Overpass aynalari bulut IP'sinden
    # 406/zaman asimi donuyor; o zaman Photon POI aramasi denenir
    # (ayni OpenStreetMap kayitlari, farkli servis). Sonuc yine OSM.
    photon_ok = False
    if not subeler:
        p_veri, p_hata = _json_al(_photon_adresi(temiz_marka, enlem, boylam),
                                  sure=_SUBE_ZAMAN_ASIMI)
        photon_ok = isinstance(p_veri, dict)
        if photon_ok:
            subeler = _photon_subeleri(p_veri, temiz_marka, enlem, boylam,
                                       yaricap)
            denenen.append({"ayna": _PHOTON_TABANI, "durum": "ok"
                            if subeler else "bos"})
            if subeler:
                kaynak_veri = "photon"
        else:
            denenen.append({"ayna": _PHOTON_TABANI, "durum": "hata",
                            "hata": p_hata or "beklenmeyen yanıt"})

    # Bos Overpass govdesi "baktım, yok" demek DEGILDIR (osm.ch gibi bos
    # veritabanli ayna 200 donuyor). Gercek arama sayilmasi icin ya sube
    # ya da Photon yaniti gerekir; ikisi de yoksa acik hata doner.
    gercek_arama = photon_ok or bool((veri or {}).get("elements"))
    if not gercek_arama:
        ozet = "; ".join("%s: %s" % (_ayna_adi(k.get("ayna")),
                                     k.get("hata") or "basarisız")
                         for k in denenen)
        return {"error": "OpenStreetMap servisine ulaşılamadı. Denenen "
                         "aynalar: %s" % ozet}

    not_metni = ""
    if not subeler:
        not_metni = ("Arama yapıldı; OpenStreetMap'te bu markanın bu "
                     "bölgede etiketli şubesi görünmüyor. Şubesi olabilir — "
                     "OSM kaydı eksik olabilir; harita_goster ile bölgede "
                     "arama yapılabilir.")

    return {"result": _j({
        "marka": temiz_marka,
        "merkez": {"enlem": round(enlem, 6), "boylam": round(boylam, 6),
                   "gosterim_adi": gosterim_adi,
                   "kaynak": merkez_kaynak},
        "yaricap_km": yaricap,
        "sube_sayisi": len(subeler),
        "subeler": subeler,
        "veri_kaynagi": kaynak_veri,
        "atif": _ATFI,
        "not": not_metni,
        "denenen_hatlar": denenen,
    })}
