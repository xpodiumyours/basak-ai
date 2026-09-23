"""tools/hava.py — Open-Meteo hava durumu (anahtarsız, ücretsiz).

İki uç: geocoding (şehir adı → enlem/boylam) + forecast (anlık sıcaklık,
hava kodu, rüzgâr). Yalnız urllib/stdlib; yeni pip paketi yok.
Hata/boşşehir/bulunamadı/ağ hatasında uydurma sıcaklık YOK — net
Türkçe hata döner. "İstanbul" varsayılanı YOK.
"""

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

_GEOCODING = "https://geocoding-api.open-meteo.com/v1/search"
_FORECAST = "https://api.open-meteo.com/v1/forecast"
_ZAMAN_ASIMI = 8

# WMO weather_code → Türkçe kısa etiket.
_ETIKETLER = {
    0: "Açık",
    1: "Az bulutlu",
    2: "Parçalı bulutlu",
    3: "Çok bulutlu",
    45: "Sisli",
    46: "Sisli (donducu)",
    51: "Hafif çisenti",
    53: "Çisenti",
    55: "Yoğun çisenti",
    56: "Donan çisenti",
    57: "Donan çisenti",
    61: "Hafif yağmurlu",
    63: "Yağmurlu",
    65: "Şiddetli yağmurlu",
    66: "Donan yağmur",
    67: "Donan yağmur",
    71: "Hafif kar yağışlı",
    73: "Kar yağışlı",
    75: "Yoğun kar yağışlı",
    77: "Kar taneleri",
    80: "Hafif sağanak",
    81: "Sağanak yağış",
    82: "Şiddetli sağanak",
    85: "Kar sağanağı",
    86: "Yoğun kar sağanağı",
    95: "Gök gürültülü fırtına",
    96: "Dolulu fırtına",
    99: "Şiddetli dolulu fırtına",
}


def hava_etiketi(kod):
    """WMO weather_code → Türkçe kısa etiket; bilinmeyen kod için net yazı."""
    try:
        return _ETIKETLER.get(int(kod), "Bilinmeyen hava")
    except (TypeError, ValueError):
        return "Bilinmeyen hava"


def _git(url):
    istek = urllib.request.Request(
        url, headers={"User-Agent": "basak-hava/1.0"})
    with urllib.request.urlopen(istek, timeout=_ZAMAN_ASIMI) as yanit:
        return json.loads(yanit.read().decode("utf-8"))


def _ag_hatasi():
    return {"error": "Hava durumu servisine ulaşılamadı (ağ hatası)."}


def hava_durumu(sehir: str) -> dict:
    """Şehrin anlık hava durumunu Open-Meteo'dan okur.

    Dönüş: {"result": "..."} — sıcaklık, hava etiketi, rüzgâr, saat:dakika
    zaman damgası + kaynak: open-meteo. Bulunamadı/ağ hatası → {"error": ...}
    ve uydurma sıcaklık asla üretilmez.
    """
    sehir = (sehir or "").strip()
    if not sehir:
        return {"error": "Şehir adı boş olamaz."}
    if len(sehir) > 100:
        return {"error": "Şehir adı çok uzun (en fazla 100 karakter)."}

    sorgu = urllib.parse.urlencode({
        "name": sehir, "count": 1, "language": "tr", "format": "json"})
    try:
        geo = _git(_GEOCODING + "?" + sorgu)
    except (urllib.error.URLError, OSError, ValueError, TimeoutError):
        return _ag_hatasi()
    except Exception:
        return _ag_hatasi()

    sonuclar = (geo or {}).get("results") or []
    if not sonuclar:
        return {"error": "Şehir bulunamadı: %s" % sehir}

    ilk = sonuclar[0]
    try:
        enlem = ilk["latitude"]
        boylam = ilk["longitude"]
    except (KeyError, TypeError):
        return _ag_hatasi()
    bulunan = str(ilk.get("name") or sehir).strip() or sehir

    sorgu2 = urllib.parse.urlencode({
        "latitude": enlem,
        "longitude": boylam,
        "current": "temperature_2m,weather_code,wind_speed_10m",
        "timezone": "auto",
    })
    try:
        tahmin = _git(_FORECAST + "?" + sorgu2)
    except (urllib.error.URLError, OSError, ValueError, TimeoutError):
        return _ag_hatasi()
    except Exception:
        return _ag_hatasi()

    simdi = (tahmin or {}).get("current") or {}
    sicaklik = simdi.get("temperature_2m")
    if not isinstance(sicaklik, (int, float)):
        return {"error": "Sıcaklık verisi alınamadı: %s" % bulunan}

    etiket = hava_etiketi(simdi.get("weather_code"))
    parcalar = ["%s: %s°C" % (bulunan, round(float(sicaklik), 1)), etiket]

    ruzgar = simdi.get("wind_speed_10m")
    if isinstance(ruzgar, (int, float)):
        parcalar.append("rüzgâr %s km/sa" % round(float(ruzgar), 1))

    zaman = str(simdi.get("time") or "")
    if "T" in zaman and len(zaman) >= 16:
        saat = zaman.split("T", 1)[1][:5]
    else:
        saat = datetime.now().strftime("%H:%M")
    parcalar.append("(%s)" % saat)

    satir = ", ".join(parcalar) + " — kaynak: open-meteo"
    return {"result": satir}
