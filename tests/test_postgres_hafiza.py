"""Postgres hafiza adaptoru — kota/ag kullanmayan sozlesme testleri."""

import os
import json

import pytest

from memory.engine import HafizaMotoru as SQLiteHafizaMotoru
from memory.postgres import PostgresHafizaMotoru, _arama_kelimeleri, _vektor_metni


YUZ = (
    "ekle", "episodik_temizle", "episodik_kaydet", "kaynak_sil",
    "kaynak_satir", "meta_al", "meta_koy", "say", "ara",
    "vektorleri_temizle", "kapat",
)


def test_postgres_dis_yuzu_sqlite_ile_ayni_11_metodu_tasir():
    for ad in YUZ:
        assert callable(getattr(SQLiteHafizaMotoru, ad, None)), ad
        assert callable(getattr(PostgresHafizaMotoru, ad, None)), ad


def test_postgres_arama_sozlesmesi():
    assert _arama_kelimeleri("Vixrex ve hafıza için Casper") == [
        "vixrex", "hafıza", "casper"]
    assert _vektor_metni([1.0, 2.0]) is None
    assert _vektor_metni([0.0] * 768).startswith("[")


def test_uretimde_db_yoksa_gecici_sqlitea_dusmez(monkeypatch):
    import memory
    monkeypatch.setenv("VERCEL", "1")
    for ad in ("DATABASE_URL", "POSTGRES_URL", "NEON_DATABASE_URL"):
        monkeypatch.delenv(ad, raising=False)
    with pytest.raises(RuntimeError, match="kalici hafiza"):
        memory.HafizaMotoru(embed_fn=None)


def test_uretimde_postgres_fabrikasi_secilir(monkeypatch):
    import memory
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("DATABASE_URL", "postgresql://ornek")
    gorulen = {}

    def sahte(dsn, embed_fn):
        gorulen["dsn"] = dsn
        gorulen["embed_fn"] = embed_fn
        return "PG"

    monkeypatch.setattr(memory, "_postgres_motor", sahte)
    fn = lambda x: None
    assert memory.HafizaMotoru(embed_fn=fn) == "PG"
    assert gorulen == {"dsn": "postgresql://ornek", "embed_fn": fn}


def test_bulut_motoru_vektor_yenilemeyi_kendi_yapar(monkeypatch):
    from chat import context as cc

    class SahteBulut:
        _embed_fn = object()
        def _vektor_uzayi_sagla(self, damga, limit):
            return (damga, limit)

    monkeypatch.setattr(cc, "VEKTOR_UZAYI", "deneme-uzayi")
    assert cc._vektor_uzay_sagla(SahteBulut()) == (
        "deneme-uzayi", cc._GERI_DOLDURMA_TAVAN)


def test_veri_sorgulari_kullanici_kimligini_tasir(monkeypatch):
    import sys
    import types

    durum = {"calls": [], "connect": []}

    class Cursor:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def execute(self, sql, params=None):
            q = " ".join(sql.split())
            durum["calls"].append((q, params))
            if "SELECT COUNT(*) FROM basak_memories WHERE user_id=%s" in q:
                self.rows = [(1,)]
            elif "SELECT to_regclass(%s)" in q:
                self.rows = [(None,)]
            elif "SELECT deger FROM basak_memory_meta" in q:
                self.rows = []
            else:
                self.rows = []
        def fetchone(self):
            return self.rows[0] if self.rows else None
        def fetchall(self):
            return list(self.rows)

    class Conn:
        prepare_threshold = 5
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def cursor(self):
            return Cursor()
        def commit(self):
            pass
        def rollback(self):
            pass

    sahte = types.ModuleType("psycopg")
    def baglan(dsn, autocommit=False, connect_timeout=10):
        durum["connect"].append((dsn, autocommit, connect_timeout))
        return Conn()
    sahte.connect = baglan
    monkeypatch.setitem(sys.modules, "psycopg", sahte)

    motor = PostgresHafizaMotoru("postgresql://fake", "ayse", embed_fn=None)
    assert motor.say() == 1

    veri = [(q, p) for q, p in durum["calls"]
            if "basak_memories" in q and q.startswith(("SELECT", "INSERT", "UPDATE", "DELETE"))]
    assert veri
    assert all((p is None) or ("ayse" in p)
               for q, p in veri)


def test_temiz_baslangic_eski_anilari_bir_kez_siler(monkeypatch):
    """61 eski kayıt ve mevcut hafıza silinir; ikinci açılış tekrar silmez."""
    import sys
    import types

    durum = {"marker": False, "memory_deleted": 0, "legacy_deleted": 0}

    class Cursor:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def execute(self, sql, params=None):
            q = " ".join(sql.split())
            if "SELECT deger FROM basak_memory_meta" in q:
                self.rows = [(json.dumps(True),)] if durum["marker"] else []
            elif "SELECT to_regclass(%s)" in q:
                ad = params[0]
                self.rows = [(ad if ad == "basak.anilar" else None,)]
            elif q == "DELETE FROM basak_memories":
                durum["memory_deleted"] += 1
                self.rows = []
            elif q == 'DELETE FROM "basak"."anilar"':
                durum["legacy_deleted"] += 1
                self.rows = []
            elif q.startswith("INSERT INTO basak_memory_meta") and params and params[0] == "__system__":
                durum["marker"] = True
                self.rows = []
            elif "SELECT COUNT(*) FROM basak_memories" in q:
                self.rows = [(0,)]
            else:
                self.rows = []
        def fetchone(self):
            return self.rows[0] if self.rows else None
        def fetchall(self):
            return list(self.rows)

    class Conn:
        prepare_threshold = 5
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def cursor(self):
            return Cursor()
        def commit(self):
            pass
        def rollback(self):
            pass

    sahte = types.ModuleType("psycopg")
    sahte.connect = lambda *a, **k: Conn()
    monkeypatch.setitem(sys.modules, "psycopg", sahte)

    PostgresHafizaMotoru("postgresql://fake", "u1111111111111111", embed_fn=None)
    assert durum["memory_deleted"] == 1
    assert durum["legacy_deleted"] == 1
    assert durum["marker"] is True

    PostgresHafizaMotoru("postgresql://fake", "u2222222222222222", embed_fn=None)
    assert durum["memory_deleted"] == 1
    assert durum["legacy_deleted"] == 1
