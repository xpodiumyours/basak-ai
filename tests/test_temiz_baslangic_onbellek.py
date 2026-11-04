# -*- coding: utf-8 -*-
"""Temiz baslangic kontrolu surec basina BIR kez DB'ye gider.

Olcum (2026-11-04, uretim): tek Postgres gidis-donusu ~8,8 sn
(/api/durum). Bu kontrol her istekte calisiyordu; sohbetin model
oncesi 50+ sn'sinin onemli parcasi buydu. Sonuc idempotent ve advisory
lock'lu oldugu icin surec omru boyunca degismez.
"""

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_modulu


class SahteCursor:
    def execute(self, *args, **kwargs):
        return None

    def fetchone(self):
        # "zaten yapildi" isareti: temizlik tekrar kosmaz.
        return ("true",)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class SahteConn:
    def __init__(self):
        self.prepare_threshold = None
        self.commits = 0

    def cursor(self):
        return SahteCursor()

    def commit(self):
        self.commits += 1

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _hazirla(monkeypatch):
    import kullanici as kullanici_modulu
    import psycopg

    monkeypatch.setenv("DATABASE_URL", "postgresql://ornek/ornek")
    monkeypatch.setattr(kullanici_modulu, "uretim_mi", lambda: True)
    monkeypatch.setattr(app_modulu, "_SIFIRLAMA_TAMAM", False)
    baglantilar = []

    def _connect(*args, **kwargs):
        c = SahteConn()
        baglantilar.append(c)
        return c

    monkeypatch.setattr(psycopg, "connect", _connect)
    return baglantilar


def test_ikinci_cagri_veritabanina_gitmez(monkeypatch):
    baglantilar = _hazirla(monkeypatch)

    assert app_modulu._hafizayi_bir_kez_sifirla() is True
    assert len(baglantilar) == 1

    # Surec icindeki sonraki istekler: DB'ye tekrar gidilmez.
    assert app_modulu._hafizayi_bir_kez_sifirla() is True
    assert app_modulu._hafizayi_bir_kez_sifirla() is True
    assert len(baglantilar) == 1


def test_uretim_disi_hizli_doner(monkeypatch):
    import kullanici as kullanici_modulu

    monkeypatch.setattr(kullanici_modulu, "uretim_mi", lambda: False)
    monkeypatch.setattr(app_modulu, "_SIFIRLAMA_TAMAM", False)
    assert app_modulu._hafizayi_bir_kez_sifirla() is True
