"""brain/stats.py — Model performans takip sistemi.

Her model çağrısında istatistik toplar:
- Toplam çağrı sayısı, başarılı/başarısız
- Ortalama/min/max yanıt süresi
- Son hata mesajı
- Token kullanımı (mümkünse)

Veritabanı: data/model_stats.db
Tablolar:
  calls: her çağrı bir satır (model, sure, basarili, hata, timestamp)
  models: özet istatistikler (per-model aggregation)
"""

import logging
import os
import sqlite3
import threading
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(BASE, "data")
DB_YOLU = os.path.join(DB_DIR, "model_stats.db")


class ModelIstatistik:
    """SQLite tabanlı model performans takipçisi."""

    def __init__(self, db_yolu: str = DB_YOLU):
        self._db_yolu = db_yolu
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(db_yolu), exist_ok=True)
        self._tablo_olustur()

    def _tablo_olustur(self):
        with self._lock:
            conn = sqlite3.connect(self._db_yolu)
            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS calls (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        model TEXT NOT NULL,
                        sure_ms INTEGER NOT NULL,
                        basarili INTEGER NOT NULL DEFAULT 1,
                        hata TEXT DEFAULT '',
                        tools INTEGER NOT NULL DEFAULT 0,
                        token_in INTEGER DEFAULT 0,
                        token_out INTEGER DEFAULT 0,
                        timestamp TEXT NOT NULL
                    )
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_calls_model ON calls(model)
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_calls_timestamp ON calls(timestamp)
                """)
                conn.commit()
            finally:
                conn.close()

    def kaydet(self, model: str, sure_sn: float, basarili: bool = True,
               hata: str = "", tools: bool = False,
               token_in: int = 0, token_out: int = 0):
        """Bir model çağrısını kaydeder.

        Args:
            model: Model adı (ör: "groq", "nvidia", "yerel").
            sure_sn: Yanıt süresi (saniye).
            basarili: Başarılı mı.
            hata: Hata mesajı (başarısızsa).
            tools: Tool kullanımı var mı.
            token_in: Giren token sayısı.
            token_out: Çıkan token sayısı.
        """
        now = datetime.now(timezone.utc).isoformat()
        sure_ms = int(sure_sn * 1000)

        with self._lock:
            conn = sqlite3.connect(self._db_yolu)
            try:
                conn.execute(
                    "INSERT INTO calls (model, sure_ms, basarili, hata, tools, "
                    "token_in, token_out, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (model, sure_ms, 1 if basarili else 0, hata,
                     1 if tools else 0, token_in, token_out, now),
                )
                conn.commit()
            finally:
                conn.close()

    def ozet(self, model: str = None, son_saat: int = None) -> list[dict]:
        """Model performans özetini döndürür.

        Args:
            model: Belirli bir modelin istatistiği (None ise tümü).
            son_saat: Son kaç saat (None ise tümü).

        Returns:
            [{
                "model": "groq",
                "toplam": 45,
                "basarili": 42,
                "basarisiz": 3,
                "basari_orani": 93.3,
                "ortalama_ms": 1250,
                "min_ms": 300,
                "max_ms": 4500,
                "son_hata": "rate limit",
                "son_cagri": "2026-08-22T...",
            }]
        """
        with self._lock:
            conn = sqlite3.connect(self._db_yolu)
            try:
                where_parts = []
                params = []

                if model:
                    where_parts.append("model = ?")
                    params.append(model)
                if son_saat:
                    where_parts.append("timestamp >= datetime('now', ?)")
                    params.append("-%d hours" % son_saat)

                where = (" WHERE " + " AND ".join(where_parts)) if where_parts else ""

                rows = conn.execute(f"""
                    SELECT
                        model,
                        COUNT(*) as toplam,
                        SUM(basarili) as basarili,
                        COUNT(*) - SUM(basarili) as basarisiz,
                        ROUND(100.0 * SUM(basarili) / COUNT(*), 1) as basari_orani,
                        ROUND(AVG(sure_ms)) as ortalama_ms,
                        MIN(sure_ms) as min_ms,
                        MAX(sure_ms) as max_ms,
                        SUM(token_in) as token_in_toplam,
                        SUM(token_out) as token_out_toplam,
                        (SELECT hata FROM calls c2 WHERE c2.model = calls.model
                         AND c2.basarili = 0 ORDER BY c2.id DESC LIMIT 1) as son_hata,
                        (SELECT timestamp FROM calls c3 WHERE c3.model = calls.model
                         ORDER BY c3.id DESC LIMIT 1) as son_cagri
                    FROM calls
                    {where}
                    GROUP BY model
                    ORDER BY basarili DESC
                """, params).fetchall()

                return [
                    {
                        "model": r[0],
                        "toplam": r[1],
                        "basarili": r[2] or 0,
                        "basarisiz": r[3] or 0,
                        "basari_orani": r[4] or 0,
                        "ortalama_ms": r[5] or 0,
                        "min_ms": r[6] or 0,
                        "max_ms": r[7] or 0,
                        # Gercek token sayimi (2026-08-24): adaptorden gelen
                        # usage bilgisi artik burada birikir.
                        "token_in_toplam": r[8] or 0,
                        "token_out_toplam": r[9] or 0,
                        "son_hata": r[10] or "",
                        "son_cagri": r[11] or "",
                    }
                    for r in rows
                ]
            finally:
                conn.close()

    def sonucun(self, limit: int = 20) -> list[dict]:
        """Son N çağrıyı döndürür."""
        with self._lock:
            conn = sqlite3.connect(self._db_yolu)
            try:
                rows = conn.execute(
                    "SELECT model, sure_ms, basarili, hata, tools, timestamp "
                    "FROM calls ORDER BY id DESC LIMIT ?", (limit,)
                ).fetchall()
                return [
                    {
                        "model": r[0],
                        "sure_ms": r[1],
                        "basarili": bool(r[2]),
                        "hata": r[3],
                        "tools": bool(r[4]),
                        "timestamp": r[5],
                    }
                    for r in rows
                ]
            finally:
                conn.close()

    def siralama(self, son_saat: int = 24) -> list[dict]:
        """Son 24 saatteki en hızlı ve en başarılı modelleri sıralar.

        Skor = basari_orani * 0.6 + hiz_skoru * 0.4
        """
        ozet = self.ozet(son_saat=son_saat)
        if not ozet:
            return []

        # Hız skoru: en hızlıya 100, en yavaşa 0
        min_ortalama = min(r["ortalama_ms"] for r in ozet if r["ortalama_ms"] > 0) or 1
        max_ortalama = max(r["ortalama_ms"] for r in ozet if r["ortalama_ms"] > 0) or 1
        fark = max_ortalama - min_ortalama or 1

        for r in ozet:
            if r["ortalama_ms"] > 0:
                hiz_skoru = 100 * (1 - (r["ortalama_ms"] - min_ortalama) / fark)
            else:
                hiz_skoru = 0
            r["hiz_skoru"] = round(hiz_skoru, 1)
            r["skor"] = round(r["basari_orani"] * 0.6 + hiz_skoru * 0.4, 1)

        return sorted(ozet, key=lambda r: r["skor"], reverse=True)

    def temizle(self, gun_eski: int = 30) -> int:
        """Eski kayıtları temizler (gun_eski günden eski)."""
        with self._lock:
            conn = sqlite3.connect(self._db_yolu)
            try:
                cursor = conn.execute(
                    "DELETE FROM calls WHERE timestamp < datetime('now', ?)",
                    ("-%d days" % gun_eski,)
                )
                conn.commit()
                return cursor.rowcount
            finally:
                conn.close()


# --- Singleton ---
_stats = None
_stats_lock = threading.Lock()


def model_stats_al() -> ModelIstatistik:
    """Singleton ModelIstatistik örneği döndürür."""
    global _stats
    if _stats is not None:
        return _stats
    with _stats_lock:
        if _stats is not None:
            return _stats
        _stats = ModelIstatistik()
        return _stats
