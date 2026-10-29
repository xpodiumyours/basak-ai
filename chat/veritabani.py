"""chat/veritabani.py — tek veritabani girisi ve sema surumleri.

Neden bu modul: sohbet gecmisi, hatirlatmalar, kosu defteri, platform
kosulari ve isci kuyrugu ayni Postgres'i kullaniyor ama her modul kendi
tablosunu `CREATE TABLE IF NOT EXISTS` ile aciyordu. Sirali, surumlu ve
tek yerden uygulanan bir sema yoktu; bu yuzden "tablo yok" durumlari
(ornegin isci kuyrugu) sessizce kapali kaliyordu.

Kural (AGENTS.md §0): bu modul KARAR VERMEZ, kullanici metnine bakmaz.
Yalniz baglanti ve sema yonetimi yapar.

Kullanim:
    from chat import veritabani
    if veritabani.hazirla(): ...
    with veritabani.baglanti() as conn: ...

DSN yoksa (masaustu) `hazir()` False doner; cagiran katman dosya/SQLite
yoluna duser. Uretimde DSN yoksa memory katmani zaten acik hata verir.
"""

import logging
import threading

logger = logging.getLogger(__name__)

SURUM_TABLO = "basak_sema"

# Surumlu sema. Her surum TEK KEZ uygulanir; ifadeler idempotent yazilir
# (IF NOT EXISTS) ki yarim kalan bir kosu tekrar denenebilsin.
MIGRASYONLAR = (
    (1, (
        "CREATE TABLE IF NOT EXISTS %s ("
        "surum INTEGER PRIMARY KEY, "
        "uygulandi TIMESTAMPTZ NOT NULL DEFAULT now())" % SURUM_TABLO,
        # Sohbet gecmisi: yalniz ekleme (append-only). Boylece iki ornek
        # ayni anda yazsa bile oku-degistir-yaz kaybi olmaz.
        "CREATE TABLE IF NOT EXISTS basak_sohbet_mesaj ("
        "seq BIGSERIAL PRIMARY KEY, "
        "kullanici TEXT NOT NULL, "
        "rol TEXT NOT NULL, "
        "icerik TEXT NOT NULL, "
        "oturum TEXT NOT NULL DEFAULT '', "
        "olustu TIMESTAMPTZ NOT NULL DEFAULT now())",
        "CREATE INDEX IF NOT EXISTS basak_sohbet_mesaj_kullanici "
        "ON basak_sohbet_mesaj (kullanici, seq)",
        # Hatirlatmalar: Vercel'de /tmp kayboldugu icin kalici depo zorunlu.
        "CREATE TABLE IF NOT EXISTS basak_hatirlatma ("
        "id TEXT PRIMARY KEY, "
        "kullanici TEXT NOT NULL, "
        "metin TEXT NOT NULL, "
        "zaman DOUBLE PRECISION NOT NULL, "
        "olusturma DOUBLE PRECISION NOT NULL, "
        "gonderildi BOOLEAN NOT NULL DEFAULT FALSE, "
        "goruldu BOOLEAN NOT NULL DEFAULT FALSE)",
        "CREATE INDEX IF NOT EXISTS basak_hatirlatma_kullanici "
        "ON basak_hatirlatma (kullanici, zaman)",
        "CREATE INDEX IF NOT EXISTS basak_hatirlatma_zaman "
        "ON basak_hatirlatma (zaman) WHERE gonderildi = FALSE",
    )),
)

_KILIT = threading.Lock()
_HAZIR = False
_SON_HATA = 0.0
_HATA_ARALIGI = 60.0


def dsn():
    """Kalici veritabani DSN'i; yoksa bos metin.

    Kuyruk defteriyle AYNI cozumleme kullanilir (preview izolasyonu dahil):
    iki ayri DSN kurali, iki ayri veritabanina yazmak demekti.
    """
    try:
        from chat.kosu_deposu import _dsn
        return _dsn()
    except RuntimeError:
        raise
    except Exception:
        logger.debug("veritabani DSN cozulemedi", exc_info=True)
        return ""


def hazir():
    """DSN ve surucu varsa True (baglanti denenmez)."""
    try:
        if not dsn():
            return False
    except RuntimeError:
        return False
    try:
        import psycopg  # noqa: F401
    except ImportError:
        return False
    return True


def baglanti():
    """Autocommit baglanti dondurur (cagiran `with` ile kapatir)."""
    import psycopg
    conn = psycopg.connect(dsn(), autocommit=True, connect_timeout=10)
    try:
        conn.prepare_threshold = None
    except Exception:
        logger.debug("prepare_threshold ayarlanamadi", exc_info=True)
    return conn


def hazirla(zorla=False):
    """Sema surumlerini uygular. Basariliysa True; hata sessiz yutulmaz.

    Tek surec icinde bir kez denenir (zorla=True tekrar dener). Farkli
    ornekler ayni anda kalksa bile advisory lock siraya sokar.
    """
    global _HAZIR, _SON_HATA
    import time as _zaman
    if _HAZIR and not zorla:
        return True
    if not hazir():
        return False
    if not zorla and _SON_HATA and _zaman.monotonic() - _SON_HATA < _HATA_ARALIGI:
        # Baglanti az once basarisiz oldu: her istekte 10 sn beklemek
        # yerine kisa bir geri cekilme uygulanir.
        return False
    with _KILIT:
        if _HAZIR and not zorla:
            return True
        try:
            with baglanti() as conn:
                with conn.cursor() as cur:
                    # An already deployed schema must not wait behind an old
                    # session lock on a transaction-pooled serverless endpoint.
                    if not zorla:
                        cur.execute('SELECT to_regclass(%s)', (SURUM_TABLO,))
                        if cur.fetchone()[0] is not None:
                            cur.execute('SELECT surum FROM %s' % SURUM_TABLO)
                            done = {int(row[0]) for row in cur.fetchall()}
                            if all(version in done for version, _ in MIGRASYONLAR):
                                _HAZIR, _SON_HATA = True, 0.0
                                return True
                    # Session locks cannot be paired safely across PgBouncer
                    # transactions. Bind both the lock and DDL to this transaction.
                    with conn.transaction():
                        cur.execute("SELECT pg_advisory_xact_lock(hashtext('basak.sema.v1'))")
                        cur.execute(
                            "CREATE TABLE IF NOT EXISTS %s ("
                            "surum INTEGER PRIMARY KEY, "
                            "uygulandi TIMESTAMPTZ NOT NULL DEFAULT now())"
                            % SURUM_TABLO)
                        cur.execute("SELECT surum FROM %s" % SURUM_TABLO)
                        uygulanan = {int(satir[0]) for satir in cur.fetchall()}
                        for surum, ifadeler in MIGRASYONLAR:
                            if surum in uygulanan:
                                continue
                            for ifade in ifadeler:
                                cur.execute(ifade)
                            cur.execute(
                                "INSERT INTO %s (surum) VALUES (%%s) "
                                "ON CONFLICT (surum) DO NOTHING" % SURUM_TABLO,
                                (surum,))
                            logger.info("Sema surumu uygulandi: %s", surum)
            _HAZIR = True
            _SON_HATA = 0.0
            return True
        except Exception:
            _SON_HATA = _zaman.monotonic()
            logger.warning("Sema hazirlanamadi", exc_info=True)
            return False


def surum_bilgisi():
    """Diagnostik: uygulanan surumler ve bekleyenler."""
    bilgi = {"hazir": False, "uygulanan": [], "bekleyen":
             [s for s, _ in MIGRASYONLAR]}
    if not hazir():
        return bilgi
    try:
        with baglanti() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT surum FROM %s ORDER BY surum" % SURUM_TABLO)
                uygulanan = [int(satir[0]) for satir in cur.fetchall()]
        bilgi.update({"hazir": True, "uygulanan": uygulanan,
                      "bekleyen": [s for s, _ in MIGRASYONLAR
                                   if s not in uygulanan]})
    except Exception:
        logger.debug("sema surumu okunamadi", exc_info=True)
    return bilgi


if __name__ == "__main__":  # pragma: no cover - elle calistirma
    logging.basicConfig(level=logging.INFO)
    tamam = hazirla(zorla=True)
    print("sema:", "hazir" if tamam else "BASARISIZ",
          surum_bilgisi() if tamam else "")
    raise SystemExit(0 if tamam else 1)
