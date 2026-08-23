"""tools/web_search.py — DuckDuckGo web araması + hava durumu API.

Hava durumu sorguları için Open-Meteo API kullanılır (ücretsiz, API key gerektirmez).
Diğer sorgular için DuckDuckGo kullanılır.
"""

import json
import logging
import re

logger = logging.getLogger(__name__)


def web_search(query: str) -> dict:
    """DuckDuckGo'da arama yapar. Hava durumu için özel API kullanır."""
    if not query or not query.strip():
        return {"error": "Arama sorgusu boş olamaz"}

    q = query.strip()

    # Hava durumu sorgusu mu?
    if _hava_durumu_mu(q):
        return _hava_durumu_cek(q)

    # Diğer sorgular için DuckDuckGo
    return _duckduckgo_ara(q)


def _hava_durumu_mu(query):
    """Sorgunun hava durumu ile ilgili olup olmadığını kontrol eder."""
    anahtarlar = ['hava', 'sıcaklık', 'derece', 'yağmur', 'kar', 'güneş',
                  'weather', 'temperature', 'forecast']
    return any(k in query.lower() for k in anahtarlar)


def _sehir_cek(query):
    """Sorgudan şehir adını çeker."""
    sehirler = {
        'istanbul': (41.0082, 28.9784),
        'ankara': (39.9334, 32.8597),
        'izmir': (38.4237, 27.1428),
        'bursa': (40.1885, 29.0610),
        'antalya': (36.8969, 30.7133),
        'trabzon': (41.0027, 39.7168),
        'konya': (37.8746, 32.4932),
        'adana': (37.0000, 35.3213),
    }
    q = query.lower()
    for sehir, koordinat in sehirler.items():
        if sehir in q:
            return sehir.capitalize(), koordinat
    return "Istanbul", (41.0082, 28.9784)  # Varsayılan


def _hava_durumu_cek(query):
    """Open-Meteo API ile hava durumu çeker (ücretsiz)."""
    sehir, (enlem, boylam) = _sehir_cek(query)

    try:
        import urllib.request
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={enlem}&longitude={boylam}"
            f"&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m"
            f"&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max"
            f"&timezone=Europe/Istanbul&forecast_days=1"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Basak/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        current = data.get("current", {})
        daily = data.get("daily", {})

        sicaklik = current.get("temperature_2m", "?")
        nem = current.get("relative_humidity_2m", "?")
        ruzgar = current.get("wind_speed_10m", "?")
        kod = current.get("weather_code", 0)

        # Hava durumu kodunu çevir
        durum = _hava_kodu_cevir(kod)

        max_sic = daily.get("temperature_2m_max", ["?"])[0]
        min_sic = daily.get("temperature_2m_min", ["?"])[0]
        yagis = daily.get("precipitation_probability_max", ["?"])[0]

        return {
            "result": (
                f"{sehir} hava durumu: {durum}, {sicaklik}°C. "
                f"Gün içinde {min_sic}°C ile {max_sic}°C arası. "
                f"Nem: %{nem}, Rüzgar: {ruzgar} km/s. "
                f"Yağış ihtimali: %{yagis}."
            )
        }

    except Exception as e:
        logger.error("Hava durumu API hatası: %s", e)
        return {"error": f"Hava durumu alınamadı: {e}"}


def _hava_kodu_cevir(kod):
    """WMO hava durumu kodunu Türkçe çevirir."""
    harita = {
        0: "Açık", 1: "Az bulutlu", 2: "Parçalı bulutlu", 3: "Kapalı",
        45: "Sisli", 48: "Buzlu sis",
        51: "Hafif çiseleme", 53: "Orta çiseleme", 55: "Şiddetli çiseleme",
        61: "Hafif yağmur", 63: "Orta yağmur", 65: "Şiddetli yağmur",
        71: "Hafif kar", 73: "Orta kar", 75: "Şiddetli kar",
        80: "Hafif sağanak", 81: "Orta sağanak", 82: "Şiddetli sağanak",
        95: "Gök gürültülü fırtına",
    }
    return harita.get(kod, "Bilinmeyen")


def _duckduckgo_ara(query):
    """DuckDuckGo'da arama yapar."""
    try:
        from ddgs import DDGS

        with DDGS() as ddgs:
            results = list(ddgs.text(query, region="tr-tr", max_results=3))

        if not results:
            return {"result": "Sonuç bulunamadı"}

        parcalar = []
        for r in results:
            body = r.get("body", "").strip()
            if not body or len(body) < 20:
                continue
            body = _temizle(body)
            if body:
                parcalar.append(body)

        if not parcalar:
            return {"result": "Sonuç bulunamadı"}

        return {"result": " | ".join(parcalar[:2])}

    except ImportError:
        return {"error": "ddgs paketi yüklü değil"}
    except Exception as e:
        logger.error("Web arama hatası: %s", e)
        return {"error": f"Arama yapılamadı: {e}"}


def _temizle(text):
    """Sonuç metnini temizler."""
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'www\.\S+', '', text)
    text = re.sub(r'Visit\s+\w+\s*', '', text)
    text = re.sub(r'A travel experience.*?streets,?\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'history is full of.*?new\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+', ' ', text).strip()
    if text and not text.endswith('.') and not text.endswith('...'):
        text += '.'
    return text


# E-2: Sayfa okuma aracı — yalnizca GET, 5000 karakter siniri
_MAX_SAYFA = 5000


def sayfa_oku(url: str) -> dict:
    """E-2: Bir URL'den sayfa icerigini okur (yalnizca GET).

    HTML icerikten etiketler soyulur, duz metin olarak dondurulur.
    Max 5000 karakter okunur.

    Args:
        url: Okunacak URL (http:// veya https://).

    Returns:
        {"result": str} veya {"error": str}.
    """
    if not url or not url.strip():
        return {"error": "URL bos olamaz"}

    url = url.strip()

    # URL dogrulama — yalnizca http/https
    if not url.startswith(("http://", "https://")):
        return {"error": "Yalnizca http/https URL'leri okunabilir"}

    # Tehlikeli domain kontrolu (basit whitelist)
    yasakli = ["localhost", "127.0.0.1", "0.0.0.0"]
    for y in yasakli:
        if y in url.lower():
            return {"error": "Guvenlik engeli: %s adresine erisilemez" % y}

    try:
        import urllib.request
        import html as html_mod

        req = urllib.request.Request(url, headers={
            "User-Agent": "Basak/1.0 (arastrirma)",
            "Accept": "text/html, text/plain",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            # Icerik turunu kontrol et
            content_type = resp.headers.get("Content-Type", "")
            if "text/html" not in content_type and \
               "text/plain" not in content_type:
                return {"error": "Desteklenen icerik tipi degil: %s"
                                 % content_type[:50]}

            ham = resp.read(_MAX_SAYFA + 1000).decode(
                "utf-8", errors="replace")

        # HTML etiketlerini temizle
        if "text/html" in content_type:
            # <script> ve <style> bloklarini kaldir
            temiz = re.sub(r'<(script|style)[^>]*>.*?</\1>', '',
                           ham, flags=re.DOTALL | re.IGNORECASE)
            # HTML etiketlerini kaldir
            temiz = re.sub(r'<[^>]+>', ' ', temiz)
            # HTML entity'leri coz
            temiz = html_mod.unescape(temiz)
        else:
            temiz = ham

        # Bosluklari temizle
        temiz = re.sub(r'\s+', ' ', temiz).strip()

        if len(temiz) > _MAX_SAYFA:
            temiz = temiz[:_MAX_SAYFA] + "\n...(ilk %d karakter)" % _MAX_SAYFA

        if not temiz:
            return {"error": "Sayfa icerigi bos"}

        return {"result": temiz}

    except urllib.error.HTTPError as e:
        return {"error": "HTTP hatasi %d: %s" % (e.code, url[:60])}
    except urllib.error.URLError as e:
        return {"error": "Baglanti hatasi: %s" % str(e.reason)[:80]}
    except Exception as e:
        logger.error("Sayfa okuma hatasi: %s", e)
        return {"error": "Sayfa okunamadi: %s" % str(e)[:80]}
