"""tests/test_esnaf_faz_ab.py — Faz A/B güvencesi.

Jargon sözlüğü, sorulacaklar, tedarikçi alias, fiş üst bilgisi,
sirket_ara aracı ve sayfa_gorseller lazy-load/logo filtresi.
Ağ erişimi olmayan testler — web_search/sayfa_oku monkeypatch ile
sahtelenir.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import calistir
from tools import katalog
from tools import web_search as ws


class TestJargon:
    def test_kisaltmalar_acilir(self):
        assert katalog.jargon_coz("ELIT ERK PENYE ATLET") == \
            "ELIT Erkek Penye Atlet"
        assert katalog.jargon_coz("BYN PEN KASKORSE") == \
            "Kadın Penye Kaşkorse"

    def test_ocr_yamulmalari(self):
        assert katalog.jargon_coz("ERK SIFIRYAKA LZUNKOL") == \
            "Erkek Sıfır Yaka Uzun Kol"
        assert katalog.jargon_coz("750 SINAR") == "750 SİYAH"
        assert katalog.jargon_coz("TUT ERK LORALI BOXER") == \
            "Tut Erkek Likralı Boxer"
        assert katalog.jargon_coz("PENYE KALI BOXER") == \
            "Penye Düz Boxer"
        assert katalog.jargon_coz("PANDORA RANDORI BATO") == \
            "PANDORA Pandora BATO"
        assert katalog.jargon_coz("BOXER ENSEMILI") == "Boxer Desenli"
        # Model kodu zarar görmez:
        assert katalog.jargon_coz("TER0107") == "TER0107"

    def test_birlesik_kelimeler(self):
        assert katalog.jargon_coz("ERK SIFIRYAKA UZUNKOL") == \
            "Erkek Sıfır Yaka Uzun Kol"

    def test_bilinmeyen_kelime_dokunulmaz(self):
        assert katalog.jargon_coz("PANDORA BATO") == "PANDORA BATO"

    def test_model_kodu_bozulmaz(self):
        assert katalog.jargon_coz("ELT1301") == "ELT1301"

    def test_bos(self):
        assert katalog.jargon_coz("") == ""


class TestTedariKciAlias:
    def test_elit_tutkuya_yonlenir(self):
        kayit, _ad = katalog.tedarikci_coz("ELIT")
        assert kayit == {"site": "tutkuelit.com.tr", "ad": "Tutku"}

    def test_tut_alias(self):
        kayit, _ad = katalog.tedarikci_coz("TUT")
        assert kayit is not None and kayit["site"] == "tutkuelit.com.tr"

    def test_kayitsiz_marka_none(self):
        kayit, ad = katalog.tedarikci_coz("BilinmeyenMarka")
        assert kayit is None and ad == "BilinmeyenMarka"

    def test_tr_karakterli_alias(self):
        kayit, _ad = katalog.tedarikci_coz("ELİT")
        assert kayit is not None


class TestUstbilgi:
    ORNEK = ("Fiş No : 59.2026.49048\n"
             "Fiş Tarihi : 28.07.2026\n"
             "İrsaliye Firma : MUHTELİF MÜŞTER\n"
             "Toplam:  142 ad  11 dz  7.974,50 TL\n"
             "KDV %10 dahil")

    def test_tum_alanlar(self):
        ust = katalog._ustbilgi_cikar(self.ORNEK)
        assert ust["fis_no"] == "59.2026.49048"
        assert ust["tarih"] == "28.07.2026"
        assert ust["firma"] == "MUHTELİF MÜŞTER"
        assert ust["kdv_oran"] == 10
        assert ust["toplam"] == pytest.approx(7974.5)
        assert ust["adet"] == 142
        assert ust["dusin"] == 11

    def test_bulunamayan_alan_yazilmaz(self):
        ust = katalog._ustbilgi_cikar("sadece bir satır")
        assert "fis_no" not in ust and "toplam" not in ust

    def test_bos(self):
        assert katalog._ustbilgi_cikar("") == {}


class TestSorulacaklar:
    def _kur(self, tmp_path, monkeypatch, satirlar):
        monkeypatch.setattr(katalog, "GELEN_KOK", str(tmp_path / "gelen"))
        monkeypatch.setattr(katalog, "KATALOG_KOK", str(tmp_path / "kat"))
        os.makedirs(tmp_path / "gelen", exist_ok=True)
        (tmp_path / "gelen" / "gln_t.jpeg").write_bytes(b"\xff\xd8x")
        r = katalog.katalog_kur("gln_t", satirlar)
        assert "result" in r, r
        return json.loads(r["result"])

    def test_eksik_alanlar_soru_olur(self, tmp_path, monkeypatch):
        ozet = self._kur(tmp_path, monkeypatch, [
            {"kod": "ELT1301", "urun_adi": "Elastan Tişört",
             "adet": 3, "alis_fiyat": "115,00",
             "kategori": "Erkek Tişört"},  # marka yok
            {"marka": "Tutku", "kod": "TER0117", "adet": "belirsiz",
             "kategori": "ERK Boxer", "renk": "Siyah"},
        ])
        sorular = "\n".join(ozet["sorulacaklar"])
        assert "marka" in sorular and "ELT1301" in sorular
        assert "adet" in sorular and "TER0117" in sorular

    def test_kategori_jargonla_cozulur(self, tmp_path, monkeypatch):
        ozet = self._kur(tmp_path, monkeypatch, [
            {"marka": "Tutku", "kod": "T1", "adet": 2,
             "kategori": "ERK Boxer"}])
        assert not any("kategori" in s for s in ozet["sorulacaklar"])

    def test_varyant_rengi_ocr_duzeltmeli_gelir(self, tmp_path,
                                                monkeypatch):
        monkeypatch.setattr(katalog, "GELEN_KOK", str(tmp_path / "gelen"))
        monkeypatch.setattr(katalog, "KATALOG_KOK", str(tmp_path / "kat"))
        os.makedirs(tmp_path / "gelen", exist_ok=True)
        (tmp_path / "gelen" / "gln_t.jpeg").write_bytes(b"\xff\xd8x")
        r = katalog.katalog_kur("gln_t", [
            {"marka": "TUT", "kod": "TER0107", "adet": 34,
             "varyant": "750 SINAR", "kategori": "ERK Boxer",
             "barkod": "8680508923371", "alis_fiyat": "63,50"}])
        veri = json.loads(r["result"])
        is_id = veri["is_id"]
        tam = json.loads(katalog.katalog_getir(is_id)["result"])
        varyant = tam["kartlar"][0]["varyantlar"][0]
        assert varyant["renk"] == "siyah"
        assert tam["kartlar"][0]["kategori"] == "Erkek Boxer"

    def test_temiz_satirda_soru_yok(self, tmp_path, monkeypatch):
        ozet = self._kur(tmp_path, monkeypatch, [
            {"marka": "Tutku", "kod": "T1", "adet": 2, "renk": "Siyah",
             "kategori": "Erkek Boxer"}])
        assert ozet["sorulacaklar"] == []

    def test_ustbilgi_is_verisine_yazilir(self, tmp_path, monkeypatch):
        monkeypatch.setattr(katalog, "GELEN_KOK", str(tmp_path / "gelen"))
        monkeypatch.setattr(katalog, "KATALOG_KOK", str(tmp_path / "kat"))
        os.makedirs(tmp_path / "gelen", exist_ok=True)
        (tmp_path / "gelen" / "gln_t.jpeg").write_bytes(b"\xff\xd8x")
        r = katalog.katalog_kur("gln_t", [
            {"marka": "Tutku", "kod": "T1", "adet": 2,
             "kategori": "Erkek Boxer"}],
            ustbilgi={"fis_no": "X", "toplam": 100})
        assert "result" in r
        is_id = json.loads(r["result"])["is_id"]
        veri = json.loads(katalog.katalog_getir(is_id)["result"])
        assert veri.get("ustbilgi", {}).get("fis_no") == "X"


class TestSirketAra:
    def _sahte_ag(self, monkeypatch):
        def web_search(sorgu):
            if "resmi site" in sorgu:
                return {"result": "x\nhttps://ornek.com.tr/\nAciklama"}
            return {"result": ""}

        def sayfa_oku(url):
            if url.endswith("/iletisim"):
                return {"result": (
                    "İletişim\n"
                    "Adres: Organize Sanayi Bölgesi 5. Cad. No:12 Bursa\n"
                    "Telefon: 0224 555 44 33\n"
                    "Cep: 0532 111 22 33\n"
                    "E-posta: info@ornek.com.tr\n"
                    "Vergi No: 1234567890\n")}
            return {"error": "yok"}
        monkeypatch.setattr(ws, "web_search", web_search)
        monkeypatch.setattr(ws, "sayfa_oku", sayfa_oku)

    def test_bilinen_markada_iletisim_bulunur(self, monkeypatch):
        self._sahte_ag(monkeypatch)
        r = calistir("sirket_ara", {"marka": "Tutku"})
        veri = json.loads(r["result"])
        assert veri["site"] == "https://tutkuelit.com.tr/iletisim"
        assert "0224 555 44 33" in veri["telefonlar"]
        assert "info@ornek.com.tr" in veri["eposta"]
        assert veri["vergi_no"] == "1234567890"
        assert any("Organize Sanayi" in a for a in veri["adresler"])

    def test_bilinmeyen_markada_arama_yolu(self, monkeypatch):
        def web_search(sorgu):
            return {"result": "x\nhttps://yeni.com/iletisim\nTel: satiri"}

        def sayfa_oku(url):
            return {"result": "Adres: Deneme Mah. 1. Sk. No:2\n"
                              "Tel: 0212 111 22 33\na@yeni.com"}
        monkeypatch.setattr(ws, "web_search", web_search)
        monkeypatch.setattr(ws, "sayfa_oku", sayfa_oku)
        r = calistir("sirket_ara", {"marka": "YeniMarka"})
        veri = json.loads(r["result"])
        assert veri["marka"] == "YeniMarka"
        assert veri["telefonlar"] == ["0212 111 22 33"]
        assert "a@yeni.com" in veri["eposta"]

    def test_bos_marka_hata(self):
        assert "error" in calistir("sirket_ara", {"marka": ""})

    def test_uc_yer(self):
        from chat.tools import DURUM_METNI
        from tools.definitions import TANINMIS_TOOLLAR
        assert "sirket_ara" in TANINMIS_TOOLLAR
        assert "sirket_ara" in DURUM_METNI


class _Yanit:
    def __init__(self, html):
        self._html = html

    headers = {"Content-Type": "text/html"}

    def read(self, n):
        return self._html.encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class TestGorselFiltre:
    def _acici(self, html):
        def ac(req, timeout=15):
            return _Yanit(html)
        return ac

    def test_data_src_toplanir_logo_elenir(self):
        html = (
            '<img src="/logo.jpg" alt="">'
            '<img data-src="/urun/ter0117.jpg">'
            '<img src="/resim/icon.png">'
            '<img srcset="/buyuk.jpg 800w, /kucuk.jpg 400w">')
        r = ws.sayfa_gorseller(
            "https://ornek.com.tr/", _acici=self._acici(html))
        gorseller = json.loads(r["result"])
        assert "https://ornek.com.tr/urun/ter0117.jpg" in gorseller
        assert "https://ornek.com.tr/buyuk.jpg" in gorseller
        assert not any("logo" in g for g in gorseller)
        assert not any("icon" in g for g in gorseller)

    def test_sadece_logovarsa_hata(self):
        html = '<img src="/logo.jpg">'
        r = ws.sayfa_gorseller(
            "https://ornek.com.tr/", _acici=self._acici(html))
        assert "error" in r
