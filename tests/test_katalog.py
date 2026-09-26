"""tests/test_katalog.py — Fatura → Vixrex katalog yeteneği güvencesi.

Sözleşme: aletler üç yerde bağlı; boş girdi yan etkisiz hata döner
(ağ/dosya açılmaz); Vixrex CSV başlığı birebir; barkod JSON'da korunur;
yol kaçışı kapalı; yazma atomik. Yerel göz kapalıyken bulut yolu tek
başına çalışır (Faz 2 bağımsızlığı).
"""

import base64
import csv
import io
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import calistir
from tools import katalog
from tools.definitions import TANINMIS_TOOLLAR


def _j(r):
    return json.loads(r["result"])


SATIRLAR = [
    {"marka": "Tutku", "kod": "TK-102", "barkod": "8691234567890",
     "beden": "S", "renk": "Siyah", "adet": 5, "alis_fiyat": "120,50",
     "kategori": "Elbise"},
    {"marka": "Tutku", "kod": "tk 102", "barkod": "8691234567891",
     "beden": "M", "renk": "siyah", "adet": 3, "alis_fiyat": "120,50",
     "kategori": "Elbise"},
    {"marka": "Berrak", "kod": "BR-7", "beden": "L", "renk": "Beyaz",
     "adet": 2, "alis_fiyat": 200, "kategori": "Triko"},
    {"marka": "X", "kod": "", "adet": 1},
]


class TestUcYer:
    def test_yedi_arac_bagli(self):
        from chat.tools import DURUM_METNI
        for ad in ("fatura_oku", "katalog_kur", "katalog_getir",
                   "katalog_liste", "katalog_fiyat_guncelle",
                   "katalog_onayla", "yetki_belgesi_ekle",
                   "urun_eslestir", "yayin_paketi", "cikti_oku"):
            assert ad in TANINMIS_TOOLLAR, ad
            assert ad in DURUM_METNI, ad

    def test_bos_girdi_yan_etkisiz(self):
        assert "error" in calistir("fatura_oku", {"fatura_id": ""})
        assert "error" in calistir(
            "katalog_kur", {"fatura_id": "", "satirlar": []})
        assert "error" in calistir("katalog_getir", {"is_id": ""})
        r = calistir("katalog_liste", {})
        assert "result" in r
        assert "error" in calistir(
            "katalog_fiyat_guncelle",
            {"is_id": "", "kart_id": "", "satis_fiyat": ""})
        assert "error" in calistir("katalog_onayla", {"is_id": ""})
        assert "error" in calistir(
            "yetki_belgesi_ekle", {"is_id": "", "b64": "", "ad": ""})
        assert "error" in calistir(
            "urun_eslestir", {"is_id": "", "kart_id": ""})
        assert "error" in calistir(
            "yayin_paketi", {"is_id": "", "platform": ""})


class TestFiyat:
    def test_tr_bicimler(self):
        assert katalog.fiyat_coz("1.250,50 TL")[0] == 1250.5
        assert katalog.fiyat_coz("125,50")[0] == 125.5
        assert katalog.fiyat_coz("125.50")[0] == 125.5
        assert katalog.fiyat_coz(125)[0] == 125.0
        assert katalog.fiyat_coz("")[0] is None
        assert katalog.fiyat_coz("Mağazada sorunuz")[0] is None
        assert katalog.fiyat_coz("-5")[0] is None

    def test_tutku_dort_ondalik(self):
        assert katalog.fiyat_coz("75,0000 TL")[0] == 75.0
        assert katalog.fiyat_coz("63,5000 TL")[0] == 63.5
        assert katalog.fiyat_coz("41,5000 TL")[0] == 41.5
        assert katalog.fiyat_coz("3.244,50 TL")[0] == 3244.5

    def test_dz_bulasmasi_reddedilir(self):
        deger, uyari = katalog.fiyat_coz("1 63,5000 TL")
        assert deger is None and uyari

    def test_csv_yazimi(self):
        assert katalog.fiyat_yaz(125.0) == "125"
        assert katalog.fiyat_yaz(125.5) == "125.50"
        assert katalog.fiyat_yaz(None) == ""


class TestNorm:
    def test_kod_ayni_aile(self):
        assert katalog.kodu_normla("TK-102") == katalog.kodu_normla("tk 102")
        assert katalog.kodu_normla("BR/7") == "BR-7"

    def test_barkod(self):
        assert katalog.barkod_dogrula("8691234567890")[0] == "8691234567890"
        assert katalog.barkod_dogrula("abc")[0] is None
        assert katalog.barkod_dogrula("")[0] is None

    def test_barkod_saglama_yakaliyor(self):
        ok, uyari = katalog.barkod_dogrula("8681128321097")
        assert ok == "8681128321097" and uyari is None
        ok, uyari = katalog.barkod_dogrula("9681128321097")
        assert ok == "9681128321097" and uyari

    def test_varyant_renk(self):
        assert katalog.varyant_renk("100 BEYAZ") == "Beyaz"
        assert katalog.varyant_renk("750 SIYAH") == "Siyah"
        assert katalog.varyant_renk("975 KOMBİN") == "Kombin"
        assert katalog.varyant_renk("975 Kombin") == "Kombin"
        assert katalog.varyant_renk("") == ""
        assert katalog.varyant_renk("100") == ""

    def test_guvenli_id_reddeder(self):
        assert not katalog._guvenli_id("../kacis")
        assert not katalog._guvenli_id("a/b")
        assert not katalog._guvenli_id("")
        assert katalog._guvenli_id("gln_20260914_1234")


class TestStaging:
    def test_bozuk_b64(self, tmp_path, monkeypatch):
        monkeypatch.setattr(katalog, "GELEN_KOK", str(tmp_path))
        assert "error" in katalog.fatura_kaydet_b64("!!bozuk!!", "f.jpg")

    def test_uzanti_reddi(self, tmp_path, monkeypatch):
        monkeypatch.setattr(katalog, "GELEN_KOK", str(tmp_path))
        b64 = base64.b64encode(b"veri").decode("ascii")
        assert "error" in katalog.fatura_kaydet_b64(b64, "kotu.exe")

    def test_kayit_ve_yol(self, tmp_path, monkeypatch):
        monkeypatch.setattr(katalog, "GELEN_KOK", str(tmp_path))
        b64 = base64.b64encode(b"\xff\xd8sahte").decode("ascii")
        r = katalog.fatura_kaydet_b64(b64, "fatura.jpg")
        assert "result" in r, r
        kimlik = json.loads(r["result"])["fatura_id"]
        assert katalog._fatura_yolu(kimlik) is not None
        assert katalog._fatura_yolu("../kacis") is None

    def test_data_url_oneki(self, tmp_path, monkeypatch):
        monkeypatch.setattr(katalog, "GELEN_KOK", str(tmp_path))
        b64 = ("data:image/jpeg;base64,"
               + base64.b64encode(b"\xff\xd8sahte").decode("ascii"))
        assert "result" in katalog.fatura_kaydet_b64(b64, "f.jpg")


class TestFaturaOku:
    @pytest.fixture(autouse=True)
    def _yerel_kapali(self, monkeypatch):
        # Bulut yolu testleri gerçek yerel göze değmesin.
        from tools import yerel_goru
        monkeypatch.setattr(yerel_goru, "musait", lambda: False)

    def test_yoksa_hata(self, tmp_path, monkeypatch):
        monkeypatch.setattr(katalog, "GELEN_KOK", str(tmp_path))
        assert "error" in katalog.fatura_oku("gln_yok123")

    def test_pdf_reddi(self, tmp_path, monkeypatch):
        monkeypatch.setattr(katalog, "GELEN_KOK", str(tmp_path))
        (tmp_path / "gln_a1.pdf").write_bytes(b"%PDF-sahte")
        r = katalog.fatura_oku("gln_a1")
        assert "error" in r and "PDF" in r["error"]

    def test_goru_sonucu_adaylar(self, tmp_path, monkeypatch):
        import tools.image_analyzer as ga
        monkeypatch.setattr(katalog, "GELEN_KOK", str(tmp_path))
        (tmp_path / "gln_b2.jpg").write_bytes(b"\xff\xd8sahte")
        monkeypatch.setattr(
            ga, "image_analyze",
            lambda yol, soru=None, model=None: {
                "result": "Tutku TK-102 S 5 adet 120,50 TL "
                          "8691234567890\nBerrak elbise",
                "model": "sahte"})
        r = katalog.fatura_oku("gln_b2")
        assert "result" in r, r
        veri = json.loads(r["result"])
        assert "120,50" in veri["yazi"]
        assert veri["aday_satirlar"]
        assert veri["aday_satirlar"][0]["barkodlar"] == ["8691234567890"]

    def test_goru_hatasi_tasinir(self, tmp_path, monkeypatch):
        import tools.image_analyzer as ga
        monkeypatch.setattr(katalog, "GELEN_KOK", str(tmp_path))
        (tmp_path / "gln_c3.jpg").write_bytes(b"\xff\xd8sahte")
        monkeypatch.setattr(
            ga, "image_analyze",
            lambda yol, soru=None, model=None: {"error": "kota bitti"})
        r = katalog.fatura_oku("gln_c3")
        assert "error" in r and "kota" in r["error"]

    def test_gecici_hatada_uc_deneme(self, tmp_path, monkeypatch):
        import tools.image_analyzer as ga
        monkeypatch.setattr(katalog, "GELEN_KOK", str(tmp_path))
        (tmp_path / "gln_c4.jpg").write_bytes(b"\xff\xd8sahte")
        cagrilar = []

        def dalgali(yol, soru=None, model=None):
            cagrilar.append(yol)
            if len(cagrilar) < 3:
                return {"error": "Request timed out."}
            return {"result": "TER0101 6 ad\n"
                              "Toplam: 6 ad 1 dz 10,00 TL",
                    "model": "sahte"}

        monkeypatch.setattr(ga, "image_analyze", dalgali)
        import time as _z
        monkeypatch.setattr(_z, "sleep", lambda s: None)
        r = katalog.fatura_oku("gln_c4")
        assert "result" in r, r
        assert len(cagrilar) == 3

    def test_yarim_okumada_tekrar_deneme(self, tmp_path, monkeypatch):
        """Toplam satiri olmayan (yarim) okuma yeniden denenir."""
        import tools.image_analyzer as ga
        monkeypatch.setattr(katalog, "GELEN_KOK", str(tmp_path))
        (tmp_path / "gln_c5.jpg").write_bytes(b"\xff\xd8sahte")
        cagrilar = []

        def dalgali(yol, soru=None, model=None):
            cagrilar.append(yol)
            if len(cagrilar) < 2:
                return {"result": "ELT1302 2 ad 137,00", "model": "sahte"}
            return {"result": "ELT1302 2 ad 137,00\n"
                              "Toplam: 2 ad 1 dz 6.034,00 TL",
                    "model": "sahte"}

        monkeypatch.setattr(ga, "image_analyze", dalgali)
        r = katalog.fatura_oku("gln_c5")
        assert "result" in r, r
        veri = json.loads(r["result"])
        assert veri["ustbilgi"]["toplam"] == 6034.0
        assert len(cagrilar) == 2

    def test_adet_toplami_uyusmazsa_yarim(self):
        """Satır adetleri 77, basılı Toplam 75 → okuma sağlıksız (Kilo vakası)."""
        yazi = ("ELT1302 2 ad\nELT1303 75 ad\n"
                "Toplam: 75 ad 6 dz 6.034,00 TL")
        assert katalog._okuma_yarim(yazi) is True

    def test_adet_toplami_tutuyorsa_saglikli(self):
        yazi = ("ELT1302 2 ad\nELT1303 73 ad\n"
                "Toplam: 75 ad 6 dz 6.034,00 TL")
        assert katalog._okuma_yarim(yazi) is False

    def test_tekrar_dongusu_yarim(self):
        """Aynı satır 5+ kez → döngü okuması (yerel göz vakası)."""
        satir = "ELT2204 ELIT BYN ELS BALIK YAKA 81,0000 TL\n"
        yazi = satir * 6 + "Toplam: 81,00 TL"
        assert katalog._okuma_yarim(yazi) is True

    def test_yarim_okuma_son_denemede_kabul(self, tmp_path, monkeypatch):
        """Hep yarım okursa 4. denemede yarım metinle yetinilir."""
        import tools.image_analyzer as ga
        monkeypatch.setattr(katalog, "GELEN_KOK", str(tmp_path))
        (tmp_path / "gln_c6.jpg").write_bytes(b"\xff\xd8sahte")
        cagrilar = []

        def hep_yarim(yol, soru=None, model=None):
            cagrilar.append(yol)
            return {"result": "ELT1302 2 ad", "model": "sahte"}

        monkeypatch.setattr(ga, "image_analyze", hep_yarim)
        r = katalog.fatura_oku("gln_c6")
        assert "result" in r, r
        assert len(cagrilar) == 4


class TestYerelGoru:
    def test_kapaliysa_bulut(self, tmp_path, monkeypatch):
        from tools import yerel_goru
        monkeypatch.setattr(yerel_goru, "musait", lambda: False)
        import tools.image_analyzer as ga
        monkeypatch.setattr(katalog, "GELEN_KOK", str(tmp_path))
        (tmp_path / "gln_y1.jpg").write_bytes(b"\xff\xd8sahte")
        monkeypatch.setattr(
            ga, "image_analyze",
            lambda yol, soru=None, model=None: {"result": "bulut yazı",
                                                "model": "sahte"})
        veri = json.loads(katalog.fatura_oku("gln_y1")["result"])
        assert veri["kaynak"] == "bulut"
        assert veri["yazi"] == "bulut yazı"

    def test_yerel_once_buluta_değmez(self, tmp_path, monkeypatch):
        from tools import yerel_goru
        monkeypatch.setattr(yerel_goru, "musait", lambda: True)
        dokunuldu = []
        monkeypatch.setattr(
            yerel_goru, "oku",
            lambda yol, soru: {"result": "yerel yazı 2 ad\n"
                                        "Toplam: 2 ad 1 dz 5,00 TL",
                               "model": "sahte-goz"})
        import tools.image_analyzer as ga
        monkeypatch.setattr(
            ga, "image_analyze",
            lambda *a, **k: dokunuldu.append(1) or {"error": "asla"})
        monkeypatch.setattr(katalog, "GELEN_KOK", str(tmp_path))
        (tmp_path / "gln_y2.jpg").write_bytes(b"\xff\xd8sahte")
        veri = json.loads(katalog.fatura_oku("gln_y2")["result"])
        assert veri["kaynak"] == "yerel"
        assert veri["yazi"].startswith("yerel yazı")
        assert dokunuldu == []

    def test_yerel_cokerse_bulut(self, tmp_path, monkeypatch):
        from tools import yerel_goru
        monkeypatch.setattr(yerel_goru, "musait", lambda: True)
        monkeypatch.setattr(
            yerel_goru, "oku", lambda yol, soru: {"error": "göz kapalı"})
        import tools.image_analyzer as ga
        monkeypatch.setattr(
            ga, "image_analyze",
            lambda yol, soru=None, model=None: {"result": "bulut yazı",
                                                "model": "sahte"})
        monkeypatch.setattr(katalog, "GELEN_KOK", str(tmp_path))
        (tmp_path / "gln_y3.jpg").write_bytes(b"\xff\xd8sahte")
        veri = json.loads(katalog.fatura_oku("gln_y3")["result"])
        assert veri["kaynak"] == "bulut"

    def test_kapama_anahtari(self, monkeypatch):
        from tools import yerel_goru
        monkeypatch.setenv("BASAK_YEREL_GORU", "0")
        assert yerel_goru.acik_mi() is False
        assert yerel_goru.musait() is False

    def test_zorla_acma_ayarlari_ezer(self, monkeypatch):
        """BASAK_YEREL_GORU=1 ayarlar.json'daki kapatmayı ezer."""
        from tools import yerel_goru
        monkeypatch.setenv("BASAK_YEREL_GORU", "1")
        assert yerel_goru.acik_mi() is True

    def test_kucultme_siniri(self, tmp_path):
        from PIL import Image
        from tools import yerel_goru
        yol = str(tmp_path / "buyuk.jpg")
        Image.new("RGB", (2000, 1128), "white").save(yol)
        ham = yerel_goru._kucult(yol)
        yeniden = Image.open(io.BytesIO(ham))
        assert max(yeniden.size) <= yerel_goru.AZAMI_KENAR

    def test_oku_dosya_yok(self):
        from tools import yerel_goru
        assert "error" in yerel_goru.oku("", "soru")


class TestKatalogHatti:
    def _kur(self, tmp_path, monkeypatch):
        monkeypatch.setattr(katalog, "GELEN_KOK", str(tmp_path / "gelen"))
        monkeypatch.setattr(katalog, "KATALOG_KOK", str(tmp_path / "kat"))
        monkeypatch.setattr(katalog, "YETKI_KOK", str(tmp_path / "yzk"))
        os.makedirs(tmp_path / "gelen", exist_ok=True)
        (tmp_path / "gelen" / "gln_f1.jpg").write_bytes(b"\xff\xd8x")
        r = katalog.katalog_kur("gln_f1", SATIRLAR)
        assert "result" in r, r
        return _j(r)

    def test_gruplama(self, tmp_path, monkeypatch):
        ozet = self._kur(tmp_path, monkeypatch)
        assert ozet["kart_sayisi"] == 2
        assert len(ozet["uyarilar"]) >= 1  # kodsuz satır
        veri = _j(katalog.katalog_getir(ozet["is_id"]))
        tutku = next(k for k in veri["kartlar"] if k["kod"] == "TK-102")
        assert len(tutku["varyantlar"]) == 2
        assert tutku["toplam_adet"] == 8
        assert tutku["stok_durumu"] == "Mevcut"
        assert {v["barkod"] for v in tutku["varyantlar"]} == {
            "8691234567890", "8691234567891"}

    def test_tutku_fisi(self, tmp_path, monkeypatch):
        """Gerçek Tutku fiş biçimi: varyant, 4 ondalık, Stok=ürün adı."""
        monkeypatch.setattr(katalog, "GELEN_KOK", str(tmp_path / "gelen"))
        monkeypatch.setattr(katalog, "KATALOG_KOK", str(tmp_path / "kat"))
        monkeypatch.setattr(katalog, "YETKI_KOK", str(tmp_path / "yzk"))
        os.makedirs(tmp_path / "gelen", exist_ok=True)
        (tmp_path / "gelen" / "gln_t.jpg").write_bytes(b"\xff\xd8x")
        satirlar = [
            {"marka": "Tutku", "kod": "TER0101",
             "urun_adi": "TUT ERK PEN. ATLET", "barkod": "8680508918124",
             "varyant": "100 BEYAZ", "beden": "3", "adet": 6,
             "alis_fiyat": "63,5000 TL", "kategori": "Atlet"},
            {"marka": "Tutku", "kod": "TER0101",
             "urun_adi": "TUT ERK PEN. ATLET", "barkod": "8680508918131",
             "varyant": "100 BEYAZ", "beden": "4", "adet": 6,
             "alis_fiyat": "63,5000 TL", "kategori": "Atlet"},
            {"marka": "Tutku", "kod": "TER0101",
             "urun_adi": "TUT ERK PEN. ATLET", "barkod": "8680508918148",
             "varyant": "100 BEYAZ", "beden": "5", "adet": 6,
             "alis_fiyat": "63,5000 TL", "kategori": "Atlet"},
            {"marka": "Tutku", "kod": "TER0114",
             "urun_adi": "TUT ERK LICRALI BOXER", "barkod": "8680508921964",
             "varyant": "750 SİYAH", "beden": "M", "adet": 12,
             "alis_fiyat": "63,5000 TL", "kategori": "Boxer"},
        ]
        ozet = _j(katalog.katalog_kur("gln_t", satirlar))
        assert ozet["kart_sayisi"] == 2, ozet
        assert not ozet["uyarilar"], ozet["uyarilar"]
        veri = _j(katalog.katalog_getir(ozet["is_id"]))
        atlet = next(k for k in veri["kartlar"] if k["kod"] == "TER0101")
        assert len(atlet["varyantlar"]) == 3
        assert atlet["toplam_adet"] == 18
        assert all(v["renk"] == "beyaz" for v in atlet["varyantlar"])
        assert all(v["alis_fiyat"] == 63.5 for v in atlet["varyantlar"])
        assert "TUT ERK PEN. ATLET" in atlet["ad"]
        boxer = next(k for k in veri["kartlar"] if k["kod"] == "TER0114")
        assert boxer["varyantlar"][0]["renk"] == "siyah"

    def test_adet_ustbilgi_uyusmazsa_kaydetmez(self, tmp_path, monkeypatch):
        """Satır adet toplamı üst bilgiye uymazsa katalog kaydedilmez
        (2026-09-26 göz imtihani: 72/75 ölçümü); uyuşursa kaydedilir."""
        monkeypatch.setattr(katalog, "GELEN_KOK", str(tmp_path / "gelen"))
        monkeypatch.setattr(katalog, "KATALOG_KOK", str(tmp_path / "kat"))
        monkeypatch.setattr(katalog, "YETKI_KOK", str(tmp_path / "yzk"))
        os.makedirs(tmp_path / "gelen", exist_ok=True)
        (tmp_path / "gelen" / "gln_a.jpg").write_bytes(b"\xff\xd8x")
        satirlar = [{"marka": "Tutku", "kod": "TER0101", "adet": 3,
                     "renk": "beyaz", "kategori": "Atlet"}]

        r = katalog.katalog_kur(
            "gln_a", satirlar, ustbilgi={"adet": 75, "toplam": 6034.0})
        assert "error" in r, r
        assert "75" in r["error"] and "3" in r["error"], r
        kayitli = (os.listdir(tmp_path / "kat")
                   if os.path.isdir(tmp_path / "kat") else [])
        assert kayitli == [], kayitli

        r2 = katalog.katalog_kur("gln_a", satirlar, ustbilgi={"adet": 3})
        assert "result" in r2, r2
        assert _j(r2)["is_id"]

    def test_kaynak_okuma_kaydi_ustbilgiyi_basar(self, tmp_path, monkeypatch):
        """Model ustbilgi'yi eksik gecirse bile hedef adet kaynak
        okuma kaydindan (_oku_kaydet) okunur; uyusmazsa kapu kapanir."""
        monkeypatch.setattr(katalog, "GELEN_KOK", str(tmp_path / "gelen"))
        monkeypatch.setattr(katalog, "KATALOG_KOK", str(tmp_path / "kat"))
        monkeypatch.setattr(katalog, "YETKI_KOK", str(tmp_path / "yzk"))
        os.makedirs(tmp_path / "gelen", exist_ok=True)
        (tmp_path / "gelen" / "gln_k.jpg").write_bytes(b"\xff\xd8x")
        katalog._oku_kaydet("gln_k", {"yazi": "x",
                                      "ustbilgi": {"adet": 75}})
        satirlar = [{"marka": "Tutku", "kod": "TER0101", "adet": 3,
                     "renk": "beyaz", "kategori": "Atlet"}]
        r = katalog.katalog_kur("gln_k", satirlar)  # ustbilgi gecilmedi
        assert "error" in r and "75" in r["error"], r
        r2 = katalog.katalog_kur(
            "gln_k", [dict(satirlar[0], adet=75)])
        assert "result" in r2, r2

    def test_stok_esikleri(self, tmp_path, monkeypatch):
        assert katalog._stok_durumu(0) == "Tükendi"
        assert katalog._stok_durumu(2) == "Son birkaç adet"
        assert katalog._stok_durumu(8) == "Mevcut"

    def test_fiyat_guncelle(self, tmp_path, monkeypatch):
        ozet = self._kur(tmp_path, monkeypatch)
        veri = _j(katalog.katalog_getir(ozet["is_id"]))
        kart = veri["kartlar"][0]["kart_id"]
        r = katalog.katalog_fiyat_guncelle(ozet["is_id"], kart, "1.750,50 TL")
        assert _j(r)["satis_fiyat"] == 1750.5
        assert "error" in katalog.katalog_fiyat_guncelle(
            ozet["is_id"], kart, "paha biçilemez")
        assert "error" in katalog.katalog_fiyat_guncelle(
            ozet["is_id"], "krt_99", "10")

    def test_onayla_csv_json(self, tmp_path, monkeypatch):
        ozet = self._kur(tmp_path, monkeypatch)
        veri = _j(katalog.katalog_getir(ozet["is_id"]))
        kart = next(k["kart_id"] for k in veri["kartlar"]
                    if k["kod"] == "TK-102")
        katalog.katalog_fiyat_guncelle(ozet["is_id"], kart, "299.90")
        r = katalog.katalog_onayla(ozet["is_id"])
        assert "result" in r, r
        sonuc = _j(r)
        assert sonuc["durum"] == "hazir"
        assert len(sonuc["fiyat_onaysiz"]) == 1  # ikinci kart fiyatsız
        klasor = tmp_path / "kat" / ozet["is_id"]

        ham = (klasor / "vixrex_urunler.csv").read_bytes()
        assert ham.startswith(b"\xef\xbb\xbf")  # Excel-Türkçe BOM
        metin = ham.decode("utf-8-sig")
        okunan = list(csv.reader(io.StringIO(metin)))
        assert okunan[0] == ["Ürün Adı", "Fiyat", "Açıklama", "Kategori",
                             "Stok Durumu", "Görsel URL"]
        assert len(okunan) == 3  # başlık + 2 kart
        satirlar = {s[0]: s for s in okunan[1:]}
        tutku_satir = next(s for ad, s in satirlar.items()
                           if "TK-102" in ad or "TK-102" in s[2])
        assert tutku_satir[1] == "299.90"  # satış fiyatı yazıldı

        batch = json.loads((klasor / "vixrex_batch.json").read_text(
            encoding="utf-8"))
        assert len(batch) == 2
        tutku_oge = next(o for o in batch
                         if o["external_product_id"] == "TK-102")
        assert len(batch) == 2
        assert tutku_oge["source_type"] == "basak_fatura"
        assert tutku_oge["image_urls"] == []
        assert tutku_oge["external_product_id"] == "TK-102"
        for anahtar in ("name", "description", "price_text",
                        "category_id", "isVisible", "sort_order"):
            assert anahtar in tutku_oge, anahtar

        tam = json.loads((klasor / "basak_katalog.json").read_text(
            encoding="utf-8"))
        tutku_kart = next(k for k in tam["kartlar"] if k["kod"] == "TK-102")
        assert len(tutku_kart["varyantlar"]) == 2

        icerik = katalog.cikti_oku(ozet["is_id"], "vixrex_urunler.csv")
        assert "result" in icerik and "Ürün Adı" in icerik["result"]
        assert "error" in katalog.cikti_oku(ozet["is_id"], "kotu.csv")
        assert "error" in katalog.cikti_oku("ktg_yok", "vixrex_urunler.csv")

    def test_onay_idempotent(self, tmp_path, monkeypatch):
        ozet = self._kur(tmp_path, monkeypatch)
        ilk = _j(katalog.katalog_onayla(ozet["is_id"]))
        ikinci = _j(katalog.katalog_onayla(ozet["is_id"]))
        assert ilk["uyarilar"] == ikinci["uyarilar"]
        assert len(ikinci["uyarilar"]) == len(set(ikinci["uyarilar"]))

    def test_csv_alinti(self, tmp_path, monkeypatch):
        monkeypatch.setattr(katalog, "GELEN_KOK", str(tmp_path / "gelen"))
        monkeypatch.setattr(katalog, "KATALOG_KOK", str(tmp_path / "kat"))
        os.makedirs(tmp_path / "gelen", exist_ok=True)
        (tmp_path / "gelen" / "gln_f2.jpg").write_bytes(b"\xff\xd8x")
        satirlar = [{"marka": "A", "kod": 'K"1,özel', "adet": 9,
                     "alis_fiyat": "10"}]
        ozet = _j(katalog.katalog_kur("gln_f2", satirlar))
        katalog.katalog_onayla(ozet["is_id"])
        metin = (tmp_path / "kat" / ozet["is_id"]
                 / "vixrex_urunler.csv").read_text(encoding="utf-8-sig")
        okunan = list(csv.reader(io.StringIO(metin)))
        assert len(okunan) == 2
        assert 'K"1,özel' in okunan[1][0]

    def test_yetki_baglama(self, tmp_path, monkeypatch):
        ozet = self._kur(tmp_path, monkeypatch)
        b64 = base64.b64encode(b"sahte-belge").decode("ascii")
        r = katalog.yetki_belgesi_ekle(ozet["is_id"], b64, "izin.pdf")
        assert "result" in r, r
        veri = _j(katalog.katalog_getir(ozet["is_id"]))
        assert veri["yetki_id"] == _j(r)["yetki_id"]
        assert "error" in katalog.yetki_belgesi_ekle("", b64, "izin.exe")


class TestMarkaIzni:
    def _koklar(self, tmp_path, monkeypatch):
        monkeypatch.setattr(katalog, "GELEN_KOK", str(tmp_path / "gelen"))
        monkeypatch.setattr(katalog, "KATALOG_KOK", str(tmp_path / "kat"))
        monkeypatch.setattr(katalog, "YETKI_KOK", str(tmp_path / "yzk"))
        os.makedirs(tmp_path / "gelen", exist_ok=True)
        (tmp_path / "gelen" / "gln_m.jpg").write_bytes(b"\xff\xd8x")

    def test_marka_kapsama_isler_arasi(self, tmp_path, monkeypatch):
        self._koklar(tmp_path, monkeypatch)
        b64 = base64.b64encode(b"belge").decode("ascii")
        is1 = _j(katalog.katalog_kur("gln_m", [
            {"marka": "Tutku", "kod": "TER0101", "adet": 2}]))["is_id"]
        r = katalog.yetki_belgesi_ekle(is1, b64, "izin.pdf", "Tutku")
        assert _j(r)["marka"] == "Tutku"
        assert katalog.marka_kapsama("tutku") == _j(r)["yetki_id"]
        assert katalog.marka_kapsama("Berrak") is None
        # İkinci iş: aynı marka uyarısız, diğer marka uyarılı
        is2 = _j(katalog.katalog_kur("gln_m", [
            {"marka": "Tutku", "kod": "TER0114", "adet": 1},
            {"marka": "Berrak", "kod": "BR-7", "adet": 1}]))["is_id"]
        sonuc = _j(katalog.katalog_onayla(is2))
        assert not any("Tutku" in u and "izin" in u
                       for u in sonuc["uyarilar"]), sonuc["uyarilar"]
        assert any("Berrak" in u for u in sonuc["uyarilar"])

    def test_marka_isten_alinir(self, tmp_path, monkeypatch):
        self._koklar(tmp_path, monkeypatch)
        b64 = base64.b64encode(b"belge").decode("ascii")
        is1 = _j(katalog.katalog_kur("gln_m", [
            {"marka": "Tutku", "kod": "A", "adet": 1},
            {"marka": "Tutku", "kod": "B", "adet": 1},
            {"marka": "Berrak", "kod": "C", "adet": 1}]))["is_id"]
        r = _j(katalog.yetki_belgesi_ekle(is1, b64, "izin.pdf", ""))
        assert r["marka"] == "Tutku"
        getir = _j(katalog.katalog_getir(is1))
        assert getir["marka_kapsama"] == {"Tutku": r["yetki_id"],
                                          "Berrak": None}


class TestYayinPaketi:
    def _hazir_is(self, tmp_path, monkeypatch):
        monkeypatch.setattr(katalog, "GELEN_KOK", str(tmp_path / "gelen"))
        monkeypatch.setattr(katalog, "KATALOG_KOK", str(tmp_path / "kat"))
        monkeypatch.setattr(katalog, "YETKI_KOK", str(tmp_path / "yzk"))
        os.makedirs(tmp_path / "gelen", exist_ok=True)
        (tmp_path / "gelen" / "gln_y.jpg").write_bytes(b"\xff\xd8x")
        is_id = _j(katalog.katalog_kur("gln_y", [
            {"marka": "Tutku", "kod": "TER0101", "adet": 6,
             "alis_fiyat": "63,5000 TL"}]))["is_id"]
        katalog.katalog_onayla(is_id)
        return is_id

    def test_hazir(self, tmp_path, monkeypatch):
        is_id = self._hazir_is(tmp_path, monkeypatch)
        sonuc = _j(katalog.yayin_paketi(is_id, "vixrex"))
        assert sonuc["hazir"] is True
        assert sonuc["kart"] == 1
        assert "Toplu yükle" in sonuc["sonraki_adim"]

    def test_is_uyarilari_tasinir(self, tmp_path, monkeypatch):
        # Sekil hazir olsa da is uyarilari (fiyat/izinsiz) pakette
        # gorunur — sahte-hazir yok.
        monkeypatch.setattr(katalog, "GELEN_KOK", str(tmp_path / "gelen"))
        monkeypatch.setattr(katalog, "KATALOG_KOK", str(tmp_path / "kat"))
        monkeypatch.setattr(katalog, "YETKI_KOK", str(tmp_path / "yzk"))
        os.makedirs(tmp_path / "gelen", exist_ok=True)
        (tmp_path / "gelen" / "gln_u.jpg").write_bytes(b"\xff\xd8x")
        is_id = _j(katalog.katalog_kur("gln_u", [
            {"marka": "Berrak", "kod": "BR-9", "adet": 1}]))["is_id"]
        katalog.katalog_onayla(is_id)
        sonuc = _j(katalog.yayin_paketi(is_id, "vixrex"))
        assert sonuc["hazir"] is True  # sekil gecer
        assert any("Berrak" in u for u in sonuc["is_uyarilari"])
        assert "eksik" in sonuc["sonraki_adim"].lower() or \
            "Önce" in sonuc["sonraki_adim"]

    def test_hazir_degil_ve_platform(self, tmp_path, monkeypatch):
        monkeypatch.setattr(katalog, "KATALOG_KOK", str(tmp_path / "kat"))
        assert "error" in katalog.yayin_paketi("ktg_yok", "vixrex")
        assert "error" in katalog.yayin_paketi("ktg_yok", "trendyol")

    def test_satir_denetimi(self):
        baslik = ["urunadi", "fiyat", "aciklama", "kategori",
                  "stokdurumu", "gorselurl"]
        assert katalog._vixrex_satir_denetle(
            baslik, ["A", "10", "", "G", "Mevcut", ""], 2) == []
        hatalar = katalog._vixrex_satir_denetle(
            baslik, ["", "abc", "", "G", "Stokta", "gorsel"], 3)
        assert len(hatalar) == 4


class TestEslesme:
    def test_pure_sorgu(self):
        a = katalog.eslesme_adayi("Tutku", "tk 102")
        assert a["kod_norm"] == "TK-102"
        assert any("TK-102" in s or "tk 102" in s for s in a["sorgular"])

    def test_skor(self):
        yuksek = katalog._eslesme_skor(
            "TER0101", "Tutku",
            "https://www.tutkuelit.com.tr/urun/ter0101-tut-erkek-atlet",
            "TER0101 Tutku erkek penye atlet beyaz")
        assert yuksek >= 5
        kategori = katalog._eslesme_skor(
            "TER0101", "Tutku",
            "https://www.tutkuelit.com.tr/kategori/erkek-atletleri",
            "TER0101 Tutku erkek penye atlet beyaz")
        assert kategori < yuksek
        assert katalog._eslesme_skor("QZX", "WQW", "https://a.com/b",
                                     "alakasiz yazi") == 0


class TestSayfaGorseller:
    def test_toplama_sirasi(self, monkeypatch):
        from tools import web_search as ws
        monkeypatch.setattr(ws, "_engelli_ip_nedeni", lambda h: None)

        class Yanit:
            headers = {"Content-Type": "text/html"}

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self, n=-1):
                return ('<html><head><meta property="og:image" '
                        'content="https://d.com/og.jpg"></head>'
                        '<body><img src="/a.jpg"><img src="data:x">'
                        '<img src="https://d.com/b.png">'
                        '<img src="https://d.com/c.pdf"></body></html>'
                        ).encode("utf-8")

        r = ws.sayfa_gorseller(
            "https://www.tutkuelit.com.tr/u",
            _acici=lambda *a, **k: Yanit())
        assert "result" in r, r
        assert json.loads(r["result"]) == [
            "https://d.com/og.jpg",
            "https://www.tutkuelit.com.tr/a.jpg",
            "https://d.com/b.png"]

    def test_ssrf_ve_bos(self):
        from tools import web_search as ws
        assert "error" in ws.sayfa_gorseller("http://169.254.169.254/x")
        assert "error" in ws.sayfa_gorseller("")
        assert "error" in ws.sayfa_gorseller("ftp://d.com/a.jpg")


class TestUrunEslestir:
    def _kur(self, tmp_path, monkeypatch):
        monkeypatch.setattr(katalog, "GELEN_KOK", str(tmp_path / "gelen"))
        monkeypatch.setattr(katalog, "KATALOG_KOK", str(tmp_path / "kat"))
        monkeypatch.setattr(katalog, "YETKI_KOK", str(tmp_path / "yzk"))
        os.makedirs(tmp_path / "gelen", exist_ok=True)
        (tmp_path / "gelen" / "gln_e.jpg").write_bytes(b"\xff\xd8x")
        r = katalog.katalog_kur("gln_e", [
            {"marka": "Tutku", "kod": "TER0101", "adet": 6,
             "alis_fiyat": "63,5000 TL"},
            {"marka": "Berrak", "kod": "BR-7", "adet": 2}])
        return _j(r)["is_id"]

    def _sahte_ag(self, monkeypatch):
        from tools import web_search as ws
        monkeypatch.setattr(
            ws, "web_search",
            lambda q: {"result": (
                "Tutku TER0101 Atlet\n"
                "https://www.tutkuelit.com.tr/urun/ter0101-tut-erkek-atlet\n"
                "aciklama\n\nDiger\nhttps://baska.com/x\naciklama")})
        monkeypatch.setattr(
            ws, "sayfa_oku",
            lambda u: {"result": "TER0101 Tutku erkek penye atlet beyaz"})
        monkeypatch.setattr(
            ws, "sayfa_gorseller",
            lambda u: {"result": json.dumps(
                ["https://www.tutkuelit.com.tr/g/t.jpg"])})

    def test_eslesme_karta_islenir(self, tmp_path, monkeypatch):
        is_id = self._kur(tmp_path, monkeypatch)
        self._sahte_ag(monkeypatch)
        kart = next(k["kart_id"] for k in
                    _j(katalog.katalog_getir(is_id))["kartlar"]
                    if k["kod"] == "TER0101")
        r = katalog.urun_eslestir(is_id, kart)
        assert "result" in r, r
        sonuc = _j(r)
        assert sonuc["guven"] == "yuksek"
        assert sonuc["gorsel_sayisi"] == 1
        veri = _j(katalog.katalog_getir(is_id))
        eslesme = next(k for k in veri["kartlar"]
                       if k["kod"] == "TER0101")["eslesme"]
        assert eslesme["kaynak"].startswith("https://www.tutkuelit.com.tr")
        # İzin yok: yayına görsel girmez, uyarı çıkar
        t = _j(katalog.katalog_onayla(is_id))
        assert any("izin" in u for u in t["uyarilar"])
        metin = (tmp_path / "kat" / is_id
                 / "vixrex_urunler.csv").read_text(encoding="utf-8-sig")
        assert "tutkuelit" not in metin

    def test_izinli_gorsel_yayina_girer(self, tmp_path, monkeypatch):
        is_id = self._kur(tmp_path, monkeypatch)
        self._sahte_ag(monkeypatch)
        kart = next(k["kart_id"] for k in
                    _j(katalog.katalog_getir(is_id))["kartlar"]
                    if k["kod"] == "TER0101")
        katalog.urun_eslestir(is_id, kart)
        b64 = base64.b64encode(b"belge").decode("ascii")
        katalog.yetki_belgesi_ekle(is_id, b64, "izin.pdf", "Tutku")
        katalog.katalog_onayla(is_id)
        metin = (tmp_path / "kat" / is_id
                 / "vixrex_urunler.csv").read_text(encoding="utf-8-sig")
        assert "https://www.tutkuelit.com.tr/g/t.jpg" in metin

    def test_kayitsiz_marka(self, tmp_path, monkeypatch):
        is_id = self._kur(tmp_path, monkeypatch)
        kart = next(k["kart_id"] for k in
                    _j(katalog.katalog_getir(is_id))["kartlar"]
                    if k["kod"] == "BR-7")
        r = katalog.urun_eslestir(is_id, kart)
        assert "error" in r and "kaydı yok" in r["error"]
        veri = _j(katalog.katalog_getir(is_id))
        assert next(k for k in veri["kartlar"]
                    if k["kod"] == "BR-7")["eslesme"] is None

    def test_site_disi_sonuc(self, tmp_path, monkeypatch):
        from tools import web_search as ws
        is_id = self._kur(tmp_path, monkeypatch)
        monkeypatch.setattr(
            ws, "web_search",
            lambda q: {"result": "X\nhttps://baska.com/x\naciklama"})
        kart = next(k["kart_id"] for k in
                    _j(katalog.katalog_getir(is_id))["kartlar"]
                    if k["kod"] == "TER0101")
        r = katalog.urun_eslestir(is_id, kart)
        assert "error" in r and "bulunamadı" in r["error"]


class TestCheckupTemizlik:
    """2026-09-15 checkup kilitleri: fail-fast PDF, oksuz yetki red,
    cikti_oku arac baglantisi."""

    def _koklar(self, tmp_path, monkeypatch):
        monkeypatch.setattr(katalog, "GELEN_KOK", str(tmp_path / "gelen"))
        monkeypatch.setattr(katalog, "KATALOG_KOK", str(tmp_path / "kat"))
        monkeypatch.setattr(katalog, "YETKI_KOK", str(tmp_path / "yzk"))
        os.makedirs(tmp_path / "gelen", exist_ok=True)

    def test_staging_pdf_fail_fast(self, tmp_path, monkeypatch):
        self._koklar(tmp_path, monkeypatch)
        import base64 as _b64
        b64 = _b64.b64encode(b"%PDF-sahte").decode("ascii")
        r = katalog.fatura_kaydet_b64(b64, "fatura.pdf")
        assert "error" in r and "PDF" in r["error"]
        assert list((tmp_path / "gelen").glob("*.pdf")) == []

    def test_yetki_oksuz_reddi(self, tmp_path, monkeypatch):
        self._koklar(tmp_path, monkeypatch)
        import base64 as _b64
        b64 = _b64.b64encode(b"belge").decode("ascii")
        r = katalog.yetki_belgesi_ekle("", b64, "izin.pdf", "")
        assert "error" in r

    def test_cikti_oku_arac_bagli(self, tmp_path, monkeypatch):
        self._koklar(tmp_path, monkeypatch)
        (tmp_path / "gelen" / "gln_c.jpg").write_bytes(b"\xff\xd8x")
        is_id = _j(katalog.katalog_kur("gln_c", [
            {"marka": "Tutku", "kod": "T1", "adet": 1}]))["is_id"]
        katalog.katalog_onayla(is_id)
        r = calistir("cikti_oku", {"is_id": is_id,
                                   "dosya": "vixrex_urunler.csv"})
        assert "result" in r and "Ürün Adı" in r["result"]
        assert "error" in calistir(
            "cikti_oku", {"is_id": is_id, "dosya": "kotu.csv"})
        assert "error" in calistir(
            "cikti_oku", {"is_id": "ktg_yok", "dosya": "vixrex_urunler.csv"})
