"""tests/test_url_kodlama.py — URL kodlama hataları (2026-10-01, P1.4 ölçümü).

Kök neden gecikme ölçümünde çıktı, tahminle bulunmadı:

1. **Çift kodlama.** `urllib.parse.quote()` varsayılan olarak `%` işaretini
   de kodlar. Zaten kodlanmış bir URL gelince ikinci kez kodlanıyordu:
   `/wiki/Ba%C5%9Fak` → `/wiki/Ba%25C5%259Fak` → **HTTP 404**.
   Gerçek ölçüm: `sayfa_oku("https://tr.wikipedia.org/wiki/Ba%C5%9Fak")`
   404 döndürüyordu, `.../çilek` çalışıyordu.

2. **Ham Türkçe karakter.** Yalnız PATH kodlanıyordu; QUERY ve NETLOC
   ham kalıyordu. Türkçe karakter içeren bir adresteki
   `UnicodeEncodeError` ("'ascii' codec can't encode character '\\xe7'")
   **tüm sayfa okumayı** hata verdiriyordu. Gerçek ölçüm:
   `sirket_ara("Trendyol")` aday sayfalardan birinde bu yüzden düşüyordu.

Sözleşme:
- Zaten kodlanmış karakterlere dokunulmaz (`%` güvenli).
- Ham Türkçe karakter yolda, sorguda ve alan adında kodlanır.
- **SSRF denetimi bozulmaz** — kodlama sonrası denetim aynı yerde çalışır.

Ağ yok: yalnız URL dönüşümü ve güvenlik engeli ölçülür.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import web_search as ws


@pytest.fixture
def yakalanan(monkeypatch):
    """Gerçek ağ yerine, Request'e giden son URL'i yakalar."""
    tutulan = {}

    class _Yalanci:
        def __init__(self, url, headers=None):
            tutulan["url"] = url
            raise _YalgiDurdur()

    monkeypatch.setattr(ws.urllib.request, "Request", _Yalanci)
    return tutulan


class _YalgiDurdur(Exception):
    """Ağa cikmadan once URL kaydedildi; simdi dur."""


def _yola_giden_url(url):
    """sayfa_oku'ya giren URL'i ağ olmadan cikar."""
    tutulan = {}
    gercek = ws.urllib.request.Request

    class _Yalanci:
        def __init__(self, u, headers=None):
            tutulan["url"] = u
            raise _YalgiDurdur()

    ws.urllib.request.Request = _Yalanci
    try:
        ws.sayfa_oku(url)
    except _YalgiDurdur:
        pass
    except Exception:
        pass
    finally:
        ws.urllib.request.Request = gercek
    return tutulan.get("url")


class TestCiftKodlamaYok:
    def test_kodlanmis_yol_bozulmaz(self):
        """Zaten kodlanmış %XX dokunulmaz (404 kok nedeni)."""
        giden = _yola_giden_url("https://tr.wikipedia.org/wiki/Ba%C5%9Fak")
        assert giden is not None, "ağa cikamadi"
        assert "%25" not in giden, "cift kodlama var: %s" % giden
        assert "Ba%C5%9Fak" in giden, giden

    def test_yuzde_isareti_ayni_kalir(self):
        giden = _yola_giden_url("https://example.com/a%20b")
        assert giden.endswith("/a%20b"), giden

    def test_yuzdesiz_url_de_ayni_kalir(self):
        giden = _yola_giden_url("https://example.com/normal")
        assert giden.endswith("/normal"), giden


class TestTurkceKodlanir:
    def test_yoldaki_turkce_karakter_kodlanir(self):
        giden = _yola_giden_url("https://tr.wikipedia.org/wiki/çilek")
        assert "ç" not in giden, "kodlanmadi: %s" % giden
        assert "%C3%A7" in giden, giden

    def test_sorgudaki_turkce_karakter_kodlanir(self):
        giden = _yola_giden_url("https://example.com/a?q=iletişim")
        assert giden is not None
        assert "ş" not in giden, "sorgu kodlanmadi: %s" % giden

    def test_sorgudaki_kodlanmis_deger_bozulmaz(self):
        giden = _yola_giden_url("https://example.com/a?k=%C3%A7")
        assert giden.endswith("?k=%C3%A7"), giden

    def test_unicode_hatasi_yok(self):
        """'ascii' codec hatasinin kaynagi giderilmis olmali."""
        giden = _yola_giden_url("https://tr.wikipedia.org/wiki/Türkçe")
        try:
            giden.encode("ascii")
        except UnicodeEncodeError as e:
            pytest.fail("yol hala ASCII disi: %s (%s)" % (giden, e))
        assert giden is not None


class TestGuvenlikAyakta:
    """Kodlama duzeltmesi SSRF denetimini zayiflatmamali."""

    def test_ice_adres_yine_engelli(self):
        r = ws.sayfa_oku("http://127.0.0.1/x")
        assert "Guvenlik engeli" in r.get("error", ""), r

    def test_kodlanmis_ice_adres_yine_engelli(self):
        """Kodlama sonrasi denetim ayni yerde calismali."""
        r = ws.sayfa_oku("http://127.0.0.1/%2Fx")
        assert "Guvenlik engeli" in r.get("error", ""), r

    def test_sayfa_bos_url_hata_verir(self):
        r = ws.sayfa_oku("")
        assert "error" in r


class TestOlcumDogrulugu:
    """Yol yardimcimiz gercekten test edilen kodu gosteriyor mu?"""

    def test_yardimci_sayfa_okunun_ayni_yolundan_gecer(self, monkeypatch):
        """`or True` yazan sahte bir dogrulama olmasin diye: yardimci
        gercekten sayfa_oku -> _sayfa_oku_genis zincirinden geciyor.
        Zincirin ikinci halkasi ulasilabilir degilse, kodlamanin
        kondugu yer degistiyse bu test kirmiziya doner."""
        gorulen = []
        gercek = ws._sayfa_oku_genis

        def izle(url, *a, **kw):
            gorulen.append(url)
            raise _YalgiDurdur()

        monkeypatch.setattr(ws, "_sayfa_oku_genis", izle)
        try:
            ws.sayfa_oku("https://tr.wikipedia.org/wiki/çilek")
        except _YalgiDurdur:
            pass
        assert gorulen == ["https://tr.wikipedia.org/wiki/çilek"], (
            "sayfa_oku _sayfa_oku_genis'i cagirmiyor — test yanlis yeri "
            "olcuyor olabilir: %s" % gorulen)

    def test_yardimci_somut_url_dondurur(self):
        giden = _yola_giden_url("https://tr.wikipedia.org/wiki/çilek")
        assert giden, "yardimci URL dondurmedi"
        assert giden.startswith("https://")