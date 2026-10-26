"""tests/test_isci_ayar.py — işçi ortam ayarları ve yerel sağlık ucu.

Sır sızdırmama da burada ölçülür: `Ayarlar.__repr__` anahtarı ve DSN'i
yazmaz; log satırına sır düşmez.
"""

import json
import urllib.error
import urllib.request

import pytest

from worker import ayar as ayar_modulu
from worker.saglik import saglik_yaniti, sunucu_baslat

ANAHTAR = "test-iscisi-anahtari-32-bayt"
DSN = "postgresql://kullanici:parola@127.0.0.1:5432/basak"


def test_varsayilanlar_okunur():
    ayar = ayar_modulu.oku({"BASAK_ISCI_ANAHTARI": ANAHTAR})
    assert ayar.isci == "basak-worker-1"
    assert ayar.dsn == ""
    assert ayar.aralik == 1.0
    assert ayar.kalp_aralik == 20.0
    assert ayar.esik == 90.0
    assert ayar.zaman_asimi_ms == 15_000
    assert ayar.saglik_port == 0
    assert ayar.surum == "dev"


def test_anahtar_yoksa_acik_hata():
    with pytest.raises(ayar_modulu.AyarHatasi, match="BASAK_ISCI_ANAHTARI"):
        ayar_modulu.oku({})


def test_gecersiz_isci_adi_reddedilir():
    for ad in ("boşluk var", "-ile-baslamaz", "a" * 65):
        with pytest.raises(ayar_modulu.AyarHatasi, match="BASAK_ISCI_ADI"):
            ayar_modulu.oku({
                "BASAK_ISCI_ANAHTARI": ANAHTAR, "BASAK_ISCI_ADI": ad})


def test_sayi_hatasi_ve_aralik_hatasi_gorunur():
    with pytest.raises(ayar_modulu.AyarHatasi, match="sayı olmalı"):
        ayar_modulu.oku({
            "BASAK_ISCI_ANAHTARI": ANAHTAR, "BASAK_ISCI_ARALIK": "hızlı"})
    with pytest.raises(ayar_modulu.AyarHatasi, match="aralığında"):
        ayar_modulu.oku({
            "BASAK_ISCI_ANAHTARI": ANAHTAR, "BASAK_ISCI_ESIK": "5"})


def test_kalp_esikten_kucuk_olmali():
    with pytest.raises(ayar_modulu.AyarHatasi, match="KALP_ARALIK"):
        ayar_modulu.oku({
            "BASAK_ISCI_ANAHTARI": ANAHTAR,
            "BASAK_ISCI_ESIK": "30",
            "BASAK_ISCI_KALP_ARALIK": "30",
        })


def test_kuyruk_dsn_onceligi():
    ayar = ayar_modulu.oku({
        "BASAK_ISCI_ANAHTARI": ANAHTAR,
        "BASAK_ISCI_DATABASE_URL": DSN,
        "DATABASE_URL": "postgresql://yanlis@example.test/db",
    })
    assert ayar.dsn == DSN
    baska = ayar_modulu.oku({
        "BASAK_ISCI_ANAHTARI": ANAHTAR,
        "DATABASE_URL": DSN,
    })
    assert baska.dsn == DSN


def test_ozet_sir_yazmaz():
    ayar = ayar_modulu.oku({
        "BASAK_ISCI_ANAHTARI": ANAHTAR,
        "BASAK_ISCI_DATABASE_URL": DSN,
        "BASAK_SURUM": "abc1234",
    })
    metin = repr(ayar)
    assert ANAHTAR not in metin
    assert "parola" not in metin
    assert DSN not in metin
    ozet = ayar.ozet()
    assert ozet["kuyruk"] == "postgres"
    assert ozet["surum"] == "abc1234"
    assert "anahtar" not in ozet
    assert "dsn" not in ozet


def test_saglik_yaniti_uretici_patlarsa_acik_hata():
    def patla():
        raise RuntimeError("veritabanı yok")

    veri = saglik_yaniti(patla)
    assert veri["ok"] is False
    assert "veritabanı yok" in veri["hata"]


def test_yerel_saglik_ucu_gercekten_cevap_verir():
    httpd = sunucu_baslat(0, lambda: {
        "ok": True, "isci": "isci-1", "kuyruk": {"bekliyor": 0}})
    try:
        port = httpd.server_address[1]
        with urllib.request.urlopen(
                "http://127.0.0.1:%d/saglik" % port, timeout=5) as yanit:
            assert yanit.status == 200
            veri = json.loads(yanit.read().decode("utf-8"))
        assert veri["isci"] == "isci-1"
        assert veri["kuyruk"]["bekliyor"] == 0
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_saglik_ucu_sagliksizken_503_doner():
    def patla():
        raise RuntimeError("kuyruk okunamadı")

    httpd = sunucu_baslat(0, patla)
    try:
        port = httpd.server_address[1]
        with pytest.raises(urllib.error.HTTPError) as hata:
            urllib.request.urlopen(
                "http://127.0.0.1:%d/saglik" % port, timeout=5)
        assert hata.value.code == 503
        veri = json.loads(hata.value.read().decode("utf-8"))
        assert veri["ok"] is False
        assert "kuyruk okunamadı" in veri["hata"]
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_saglik_ucu_bilinmeyen_yol_404():
    httpd = sunucu_baslat(0, lambda: {"ok": True})
    try:
        port = httpd.server_address[1]
        with pytest.raises(urllib.error.HTTPError) as hata:
            urllib.request.urlopen(
                "http://127.0.0.1:%d/baska" % port, timeout=5)
        assert hata.value.code == 404
    finally:
        httpd.shutdown()
        httpd.server_close()
