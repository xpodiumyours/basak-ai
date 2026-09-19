"""tools/web_search.py — DuckDuckGo web araması ve sayfa okuma.

Metin, haber, tarih filtreli, site-ici, gorsel ve kitap aramasi +
sayfa okuma (standart + derin). Dis ag cikisi yalniz DuckDuckGo
ucuna ve okunan sayfayadir; sayfa cekmede SSRF savunmasi aynen
gecerlidir (_guvenli_adres + _GuvenliYonlendirme).
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

# Arama sonucu adet sinirlari (girdi dogrulama; kota/baglam korumasi).
_MIN_SONUC = 1
_MAX_SONUC = 30
_VARSAYILAN_SONUC = 20


def _adet_sinirla(adet, varsayilan=_VARSAYILAN_SONUC):
    """Sonuc adedini sayiya cevirip 1..30 araligina alir."""
    try:
        n = int(adet)
    except (TypeError, ValueError):
        return varsayilan
    return max(_MIN_SONUC, min(_MAX_SONUC, n))


def web_search(query: str, adet: int = _VARSAYILAN_SONUC) -> dict:
    """DuckDuckGo'da arama yapar. Hava durumu için özel API kullanır."""
    if not query or not query.strip():
        return {"error": "Arama sorgusu boş olamaz"}

    q = query.strip()

    # Diger sorgular icin DuckDuckGo
    return _duckduckgo_ara(q, adet=_adet_sinirla(adet))


BICIM = chr(37) + "s" + chr(10) + chr(37) + "s" + chr(10) + chr(37) + "s"
AYIRAC = chr(10) + chr(10)


def _duckduckgo_ara(query, adet=_VARSAYILAN_SONUC):
    """DuckDuckGo'da arama yapar.

    2026-09-13: eskiden 3 sonuc alinip yalniz 2 snippet donuyordu ve
    _temizle() URL'leri metinden siliyordu — model "ara, sonucu sec,
    sayfayi ac" zincirini kuramiyordu cunku elinde adres kalmiyordu.
    Artik sonuclar BASLIK + ADRES + METIN olarak oldugu gibi verilir.
    """
    try:
        from ddgs import DDGS

        with DDGS() as ddgs:
            results = list(ddgs.text(query, region="tr-tr",
                                     max_results=_adet_sinirla(adet)))

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


def haber_ara(query: str, adet: int = 10) -> dict:
    """Haber arar; baslik + adres + tarih + metin doner.

    Tarih yoksa "tarihsiz" yazar, uydurulmaz.
    """
    if not query or not str(query).strip():
        return {"error": "Arama sorgusu boş olamaz"}
    try:
        from ddgs import DDGS

        with DDGS() as ddgs:
            results = list(ddgs.news(str(query).strip(), region="tr-tr",
                                     max_results=_adet_sinirla(adet, 10)))
        if not results:
            return {"result": "Haber bulunamadi"}
        parcalar = []
        for r in results:
            parcalar.append("%s\n%s\n%s | %s" % (
                (r.get("title") or "").strip(),
                (r.get("url") or r.get("href") or "").strip(),
                (r.get("date") or "").strip() or "tarihsiz",
                (r.get("body") or "").strip()))
        return {"result": AYIRAC.join(parcalar)}
    except ImportError:
        return {"error": "ddgs paketi yuklu degil"}
    except Exception as e:
        logger.error("Haber arama hatasi: %s", e)
        return {"error": "Haber aranamadi: %s" % e}


_ARALIK_HARITASI = {"gun": "d", "hafta": "w", "ay": "m"}


def zamanli_ara(query: str, aralik: str = "hafta",
                adet: int = 10) -> dict:
    """Tarih filtreli arama yapar; yalniz verilen aralik doner.

    aralik: gun | hafta | ay. Baska deger bicim hatasidir.
    """
    if not query or not str(query).strip():
        return {"error": "Arama sorgusu boş olamaz"}
    sinir = _ARALIK_HARITASI.get((aralik or "").strip().lower())
    if sinir is None:
        return {"error": "Aralik gun, hafta veya ay olmali."}
    try:
        from ddgs import DDGS

        with DDGS() as ddgs:
            results = list(ddgs.text(str(query).strip(), region="tr-tr",
                                     timelimit=sinir,
                                     max_results=_adet_sinirla(adet, 10)))
        if not results:
            return {"result": "Sonuc bulunamadi"}
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
        logger.error("Zamanli arama hatasi: %s", e)
        return {"error": "Arama yapilamadi: %s" % e}


def site_ara(site: str, sorgu: str, adet: int = 10) -> dict:
    """Yalniz verilen sitede arar. site: adres biciminde olmali."""
    if not sorgu or not str(sorgu).strip():
        return {"error": "Arama sorgusu boş olamaz"}
    adres = (site or "").strip().lower()
    if not adres or " " in adres or "." not in adres:
        return {"error": "Site adres biciminde olmali (orn. ornek.com)."}
    return _duckduckgo_ara("site:%s %s" % (adres, str(sorgu).strip()),
                           adet=_adet_sinirla(adet, 10))


def gorsel_ara(query: str, adet: int = 10) -> dict:
    """Gorsel arar; resim adreslerini JSON liste doner."""
    if not query or not str(query).strip():
        return {"error": "Arama sorgusu boş olamaz"}
    try:
        from ddgs import DDGS

        with DDGS() as ddgs:
            results = list(ddgs.images(str(query).strip(), region="tr-tr",
                                       max_results=_adet_sinirla(adet, 10)))
        adresler = []
        for r in results:
            aday = (r.get("image") or "").strip()
            if aday and aday not in adresler:
                adresler.append(aday)
        if not adresler:
            return {"error": "Gorsel bulunamadi"}
        return {"result": json.dumps(adresler, ensure_ascii=False)}
    except ImportError:
        return {"error": "ddgs paketi yuklu degil"}
    except Exception as e:
        logger.error("Gorsel arama hatasi: %s", e)
        return {"error": "Gorsel aranamadi: %s" % e}


def kitap_ara(query: str, adet: int = 10) -> dict:
    """Kitap/katalog/brosur arar; baslik + adres + metin doner."""
    if not query or not str(query).strip():
        return {"error": "Arama sorgusu boş olamaz"}
    try:
        from ddgs import DDGS

        with DDGS() as ddgs:
            results = list(ddgs.books(str(query).strip(),
                                      max_results=_adet_sinirla(adet, 10)))
        if not results:
            return {"result": "Kitap bulunamadi"}
        parcalar = []
        for r in results:
            parcalar.append(BICIM % (
                (r.get("title") or "").strip(),
                (r.get("url") or r.get("href") or "").strip(),
                (r.get("body") or r.get("publisher") or "").strip()))
        return {"result": AYIRAC.join(parcalar)}
    except ImportError:
        return {"error": "ddgs paketi yuklu degil"}
    except Exception as e:
        logger.error("Kitap arama hatasi: %s", e)
        return {"error": "Kitap aranamadi: %s" % e}


def derin_oku(url: str) -> dict:
    """Uzun sayfalar icin sayfa okuma (en fazla 500000 karakter).

    sayfa_oku ile ayni guvenli cekme hatti (_guvenli_adres +
    _GuvenliYonlendirme); yalniz tavan buyuktur. SSRF kurali aynidir.
    """
    return _sayfa_oku_genis(url, _MAX_DERIN)


# E-2: Sayfa okuma araci — yalnizca GET, 200000 karakter siniri
_MAX_SAYFA = 200000
# Derin okuma tavani (derin_oku): uzun sayfa/katalog metinleri icin.
_MAX_DERIN = 500000
_MAX_HAM = 50 * 1024 * 1024  # Ham HTML ust siniri (50 MB)

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
                % engel)
    return None


class _GuvenliYonlendirme(urllib.request.HTTPRedirectHandler):
    """Her yonlendirme adimini yeniden SSRF denetiminden gecirir."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        engel = _guvenli_adres(newurl)
        if engel:
            logger.warning("Yonlendirme engellendi: %s", engel)
            return None   # None = takip etme -> HTTPError firlar
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def sayfa_oku(url: str) -> dict:
    """E-2: Bir URL'den sayfa icerigini okur (yalnizca GET).

    HTML icerikten etiketler soyulur, duz metin olarak dondurulur.
    En fazla 200000 karakter doner (sema ile ayni).

    Args:
        url: Okunacak URL (http:// veya https://).

    Returns:
        {"result": str} veya {"error": str}.
    """
    return _sayfa_oku_genis(url, _MAX_SAYFA)


def _sayfa_oku_genis(url: str, tavan: int) -> dict:
    """Guvenli cekme hattinin tavan parametreli govdesi.

    sayfa_oku ve derin_oku buradan gecer; SSRF denetimi, yonlendirme
    korumasi ve icerik turu kurali ikisinde aynidir, yalniz cikti
    tavani degisir.
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
                                 % content_type}

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

        if len(temiz) > tavan:
            temiz = temiz[:tavan] + "\n...(ilk %d karakter)" % tavan

        if not temiz:
            return {"error": "Sayfa icerigi bos"}

        return {"result": temiz}

    except urllib.error.HTTPError as e:
        return {"error": "HTTP hatasi %d: %s" % (e.code, url)}
    except urllib.error.URLError as e:
        return {"error": "Baglanti hatasi: %s" % str(e.reason)}
    except Exception as e:
        logger.error("Sayfa okuma hatasi: %s", e)
        return {"error": "Sayfa okunamadi: %s" % str(e)}


def adres_kontrol(url: str) -> dict:
    """Canli adres kontrolu (Is 7): govde indirilmeden baslik okunur.

    Doner: HTTP durum kodu + yanit suresi + son yonlendirme adresi.
    Once HEAD denenir; sunucu desteklemezse govdesi okunMAyan kisa GET.
    SSRF savunmasi mevcut _guvenli_adres + _GuvenliYonlendirme ile
    aynen kullanilir (yeni savunma YAZILMADI).
    """
    import time as _time

    if not url or not str(url).strip():
        return {"error": "URL bos olamaz"}
    url = str(url).strip()

    engel = _guvenli_adres(url)
    if engel:
        return {"error": engel}

    def _istek(yontem):
        opener = urllib.request.build_opener(_GuvenliYonlendirme())
        req = urllib.request.Request(url, method=yontem, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Basak/1.0",
            "Accept-Encoding": "identity",
        })
        basla = _time.time()
        with opener.open(req, timeout=15) as resp:
            sure = _time.time() - basla
            return resp.status, sure, resp.geturl()

    try:
        try:
            durum, sure, son = _istek("HEAD")
        except urllib.error.HTTPError as e:
            if e.code in (400, 403, 404, 405, 501):
                durum, sure, son = _istek("GET")
            else:
                return {"error": "HTTP hatasi %d: %s" % (e.code, url)}
        return {"result": "durum: %d | sure: %.2f sn | adres: %s"
                          % (durum, sure, son)}
    except urllib.error.HTTPError as e:
        return {"error": "HTTP hatasi %d: %s" % (e.code, url)}
    except urllib.error.URLError as e:
        return {"error": "Baglanti hatasi: %s" % str(e.reason)}
    except Exception as e:
        logger.error("Adres kontrol hatasi: %s", e)
        return {"error": "Adres kontrol edilemedi: %s" % str(e)}


_GORSEL_UZANTI = (".jpg", ".jpeg", ".png", ".webp", ".gif")
_IMG_RE = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']',
                     re.IGNORECASE)
# 2026-09-18 (Faz B): lazy-load sitelerinde gorsel src'de degil,
# data-* niteliginde bekler (srcset ilk aday da denenir).
_IMG_DATA_RE = re.compile(
    r'<img[^>]+data-(?:src|original|lazy-src|lazy)=["\']([^"\']+)["\']',
    re.IGNORECASE)
_SRCSET_RE = re.compile("<img[^>]+srcset=[\"']([^\"']+)[\"']",
                        re.IGNORECASE)
_OG_RE = re.compile(
    r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
    re.IGNORECASE)
# Logo/ikon/şablon görselleri ürün sayfası eşleşmesinden düşer.
_GORSEL_ATIK_KELIME = ("logo", "icon", "favicon", "sprite", "placeholder",
                       "banner", "loading", "spinner", "avatar", "marka-")


def _srcset_ilk(deger):
    """srcset içeriğinden ilk aday URL'i döner ("a.jpg 400w, b.jpg 800w")."""
    ilk = (deger or "").split(",")[0].strip().split()[0] \
        if (deger or "").strip() else ""
    return ilk


def sayfa_gorseller(url: str, _acici=None) -> dict:
    """Sayfadaki ürün görsellerini toplar (yalnızca GET, salt-okunur).

    og:image önce, sonra <img> sırasıyla en fazla 10 adres döner.
    2026-09-18 (Faz B): data-src/data-original/srcset nitelikleri de
    taranır (lazy-load siteleri); logo/ikon/benzeri atık yollar
    elenir. SSRF savunması sayfa_oku ile aynı (_guvenli_adres +
    _GuvenliYonlendirme); yeni savunma yazılmadı.

    Dönüş: {"result": "[url, ...]"} veya {"error": ...}.
    """
    if not url or not str(url).strip():
        return {"error": "URL bos olamaz"}
    url = str(url).strip()

    engel = _guvenli_adres(url)
    if engel:
        return {"error": engel}

    try:
        from urllib.parse import urljoin
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Basak/1.0",
            "Accept": "text/html",
            "Accept-Encoding": "identity",
        })
        if _acici is not None:
            acilis = _acici(req, timeout=15)
        else:
            opener = urllib.request.build_opener(_GuvenliYonlendirme())
            acilis = opener.open(req, timeout=15)
        with acilis as resp:
            icerik_turu = resp.headers.get("Content-Type", "")
            if "text/html" not in icerik_turu:
                return {"error": "Desteklenen icerik tipi degil: %s"
                                 % icerik_turu}
            ham = resp.read(_MAX_HAM).decode("utf-8", errors="replace")

        adaylar = _OG_RE.findall(ham) + _IMG_RE.findall(ham)
        adaylar += _IMG_DATA_RE.findall(ham)
        adaylar += [_srcset_ilk(s) for s in _SRCSET_RE.findall(ham)]
        gorseller = []
        for aday in adaylar:
            aday = (aday or "").strip()
            if not aday or aday.startswith("data:"):
                continue
            mutlak = urljoin(url, aday).split("#")[0]
            k = urlparse(mutlak)
            if k.scheme not in ("http", "https") or not k.hostname:
                continue
            yol = k.path.lower().split("?")[0]
            if not yol.endswith(_GORSEL_UZANTI):
                continue
            if any(kelime in yol for kelime in _GORSEL_ATIK_KELIME):
                continue
            if mutlak not in gorseller:
                gorseller.append(mutlak)
            if len(gorseller) >= 10:
                break
        if not gorseller:
            return {"error": "Sayfada urun gorseli bulunamadi"}
        return {"result": json.dumps(gorseller, ensure_ascii=False)}
    except urllib.error.HTTPError as e:
        return {"error": "HTTP hatasi %d: %s" % (e.code, url)}
    except urllib.error.URLError as e:
        return {"error": "Baglanti hatasi: %s" % str(e.reason)}
    except Exception as e:
        logger.error("Gorsel toplama hatasi: %s", e)
        return {"error": "Gorseller alinamadi: %s" % str(e)}
