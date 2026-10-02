"""tests/test_olcum.py — cerezsiz anonim olcum + arac geri bildirimi bekcileri.

Sozlesme:
- POST /api/olcum cerez YAZMAZ; yalniz (gun, yol) toplam sayar.
- Gecersiz yol (site disi, cok uzun, bos) sayilmaz.
- Sec-GPC: 1 basligi gelirse hic sayilmaz (sunucu tarafi DNT saygisi).
- GET /api/olcum yonetici token'i ister; token'siz kapali.
- POST /api/oy yalniz +1/-1 kabul eder; digerine 400.
- Gizlilik metinleri (gizlilik/cerez/envanter/bilgilendirme) anonim sayaci anlatir.
- Tum arac sayfalari olcum.js tasir; olcum.js harici adres kullanmaz.
"""

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

import app
import olcum

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
TOKEN = "olcum-test-token-ascii"
ORNEK = "/araclar/security-tools/sha-hash-generator"


def _ortam(monkeypatch, token=None):
    """Preview kimligi + bellek yedegi (Postgres'e asla gidilmez)."""
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("VERCEL_ENV", "preview")
    monkeypatch.setenv("BASAK_STATE_DIR", str(Path(".").resolve()))
    for ad in ("BASAK_URETIM", "BASAK_OTURUM_ANAHTARI", "DATABASE_URL",
               "POSTGRES_URL", "NEON_DATABASE_URL", "BASAK_WEB_TOKEN"):
        monkeypatch.delenv(ad, raising=False)
    if token:
        monkeypatch.setenv("BASAK_WEB_TOKEN", token)
    monkeypatch.setattr(olcum, "_dsn_bul", lambda: "")
    olcum.sifirla()


def _istemci(monkeypatch, token=None):
    _ortam(monkeypatch, token=token)
    c = TestClient(app.app, base_url="https://ornek.test")
    c.__enter__()
    return c


class TestAnonimSayac:
    def test_sayar_ve_raporlar(self, monkeypatch):
        c = _istemci(monkeypatch, token=TOKEN)
        try:
            assert c.post(
                "/api/olcum", json={"yol": "/araclar"}).json()[
                    "sayildi"] is True
            assert c.post(
                "/api/olcum", json={"yol": "/araclar/x?a=1"}).json()[
                    "sayildi"] is True
            r = c.get("/api/olcum", headers={"X-Basak-Token": TOKEN})
            assert r.status_code == 200
            top = dict(r.json()["sayfalar"])
            assert top.get("/araclar") == 1
            assert top.get("/araclar/x") == 1
        finally:
            c.__exit__(None, None, None)

    def test_gecersiz_yol_sayilmaz(self, monkeypatch):
        c = _istemci(monkeypatch, token=TOKEN)
        try:
            for yol in ("https://baska.site/x", "//baska", "araclar",
                        "", "/" + "k" * 121, None):
                govde = c.post("/api/olcum", json={"yol": yol}).json()
                assert govde["sayildi"] is False, yol
            assert dict(c.get(
                "/api/olcum",
                headers={"X-Basak-Token": TOKEN}).json()["sayfalar"]) == {}
        finally:
            c.__exit__(None, None, None)

    def test_sorgu_kisaltir_bos_govde_sayilmaz(self, monkeypatch):
        c = _istemci(monkeypatch, token=TOKEN)
        try:
            r = c.post("/api/olcum", json={"yol": "/deneme?x=1#y"})
            assert r.json()["sayildi"] is True
            r = c.post("/api/olcum", json={})
            assert r.json()["sayildi"] is False
            top = dict(c.get(
                "/api/olcum",
                headers={"X-Basak-Token": TOKEN}).json()["sayfalar"])
            assert top.get("/deneme") == 1
        finally:
            c.__exit__(None, None, None)

    def test_gpc_sayilmaz(self, monkeypatch):
        c = _istemci(monkeypatch, token=TOKEN)
        try:
            r = c.post("/api/olcum", json={"yol": "/deneme"},
                       headers={"Sec-GPC": "1"})
            assert r.json() == {"ok": True, "sayildi": False}
            assert dict(c.get(
                "/api/olcum",
                headers={"X-Basak-Token": TOKEN}).json()["sayfalar"]) == {}
        finally:
            c.__exit__(None, None, None)

    def test_cerez_yazilmaz(self, monkeypatch):
        c = _istemci(monkeypatch, token=TOKEN)
        try:
            r = c.post("/api/olcum", json={"yol": "/deneme"})
            assert "set-cookie" not in r.headers
            r = c.get("/api/olcum", headers={"X-Basak-Token": TOKEN})
            assert "set-cookie" not in r.headers
        finally:
            c.__exit__(None, None, None)


class TestYoneticiRaporu:
    def test_tokensiz_kapali(self, monkeypatch):
        c = _istemci(monkeypatch)
        try:
            assert c.get("/api/olcum").status_code != 200
        finally:
            c.__exit__(None, None, None)

    def test_gun_parametresi(self, monkeypatch):
        c = _istemci(monkeypatch, token=TOKEN)
        try:
            baslik = {"X-Basak-Token": TOKEN}
            assert c.get("/api/olcum", headers=baslik).json()[
                "gun_sayisi"] == 7
            assert c.get("/api/olcum?gun=1", headers=baslik).json()[
                "gun_sayisi"] == 1
            assert c.get("/api/olcum?gun=bozuk", headers=baslik).json()[
                "gun_sayisi"] == 7
        finally:
            c.__exit__(None, None, None)

class TestOy:
    def test_gecerli_oy_kaydedilir(self, monkeypatch):
        c = _istemci(monkeypatch, token=TOKEN)
        try:
            baslik = {"X-Basak-Token": TOKEN}
            assert c.post("/api/oy",
                          json={"yol": "/deneme", "oy": 1}
                          ).status_code == 200
            assert c.post("/api/oy",
                          json={"yol": "/deneme", "oy": -1}
                          ).status_code == 200
            oylar = c.get("/api/olcum", headers=baslik).json()["oylar"]
            assert ["/deneme", 1, 1] in oylar
        finally:
            c.__exit__(None, None, None)

    def test_gecersiz_oy_reddedilir(self, monkeypatch):
        c = _istemci(monkeypatch)
        try:
            for govde in ({"yol": "/deneme", "oy": 5},
                          {"yol": "/deneme", "oy": True},
                          {"yol": "/deneme", "oy": "1"},
                          {"yol": "/deneme"},
                          {"yol": "disarda", "oy": 1},
                          {"oy": 1}):
                assert c.post("/api/oy", json=govde).status_code == 400, govde
        finally:
            c.__exit__(None, None, None)


class TestMetinlerVeBetik:
    def test_gizlilik_anlatir(self):
        metin = (WEB / "gizlilik.html").read_text(encoding="utf-8")
        assert "Anonim sayfa sayacı" in metin
        assert "DNT/GPC" in metin

    def test_cerez_anlatir(self):
        metin = (WEB / "cerez.html").read_text(encoding="utf-8")
        assert "Çerezsiz anonim sayım (onay gerektirmez)" in metin

    def test_envanter_ve_bilgilendirme_anlatir(self):
        envanter = (Path(__file__).resolve().parents[1]
                    / "docs" / "KVKK-ENVANTER.md").read_text(
                        encoding="utf-8")
        assert "Anonim sayfa görüntüleme sayacı" in envanter
        assert "Araç mikro-geri bildirimi" in envanter
        bilgi = (WEB / "bilgilendirme.html").read_text(encoding="utf-8")
        assert "anonim toplam" in bilgi

    def test_arac_sayfasi_betigi_tasir(self):
        with TestClient(app.app, base_url="https://ornek.test") as c:
            h = c.get(ORNEK).text
        assert "/olcum.js" in h
        index = (WEB / "index.html").read_text(encoding="utf-8")
        assert 'src="/olcum.js' in index

    def test_betik_harici_adres_ve_cerez_kullanmaz(self):
        js = (WEB / "olcum.js").read_text(encoding="utf-8")
        assert "/api/olcum" in js and "/api/oy" in js
        assert "sendBeacon" in js
        assert not re.search(r"https?://", js)
        assert "document.cookie" not in js
        assert "fetch(" not in js
class TestKimliksizTavan:
    """Koruma kisisel veri URETMEDEN calismalidir (2026-09-30).

    Temel ilke: kotu kullanim durdurulurken IP/cerez/oturum sayaca
    baglanmaz. Aksi halde cerez.html + gizlilik.html +
    KVKK-ENVANTER.md'teki "IP saklamiyoruz" beyani tutarsiz hale gelir.
    """

    def test_tavan_env_ile_ayarlanir(self, monkeypatch):
        monkeypatch.setenv("BASAK_OLCUM_GUNLUK_TAVAN", "7")
        assert olcum._tavan_env() == 7
        monkeypatch.setenv("BASAK_OLCUM_GUNLUK_TAVAN", "0")
        assert olcum._tavan_env() == olcum.VARSAYILAN_GUNLUK_TAVAN
        monkeypatch.setenv("BASAK_OLCUM_GUNLUK_TAVAN", "bozuk")
        assert olcum._tavan_env() == olcum.VARSAYILAN_GUNLUK_TAVAN
        monkeypatch.delenv("BASAK_OLCUM_GUNLUK_TAVAN", raising=False)
        assert olcum._tavan_env() == olcum.VARSAYILAN_GUNLUK_TAVAN

    def test_tavan_oyu_kapatir(self, monkeypatch):
        monkeypatch.setenv("BASAK_OLCUM_GUNLUK_TAVAN", "3")
        olcum.sifirla()
        sonuc = [olcum.oy_ekle(ORNEK, 1) for _ in range(5)]
        assert sonuc == [True, True, True, False, False]
        olcum.sifirla()

    def test_tavan_saymayi_durdurur_hata_vermez(self, monkeypatch):
        """Asilirsa hata vermez; yalniz saymaz (veri bozulmaz)."""
        monkeypatch.setenv("BASAK_OLCUM_GUNLUK_TAVAN", "2")
        olcum.sifirla()
        for _ in range(5):
            assert olcum.say(ORNEK) is True
        rapor = olcum.rapor(1)
        adet = [s[1] for s in rapor["sayfalar"] if s[0] == ORNEK]
        assert adet == [2], rapor["sayfalar"]
        olcum.sifirla()

    def test_tavan_kimlik_tutmaz(self):
        """Sayac yalniz gun ile iliskilidir; kimlik KAYNAGI CAGIRILMAZ.

        Not: metin icinde 'ip' kelimesi yorumlarda gecer (beyan).
        Gercek risk, IP'yi/oturumu SISTEME DOKUNDURAN bir cagridir.
        """
        import inspect
        kaynak = inspect.getsource(olcum)
        for yasak in ("client.host", "x-forwarded-for", "cf-connecting-ip",
                      "user-agent", "set_cookie", "cookie", "request."):
            assert yasak not in kaynak.lower(), yasak
        # Tablo semasinda kimlik sutunu OLMAMALI. Sadece sayim sutunlari
        # (yol/gun/adet/arti/eksi) serbest — bunlar kimseye baglanmaz.
        sema = inspect.getsource(olcum._tablolari_kur).lower()
        for sutun in ("ip", "kid", "user_id", "token", "cerez",
                      "kullanici", "oturum", "fingerprint"):
            assert sutun not in sema, sutun

    def test_sifirla_temizler(self, monkeypatch):
        monkeypatch.setenv("BASAK_OLCUM_GUNLUK_TAVAN", "100")
        olcum.sifirla()
        olcum.say(ORNEK)
        assert olcum._bellek_tavan, "sayac bosalmamis"
        olcum.sifirla()
        assert not olcum._bellek_tavan

    def test_uc_tavan_asiminda_400_doner(self, monkeypatch):
        monkeypatch.setenv("BASAK_OLCUM_GUNLUK_TAVAN", "1")
        with TestClient(app.app, base_url="https://ornek.test") as c:
            c.post("/api/oy", json={"yol": ORNEK, "oy": 1})
            r = c.post("/api/oy", json={"yol": ORNEK, "oy": 1})
        assert r.status_code == 400
        assert "Gecersiz yol" in r.text or "Gecersiz" in r.text
        olcum.sifirla()
class TestSaglayiciSeffafligi:
    """Kullanici saglayicinin veri kartini gormeli (2026-09-30)."""

    def test_uc_dogru_veri_donuyor(self):
        with TestClient(app.app, base_url="https://ornek.test") as c:
            r = c.get("/api/saglayici-veri")
        assert r.status_code == 200
        satirlar = r.json()["saglayicilar"]
        assert satirlar, "tablo bos"
        for s in satirlar:
            assert s["ad"] and s["durum"] and s["aciklama"]
            assert s["durum"] in ("kaydetmez", "kaydeder",
                                  "egitime_kullanilir", "dogrulanmadi")

    def test_uc_kimlik_gerektirmez(self):
        """Saglayici listesi herkese aciktir (zaten herkese acik veri)."""
        with TestClient(app.app, base_url="https://ornek.test") as c:
            r = c.get("/api/saglayici-veri")
        assert r.status_code == 200
        assert "set-cookie" not in r.headers.get("set-cookie", "")

    def test_gizlilik_sayfasi_tablosu_tasir(self):
        html = (WEB / "gizlilik.html").read_text(encoding="utf-8")
        assert "/saglayici-veri.js" in html
        assert 'id="saglayici-tablosu"' in html
        # Sohbet gizliligi anlatilir (dosyanin ilk kismi zaten vardi)
        assert "Sağlayıcıya giden mesaj" in html

    def test_betik_harici_adres_kullanmaz(self):
        js = (WEB / "saglayici-veri.js").read_text(encoding="utf-8")
        assert not re.search(r"https?://", js)
        assert "/api/saglayici-veri" in js
        assert "document.cookie" not in js

    def test_betik_dogrulanmadigi_olguyle_gosterir(self):
        """Bilinmeyen icin IDDIA yok: ne saklar ne saklamaz denmez."""
        js = (WEB / "saglayici-veri.js").read_text(encoding="utf-8")
        assert "dogrulanmadi" in js
        assert "Doğrulanmadı" in js
        # Kullaniciya gosterilen METIN icinde tahmin/varsayim olmamali
        # (yorum satirlari test kapsam disi)
        gosterilen = "\n".join(
            satir for satir in js.splitlines()
            if not satir.strip().startswith(("//", "*", "/*"))
        ).lower()
        assert "varsay" not in gosterilen
        assert "tahmin" not in gosterilen

    def test_gizlilik_metni_bilinmeyende_iddia_surmuyor(self):
        """Beyan metni de ayni durustu tasi: iddia yok, resmi belge var."""
        html = (WEB / "gizlilik.html").read_text(encoding="utf-8")
        assert "hiçbir iddia" in html
        assert "resmî belgelerdir" in html
        # Eskiden "en kotu durum varsayilir" yaziyordu; kaldirildi
        assert "en kötü durum (saklama) varsayılır" not in html

    def test_uc_zincir_sirasini_degistirmiyor(self):
        """Saglayici veri ucu sirayi TETIKLEMEZ."""
        from brain import registry
        with TestClient(app.app, base_url="https://ornek.test") as c:
            c.get("/api/saglayici-veri")
        assert registry.VARSAYILAN_SIRA == [
            "groq", "gemini", "cloudflare", "kilo", "nvidia",
            "glm", "openrouter", "cohere", "mistral",
            "sambanova",
            # 2026-10-02: LLM7.io — veri karti "dogrulanmadi"
            # olsa da zincire girmesi sirayi TETIKLEMEZ; sira yine
            # yalniz registry'nin kendi sabididir.
            "llm7"]
