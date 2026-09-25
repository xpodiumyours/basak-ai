"""memory — Başak hafıza motoru.

Yerelde çalışan SQLite motoru aynen korunur. Üretimde/Vercel'de kalıcı
Postgres bağlantısı zorunludur; bağlantı yoksa geçici SQLite'a sessizce
düşülmez.
"""

import os
from urllib.parse import urlsplit


def _preview_mi():
    return (os.environ.get("VERCEL_ENV") or "").strip().lower() == "preview"


def _uretim_mi():
    return bool(os.environ.get("VERCEL") or os.environ.get("BASAK_URETIM"))


def _postgres_url():
    for ad in ("DATABASE_URL", "POSTGRES_URL", "NEON_DATABASE_URL"):
        deger = (os.environ.get(ad) or "").strip()
        if deger:
            return deger
    return ""


def _postgres_motor(dsn, embed_fn):
    from chat.kimlik import aktif_kullanici
    from memory.postgres import PostgresHafizaMotoru
    return PostgresHafizaMotoru(
        dsn=dsn, kullanici_id=aktif_kullanici(), embed_fn=embed_fn)


def _dsn_hedefi(dsn):
    """Kimlik bilgisinden bagimsiz GERCEK veritabani hedefini karsilastir.

    Farkli kullanici/sifre ayni host+port+database hedefine baglanabilir;
    Preview bunu "ayri DB" sanamaz. postgres/postgresql ve varsayilan 5432
    de ayni hedef sayilir.
    """
    dsn = (dsn or "").strip()
    if not dsn:
        return None
    try:
        p = urlsplit(dsn)
        sema = (p.scheme or "").lower()
        if sema in ("postgres", "postgresql"):
            sema = "postgres"
        port = p.port
        if sema == "postgres" and port is None:
            port = 5432
        yol = (p.path or "/").rstrip("/") or "/"
        return (
            sema,
            (p.hostname or "").lower(),
            port,
            yol,
        )
    except Exception:
        return ("raw", dsn)


def preview_hafiza_modu():
    """Preview DB parity durumunu sir ifsa etmeden bildir."""
    if not _preview_mi():
        return "production_or_local"
    p = (os.environ.get("BASAK_PREVIEW_DATABASE_URL") or "").strip()
    if not p:
        return "sqlite_ephemeral"
    if _dsn_hedefi(p) == _dsn_hedefi(_postgres_url()):
        return "preview_dsn_rejected_same_as_production"
    return "postgres_isolated"


def HafizaMotoru(db_yolu=None, embed_fn=None):
    """Calisma ortamina gore dogru hafiza motorunu kurar.

    Preview icin ayri BASAK_PREVIEW_DATABASE_URL varsa production ile ayni
    Postgres motor davranisi kullanilir. DSN production DSN ile ayniysa
    bilincli olarak reddedilir. Ayri DSN yoksa gecici SQLite acikca kullanilir.
    """
    if _preview_mi():
        preview_dsn = (
            os.environ.get("BASAK_PREVIEW_DATABASE_URL") or ""
        ).strip()
        if preview_dsn:
            if _dsn_hedefi(preview_dsn) == _dsn_hedefi(_postgres_url()):
                raise RuntimeError(
                    "Preview hafiza DSN'i production DSN ile ayni olamaz")
            return _postgres_motor(preview_dsn, embed_fn)
        from memory.engine import HafizaMotoru as SQLiteHafizaMotoru
        return SQLiteHafizaMotoru(db_yolu=db_yolu, embed_fn=embed_fn)

    if _uretim_mi():
        dsn = _postgres_url()
        if not dsn:
            raise RuntimeError(
                "Uretimde kalici hafiza baglantisi yok: DATABASE_URL tanimli degil")
        return _postgres_motor(dsn, embed_fn)

    from memory.engine import HafizaMotoru as SQLiteHafizaMotoru
    return SQLiteHafizaMotoru(db_yolu=db_yolu, embed_fn=embed_fn)


__all__ = ["HafizaMotoru", "preview_hafiza_modu"]
