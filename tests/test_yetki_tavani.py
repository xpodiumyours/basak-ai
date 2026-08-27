"""tests/test_yetki_tavani.py — Fren sokumu: yetki tavani kaldirildi.

Ajan modu: tum araclar her tura ayni tam setle gider — tavan yok.
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
    def test_tum_araclar_her_tura_gider(self, izole):
        """Fren sokumu: ilk tur ne olursa olsun tam set gider, dongu de ayni."""
        brain = SahteBrain()
        c.mesaj_isle("Projedeki degisiklikleri soyle.", brain, "SYS",
                     lambda code: None, TAM_TOOLLAR)
        assert set(brain.goren[0]) == {"git_durum", "write_file_tool", "ac_uygulama"}
        assert set(brain.goren[1]) == {"git_durum", "write_file_tool", "ac_uygulama"}

    def test_anahtar_kelimeli_is_tam_seti_alir(self, izole):
        brain = SahteBrain()
        c.mesaj_isle(
            "VixRex durumuna bak, su dosyaya yaz, uygulamayi calistir.",
            brain, "SYS", lambda code: None, TAM_TOOLLAR)
        assert set(brain.goren[0]) == {"git_durum", "write_file_tool", "ac_uygulama"}
        assert set(brain.goren[1]) == {"git_durum", "write_file_tool", "ac_uygulama"}

    def test_tools_hic_verilmeyen_cagrıda_dongu_araç_sunmaz(self, izole):
        brain = SahteBrain()
        c.mesaj_isle("merhaba nasilsin?", brain, "SYS",
                     lambda code: None, None)
        assert brain.goren[0] == []
