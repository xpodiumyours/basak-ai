"""olcum.py — Cerezsiz anonim sayfa sayaci + arac geri bildirimi.

Kural (gizlilik):
- Cerez YOK; kisi kimligi, IP veya tarayici bilgisi SAKLANMAZ.
- Yalniz (gun, sayfa yolu) toplam sayilari tutulur — anonim toplam veri.
- DNT/GPC sinyaline saygi: sinyal varsa hic sayilmaz (istemci + sunucu).
- Amac: "hangi sayfa/arac ise yariyor" sorusunu tahminle degil olcuyle
  yanitlamak (gelir + bakim karari).

Kalicilik: kota.py ile ayni desen — Postgres varsa atomik artis; yoksa
instance bellegi (local/preview/test) — soguk baslangicta sifirlanir.
"""

import os
import threading
import time

YOL_TAVAN = 120

# Bellek yedegi (Postgres yokken): (gun, yol) -> adet / (arti, eksi)
_bellek = {}
_bellek_oy = {}
_kilit = threading.Lock()
_tablo_hazir = False


def _gun():
    """UTC gunu — kota sayaclariyla ayni takvim."""
    return time.strftime("%Y-%m-%d", time.gmtime())


def _dsn_bul():
    for ad in ("DATABASE_URL", "POSTGRES_URL", "NEON_DATABASE_URL"):
        dsn = (os.environ.get(ad) or "").strip()
        if dsn:
            return dsn
    return ""


def yol_temizle(ham):
    """Yalniz site ici yol gecerli; sorgu/parca atilir, uzunluk sinirlanir."""
    yol = str(ham or "").strip()
    if not yol.startswith("/") or yol.startswith("//"):
        return ""
    yol = yol.split("?", 1)[0].split("#", 1)[0]
    if not yol or len(yol) > YOL_TAVAN:
        return ""
    return yol


def _tablolari_kur(conn):
    global _tablo_hazir
    if _tablo_hazir:
        return
    conn.execute(
        "CREATE TABLE IF NOT EXISTS basak_olcum ("
        " yol TEXT NOT NULL, gun TEXT NOT NULL, adet INT NOT NULL,"
        " PRIMARY KEY (yol, gun))")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS basak_oy ("
        " yol TEXT NOT NULL, gun TEXT NOT NULL,"
        " arti INT NOT NULL DEFAULT 0, eksi INT NOT NULL DEFAULT 0,"
        " PRIMARY KEY (yol, gun))")
    _tablo_hazir = True


def _pg_calistir(sql, params):
    """Postgres'te calistirir; baglanti yoksa/hata olursa None doner."""
    dsn = _dsn_bul()
    if not dsn:
        return None
    try:
        import psycopg
        with psycopg.connect(dsn, autocommit=True,
                             connect_timeout=5) as conn:
            _tablolari_kur(conn)
            return conn.execute(sql, params).fetchall()
    except Exception:
        return None


def _bellek_ekle(yol, gun):
    with _kilit:
        adet = _bellek.get((gun, yol), 0) + 1
        _bellek[(gun, yol)] = adet
        # Gun disi kayitlari ve tasma temizligi (cok basit GC).
        if len(_bellek) > 4096:
            for k in [k for k in _bellek if k[0] != gun][:2048]:
                _bellek.pop(k, None)
        return adet


def say(yol):
    """Sayfayi 1 artirir; yalniz gecerli site ici yol sayilir."""
    yol = yol_temizle(yol)
    if not yol:
        return False
    gun = _gun()
    satir = _pg_calistir(
        "INSERT INTO basak_olcum (yol, gun, adet) VALUES (%s, %s, 1) "
        "ON CONFLICT (yol, gun) DO UPDATE "
        "SET adet = basak_olcum.adet + 1 RETURNING adet",
        (yol, gun))
    if satir is None:
        _bellek_ekle(yol, gun)
    return True


def oy_ekle(yol, oy):
    """+1 / -1 mikro-geri bildirimi; diger degerler reddedilir."""
    yol = yol_temizle(yol)
    if not yol or oy not in (1, -1):
        return False
    gun = _gun()
    sutun = "arti" if oy == 1 else "eksi"
    satir = _pg_calistir(
        "INSERT INTO basak_oy (yol, gun, arti, eksi) VALUES (%s, %s, %s, %s) "
        "ON CONFLICT (yol, gun) DO UPDATE "
        "SET " + sutun + " = basak_oy." + sutun + " + 1 "
        "RETURNING " + sutun,
        (yol, gun, 1 if oy == 1 else 0, 1 if oy == -1 else 0))
    if satir is None:
        with _kilit:
            arti, eksi = _bellek_oy.get((gun, yol), (0, 0))
            if oy == 1:
                arti += 1
            else:
                eksi += 1
            _bellek_oy[(gun, yol)] = (arti, eksi)
    return True


def rapor(gun_sayisi=7):
    """Son N gunun en cok goruntulenen sayfalari ve oy toplamlari."""
    try:
        gun_sayisi = max(1, min(90, int(gun_sayisi)))
    except (TypeError, ValueError):
        gun_sayisi = 7
    esik = time.strftime(
        "%Y-%m-%d", time.gmtime(time.time() - (gun_sayisi - 1) * 86400))
    sayfalar = _pg_calistir(
        "SELECT yol, SUM(adet) FROM basak_olcum WHERE gun >= %s "
        "GROUP BY yol ORDER BY SUM(adet) DESC, yol LIMIT 50", (esik,))
    oylar = _pg_calistir(
        "SELECT yol, SUM(arti), SUM(eksi) FROM basak_oy WHERE gun >= %s "
        "GROUP BY yol ORDER BY SUM(arti) DESC, yol LIMIT 50", (esik,))
    if sayfalar is None:
        with _kilit:
            toplam = {}
            for (gun, yol), adet in _bellek.items():
                if gun >= esik:
                    toplam[yol] = toplam.get(yol, 0) + adet
            sayfalar = sorted(toplam.items(),
                              key=lambda kv: (-kv[1], kv[0]))[:50]
    if oylar is None:
        with _kilit:
            toplam_oy = {}
            for (gun, yol), (arti, eksi) in _bellek_oy.items():
                if gun >= esik:
                    a, e = toplam_oy.get(yol, (0, 0))
                    toplam_oy[yol] = (a + arti, e + eksi)
            oylar = sorted(
                [(yol, t[0], t[1]) for yol, t in toplam_oy.items()],
                key=lambda x: (-x[1], x[0]))[:50]
    return {"gun_sayisi": gun_sayisi, "esik": esik,
            "sayfalar": [[y, int(s)] for y, s in sayfalar],
            "oylar": [[y, int(a), int(e)] for y, a, e in oylar]}


def sifirla():
    """Testler icin bellek sayaclarini temizler."""
    global _tablo_hazir
    with _kilit:
        _bellek.clear()
        _bellek_oy.clear()
    _tablo_hazir = False
