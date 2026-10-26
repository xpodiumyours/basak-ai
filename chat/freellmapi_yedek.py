"""Resmi FreeLLMAPI'nin sifreli HTTP yedegini mevcut Postgres'te saklar.

Gateway AES-256-GCM ile sifreler; Basak anahtarlari veya acik DB'yi gormez.
Protokol: FreeLLMAPI db-backup.ts, GET/PUT + Bearer + FAPIBK1 NUL zarfi.
"""

import hashlib
import hmac
import logging
import os
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

logger = logging.getLogger(__name__)
router = APIRouter()
MAGIC = b"FAPIBK1\0"
MAX_BYTES = 4 * 1024 * 1024
SQL = Path(__file__).resolve().parents[1] / "deploy" / "freellmapi" / "backup.sql"


def _yetkili(request):
    token = os.environ.get("FREELLMAPI_BACKUP_TOKEN", "").strip()
    actual = request.headers.get("authorization", "")
    return bool(token and hmac.compare_digest(
        actual.encode("utf-8"), ("Bearer " + token).encode("utf-8")))


def _baglan():
    import psycopg
    dsn = os.environ.get("FREELLMAPI_BACKUP_DATABASE_URL", "").strip()
    if not dsn and os.environ.get("VERCEL_ENV") == "preview":
        dsn = os.environ.get("BASAK_PREVIEW_DATABASE_URL", "").strip()
        if not dsn:
            raise RuntimeError("Preview yedek veritabani yapilandirilmadi")
    dsn = dsn or os.environ.get("DATABASE_URL", "").strip()
    if not dsn:
        raise RuntimeError("Yedek veritabani yapilandirilmadi")
    return psycopg.connect(dsn, connect_timeout=10, prepare_threshold=None)


def kaydet(payload):
    with _baglan() as conn:
        conn.execute(SQL.read_text(encoding="utf-8"))
        conn.execute(
            "INSERT INTO basak_gateway.encrypted_backup (name, payload) "
            "VALUES ('freellmapi-v1', %s) ON CONFLICT (name) DO UPDATE "
            "SET payload = EXCLUDED.payload, updated_at = now()", (payload,))


def yukle():
    with _baglan() as conn:
        conn.execute(SQL.read_text(encoding="utf-8"))
        row = conn.execute(
            "SELECT payload FROM basak_gateway.encrypted_backup "
            "WHERE name = 'freellmapi-v1'").fetchone()
    return bytes(row[0]) if row else None


@router.api_route("/api/freellmapi-backup", methods=["GET", "PUT"])
async def yedek(request: Request):
    if not _yetkili(request):
        return JSONResponse({"error": "yetkisiz"}, status_code=401,
                            headers={"Cache-Control": "no-store"})
    try:
        if request.method == "PUT":
            payload = bytearray()
            async for chunk in request.stream():
                payload.extend(chunk)
                if len(payload) > MAX_BYTES:
                    return JSONResponse({"error": "yedek cok buyuk"}, status_code=413)
            payload = bytes(payload)
            if len(payload) < len(MAGIC) + 12 + 16 or not payload.startswith(MAGIC):
                return JSONResponse({"error": "sifreli yedek bicimi gecersiz"}, status_code=400)
            from asyncio import to_thread
            await to_thread(kaydet, payload)
            return Response(status_code=204, headers={"Cache-Control": "no-store"})
        from asyncio import to_thread
        payload = await to_thread(yukle)
        if payload is None:
            return Response(status_code=404, headers={"Cache-Control": "no-store"})
        return Response(payload, media_type="application/octet-stream", headers={
            "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
            "ETag": '"' + hashlib.sha256(payload).hexdigest() + '"',
        })
    except Exception:
        # Baglanti/SQL hatasi DSN veya sifreli veri icerebilir; loglama.
        logger.warning("FreeLLMAPI sifreli yedek deposuna erisilemedi")
        return JSONResponse({"error": "yedek deposu kullanilamiyor"}, status_code=503)
