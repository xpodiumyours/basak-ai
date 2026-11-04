# -*- coding: utf-8 -*-
"""Baglanti havuzu: surec basina TEK havuz, istek basina yeni TLS YOK.

Olcum (2026-11-04, uretim): her `psycopg.connect` yaklasik 8,8 sn
suruyordu ve sohbet yolunda birden fazla kez cagriliyordu; model
cagrilmadan once 50+ sn buradan geliyordu. Resmi kaynaklar (Vercel
connection pooling, psycopg3 ConnectionPool, Supabase pooler) havuzun
modul kapsaminda tutulmasini soyluyor.
"""

import ast
import os
import sys
from contextlib import contextmanager

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import chat.veritabani as vt


class SahteHavuz:
    kayitlar = []

    def __init__(self, **kw):
        self.kw = kw
        self.acildi = 0
        self.kapandi = 0
        self.baglanan = 0
        SahteHavuz.kayitlar.append(self)

    def open(self, *a, **k):
        self.acildi += 1

    def close(self):
        self.kapandi += 1

    @staticmethod
    def check_connection(_conn):
        return None

    @contextmanager
    def connection(self):
        self.baglanan += 1
        yield "baglanti"


@pytest.fixture
def sahte_havuz(monkeypatch):
    import psycopg_pool

    SahteHavuz.kayitlar = []
    monkeypatch.setattr(psycopg_pool, "ConnectionPool", SahteHavuz)
    monkeypatch.setattr(vt, "_POOL", None)
    monkeypatch.setattr(vt, "_POOL_DSN", "")
    monkeypatch.setattr(vt, "dsn", lambda: "postgresql://ornek/ornek")
    yield SahteHavuz
    monkeypatch.setattr(vt, "_POOL", None)
    monkeypatch.setattr(vt, "_POOL_DSN", "")


def test_tek_havuz_kurulur_ve_yeniden_kullanilir(sahte_havuz):
    with vt.baglanti() as conn:
        assert conn == "baglanti"
    with vt.baglanti() as conn:
        assert conn == "baglanti"

    assert len(sahte_havuz.kayitlar) == 1, "istek basina yeni havuz kurulmamali"
    havuz = sahte_havuz.kayitlar[0]
    assert havuz.acildi == 1
    assert havuz.baglanan == 2
    assert havuz.kw["min_size"] == 1
    assert havuz.kw["max_size"] >= 2, "max_size=1 eszamanli istekleri kilitler"
    assert havuz.kw["open"] is False
    assert havuz.kw["kwargs"]["autocommit"] is True
    assert havuz.kw["kwargs"]["prepare_threshold"] is None
    assert havuz.kw["check"] is not None, "donmus soket denetimi kapali olmamali"


def test_dsn_yoksa_acik_hata(monkeypatch):
    monkeypatch.setattr(vt, "_POOL", None)
    monkeypatch.setattr(vt, "_POOL_DSN", "")
    monkeypatch.setattr(vt, "dsn", lambda: "")
    with pytest.raises(RuntimeError):
        with vt.baglanti():
            pass


def test_havuz_gercek_modulde_tek_kez_olusturuluyor():
    """Kaynak duzeyinde kilit: `baglanti()` her cagride connect ETMEZ."""
    yol = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "chat", "veritabani.py")
    with open(yol, encoding="utf-8") as f:
        kaynak = f.read()
    assert "psycopg.connect(" not in kaynak, (
        "veritabani.py dogrudan connect etmemeli; havuz kullanmali")
    agac = ast.parse(kaynak)
    adlar = {d.name for d in ast.walk(agac) if isinstance(d, ast.FunctionDef)}
    assert "_havuz" in adlar and "baglanti" in adlar
