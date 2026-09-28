"""tests/test_kota_web.py — Faz 2: anonim gunluk kota kapisi (web).

Kota MODEL DARALTMA DEGILDIR: karar istegin basinda, model calismadan
Once verilir; cevaba/akisa/arac secimine dokunmaz. Burada olculen sey:
1) sayac dogru artar ve tavaninda durur,
2) asimda 429 + Turkce net uyari doner ve model HIC calismaz,
3) X-Basak-Token sahibi kotanin disindadir,
4) UI 429'u sohbeti bozmadan gosterir.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

import app
import kota

ROOT = Path(__file__).resolve().parents[1]
TOKEN = "kota-test-token-ascii"


def _preview(monkeypatch, tmp_path, tavan="2", token=None):
    """Preview kimligi + bellek yedegi (Postgres'e asla gidilmez)."""
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("VERCEL_ENV", "preview")
    monkeypatch.setenv("BASAK_STATE_DIR", str(tmp_path / "state"))
    for ad in ("BASAK_URETIM", "BASAK_OTURUM_ANAHTARI", "DATABASE_URL",
               "POSTGRES_URL", "NEON_DATABASE_URL"):
        monkeypatch.delenv(ad, raising=False)
    if token:
        monkeypatch.setenv("BASAK_WEB_TOKEN", token)
    else:
        monkeypatch.delenv("BASAK_WEB_TOKEN", raising=False)
    monkeypatch.setenv("BASAK_ANONIM_KOTA_TAVAN", tavan)
    monkeypatch.setattr(kota, "_dsn_bul", lambda: "")  # bellek yedegi
    kota.sifirla()


def _sahte_akis(yakalanan):
    """Modeli taklit eder: kac kez calistigini sayar."""
    def _mesaj_isle(metin, beyin, sistem, js_callback, tools=None, **ekstra):
        yakalanan["n"] = yakalanan.get("n", 0) + 1
        js_callback("BasakUI.thinking()")
        js_callback('BasakUI.bitir("tamam", "test")')

    return _mesaj_isle


def _istemci(monkeypatch, tmp_path, **kw):
    yakalanan = {"n": 0}
    _preview(monkeypatch, tmp_path, **kw)
    monkeypatch.setattr(app, "_cekirdek", lambda: (object(), []))
    import chat.flow as flow
    monkeypatch.setattr(flow, "mesaj_isle", _sahte_akis(yakalanan))
    c = TestClient(app.app, base_url="https://preview.test")
    c.__enter__()
    assert c.post("/api/kimlik", json={}).status_code == 200
    return c, yakalanan


def _gonder(c, metin="merhaba", headers=None):
    ham = {"accept": "application/x-ndjson"}
    ham.update(headers or {})
    return c.post("/api/sohbet",
                  json={"metin": metin, "misafir": False, "gecmis": []},
                  headers=ham)


# ── sayac modulu ─────────────────────────────────────────────────────

class TestSayac:
    def setup_method(self):
        kota.sifirla()

    def teardown_method(self):
        kota.sifirla()

    def test_tavan_env_ile_ayarlaniyor(self, monkeypatch):
        monkeypatch.setenv("BASAK_ANONIM_KOTA_TAVAN", "7")
        assert kota.tavan() == 7
        monkeypatch.setenv("BASAK_ANONIM_KOTA_TAVAN", "0")
        assert kota.tavan() == kota.VARSAYILAN_TAVAN
        monkeypatch.setenv("BASAK_ANONIM_KOTA_TAVAN", "bozuk")
        assert kota.tavan() == kota.VARSAYILAN_TAVAN

    def test_kota_ekle_sayar_ve_kalan_doner(self, monkeypatch):
        monkeypatch.setattr(kota, "_dsn_bul", lambda: "")
        monkeypatch.setenv("BASAK_ANONIM_KOTA_TAVAN", "3")
        kid = "u1234567890123456"
        assert kota.kota_ekle(kid) == (True, 2)
        assert kota.kota_ekle(kid) == (True, 1)
        assert kota.kota_ekle(kid) == (True, 0)
        assert kota.kota_ekle(kid) == (False, 0)
        assert kota.kalan_bildir(kid) == 0

    def test_kota_ayni_gunde_baska_id_den(self, monkeypatch):
        monkeypatch.setattr(kota, "_dsn_bul", lambda: "")
        monkeypatch.setenv("BASAK_ANONIM_KOTA_TAVAN", "1")
        assert kota.kota_ekle("u1111111111111111") == (True, 0)
        assert kota.kota_ekle("u2222222222222222") == (True, 0)
        assert kota.kota_ekle("u1111111111111111") == (False, 0)

    def test_kota_gun_degisince_sifirlanir(self, monkeypatch):
        monkeypatch.setattr(kota, "_dsn_bul", lambda: "")
        monkeypatch.setenv("BASAK_ANONIM_KOTA_TAVAN", "1")
        kid = "u3333333333333333"
        assert kota.kota_ekle(kid)[0] is True
        assert kota.kota_ekle(kid)[0] is False
        monkeypatch.setattr(kota, "_gun", lambda: "2099-01-01")
        assert kota.kota_ekle(kid) == (True, 0)

    def test_postgres_yoksa_bellege_duser(self, monkeypatch):
        """Ag yokken sayac yine de calisir (fail-open modul)."""
        monkeypatch.setattr(kota, "_dsn_bul", lambda: "")
        monkeypatch.setenv("BASAK_ANONIM_KOTA_TAVAN", "1")
        assert kota.kota_ekle("u4444444444444444")[0] is True
        assert kota.kota_ekle("u4444444444444444")[0] is False


# ── web kapisi ───────────────────────────────────────────────────────

class TestSohbetKapisi:
    def test_ilk_istek_gecer_ikincisi_429(self, monkeypatch, tmp_path):
        c, yakalanan = _istemci(monkeypatch, tmp_path, tavan="2")
        try:
            ilk = _gonder(c)
            assert ilk.status_code == 200
            assert ilk.headers.get("x-basak-kota-kalan") == "1"
            ikinci = _gonder(c)
            assert ikinci.status_code == 200
            assert ikinci.headers.get("x-basak-kota-kalan") == "0"

            ucuncu = _gonder(c)
            assert ucuncu.status_code == 429
            govde = ucuncu.json()
            assert govde["kota"] is True
            assert govde["kalan"] == 0
            assert "olaylar" not in govde and "cevap" not in govde
            assert "Retry-After" in ucuncu.headers
            # model tam olarak izin verilen sayi kadar calisti
            assert yakalanan["n"] == 2
        finally:
            c.__exit__(None, None, None)

    def test_429_mesaji_turkce_ve_kinamaz(self, monkeypatch, tmp_path):
        c, _ = _istemci(monkeypatch, tmp_path, tavan="1")
        try:
            _gonder(c)
            r = _gonder(c)
            assert r.status_code == 429
            hata = r.json()["error"]
            assert "Günlük ücretsiz hakkın doldu" in hata
            assert "sıfırlanır" in hata
            assert "kayıt zorunlu değil" in hata
            assert all(c not in hata for c in "?!")  # sacma bir kisit degil
        finally:
            c.__exit__(None, None, None)

    def test_asimda_model_hic_calismaz(self, monkeypatch, tmp_path):
        """Kota, _cekirdek/model'den ONCE karar verir (CHATBOT-YASAGI disi)."""
        c, yakalanan = _istemci(monkeypatch, tmp_path, tavan="1")
        try:
            kid = c.post("/api/kimlik", json={}).json()["kullanici"]
            assert kota.kota_ekle(kid)[0] is True      # kotayi doldur
            monkeypatch.setattr(
                app, "_cekirdek",
                lambda: (_ for _ in ()).throw(
                    AssertionError("model kota kapisi oncesinde calisti")))
            r = _gonder(c)
            assert r.status_code == 429
            assert yakalanan["n"] == 0
        finally:
            c.__exit__(None, None, None)

    def test_token_sahibi_kotanin_disinda(self, monkeypatch, tmp_path):
        c, yakalanan = _istemci(monkeypatch, tmp_path, tavan="1", token=TOKEN)
        try:
            _gonder(c)                       # kotayi doldur
            assert _gonder(c).status_code == 429
            yonetici = _gonder(c, headers={"X-Basak-Token": TOKEN})
            assert yonetici.status_code == 200
            assert yakalanan["n"] == 2       # yonetici istegi modeli calistirdi
        finally:
            c.__exit__(None, None, None)

    def test_kota_hatasi_sohbeti_kirilmaz(self, monkeypatch, tmp_path):
        """429 bir istemci hatasi gibi yorulmaz; mesaj ve durum net."""
        c, _ = _istemci(monkeypatch, tmp_path, tavan="1")
        try:
            _gonder(c)
            r = _gonder(c)
            assert r.headers.get("content-type", "").startswith(
                "application/json")
            assert r.json()["error"]
        finally:
            c.__exit__(None, None, None)


# ── UI (istemci) ─────────────────────────────────────────────────────

class TestArayuz:
    def test_ui_429_uarisini_sohbeti_bozmadan_gosterir(self):
        ui = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        assert "err.kota" in ui                    # kota uygundur
        assert "x-basak-kota-kalan" in ui          # kalan hak okunur
        assert "Bir sorun oluştu" in ui            # normal hata yolu korundu
        # kota uygundugunda "Bir sorun oluştu" oneki kullanilmaz
        assert "err && err.kota" in ui

    def test_ui_alt_bilgide_kalan_hakki_gorunur(self):
        ui = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        assert "Bugün kalan ücretsiz hak" in ui
