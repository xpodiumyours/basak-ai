"""tests/test_ollama_bagimsizlik.py — Ollama kapaliyken bulutla sohbet.

2026-08-24'te Casper'in buldugu hata: mesaj_isle() brain.yerel_modeller()
bos oldugunda HEMEN hata donuyordu; Groq/GLM/NVIDIA/Kilo hazir olsa bile
sohbet yolu kesiliyordu. Oysa mimaride Ollama SON CARE, on kosul degil.
boot() da ok'u yalniz yerel modele bagliyordu.

Kural: dur yalnizca "yerel YOK ve bulut YOK" iken gelir.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json

import pytest

import chat as c


class BulutluBrain:
    """Yerel modeli yok; bulut zinciri ayakta (sahte)."""

    def __init__(self, cevap="buluttan cevap"):
        self._cevap = cevap
        self.gelen_yerel_model = None

    def yerel_modeller(self):
        return []

    def bulut_musait(self):
        return True

    def cevapla(self, messages, yerel_model, tools=None,
                override_model=None):
        self.gelen_yerel_model = yerel_model   # None gelebilir (tam bulut)
        return {"content": self._cevap}, "groq"


class CeholBrain:
    def yerel_modeller(self):
        return []

    def bulut_musait(self):
        return False

    def cevapla(self, *a, **kw):
        raise AssertionError("hicbir beyin yokken cagrilMAMALI")


def _toplayici():
    kutu = {"cevap": None, "hata": None}

    def cb(code):
        if not (code.startswith("BasakUI.reply")
                or code.startswith("BasakUI.error")):
            return   # thinking/toolStatus gibi diger UI cagrilarini yoksay
        ic = code[code.index("(") + 1: code.rindex(")")]
        m = json.loads("[" + ic + "]")
        if code.startswith("BasakUI.reply"):
            kutu["cevap"] = m[0]
        else:
            kutu["hata"] = m[0]
    return kutu, cb


@pytest.fixture
def izole(monkeypatch, tmp_path):
    monkeypatch.setattr(c, "HISTORY_FILE", str(tmp_path / "g.json"))
    monkeypatch.setattr(c, "SETTINGS_FILE", str(tmp_path / "a.json"))
    monkeypatch.setattr(c, "_hafiza", False)
    return tmp_path


class TestOllamaBagimsizlik:
    def test_ollama_kapali_bulut_acik_sohbet_surer(self, izole):
        brain = BulutluBrain()
        kutu, cb = _toplayici()
        c.mesaj_isle("merhaba nasilsin?", brain, "SYS", cb, None)
        assert kutu["hata"] is None
        assert kutu["cevap"] == "buluttan cevap"
        assert brain.gelen_yerel_model is None

    def test_hicbir_beyin_yoksa_durur(self, izole):
        kutu, cb = _toplayici()
        c.mesaj_isle("merhaba", CeholBrain(), "SYS", cb, None)
        assert kutu["cevap"] is None
        assert "beyin" in (kutu["hata"] or "")


class TestBoot:
    def test_boot_ok_bulutla_acilir(self, monkeypatch):
        import basak_app

        api = basak_app.Api.__new__(basak_app.Api)   # Brain'siz kurulum

        class Sahte:
            def yerel_modeller(self):
                return []
            def bulut_musait(self):
                return True

        api.brain = Sahte()
        api.tts_on = False
        monkeypatch.setattr(api, "bugunku_hatirlatmalar",
                            lambda: {"result": ""})
        r = api.boot()
        assert r["ok"] is True and r["cloud"] is True and r["models"] == []

    def test_boot_ok_hicbiri_yoksa_false(self, monkeypatch):
        import basak_app

        api = basak_app.Api.__new__(basak_app.Api)

        class Sahte:
            def yerel_modeller(self):
                return []
            def bulut_musait(self):
                return False

        api.brain = Sahte()
        api.tts_on = False
        monkeypatch.setattr(api, "bugunku_hatirlatmalar",
                            lambda: {"result": ""})
        r = api.boot()
        assert r["ok"] is False
