"""Ucretsiz model zincirinin kota ve geri-cekilme regresyon testleri."""

from types import SimpleNamespace


def test_resmi_sabit_kota_kartlari():
    from brain import registry

    groq = registry.kart("groq")
    assert groq["dakikalik_istek"] == 30
    assert groq["gunluk_istek"] == 1000
    assert groq["dakikalik_token"] == 8000
    assert groq["gunluk_token"] == 200000

    assert registry.kart("openrouter")["gunluk_istek"] == 50
    assert registry.kart("kilo")["saatlik_istek"] == 200
    assert registry.kart("cohere")["aylik_istek"] == 1000

    # Gemini/NVIDIA gibi hesap/model bazli degisen kotalar uydurulmaz.
    assert registry.kart("gemini")["gunluk_istek"] is None
    assert registry.kart("nvidia")["gunluk_istek"] is None


def test_retry_after_http_basligi_onceliklidir():
    from brain.brain import _bekleme_suresi

    hata = RuntimeError("429 rate limit")
    hata.response = SimpleNamespace(headers={"retry-after": "47"})
    assert _bekleme_suresi(hata) == 47.0


def test_groq_reset_suresi_bilesik_birim_okunur():
    from brain.brain import _bekleme_suresi

    hata = RuntimeError("429")
    hata.response = SimpleNamespace(
        headers={"x-ratelimit-reset-tokens": "2m30s"})
    assert _bekleme_suresi(hata) == 150.0


def test_hata_metnindeki_retry_suresi_yedek_yoldur():
    from brain.brain import _bekleme_suresi

    assert _bekleme_suresi(
        RuntimeError("rate limit; try again in 10.7s")) == 10.7


class _Istat:
    def __init__(self, saat=0, gun=0, ay=0, token=(0, 0)):
        self.deger = {"saat": saat, "gun": gun, "ay": ay}
        self.token = token

    def istek_sayisi(self, model, pencere):
        return self.deger[pencere]

    def token_bugun(self, model):
        return self.token


def test_bilinen_kota_dolunca_api_denemesi_yapilmaz():
    from brain.brain import _yerel_kota_doldu

    assert _yerel_kota_doldu("openrouter", _Istat(gun=50)) == (
        "gunluk istek kotasi")
    assert _yerel_kota_doldu("kilo", _Istat(saat=200)) == (
        "saatlik istek kotasi")
    assert _yerel_kota_doldu("cohere", _Istat(ay=1000)) == (
        "aylik istek kotasi")
    # Groq org limiti hesap bazinda degisebildigi icin statik kart
    # bilgilendirme amaclidir; sert kesme 429/reset sinyaline birakilir.
    assert _yerel_kota_doldu(
        "groq", _Istat(gun=1000, token=(150000, 50000))) == ""


def test_degisken_kotaya_sahte_tavan_konmaz():
    from brain.brain import _yerel_kota_doldu

    assert _yerel_kota_doldu("gemini", _Istat(
        saat=999999, gun=999999, ay=999999, token=(999999, 999999))) == ""
    assert _yerel_kota_doldu("nvidia", _Istat(
        saat=999999, gun=999999, ay=999999, token=(999999, 999999))) == ""
