"""tests/live/test_freetools_canli.py — gercek freetools.org uzerinde kopru.

Bu test GERCEK siteye gider ve gercek Chromium baslatir; yalnizca
`pytest tests/live --live` ile kosar. Kod degistiginde koprun gercten
calistigini kanitlar: sonuc, bagimsiz Python karsilastirmasiyla
(hashlib/base64/aritmetik) birebir dogrulanir.

Nazik erisim: uc arac x 1 cagri = 3 istek (kota tavaninin cok altinda).
"""

import base64
import hashlib

import pytest

from tools import freetools_kopru as kopru

SHA_ADRES = ("https://www.freetools.org/security-tools/"
             "sha-hash-generator")
B64_ADRES = ("https://www.freetools.org/encode-tools/"
             "base64-encode-decode")
YUZDE_ADRES = ("https://www.freetools.org/data-tools/"
               "percentage-calculator")


@pytest.fixture(autouse=True)
def kota_sifre():
    kopru.sifirla()
    yield
    kopru.sifirla()


def test_canli_sha256_hashlib_ile_eslesir():
    beklenen = hashlib.sha256("merhaba".encode()).hexdigest()
    r = kopru.freetools_calistir(SHA_ADRES, ["merhaba"])
    assert "error" not in r, r
    assert beklenen in r.get("sonuc", ""), r


def test_canli_base64_python_ile_eslesir():
    beklenen = base64.b64encode("merhaba dunya".encode()).decode()
    r = kopru.freetools_calistir(B64_ADRES, ["merhaba dunya"])
    assert "error" not in r, r
    assert beklenen in r.get("sonuc", ""), r


def test_canli_yuzde_hesabi_dogru():
    # 15'in 200 uzerinden yuzdesi: aracla dogrudan test edilmez;
    # arac "200'un %15'i" modunda 30 donmeli (sayfa varsayilani).
    r = kopru.freetools_calistir(YUZDE_ADRES, ["15", "200"])
    assert "error" not in r, r
    sonuc = r.get("sonuc", "")
    assert "30" in sonuc, sonuc[:300]


def test_canli_onbellek_ikinci_cagriyi_agsiz_karsilar():
    birinci = kopru.freetools_calistir(SHA_ADRES, ["merhaba"])
    assert "error" not in birinci
    ikinci = kopru.freetools_calistir(SHA_ADRES, ["merhaba"])
    assert ikinci.get("onbellek") is True
    assert ikinci["sonuc"] == birinci["sonuc"]


def test_canli_beyaz_liste_disi_istek_aga_CIKMAZ():
    # dis site adresi hemen reddedilir — tarayici bile acilmaz
    r = kopru.freetools_calistir("https://ornek-matbaa.com/hesapla",
                                 ["1"])
    assert "error" in r
    assert "engel" in r["error"]
