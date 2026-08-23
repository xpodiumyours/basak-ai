"""tests/test_yetki_tavani.py — Araç döngüsünde yetki tavanı testleri.

2026-08-23'te Casper'in buldugu acik: ilk cagrida olcum-suzugunden gecen
is, arac dongusunun ikinci turunda HAM tools listesini goruyordu —
write_file_tool, deftere_kaydet, ac_uygulama dahil. Kural artik su:
ilk turda ne sunulduysa o tavandir; dongu seti asla buyutmez.

Testler gercek mesaj_isle akisini sahte beyinle kosar ve her turda
modele sunulan araç adlarini yakalar.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import chat as c


def _schema(ad):
    return {"type": "function",
            "function": {"name": ad, "description": "",
                         "parameters": {"type": "object", "properties": {}}}}


class SahteBrain:
    """Ilk cagriya tool_call doner, ikinciye duz metin; sunulan setleri yakalar."""

    def __init__(self, ilk_arac="git_durum"):
        self.goren = []
        self._ilk_arac = ilk_arac

    def yerel_modeller(self):
        return ["sahte-model"]

    def cevapla(self, mesajlar, model, tools=None, override_model=None):
        self.goren.append([t["function"]["name"] for t in (tools or [])])
        if len(self.goren) == 1:
            return ({"content": "", "tool_calls": [
                {"id": "1", "type": "function",
                 "function": {"name": self._ilk_arac,
                              "arguments": "{\"proje\": \"basak\"}"}}]},
                "sahte")
        return {"content": "Olcum tamam."}, "sahte"


@pytest.fixture
def izole(monkeypatch, tmp_path):
    """Gercek dosyalara dokunmayan mesaj_isle ortami."""
    monkeypatch.setattr(c, "HISTORY_FILE", str(tmp_path / "gecmis.json"))
    monkeypatch.setattr(c, "SETTINGS_FILE", str(tmp_path / "ayarlar.json"))
    monkeypatch.setattr(c, "_hafiza", False)
    monkeypatch.setattr("tools.calistir",
                        lambda ad, args, kdir="", gdosya="":
                        {"result": "%s sahte sonuc" % ad})
    return tmp_path


TAM_TOOLLAR = [_schema("git_durum"), _schema("write_file_tool"),
               _schema("ac_uygulama")]


class TestYetkiTavani:
    def test_olcum_suzugu_dongude_buyumez(self, izole):
        """Anahtar kelime cermeyen soru -> yalniz olcum aracları;
        ikinci turda yazma/sistem araci GORUNMEZ."""
        brain = SahteBrain()
        c.mesaj_isle("Projedeki degisiklikleri soyle.", brain, "SYS",
                     lambda code: None, TAM_TOOLLAR)
        assert brain.goren[0] == ["git_durum"]
        assert brain.goren[1] == ["git_durum"], (
            "Dongu ikinci turda yetkiyi genisletti: %s" % brain.goren[1])

    def test_anahtar_kelimeli_is_ilgili_aileyi_bastan_alir(self, izole):
        """Baglam diyeti: anahtar kelime ARTIK tam seti acmaz — yalniz
        ilgili aile + olcum uclusu sunulur. Cok adimli is korunur:
        dongu her turda AYNI seti gorur (yetki tavani)."""
        brain = SahteBrain()
        c.mesaj_isle(
            "VixRex durumuna bak, su dosyaya yaz, uygulamayi calistir.",
            brain, "SYS", lambda code: None, TAM_TOOLLAR)
        beklenen = ["git_durum", "write_file_tool", "ac_uygulama"]
        assert brain.goren[0] == beklenen
        assert brain.goren[1] == beklenen

    def test_tools_hic_verilmeyen_cagrıda_dongu_araç_sunmaz(self, izole):
        """tools=None ise dongu de None sunar."""
        brain = SahteBrain()
        c.mesaj_isle("merhaba nasilsin?", brain, "SYS",
                     lambda code: None, None)
        assert brain.goren[0] == []
