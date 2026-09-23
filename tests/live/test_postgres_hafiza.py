"""Canli Neon kabul testi — normal pytest paketinde kosmaz.

Gercek DB'ye yalniz benzersiz test kullanicisi yazar; Casper verisine dokunmaz.
"""

import os
import uuid

import pytest


def test_neon_kapat_ac_hatirlar_ve_kullaniciyi_karistirmaz():
    dsn = (os.environ.get("DATABASE_URL") or "").strip()
    if not dsn:
        pytest.skip("DATABASE_URL yok")

    from memory.postgres import PostgresHafizaMotoru

    benzersiz = uuid.uuid4().hex[:12]
    kisi = "canli-hafiza-" + benzersiz
    diger = "canli-diger-" + benzersiz
    soru = "Kabul anahtarim %s" % benzersiz
    cevap = "Bulutta kalici"

    m1 = PostgresHafizaMotoru(dsn, kisi, embed_fn=None)
    assert m1.episodik_kaydet(soru, cevap) is True
    m1.kapat()

    m2 = PostgresHafizaMotoru(dsn, kisi, embed_fn=None)
    bulunan = m2.ara("Kabul anahtarim %s" % benzersiz, limit=5)
    assert any(benzersiz in (x.get("text") or "") for x in bulunan)

    m3 = PostgresHafizaMotoru(dsn, diger, embed_fn=None)
    baskasi = m3.ara("Kabul anahtarim %s" % benzersiz, limit=5)
    assert not any(benzersiz in (x.get("text") or "") for x in baskasi)

    # Yalniz test kullanicisinin episodik kaydini temizle.
    assert m2.episodik_temizle() >= 1
