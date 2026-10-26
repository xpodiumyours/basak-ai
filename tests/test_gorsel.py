"""tests/test_gorsel.py — Gorsel uretme guvencesi.

Sozlesme: uc yerde bagli; adres sabit hosta gider (model adres
veremez); boyutlar kilitli; ag YOK (acici sahte).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

import app
from tools import calistir, gorsel
from tools.definitions import TANINMIS_TOOLLAR


class SahteYanıt:
    headers = {"Content-Type": "image/jpeg"}

    def __init__(self, yakalayici):
        self._y = yakalayici

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self, n=-1):
        return b"\xff\xd8sahte"


class TestUcYer:
    def test_beyaz_listede(self):
        assert "gorsel_uret" in TANINMIS_TOOLLAR

    def test_durum_etiketi_var(self):
        from chat.tools import DURUM_METNI
        assert "gorsel_uret" in DURUM_METNI


class TestGorsel:
    def test_sabit_hosta_gider_dosyaya_yazar(self, tmp_path, monkeypatch):
        monkeypatch.setattr(gorsel, "URETILEN_KOK", str(tmp_path))
        yakalanan = {}

        def sahte_ac(istek, timeout=None):
            yakalanan["url"] = istek.full_url
            return SahteYanıt(yakalanan)

        r = gorsel.gorsel_uret("kedi", _acici=sahte_ac)
        assert "result" in r, r
        assert yakalanan["url"].startswith(
            "https://image.pollinations.ai/prompt/kedi?")
        ad = r["result"][len("/gorsel/"):]
        assert r["result"] == "/gorsel/" + ad
        assert gorsel.gorsel_yolu_coz(ad) == os.path.join(str(tmp_path), ad)
        assert open(gorsel.gorsel_yolu_coz(ad), "rb").read() == b"\xff\xd8sahte"

    def test_servis_yolu_yalniz_uretilen_altindan(self, tmp_path, monkeypatch):
        monkeypatch.setattr(gorsel, "URETILEN_KOK", str(tmp_path))
        assert gorsel.gorsel_yolu_coz("../app.py") is None
        assert gorsel.gorsel_yolu_coz("gorsel_0123abcd.jpg") == os.path.join(
            str(tmp_path), "gorsel_0123abcd.jpg")

    def test_boyut_kilidi_ve_bos_reddi(self, tmp_path, monkeypatch):
        assert "error" in gorsel.gorsel_uret("   ")
        assert "error" in gorsel.gorsel_uret("x" * 501)
        assert "error" in gorsel.gorsel_uret("kedi", genislik="abc")

    def test_gorsel_degilse_reddedilir(self, tmp_path, monkeypatch):

        class MetinYanıt(SahteYanıt):
            headers = {"Content-Type": "text/html"}

        r = gorsel.gorsel_uret(
            "kedi", _acici=lambda *a, **k: MetinYanıt(None))
        assert "error" in r

    def test_calistir_hatti(self):
        r = calistir("gorsel_uret", {"aciklama": ""})
        assert "error" in r


# ── Tarayici gorunumu: "gorsel cizdi ama ortada gorsel yok" ──────────
# Yerel disk yolu tarayicida acilamaz; gorsel yalniz uygulamanin
# /gorsel/ rotasindan gelir ve web tarafinda <img> olarak cizilir.
# Bu bolum uc halkayi da kilitler: rota, JS donusumu, CSS tasima.

_WEB = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")


def _uretim(monkeypatch, tmp_path):
    """Uretim kapi testi: anahtarli, hafiza sifirlamasi pasif."""
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("BASAK_URETIM", "1")
    monkeypatch.setenv("BASAK_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("BASAK_OTURUM_ANAHTARI", "test-signing-key-1234567890")
    monkeypatch.delenv("BASAK_WEB_TOKEN", raising=False)
    monkeypatch.setattr(app, "_hafizayi_bir_kez_sifirla", lambda: True)


def _web_oku(ad):
    with open(os.path.join(_WEB, ad), encoding="utf-8") as f:
        return f.read()


class TestServisRota:
    def test_girissiz_erisilemez(self, monkeypatch, tmp_path):
        _uretim(monkeypatch, tmp_path)
        monkeypatch.setattr(gorsel, "URETILEN_KOK", str(tmp_path))
        with TestClient(app.app, base_url="https://testserver") as c:
            r = c.get("/gorsel/gorsel_0123abcd.jpg")
            assert r.status_code == 401, r.text

    def test_girisle_uretilen_dosyayi_verir(self, monkeypatch, tmp_path):
        _uretim(monkeypatch, tmp_path)
        monkeypatch.setattr(gorsel, "URETILEN_KOK", str(tmp_path))
        ad = "gorsel_0123abcd.jpg"
        with open(os.path.join(str(tmp_path), ad), "wb") as f:
            f.write(b"\xff\xd8sahte")
        with TestClient(app.app, base_url="https://testserver") as c:
            c.post("/api/kimlik", json={})
            r = c.get("/gorsel/" + ad)
            assert r.status_code == 200, r.text
            assert r.headers["content-type"].startswith("image/jpeg")
            assert r.content == b"\xff\xd8sahte"

    def test_adi_kuraldisi_dosya_bulunamaz(self, monkeypatch, tmp_path):
        """Ad sabit: yalniz gorsel_<8 hex>.jpg; digeri rotada 404."""
        _uretim(monkeypatch, tmp_path)
        monkeypatch.setattr(gorsel, "URETILEN_KOK", str(tmp_path))
        with open(os.path.join(str(tmp_path), "app.py"), "wb") as f:
            f.write(b"ASILAMAZ")
        with TestClient(app.app, base_url="https://testserver") as c:
            c.post("/api/kimlik", json={})
            assert c.get("/gorsel/app.py").status_code == 404
            assert c.get("/gorsel/yok.jpg").status_code == 404


class TestTarayiciGorunumu:
    def test_app_js_gorsel_sozdizimini_cizdirir(self):
        js = _web_oku("app.js")
        assert "/gorsel/" in js
        assert "answer-image" in js

    def test_app_js_dis_gorsel_cizdirmez(self):
        """Gizlilik: ayni koken disinden gorsel veya kod yuklenmez."""
        js = _web_oku("app.js")
        assert 'src="https://' not in js
        assert "<iframe" not in js.lower()
        assert 'fetch("https://' not in js

    def test_chat_css_gorseli_tasmasin(self):
        """Uretilen gorsel boyu 1024px, balon 65ch: sinirlanmazsa taşar."""
        css = _web_oku("chat.css")
        assert ".icerik .answer-image" in css
        assert "max-width:100%" in css

    def test_cache_surumu_artirildi(self):
        html = _web_oku("index.html")
        assert "/app.js?v=30" in html
        assert "/chat.css?v=22" in html
