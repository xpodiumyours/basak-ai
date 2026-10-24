# -*- coding: utf-8 -*-
"""Belge eki, kota görünümü, kişisel talimat, hafıza ve hatırlatma testleri.

Kural: her test kanıt ölçer — uç noktanın varlığı değil, davranışı.
Depo (depo.py) YOK; her modül projenin kendi state klasörü düzenini kullanır
(`<BASAK_STATE_DIR>/<kullanici>/...`).
"""

import io
import json

import pytest

from chat import ayar, belge, hatirlatma, kullanim


@pytest.fixture()
def izole(monkeypatch, tmp_path):
    monkeypatch.setenv("BASAK_STATE_DIR", str(tmp_path / "state"))
    from chat import kimlik
    kimlik._MIGRASYON_YAPILDI = False
    yield tmp_path
    kimlik._MIGRASYON_YAPILDI = False


# ── belge ─────────────────────────────────────────────────────────────

def test_docx_uzantili_ama_pdf_olan_dosya_pdf_sayilir():
    ham = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
    assert belge.tur_belirle("rapor.docx", ham) == "pdf"


def test_pdf_destekli_olmayan_zip_reddedilir():
    import zipfile

    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w") as z:
        z.writestr("veri.txt", "x")
    with pytest.raises(belge.BelgeHatasi):
        belge.tur_belirle("arsiv.zip", tampon.getvalue())


def test_metin_dosyasi_utf8_ve_cp1254_okunur():
    cikarim = belge.metin_cikar("not.txt", "Kadıköy şube".encode("utf-8"))
    assert cikarim["tur"] == "txt"
    assert "Kadıköy" in cikarim["sayfalar"][0]["metin"]

    cikarim2 = belge.metin_cikar("not.txt", "Kadıköy şube".encode("cp1254"))
    assert "Kadıköy" in cikarim2["sayfalar"][0]["metin"]


def test_ikili_icerik_metin_sayilmaz():
    with pytest.raises(belge.BelgeHatasi):
        belge.tur_belirle("veri.txt", b"abc\x00\x01\x02")


def test_boyut_siniri_asilirsa_acik_hata():
    ham = b"a" * (belge.BOYUT_SINIR + 1)
    with pytest.raises(belge.BelgeHatasi) as hata:
        belge._metin_cikar("buyuk.txt", ham)
    assert "sinir" in str(hata.value).lower() or "MB" in str(hata.value)


def test_cikarma_sure_siniri_asilinca_hata():
    def yavas(ad, ham):
        import time
        time.sleep(0.4)
        return {"tur": "txt", "sayfalar": [{"sayfa": 1, "metin": "x"}],
                "kirpildi": False}

    eski = belge._metin_cikar
    belge._metin_cikar = yavas
    try:
        with pytest.raises(belge.BelgeHatasi) as hata:
            belge.metin_cikar("yavas.txt", b"x", sure_sinir=0.05)
        assert "süresi" in str(hata.value) or "süre" in str(hata.value)
    finally:
        belge._metin_cikar = eski


def test_istemciden_gelen_metin_sayfa_etiketi_tasir():
    blok = belge.istemciden_blogu({
        "ad": "sozlesme.pdf",
        "sayfalar": [{"sayfa": 1, "metin": "birinci"},
                     {"sayfa": 2, "metin": "ikinci"}],
    })
    assert "[sozlesme.pdf · sayfa 1]" in blok
    assert "[sozlesme.pdf · sayfa 2]" in blok
    assert "birinci" in blok and "ikinci" in blok


def test_istemciden_gelen_bos_belge_reddedilir():
    with pytest.raises(belge.BelgeHatasi):
        belge.istemciden_blogu({"ad": "x.pdf", "sayfalar": []})


def test_istemciden_gelen_metin_sinira_kirpilir():
    blok = belge.istemciden_blogu({
        "ad": "buyuk.txt",
        "sayfalar": [{"sayfa": 1, "metin": "a" * (belge.METIN_SINIR + 500)}],
    })
    assert len(blok) < belge.METIN_SINIR + 400
    assert "okunmadı" in blok


def test_data_url_cozulur_ve_bozuk_veri_reddedilir():
    import base64

    ham = b"%PDF-1.4 test"
    url = "data:application/pdf;base64," + base64.b64encode(ham).decode()
    assert belge.coz_data_url(url) == ham
    with pytest.raises(belge.BelgeHatasi):
        belge.coz_data_url("data:application/pdf;base64,@@@")


# ── kota görünümü ─────────────────────────────────────────────────────

def test_kota_ozeti_olculen_saglayicilari_dondurur(izole):
    ozet = kullanim.kota_ozeti("casper")
    assert ozet["gun"]
    assert isinstance(ozet["saglayicilar"], list)
    adlar = [s["ad"] for s in ozet["saglayicilar"]]
    assert "groq" in adlar
    for satir in ozet["saglayicilar"]:
        assert "bugun_token" in satir
        assert "gunluk_istek" in satir


def test_kota_ozeti_istatistik_hatasinda_dusmez(izole, monkeypatch):
    def patlat(*a, **k):
        raise RuntimeError("stats yok")

    import brain.stats as stats_modulu
    monkeypatch.setattr(stats_modulu, "model_stats_al", patlat)
    ozet = kullanim.kota_ozeti("casper")
    assert isinstance(ozet["saglayicilar"], list)
    assert all(s["bugun_token"] is None for s in ozet["saglayicilar"])


# ── kişisel talimat ───────────────────────────────────────────────────

def test_ayar_yazilir_ve_geri_okunur(izole):
    ayar.ayarlari_yaz("casper", kisisel_talimat="kısa yaz", hitap="Casper")
    okunan = ayar.ayarlari_al("casper")
    assert okunan["kisisel_talimat"] == "kısa yaz"
    assert okunan["hitap"] == "Casper"
    assert okunan["dil"] == ""


def test_ayar_bos_deger_alan_siler(izole):
    ayar.ayarlari_yaz("casper", hitap="Casper")
    ayar.ayarlari_yaz("casper", hitap="")
    assert ayar.ayarlari_al("casper")["hitap"] == ""


def test_ayar_kisiler_arasinda_sizmaz(izole):
    ayar.ayarlari_yaz("casper", hitap="Casper")
    assert ayar.ayarlari_al("baska")["hitap"] == ""


def test_ayar_uzunluk_siniri_uygulanir(izole):
    ayar.ayarlari_yaz("casper", kisisel_talimat="a" * (ayar.KISISEL_SINIR + 50))
    assert len(ayar.ayarlari_al("casper")["kisisel_talimat"]) == ayar.KISISEL_SINIR


def test_kisisel_blogu_talimati_aynen_tasir(izole):
    ayar.ayarlari_yaz("casper", kisisel_talimat="Bana 'patron' de.",
                      dil="Türkçe")
    blok = ayar.kisisel_blogu("casper")
    assert "Bana 'patron' de." in blok
    assert "Türkçe" in blok


def test_misafirde_kisisel_talimat_okunmaz(izole):
    ayar.ayarlari_yaz("casper", kisisel_talimat="gizli talimat")
    blok = ayar.sistem_blogu("casper", misafir=True)
    assert "gizli talimat" not in blok


def test_bozuk_ayar_dosyasi_kaydetmeyi_engellemez(izole):
    yol = ayar._yol("casper")
    import os
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    with open(yol, "w", encoding="utf-8") as f:
        f.write("{bozuk json")
    ayar.ayarlari_yaz("casper", hitap="Casper")
    assert ayar.ayarlari_al("casper")["hitap"] == "Casper"


# ── hatırlatma ────────────────────────────────────────────────────────

def test_hatirlatma_eklenir_ve_listelenir(izole):
    kayit = hatirlatma.ekle("casper", "faturayı öde", "2030-01-01 09:00")
    assert kayit["id"]
    liste = hatirlatma.listele("casper")
    assert [k["id"] for k in liste["bekleyen"]] == [kayit["id"]]
    assert liste["gelen"] == []


def test_hatirlatma_zamani_gelince_gelen_listesine_duser(izole):
    hatirlatma.ekle("casper", "şimdi", "2020-01-01 09:00")
    liste = hatirlatma.listele("casper")
    assert liste["bekleyen"] == []
    assert len(liste["gelen"]) == 1


def test_hatirlatma_ayni_kayit_iki_kez_tetiklenmez(izole):
    hatirlatma.ekle("casper", "şimdi", "2020-01-01 09:00")
    ilk = hatirlatma.tetikle()
    ikinci = hatirlatma.tetikle()
    assert len(ilk) == 1
    assert ikinci == []


def test_hatirlatma_kullanicilar_arasinda_sizmaz(izole):
    hatirlatma.ekle("casper", "benim", "2030-01-01 09:00")
    assert hatirlatma.listele("baska")["bekleyen"] == []


def test_hatirlatma_silinir(izole):
    kayit = hatirlatma.ekle("casper", "silinecek", "2030-01-01 09:00")
    assert hatirlatma.sil("casper", kayit["id"]) is True
    assert hatirlatma.listele("casper")["bekleyen"] == []
    assert hatirlatma.sil("casper", "yok") is False


def test_hatirlatma_bos_metin_reddedilir(izole):
    with pytest.raises(ValueError):
        hatirlatma.ekle("casper", "   ", "2030-01-01 09:00")


def test_hatirlatma_zaman_bicimi_anlasilmazsa_hata(izole):
    with pytest.raises(ValueError):
        hatirlatma.ekle("casper", "x", "yarın akşam")


def test_hatirlatma_dosyasi_atomik_yazilir(izole):
    hatirlatma.ekle("casper", "a", "2030-01-01 09:00")
    yol = hatirlatma._yol("casper")
    assert not (yol + ".tmp").endswith(".json")
    with open(yol, encoding="utf-8") as f:
        veri = json.load(f)
    assert veri["hatirlatmalar"][0]["metin"] == "a"


def test_goruldu_isareti_gelen_listesini_bosaltir(izole):
    kayit = hatirlatma.ekle("casper", "oku beni", "2020-01-01 09:00")
    assert len(hatirlatma.listele("casper")["gelen"]) == 1
    assert hatirlatma.goruldu("casper", kayit["id"]) is True
    assert hatirlatma.listele("casper")["gelen"] == []


# ── araç bağlantısı ───────────────────────────────────────────────────

def test_hatirlatma_araci_state_klasorune_yazar(izole):
    from chat.kimlik import kullanici_kur
    from tools import calistir

    kullanici_kur("casper")
    sonuc = calistir("hatirlatma_kur", {
        "metin": "spor yap", "zaman": "2030-01-01 08:00"})
    assert sonuc["result"]["metin"] == "spor yap"
    liste = calistir("hatirlatma_listele", {})
    assert "spor yap" in str(liste["result"])


def test_hatirlatma_araci_gecersiz_zamanda_hata_dondurur(izole):
    from tools import calistir

    sonuc = calistir("hatirlatma_kur", {"metin": "x", "zaman": "yarın"})
    assert "error" in sonuc
