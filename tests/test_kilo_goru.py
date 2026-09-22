from tools import image_analyzer as ga


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
