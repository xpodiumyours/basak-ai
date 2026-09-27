from tools import image_analyzer as ga


def test_buyuk_gorsel_kucultulur(tmp_path):
    """700 KB'ı aşan görsel küçültülüp JPEG'e çevrilir (NVIDIA duvarı)."""
    import base64 as b64m
    import io
    import os
    from PIL import Image
    yol = tmp_path / "buyuk.png"
    gorsel = Image.frombytes("RGB", (1500, 1100),
                             os.urandom(1500 * 1100 * 3))
    gorsel.save(yol)
    orijinal = yol.read_bytes()
    assert len(orijinal) > 700 * 1024
    veri, mime = ga._goruntu_b64(str(yol))
    govde = b64m.b64decode(veri)
    assert mime == "image/jpeg"
    assert len(govde) < len(orijinal)
    assert max(Image.open(io.BytesIO(govde)).size) <= 1600


def test_kucuk_gorsel_degistirilmez(tmp_path):
    from PIL import Image
    yol = tmp_path / "kucuk.png"
    Image.new("RGB", (100, 80), "white").save(yol)
    orijinal = yol.read_bytes()
    veri, mime = ga._goruntu_b64(str(yol))
    import base64 as b64m
    assert b64m.b64decode(veri) == orijinal
    assert mime == "image/png"


def test_nvidia_yokken_kilo_goru_yedegi(monkeypatch, tmp_path):
    foto = tmp_path / "foto.jpg"
    foto.write_bytes(b"test")

    monkeypatch.setattr(ga, "_nvidia_key_al", lambda: "")
    monkeypatch.setattr(ga, "_gemini_goru",
                        lambda yol, soru, deadline_monotonic=None: {"error": "Gemini anahtari yok"})
    monkeypatch.setattr(ga, "_kilo_goru",
                        lambda yol, soru, deadline_monotonic=None: {"result": "gordum", "model": "kilo"})

    sonuc = ga.image_analyze(str(foto), "Ne goruyorsun?")
    assert sonuc["result"] == "gordum"
    assert sonuc["yedek"] == "kilo"


def test_kilo_goru_multimodal_mesaj_gonderir(monkeypatch, tmp_path):
    foto = tmp_path / "foto.jpg"
    foto.write_bytes(b"test")
    yakalanan = {}

    class SahteKilo:
        def __init__(self, model=None):
            yakalanan["model"] = model

        def goru_cevapla(self, messages, timeout=None):
            yakalanan["messages"] = messages
            yakalanan["timeout"] = timeout
            return {"content": "resim aciklamasi"}

    import brain.kilo
    monkeypatch.setattr(brain.kilo, "KiloClient", SahteKilo)

    sonuc = ga._kilo_goru(str(foto), "Bu nedir?")
    assert sonuc["result"] == "resim aciklamasi"
    assert yakalanan["model"] == "stepfun/step-3.7-flash:free"
    parcalar = yakalanan["messages"][0]["content"]
    assert parcalar[0]["type"] == "text"
    assert parcalar[1]["type"] == "image_url"
    assert parcalar[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")


def test_exif_yonu_normalize_edilir(tmp_path):
    import base64 as b64m
    import io
    from PIL import Image
    yol = tmp_path / "donuk.jpg"
    resim = Image.new("RGB", (120, 60), "white")
    exif = resim.getexif()
    exif[274] = 6
    resim.save(yol, exif=exif)
    veri, mime = ga._goruntu_b64(str(yol))
    duz = Image.open(io.BytesIO(b64m.b64decode(veri)))
    assert mime == "image/jpeg"
    assert duz.size == (60, 120)


def test_kalite_reddi_siradaki_goze_gecer(monkeypatch, tmp_path):
    foto = tmp_path / "foto.jpg"
    foto.write_bytes(b"test")
    monkeypatch.setattr(ga, "_nvidia_key_al", lambda: "")
    cagrilar = []
    monkeypatch.setattr(ga, "_gemini_goru",
        lambda *a, **k: cagrilar.append("gemini") or {"result": "yarim", "model": "g"})
    monkeypatch.setattr(ga, "_kilo_goru",
        lambda *a, **k: cagrilar.append("kilo") or {"result": "tamam", "model": "k"})
    sonuc = ga.image_analyze(str(foto), "oku", kabul=lambda metin: metin == "tamam")
    assert sonuc["result"] == "tamam"
    assert sonuc["yedek"] == "kilo"
    assert cagrilar == ["gemini", "kilo"]


def test_varsayilan_goruntu_butcesi_tum_yedeklere_ortak(monkeypatch, tmp_path):
    import time
    foto = tmp_path / "foto.jpg"
    foto.write_bytes(b"test")
    monkeypatch.setattr(ga, "_nvidia_key_al", lambda: "")
    gorulen = []

    def gemini(*args, **kwargs):
        gorulen.append(kwargs.get("deadline_monotonic"))
        return {"error": "gecici"}

    def kilo(*args, **kwargs):
        gorulen.append(kwargs.get("deadline_monotonic"))
        return {"result": "gordum", "model": "kilo"}

    monkeypatch.setattr(ga, "_gemini_goru", gemini)
    monkeypatch.setattr(ga, "_kilo_goru", kilo)
    bas = time.monotonic()
    sonuc = ga.image_analyze(str(foto), "Ne goruyorsun?")
    assert sonuc["result"] == "gordum"
    assert len(gorulen) == 2
    assert gorulen[0] == gorulen[1]
    assert bas < gorulen[0] <= bas + ga.GORUNTU_TOPLAM_BUTCE_SN + 1
