"""tests/test_hafiza_araci.py — Derin hafiza arama guvencesi.

Sozlesme: uc yerde bagli; sonuclar tam metin (kirpma yok);
gercek hafizaya DOKUNULMAZ (motor sahte).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import calistir, hafiza
from tools.definitions import TANINMIS_TOOLLAR


class SahteMotor:
    def ara(self, sorgu, limit=4):
        assert limit == 5
        if sorgu == "bos":
            return []
        return [{"text": "uzun kayit " + "x" * 500}]


class TestUcYer:
    def test_beyaz_listede(self):
        assert "hafiza_ara" in TANINMIS_TOOLLAR

    def test_durum_etiketi_var(self):
        from chat.tools import DURUM_METNI
        assert "hafiza_ara" in DURUM_METNI


class TestArama:
    def test_tam_metin_doner(self, monkeypatch):
        from chat import context as cc
        monkeypatch.setattr(cc, "_hafiza", SahteMotor())
        r = hafiza.hafiza_ara("konu")
        assert "result" in r, r
        assert "x" * 500 in r["result"]  # kirpma yok

    def test_bulunamadi_ve_bos(self, monkeypatch):
        from chat import context as cc
        monkeypatch.setattr(cc, "_hafiza", SahteMotor())
        assert "bulunamadi" in hafiza.hafiza_ara("bos")["result"]
        assert "error" in hafiza.hafiza_ara("   ")

    def test_motor_yoksa_hata(self, monkeypatch):
        from chat import context as cc
        monkeypatch.setattr(cc, "_hafiza", False)
        assert "error" in hafiza.hafiza_ara("konu")

    def test_calistir_hatti(self, monkeypatch):
        from chat import context as cc
        monkeypatch.setattr(cc, "_hafiza", SahteMotor())
        r = calistir("hafiza_ara", {"sorgu": "konu"})
        assert "result" in r
