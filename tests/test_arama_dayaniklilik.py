"""tests/test_arama_dayaniklilik.py — Arama hattinin dayanikliligi (2026-10-01).

Kok neden (olculdu, 2026-10-01, ddgs 9.16.0): motorlar tek turda paralel
kosar ve `wait(..., FIRST_EXCEPTION)` ile erken doner; bir motor hata
verince o turdaki sonuclar toplanmadan
`DDGSException("No results found.")` yukseltilebiliyor. Motorlarin gercek
sebebi (HTTP 429/403/202) yalniz alt katman gunlugunde kalir; bizim kod
onu duz "No results found" metnine indiriyordu. Ayni sorgu "auto" ile 6
turun 1'inde tamamen bos dondu.

Sozlesme (ag yok; ddgs ve gunluk sahtelenir):
- Arama tek noktadan kosar: `_arama_kos`.
- Ilk tur `auto`; tekrar turlarinda yalniz gercek arama motorlari
  (wikipedia/grokipedia disarida: typeahead/opensearch, 0 sonuc).
- Tur tekrari dalgali motor hatalarini yutar.
- Basarisizlikta hata metni gercek motor sebebini (HTTP kodu) tasir.
- Sonuc yok ama motorlar saglikliysa eski "bulunamadi" metni korunur.
- Gunluk yakalayici is bitince logger'dan sokulur (sizinti yok).
"""

import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from tools import web_search as ws


class SahteDDGS:
    """Sirali ddgs taklidi: her cagri bir davranis adimi tuketir.

    Adim istisnaysa firlatilir, degilse sonuc listesi olarak doner.
    Her cagride verilen `backend` ve `timeout` kaydedilir; `gunluk`
    listesindeki satirlar istisna oncesi ilgili logger'a yazilir.
    """

    adimlar = []
    arkalar = []
    zaman_asimlari = []
    gunluk = []

    def __init__(self, *a, **kwargs):
        SahteDDGS.zaman_asimlari.append(kwargs.get("timeout"))

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def _kos(self, **kwargs):
        SahteDDGS.arkalar.append(kwargs.get("backend"))
        adim = SahteDDGS.adimlar.pop(0)
        for ad, satir in SahteDDGS.gunluk:
            logging.getLogger(ad).info(satir)
        if isinstance(adim, Exception):
            raise adim
        return adim

    def text(self, query, **kwargs):
        return self._kos(**kwargs)

    def news(self, query, **kwargs):
        return self._kos(**kwargs)

    def images(self, query, **kwargs):
        return self._kos(**kwargs)

    def books(self, query, **kwargs):
        return self._kos(**kwargs)


@pytest.fixture
def sahte(monkeypatch):
    """Ag yok, bekleme yok; her test temiz ddgs durumuyla baslar."""
    import ddgs

    monkeypatch.setattr(ddgs, "DDGS", SahteDDGS)
    monkeypatch.setattr(ws, "_ARAMA_BEKLEME", 0)
    SahteDDGS.adimlar = []
    SahteDDGS.arkalar = []
    SahteDDGS.zaman_asimlari = []
    SahteDDGS.gunluk = []
    return SahteDDGS


def _sonuc(baslik="B"):
    return [{"title": baslik, "href": "https://ornek.com", "body": "m"}]


class TestTekrar:
    def test_ilk_tur_hata_ikinci_tur_basarir(self, sahte):
        """Dalgali motor hatasi tur tekrariyla kurtarilir."""
        sahte.adimlar = [RuntimeError("No results found."), _sonuc()]
        r = ws.web_search("soru")
        assert "result" in r and "B" in r["result"], r
        assert len(sahte.arkalar) == 2

    def test_tekrarda_gercek_motorlara_daraltir(self, sahte):
        """Ilk tur auto; tekrar turu yalniz gercek arama motorlari."""
        sahte.adimlar = [RuntimeError("No results found."), _sonuc()]
        ws.web_search("soru")
        assert sahte.arkalar[0] == "auto"
        assert "wikipedia" not in sahte.arkalar[1]
        assert "grokipedia" not in sahte.arkalar[1]
        assert "yahoo" in sahte.arkalar[1]

    def test_uc_tur_de_hataliysa_hata_doner(self, sahte):
        sahte.adimlar = [RuntimeError("bir"), RuntimeError("iki"),
                         RuntimeError("uc")]
        r = ws.web_search("soru")
        assert "error" in r
        assert "3 denemede" in r["error"]

    def test_tek_zaman_asimi_sabiti_kullanilir(self, sahte):
        sahte.adimlar = [_sonuc()]
        ws.web_search("soru")
        assert sahte.zaman_asimlari == [ws._ARAMA_ZAMAN_ASIMI]

    def test_temiz_bos_sonuc_hata_degildir(self, sahte):
        """Motorlar saglikli ama sonuc yoksa eski 'bulunamadi' metni kalir."""
        sahte.adimlar = [[], []]
        r = ws.web_search("soru")
        assert "result" in r and "bulunamadi" in r["result"], r


class TestSebepTasima:
    def test_hata_motor_http_sebebini_tasir(self, sahte):
        """'No results found' yerine gercek HTTP sebepleri gorunur."""
        sahte.adimlar = [RuntimeError("No results found.")] * 3
        sahte.gunluk = [
            ("primp", "response: https://www.mojeek.com/search?q=x 403"),
            ("primp", "response: https://search.brave.com/search?q=x 429"),
        ]
        r = ws.web_search("soru")
        assert "error" in r
        assert "mojeek.com HTTP 403" in r["error"]
        assert "search.brave.com HTTP 429" in r["error"]
        assert "No results found" not in r["error"]

    def test_sebep_yoksa_son_istisna_kullanilir(self, sahte):
        sahte.adimlar = [RuntimeError("ag kapali")] * 3
        r = ws.web_search("soru")
        assert "ag kapali" in r["error"]

    def test_tekrar_eden_sebep_bir_kez_yazilir(self, sahte):
        """Ayni motor her turda engellense de hata metni sismez."""
        sahte.adimlar = [RuntimeError("No results found.")] * 3
        sahte.gunluk = [
            ("primp", "response: https://www.mojeek.com/search?q=x 403")]
        r = ws.web_search("soru")
        assert r["error"].count("mojeek.com HTTP 403") == 1

    def test_motor_seviyesi_hata_da_tasinir(self, sahte):
        sahte.adimlar = [RuntimeError("No results found.")] * 3
        sahte.gunluk = [("ddgs.ddgs", "Error in engine brave: timeout")]
        r = ws.web_search("soru")
        assert "brave hata verdi" in r["error"]


class TestGunlukSizintisi:
    def _sayim(self):
        return {ad: len(logging.getLogger(ad).handlers)
                for ad in ws._ARAMA_GUNLUK_ADLARI}

    def test_basarida_yakalayici_sokulur(self, sahte):
        once = self._sayim()
        sahte.adimlar = [_sonuc()]
        ws.web_search("soru")
        assert self._sayim() == once

    def test_hatada_da_yakalayici_sokulur(self, sahte):
        once = self._sayim()
        sahte.adimlar = [RuntimeError("x")] * 3
        ws.web_search("soru")
        assert self._sayim() == once

    def test_logger_seviyesi_geri_doner(self, sahte):
        lg = logging.getLogger("primp")
        eski = lg.level
        sahte.adimlar = [_sonuc()]
        ws.web_search("soru")
        assert lg.level == eski


class TestKategoriMotorlari:
    def test_her_kategoride_gercek_motor_var(self):
        for kategori in ("text", "news", "images", "books"):
            assert ws._GERCEK_MOTORLAR[kategori], kategori

    def test_sonuc_uretmeyen_motorlar_disarida(self):
        for kategori in ("text", "news"):
            assert "wikipedia" not in ws._GERCEK_MOTORLAR[kategori]
            assert "grokipedia" not in ws._GERCEK_MOTORLAR[kategori]

    def test_haber_kategorisi_kullanilir(self, sahte):
        sahte.adimlar = [RuntimeError("x"), _sonuc()]
        ws.haber_ara("konu")
        assert "yahoo" in sahte.arkalar[1]
        assert "bing" in sahte.arkalar[1]

    def test_gorsel_tekrarda_bing_ve_duckduckgo(self, sahte):
        sahte.adimlar = [RuntimeError("x"), [{"image": "http://a/x.jpg"}]]
        ws.gorsel_ara("urun")
        assert sahte.arkalar[1] == "bing,duckduckgo"

    def test_kitap_tekrarda_annasarchive(self, sahte):
        sahte.adimlar = [RuntimeError("x"),
                         [{"title": "K", "url": "U", "publisher": "Y"}]]
        ws.kitap_ara("katalog")
        assert sahte.arkalar[1] == "annasarchive"

    def test_site_ara_da_ayni_hatti_kullanir(self, sahte):
        sahte.adimlar = [RuntimeError("x"), _sonuc()]
        r = ws.site_ara("ornek.com", "urun")
        assert "result" in r
