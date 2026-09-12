"""tests/test_kisisel_kapi.py - Ise-gore-acma testleri (2026-09-12).

Profil blogu YALNIZ kisisel turda modele gider. Anilar, gecmis, araclar,
KISILIK aynen korunur.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chat  # once tam paket (dairesel import onlemi)
import chat.flow as flow
from chat.flow import _kisisel_gerekli_mi


class TestKapiKurali:
    @pytest.mark.parametrize("soru", [
        "benim hakkımda ne biliyorsun",
        "benim hakkimda ne biliyorsun",
        "adım neydi",
        "beni anlat",
        "ben kimim",
        "çayı seviyorum",
        "hatırla: yarın dişçi randevum var",
        "unut: eski adresim",
        "tercihlerim neler",
        "hobilerim hakkında ne biliyorsun",
    ])
    def test_kisisel_sorular_gecer(self, soru):
        assert _kisisel_gerekli_mi(soru) is True

    @pytest.mark.parametrize("soru", [
        "masaüstünde ne var",
        "merhaba nasılsın",
        "vixrex'te son durum ne",
        "şu dosyanın içinde ne yazıyor",
        "bugünkü hava nasıl",
        "fiyat araştır",
        "",
        "   ",
    ])
    def test_kisisel_olmayanlar_gecmez(self, soru):
        assert _kisisel_gerekli_mi(soru) is False


class SahteBeyin:
    def __init__(self):
        self.mesajlar = None

    def yerel_modeller(self):
        return ["m"]

    def bulut_musait(self):
        return True

    def _bulut_zinciri(self):
        return []

    def cevapla(self, messages, yerel_model, tools=None, **kw):
        self.mesajlar = messages
        return {"content": "ok"}, "sahte"


def _akis_hazirla(monkeypatch):
    import _chat_legacy as legacy
    import chat.context as _ctx
    import memory.profil as _profil
    monkeypatch.setattr(legacy, "yukle", lambda *a, **k: {})
    monkeypatch.setattr(legacy, "kaydet", lambda *a, **k: None)
    monkeypatch.setattr(legacy, "_save_and_reply", lambda *a, **k: None)
    monkeypatch.setattr(legacy, "_hafiza_al", lambda: None)
    monkeypatch.setattr(legacy, "_ilgili_anilar", lambda *a, **k: [])
    monkeypatch.setattr(_ctx, "hafiza_al", lambda: object())
    monkeypatch.setattr(_profil, "unut", lambda *a, **k: 0)
    monkeypatch.setattr(_profil, "ogren", lambda *a, **k: [])
    monkeypatch.setattr(_profil, "blok", lambda m: "KALICI PROFIL ORNEGI")


def _sistem_metinleri(beyin):
    return "\n".join(m.get("content", "") for m in beyin.mesajlar
                     if m.get("role") == "system")


class TestAkisKapisi:
    def test_kisisel_olmayanda_profil_yok(self, monkeypatch):
        _akis_hazirla(monkeypatch)
        from tools import TOOLS
        beyin = SahteBeyin()
        flow.mesaj_isle_yeni("masaüstünde ne var", beyin, "SYS",
                             lambda c: None, TOOLS)
        assert "KALICI PROFIL ORNEGI" not in _sistem_metinleri(beyin)

    def test_kisisel_soruda_profil_var(self, monkeypatch):
        _akis_hazirla(monkeypatch)
        from tools import TOOLS
        beyin = SahteBeyin()
        flow.mesaj_isle_yeni("benim hakkımda ne biliyorsun", beyin, "SYS",
                             lambda c: None, TOOLS)
        assert "KALICI PROFIL ORNEGI" in _sistem_metinleri(beyin)

    def test_ogrenme_turu_kisisel_sayilir(self, monkeypatch):
        # Anahtar listede olmasa bile ogrenme tetiklenirse profil gider.
        _akis_hazirla(monkeypatch)
        import memory.profil as _profil
        monkeypatch.setattr(_profil, "ogren",
                            lambda *a, **k: [("tercih", "sade konusma")])
        from tools import TOOLS
        beyin = SahteBeyin()
        flow.mesaj_isle_yeni("ben sade konuşurum", beyin, "SYS",
                             lambda c: None, TOOLS)
        assert "KALICI PROFIL ORNEGI" in _sistem_metinleri(beyin)


class TestSabitDavranis:
    """2026-09-12: davranis kurallari kapiya takilmaz — her turda gider."""

    def test_kisisel_olmayan_turda_davranis_var_olgu_yok(
            self, monkeypatch):
        _akis_hazirla(monkeypatch)
        from basak_app import KISILIK
        from tools import TOOLS
        beyin = SahteBeyin()
        flow.mesaj_isle_yeni("masaüstünde ne var", beyin, KISILIK,
                             lambda c: None, TOOLS)
        metin = _sistem_metinleri(beyin)
        assert "Teknik terim kullanma" in metin
        assert "Sonucu once soyle" in metin
        assert "ucretsizine bak" in metin
        assert "KALICI PROFIL ORNEGI" not in metin
