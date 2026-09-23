import os, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
import kullanici
import app


def _prod(monkeypatch, tmp_path):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("BASAK_URETIM", "1")
    monkeypatch.setenv("BASAK_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("BASAK_OTURUM_ANAHTARI", "test-signing-key-1234567890")
    monkeypatch.delenv("BASAK_WEB_TOKEN", raising=False)


def test_anonim_id_bicimi_ve_benzersizlik():
    ids = {kullanici.yeni_anonim_kimlik() for _ in range(1000)}
    assert len(ids) == 1000
    assert all(re.fullmatch(r"u\d{16}", x) for x in ids)
    assert "casper" not in ids


def test_id_tek_basina_oturum_acmaz(monkeypatch, tmp_path):
    _prod(monkeypatch, tmp_path)
    kid = kullanici.yeni_anonim_kimlik()
    assert kullanici.oturum_coz(kid) is None
    token = kullanici.oturum_tokeni_uret(kid)
    assert kullanici.oturum_coz(token) == kid


def test_ilk_ziyaret_id_verir_ve_cerez_guvenli(monkeypatch, tmp_path):
    _prod(monkeypatch, tmp_path)
    with TestClient(app.app, base_url="https://testserver") as c:
        r = c.post("/api/kimlik", json={})
        assert r.status_code == 200
        d = r.json()
        assert d["ok"] is True and d["kayit_gerekli"] is False
        assert re.fullmatch(r"u\d{16}", d["kullanici"])
        assert re.fullmatch(r"\d{4} \d{4} \d{4} \d{4}", d["basak_id"])
        sc = r.headers.get("set-cookie", "")
        assert "HttpOnly" in sc and "Secure" in sc and "SameSite=lax" in sc


def test_ayni_tarayici_ayni_id(monkeypatch, tmp_path):
    _prod(monkeypatch, tmp_path)
    with TestClient(app.app, base_url="https://testserver") as c:
        a = c.post("/api/kimlik", json={}).json()["kullanici"]
        b = c.post("/api/kimlik", json={}).json()["kullanici"]
        assert a == b


def test_iki_tarayici_farkli_id(monkeypatch, tmp_path):
    _prod(monkeypatch, tmp_path)
    with TestClient(app.app, base_url="https://a.test") as a, TestClient(app.app, base_url="https://b.test") as b:
        ida = a.post("/api/kimlik", json={}).json()["kullanici"]
        idb = b.post("/api/kimlik", json={}).json()["kullanici"]
        assert ida != idb


def test_eski_casper_public_webde_yeni_idye_doner(monkeypatch, tmp_path):
    _prod(monkeypatch, tmp_path)
    eski = kullanici.oturum_tokeni_uret("casper")
    with TestClient(app.app, base_url="https://testserver") as c:
        c.cookies.set(kullanici.cookie_adi(), eski)
        d = c.post("/api/kimlik", json={}).json()
        assert d["kullanici"] != "casper"
        assert re.fullmatch(r"u\d{16}", d["kullanici"])


def test_anahtar_yoksa_fail_closed(monkeypatch, tmp_path):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("BASAK_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.delenv("BASAK_OTURUM_ANAHTARI", raising=False)
    monkeypatch.delenv("BASAK_WEB_TOKEN", raising=False)
    with TestClient(app.app, base_url="https://testserver") as c:
        r = c.post("/api/kimlik", json={})
        assert r.status_code == 503


def test_web_kodunda_giris_zorunlulugu_yok_ve_depo_id_bazli():
    root = Path(__file__).resolve().parents[1]
    common = (root / "web/common.js").read_text(encoding="utf-8")
    ui = (root / "web/app.js").read_text(encoding="utf-8")
    index = (root / "web/index.html").read_text(encoding="utf-8")
    assert "/api/kimlik" in common
    assert "giris.html" not in common
    assert "depoAnahtari" in ui and "basak_cloud_chats_v2" in ui
    assert "const LEGACY_KEY" not in ui
    assert "localStorage.getItem(LEGACY_KEY)" not in ui
    assert "Başak hata yapabilir" in index
    assert "Önemli bilgileri" in index
