"""tests/test_isci_kuyrugu_postgres.py — gerçek Postgres üzerinde kuyruk.

SQLite testleri tek yazıcı davranışını ölçer; üretimde kuyruk Postgres'tir
ve iki işçi farklı makinelerden aynı anda gelebilir. Burada `FOR UPDATE
SKIP LOCKED` ile atomik alma, kalıcı nonce ve kalp özeti gerçek sunucuda
ölçülür.

Test DSN'i yoksa dosya atlanır. CI'da `.github/workflows/bulut-iscisi.yml`
Postgres servisini açar ve `BASAK_TEST_DATABASE_URL` verir. Test kendi
tablolarını kurar/siler; paylaşılan `basak_kosu` tablolarına dokunmaz.
"""

import os
import threading
import time

import pytest

psycopg = pytest.importorskip("psycopg")

from worker import kuyruk as kq  # noqa: E402
from worker.guvenlik import token_uret  # noqa: E402

DSN = (os.environ.get("BASAK_TEST_DATABASE_URL") or "").strip()

pytestmark = pytest.mark.skipif(
    not DSN, reason="BASAK_TEST_DATABASE_URL yok")

TABLOLAR = (kq.IS_TABLO, kq.KALP_TABLO, kq.NONCE_TABLO)
ANAHTAR = "test-iscisi-anahtari-32-bayt"
URL = "https://ornek.test/sayfa"


def _tablolari_sil():
    with psycopg.connect(DSN, autocommit=True) as conn:
        with conn.cursor() as cur:
            for tablo in TABLOLAR:
                cur.execute("DROP TABLE IF EXISTS %s CASCADE" % tablo)


@pytest.fixture(autouse=True)
def _temiz_veritabani():
    _tablolari_sil()
    yield
    _tablolari_sil()


def _birak(kuyruk, adim="a1", kosu="kosu-1"):
    eylem = {"tur": "oku", "secici": "#icerik"}
    token, _ = token_uret(
        ANAHTAR, kosu_id=kosu, adim_id=adim, tur="oku", url=URL,
        argumanlar=eylem)
    return kuyruk.birak(kosu, adim, eylem, token, URL)


def test_postgres_kuyrugu_kurar_ve_is_akisini_yazar():
    kuyruk = kq.Kuyruk(dsn=DSN)
    assert kuyruk.ad == "postgres"
    birakilan = _birak(kuyruk)
    assert birakilan["durum"] == "bekliyor"

    alinan = kuyruk.al("isci-1")
    assert alinan["id"] == birakilan["id"]
    assert alinan["deneme"] == 1

    bitti = kuyruk.bitir(alinan["id"], "isci-1", {"ok": True, "metin": "x"})
    assert bitti["durum"] == "bitti"

    # Yeni süreç aynı satırı görür: kuyruk bellekte değil.
    yeniden = kq.Kuyruk(dsn=DSN)
    satir = yeniden.oku(birakilan["id"])
    assert satir["durum"] == "bitti"
    assert '"metin":"x"' in satir["sonuc"]


def test_postgres_iki_iscide_ayni_isi_alamaz():
    k1 = kq.Kuyruk(dsn=DSN)
    k2 = kq.Kuyruk(dsn=DSN)
    _birak(k1, adim="a1")
    _birak(k1, adim="a2")

    sonuc = []
    kilit = threading.Lock()

    def al(kuyruk, ad):
        satir = kuyruk.al(ad)
        with kilit:
            sonuc.append(satir)

    p1 = threading.Thread(target=al, args=(k1, "isci-1"))
    p2 = threading.Thread(target=al, args=(k2, "isci-2"))
    p1.start()
    p2.start()
    p1.join(timeout=20)
    p2.join(timeout=20)
    assert not p1.is_alive() and not p2.is_alive()

    alinan = [s for s in sonuc if s]
    assert len(alinan) == 2
    assert len({s["id"] for s in alinan}) == 2
    assert {s["isci"] for s in alinan} == {"isci-1", "isci-2"}
    assert k1.al("isci-3") is None


def test_postgres_kalp_ve_nonce_yeniden_baslatmaya_dayanir():
    k1 = kq.Kuyruk(dsn=DSN)
    k1.kalp("isci-1", durum="hazir", surum="abc", simdi=1_000)
    assert k1.nonce_al("n-1", 2_000, simdi=1_001) is True

    k2 = kq.Kuyruk(dsn=DSN)
    assert k2.nonce_al("n-1", 2_000, simdi=1_002) is False
    canli = k2.canli_isciler(esik=90, simdi=1_010)
    assert len(canli) == 1
    assert canli[0]["isci"] == "isci-1"
    assert canli[0]["surum"] == "abc"

    assert k2.canli_isciler(esik=90, simdi=2_000) == []


def test_postgres_coken_iscinin_isi_supheli_olur():
    simdi = 1_000.0
    kuyruk = kq.Kuyruk(dsn=DSN)
    _birak(kuyruk)
    alinan = kuyruk.al("isci-1", simdi=simdi)
    kuyruk.kalp("isci-1", simdi=simdi)

    assert kuyruk.temizle(esik=90, simdi=simdi + 10) == 0
    assert kuyruk.temizle(esik=90, simdi=simdi + 200) == 1
    assert kuyruk.oku(alinan["id"])["durum"] == "supheli"


def test_postgres_ozet_gercek_sayilari_doner():
    kuyruk = kq.Kuyruk(dsn=DSN)
    _birak(kuyruk, adim="a1")
    _birak(kuyruk, adim="a2")
    kuyruk.kalp("isci-1", simdi=time.time())

    ozet = kuyruk.ozet()
    assert ozet["bekliyor"] == 2
    assert ozet["canli"] == 1
    assert ozet["isciler"][0]["isci"] == "isci-1"
