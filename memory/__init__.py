"""memory — Başak hafıza motoru.

Yerelde çalışan SQLite motoru aynen korunur. Üretimde/Vercel'de kalıcı
Postgres bağlantısı zorunludur; bağlantı yoksa geçici SQLite'a sessizce
düşülmez.
"""

import os


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


def HafizaMotoru(db_yolu=None, embed_fn=None):
    """Çalışma ortamına göre doğru hafıza motorunu kurar.

    Vercel Preview canlıyla aynı hafıza kod yolunu çalıştırır ama üretim
    Postgres'ine bağlanmaz; BASAK_STATE_DIR altındaki geçici SQLite kullanır.
    Production davranışı değişmez.
    """
    if _preview_mi():
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


__all__ = ["HafizaMotoru"]
