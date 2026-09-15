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
        r = ws.derin_oku("http://ornek.com/uzun")
        assert "result" in r, r
        assert len(r["result"]) > 200000
        assert "500000" in r["result"]

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
