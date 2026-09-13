"""tools/web_search.py — DuckDuckGo web araması ve sayfa okuma.

Hava durumu sorguları için Open-Meteo API kullanılır (ücretsiz, API key gerektirmez).
Diğer sorgular için DuckDuckGo kullanılır.
"""

import ipaddress
import json
import logging
import re
import socket
import urllib.error
import urllib.request
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def web_search(query: str) -> dict:
    """DuckDuckGo'da arama yapar. Hava durumu için özel API kullanır."""
    if not query or not query.strip():
        return {"error": "Arama sorgusu boş olamaz"}

    q = query.strip()

    # Hava durumu sorgusu mu?

    # Diğer sorgular için DuckDuckGo
    return _duckduckgo_ara(q)


BICIM = chr(37) + "s" + chr(10) + chr(37) + "s" + chr(10) + chr(37) + "s"
AYIRAC = chr(10) + chr(10)


def _duckduckgo_ara(query):
    """DuckDuckGo'da arama yapar.

    2026-09-13: eskiden 3 sonuc alinip yalniz 2 snippet donuyordu ve
    _temizle() URL'leri metinden siliyordu — model "ara, sonucu sec,
    sayfayi ac" zincirini kuramiyordu cunku elinde adres kalmiyordu.
    Artik sonuclar BASLIK + ADRES + METIN olarak oldugu gibi verilir.
    """
    try:
        from ddgs import DDGS

        with DDGS() as ddgs:
            results = list(ddgs.text(query, region="tr-tr", max_results=20))

        if not results:
            return {"result": "Sonuc bulunamadi"}

        parcalar = []
        parcalar = []
        for r in results:
            parcalar.append(BICIM % (
                (r.get("title") or "").strip(),
                (r.get("href") or "").strip(),
                (r.get("body") or "").strip()))
        return {"result": AYIRAC.join(parcalar)}

    except ImportError:
        return {"error": "ddgs paketi yuklu degil"}
    except Exception as e:
        logger.error("Web arama hatasi: %s", e)
        return {"error": "Arama yapilamadi: %s" % e}


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
_MAX_SAYFA = 200000
_MAX_HAM = 2 * 1024 * 1024  # Ham HTML ust siniri (2 MB)

# SSRF korumasi (2026-08-24, Casper'in bulgusu): string tabanli "localhost"
# aramasi 127.0.0.2, [::1], onluk IP, ozel aglar ve ic IP'ye cozunen
# domain'leri geciriyordu. Artik hostname COZULUR ve tum IP'lerin ozellikleri
# denetlenir; yonlendirmelerde de her adim yeniden denetlenir.
_IZINLI_PORT = (80, 443)


def _engelli_ip_nedeni(hostname):
    """Hostname'in cozuldugu TUM IP'ler guvenli mi?

    Engel bulursa neden IP'yi, hepsi guvenliyse None dondurur.
    getaddrinfo tabanli oldugu icin onluk/hex/sekizlik IP yazimlari ve
    DNS uzerinden ic adreslere yonlenen domain'ler de yakalanir.
    """
    try:
        bilgiler = socket.getaddrinfo(hostname, None)
    except (socket.gaierror, OSError):
        return "adres cozulemedi"
    for b in bilgiler:
        try:
            ip = ipaddress.ip_address(b[4][0])
        except ValueError:
            continue
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
            return str(ip)
    return None


def _guvenli_adres(url):
    """URL'in adres bilesenlerini denetler; engel varsa hata metni doner."""
    k = urlparse(url)
    if k.scheme not in ("http", "https"):
        return "Yalnizca http/https URL'leri okunabilir"
    if k.port is not None and k.port not in _IZINLI_PORT:
        return ("Guvenlik engeli: yalnizca standart web portlari "
                "(80/443) aciktir")
    if not k.hostname:
        return "Gecersiz URL: sunucu adi yok"
    engel = _engelli_ip_nedeni(k.hostname)
    if engel:
        return ("Guvenlik engeli: adres ic/ağ adresine cozuldu (%s)"
                % engel[:40])
    return None


class _GuvenliYonlendirme(urllib.request.HTTPRedirectHandler):
    """Her yonlendirme adimini yeniden SSRF denetiminden gecirir."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        engel = _guvenli_adres(newurl)
        if engel:
            logger.warning("Yonlendirme engellendi: %s", engel[:80])
            return None   # None = takip etme -> HTTPError firlar
        return super().redirect_request(req, fp, code, msg, headers, newurl)


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

    # URL encode: Turkce/harf disi karakterleri HTTP yolunda encode et
    # Python http.client ASCII olmayan yollarda UnicodeEncodeError firlatir
    try:
        from urllib.parse import urlparse as _urlparse, quote as _quote
        _k = _urlparse(url)
        if _k.path:
            _yeni_path = _quote(_k.path, safe="/:@!$&'()*+,;=-._~")
            url = f"{_k.scheme}://{_k.netloc}{_yeni_path}"
            if _k.query:
                url += f"?{_k.query}"
            if _k.fragment:
                url += f"#{_k.fragment}"
    except Exception:
        pass  # Encode edilemezse orijinal URL ile devam et

    # SSRF denetimi: semantik + port + cozulen IP'ler
    engel = _guvenli_adres(url)
    if engel:
        return {"error": engel}

    try:
        import html as html_mod

        opener = urllib.request.build_opener(_GuvenliYonlendirme())
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Basak/1.0",
            "Accept": "text/html, text/plain",
            "Accept-Encoding": "identity",
        })
        with opener.open(req, timeout=15) as resp:
            # Icerik turunu kontrol et
            content_type = resp.headers.get("Content-Type", "")
            if "text/html" not in content_type and \
               "text/plain" not in content_type:
                return {"error": "Desteklenen icerik tipi degil: %s"
                                 % content_type[:50]}

            ham = resp.read(_MAX_HAM).decode(
                "utf-8", errors="replace")

        # HTML etiketlerini temizle
        if "text/html" in content_type:
            # <script>, <style>, <noscript> bloklarini temizle
            # 1) Kapanmis bloklari kaldir
            temiz = re.sub(
                r'<(script|style|noscript)[^>]*>.*?</\1>',
                '', ham, flags=re.DOTALL | re.IGNORECASE)
            # 2) Kapanmamis bloklari kaldir (dosya sonunda kesilmis)
            temiz = re.sub(
                r'<(script|style|noscript)[^>]*>.*',
                '', temiz, flags=re.DOTALL | re.IGNORECASE)
            # HTML yorumlarini kaldir
            temiz = re.sub(r'<!--.*?-->', '', temiz, flags=re.DOTALL)
            # SVG iceriklerini kaldir
            temiz = re.sub(r'<svg[^>]*>.*?</svg>', '', temiz,
                           flags=re.DOTALL | re.IGNORECASE)
            temiz = re.sub(r'<svg[^>]*>.*', '', temiz,
                           flags=re.DOTALL | re.IGNORECASE)
            # Tum HTML etiketlerini kaldir
            temiz = re.sub(r'<[^>]+>', ' ', temiz)
            # Kapanmamis < parcasi kaldiysa temizle
            temiz = re.sub(r'<\s*$', '', temiz)
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
