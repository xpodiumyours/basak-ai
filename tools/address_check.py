"""Canli web adresi kontrolu — mevcut SSRF savunmasini yeniden kullanir."""

import time
import urllib.error
import urllib.request

from tools.web_search import _GuvenliYonlendirme, _guvenli_adres


def _sonuc(kod, baslangic, son_url):
    ms = int((time.perf_counter() - baslangic) * 1000)
    return {"result": "HTTP %d | %d ms | %s" % (kod, ms, son_url)}


def adres_kontrol(url):
    """HEAD ile durum kodu/sure/son URL olcer; desteklenmezse kisa GET."""
    if not url or not str(url).strip():
        return {"error": "URL bos olamaz"}
    url = str(url).strip()
    engel = _guvenli_adres(url)
    if engel:
        return {"error": engel}

    opener = urllib.request.build_opener(_GuvenliYonlendirme())
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Basak/1.0",
        "Accept-Encoding": "identity",
    }
    baslangic = time.perf_counter()

    try:
        req = urllib.request.Request(url, headers=headers, method="HEAD")
        with opener.open(req, timeout=15) as resp:
            return _sonuc(resp.getcode(), baslangic, resp.geturl())
    except urllib.error.HTTPError as e:
        if e.code not in (405, 501):
            if 300 <= e.code < 400:
                return {"error": "Yonlendirme guvenle takip edilemedi: HTTP %d" % e.code}
            return _sonuc(e.code, baslangic, e.geturl())
    except urllib.error.URLError as e:
        return {"error": "Baglanti hatasi: %s" % str(e.reason)[:80]}
    except Exception as e:
        return {"error": "Adres kontrol edilemedi: %s" % str(e)[:80]}

    # Sunucu HEAD desteklemiyorsa govdeyi tuketmeden Range GET dene.
    try:
        get_headers = dict(headers)
        get_headers["Range"] = "bytes=0-0"
        req = urllib.request.Request(url, headers=get_headers, method="GET")
        with opener.open(req, timeout=15) as resp:
            return _sonuc(resp.getcode(), baslangic, resp.geturl())
    except urllib.error.HTTPError as e:
        if 300 <= e.code < 400:
            return {"error": "Yonlendirme guvenle takip edilemedi: HTTP %d" % e.code}
        return _sonuc(e.code, baslangic, e.geturl())
    except urllib.error.URLError as e:
        return {"error": "Baglanti hatasi: %s" % str(e.reason)[:80]}
    except Exception as e:
        return {"error": "Adres kontrol edilemedi: %s" % str(e)[:80]}
