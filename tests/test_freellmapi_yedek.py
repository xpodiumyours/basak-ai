from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from chat import freellmapi_yedek as backup


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("FREELLMAPI_BACKUP_TOKEN", "test-private-backup-token")
    store = {}
    monkeypatch.setattr(backup, "kaydet", lambda data: store.update(payload=data))
    monkeypatch.setattr(backup, "yukle", lambda: store.get("payload"))
    app = FastAPI()
    app.include_router(backup.router)
    with TestClient(app) as client:
        yield client


HEADERS = {"Authorization": "Bearer test-private-backup-token"}
PAYLOAD = backup.MAGIC + b"a" * 12 + b"b" * 16 + b"encrypted-database"


def test_sifreli_yedek_put_get_ayni_baytlari_korur(client):
    assert client.get("/api/freellmapi-backup", headers=HEADERS).status_code == 404
    assert client.put("/api/freellmapi-backup", headers=HEADERS, content=PAYLOAD).status_code == 204
    result = client.get("/api/freellmapi-backup", headers=HEADERS)
    assert result.status_code == 200 and result.content == PAYLOAD
    assert result.headers["cache-control"] == "no-store"
    assert result.headers["content-type"] == "application/octet-stream"


@pytest.mark.parametrize("method", ["GET", "PUT"])
def test_oturumsuz_ve_yanlis_token_depoya_erisemez(client, monkeypatch, method):
    monkeypatch.setattr(backup, "yukle", lambda: pytest.fail("unauthorized DB read"))
    monkeypatch.setattr(backup, "kaydet", lambda value: pytest.fail("unauthorized DB write"))
    assert client.request(method, "/api/freellmapi-backup", content=PAYLOAD).status_code == 401
    assert client.request(method, "/api/freellmapi-backup", content=PAYLOAD,
                          headers={"Authorization": "Bearer wrong"}).status_code == 401


def test_token_yapilandirilmadiysa_herkes_reddedilir(client, monkeypatch):
    monkeypatch.delenv("FREELLMAPI_BACKUP_TOKEN")
    assert client.get("/api/freellmapi-backup", headers=HEADERS).status_code == 401


@pytest.mark.parametrize("data", [b"SQLite format 3\0plain", b"", backup.MAGIC])
def test_acik_ve_eksik_veritabani_reddedilir(client, data):
    assert client.put("/api/freellmapi-backup", headers=HEADERS, content=data).status_code == 400


def test_teknik_govde_limiti_veritabanina_yazmadan_uygulanir(client, monkeypatch):
    monkeypatch.setattr(backup, "MAX_BYTES", 40)
    assert client.put("/api/freellmapi-backup", headers=HEADERS, content=PAYLOAD).status_code == 413


def test_db_hatasi_sir_sizdirmaz(client, monkeypatch):
    def fail():
        raise RuntimeError("postgresql://private-password@secret-host")
    monkeypatch.setattr(backup, "yukle", fail)
    result = client.get("/api/freellmapi-backup", headers=HEADERS)
    assert result.status_code == 503 and "private-password" not in result.text


def test_preview_uretimin_veritabanina_dusmez(monkeypatch):
    monkeypatch.setenv("VERCEL_ENV", "preview")
    monkeypatch.setenv("DATABASE_URL", "production")
    monkeypatch.delenv("FREELLMAPI_BACKUP_DATABASE_URL", raising=False)
    monkeypatch.delenv("BASAK_PREVIEW_DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="Preview"):
        backup._baglan()
