"""tests/test_tekrar_yaz.py — "Daha düzgün yaz" taze deneme testleri.

Çevrimdışı: gerçek model yok. Kilitler:
1. tazele=True aynı soruda önbelleğe bakmadan modeli yeniden çağırır.
2. tercih zincire aynen taşınır (beğenilmeyen sağlayıcı en sonda denenir).
3. tercih bilmeyen eski imzalı beyinde akış kırılmaz (aynı davranış).
4. Cevap metnine dokunulmaz; yasaklı isimler kullanılmaz.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chat as c
from chat import onbellek


@pytest.fixture(autouse=True)
def _temiz_onbellek():
    onbellek.temizle()
    yield
    onbellek.temizle()


@pytest.fixture
def izole(monkeypatch, tmp_path):
    from chat import context as cc
    monkeypatch.setattr(cc, "HISTORY_FILE", str(tmp_path / "g.json"))
    monkeypatch.setattr(cc, "SETTINGS_FILE", str(tmp_path / "a.json"))
    monkeypatch.setattr(cc, "_hafiza", False)
    return tmp_path


def _toplayici():
    kutu = {"cevap": None, "hata": None, "kaynak": None}

    def cb(code):
        if not (code.startswith("BasakUI.bitir")
                or code.startswith("BasakUI.error")):
            return
        ic = code[code.index("(") + 1: code.rindex(")")]
        m = json.loads("[" + ic + "]")
        if code.startswith("BasakUI.bitir"):
            kutu["cevap"] = m[0]
            kutu["kaynak"] = m[1] if len(m) > 1 else None
        else:
            kutu["hata"] = m[0]
    return kutu, cb


class SayanBeyin:
    def __init__(self):
        self.cagri = 0

    def bulut_musait(self):
        return True

    def cevapla(self, mesajlar, model=None, tools=None, tool_choice=None,
                **kw):
        self.cagri += 1
        return {"content": "cevap %d" % self.cagri}, "sahte"


class KaydedenBeyin(SayanBeyin):
    def __init__(self):
        super().__init__()
        self.tercihler = []

    def cevapla(self, mesajlar, model=None, tools=None, tool_choice=None,
                tercih=None, **kw):
        self.tercihler.append(list(tercih) if tercih else None)
        return super().cevapla(mesajlar, model, tools, tool_choice, **kw)


class EskiBeyin:
    """tercih bilmeyen eski imza — akış kırılmamalı."""

    def __init__(self):
        self.cagri = 0

    def bulut_musait(self):
        return True

    def cevapla(self, mesajlar, model=None, tools=None, durum=None):
        self.cagri += 1
        return {"content": "eski %d" % self.cagri}, "sahte"


class TestTazele:
    def test_ayni_soru_tazeleyle_modele_yeniden_gider(self, izole):
        brain = SayanBeyin()
        _, cb1 = _toplayici()
        c.mesaj_isle("merhaba", brain, "SYS", cb1)
        assert brain.cagri == 1
        _, cb2 = _toplayici()
        c.mesaj_isle("merhaba", brain, "SYS", cb2)
        assert brain.cagri == 1, "normal tekrar onbellekten gelmeli"
        kutu3, cb3 = _toplayici()
        c.mesaj_isle("merhaba", brain, "SYS", cb3, tazele=True)
        assert brain.cagri == 2, "tazele onbellegi atlamali"
        assert kutu3["cevap"] == "cevap 2"

    def test_tazelesiz_davranis_degismedi(self, izole):
        brain = SayanBeyin()
        _, cb1 = _toplayici()
        c.mesaj_isle("merhaba", brain, "SYS", cb1)
        kutu2, cb2 = _toplayici()
        c.mesaj_isle("merhaba", brain, "SYS", cb2)
        assert kutu2["kaynak"] == "onbellek"


class TestTercih:
    def test_tercih_zincire_tasinir(self, izole):
        brain = KaydedenBeyin()
        _, cb = _toplayici()
        c.mesaj_isle("merhaba", brain, "SYS", cb,
                     tercih=["gemini", "groq"])
        assert brain.tercihler == [["gemini", "groq"]]

    def test_tercihsiz_cagri_ayni_kalir(self, izole):
        brain = KaydedenBeyin()
        _, cb = _toplayici()
        c.mesaj_isle("merhaba", brain, "SYS", cb)
        assert brain.tercihler == [None]

    def test_eski_imzali_beyin_kirilmaz(self, izole):
        brain = EskiBeyin()
        kutu, cb = _toplayici()
        c.mesaj_isle("merhaba", brain, "SYS", cb,
                     tercih=["gemini"], tazele=True)
        assert brain.cagri == 1
        assert kutu["cevap"] == "eski 1"


class TestTekrarTercihi:
    def test_begenilmeyen_en_sona_alinir(self):
        import app as app_modulu
        from brain import registry
        tercih = app_modulu._tekrar_tercihi("groq")
        assert tercih is not None
        assert "groq" not in tercih
        beklenen = [a for a in registry.VARSAYILAN_SIRA if a != "groq"]
        assert tercih == beklenen

    def test_bos_ve_bilinmeyen_normal_zincir(self):
        import app as app_modulu
        assert app_modulu._tekrar_tercihi("") is None
        assert app_modulu._tekrar_tercihi("olmayan-saglayici") is None
