import os
import re
import sys
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
    monkeypatch.setattr(app, "_hafizayi_bir_kez_sifirla", lambda: True)


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


def test_ilk_ziyaret_id_verir(monkeypatch, tmp_path):
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
    with TestClient(app.app, base_url="https://a.test") as a, \
         TestClient(app.app, base_url="https://b.test") as b:
        ida = a.post("/api/kimlik", json={}).json()["kullanici"]
        idb = b.post("/api/kimlik", json={}).json()["kullanici"]
        assert ida != idb


def test_web_kodunda_giris_zorunlulugu_yok_ve_depo_id_bazli():
    root = Path(__file__).resolve().parents[1]
    common = (root / "web/common.js").read_text(encoding="utf-8")
    ui = (root / "web/app.js").read_text(encoding="utf-8")
    index = (root / "web/index.html").read_text(encoding="utf-8")
    assert "/api/kimlik" in common
    assert "giris.html" not in common
    assert "depoAnahtari" in ui and "basak_cloud_chats_v2" in ui
    assert "basak_cloud_history" not in ui
    assert "Başak hata yapabilir" in index
    assert "Önemli bilgileri" in index


def _preview(monkeypatch, tmp_path):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("VERCEL_ENV", "preview")
    monkeypatch.setenv("BASAK_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.delenv("BASAK_URETIM", raising=False)
    monkeypatch.delenv("BASAK_OTURUM_ANAHTARI", raising=False)
    monkeypatch.delenv("BASAK_WEB_TOKEN", raising=False)


def test_preview_anahtarsiz_izole_kimlik_verir(monkeypatch, tmp_path):
    _preview(monkeypatch, tmp_path)

    def _hafizaya_dokunma():
        raise AssertionError("Preview production hafiza sifirlamasina dokundu")

    monkeypatch.setattr(app, "_hafizayi_bir_kez_sifirla", _hafizaya_dokunma)

    with TestClient(app.app, base_url="https://preview.test") as c:
        r = c.post("/api/kimlik", json={})
        assert r.status_code == 200
        d = r.json()
        assert d["ok"] is True
        assert d["preview"] is True
        assert d["kalici_hafiza"] is False
        assert re.fullmatch(r"p[0-9a-f]{16}", d["kullanici"])
        assert d["basak_id"].startswith("Preview ")
        sc = r.headers.get("set-cookie", "")
        assert "basak_preview_oturum=" in sc
        assert "HttpOnly" in sc and "Secure" in sc and "SameSite=lax" in sc

        # Ayni tarayici Preview oturumunda ayni izole kimligi korur.
        d2 = c.post("/api/kimlik", json={}).json()
        assert d2["kullanici"] == d["kullanici"]

        # Korunan API de Preview kimligiyle acilir; auth anahtari gerekmez.
        monkeypatch.setattr(app, "_cekirdek", lambda: (object(), []))
        durum = c.get("/api/durum")
        assert durum.status_code == 200


def test_preview_sohbeti_misafir_ve_izsiz_calistirir(monkeypatch, tmp_path):
    _preview(monkeypatch, tmp_path)
    monkeypatch.setattr(
        app,
        "_hafizayi_bir_kez_sifirla",
        lambda: (_ for _ in ()).throw(
            AssertionError("Preview hafiza sifirlamasina dokundu")
        ),
    )

    class _Beyin:
        def _bulut_zinciri(self, tools=True):
            return []

    monkeypatch.setattr(app, "_cekirdek", lambda: (_Beyin(), []))

    import chat.flow as flow
    yakalanan = {}

    def _sahte_mesaj_isle(
        metin, beyin, sistem, js_callback, tools=None,
        misafir=False, gecmis_override=None
    ):
        yakalanan["misafir"] = misafir
        yakalanan["metin"] = metin
        js_callback('BasakUI.thinking()')
        js_callback('BasakUI.bitir("preview-ok", "test")')

    monkeypatch.setattr(flow, "mesaj_isle", _sahte_mesaj_isle)

    with TestClient(app.app, base_url="https://preview.test") as c:
        assert c.post("/api/kimlik", json={}).status_code == 200
        r = c.post(
            "/api/sohbet",
            json={"metin": "test", "misafir": False, "gecmis": []},
            headers={"accept": "application/x-ndjson"},
        )
        assert r.status_code == 200
        assert '"cevap":"preview-ok"' in r.text
        assert yakalanan == {"misafir": True, "metin": "test"}


def test_production_preview_kuralindan_etkilenmez(monkeypatch, tmp_path):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("VERCEL_ENV", "production")
    monkeypatch.setenv("BASAK_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.delenv("BASAK_OTURUM_ANAHTARI", raising=False)
    monkeypatch.delenv("BASAK_WEB_TOKEN", raising=False)
    monkeypatch.setattr(app, "_hafizayi_bir_kez_sifirla", lambda: True)

    with TestClient(app.app, base_url="https://prod.test") as c:
        r = c.post("/api/kimlik", json={})
        assert r.status_code == 503
        assert "BASAK_OTURUM_ANAHTARI" in r.json()["error"]
