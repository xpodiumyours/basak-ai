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
import threading
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from urllib.parse import unquote, urlparse

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


# ── Arama hatti dayanikliligi (2026-10-01, olculdu) ──────────────────
# Kok neden: ddgs motorlari tek turda paralel kosar ve
# wait(..., FIRST_EXCEPTION) ile erken doner; bir motor hata verince
# o turdaki sonuclar toplanmadan DDGSException("No results found.")
# yukseltilebiliyor. Ayrica "auto" wikipedia/grokipedia'yi one alir;
# ikisi de yalniz typeahead/opensearch dondurdugu icin genel sorguda
# 0 sonuc uretir ve calisan motorlardan is parcacigi calar.
# Olcum (2026-10-01, "Vestel iletisim telefon", tek motor): brave 429,
# duckduckgo 202, google 429, mojeek 403; startpage/grokipedia/wikipedia
# 200 ama 0 sonuc; sonuc yalniz yahoo'dan geldi. Ayni sorgu "auto" ile
# 6 turun 1'inde tamamen bos dondu.
# Cozum: tur tekrari (motorlar her turda yeniden karilir) + ilk tur
# sonrasi yalniz gercek arama motorlarina daraltma + gercek sebebi
# (HTTP kodu) hataya tasima. Kelime/niyet kurali YOK.
_ARAMA_DENEMESI = 3
_ARAMA_BEKLEME = 0.4       # denemeler arasi taban bekleme (saniye)
_ARAMA_ZAMAN_ASIMI = 5     # tek deneme zaman asimi (eskiden her yerde 5'ti)
_ARAMA_SEBEP_SAYISI = 6    # hata metnine yazilan en fazla motor sebebi

# Kategori basina gercek arama motorlari. wikipedia/grokipedia bilerek
# yok: genel sorguda sonuc uretmezler (typeahead/opensearch).
_GERCEK_MOTORLAR = {
    "text": ("yahoo", "duckduckgo", "brave", "google", "mojeek",
             "startpage"),
    "news": ("yahoo", "bing", "duckduckgo"),
    "images": ("bing", "duckduckgo"),
    "books": ("annasarchive",),
}

# Motor sebebi yalniz alt katman gunlugunde gorunur (ddgs hatayi yutar).
_MOTOR_YANIT_RE = re.compile(r"response:\s+(\S+)\s+(\d{3})")
_MOTOR_HATA_RE = re.compile(r"Error in engine (\w+)")
_ARAMA_GUNLUK_ADLARI = ("primp", "ddgs", "ddgs.ddgs")


class _MotorGunlugu(logging.Handler):
    """Arama suresince motorlarin gercek sebebini toplar (en iyi caba).

    ddgs motorlari HTTP hatasini yutup yalnizca "No results found"
    yukseltebilir; gercek sebep (HTTP 429/403/202) alt katman
    gunlugunde kalir. Burada toplanip hata metnine tasinir. Gunluk
    bicimi degisirse liste bos kalir, arama etkilenmez.
    """

    def __init__(self):
        super().__init__(level=logging.INFO)
        self.sebepler = []
        self._kilit = threading.Lock()

    def emit(self, kayit):
        try:
            metin = kayit.getMessage() or ""
        except Exception:
            return
        yanit = _MOTOR_YANIT_RE.search(metin)
        if yanit:
            try:
                ad = urlparse(yanit.group(1)).hostname or yanit.group(1)
            except ValueError:
                ad = yanit.group(1)
            self._ekle("%s HTTP %s" % (ad, yanit.group(2)))
            return
        hata = _MOTOR_HATA_RE.search(metin)
        if hata:
            self._ekle("%s hata verdi" % hata.group(1))

    def _ekle(self, metin):
        with self._kilit:
            if metin not in self.sebepler:
                self.sebepler.append(metin)


def _arama_hatasi(denenen, son_sebep, sebepler):
    """Kullaniciya donuk tek satir arama hatasi uretir.

    Motor sebepleri varsa onlar yazilir; yoksa son istisna metni.
    "No results found." tek basina anlamsiz oldugu icin yalniz sebep
    bulunamazsa kullanilir.
    """
    if sebepler:
        ayrinti = "; ".join(sebepler[:_ARAMA_SEBEP_SAYISI])
    else:
        ayrinti = str(son_sebep) if son_sebep else "sonuc donmedi"
    return ("Arama yapilamadi: %d denemede sonuc alinamadi (%s)"
            % (denenen, ayrinti))


def _arama_kos(kategori, cagri):
    """ddgs aramasini gerekirse tekrarlayarak kosar.

    cagri(ddgs, backend) -> sonuc listesi. Donus: (sonuclar, hata).
    Sonuclar bos olsa da cagri istisnasiz tamamlandiysa hata None'dur;
    bu "gercekten sonuc yok" demektir. Istisna ile biten turlarda ise
    kullaniciya donuk tek satirlik hata dondurulur.
    """
    try:
        from ddgs import DDGS
    except ImportError:
        return [], "ddgs paketi yuklu degil"

    gunluk = _MotorGunlugu()
    gunlukler = [logging.getLogger(ad) for ad in _ARAMA_GUNLUK_ADLARI]
    onceki = [(lg, lg.level) for lg in gunlukler]
    for lg in gunlukler:
        lg.setLevel(logging.INFO)
        lg.addHandler(gunluk)

    son_sebep = None
    temiz_bos = False
    denenen = 0
    try:
        for deneme in range(_ARAMA_DENEMESI):
            if deneme:
                time.sleep(_ARAMA_BEKLEME * deneme)
            denenen = deneme + 1
            arka = "auto" if deneme == 0 else ",".join(
                _GERCEK_MOTORLAR.get(kategori, ()))
            try:
                with DDGS(timeout=_ARAMA_ZAMAN_ASIMI) as ddgs:
                    sonuc = list(cagri(ddgs, arka) or [])
            except Exception as istisna:      # ddgs tek hata turu yukseltir
                son_sebep = istisna
                continue
            if sonuc:
                return sonuc, None
            temiz_bos = True
            # Acik motor listesi bos donduyse tekrar denemek gereksizdir.
            if deneme:
                break
    finally:
        for lg, seviye in onceki:
            lg.removeHandler(gunluk)
            lg.setLevel(seviye)

    if temiz_bos:
        return [], None
    return [], _arama_hatasi(denenen, son_sebep, gunluk.sebepler)


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
    2026-10-01: arama _arama_kos uzerinden kosar (tekrar + sebep).
    """
    results, hata = _arama_kos(
        "text",
        lambda ddgs, arka: ddgs.text(query, region="tr-tr", backend=arka,
                                     max_results=_adet_sinirla(adet)))
    if hata:
        logger.error("Web arama hatasi: %s", hata)
        return {"error": hata}
    if not results:
        return {"result": "Sonuc bulunamadi"}

    parcalar = []
    for r in results:
        parcalar.append(BICIM % (
            (r.get("title") or "").strip(),
            (r.get("href") or "").strip(),
            (r.get("body") or "").strip()))
    return {"result": AYIRAC.join(parcalar)}


def haber_ara(query: str, adet: int = 10) -> dict:
    """Haber arar; baslik + adres + tarih + metin doner.

    Tarih yoksa "tarihsiz" yazar, uydurulmaz.
    """
    if not query or not str(query).strip():
        return {"error": "Arama sorgusu boş olamaz"}
    results, hata = _arama_kos(
        "news",
        lambda ddgs, arka: ddgs.news(str(query).strip(), region="tr-tr",
                                     backend=arka,
                                     max_results=_adet_sinirla(adet, 10)))
    if hata:
        logger.error("Haber arama hatasi: %s", hata)
        return {"error": hata}
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
    results, hata = _arama_kos(
        "text",
        lambda ddgs, arka: ddgs.text(str(query).strip(), region="tr-tr",
                                     backend=arka, timelimit=sinir,
                                     max_results=_adet_sinirla(adet, 10)))
    if hata:
        logger.error("Zamanli arama hatasi: %s", hata)
        return {"error": hata}
    if not results:
        return {"result": "Sonuc bulunamadi"}
    parcalar = []
    for r in results:
        parcalar.append(BICIM % (
            (r.get("title") or "").strip(),
            (r.get("href") or "").strip(),
            (r.get("body") or "").strip()))
    return {"result": AYIRAC.join(parcalar)}


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
    results, hata = _arama_kos(
        "images",
        lambda ddgs, arka: ddgs.images(str(query).strip(), region="tr-tr",
                                       backend=arka,
                                       max_results=_adet_sinirla(adet, 10)))
    if hata:
        logger.error("Gorsel arama hatasi: %s", hata)
        return {"error": hata}
    adresler = []
    for r in results:
        aday = (r.get("image") or "").strip()
        if aday and aday not in adresler:
            adresler.append(aday)
    if not adresler:
        return {"error": "Gorsel bulunamadi"}
    return {"result": json.dumps(adresler, ensure_ascii=False)}


def kitap_ara(query: str, adet: int = 10) -> dict:
    """Kitap/katalog/brosur arar; baslik + adres + metin doner."""
    if not query or not str(query).strip():
        return {"error": "Arama sorgusu boş olamaz"}
    results, hata = _arama_kos(
        "books",
        lambda ddgs, arka: ddgs.books(str(query).strip(), backend=arka,
                                      max_results=_adet_sinirla(adet, 10)))
    if hata:
        logger.error("Kitap arama hatasi: %s", hata)
        return {"error": hata}
    if not results:
        return {"result": "Kitap bulunamadi"}
    parcalar = []
    for r in results:
        parcalar.append(BICIM % (
            (r.get("title") or "").strip(),
            (r.get("url") or r.get("href") or "").strip(),
            (r.get("body") or r.get("publisher") or "").strip()))
    return {"result": AYIRAC.join(parcalar)}


def derin_oku(url: str, baslangic=0, uzunluk=None) -> dict:
    """Uzun sayfayi cursor ile okur; tek tool sonucu baglami sisirmez."""
    return _sayfa_oku_genis(
        url, _MAX_DERIN, baslangic=baslangic, uzunluk=uzunluk)


# E-2: Sayfa okuma araci — yalnizca GET, 200000 karakter siniri
_MAX_SAYFA = 200000
# Derin okuma tavani (derin_oku): uzun sayfa/katalog metinleri icin.
_MAX_DERIN = 500000
_MAX_HAM = 50 * 1024 * 1024  # Ham HTML ust siniri (50 MB)
_SITEMAP_MAX_HAM = 2 * 1024 * 1024
_SITEMAP_MAX_DOSYA = 12
_SITEMAP_MAX_URL = 10000
_SITEMAP_CACHE_SN = 600
_SITEMAP_CACHE = {}
_SITEMAP_KILIT = threading.Lock()
_SITEMAP_HOST_KILIT = {}

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




def _xml_loclar(ham):
    """Sitemap XML'den loc adreslerini ve kok turunu okur."""
    try:
        kok = ET.fromstring(ham)
    except ET.ParseError:
        return "", []
    tur = kok.tag.rsplit("}", 1)[-1].lower()
    loclar = []
    for eleman in kok.iter():
        if eleman.tag.rsplit("}", 1)[-1].lower() != "loc":
            continue
        deger = (eleman.text or "").strip()
        if deger:
            loclar.append(deger)
    return tur, loclar


def _sitemap_cek(url):
    engel = _guvenli_adres(url)
    if engel:
        return None
    try:
        opener = urllib.request.build_opener(_GuvenliYonlendirme())
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Basak/1.0",
            "Accept": "application/xml,text/xml,text/plain,*/*",
            "Accept-Encoding": "identity",
        })
        with opener.open(req, timeout=12) as resp:
            ctype = (resp.headers.get("Content-Type", "") or "").lower()
            if not any(x in ctype for x in ("xml", "text/plain", "octet-stream")):
                return None
            return resp.read(_SITEMAP_MAX_HAM)
    except Exception:
        return None


def _sitemap_url_listesi(host):
    """Bir hostun sitemap URL envanterini kısa süreli kamu verisi olarak cache'ler.

    Aynı hostu paralel ürün kartları aynı anda isterse tek ağ fetch'i yapılır.
    Farklı hostlar birbirini bloke etmez.
    """
    host = (host or "").strip().lower().lstrip("www.")
    if not host or " " in host or "." not in host:
        return []

    with _SITEMAP_KILIT:
        host_kilit = _SITEMAP_HOST_KILIT.setdefault(host, threading.Lock())

    with host_kilit:
        simdi = time.time()
        with _SITEMAP_KILIT:
            kayit = _SITEMAP_CACHE.get(host)
            if kayit and simdi - kayit["zaman"] < _SITEMAP_CACHE_SN:
                return list(kayit["url"])

        ana = "https://%s/sitemap.xml" % host
        ham = _sitemap_cek(ana)
        if not ham:
            return []
        tur, loclar = _xml_loclar(ham)
        urller = []
        if tur == "urlset":
            urller = loclar[:_SITEMAP_MAX_URL]
        elif tur == "sitemapindex":
            # Önce ürün/katalog sitemapleri; sonra diğerleri. Ağ yükü sınırlı.
            sirali = sorted(
                loclar,
                key=lambda u: (
                    0 if any(k in u.lower()
                             for k in ("product", "urun", "shop")) else 1,
                    u))
            for alt in sirali[:_SITEMAP_MAX_DOSYA]:
                alt_ham = _sitemap_cek(alt)
                if not alt_ham:
                    continue
                alt_tur, alt_loclar = _xml_loclar(alt_ham)
                if alt_tur != "urlset":
                    continue
                for u in alt_loclar:
                    if u not in urller:
                        urller.append(u)
                        if len(urller) >= _SITEMAP_MAX_URL:
                            break
                if len(urller) >= _SITEMAP_MAX_URL:
                    break

        with _SITEMAP_KILIT:
            # Cache yalnız kamuya açık URL envanteridir; kullanıcı/fatura verisi yok.
            if len(_SITEMAP_CACHE) >= 20:
                en_eski = min(_SITEMAP_CACHE,
                              key=lambda h: _SITEMAP_CACHE[h]["zaman"])
                _SITEMAP_CACHE.pop(en_eski, None)
            _SITEMAP_CACHE[host] = {"zaman": simdi, "url": list(urller)}
        return urller


def site_haritasi_ara(site, terim, adet=8):
    """Doğrulanmış firma sitesinin sitemap'inde tam ürün kodu/GTIN ara.

    Arama motoru indekslemesine bağlı değildir. İç yardımcıdır; yeni ajan
    aracı eklemez. Sonuç yalnız URL adaylarıdır, ürün doğrulaması sayfa
    içeriğinde ayrıca yapılır.
    """
    host = str(site or "").strip()
    if "://" in host:
        host = (urlparse(host).hostname or "")
    host = host.lower().lstrip("www.")
    hedef = re.sub(r"[^a-z0-9]", "", str(terim or "").lower())
    if not host or not hedef:
        return {"result": json.dumps([], ensure_ascii=False)}
    eslesen = []
    for u in _sitemap_url_listesi(host):
        yol = re.sub(r"[^a-z0-9]", "", unquote(str(u)).lower())
        if hedef in yol:
            eslesen.append(u)
            if len(eslesen) >= max(1, min(20, int(adet or 8))):
                break
    return {"result": json.dumps(eslesen, ensure_ascii=False)}


def sayfa_oku(url: str, baslangic=0, uzunluk=None) -> dict:
    """Bir URL'yi cursor ile okur; tam metni tek tool sonucuna yigmaz."""
    return _sayfa_oku_genis(
        url, _MAX_SAYFA, baslangic=baslangic, uzunluk=uzunluk)


def _sayfa_oku_genis(
        url: str, tavan: int, baslangic=0, uzunluk=None) -> dict:
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
            son_url = resp.geturl()
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

        if not temiz:
            return {"error": "Sayfa icerigi bos"}

        try:
            baslangic = max(0, int(baslangic or 0))
        except (TypeError, ValueError):
            return {"error": "baslangic sayi olmali"}

        kaynak_toplam = len(temiz)
        erisilebilir = min(kaynak_toplam, int(tavan))

        # Geriye uyumluluk: tools/katalog.py gibi Python ic tuketiciler
        # sayfa_oku(url) cagrısından duz metin bekler. Agent dispatcher ise
        # uzunluk parametresini ACIKCA verir ve cursor/meta moduna girer.
        if uzunluk is None and baslangic == 0:
            duz = temiz[:erisilebilir]
            if kaynak_toplam > tavan:
                duz += "\n...(ilk %d karakter)" % tavan
            return {"result": duz}

        try:
            uzunluk = int(uzunluk or 30000)
        except (TypeError, ValueError):
            return {"error": "uzunluk sayi olmali"}
        uzunluk = max(1, min(50000, uzunluk))

        if baslangic >= erisilebilir and erisilebilir > 0:
            return {
                "error": "baslangic erisilebilir metnin disinda",
                "meta": {
                    "url": son_url,
                    "kaynak_toplam": kaynak_toplam,
                    "erisilebilir": erisilebilir,
                    "kaynak_tavani_asildi": kaynak_toplam > tavan,
                },
            }

        son = min(erisilebilir, baslangic + uzunluk)
        parca = temiz[baslangic:son]
        meta = {
            "url": son_url,
            "baslangic": baslangic,
            "son": son,
            "kaynak_toplam": kaynak_toplam,
            "erisilebilir": erisilebilir,
            "devam": son < erisilebilir,
            "sonraki_baslangic": son if son < erisilebilir else None,
            "kaynak_tavani_asildi": kaynak_toplam > tavan,
        }
        return {"result": parca, "meta": meta}

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


# ── Ürün sayfası kanıt okuyucusu ──────────────────────────────────
_JSONLD_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL)


def _jsonld_dugumleri(deger):
    if isinstance(deger, list):
        for x in deger:
            yield from _jsonld_dugumleri(x)
        return
    if not isinstance(deger, dict):
        return
    yield deger
    graph = deger.get("@graph")
    if isinstance(graph, (list, dict)):
        yield from _jsonld_dugumleri(graph)
    # ProductGroup siteleri varyantlari hasVariant icinde tutabilir.
    # Yalniz urun-varyant agacini geziyoruz; Offer vb. tum JSON-LD
    # nesnelerini kontrolsuzce taramiyoruz.
    varyantlar = deger.get("hasVariant")
    if isinstance(varyantlar, (list, dict)):
        yield from _jsonld_dugumleri(varyantlar)


def _jsonld_kurumlar(ham):
    """Schema.org Organization/Corporation/Brand/WebSite kimliklerini çıkarır."""
    import html as _html
    sonuc = []
    izinli = {"organization", "corporation", "localbusiness", "brand", "website"}
    for parca in _JSONLD_RE.findall(ham or ""):
        try:
            veri = json.loads(_html.unescape(parca).strip())
        except (TypeError, ValueError):
            continue
        for dugum in _jsonld_dugumleri(veri):
            tur = dugum.get("@type")
            turler = tur if isinstance(tur, list) else [tur]
            if not any(str(t or "").lower() in izinli for t in turler):
                continue
            ad = str(dugum.get("name") or "").strip()
            url = str(dugum.get("url") or dugum.get("@id") or "").strip()
            same_as = dugum.get("sameAs")
            same_as = same_as if isinstance(same_as, list) else [same_as]
            kayit = {
                "type": next((str(t) for t in turler if t), ""),
                "name": ad,
                "url": url,
                "sameAs": [str(x) for x in same_as if x],
            }
            if (ad or url) and kayit not in sonuc:
                sonuc.append(kayit)
            if len(sonuc) >= 20:
                return sonuc
    return sonuc


def _jsonld_urun(ham):
    """Schema.org Product/ProductGroup bloklarini dar JSON'a cevirir."""
    import html as _html
    urunler = []
    for parca in _JSONLD_RE.findall(ham or ""):
        try:
            veri = json.loads(_html.unescape(parca).strip())
        except (TypeError, ValueError):
            continue
        for dugum in _jsonld_dugumleri(veri):
            tur = dugum.get("@type")
            turler = tur if isinstance(tur, list) else [tur]
            if not any(str(t or "").lower() in ("product", "productgroup")
                       for t in turler):
                continue
            brand = dugum.get("brand")
            if isinstance(brand, dict):
                brand = brand.get("name") or brand.get("@id") or ""
            image = dugum.get("image")
            if isinstance(image, dict):
                image = image.get("url") or image.get("contentUrl") or ""
            gtinler = []
            for anahtar in ("gtin", "gtin8", "gtin12", "gtin13", "gtin14"):
                deger = dugum.get(anahtar)
                if isinstance(deger, list):
                    gtinler.extend(str(x) for x in deger if x)
                elif deger:
                    gtinler.append(str(deger))
            urunler.append({
                "name": dugum.get("name") or "",
                "brand": brand or "",
                "sku": dugum.get("sku") or "",
                "mpn": dugum.get("mpn") or "",
                "gtin": gtinler,
                "color": dugum.get("color") or "",
                "size": dugum.get("size") or "",
                "productGroupID": dugum.get("productGroupID") or
                                  dugum.get("inProductGroupWithID") or "",
                "image": image or "",
                "url": dugum.get("url") or "",
            })
            if len(urunler) >= 30:
                return urunler
    return urunler


def _ham_sayfa_getir(url, _acici=None):
    """Korumali tek HTTP GET → (ham, son_url, None) ya da (None, None, hata).

    SSRF/yönlendirme savunması tek yerde kalsın diye sayfa okuyan
    okuyucular bu yardımcıyı paylaşır; her okuyucu kendi savunmasını
    yazmaz. `_acici` yalnız testler içindir.
    """
    if not url or not str(url).strip():
        return None, None, {"error": "URL bos olamaz"}
    url = str(url).strip()
    engel = _guvenli_adres(url)
    if engel:
        return None, None, {"error": engel}
    try:
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
            content_type = resp.headers.get("Content-Type", "")
            son_url = resp.geturl() if hasattr(resp, "geturl") else url
            if "text/html" not in content_type:
                return None, None, {
                    "error": "Desteklenen icerik tipi degil: %s" % content_type}
            ham = resp.read(_MAX_HAM).decode("utf-8", errors="replace")
        return ham, son_url, None
    except urllib.error.HTTPError as e:
        return None, None, {"error": "HTTP hatasi %d: %s" % (e.code, url)}
    except urllib.error.URLError as e:
        return None, None, {"error": "Baglanti hatasi: %s" % str(e.reason)}
    except Exception as e:
        logger.warning("Sayfa okuma hatasi: %s", e)
        return None, None, {"error": "Sayfa okunamadi: %s" % str(e)}


def urun_sayfasi_oku(url: str, _acici=None) -> dict:
    """Bir urun aday sayfasini tek HTTP GET ile kanit paketine cevirir.

    Donus: metin + Schema.org Product/ProductGroup + urun gorselleri.
    SSRF ve yonlendirme savunmasi sayfa_oku ile aynidir.
    """
    ham, son_url, hata = _ham_sayfa_getir(url, _acici)
    if hata:
        return hata
    try:
        import html as html_mod
        from urllib.parse import urljoin

        urunler = _jsonld_urun(ham)
        kurumlar = _jsonld_kurumlar(ham)
        temiz = re.sub(
            r'<(script|style|noscript)[^>]*>.*?</\1>',
            '', ham, flags=re.DOTALL | re.IGNORECASE)
        temiz = re.sub(r'<!--.*?-->', '', temiz, flags=re.DOTALL)
        temiz = re.sub(r'<[^>]+>', ' ', temiz)
        temiz = re.sub(r'\s+', ' ', html_mod.unescape(temiz)).strip()

        adaylar = _OG_RE.findall(ham) + _IMG_RE.findall(ham)
        adaylar += _IMG_DATA_RE.findall(ham)
        adaylar += [_srcset_ilk(s) for s in _SRCSET_RE.findall(ham)]
        for u in urunler:
            img = u.get("image")
            if isinstance(img, list):
                adaylar.extend(img)
            elif img:
                adaylar.append(img)

        gorseller = []
        for aday in adaylar:
            aday = str(aday or "").strip()
            if not aday or aday.startswith("data:"):
                continue
            mutlak = urljoin(son_url, aday).split("#")[0]
            k = urlparse(mutlak)
            if k.scheme not in ("http", "https") or not k.hostname:
                continue
            yol = k.path.lower().split("?")[0]
            if any(kelime in yol for kelime in _GORSEL_ATIK_KELIME):
                continue
            if mutlak not in gorseller:
                gorseller.append(mutlak)
            if len(gorseller) >= 10:
                break

        return {"result": json.dumps({
            "url": son_url,
            "metin": temiz[:50000],
            "urunler": urunler,
            "kurumlar": kurumlar,
            "gorseller": gorseller,
        }, ensure_ascii=False)}
    except urllib.error.HTTPError as e:
        return {"error": "HTTP hatasi %d: %s" % (e.code, url)}
    except urllib.error.URLError as e:
        return {"error": "Baglanti hatasi: %s" % str(e.reason)}
    except Exception as e:
        logger.warning("Urun sayfasi okuma hatasi: %s", e)
        return {"error": "Urun sayfasi okunamadi: %s" % str(e)}


# ── Şirket/kurum sayfası gerçekleri ───────────────────────────────
# urun_sayfasi_oku ile aynı korumalı hattı paylaşır; farkı: Product
# yerine Organization/LocalBusiness alanları (ad, resmî ad, adres,
# telefon, e-posta, vergi no) olgu olarak çıkarılır. Değerler sayfada
# yazdığı gibi kalır; hiçbir alan türetilmez, tamamlanmaz ya da tahmin
# edilmez. Ölçüm (2026-10-01): modern siteler adresi yalnız JSON-LD
# PostalAddress içinde verir; yalnız düz metne bakan çıkarım bunu
# tamamen kaçırıyordu.

_KURUM_TURLERI = (
    "organization", "corporation", "localbusiness", "store", "onlinestore",
    "professionalservice", "foodestablishment", "restaurant", "hairsalon",
    "medicalorganization", "educationalorganization",
)
# Not: "website" BİLEREK yok — WebSite düğümü adres/ad/telefon taşımaz,
# yalnız site adı taşır; gerçek kurum bilgisini gölgeler (ölçüldü).
# Blok etiketleri satır sonu, satir içi etiketler boşluk olur: adres
# satırları tek dev satıra yapışmasın (eski akışta yapışıyordu).
_BLOK_ETIKET_RE = re.compile(
    r"</?(?:br|p|div|li|tr|td|th|h[1-6]|section|article|header|footer|"
    r"address|ul|ol|table|form|label|dl|dt|dd)\b[^>]*>",
    re.IGNORECASE)


def _duz_metin(deger):
    """str|dict (name/@id/value) alanı düz metne çevirir."""
    if isinstance(deger, dict):
        deger = (deger.get("name") or deger.get("@id")
                 or deger.get("value"))
    return str(deger or "").strip()


def _metin_listesi(deger):
    """str|liste alanı tekilleştirilmiş düz metin listesine çevirir."""
    deger = deger if isinstance(deger, list) else [deger]
    sonuc = []
    for x in deger:
        x = _duz_metin(x)
        if x and x not in sonuc:
            sonuc.append(x)
    return sonuc


def _adres_alani(deger):
    """Schema.org PostalAddress → {alan: değer} + okunur tek satır."""
    if isinstance(deger, list):
        deger = next((x for x in deger if isinstance(x, (dict, str))), None)
    if isinstance(deger, str):
        return {}, " ".join(deger.split())
    if not isinstance(deger, dict):
        return {}, ""
    alanlar = {
        "sokak": _duz_metin(deger.get("streetAddress")),
        "yerlesim": _duz_metin(deger.get("addressLocality")),
        "bolge": _duz_metin(deger.get("addressRegion")),
        "posta_kodu": _duz_metin(deger.get("postalCode")),
        "ulke": _duz_metin(deger.get("addressCountry")),
    }
    return alanlar, ", ".join(x for x in alanlar.values() if x)


def _kurum_gercekleri(ham):
    """Organization/LocalBusiness JSON-LD alanlarını olgu olarak çıkarır."""
    import html as _html
    sonuc = []
    for parca in _JSONLD_RE.findall(ham or ""):
        try:
            veri = json.loads(_html.unescape(parca).strip())
        except (TypeError, ValueError):
            continue
        for dugum in _jsonld_dugumleri(veri):
            tur = dugum.get("@type")
            turler = tur if isinstance(tur, list) else [tur]
            if not any(str(t or "").lower() in _KURUM_TURLERI for t in turler):
                continue
            adres, adres_metni = _adres_alani(dugum.get("address"))
            kayit = {
                "tur": next((str(t) for t in turler if t), ""),
                "ad": _duz_metin(dugum.get("name")),
                "resmi_ad": _duz_metin(dugum.get("legalName")),
                "url": _duz_metin(dugum.get("url") or dugum.get("@id")),
                "telefonlar": _metin_listesi(dugum.get("telephone")),
                "epostalar": _metin_listesi(dugum.get("email")),
                "adres": adres,
                "adres_metni": adres_metni,
                "vergi_no": _duz_metin(dugum.get("vatID") or dugum.get("taxID")),
            }
            dolu = (kayit["ad"] or kayit["resmi_ad"] or kayit["url"]
                    or kayit["telefonlar"] or kayit["epostalar"]
                    or kayit["adres_metni"] or kayit["vergi_no"])
            if dolu and kayit not in sonuc:
                sonuc.append(kayit)
            if len(sonuc) >= 20:
                return sonuc
    return sonuc


def kurum_sayfasi_oku(url: str, _acici=None) -> dict:
    """Şirket sayfasını TEK kez indirir; metin + schema.org gerçekleri.

    Dönüş JSON: {"url", "metin", "gercekler"}. `gercekler` sayfadaki
    Organization/LocalBusiness bloklarının olgularıdır; eksik alan boş
    kalır. `metin` satır yapısını korur (blok etiketleri satır sonu olur).
    SSRF ve yönlendirme savunması sayfa_oku ile aynıdır.
    """
    ham, son_url, hata = _ham_sayfa_getir(url, _acici)
    if hata:
        return hata
    try:
        import html as html_mod

        temiz = re.sub(
            r'<(script|style|noscript)[^>]*>.*?</\1>',
            '', ham, flags=re.DOTALL | re.IGNORECASE)
        temiz = re.sub(r'<(script|style|noscript)[^>]*>.*', '', temiz,
                       flags=re.DOTALL | re.IGNORECASE)
        temiz = re.sub(r'<!--.*?-->', '', temiz, flags=re.DOTALL)
        temiz = _BLOK_ETIKET_RE.sub('\n', temiz)
        temiz = re.sub(r'<[^>]+>', ' ', temiz)
        temiz = html_mod.unescape(temiz)
        satirlar = [re.sub(r"[ \t\u00a0]+", " ", s).strip()
                    for s in temiz.splitlines()]
        metin = "\n".join(s for s in satirlar if s)
        return {"result": json.dumps({
            "url": son_url,
            "metin": metin[:_MAX_SAYFA],
            "gercekler": _kurum_gercekleri(ham),
        }, ensure_ascii=False)}
    except Exception as e:
        logger.warning("Kurum sayfasi okuma hatasi: %s", e)
        return {"error": "Kurum sayfasi okunamadi: %s" % str(e)}
