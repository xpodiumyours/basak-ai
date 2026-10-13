"""tests/test_goru_yedekleri.py — görüntü zincirindeki ek gözler.

Sözleşme: bakış zinciri nvidia -> gemini -> groq -> cloudflare -> kilo
sırasıyla koşar; anahtarı olmayan göz çağrı YAPMADAN atlanır ve gerekçesi
hata listesine yazılır. Hiçbir göz sonuç veremezse hata metni her gözün
kendi nedenini taşır (kullanıcı sebebi görebilsin).

Ağ yok: openai istemcisi ve requests sahtelenir.
"""

import base64
import json

import pytest

from tools import image_analyzer as ga

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8"
    "z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")


@pytest.fixture()
def foto(tmp_path):
    yol = tmp_path / "fatura.png"
    yol.write_bytes(PNG)
    return str(yol)


@pytest.fixture(autouse=True)
def _ayarsiz(monkeypatch, tmp_path):
    """Yerel ayarlar.json testi etkilemesin; anahtarlar yalnız monkeypatch ile."""
    monkeypatch.setattr(ga, "_AYARLAR_DOSYASI",
                        str(tmp_path / "yok.json"))
    for ad in ("GROQ_API_KEY", "GEMINI_API_KEY", "NVIDIA_API_KEY",
               "CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_API_TOKEN"):
        monkeypatch.delenv(ad, raising=False)


# ── Groq gözü ───────────────────────────────────────────────────────

def test_groq_anahtari_yoksa_cagri_yapilmaz(monkeypatch, foto):
    cagrildi = []
    monkeypatch.setattr("openai.OpenAI",
                        lambda *a, **k: cagrildi.append("istemci"))
    sonuc = ga._groq_goru(foto, "oku")
    assert sonuc == {"error": "Groq anahtari yok"}
    assert cagrildi == []


def test_groq_gozu_dogru_uc_ve_modele_multimodal_gonderir(monkeypatch, foto):
    yakalanan = {}

    class SahteIstek:
        def __init__(self):
            self.choices = [type("S", (), {"message": type(
                "M", (), {"content": "fatura okundu"})()})()]

    class SahteChat:
        def create(self, **kwargs):
            yakalanan["create"] = kwargs
            return SahteIstek()

    class SahteOpenAI:
        def __init__(self, **kwargs):
            yakalanan["istemci"] = kwargs
            self.chat = type("C", (), {"completions": SahteChat()})()

    monkeypatch.setenv("GROQ_API_KEY", "test-groq-anahtari")
    monkeypatch.setattr("openai.OpenAI", SahteOpenAI)

    sonuc = ga._groq_goru(foto, "Bu faturayi oku")

    assert sonuc["result"] == "fatura okundu"
    assert sonuc["model"] == ga.GROQ_GORU_MODEL
    assert yakalanan["istemci"]["base_url"] == "https://api.groq.com/openai/v1"
    assert yakalanan["istemci"]["api_key"] == "test-groq-anahtari"
    assert yakalanan["istemci"]["max_retries"] == 0
    assert yakalanan["create"]["model"] == ga.GROQ_GORU_MODEL
    parcalar = yakalanan["create"]["messages"][0]["content"]
    assert parcalar[0]["type"] == "text"
    assert parcalar[1]["image_url"]["url"].startswith("data:image/png;base64,")


def test_groq_gozu_bos_yaniti_hata_sayar(monkeypatch, foto):
    class SahteOpenAI:
        def __init__(self, **kwargs):
            self.chat = type("C", (), {"completions": type("D", (), {
                "create": lambda _s, **k: type("R", (), {"choices": [
                    type("S", (), {"message": type(
                        "M", (), {"content": "   "})()})()]})()})()})()

    monkeypatch.setenv("GROQ_API_KEY", "test-groq-anahtari")
    monkeypatch.setattr("openai.OpenAI", SahteOpenAI)

    sonuc = ga._groq_goru(foto, "oku")
    assert "Groq bos dondu" in sonuc["error"]


# ── Cloudflare gözü ─────────────────────────────────────────────────

def test_cloudflare_anahtari_yoksa_cagri_yapilmaz(monkeypatch, foto):
    import requests
    cagrildi = []
    monkeypatch.setattr(requests, "post",
                        lambda *a, **k: cagrildi.append("post"))
    sonuc = ga._cloudflare_goru(foto, "oku")
    assert sonuc == {"error": "Cloudflare anahtari yok"}
    assert cagrildi == []


def test_cloudflare_gozu_veri_uri_gonderir_ve_yaniti_cozer(monkeypatch, foto):
    import requests
    yakalanan = {}

    class SahteYanit:
        status_code = 200

        def json(self):
            return {"success": True, "errors": [],
                    "result": {"response": "urun listesi okundu"}}

    def sahte_post(url, **kwargs):
        yakalanan["url"] = url
        yakalanan["kwargs"] = kwargs
        return SahteYanit()

    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "hesap123")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "test-cf-token")
    monkeypatch.setattr(requests, "post", sahte_post)

    sonuc = ga._cloudflare_goru(foto, "Bu faturayi oku")

    assert sonuc["result"] == "urun listesi okundu"
    assert sonuc["model"] == ga.CLOUDFLARE_GORU_MODEL
    assert yakalanan["url"].endswith(
        "/accounts/hesap123/ai/run/" + ga.CLOUDFLARE_GORU_MODEL)
    basliklar = yakalanan["kwargs"]["headers"]
    assert basliklar["Authorization"] == "Bearer test-cf-token"
    parcalar = yakalanan["kwargs"]["json"]["messages"][0]["content"]
    assert parcalar[1]["image_url"]["url"].startswith("data:image/png;base64,")


def test_cloudflare_success_false_gerekceyi_tasir(monkeypatch, foto):
    import requests

    class SahteYanit:
        status_code = 400

        def json(self):
            return {"success": False,
                    "errors": [{"code": 7000, "message": "model yok"}]}

    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "hesap123")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "test-cf-token")
    monkeypatch.setattr(requests, "post", lambda *a, **k: SahteYanit())

    sonuc = ga._cloudflare_goru(foto, "oku")
    assert "Cloudflare hata" in sonuc["error"]
    assert "model yok" in sonuc["error"]


def test_cloudflare_gecersiz_govde_hata_doner(monkeypatch, foto):
    import requests

    class SahteYanit:
        status_code = 502

        def json(self):
            raise ValueError("html dondü")

    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "hesap123")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "test-cf-token")
    monkeypatch.setattr(requests, "post", lambda *a, **k: SahteYanit())

    sonuc = ga._cloudflare_goru(foto, "oku")
    assert "gecersiz yanit" in sonuc["error"]
    assert "502" in sonuc["error"]


def test_cloudflare_ayarlar_dosyasindan_anahtar_okur(monkeypatch, foto, tmp_path):
    import requests
    dosya = tmp_path / "ayarlar.json"
    dosya.write_text(json.dumps({"cloudflare_account_id": "hesapA",
                                 "cloudflare_api_token": "tokenA"}),
                     encoding="utf-8")
    monkeypatch.setattr(ga, "_AYARLAR_DOSYASI", str(dosya))

    class SahteYanit:
        status_code = 200

        def json(self):
            return {"success": True, "result": {"response": "ok"}}

    yakalanan = {}
    monkeypatch.setattr(requests, "post", lambda url, **k: (
        yakalanan.update({"url": url}), SahteYanit())[1])

    sonuc = ga._cloudflare_goru(foto, "oku")
    assert sonuc["result"] == "ok"
    assert "/accounts/hesapA/" in yakalanan["url"]


# ── Zincir sırası ───────────────────────────────────────────────────

def test_zincir_sirasi_groq_tutmazsa_cloudflare_devralir(monkeypatch, foto):
    cagrilar = []
    monkeypatch.setattr(ga, "_nvidia_key_al", lambda: "")
    monkeypatch.setattr(ga, "_gemini_goru", lambda *a, **k: (
        cagrilar.append("gemini") or {"error": "Gemini anahtari yok"}))
    monkeypatch.setattr(ga, "_groq_goru", lambda *a, **k: (
        cagrilar.append("groq") or {"error": "Groq bos dondu"}))
    monkeypatch.setattr(ga, "_cloudflare_goru", lambda *a, **k: (
        cagrilar.append("cloudflare") or {"result": "tamam", "model": "cf"}))
    monkeypatch.setattr(ga, "_kilo_goru", lambda *a, **k: (
        cagrilar.append("kilo") or {"result": "olmaz", "model": "k"}))

    sonuc = ga.image_analyze(foto, "oku")

    assert sonuc["result"] == "tamam"
    assert sonuc["yedek"] == "cloudflare"
    assert cagrilar == ["gemini", "groq", "cloudflare"]


def test_tum_gozler_kapaliysa_her_gerekce_hata_metninde(monkeypatch, foto):
    monkeypatch.setattr(ga, "_nvidia_key_al", lambda: "")
    monkeypatch.setattr(ga, "_gemini_goru", lambda *a, **k: {
        "error": "Gemini anahtari yok"})
    monkeypatch.setattr(ga, "_groq_goru", lambda *a, **k: {
        "error": "Groq anahtari yok"})
    monkeypatch.setattr(ga, "_cloudflare_goru", lambda *a, **k: {
        "error": "Cloudflare anahtari yok"})
    monkeypatch.setattr(ga, "_kilo_goru", lambda *a, **k: {
        "error": "Kilo goru calismadi: 404"})

    sonuc = ga.image_analyze(foto, "oku")

    assert "error" in sonuc
    for ad in ("gemini", "groq", "cloudflare", "kilo"):
        assert ad in sonuc["error"]


def test_butce_ek_gozlere_de_ayni_deadline_ile_gecer(monkeypatch, foto):
    import time
    monkeypatch.setattr(ga, "_nvidia_key_al", lambda: "")
    gorulen = []

    def _kayit(ad, sonuc):
        def _sahte(*args, **kwargs):
            gorulen.append((ad, kwargs.get("deadline_monotonic")))
            return sonuc
        return _sahte

    monkeypatch.setattr(ga, "_gemini_goru",
                        _kayit("gemini", {"error": "yok"}))
    monkeypatch.setattr(ga, "_groq_goru", _kayit("groq", {"error": "yok"}))
    monkeypatch.setattr(ga, "_cloudflare_goru",
                        _kayit("cloudflare", {"error": "yok"}))
    monkeypatch.setattr(ga, "_kilo_goru",
                        _kayit("kilo", {"result": "gordum", "model": "k"}))

    bas = time.monotonic()
    sonuc = ga.image_analyze(foto, "oku")

    assert sonuc["result"] == "gordum"
    assert [ad for ad, _ in gorulen] == ["gemini", "groq", "cloudflare", "kilo"]
    son_deadline = gorulen[-1][1]
    assert gorulen[0][1] == son_deadline
    assert bas < son_deadline <= bas + ga.GORUNTU_TOPLAM_BUTCE_SN + 1


def test_saglayici_butceleri_tanimli():
    for ad in ("nvidia", "gemini", "groq", "cloudflare", "kilo"):
        assert ga._SAGLAYICI_BUTCE_SN[ad] >= ga._MIN_CAGRI_SN


# ── Boyut kapısı ve küçültme ─────────────────────────────────────────
def _buyuk_png(tmp_path, ad="telefon.png"):
    """10.8 MP rastgele PNG: ham hâli 10 MB kapısını AŞAR (telefon fotoğrafı)."""
    import os as _os
    from PIL import Image
    yol = tmp_path / ad
    genislik, yukseklik = 2400, 1500
    resim = Image.frombytes(
        "RGB", (genislik, yukseklik),
        _os.urandom(genislik * yukseklik * 3))
    resim.save(yol)
    assert yol.stat().st_size > 10 * 1024 * 1024
    return yol


def test_asiri_buyuk_fotograf_kucultulur_ve_gonderilir(tmp_path):
    """Boyut kapısı normalizasyondan SONRA: fotoğraf 10 MB'ı aşsa da göze gider."""
    yol = _buyuk_png(tmp_path)
    veri, mime = ga._goruntu_b64(str(yol))
    govde = base64.b64decode(veri)
    assert mime == "image/jpeg"
    assert len(govde) < 10 * 1024 * 1024
    assert len(govde) < yol.stat().st_size


def test_pillow_yokken_asiri_buyuk_gorsel_reddedilir(monkeypatch, tmp_path):
    """Pillow kurulu değilse küçültme yapılamaz; kapı yine de kapanır."""
    import sys as _sys
    yol = tmp_path / "ham.png"
    yol.write_bytes(b"\x00" * (11 * 1024 * 1024))
    monkeypatch.setitem(_sys.modules, "PIL", None)
    with pytest.raises(ValueError):
        ga._goruntu_b64(str(yol))
