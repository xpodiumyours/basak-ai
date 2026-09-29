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

# ---------------------------------------------------------------------
# KIMLIKSIZ GUNLUK TAVAN (2026-09-30, Casper karari)
# ---------------------------------------------------------------------
# SORU: kotu kullanimi durdururken kisisel veri URETMEYEN koruma nasil
# olur?  CEVAP: kimlige BAKMAK. IP, cerez ya da oturum kullanilirsa
# sayaç kisisel veriye baglanir ve tum KVKK beyani (cerez.html,
# gizlilik.html, KVKK-ENVANTER.md) tutarsiz hale gelir.
#
# Buradaki tavan GLOBAL ve KIMLIKSIZDIR: "bugun toplam N olaydan
# sonra kapat". Bu da spam'i durdurur (saldirgan da ayni kovadan
# icer) ama HICBIR kisi hakkinda veri tutmaz. Bozulan tek sey veri
# kalitesidir — kisinin degil.
#
# kota.py ile ayni desen: Postgres varsa atomik, yoksa bellek yedegi.
VARSAYILAN_GUNLUK_TAVAN = 20000

def _tavan_env():
    """Gunluk olay tavani — env ile ayarlanabilir (test/preview icin)."""
    ham = (os.environ.get("BASAK_OLCUM_GUNLUK_TAVAN") or "").strip()
    try:
        deger = int(ham)
        return max(1, deger) if deger > 0 else VARSAYILAN_GUNLUK_TAVAN
    except ValueError:
        return VARSAYILAN_GUNLUK_TAVAN

# Bellek yedegi (Postgres yokken): gun -> oy/olay toplami
_bellek_tavan = {}

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
    # Kimliksiz gunluk tavan sayaci (bkz. basinda gerekce).
    conn.execute(
        "CREATE TABLE IF NOT EXISTS basak_olcum_tavan ("
        " gun TEXT PRIMARY KEY, adet INT NOT NULL)")
    _tablo_hazir = True


def _tavan_artir():
    """Gunluk olay sayacini 1 artirir; (toplam, tavan) dondurur.

    Kimlik YOK: tek bir global gun sayaci. Kimseyle eslestirilmez.
    """
    gun = _gun()
    t = _tavan_env()
    satir = _pg_calistir(
        "INSERT INTO basak_olcum_tavan (gun, adet) VALUES (%s, 1) "
        "ON CONFLICT (gun) DO UPDATE "
        "SET adet = basak_olcum_tavan.adet + 1 RETURNING adet", (gun,))
    if satir is None:
        with _kilit:
            adet = _bellek_tavan.get(gun, 0) + 1
            _bellek_tavan[gun] = adet
            # Gun disi kayitlari temizle
            for k in [k for k in _bellek_tavan if k != gun]:
                _bellek_tavan.pop(k, None)
    else:
        adet = int(satir[0][0]) if satir and satir[0] is not None else 0
    return adet, t


def tavan_kontrol():
    """(izin, kalan) — tavan asilmadiysa True. Cevap kalitesi icin."""
    adet, t = _tavan_artir()
    return adet <= t, max(0, t - adet)


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
    """Sayfayi 1 artirir; yalniz gecerli site ici yol sayilir.

    Tavan asildiysa yine True doner ama SAYMAZ: kotu kullanim veriyi
    bozmaz, yalniz biriktirmeyi durdurur (kimliksiz global koruma).
    """
    yol = yol_temizle(yol)
    if not yol:
        return False
    izin, _ = tavan_kontrol()
    if not izin:
        return True
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
    """+1 / -1 mikro-geri bildirimi; diger degerler reddedilir.

    Tavan asildiysa False doner: oy bozulunca gelir/bakim karari
    bozulur — bu yuzden geri bildirim tavana gore daha korunur.
    """
    yol = yol_temizle(yol)
    if not yol or oy not in (1, -1):
        return False
    izin, _ = tavan_kontrol()
    if not izin:
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
        _bellek_tavan.clear()
    _tablo_hazir = False
