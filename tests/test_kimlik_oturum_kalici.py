"""tests/test_kimlik_oturum_kalici.py — geçici hata kimliği değiştirmez.

Ölçülen kusur (2026-10-31): `POST /api/kimlik`, tarayıcının getirdiği
platform oturum çerezini geçici bir depo hatası yüzünden çözemediğinde
bunu "kimlik yok" sayıp sessizce YENİ hesap açıyor ve çerezi eziyordu.
Yeni hesabın eski hesapla hiçbir bağı olmadığı için kullanıcının bütün
platform bağlantıları görünmez oluyordu ("her sohbette düşüyor").

Kural: oturum deposu bir an okunamazsa cevap 503'tür; yeni hesap
açılmaz, çerez değiştirilmez, depo düzelince aynı kimlik geri gelir.
"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def depo(monkeypatch, tmp_path):
    from chat.kosu_deposu import _SqliteDepo
    from chat.platform_connections import ConnectionStore
    from chat import kosu_deposu
    db = _SqliteDepo(str(tmp_path / "kimlik.db"))
    store = ConnectionStore(db)
    monkeypatch.setattr(kosu_deposu, "_DEPO", db)
    monkeypatch.setattr("chat.platform_identity.ConnectionStore", lambda: store)
    monkeypatch.setenv("VERCEL_ENV", "production")
    return store


def _hesap_sayisi(store):
    return len(store._db._sorgu("SELECT id FROM basak_account"))


def _kimlik_al(istemci):
    return istemci.post("/api/kimlik", headers={"Origin": "http://testserver"})


def test_ayni_tarayici_ayni_kimlik(depo):
    import app
    istemci = TestClient(app.app)
    ilk = _kimlik_al(istemci).json()["kullanici"]
    ikinci = _kimlik_al(istemci).json()["kullanici"]
    assert ilk == ikinci
    assert _hesap_sayisi(depo) == 1


def test_gecici_depo_hatasi_kimligi_degistirmez(depo, monkeypatch):
    import app
    from chat.platform_identity import COOKIE, IdentityService

    istemci = TestClient(app.app)
    uid = _kimlik_al(istemci).json()["kullanici"]
    token = istemci.cookies[COOKIE]
    assert token.startswith("b1.")

    orijinal = IdentityService.resolve_session

    def patlat(self, *_args, **_kwargs):
        raise RuntimeError("gecici depo hatasi")

    monkeypatch.setattr(IdentityService, "resolve_session", patlat)
    try:
        cevap = _kimlik_al(istemci)
    finally:
        monkeypatch.setattr(IdentityService, "resolve_session", orijinal)

    assert cevap.status_code == 503, cevap.text
    assert "set-cookie" not in {ad.lower() for ad in cevap.headers}
    assert istemci.cookies[COOKIE] == token, "çerez ezilmemeli"
    assert _hesap_sayisi(depo) == 1, "geçici hatada yeni hesap açılmamalı"
    assert _kimlik_al(istemci).json()["kullanici"] == uid, "depo düzelince aynı kimlik"
