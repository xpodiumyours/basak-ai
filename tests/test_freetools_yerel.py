"""tests/test_freetools_yerel.py — Faz 2: web icin yerel standart algoritma.

Vercel'de playwright yok; freetools.org araclari burada Python stdlib ile
yerelde hesaplanir. freetools.org'un JS'i KOPYALANMAZ — bu test AST ile
yalnizca standart kutuphane importu oldugunu da kontrol eder.

Cevrimdisi calisir: ag yok, tarayici yok.
"""

import ast
import base64
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chat.tools import sonucu_donustur
from tools import calistir
from tools import freetools_kopru as kopru
from tools import freetools_yerel as yerel

SHA = "https://www.freetools.org/security-tools/sha-hash-generator"
B64 = "https://www.freetools.org/encode-tools/base64-encode-decode"
YUZDE = "https://www.freetools.org/data-tools/percentage-calculator"


class TestYerelHesap:
    def test_sha256_canli_sonucla_birebir(self):
        r = yerel.hesapla(SHA, ["merhaba"])
        assert r["sonuc"] == hashlib.sha256(b"merhaba").hexdigest()

    def test_sha_diger_algoritma_ikinci_alandan(self):
        assert yerel.hesapla(SHA, ["merhaba", "md5"])["sonuc"] == \
            hashlib.md5(b"merhaba").hexdigest()
        assert yerel.hesapla(SHA, ["merhaba", "SHA-512"])["sonuc"] == \
            hashlib.sha512(b"merhaba").hexdigest()

    def test_base64_kodlama_ve_cozme(self):
        kodlu = yerel.hesapla(B64, ["merhaba dunya"])["sonuc"]
        assert kodlu == base64.b64encode(b"merhaba dunya").decode()
        assert yerel.hesapla(B64, [kodlu, "decode"])["sonuc"] == \
            "merhaba dunya"

    def test_yuzde_canli_sonucla_ayni(self):
        # Faz 1 canli testinde sayfanin dondugu deger 30 idi (15, 200)
        assert yerel.hesapla(YUZDE, ["15", "200"])["sonuc"] == "30"

    def test_url_kodlama(self):
        kodlu = yerel.hesapla(
            "https://www.freetools.org/encode-tools/url-encode-decode",
            ["a b&c"])["sonuc"]
        assert kodlu == "a%20b%26c"

    def test_harf_sayaci(self):
        metin = yerel.hesapla(
            "https://www.freetools.org/text-tools/letter-counter",
            ["Merhaba 12"])["sonuc"]
        assert "Harf: 7" in metin
        assert "Rakam: 2" in metin
        assert "Kelime: 2" in metin

    def test_ters_cevirme(self):
        assert yerel.hesapla(
            "https://www.freetools.org/text-tools/reverse-text",
            ["abc"])["sonuc"] == "cba"

    def test_hex_ondalik(self):
        assert yerel.hesapla(
            "https://www.freetools.org/conversion-tools/"
            "hexadecimal-to-decimal-converter", ["ff"])["sonuc"] == "255"

    def test_binary_hex(self):
        assert yerel.hesapla(
            "https://www.freetools.org/encode-tools/binary-hex-converter",
            ["1010"])["sonuc"] == "0xa"

    def test_sonuc_etiketi_ve_adres(self):
        r = yerel.hesapla(SHA, ["x"])
        assert "yerel-hesaplama" in r["kaynak"]
        assert r["adres"] == SHA
        assert "sonuc" in r and "error" not in r

    def test_bilinmeyen_arac_none_doner(self):
        assert yerel.hesapla("https://www.freetools.org/x/yy", ["a"]) is None

    def test_gecersiz_girdi_uydurma_degil_hata(self):
        r = yerel.hesapla(B64, ["!!!gecersiz base64!!!", "decode"])
        assert "error" in r and "sonuc" not in r


class TestKopruGeriDususu:
    def setup_method(self):
        kopru.sifirla()

    def teardown_method(self):
        kopru.sifirla()

    def test_kopru_hatasi_yerel_sonuca_duser(self, monkeypatch):
        monkeypatch.setattr(
            kopru, "_sarmalayici",
            lambda *a, **k: {"error": "playwright kurulu degil"})
        r = kopru.freetools_calistir(SHA, ["yerel-geri-dus-1"])
        assert r["sonuc"] == hashlib.sha256(b"yerel-geri-dus-1").hexdigest()
        assert "yerel-hesaplama" in r["kaynak"]
        assert "playwright kurulu degil" in r["not"]

    def test_bilinmeyen_arac_kopru_hatasi_kalir(self, monkeypatch):
        monkeypatch.setattr(
            kopru, "_sarmalayici",
            lambda *a, **k: {"error": "Zaman asimi"})
        r = kopru.freetools_calistir(
            "https://www.freetools.org/xx/yy", ["a"])
        assert r == {"error": "Zaman asimi"} or "error" in r

    def test_beyaz_liste_yerel_hesaptan_once(self, monkeypatch):
        """Freetools disindaki adrese yerel hesapla bile ulasilamaz."""
        def _asin(*a, **k):
            raise AssertionError("beyaz liste disi adreste yerel hesap calisti")

        monkeypatch.setattr(yerel, "hesapla", _asin)
        r = kopru.freetools_calistir("https://evil.example.com/x", ["a"])
        assert "error" in r

    def test_model_gordugu_metin_adres_icerir(self, monkeypatch):
        """Derin baglanti: modelin gordugu metinde arac adresi var."""
        monkeypatch.setattr(
            kopru, "_sarmalayici",
            lambda *a, **k: {"error": "playwright yok"})
        r = kopru.freetools_calistir(SHA, ["derin-baglanti-1"])
        metin = sonucu_donustur(r)
        assert hashlib.sha256(b"derin-baglanti-1").hexdigest() in metin
        assert "[Araç sayfası: %s]" % SHA in metin
        assert "yerel-hesaplama" in metin

    def test_dispatcher_sonucu_artik_bos_kalmaz(self, monkeypatch):
        """Eski hata: {sonuc: ...} sozlugu model bos string goruyordu."""
        monkeypatch.setattr(
            kopru, "_sarmalayici",
            lambda *a, **k: {"error": "playwright yok"})
        ham = calistir("freetools_calistir", {"adres": SHA, "form": ["abc"]})
        metin = sonucu_donustur(ham)
        assert hashlib.sha256(b"abc").hexdigest() in metin
        assert metin.strip()

    def test_katalog_aramasi_bos_donmez(self):
        metin = sonucu_donustur(calistir("freetools_ara",
                                         {"sorgu": "sha hash"}))
        assert "sha-hash-generator" in metin


class TestYerelModuldeKopyalamaYok:
    def test_yamlniz_standart_kutuphane(self):
        """freetools.org JS'i kopyalanmaz; ag/ tarayici importu yoktur."""
        yol = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "tools", "freetools_yerel.py")
        with open(yol, encoding="utf-8") as f:
            agac = ast.parse(f.read())
        importlar = []
        for dugum in ast.walk(agac):
            if isinstance(dugum, ast.Import):
                importlar.extend(a.name for a in dugum.names)
            elif isinstance(dugum, ast.ImportFrom) and dugum.module:
                importlar.append(dugum.module)
        yasak = ("playwright", "requests", "urllib.request", "httpx",
                 "selenium", "freetools")
        for ad in importlar:
            for y in yasak:
                assert not ad.startswith(y), (ad, y)
        assert {"hashlib", "base64"} <= set(importlar)

    def test_dosya_beyaz_liste_kontrolu_yapmaz(self):
        """Adres denetimi kopru (freetools_kopru) katmanindadir."""
        yol = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "tools", "freetools_yerel.py")
        with open(yol, encoding="utf-8") as f:
            metin = f.read()
        assert "_adres_denetle" not in metin
        assert "IZINLI_YONETICILER" not in metin
