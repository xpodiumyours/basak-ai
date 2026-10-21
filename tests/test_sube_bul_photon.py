"""tests/test_sube_bul_photon.py — Overpass çökünce Photon yedek hattı.

Ölçülen olay (2026-10-21): bulut IP'sinden Overpass aynaları 406/zaman
aşımı dönüyor; `sube_bul` şube bulamıyordu. Aynı OpenStreetMap kayıtları
Photon üzerinden erişilebiliyor (canlı ölçüm: Ankara'da 5 Migros şubesi,
adres + koordinatla). Bu dosya yedek hattın sözleşmesini kilitler:

- Yalnız adı markayı içeren ve yarıçap içindeki kayıtlar şube sayılır.
- Overpass şube döndürdüyse Photon HİÇ çağrılmaz (gereksiz trafik yok).
- İki hat da susarsa hata değil, "kayıt yok" sonucu döner (uydurma yok).
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools import harita  # noqa: E402
from tools.harita import sube_bul  # noqa: E402

MERKEZ = "39.920776,32.85405"      # Ankara, Çankaya


def _ozellik(ad, enlem, boylam, **fazla):
    ozellik = {
        "type": "Feature",
        "properties": {"name": ad, "street": fazla.pop("street", "Cadde"),
                       "housenumber": fazla.pop("housenumber", ""),
                       "city": fazla.pop("city", "Çankaya"),
                       "osm_id": fazla.pop("osm_id", 1),
                       "osm_type": fazla.pop("osm_type", "N"),
                       "osm_value": fazla.pop("osm_value", "supermarket")},
        "geometry": {"type": "Point", "coordinates": [boylam, enlem]},
    }
    ozellik["properties"].update(fazla)
    return ozellik


PHOTON_GOVDE = {"features": [
    _ozellik("Migros", 39.9060813, 32.860271),          # ~1.9 km
    _ozellik("Migros", 39.9219336, 32.8264001),         # ~2.6 km
    _ozellik("BİM", 39.9050, 32.8600),                  # başka marka
    _ozellik("Migros", 40.3000, 33.0000),               # yarıçap dışı
]}


class SahteHat:
    """URL'ye göre cevap veren sahte ağ: Overpass ve Photon ayrı."""

    def __init__(self, overpass=(None, "HTTP 406 Not Acceptable"),
                 photon=(PHOTON_GOVDE, None)):
        self.overpass = overpass
        self.photon = photon
        self.adresler = []

    def __call__(self, url, sure=None):
        self.adresler.append(url)
        if "photon" in url:
            return self.photon
        return self.overpass


def _coz(sonuc):
    assert "result" in sonuc, sonuc
    return json.loads(sonuc["result"])


def test_overpass_cokunce_photon_devralir(monkeypatch):
    hat = SahteHat()
    monkeypatch.setattr("tools.harita._json_al", hat)
    veri = _coz(sube_bul("Migros", MERKEZ, 5))
    assert veri["veri_kaynagi"] == "photon"
    assert veri["sube_sayisi"] == 2                    # BİM ve yarıçap dışı elendi
    assert [s["ad"] for s in veri["subeler"]] == ["Migros", "Migros"]
    assert veri["subeler"][0]["mesafe_km"] < veri["subeler"][1]["mesafe_km"]
    assert any("photon" in u for u in hat.adresler)


def test_overpass_bos_donerse_photon_denenir(monkeypatch):
    monkeypatch.setattr("tools.harita._json_al",
                        SahteHat(overpass=({"elements": []}, None)))
    veri = _coz(sube_bul("Migros", MERKEZ, 5))
    assert veri["sube_sayisi"] == 2
    assert veri["veri_kaynagi"] == "photon"


def test_overpass_doluysa_photon_cagrilmaz(monkeypatch):
    govde = {"elements": [{"type": "node", "id": 7, "lat": 39.92,
                           "lon": 32.85, "tags": {"name": "Migros",
                                                  "shop": "supermarket"}}]}
    hat = SahteHat(overpass=(govde, None))
    monkeypatch.setattr("tools.harita._json_al", hat)
    veri = _coz(sube_bul("Migros", MERKEZ, 5))
    assert veri["veri_kaynagi"] == "overpass"
    assert veri["sube_sayisi"] == 1
    assert not any("photon" in u for u in hat.adresler)


def test_iki_hat_da_susarsa_hata_degil_kayit_yok(monkeypatch):
    monkeypatch.setattr("tools.harita._json_al",
                        SahteHat(photon=({"features": []}, None)))
    veri = _coz(sube_bul("Migros", MERKEZ, 5))
    assert veri["sube_sayisi"] == 0
    assert "OpenStreetMap" in veri["not"]


def test_photon_da_hataliysa_acik_hata(monkeypatch):
    monkeypatch.setattr("tools.harita._json_al",
                        SahteHat(photon=(None, "HTTP 503 Service Unavailable")))
    sonuc = sube_bul("Migros", MERKEZ, 5)
    assert "error" in sonuc
    assert "aynalar" in sonuc["error"]


def test_marka_eslesmesi_turkce_duyarsiz():
    veri = {"features": [_ozellik("MİGROS Jet", 39.9060813, 32.860271),
                         _ozellik("Migros", 39.9219336, 32.8264001)]}
    subeler = harita._photon_subeleri(veri, "migros", 39.920776, 32.85405, 5)
    assert len(subeler) == 2


def test_koordinatsiz_ozellik_atlanir():
    veri = {"features": [
        {"properties": {"name": "Migros"}, "geometry": {}},
        _ozellik("Migros", 39.9060813, 32.860271),
    ]}
    subeler = harita._photon_subeleri(veri, "Migros", 39.920776, 32.85405, 5)
    assert len(subeler) == 1


@pytest.mark.parametrize("yaricap", [1, 5, 25])
def test_yaricap_disi_kayit_girmez(monkeypatch, yaricap):
    monkeypatch.setattr("tools.harita._json_al", SahteHat())
    veri = _coz(sube_bul("Migros", MERKEZ, yaricap))
    assert all(s["mesafe_km"] <= yaricap for s in veri["subeler"])


def test_bos_ayna_ve_photon_hatasi_hata_doner(monkeypatch):
    """osm.ch gibi boş aynalar 200 döner; bu "baktım, yok" sayılmaz.

    Ölçüldü (2026-10-21): boş gövdeli ayna + Photon hatası birleşince
    sonuç "0 şube" görünüyordu; oysa gerçek bir arama yapılmamıştı.
    """
    monkeypatch.setattr("tools.harita._json_al",
                        SahteHat(overpass=({"elements": []}, None),
                                 photon=(None, "HTTP 429 Too Many Requests")))
    sonuc = sube_bul("Migros", MERKEZ, 5)
    assert "error" in sonuc, sonuc
    assert "aynalar" in sonuc["error"]
