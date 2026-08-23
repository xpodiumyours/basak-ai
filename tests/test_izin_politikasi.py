"""tests/test_izin_politikasi.py — Gercek izin politikasi testleri.

2026-08-23'te Casper'in buldugu bosluk: etiketler (yazma/internet/sistem)
yalnizca belgeydi; izinli_mi() tabloda is arıyor, TUM tanimli araçlar
otomatik geciyordu — yani ac_uygulama da otomatik kosabiliyordu.

Yeni kural: etiket POLITIKAYA baglanir. sistem etiketli araçlar varsayilan
KAPALI; ayarlar.json'da 'sistem_araclari_acik': true dersek acilir.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from tools import executor
from tools.permissions import (SETTINGS_YOLU, calistirilabilir_mi,
                               izinli_mi, politika)


@pytest.fixture
def ayar(monkeypatch, tmp_path):
    """Izin katmanini gecici ayar dosyasina baglar."""
    yol = tmp_path / "ayarlar.json"
    monkeypatch.setattr("tools.permissions.SETTINGS_YOLU", str(yol))
    return yol


class TestPolitika:
    def test_gunluk_araclar_otomatik(self):
        assert politika("git_durum") == "otomatik"
        assert politika("web_search") == "otomatik"
        assert politika("add_task") == "otomatik"

    def test_sistem_opt_in(self):
        assert politika("ac_uygulama") == "opt-in"

    def test_tanimsiz_yasak(self):
        assert politika("terminal_calistir") == "yasak"

    def test_eski_kapi_hala_tanimsizlari_dusturur(self):
        assert izinli_mi("git_durum") and not izinli_mi("dosya_sil")


class TestCalistirilabilirlik:
    def test_otomatik_araclar_gecer(self):
        assert calistirilabilir_mi("list_tasks") is True
        assert calistirilabilir_mi("deftere_kaydet") is True

    def test_sistem_varsayilan_kapali(self, ayar):
        assert not ayar.exists()  # ayar yokken
        assert calistirilabilir_mi("ac_uygulama") is False

    def test_sistem_anahtarla_acilir(self, ayar):
        ayar.write_text(json.dumps({"sistem_araclari_acik": True}),
                        encoding="utf-8")
        assert calistirilabilir_mi("ac_uygulama") is True

    def test_bomlu_ayar_dosyasi_okunur(self, ayar):
        # D-2 kurali: BOM'lu dosya sessizce okunamaz hata vermemeli
        ayar.write_bytes(
            b'\xef\xbb\xbf{"sistem_araclari_acik": true}')
        assert calistirilabilir_mi("ac_uygulama") is True


class TestExecutorEngeli:
    def test_ac_uygulama_engellenir_ve_kosmaz(self, ayar, monkeypatch):
        """Varsayilan ayarla ac_uygulama executor'dan DONEN HATA ile karsilanir;
        uygulama baslatma fonksiyonuna hic ulasilmaz."""
        firlatildi = []
        monkeypatch.setattr("tools.executor.ac_uygulama",
                            lambda u, p="": firlatildi.append(u) or {})
        sonuc = executor.calistir("ac_uygulama", {"uygulama": "notepad"},
                                  knowledge_dir="", gorevler_file="")
        assert sonuc.get("error")
        assert "varsayılan kapalı" in sonuc["error"]
        assert firlatildi == []  # uygulama hicbaslatilmadi

    def test_tanimsiz_arac_yine_engellenir(self, ayar):
        sonuc = executor.calistir("dosya_sil", {}, knowledge_dir="", gorevler_file="")
        assert "izin etiketi yok" in sonuc["error"]
