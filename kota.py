"""kota.py — Anonim gunluk sohbet kotasi (ucretsiz zinciri korur).

Kural: kayit zorunlu degil (Basak ID); her anonim ID gununde belirli
mesaj hakkindir. Token sahibi (X-Basak-Token / BASAK_WEB_TOKEN) kotasizdir.

Bu MODEL DARALTMA DEGILDIR (CHATBOT-YASAGI kapsamı disi):
- Karar istegin BASINDA, model calismadan_once verilir.
- Cevap akisina, arac secimine, tur sayisina, gecmise dokunmaz.
- Amac ucretsiz saglayici zincirinin gunluk kotasinin tek bir
  kullanici tarafindan tuketilmemesidir.

Kalıcilik: Postgres varsa atomik artis (Vercel'de dogru yer); yoksa
instance bellegi (local/preview/test) — soguk baslangicta sifirlanir.
"""

import os
import threading
import time

VARSAYILAN_TAVAN = 50

# Bellek yedegi (Postgres yokken): kid -> (gun, adet)
_bellek = {}
_kilit = threading.Lock()
_tablo_hazir = False


def tavan():
    """Gunluk tavan — env ile ayarlanabilir (test/preview icin)."""
    ham = (os.environ.get("BASAK_ANONIM_KOTA_TAVAN") or "").strip()
    try:
        deger = int(ham)
        return max(1, deger) if deger > 0 else VARSAYILAN_TAVAN
    except ValueError:
        return VARSAYILAN_TAVAN


def _gun():
    """UTC gunu — saglayici kotalari da UTC sifirlanir."""
    return time.strftime("%Y-%m-%d", time.gmtime())


def _dsn_bul():
    for ad in ("DATABASE_URL", "POSTGRES_URL", "NEON_DATABASE_URL"):
        dsn = (os.environ.get(ad) or "").strip()
        if dsn:
            return dsn
    return ""


def _pg_ekle(kid, gun):
    """Postgres'te atomik artir; calismazsa None (bellege dusulur)."""
    global _tablo_hazir
    dsn = _dsn_bul()
    if not dsn:
        return None
    try:
        import psycopg
        with psycopg.connect(dsn, autocommit=True, connect_timeout=5) as conn:
            if not _tablo_hazir:
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS basak_kota ("
                    " user_id TEXT NOT NULL, gun TEXT NOT NULL, "
                    " adet INT NOT NULL, "
                    " PRIMARY KEY (user_id, gun))"
                )
                _tablo_hazir = True
            # ON CONFLICT DO UPDATE atomiktir: ayni anda iki istek
            # kaybi kaybetmez ( RETURNING ile yeni adedi dondurur ).
            satir = conn.execute(
                "INSERT INTO basak_kota (user_id, gun, adet) "
                "VALUES (%s, %s, 1) "
                "ON CONFLICT (user_id, gun) "
                "DO UPDATE SET adet = basak_kota.adet + 1 "
                "RETURNING adet",
                (kid, gun),
            ).fetchone()
            return int(satir[0]) if satir else None
    except Exception:
        return None


def _bellek_ekle(kid, gun):
    """Instance belleginde artir (yedek yol; local/preview/test)."""
    with _kilit:
        kayit = _bellek.get(kid)
        if kayit and kayit[0] == gun:
            adet = kayit[1] + 1
        else:
            adet = 1
        _bellek[kid] = (gun, adet)
        # Gun disi kayitlari ve tasma temizligi (cok basit GC).
        if len(_bellek) > 4096:
            for k in [k for k, v in _bellek.items() if v[0] != gun][:2048]:
                _bellek.pop(k, None)
        return adet


def kota_ekle(kid):
    """Kotayi 1 artirir; (izin, kalan) dondurur.

    Postgres once denenir; basilamazsa bellek yedegine dusulur —
    kota hicbir kosulda istegi sessizce gecirmez (fail-closed sayim).
    """
    gun = _gun()
    t = tavan()
    adet = _pg_ekle(kid, gun)
    if adet is None:
        adet = _bellek_ekle(kid, gun)
    return adet <= t, max(0, t - adet)


def kalan_bildir(kid):
    """Sayim arttirmadan kalan hakki soyler (gosterim icin)."""
    gun = _gun()
    with _kilit:
        kayit = _bellek.get(kid)
        adet = kayit[1] if kayit and kayit[0] == gun else 0
    return max(0, tavan() - adet)


def sifirla():
    """Testler icin bellek sayacini temizler."""
    global _tablo_hazir
    with _kilit:
        _bellek.clear()
    _tablo_hazir = False
