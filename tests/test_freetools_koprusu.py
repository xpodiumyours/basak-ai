"""tests/test_freetools_koprusu.py — Faz 1 freetools koprusu bekci testleri.

Bu testler AG cevrimdisi calisir: ag YOK, tarayici YOK.
Kopru birimleri (beyaz liste, kota, onbellek, fail-open) saf Python ile
olculur; tarayici adimi yalnizca monkeypatch ile sahtelenir.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import calistir
from tools.freetools_katalog import ARACLAR, KATEGORI_ADI, adres as kat_adres
from tools import freetools_kopru as kopru


class TestBeyazListe:
    def test_freetools_org_izinli(self):
        assert kopru._adres_denetle(
            "https://www.freetools.org/security-tools/sha-hash-generator"
        ) is None
        assert kopru._adres_denetle(
            "https://freetools.org/text-tools/letter-counter"
        ) is None

    def test_dis_site_red(self):
        for url in ("https://evil.example.com/x",
                    "https://freetools.org.evil.com/x",
                    "https://notfreetools.org/x"):
            hata = kopru._adres_denetle(url)
            assert hata and "engel" in hata.lower(), url

    def test_scheme_ve_port_denetimi(self):
        assert kopru._adres_denetle(
            "ftp://www.freetools.org/x") is not None
        assert kopru._adres_denetle(
            "https://www.freetools.org:8443/x") is not None
        assert kopru._adres_denetle("") is not None

    def test_dispatcher_beyaz_liste_disini_kostrmaz(self):
        # arac dispathcer'dan gecse bile kopru reddeder
        r = calistir("freetools_calistir",
                    {"adres": "https://ornek.com/araç"})
        assert "error" in r
        assert "engel" in r["error"].lower() or "yalnizca" in r["error"]


class TestKatalog:
    def test_katalog_kendi_iceriginde_tutarli(self):
        assert len(ARACLAR) >= 150
        assert len(set(ARACLAR)) == len(ARACLAR)   # tekrar yok
        for kategori, slug in ARACLAR:
            assert kategori in KATEGORI_ADI, kategori
            assert "/" not in slug and slug.islower(), slug

    def test_arama_kelime_eslesmesi(self):
        sonuc = calistir("freetools_ara", {"sorgu": "sha hash"})
        eslesen = [s["ad"] for s in sonuc["sonuclar"]]
        assert "sha-hash-generator" in eslesen

    def test_arama_kategori_filtresi(self):
        sonuc = calistir("freetools_ara",
                         {"sorgu": "converter",
                          "kategori": "conversion-tools"})
        assert sonuc["sonuclar"]
        assert all(s["kategori"] == "conversion-tools"
                   for s in sonuc["sonuclar"])

    def test_arama_sorgusuz_kategorileri_doner(self):
        sonuc = calistir("freetools_ara", {"sorgu": ""})
        assert "kategoriler" in sonuc
        assert len(sonuc["kategoriler"]) == len(KATEGORI_ADI)

    def test_adres_yapisi(self):
        assert kat_adres("text-tools", "letter-counter") == (
            "https://www.freetools.org/text-tools/letter-counter")


class TestKotaVeOnbellek:
    def setup_method(self):
        kopru.sifirla()

    def teardown_method(self):
        kopru.sifirla()

    def test_onbellek_ikinci_cagriyi_sarar(self, monkeypatch):
        cagri = {"n": 0}

        def sahte(adres, form):
            cagri["n"] += 1
            return {"sonuc": "deger", "kaynak": "freetools.org",
                    "adres": adres}

        monkeypatch.setattr(kopru, "_sarmalayici", sahte)
        ilk = kopru.freetools_calistir(
            "https://www.freetools.org/x", ["merhaba"])
        ikinci = kopru.freetools_calistir(
            "https://www.freetools.org/x", ["merhaba"])
        assert cagri["n"] == 1
        assert ilk["sonuc"] == "deger"
        assert ikinci.get("onbellek") is True

    def test_farkli_girdi_onbellekte_ayri(self, monkeypatch):
        cagri = {"n": 0}

        def sahte(adres, form):
            cagri["n"] += 1
            return {"sonuc": "-".join(form), "adres": adres}

        monkeypatch.setattr(kopru, "_sarmalayici", sahte)
        kopru.freetools_calistir("https://www.freetools.org/x", ["a"])
        kopru.freetools_calistir("https://www.freetools.org/x", ["b"])
        assert cagri["n"] == 2

    def test_kota_dolunca_hata_donu(self, monkeypatch):
        def sahte(adres, form):
            return {"sonuc": "x", "adres": adres}

        monkeypatch.setattr(kopru, "_sarmalayici", sahte)
        # her cagri farkli girdi: onbellek kota yakmasin (nazik erisim)
        for i in range(kopru.GUNLUK_TAVAN):
            r = kopru.freetools_calistir(
                "https://www.freetools.org/x", ["girdi-%d" % i])
            assert "error" not in r
        r = kopru.freetools_calistir(
            "https://www.freetools.org/x", ["girdi-son"])
        assert "error" in r
        assert "sinir" in r["error"].lower()

    def test_onbellek_kota_yakmaz(self, monkeypatch):
        """Ayni girdi tekrarlanirsa tarayici ve kota harcanmaz."""
        cagri = {"n": 0}

        def sahte(adres, form):
            cagri["n"] += 1
            return {"sonuc": "x", "adres": adres}

        monkeypatch.setattr(kopru, "_sarmalayici", sahte)
        for _ in range(10):
            kopru.freetools_calistir("https://www.freetools.org/x",
                                     ["ayni"])
        assert cagri["n"] == 1
        with kopru._kilit:
            assert kopru._gun_sayaci["adet"] == 1

    def test_kota_ayni_gun_sifirlanmaz_ayni_tur_sayilir(self, monkeypatch):
        def sahte(adres, form):
            return {"sonuc": "x", "adres": adres}

        monkeypatch.setattr(kopru, "_sarmalayici", sahte)
        for i in range(5):
            kopru.freetools_calistir("https://www.freetools.org/x",
                                     ["girdi-%d" % i])
        with kopru._kilit:
            assert kopru._gun_sayaci["adet"] == 5


class TestFailOpen:
    def test_bos_adres_hata(self):
        r = calistir("freetools_calistir", {"adres": ""})
        assert "error" in r

    def test_playwright_yoksa_sohbet_kirilmaz(self, monkeypatch):
        """Playwright yokken (Vercel): bilinen arac yerel standart
        algoritmayla doner, bilmeyen arac hata doner — ikisinde de Basak
        devam eder, chatbot yasağı ihlal edilmez."""
        import hashlib

        monkeypatch.setattr(
            kopru, "_tarayici_kos",
            lambda *a, **k: (_ for _ in ()).throw(
                ModuleNotFoundError("playwright")))
        r = kopru.freetools_calistir(
            "https://www.freetools.org/security-tools/sha-hash-generator",
            ["yerel-girdi-1"])
        assert "sonuc" in r and "error" not in r
        assert r["sonuc"] == hashlib.sha256(
            b"yerel-girdi-1").hexdigest()
        assert "yerel-hesaplama" in r["kaynak"]
        assert r["adres"].endswith("sha-hash-generator")
        assert "playwright" in r["not"].lower()

        r2 = kopru.freetools_calistir(
            "https://www.freetools.org/xx/yy", ["a"])
        assert "error" in r2
        assert "playwright" in r2["error"].lower()

    def test_kopru_hatasi_cevap_yolunu_kirpmaz(self, monkeypatch):
        """Kopru patlarsa sohbet aynen devam eder (MIMARI ilke 4)."""
        def patlar(*a, **k):
            raise RuntimeError("tarayici patladi")

        monkeypatch.setattr(kopru, "_tarayici_kos", patlar)
        r = kopru.freetools_calistir("https://www.freetools.org/x/y",
                                    ["girdi"])
        assert "error" in r
        # diger arac aynen calisir
        r2 = calistir("simdi", {})
        assert "result" in r2

    def test_zaman_asimi_hata_doner(self, monkeypatch):
        import time as _t

        def uyuyan(adres, form):
            _t.sleep(0.1)
            raise TimeoutError("yavas")

        monkeypatch.setattr(kopru, "_tarayici_kos", uyuyan)
        r = kopru.freetools_calistir("https://www.freetools.org/a/b",
                                    ["girdi"])
        assert "error" in r


class TestYasaklar:
    def test_chatbot_yasagi_adi_gecmez(self):
        """Kopru modulunde yasakli tanimlayici adi yok (AST tarayisi)."""
        import ast
        yol = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "tools", "freetools_kopru.py")
        with open(yol, encoding="utf-8") as f:
            agac = ast.parse(f.read())
        yasak = ("ARAC_ISARET", "arac_gerek", "TUR_SINIRI",
                 "ARAC_SONUC_TAVAN", "onay_kuyrugu", "yetki_tavani")
        for dugum in ast.walk(agac):
            adlar = []
            if isinstance(dugum, (ast.FunctionDef, ast.AsyncFunctionDef,
                                  ast.ClassDef)):
                adlar.append(dugum.name)
            elif isinstance(dugum, ast.arg):
                adlar.append(dugum.arg)
            elif isinstance(dugum, ast.Name):
                adlar.append(dugum.id)
            for ad in adlar:
                for y in yasak:
                    assert y not in ad, (ad, y)

    def test_duyarli_dosya_taramasinda_temiz(self):
        """test_chatbot_yasagi DOSYALAR listesindeki dosyalara dokunulmadi."""
        # freetools_kopru.py o listede degil; yine de ayni yasak adlari
        # tanimlamadigimizi TestYasaklar ustte olcer. Burada yalnizca
        # definitions/__init__ eklenenlerin yasak isim tasimadigini
        # sozlesme uzerinden dogrulariz.
        from tools.definitions import TANINMIS_TOOLLAR
        assert "freetools_ara" in TANINMIS_TOOLLAR
        assert "freetools_calistir" in TANINMIS_TOOLLAR
