"""Kalici kosu defteri (chat/kosu_deposu) testleri.

Olculen sozlesme:
- Kosu ve her arac adimi kalici deftere yazilir.
- Ayni cagri kimligi ikinci kez kapandiysa satir EZILMEZ.
- Mola, cekirdegin kabul ettigi `p2-handoff-v1` devam paketini uretir.
- Baska kullanicinin kosusu okunamaz.
- Uretimde DSN yoksa defter kapalidir; gecici diske "kalici" denmez.
"""

import json

import pytest

from chat import kosu_deposu as kd


@pytest.fixture(autouse=True)
def _defter(tmp_path, monkeypatch):
    monkeypatch.setenv("BASAK_STATE_DIR", str(tmp_path))
    for ad in ("DATABASE_URL", "POSTGRES_URL", "NEON_DATABASE_URL",
               "VERCEL", "BASAK_URETIM", "BASAK_PREVIEW_DATABASE_URL"):
        monkeypatch.delenv(ad, raising=False)
    kd.sifirla()
    yield
    kd.sifirla()


def test_kosu_acilir_ve_adim_deftere_yazilir():
    kosu = kd.ac("casper", "fiyatlari topla")
    assert kosu is not None
    assert kosu.durum == "running"
    assert kosu.istek == "fiyatlari topla"
    assert kosu.ozet()["adim"] == 0

    kosu.adim_basla("web_search", "c1", {"q": "kahve"}, tur=1)
    assert kosu.adim_bitti("web_search", "c1", "sonuc-1", True) is True

    ozet = kosu.ozet()
    assert ozet["adim"] == 1
    assert ozet["araclar"] == ["web_search"]
    assert kosu.adim_onceki("c1") == {
        "arac": "web_search", "sonuc": "sonuc-1", "ok": True,
    }


def test_ayni_cagri_ikinci_kez_kapanmaz():
    kosu = kd.ac("casper", "is")
    kosu.adim_basla("sayfa_tikla", "c9", {"ref": "abc"}, tur=1)
    assert kosu.adim_bitti("sayfa_tikla", "c9", "ilk", True) is True
    # Ayni cagri kimligi ikinci kez: satir EZILMEZ, adim sayisi artmaz.
    assert kosu.adim_bitti("sayfa_tikla", "c9", "ikinci", True) is False
    assert kosu.ozet()["adim"] == 1
    assert kosu.adim_onceki("c9")["sonuc"] == "ilk"


def test_mola_devam_paketi_uretir():
    kosu = kd.ac("casper", "bes fiyat karsilastir")
    kosu.adim_basla("web_search", "c1", {"q": "a"}, tur=1)
    kosu.adim_bitti("web_search", "c1", "A SONUCU", True)
    kosu.adim_basla("sayfa_oku", "c2", {"url": "https://x"}, tur=1)
    kosu.adim_bitti("sayfa_oku", "c2", "B SONUCU", False)
    kosu.duraklat()

    paket = kosu.kayitli_devam()
    assert paket["schema"] == "p2-handoff-v1"
    olaylar = paket["olaylar"]
    assert olaylar[0]["tur"] == "runContext"
    assert olaylar[0]["metin"] == "bes fiyat karsilastir"
    adimlar = [o for o in olaylar if o["tur"] == "toolDone"]
    assert [o["name"] for o in adimlar] == ["web_search", "sayfa_oku"]
    assert adimlar[0]["result"] == "A SONUCU"
    assert adimlar[1]["ok"] is False
    assert json.loads(json.dumps(paket)) == paket  # JSON'a yazilabilir
    assert kosu.durum == "paused"


def test_baska_kullanici_kosuyu_goremez():
    kosu = kd.ac("casper", "ozel is")
    assert kd.yukle(kosu.id, "casper") is not None
    assert kd.yukle(kosu.id, "baska") is None


def test_defter_yeniden_acilinca_kayit_kalir(tmp_path):
    kosu = kd.ac("casper", "kalici is")
    kosu.adim_basla("web_search", "c1", {}, tur=1)
    kosu.adim_bitti("web_search", "c1", "sonuc", True)

    # Yeni "surec": defter nesnesi sifirlanir, dosya yerinde kalir.
    kd.sifirla()
    tekrar = kd.yukle(kosu.id, "casper")
    assert tekrar is not None
    assert tekrar.ozet()["adim"] == 1


def test_baskasinin_kosu_kimligi_devralinmaz():
    """Ayni run_id baska kullaniciya denk gelirse satir KULLANILMAZ."""
    ilk = kd.ac("casper", "casper isi", run_id="paylasilan")
    baska = kd.ac("baska", "baska isi", run_id="paylasilan")
    assert baska.id != ilk.id
    assert baska.istek == "baska isi"
    assert baska.kullanici == "baska"


def test_ayni_run_id_ikinci_kez_yeni_satir_acmaz():
    ilk = kd.ac("casper", "ilk metin", run_id="sabit-kimlik")
    ikinci = kd.ac("casper", "baska metin", run_id="sabit-kimlik")
    assert ilk.id == ikinci.id
    assert ikinci.istek == "ilk metin"


def test_uretimde_dsn_yoksa_defter_kapali(monkeypatch):
    monkeypatch.setenv("BASAK_URETIM", "1")
    kd.sifirla()
    assert kd.hazir() is False
    assert kd.ac("casper", "is") is None
    assert kd.yukle("herhangi") is None


def test_bitir_durumu_ve_cevabi_yazar():
    kosu = kd.ac("casper", "is")
    kosu.bitir("completed", cevap="bitti")
    tekrar = kd.yukle(kosu.id, "casper")
    assert tekrar.durum == "completed"
    assert tekrar.ozet()["cevap"] == "bitti"
    assert tekrar.ozet()["devam_var"] is False


def test_kosu_ucu_kimliksiz_acilmaz(monkeypatch, tmp_path):
    """`/api/kosu/{id}` kimlik ister; kimliksiz 401."""
    from fastapi.testclient import TestClient

    monkeypatch.setenv("BASAK_URETIM", "1")
    monkeypatch.setenv("BASAK_STATE_DIR", str(tmp_path / "durum"))
    monkeypatch.setenv("BASAK_WEB_TOKEN", "test-anahtar")
    import app as app_modulu
    monkeypatch.setattr(app_modulu, "_hafizayi_bir_kez_sifirla",
                        lambda: True)
    with TestClient(app_modulu.app) as istemci:
        cevap = istemci.get("/api/kosu/herhangi")
    assert cevap.status_code == 401, cevap.text


def test_bozuk_devam_paketi_uydurulmaz():
    """Bozuk JSON sessizce yutulmaz; "devam yok" doner."""
    kosu = kd.ac("casper", "is")
    depo = kosu._depo
    depo.kosu_guncelle(kosu.id, {"devam": "{bozuk"})
    okunan = kd.yukle(kosu.id, "casper")
    assert okunan.kayitli_devam() is None
