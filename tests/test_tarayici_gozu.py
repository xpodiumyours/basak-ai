"""tests/test_tarayici_gozu.py — sayfa gozu bekcileri (T0).

Tarayici YOK, ag YOK, gercek eklenti YOK: istemci sahtelenir. Olculen
seyler:

1. Uc bambaska sayfa sekli (vitrin listesi, uzun form, yonetim paneli)
   AYNI kodla okunur — kodda site adi, alan adi, kelime tetikleyicisi yok.
2. Sayfalama eksiksiz: sonraki_baslangic ile devam edilince tum ogeler
   birebir elde edilir; sessiz kirpma olmaz.
3. Nesil: sayfa degisince eski ref reddedilir (bayat ref ile eylem
   yapilamaz).
4. Istemci yoksa/patlarsa/gec cevap verirse ACIK hata doner; sohbet
   kesilmez, uydurma sayfa uretilmez.
"""

import os
import re
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import calistir
from tools import tarayici_goz as goz
from tools import tarayici_kopru as kopru
from tools.definitions import TOOLS

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ── Uc bambaska sayfa: hicbirinde ortak alan adi yok ──────────────────

VITRIN = {
    "url": "https://ornek-vitrin.test/kategori",
    "baslik": "Kategori",
    "ogeler": [
        {"rol": "heading", "ad": "Kategori"},
        {"rol": "text", "ad": "24 urun bulundu"},
        {"rol": "link", "ad": "Mavi Kalem"},
        {"rol": "link", "ad": "Kirmizi Defter"},
        {"rol": "button", "ad": "Daha fazla goster"},
        {"rol": "button", "ad": "Sepete ekle", "kapali": True},
    ],
}

FORM = {
    "url": "https://ornek-form.test/basvuru",
    "baslik": "Basvuru",
    "ogeler": [
        {"rol": "textbox", "ad": "Ad Soyad", "deger": ""},
        {"rol": "textbox", "ad": "", "deger": "ornek@eposta.test"},
        {"rol": "combobox", "ad": "Sehir", "deger": "Ankara"},
        {"rol": "checkbox", "ad": "Kosullari kabul ediyorum", "deger": "false"},
        {"rol": "button", "ad": "Gonder"},
    ],
}

PANEL = {
    "url": "https://ornek-panel.test/panel",
    "baslik": "Panel",
    "ogeler": [
        {"rol": "heading", "ad": "Gunluk ozet"},
        {"rol": "metin", "ad": "12 is tamamlandi"},
        {"rol": "button", "ad": "Yenile"},
        {"rol": "widget", "ad": "Ozel bilesen"},
        {"rol": "", "ad": "Rolsuz oge"},
        {"rol": "text", "ad": "Gizli ipucu", "gorunur": False},
        {"rol": "text", "ad": "   "},
    ],
}

SAYFALAR = [VITRIN, FORM, PANEL]


@pytest.fixture(autouse=True)
def _temiz_kopru():
    """Her testten once/sonra bagli istemci birakma."""
    for kimlik in kopru.KOPRU.kimlikler():
        kopru.KOPRU.ayir(kimlik)
    yield
    for kimlik in kopru.KOPRU.kimlikler():
        kopru.KOPRU.ayir(kimlik)


def _istemci(baslik):
    """Sahte eklenti: tek islem (sayfa_gozlem) icin gozlem dondurur."""
    def gonder(islem, veri, sure):
        assert islem == "sayfa_gozlem", islem
        return {"ok": True, "sonuc": baslik}
    return gonder


class TestGenelGoz:
    def test_uc_farkli_sayfa_ayni_kodla_okunur(self):
        for ham in SAYFALAR:
            sonuc = goz.modelle(ham)
            assert "error" not in sonuc, ham["url"]
            assert sonuc["sayfa"]["url"] == ham["url"]
            assert sonuc["sayfa"]["baslik"] == ham["baslik"]
            assert sonuc["sayfa"]["nesil"]
            assert sonuc["ogeler"], ham["url"]
            for oge in sonuc["ogeler"]:
                assert oge["ref"].startswith(sonuc["sayfa"]["nesil"] + "-")
                assert set(oge) == {"ref", "rol", "ad", "deger", "kapali"}

    def test_kodda_site_adi_gecmez(self):
        """Site adi/alan adi gomulu degilse goz gercekten geneldir."""
        for dosya in ("tools/tarayici_goz.py", "tools/tarayici_kopru.py"):
            kaynak = open(os.path.join(KOK, dosya), encoding="utf-8").read()
            assert not re.search(r"https?://", kaynak), dosya
            assert not re.search(
                r"\b[a-z0-9-]+\.(com|net|org|io|dev|test|gov)\b", kaynak), dosya

    def test_gorunmeyen_oge_atilir(self):
        adlar = [o["ad"] for o in goz.modelle(PANEL)["ogeler"]]
        assert "Gizli ipucu" not in adlar

    def test_bos_oge_atilir(self):
        adlar = [o["ad"] for o in goz.modelle(PANEL)["ogeler"]]
        assert "" not in adlar

    def test_bilinmeyen_rol_korunur(self):
        """Taninmayan rol silinmez; rolsuz oge 'diger' olur."""
        roller = [o["rol"] for o in goz.modelle(PANEL)["ogeler"]]
        assert "widget" in roller
        assert "diger" in roller

    def test_kapali_dugme_isaretlenir(self):
        kapali = [o for o in goz.modelle(VITRIN)["ogeler"] if o["kapali"]]
        assert [o["ad"] for o in kapali] == ["Sepete ekle"]

    def test_tek_oge_metni_kirpilmaz(self):
        uzun = "a" * 5000
        sonuc = goz.modelle({"url": "u", "baslik": "b",
                             "ogeler": [{"rol": "text", "ad": uzun}]})
        assert sonuc["ogeler"][0]["ad"] == uzun


class TestSayfalama:
    def test_sayfalar_birlesince_tam_liste(self):
        tam = goz.modelle(VITRIN)["ogeler"]
        toplanan, baslangic, tur = [], 0, 0
        while baslangic is not None:
            parca = goz.modelle(VITRIN, baslangic=baslangic, adet=2)
            toplanan.extend(parca["ogeler"])
            baslangic = parca["sayfalama"]["sonraki_baslangic"]
            tur += 1
            assert tur < 50
        assert toplanan == tam
        assert goz.modelle(VITRIN)["sayfalama"]["toplam"] == len(tam)

    def test_son_sayfada_sonraki_yok(self):
        son = goz.modelle(VITRIN, baslangic=0, adet=200)
        assert son["sayfalama"]["sonraki_baslangic"] is None
        assert son["sayfalama"]["donen"] == son["sayfalama"]["toplam"]

    def test_adet_sinirlanir_ama_veri_kaybolmaz(self):
        cok = goz.modelle(VITRIN, baslangic=0, adet=9999)
        assert cok["sayfalama"]["donen"] == cok["sayfalama"]["toplam"]


class TestNesil:
    def test_ayni_sayfa_ayni_nesil(self):
        assert (goz.modelle(VITRIN)["sayfa"]["nesil"]
                == goz.modelle(VITRIN)["sayfa"]["nesil"])

    def test_sayfa_degisince_nesil_degisir(self):
        eski = goz.modelle(VITRIN)["sayfa"]["nesil"]
        degismis = dict(VITRIN)
        degismis["ogeler"] = [{"rol": "button", "ad": "Baska dugme"}]
        assert goz.modelle(degismis)["sayfa"]["nesil"] != eski

    def test_bayat_ref_reddedilir(self):
        eski = goz.modelle(VITRIN)
        degismis = dict(VITRIN)
        degismis["ogeler"] = VITRIN["ogeler"] + [
            {"rol": "button", "ad": "Sonradan gelen dugme"}]
        yeni = goz.modelle(degismis)
        assert yeni["sayfa"]["nesil"] != eski["sayfa"]["nesil"]
        with pytest.raises(ValueError) as hata:
            goz.ref_coz(eski["ogeler"][0]["ref"], yeni["sayfa"]["nesil"])
        assert "Bayat" in str(hata.value)

    def test_yalniz_baslik_degisirse_ref_gecerli_kalir(self):
        """Nesil oge listesini izler; sus basligi ref'i bayatlatmaz."""
        eski = goz.modelle(VITRIN)
        yeni = goz.modelle({**VITRIN, "baslik": "Baska baslik"})
        assert yeni["sayfa"]["nesil"] == eski["sayfa"]["nesil"]
        assert goz.ref_coz(eski["ogeler"][0]["ref"],
                           yeni["sayfa"]["nesil"]) == 0

    def test_bozuk_ref_reddedilir(self):
        nesil = goz.modelle(VITRIN)["sayfa"]["nesil"]
        for bozuk in ("", "abc", "%s-x" % nesil, "12"):
            with pytest.raises(ValueError):
                goz.ref_coz(bozuk, nesil)

    def test_gecerli_ref_siraya_cevrilir(self):
        sonuc = goz.modelle(VITRIN)
        assert goz.ref_coz(sonuc["ogeler"][2]["ref"],
                           sonuc["sayfa"]["nesil"]) == 2


class TestKopru:
    def test_istemci_yoksa_acik_hata(self):
        sonuc = kopru.sayfa_bakis()
        assert "error" in sonuc
        assert "eklent" in sonuc["error"]

    def test_bagli_istemciden_gozlem_alir(self):
        kopru.KOPRU.bagla("sekme-1", _istemci(FORM))
        sonuc = kopru.sayfa_bakis(adet=2)
        assert sonuc["sayfa"]["url"] == FORM["url"]
        assert sonuc["sayfalama"]["donen"] == 2
        assert sonuc["sayfalama"]["toplam"] == len(
            goz.ogeleri_coz(FORM["ogeler"]))

    def test_istemci_hatasi_acik_doner(self):
        kopru.KOPRU.bagla(
            "sekme-1", lambda islem, veri, sure: {
                "ok": False, "hata": "sekme kapandi"})
        assert "sekme kapandi" in kopru.sayfa_bakis()["error"]

    def test_istemci_patlarsa_sohbet_kesilmez(self):
        def patla(islem, veri, sure):
            raise RuntimeError("kopru koptu")
        kopru.KOPRU.bagla("sekme-1", patla)
        sonuc = kopru.sayfa_bakis()
        assert "error" in sonuc and "kopru koptu" in sonuc["error"]

    def test_gec_cevap_zaman_asimina_duser(self):
        def yavas(islem, veri, sure):
            time.sleep(0.6)
            return {"ok": True, "sonuc": VITRIN}
        kopru.KOPRU.bagla("sekme-1", yavas)
        sonuc = kopru.KOPRU.iste("sayfa_gozlem", {}, sure=0.15)
        assert "error" in sonuc and "cevap vermedi" in sonuc["error"]

    def test_beklenmeyen_cevap_bicimi_reddedilir(self):
        kopru.KOPRU.bagla(
            "sekme-1", lambda islem, veri, sure: ["liste", "dondu"])
        assert "error" in kopru.sayfa_bakis()

    def test_bos_gozlem_uydurulmaz(self):
        kopru.KOPRU.bagla(
            "sekme-1", lambda islem, veri, sure: {"ok": True, "sonuc": None})
        assert "error" in kopru.sayfa_bakis()


class TestDortYer:
    def test_arac_semada_ve_namespace_te(self):
        from chat.agent_protocol import YETENEK_ALANLARI
        from chat.tools import DURUM_METNI

        adlar = {t["function"]["name"] for t in TOOLS}
        assert "sayfa_bakis" in adlar
        assert "sayfa_bakis" in YETENEK_ALANLARI["tarayici"]
        assert "sayfa_bakis" in DURUM_METNI

    def test_dispatcher_istemci_yokken_guvenli_hata(self):
        sonuc = calistir("sayfa_bakis", {})
        assert isinstance(sonuc, dict)
        assert "error" in sonuc
        assert sonuc != {"error": "'sayfa_bakis' calistirilamadi."}

    def test_dispatcher_istemci_varken_tam_gozlem(self):
        kopru.KOPRU.bagla("sekme-1", _istemci(PANEL))
        sonuc = calistir("sayfa_bakis", {"adet": 3})
        assert set(sonuc) == {"sayfa", "ogeler", "sayfalama"}
        assert sonuc["sayfa"]["baslik"] == "Panel"
        assert len(sonuc["ogeler"]) == 3
