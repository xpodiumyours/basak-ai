"""tests/test_harita_z0.py — Z0: harita_goster (Google Maps baglantisi).

Kabul olcusu: docs/HARITA-ZINCIRI-PLANI.md, FAZ 1.
- Iki modda dogru URL bicimi
- Turkce karakter kacisi
- Bos/asiri uzun/gudum disi girdi → anlamli hata, uydurma baglanti YOK
- Dordun dordu de dolu: sema + dispatcher dali + yetenek alani + durum etiketi
- AG CAGRISI YOK: modul ag kutuphanesi kullanmaz (anahtar/kota gerektirmez)
"""

import inspect
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from tools import calistir
from tools.harita import (ARAMA_TABANI, GECERLI_MODLAR, KONUM_TAVANI,
                          MOD_ARAMA, MOD_YOL, YOL_TABANI, harita_goster)


def _baglanti(konum, mod=MOD_YOL):
    """Basari yolundan 'result' JSON'unu cozer; hata varsa None doner."""
    import json
    r = harita_goster(konum, mod)
    if "error" in r:
        return None
    return json.loads(r["result"])


class TestBaglantiBicimi:
    def test_yol_modu(self):
        veri = _baglanti("Moda, Kadikoy")
        assert veri["mod"] == MOD_YOL
        assert veri["baglanti"].startswith(YOL_TABANI)
        assert veri["kaynak"] == "Google Maps"

    def test_ara_modu(self):
        veri = _baglanti("Moda, Kadikoy", MOD_ARAMA)
        assert veri["mod"] == MOD_ARAMA
        assert veri["baglanti"].startswith(ARAMA_TABANI)

    def test_mod_verilmezse_yol(self):
        veri = _baglanti("Ankara")
        assert veri["mod"] == MOD_YOL

    def test_konum_baglantida_tasinir(self):
        veri = _baglanti("Besiktas")
        assert "Besiktas" in veri["baglanti"].replace("%20", " ")
        assert veri["konum"] == "Besiktas"

    def test_fazla_bosluk_tek_bosluga_iner(self):
        veri = _baglanti("  Sisli \n  Istanbul  ")
        assert veri["konum"] == "Sisli Istanbul"


class TestKacisGuvenligi:
    def test_turkce_karakterler_kacir(self):
        veri = _baglanti("Şişli/İstanbul")
        baglanti = veri["baglanti"]
        # Ham Turkce karakter URL'de durmaz; yuzde kodlamali gider.
        assert "Ş" not in baglanti and "İ" not in baglanti
        assert "%C5%9E" in baglanti or "%C5%9F" in baglanti

    def test_parametre_kacisi_yapilamaz(self):
        """Konum metni URL parametresinden KACAMAZ (& / = / ? kodlanir)."""
        veri = _baglanti("x&destination=basaka&q=?")
        baglanti = veri["baglanti"]
        assert baglanti.count("destination=") == 1
        assert "&destination=basaka" not in baglanti.replace("%26", "&")
        assert "%26" in baglanti


class TestHataYollari:
    def test_bos_konum_hata(self):
        assert "error" in harita_goster("")
        assert "error" in harita_goster("   ")

    def test_none_konum_hata(self):
        assert "error" in harita_goster(None)

    def test_asiri_uzun_konum_hata(self):
        assert "error" in harita_goster("a" * (KONUM_TAVANI + 1))

    def test_gudum_disi_mod_hata(self):
        r = harita_goster("Ankara", "ucak")
        assert "error" in r
        for mod in GECERLI_MODLAR:
            assert mod in r["error"]

    def test_hata_durumunda_baglanti_uretilmez(self):
        """Hata yolunda 'result' YOK — uydurma baglanti yazilmaz."""
        r = harita_goster("")
        assert "result" not in r
        assert "google.com/maps" not in str(r)


class TestDortYer:
    """AGENTS.md §0: arac dort yerde birden olmali, yoksa sessizce olur."""

    def test_sema_kayitli(self):
        from tools.definitions import TANINMIS_TOOLLAR
        assert "harita_goster" in TANINMIS_TOOLLAR

    def test_dispatcher_dali_calisir(self):
        r = calistir("harita_goster", {"konum": "Ankara"})
        assert "error" not in r, r
        assert "google.com/maps" in r["result"]

    def test_dispatcher_mod_aktarir(self):
        r = calistir("harita_goster", {"konum": "Ankara", "mod": "ara"})
        assert ARAMA_TABANI in r["result"]

    def test_yetenek_alaninda(self):
        from chat.agent_protocol import YETENEK_ALANLARI
        assert "harita" in YETENEK_ALANLARI
        assert "harita_goster" in YETENEK_ALANLARI["harita"]

    def test_alan_aciklamasi_var(self):
        """Alan adi YETENEK_ALANLARI ve ALAN_ACIKLAMALARI'nda birlikte olmali."""
        from chat.agent_protocol import ALAN_ACIKLAMALARI
        assert "harita" in ALAN_ACIKLAMALARI
        assert ALAN_ACIKLAMALARI["harita"].strip()

    def test_durum_etiketi_var(self):
        from chat.tools import DURUM_METNI
        assert DURUM_METNI.get("harita_goster")

    def test_kapasite_defteri_eksiksiz(self):
        from tools.capabilities import validate_registry
        assert validate_registry()["ok"] is True


class TestAgCagrisiYok:
    """Z0'in sozu: ag cagrisi yok, anahtar yok, kota yok. Statik olarak kanitlanir."""

    KAYNAK = inspect.getsource(sys.modules["tools.harita"])

    @pytest.mark.parametrize("kaliplar", [
        r"\brequests\b",
        r"urllib\.request",
        r"\burlopen\b",
        r"\bsocket\b",
        r"\bhttpx\b",
        r"\baiohttp\b",
    ])
    def test_ag_kutuphanesi_kullanilmaz(self, kaliplar):
        assert not re.search(kaliplar, self.KAYNAK), kaliplar

    def test_donus_metin_icerir(self):
        """Arac sonucu gercek metin doner; bos soz vermez."""
        r = harita_goster("Izmir")
        assert isinstance(r["result"], str) and r["result"]
