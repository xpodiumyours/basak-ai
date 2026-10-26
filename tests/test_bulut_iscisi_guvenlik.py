"""tests/test_bulut_iscisi_guvenlik.py — onay belgesi ve SSRF çekirdeği.

Neden bu dosya: bulut işçisi karar vermez; yalnız kullanıcının onayladığı
tek eylemi uygular. Burada belgenin koşuya, adıma, kaynağa, eyleme ve
argüman özetine bağlı olduğu; süresinin dolduğu ve ikinci kez
kullanılamadığı; adres denetiminin iç ağlara çıkışı kapattığı gerçek
kodla ölçülür.

Ağ gerekmez: DNS çözümlemesi sahte bir `getaddrinfo` ile yapılır.
"""

import os
import socket
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import worker.guvenlik as wg
from worker.guvenlik import (
    TekKullanim,
    TokenHatasi,
    eylem_ozeti,
    guvenli_url,
    kaynak,
    token_dogrula,
    token_uret,
)

ANAHTAR = "test-iscisi-anahtari-32-bayt"
SIMDI = 1_800_000_000
URL = "https://ornek.test/yol"


def _eylem(tur="ac"):
    if tur == "ac":
        return {"tur": "ac", "url": URL}
    return {"tur": tur, "secici": "#icerik"}


def _belge(tur="ac", url=URL, argumanlar=None, simdi=SIMDI, ttl=120,
           nonce="n-1", kosu="kosu-1", adim="adim-1"):
    return token_uret(
        ANAHTAR, kosu_id=kosu, adim_id=adim, tur=tur, url=url,
        argumanlar=argumanlar if argumanlar is not None else _eylem(tur),
        ttl=ttl, nonce=nonce, simdi=simdi,
    )


class TestBelge:
    def test_gecerli_belge_geri_doner(self):
        token, payload = _belge()
        geri = token_dogrula(
            ANAHTAR, token, tur="ac", url=URL, argumanlar=_eylem("ac"),
            simdi=SIMDI + 1, kosu_id="kosu-1", adim_id="adim-1",
        )
        assert geri == payload
        assert geri["rid"] == "kosu-1"
        assert geri["sid"] == "adim-1"
        assert geri["org"] == "https://ornek.test:443"

    def test_baska_kosu_reddedilir(self):
        token, _ = _belge()
        with pytest.raises(TokenHatasi, match="başka koşu"):
            token_dogrula(
                ANAHTAR, token, tur="ac", url=URL, argumanlar=_eylem("ac"),
                simdi=SIMDI, kosu_id="baska-kosu", adim_id="adim-1",
            )

    def test_baska_adim_reddedilir(self):
        token, _ = _belge()
        with pytest.raises(TokenHatasi, match="başka adım"):
            token_dogrula(
                ANAHTAR, token, tur="ac", url=URL, argumanlar=_eylem("ac"),
                simdi=SIMDI, kosu_id="kosu-1", adim_id="baska-adim",
            )

    def test_baska_eylem_reddedilir(self):
        token, _ = _belge("oku")
        with pytest.raises(TokenHatasi, match="başka eylem"):
            token_dogrula(
                ANAHTAR, token, tur="tikla", url=URL, argumanlar=_eylem("oku"),
                simdi=SIMDI,
            )

    def test_baska_kaynak_reddedilir(self):
        token, _ = _belge("oku", url="https://a.test/sayfa")
        with pytest.raises(TokenHatasi, match="başka kaynak"):
            token_dogrula(
                ANAHTAR, token, tur="oku", url="https://b.test/sayfa",
                argumanlar=_eylem("oku"), simdi=SIMDI,
            )

    def test_baska_port_ayri_kaynaktir(self):
        token, _ = _belge("oku", url="https://a.test/sayfa")
        with pytest.raises(TokenHatasi, match="başka kaynak"):
            token_dogrula(
                ANAHTAR, token, tur="oku", url="https://a.test:8443/sayfa",
                argumanlar=_eylem("oku"), simdi=SIMDI,
            )

    def test_baska_arguman_reddedilir(self):
        token, _ = _belge("oku")
        baska = {"tur": "oku", "secici": "#baska"}
        with pytest.raises(TokenHatasi, match="başka argüman"):
            token_dogrula(
                ANAHTAR, token, tur="oku", url=URL, argumanlar=baska,
                simdi=SIMDI,
            )

    def test_suresi_dolan_belge_reddedilir(self):
        token, _ = _belge(ttl=120)
        with pytest.raises(TokenHatasi, match="süresi doldu"):
            token_dogrula(
                ANAHTAR, token, tur="ac", url=URL, argumanlar=_eylem("ac"),
                simdi=SIMDI + 120,
            )
        # Bir saniye önce hâlâ geçerlidir; sınır tam exp anıdır.
        assert token_dogrula(
            ANAHTAR, token, tur="ac", url=URL, argumanlar=_eylem("ac"),
            simdi=SIMDI + 119,
        )

    def test_ttl_ust_siniri_300_saniyedir(self):
        _, payload = _belge(ttl=9_999)
        assert payload["exp"] - SIMDI == 300

    def test_ttl_en_az_bir_saniyedir(self):
        _, payload = _belge(ttl=0)
        assert payload["exp"] - SIMDI == 1

    def test_kurcalanmis_govde_reddedilir(self):
        token, _ = _belge()
        govde, imza = token.split(".")
        ilk = "A" if govde[0] != "A" else "B"
        with pytest.raises(TokenHatasi, match="imza geçersiz"):
            token_dogrula(
                ANAHTAR, ilk + govde[1:] + "." + imza, tur="ac", url=URL,
                argumanlar=_eylem("ac"), simdi=SIMDI,
            )

    def test_baska_anahtar_reddedilir(self):
        token, _ = _belge()
        with pytest.raises(TokenHatasi, match="imza geçersiz"):
            token_dogrula(
                "baska-anahtar", token, tur="ac", url=URL,
                argumanlar=_eylem("ac"), simdi=SIMDI,
            )

    @pytest.mark.parametrize("bozuk", ["", "tek-parca", "a.b.c", ".", "a."])
    def test_bicim_bozuk_belgeler_reddedilir(self, bozuk):
        with pytest.raises(TokenHatasi):
            token_dogrula(
                ANAHTAR, bozuk, tur="ac", url=URL, argumanlar=_eylem("ac"),
                simdi=SIMDI,
            )

    def test_bos_anahtar_kabul_edilmez(self):
        with pytest.raises(TokenHatasi, match="anahtar"):
            token_uret("", kosu_id="k", adim_id="a", tur="ac", url=URL)
        with pytest.raises(TokenHatasi, match="anahtar"):
            token_dogrula(
                "", _belge()[0], tur="ac", url=URL, argumanlar=_eylem("ac"),
            )

    @pytest.mark.parametrize("kosu,adim", [("", "a"), ("k", ""), (" ", " ")])
    def test_kosu_ve_adim_kimligi_zorunlu(self, kosu, adim):
        with pytest.raises(TokenHatasi, match="kimliği zorunlu"):
            token_uret(ANAHTAR, kosu_id=kosu, adim_id=adim, tur="ac", url=URL)

    def test_asiri_uzun_kimlik_reddedilir(self):
        with pytest.raises(TokenHatasi, match="çok uzun"):
            token_uret(
                ANAHTAR, kosu_id="k" * 97, adim_id="a", tur="ac", url=URL,
            )
        with pytest.raises(TokenHatasi, match="çok uzun"):
            token_uret(
                ANAHTAR, kosu_id="k", adim_id="a" * 97, tur="ac", url=URL,
            )


class TestKaynak:
    def test_varsayilan_port_acikca_yazilir(self):
        assert kaynak("https://Example.TEST/yol") == "https://example.test:443"
        assert kaynak("http://ornek.test/") == "http://ornek.test:80"
        assert kaynak("https://ornek.test:443/") == "https://ornek.test:443"

    @pytest.mark.parametrize("url", [
        "ftp://ornek.test/",
        "file:///etc/passwd",
        "https://kullanici:sifre@ornek.test/",
        "https://ornek.test:99999/",
        "https:///yol",
        "https://",
    ])
    def test_gecersiz_kaynak_reddedilir(self, url):
        with pytest.raises(TokenHatasi):
            kaynak(url)

    def test_eylem_ozeti_anahtar_sirasindan_bagimsiz(self):
        a = eylem_ozeti("ac", {"tur": "ac", "url": "https://a.test/"})
        b = eylem_ozeti("ac", {"url": "https://a.test/", "tur": "ac"})
        c = eylem_ozeti("ac", {"tur": "ac", "url": "https://b.test/"})
        assert a == b
        assert a != c


class TestTekKullanim:
    def test_ayni_nonce_ikinci_kez_kullanilamaz(self):
        defter = TekKullanim()
        assert defter.kullan("n-1", SIMDI + 60, simdi=SIMDI) is True
        assert defter.kullan("n-1", SIMDI + 60, simdi=SIMDI + 1) is False

    def test_bos_nonce_reddedilir(self):
        defter = TekKullanim()
        assert defter.kullan("", SIMDI + 60, simdi=SIMDI) is False
        assert defter.kullan(None, SIMDI + 60, simdi=SIMDI) is False

    def test_suresi_dolan_nonce_defterden_temizlenir(self):
        defter = TekKullanim()
        assert defter.kullan("eski", SIMDI + 10, simdi=SIMDI) is True
        assert defter.kullan("yeni", SIMDI + 300, simdi=SIMDI + 11) is True
        # "eski" süresi geçtiği için temizlendi; aynı ad yeniden kullanılır.
        assert defter.kullan("eski", SIMDI + 300, simdi=SIMDI + 11) is True


def _sahte_cozucu(harita):
    def sahte(host, *args, **kwargs):
        ip = harita.get(str(host))
        if ip is None:
            raise socket.gaierror(11001, "cozulemedi")
        adresler = ip if isinstance(ip, (list, tuple)) else [ip]
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", (adres, 0))
            for adres in adresler
        ]
    return sahte


@pytest.fixture
def cozucu(monkeypatch):
    def kur(harita):
        monkeypatch.setattr(wg.socket, "getaddrinfo", _sahte_cozucu(harita))
    return kur


class TestAdresGuvenligi:
    @pytest.mark.parametrize("ip", [
        "127.0.0.1",
        "127.1.1.1",
        "10.0.0.1",
        "172.16.0.1",
        "192.168.1.1",
        "169.254.169.254",
        "100.64.0.1",
        "0.0.0.0",
        "224.0.0.1",
        "240.0.0.1",
        "::1",
        "fd00::1",
        "fe80::1",
    ])
    def test_ic_ve_ozel_adresler_engellenir(self, cozucu, ip):
        cozucu({"ic.test": ip})
        neden = guvenli_url("https://ic.test/")
        assert neden and ip in neden

    def test_genel_adres_gecer(self, cozucu):
        cozucu({"genel.test": "93.184.216.34"})
        assert guvenli_url("https://genel.test/yol") is None

    def test_cozumlerden_biri_ozelse_engellenir(self, cozucu):
        cozucu({"karisik.test": ["93.184.216.34", "10.0.0.5"]})
        assert guvenli_url("https://karisik.test/") == "iç/özel adres (10.0.0.5)"

    def test_cozulemeyen_adres_engellenir(self, cozucu):
        cozucu({})
        assert guvenli_url("https://yok.test/") == "adres çözülemedi"

    @pytest.mark.parametrize("url,neden", [
        ("http://ic.test:8080/", "yalnız 80/443"),
        ("http://kullanici:sifre@ic.test/", "kimlik bilgisi"),
        ("ftp://ic.test/", "yalnız http/https"),
        ("file:///etc/passwd", "yalnız http/https"),
        ("http:///yol", "sunucu adı yok"),
        ("http://ic.test:abc/", "geçersiz URL"),
    ])
    def test_sema_port_ve_kimlik_bilgisi_denetlenir(self, cozucu, url, neden):
        cozucu({"ic.test": "93.184.216.34"})
        sonuc = guvenli_url(url)
        assert sonuc and neden in sonuc
