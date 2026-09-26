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
                        lambda yol, soru: {"error": "Gemini anahtari yok"})
    monkeypatch.setattr(ga, "_kilo_goru",
                        lambda yol, soru: {"result": "gordum", "model": "kilo"})

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

        def goru_cevapla(self, messages):
            yakalanan["messages"] = messages
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
