"""tests/test_hava.py — hava_durumu aracı: mock geocode+forecast, hata yolları.

Gerçek ağ yok: tools.hava._git monkeypatch edilir. Uydurma sıcaklık YOK —
boşşehir/bulunamadı/ağ hatasında result alanı hiç dönmez.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import calistir, hava
from tools.definitions import TANINMIS_TOOLLAR


class TestUcYer:
    def test_beyaz_listede(self):
        assert "hava_durumu" in TANINMIS_TOOLLAR

    def test_durum_etiketi_var(self):
        from chat.tools import DURUM_METNI
        assert "hava_durumu" in DURUM_METNI

    def test_yetenek_alaninda_internet(self):
        from tools.capabilities import CAPABILITY_NAMESPACES
        assert "hava_durumu" in CAPABILITY_NAMESPACES["internet"]

    def test_sema_zorunlu_sehir(self):
        from tools.definitions import TOOLS
        sema = next(t for t in TOOLS
                    if t["function"]["name"] == "hava_durumu")
        p = sema["function"]["parameters"]
        assert p["required"] == ["sehir"]
        assert "sehir" in p["properties"]


class TestGirdi:
    def test_bos_sehir(self):
        r = hava.hava_durumu("")
        assert "error" in r and "result" not in r

    def test_bos_sehir_bosluk(self):
        r = hava.hava_durumu("   ")
        assert "error" in r and "result" not in r

    def test_dispatcher_bos_sehir_ag_gitmez(self, monkeypatch):
        def patlak(url):
            raise AssertionError("ag cagrisi olmamali: %s" % url)
        monkeypatch.setattr(hava, "_git", patlak)
        r = calistir("hava_durumu", {"sehir": ""})
        assert "error" in r


class TestBulunamadi:
    def test_bulunamadi(self, monkeypatch):
        monkeypatch.setattr(hava, "_git", lambda url: {"results": []})
        r = hava.hava_durumu("Zzzz-yok-sehir")
        assert r == {"error": "Şehir bulunamadı: Zzzz-yok-sehir"}
        assert "result" not in r

    def test_dispatcher_bulunamadi(self, monkeypatch):
        monkeypatch.setattr(hava, "_git", lambda url: {"results": []})
        r = calistir("hava_durumu", {"sehir": "Yoksehir"})
        assert "error" in r and "result" not in r


class TestAgHatasi:
    def test_geocode_ag_hatasi(self, monkeypatch):
        def patlak(url):
            raise OSError("connection refused")
        monkeypatch.setattr(hava, "_git", patlak)
        r = hava.hava_durumu("Ankara")
        assert "error" in r
        assert "result" not in r
        assert "°C" not in r["error"]

    def test_forecast_ag_hatasi(self, monkeypatch):
        def sahte(url):
            if "geocoding" in url:
                return {"results": [{"name": "Ankara",
                                     "latitude": 39.9,
                                     "longitude": 32.8}]}
            raise OSError("timeout")
        monkeypatch.setattr(hava, "_git", sahte)
        r = hava.hava_durumu("Ankara")
        assert "error" in r and "result" not in r
        assert "°C" not in r["error"]

    def test_sicaklik_yoksa_uydurma_yok(self, monkeypatch):
        def sahte(url):
            if "geocoding" in url:
                return {"results": [{"name": "Ankara",
                                     "latitude": 39.9,
                                     "longitude": 32.8}]}
            return {"current": {"weather_code": 0,
                                "wind_speed_10m": 5.0,
                                "time": "2026-09-23T12:00"}}
        monkeypatch.setattr(hava, "_git", sahte)
        r = hava.hava_durumu("Ankara")
        assert "error" in r and "result" not in r


class TestKodEtiket:
    @pytest.mark.parametrize("kod,beklenen", [
        (0, "Açık"),
        (1, "Az bulutlu"),
        (3, "Çok bulutlu"),
        (45, "Sisli"),
        (63, "Yağmurlu"),
        (81, "Sağanak yağış"),
        (95, "Gök gürültülü fırtına"),
    ])
    def test_wmo_kodu_turkce_etiket(self, kod, beklenen):
        assert hava.hava_etiketi(kod) == beklenen

    def test_bilinmeyen_kod(self):
        assert hava.hava_etiketi(12345) == "Bilinmeyen hava"
        assert hava.hava_etiketi(None) == "Bilinmeyen hava"


class TestBasarili:
    @staticmethod
    def _sahte_git(url):
        if "geocoding" in url:
            return {"results": [{"name": "İstanbul",
                                 "latitude": 41.0,
                                 "longitude": 28.98}]}
        return {"current": {
            "temperature_2m": 18.44,
            "weather_code": 3,
            "wind_speed_10m": 9.26,
            "time": "2026-09-23T21:55",
        }}

    def test_satir_bicimi(self, monkeypatch):
        monkeypatch.setattr(hava, "_git", self._sahte_git)
        r = hava.hava_durumu("İstanbul")
        assert "result" in r and "error" not in r
        satir = r["result"]
        assert "İstanbul" in satir
        assert "18.4°C" in satir
        assert "Çok bulutlu" in satir
        assert "rüzgâr 9.3 km/sa" in satir
        assert "21:55" in satir
        assert "kaynak: open-meteo" in satir
        # Hissedilen sıcaklık istenmedi — metinde geçmez.
        assert "hissedilen" not in satir.lower()

    def test_dispatcher_hatti(self, monkeypatch):
        monkeypatch.setattr(hava, "_git", self._sahte_git)
        r = calistir("hava_durumu", {"sehir": "istanbul"})
        assert "result" in r
        assert "open-meteo" in r["result"]
