"""Yarim kalan kosuyu kendiliginden surdurme tetigi (P7).

Olculen sozlesme:
- `bekleyen()` moladaki kosuyu bulur; taze calisan kosuyu ATLAR.
- Bayatlamis (kesilmis istek) `running` kosu yeniden devam ettirilir.
- Eklenti yoklamasi (`kutu_al`) kosu icin `kosu_devam` isi uretir; ikinci
  yoklama ayni kosu icin ikinci tetik URETMEZ.
- Misafire tik uretilmez.

Tik, modelin yerine karar vermez: yalniz "bu kosu yarim kaldi" bilgisini
tasiyacak isi birakir; isin surdurulup surdurulmeyecegine model karar verir.
"""

import pytest

from chat import kosu_deposu as kd


@pytest.fixture(autouse=True)
def _ortam(tmp_path, monkeypatch):
    monkeypatch.setenv("BASAK_STATE_DIR", str(tmp_path))
    for ad in ("DATABASE_URL", "POSTGRES_URL", "NEON_DATABASE_URL",
               "VERCEL", "BASAK_URETIM", "BASAK_PREVIEW_DATABASE_URL"):
        monkeypatch.delenv(ad, raising=False)
    kd.sifirla()

    from tools import kutu as kutu_modulu
    monkeypatch.setattr(kutu_modulu, "_DEPO", kutu_modulu._BellekDeposu())
    yield
    kd.sifirla()


def _duraklamis_kosu(istek="fiyat karsilastir"):
    kosu = kd.ac("casper", istek)
    kosu.adim_basla("web_search", "c1", {"q": "kahve"}, tur=1)
    kosu.adim_bitti("web_search", "c1", "sonuc", True)
    kosu.duraklat()
    return kosu


def test_bekleyen_moladaki_kosuyu_bulur():
    kosu = _duraklamis_kosu()
    bulunan = kd.bekleyen("casper")
    assert bulunan is not None
    assert bulunan.id == kosu.id


def test_bekleyen_taze_calisan_kosuyu_atlar():
    kosu = _duraklamis_kosu()
    kosu.devam_et()          # devam istegi yolda: ikinci tik uretilmemeli
    assert kd.bekleyen("casper") is None


def test_bekleyen_calisan_kosuya_dokunmaz():
    """"running" iki seyi anlatir: calisan istek VE kullanicinin durdurduğu
    kosu. Ikincisini kendiliginden surdurmek "Durdur"a ragmen is yapmak
    olurdu; bu yuzden yalniz `paused` kosu tetiklenir."""
    kosu = _duraklamis_kosu()
    kosu.devam_et()
    assert kd.bekleyen("casper") is None


def test_bekleyen_baska_kullaniciya_kosu_vermez():
    _duraklamis_kosu()
    assert kd.bekleyen("baska") is None


def test_kutu_al_kosu_icin_tik_uretir_ve_tekrarlamaz():
    from chat.eklenti_ws import _kutu_al

    kosu = _duraklamis_kosu()
    is_ = _kutu_al("casper")
    assert is_ and is_.get("islem") == "kosu_devam", is_
    assert is_["veri"]["kosu_id"] == kosu.id
    # Kosu "running"a cekildi: hemen ikinci tetik uretilmez.
    ikinci = _kutu_al("casper")
    assert ikinci == {"bos": True}, ikinci


def test_kutu_al_misafire_tik_uretmez():
    from chat.eklenti_ws import _kutu_al

    _duraklamis_kosu()
    assert _kutu_al("misafir") == {"bos": True}
    assert _kutu_al("") == {"bos": True}


def test_bekleyen_kosu_yoksa_none():
    assert kd.bekleyen("casper") is None
