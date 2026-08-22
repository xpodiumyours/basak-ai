"""voice/speaker_db.py — Konuşmacı embedding veritabanı.

Konuşmacı tanıma için üretilen embedding'leri SQLite'ta saklar.
Her konuşmacının birden fazla ses örneği olabilir (ortalama embedding hesaplar).

Tablo: speakers
  id INTEGER PRIMARY KEY
  isim TEXT UNIQUE       — konuşmacı adı
  embedding BLOB         — numpy array olarak saklanır
  ornek_sayisi INTEGER   — kaç kaynak örnekle üretilmiş
  kayit_zamani TEXT      — ISO format tarih

Veritabanı: data/speakers.db
"""

import json
import logging
import os
import sqlite3
import threading
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DB_DIR = os.path.join(_BASE, "data")
_DB_YOLU = os.path.join(_DB_DIR, "speakers.db")


class KonusmaciDB:
    """SQLite tabanlı konuşmacı embedding deposu."""

    def __init__(self, db_yolu: str = _DB_YOLU):
        self._db_yolu = db_yolu
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(db_yolu), exist_ok=True)
        self._tablo_olustur()

    def _tablo_olustur(self):
        """Speakers tablosunu oluşturur (yoksa)."""
        with self._lock:
            conn = sqlite3.connect(self._db_yolu)
            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS speakers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        isim TEXT UNIQUE NOT NULL,
                        embedding BLOB NOT NULL,
                        ornek_sayisi INTEGER DEFAULT 1,
                        kayit_zamani TEXT NOT NULL
                    )
                """)
                conn.commit()
            finally:
                conn.close()

    def konusmaci_kaydet(self, isim: str, embedding: np.ndarray, ornek_sayisi: int = 1) -> bool:
        """Konuşmacı embedding'ini kaydeder veya günceller.

        Aynı isim varsa embedding ortalaması alınarak güncellenir.

        Args:
            isim: Konuşmacı adı.
            embedding: (256,) boyutunda numpy array.
            ornek_sayisi: Bu embedding kaç örnekle üretilmiş.

        Returns:
            True başarılıysa.
        """
        from datetime import datetime, timezone

        embedding_list = embedding.tolist()
        embedding_json = json.dumps(embedding_list)
        now = datetime.now(timezone.utc).isoformat()

        with self._lock:
            conn = sqlite3.connect(self._db_yolu)
            try:
                # Mevcut kayıt var mı?
                row = conn.execute(
                    "SELECT embedding, ornek_sayisi FROM speakers WHERE isim = ?",
                    (isim,)
                ).fetchone()

                if row:
                    # Ortalama embedding hesapla (eski + yeni)
                    eski_emb = np.array(json.loads(row[0]), dtype=np.float64)
                    eski_sayisi = row[1]
                    toplam = eski_sayisi + ornek_sayisi
                    yeni_emb = (eski_emb * eski_sayisi + embedding * ornek_sayisi) / toplam
                    # Normalize
                    norm = np.linalg.norm(yeni_emb)
                    if norm > 1e-8:
                        yeni_emb = yeni_emb / norm

                    conn.execute(
                        "UPDATE speakers SET embedding = ?, ornek_sayisi = ?, kayit_zamani = ? WHERE isim = ?",
                        (json.dumps(yeni_emb.tolist()), toplam, now, isim)
                    )
                    logger.info("Konusmaci guncellendi: %s (toplam %d ornek)", isim, toplam)
                else:
                    conn.execute(
                        "INSERT INTO speakers (isim, embedding, ornek_sayisi, kayit_zamani) VALUES (?, ?, ?, ?)",
                        (isim, embedding_json, ornek_sayisi, now)
                    )
                    logger.info("Konusmaci kaydedildi: %s (%d ornek)", isim, ornek_sayisi)

                conn.commit()
                return True
            except Exception as e:
                logger.error("Konuşmacı kaydetme hatası: %s", e)
                return False
            finally:
                conn.close()

    def konusmaci_yukle(self, isim: str) -> Optional[np.ndarray]:
        """Konuşmacının embedding'ini yükler."""
        with self._lock:
            conn = sqlite3.connect(self._db_yolu)
            try:
                row = conn.execute(
                    "SELECT embedding FROM speakers WHERE isim = ?",
                    (isim,)
                ).fetchone()
                if row:
                    return np.array(json.loads(row[0]), dtype=np.float64)
                return None
            finally:
                conn.close()

    def tumunu_yukle(self) -> dict[str, np.ndarray]:
        """Tüm kayıtlı konuşmacıları yükler.

        Returns:
            {isim: embedding_array, ...}
        """
        with self._lock:
            conn = sqlite3.connect(self._db_yolu)
            try:
                rows = conn.execute("SELECT isim, embedding FROM speakers").fetchall()
                return {
                    isim: np.array(json.loads(emb), dtype=np.float64)
                    for isim, emb in rows
                }
            finally:
                conn.close()

    def konusmaci_sil(self, isim: str) -> bool:
        """Konuşmacıyı siler."""
        with self._lock:
            conn = sqlite3.connect(self._db_yolu)
            try:
                cursor = conn.execute("DELETE FROM speakers WHERE isim = ?", (isim,))
                conn.commit()
                return cursor.rowcount > 0
            finally:
                conn.close()

    def konusmaci_listesi(self) -> list[dict]:
        """Tüm kayıtlı konuşmacıları listeler."""
        with self._lock:
            conn = sqlite3.connect(self._db_yolu)
            try:
                rows = conn.execute(
                    "SELECT isim, ornek_sayisi, kayit_zamani FROM speakers ORDER BY isim"
                ).fetchall()
                return [
                    {"isim": r[0], "ornek_sayisi": r[1], "kayit_zamani": r[2]}
                    for r in rows
                ]
            finally:
                conn.close()


# --- Singleton ---
_db = None
_db_lock = threading.Lock()


def konusmaci_db_al() -> KonusmaciDB:
    """Singleton KonusmaciDB örneği döndürür."""
    global _db
    if _db is not None:
        return _db
    with _db_lock:
        if _db is not None:
            return _db
        _db = KonusmaciDB()
        return _db
