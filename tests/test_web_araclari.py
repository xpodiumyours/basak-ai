"""tests/test_web_araclari.py — Arama genislemesi guvencesi (2026-09-15).

Sozlesme (uc yer + davranis):
- 6 yeni arac semada, dispatcher'da, durum etiketinde bagli.
- Kelime tetikleyici YOK: secimi model yapar, kod yapmaz.
- Tarih uydurulmaz (tarihsiz yazar); aralik/site bicim disi red.
- derin_oku, sayfa_oku ile ayni SSRF hattindan gecer.
- Ag yok: ddgs ve opener sahtelenir.
"""

import io
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import calistir
from tools import web_search as ws
from tools.definitions import TANINMIS_TOOLLAR

YENILER = ("haber_ara", "zamanli_ara", "site_ara", "gorsel_ara",
           "kitap_ara", "derin_oku")


class SahteDDGS:
    """ddgs.DDGS taklidi; kwargs'lari yakalar, sabit kayit doner."""

    kayit = {}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def _al(self, ad, **kwargs):
        SahteDDGS.kayit[ad] = kwargs
        return SahteDDGS.kayit.get("_ver", [])

    def text(self, query, **kwargs):
        return self._al("text", query=query, **kwargs)

    def news(self, query, **kwargs):
        return self._al("news", query=query, **kwargs)

    def images(self, query, **kwargs):
        return self._al("images", query=query, **kwargs)

    def books(self, query, **kwargs):
        return self._al("books", query=query, **kwargs)


def _ddgs(monkeypatch, ver):
    import ddgs
    SahteDDGS.kayit = {"_ver": ver}
    monkeypatch.setattr(ddgs, "DDGS", SahteDDGS)


class TestUcYer:
    def test_alti_arac_bagli(self):
        from chat.tools import DURUM_METNI
        for ad in YENILER:
            assert ad in TANINMIS_TOOLLAR, ad
            assert ad in DURUM_METNI, ad

    def test_bos_girdi_yan_etkisiz(self):
        assert "error" in calistir("haber_ara", {"query": ""})
        assert "error" in calistir("zamanli_ara",
                                   {"query": "", "aralik": "hafta"})
        assert "error" in calistir("site_ara",
                                   {"site": "x.com", "sorgu": ""})
        assert "error" in calistir("gorsel_ara", {"query": ""})
        assert "error" in calistir("kitap_ara", {"query": ""})
        assert "error" in calistir("derin_oku", {"url": ""})


class TestAdet:
    def test_web_search_adet_gecer(self, monkeypatch):
        _ddgs(monkeypatch, [{"title": "a", "href": "u", "body": "m"}])
        r = ws.web_search("soru", adet=5)
        assert "result" in r
        assert SahteDDGS.kayit["text"]["max_results"] == 5

    def test_adet_tavani(self, monkeypatch):
        _ddgs(monkeypatch, [])
        ws.web_search("soru", adet=9999)
        assert SahteDDGS.kayit["text"]["max_results"] == 30
        ws.web_search("soru", adet="bozuk")
        assert SahteDDGS.kayit["text"]["max_results"] == 20


class TestHaber:
    def test_tarih_tasinir(self, monkeypatch):
        _ddgs(monkeypatch, [{"title": "T", "url": "U",
                             "date": "2026-09-01", "body": "B"}])
        r = ws.haber_ara("konu")
        assert "2026-09-01" in r["result"]

    def test_tarihsiz_uydurmaz(self, monkeypatch):
        _ddgs(monkeypatch, [{"title": "T", "url": "U", "body": "B"}])
        r = ws.haber_ara("konu")
        assert "tarihsiz" in r["result"]

    def test_bos_haber(self, monkeypatch):
        _ddgs(monkeypatch, [])
        assert "result" in ws.haber_ara("konu")


class TestZamanli:
    def test_aralik_haritasi(self, monkeypatch):
        _ddgs(monkeypatch, [])
        ws.zamanli_ara("konu", "gun")
        assert SahteDDGS.kayit["text"]["timelimit"] == "d"
        ws.zamanli_ara("konu", "ay")
        assert SahteDDGS.kayit["text"]["timelimit"] == "m"

    def test_bozuk_aralik_reddedilir(self, monkeypatch):
        _ddgs(monkeypatch, [{"title": "a"}])
        r = ws.zamanli_ara("konu", "yil")
        assert "error" in r and "gun" in r["error"]


class TestSite:
    def test_site_oneki(self, monkeypatch):
        _ddgs(monkeypatch, [])
        ws.site_ara("ornek.com", "urun")
        assert SahteDDGS.kayit["text"]["query"].startswith(
            "site:ornek.com ")

    def test_bozuk_site_reddedilir(self):
        assert "error" in ws.site_ara("bosluk var", "sorgu")
        assert "error" in ws.site_ara("noktasiz", "sorgu")


class TestGorselKitap:
    def test_gorsel_json_liste(self, monkeypatch):
        _ddgs(monkeypatch, [{"image": "http://a/x.jpg"},
                             {"image": "http://a/x.jpg"},
                             {"image": ""}])
        r = ws.gorsel_ara("urun")
        assert json.loads(r["result"]) == ["http://a/x.jpg"]

    def test_gorsel_yoksa_hata(self, monkeypatch):
        _ddgs(monkeypatch, [])
        assert "error" in ws.gorsel_ara("urun")

    def test_kitap_bicimi(self, monkeypatch):
        _ddgs(monkeypatch, [{"title": "K", "url": "U",
                             "publisher": "Y"}])
        r = ws.kitap_ara("katalog")
        assert "K" in r["result"] and "U" in r["result"]


class TestDerinOku:
    def test_ssrf_ayni_hat(self):
        # Ic ag derin okumada da kapali (sayfa_oku ile ayni kapi).
        r = ws.derin_oku("http://127.0.0.1/gizli")
        assert "error" in r and "Guvenlik" in r["error"]
        assert "error" in ws.derin_oku("ftp://x/y")

    def test_tavan_500bin(self, monkeypatch):
        govde = "x" * 600000

        class Yanit:
            headers = {"Content-Type": "text/plain"}

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self, n=-1):
                return govde.encode("utf-8")

            def geturl(self):
                return "http://ornek.com/uzun"

        class Acici:
            def __init__(self, *a, **k):
                pass

            def open(self, req, timeout=None):
                return Yanit()

        monkeypatch.setattr(urllib.request, "build_opener",
                            lambda *a, **k: Acici())
        monkeypatch.setattr(ws.socket, "getaddrinfo",
                            lambda h, p: [(2, 1, 6, "",
                                           ("93.184.216.34", 0))])
        # Dogrudan Python tuketicisi eski duz-result sozlesmesini korur.
        legacy = ws.derin_oku("http://ornek.com/uzun")
        assert "result" in legacy, legacy
        assert legacy["result"].startswith("x" * 100)
        assert "500000" in legacy["result"]

        # Agent dispatcher explicit uzunluk verdiginde cursor/meta modudur.
        r = ws.derin_oku("http://ornek.com/uzun", uzunluk=40000)
        assert "result" in r and "meta" in r, r
        assert len(r["result"]) <= 50000
        assert r["meta"]["kaynak_toplam"] == 600000
        assert r["meta"]["erisilebilir"] == 500000
        assert r["meta"]["kaynak_tavani_asildi"] is True
        assert r["meta"]["sonraki_baslangic"] is not None

        r2 = ws.derin_oku(
            "http://ornek.com/uzun",
            baslangic=r["meta"]["sonraki_baslangic"],
            uzunluk=40000,
        )
        assert r2["meta"]["baslangic"] == r["meta"]["sonraki_baslangic"]

    def test_calistir_hatti(self, monkeypatch):
        _ddgs(monkeypatch, [{"title": "a", "href": "u", "body": "m"}])
        for ad, args in (
                ("haber_ara", {"query": "k"}),
                ("zamanli_ara", {"query": "k", "aralik": "hafta"}),
                ("site_ara", {"site": "x.com", "sorgu": "k"}),
                ("gorsel_ara", {"query": "k"}),
                ("kitap_ara", {"query": "k"})):
            assert isinstance(calistir(ad, args), dict)
        _ddgs(monkeypatch, [])
        assert isinstance(
            calistir("web_search", {"query": "k", "adet": 3}), dict)


def test_urun_sayfasi_schema_product_tek_get(monkeypatch):
    from tools import web_search as ws
    monkeypatch.setattr(ws, "_engelli_ip_nedeni", lambda h: None)

    class Yanit:
        headers = {"Content-Type": "text/html"}
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def geturl(self): return "https://marka.example/urun/x"
        def read(self, n=-1):
            return b"""<html><head>
            <meta property="og:image" content="/x.jpg">
            <script type="application/ld+json">
            {"@context":"https://schema.org","@type":"Product",
             "name":"Urun X","brand":{"@type":"Brand","name":"Marka"},
             "sku":"SKU-X","gtin13":"8680508918124","color":"Siyah","size":"M",
             "image":"https://marka.example/i/x2.jpg"}
            </script></head><body>Marka SKU-X 8680508918124</body></html>"""

    r = ws.urun_sayfasi_oku(
        "https://marka.example/urun/x",
        _acici=lambda *a, **k: Yanit())
    assert "result" in r, r
    veri = json.loads(r["result"])
    assert veri["urunler"][0]["sku"] == "SKU-X"
    assert "8680508918124" in veri["urunler"][0]["gtin"]
    assert veri["urunler"][0]["brand"] == "Marka"
    assert len(veri["gorseller"]) >= 1


def test_site_haritasi_exact_sku_filtreler(monkeypatch):
    monkeypatch.setattr(
        ws, "_sitemap_url_listesi",
        lambda host: [
            "https://firma.example/urun/ter0117-erkek-boxer",
            "https://firma.example/urun/ter0118-atlet",
            "https://firma.example/kategori/erkek",
        ])
    r = ws.site_haritasi_ara("firma.example", "TER0117")
    assert json.loads(r["result"]) == [
        "https://firma.example/urun/ter0117-erkek-boxer"]


def test_sitemap_xml_urlset_parser():
    tur, loclar = ws._xml_loclar(b"""<?xml version="1.0"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <url><loc>https://firma.example/urun/a</loc></url>
      <url><loc>https://firma.example/urun/b</loc></url>
    </urlset>""")
    assert tur == "urlset"
    assert loclar == [
        "https://firma.example/urun/a",
        "https://firma.example/urun/b"]
