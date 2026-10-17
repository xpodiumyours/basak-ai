"""tests/test_fatura_metin_katmani.py — Kapsam 1: fatura metni + satır tutarı.

Sözleşme (2026-10-13):
- Üst bilgi etiketleri belge biçimine bağlı değildir: fiş, fatura ve
  e-Arşiv dökümünde aynı olgu aynı anahtara yazılır.
- Bulunamayan alan uydurulmaz; anahtar hiç yazılmaz.
- "Ara Toplam" ve "Toplam KDV" genel toplam sayılmaz.
- Faturadaki satır tutarı basılıysa miktar × birim fiyat ile
  karşılaştırılır; tutmazsa satır REDDEDİLMEZ, esnafa soru üretilir.

Eski fiş biçiminin (Tutku tipi Satış Teklif Form) gerileme güvencesi
tests/test_esnaf_faz_ab.py içindeki TestUstbilgi'de durur.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import katalog


# Gerçek e-Arşiv başlık düzeni: etiketler farklı, olgular aynı.
E_ARSIV = (
    "ABC TEKSTİL SANAYİ VE TİCARET A.Ş.\n"
    "Satıcı : ABC TEKSTİL SANAYİ VE TİCARET A.Ş.\n"
    "Vergi Dairesi : Kadıköy\n"
    "VKN : 1234567890\n"
    "e-Arşiv Fatura No : GIB2026000001234\n"
    "ETTN : 8f14e45f-ceea-467e-b5a0-1a2b3c4d5e6f\n"
    "Düzenleme Tarihi : 12.09.2026\n"
    "Alıcı : ÖRNEK MAĞAZA LTD. ŞTİ.\n"
    "Ara Toplam : 5.000,00 TL\n"
    "KDV Oranı : 20\n"
    "Toplam KDV : 1.000,00 TL\n"
    "Genel Toplam : 6.000,00 TL\n"
)


class TestUstBilgi:
    def test_e_arsiv_alanlari_okunur(self):
        ust = katalog._ustbilgi_cikar(E_ARSIV)
        assert ust["fis_no"] == "GIB2026000001234"
        assert ust["ettn"] == "8f14e45f-ceea-467e-b5a0-1a2b3c4d5e6f"
        assert ust["tarih"] == "12.09.2026"
        assert ust["firma"] == "ABC TEKSTİL SANAYİ VE TİCARET A.Ş"
        assert ust["alici"] == "ÖRNEK MAĞAZA LTD. ŞTİ"
        assert ust["vkn"] == "1234567890"
        assert ust["vergi_dairesi"] == "Kadıköy"
        assert ust["kdv_oran"] == 20
        assert ust["para_birimi"] == "TL"

    def test_ara_toplam_genel_toplam_sayilmaz(self):
        """Üç tutar ayrı kalır; ara toplam genel toplam yerine geçmez."""
        ust = katalog._ustbilgi_cikar(E_ARSIV)
        assert ust["ara_toplam"] == pytest.approx(5000.0)
        assert ust["kdv_tutar"] == pytest.approx(1000.0)
        assert ust["toplam"] == pytest.approx(6000.0)

    def test_toplam_kdv_genel_toplam_sayilmaz(self):
        """Yalnız 'Toplam KDV' varsa genel toplam uydurulmaz."""
        ust = katalog._ustbilgi_cikar("Toplam KDV : 1.000,00 TL\n")
        assert "toplam" not in ust
        assert ust["kdv_tutar"] == pytest.approx(1000.0)

    def test_ekli_kelime_etiket_sayilmaz(self):
        """'Firmamız' / 'Vergi Dairesimiz' bir etiket değildir."""
        ust = katalog._ustbilgi_cikar(
            "Firmamız : ÖRNEK A.Ş.\nVergi Dairesimiz : Kadıköy\n")
        assert "firma" not in ust
        assert "vergi_dairesi" not in ust

    def test_tarihsiz_etiketleri_tahmin_etmez(self):
        """'Son Ödeme Tarihi' düzenleme tarihi sayılmaz."""
        ust = katalog._ustbilgi_cikar("Son Ödeme Tarihi : 01.01.2027\n")
        assert "tarih" not in ust

    def test_bos_ve_etiketsiz(self):
        assert katalog._ustbilgi_cikar("") == {}
        ust = katalog._ustbilgi_cikar("sadece bir satır")
        assert "fis_no" not in ust and "toplam" not in ust
        assert "vkn" not in ust and "firma" not in ust


def _kur(tmp_path, monkeypatch, satirlar):
    monkeypatch.setattr(katalog, "GELEN_KOK", str(tmp_path / "gelen"))
    monkeypatch.setattr(katalog, "KATALOG_KOK", str(tmp_path / "kat"))
    os.makedirs(tmp_path / "gelen", exist_ok=True)
    (tmp_path / "gelen" / "gln_f.jpeg").write_bytes(b"\xff\xd8x")
    r = katalog.katalog_kur("gln_f", satirlar)
    assert "result" in r, r
    return json.loads(r["result"])


def _satir(**ek):
    satir = {"marka": "Tutku", "kod": "K1", "adet": 5,
             "alis_fiyat": "120,50", "renk": "Siyah",
             "kategori": "Erkek Tişört"}
    satir.update(ek)
    return satir


class TestSatirTutari:
    def test_tutar_tutuyorsa_soru_yok(self, tmp_path, monkeypatch):
        ozet = _kur(tmp_path, monkeypatch, [_satir(tutar="602,50")])
        assert ozet["sorulacaklar"] == []

    def test_tutar_tutmuyorsa_soru_uretir(self, tmp_path, monkeypatch):
        ozet = _kur(tmp_path, monkeypatch, [_satir(tutar="700,00")])
        sorular = "\n".join(ozet["sorulacaklar"])
        assert "SOR:" in sorular
        assert "K1" in sorular
        assert "602.50" in sorular and "700" in sorular

    def test_tutmazsa_satir_yine_kabul_edilir(self, tmp_path, monkeypatch):
        """Çelişki satırı düşürmez; kart kurulur, soru üretilir."""
        ozet = _kur(tmp_path, monkeypatch, [_satir(tutar="700,00")])
        assert ozet["sorulacaklar"]
        r = katalog.katalog_getir(ozet["is_id"])
        veri = json.loads(r["result"])
        assert len(veri["kartlar"]) == 1
        assert veri["kartlar"][0]["toplam_adet"] == 5

    def test_tutar_yoksa_sessiz(self, tmp_path, monkeypatch):
        """Satır tutarı okunmamışsa çarpım denetimi sessiz kalır."""
        ozet = _kur(tmp_path, monkeypatch, [_satir()])
        assert ozet["sorulacaklar"] == []

    def test_kucuk_yuvarlama_farki_soru_uretmez(self, tmp_path,
                                                monkeypatch):
        ozet = _kur(tmp_path, monkeypatch, [_satir(tutar="602,51")])
        assert ozet["sorulacaklar"] == []

    def test_cozulemez_tutar_uyari_uretir(self, tmp_path, monkeypatch):
        """Çözülemeyen tutar, alis_fiyat gibi bilgi uyarısı üretir."""
        ozet = _kur(tmp_path, monkeypatch, [_satir(tutar="belirsiz")])
        assert any("satır tutarı" in u for u in ozet["uyarilar"])
        assert ozet["sorulacaklar"] == []

    def test_varyantta_fatura_tutari_saklanir(self, tmp_path, monkeypatch):
        ozet = _kur(tmp_path, monkeypatch, [_satir(tutar="602,50")])
        veri = json.loads(katalog.katalog_getir(ozet["is_id"])["result"])
        varyant = veri["kartlar"][0]["varyantlar"][0]
        assert varyant["tutar"] == pytest.approx(602.5)
        assert varyant["alis_fiyat"] == pytest.approx(120.5)


# Gerçek belge (14.10.2026, IKEA/MAPA faturası) OCR metni olarak.
# Aynı belgede iki VKN/vergi dairesi var: satıcı ve alıcı.
IKEA_FATURA = (
    "MAPA MOBİLYA VE AKSESUAR PAZARLAMA A.Ş.\n"
    "Fatih Sultan Mehmet Mah. Balkan Cad. No:62\n"
    "Ümraniye / İstanbul\n"
    "Tel: 444 4 532\n"
    "www.ikea.com.tr\n"
    "FATURA\n"
    "Ön Bilgilendirme\n"
    "Tarih : 14.10.2026\n"
    "Fatura No : IK-2026-10427\n"
    "Düzenleme Saati : 15:42\n"
    "Sayfa : 1 / 1\n"
    "Vergi Dairesi: Ümraniye\n"
    "VKN: 6120729513\n"
    "Mersis No: 0612072951300010\n"
    "SATICI BİLGİLERİ\n"
    "MAPA MOBİLYA VE AKSESUAR PAZARLAMA A.Ş.\n"
    "Fatih Sultan Mehmet Mah. Balkan Cad. No:62\n"
    "Ümraniye / İstanbul\n"
    "Tel: 444 4 532\n"
    "www.ikea.com.tr\n"
    "ALICI BİLGİLERİ\n"
    "Nova İç Mimarlık ve Tasarım Ltd. Şti.\n"
    "Esentepe Mah. Büyükdere Cad. No:101\n"
    "Şişli / İstanbul\n"
    "Vergi Dairesi: Zincirlikuyu\n"
    "VKN: 2345678901\n"
    "Matrah: 54.720,00 TL\n"
    "KDV (%20): 10.944,00 TL\n"
    "GENEL TOPLAM: 65.664,00 TL"
)


class TestIkeaFaturasi:
    """Ölçülen belge: iki VKN'li faturada bölüm başlığı değer sanılmaz."""

    def test_belge_bilgileri(self):
        ust = katalog._ustbilgi_cikar(IKEA_FATURA)
        assert ust["fis_no"] == "IK-2026-10427"
        assert ust["tarih"] == "14.10.2026"
        assert ust["saat"] == "15:42"
        assert ust["para_birimi"] == "TL"
        assert ust["kdv_oran"] == 20

    def test_bolum_basligi_deger_sayilmaz(self):
        """Ölçülen hata: 'SATICI BİLGİLERİ' firma adı sanılmıştı."""
        ust = katalog._ustbilgi_cikar(IKEA_FATURA)
        assert ust["firma"] == "MAPA MOBİLYA VE AKSESUAR PAZARLAMA A.Ş"
        assert ust["alici"] == "Nova İç Mimarlık ve Tasarım Ltd. Şti"
        assert "BİLGİLERİ" not in " ".join(str(v) for v in ust.values())

    def test_satici_ve_alici_vergisi_ayrilir(self):
        ust = katalog._ustbilgi_cikar(IKEA_FATURA)
        assert ust["vkn"] == "6120729513"
        assert ust["vergi_dairesi"] == "Ümraniye"
        assert ust["alici_vkn"] == "2345678901"
        assert ust["alici_vergi_dairesi"] == "Zincirlikuyu"
        assert ust["mersis_no"] == "0612072951300010"

    def test_matrah_ve_kdv_tutari_okunur(self):
        ust = katalog._ustbilgi_cikar(IKEA_FATURA)
        assert ust["ara_toplam"] == pytest.approx(54720.0)
        assert ust["kdv_tutar"] == pytest.approx(10944.0)
        assert ust["toplam"] == pytest.approx(65664.0)
        # Belgenin kendi aritmetiği: matrah + KDV = genel toplam.
        assert (ust["ara_toplam"] + ust["kdv_tutar"]
                == pytest.approx(ust["toplam"]))

    def test_bagimsiz_tarih_satir_basi_ister(self):
        """Satır başında olmayan 'Tarih' düzenleme tarihi sayılmaz."""
        ust = katalog._ustbilgi_cikar(
            "Son Ödeme Tarih : 01.01.2027\nVade Tarihi : 05.01.2027\n")
        assert "tarih" not in ust


SATIRLAR_IKEA = [
    ("002.638.50", "BILLY Kitaplık Beyaz 80x28x202 cm", 2, "4.299,00",
     "8.598,00"),
    ("795.529.08", "KALLAX Açık Raf Ünitesi Beyaz 147x77 cm", 1, "7.199,00",
     "7.199,00"),
    ("200.114.08", "LACK Yan Sehpa Siyah 55x55 cm", 2, "189,00", "378,00"),
    ("802.130.74", "MICKE Çalışma Masası Beyaz 105x50 cm", 1, "6.499,00",
     "6.499,00"),
    ("102.392.80", "HEMNES 8 Çekmeceli Şifonyer Beyaz 160x95 cm", 1,
     "24.999,00", "24.999,00"),
    ("405.821.81", "RÅSKOG Tekerlekli Servis Arabası Siyah 35x45x77 cm", 2,
     "3.299,00", "6.598,00"),
    ("003.208.03", "SKÅDIS Çok Amaçlı Pano Beyaz 56x56 cm", 2, "1.199,00",
     "2.398,00"),
    ("306.376.31", "FEJKA Yapay Bitki İç/Dış Mekan 15 cm", 3, "999,00",
     "2.997,00"),
    ("802.638.32", "BILLY Kitaplık Beyaz 40x28x106 cm", 1, "1.699,00",
     "1.699,00"),
    ("302.130.76", "MICKE Çalışma Masası Beyaz 73x50 cm", 1, "4.299,00",
     "4.299,00"),
]


# Tablo satırları OCR metninde böyle tek satır hâlinde gelir.
IKEA_TABLO = (
    "1 002.638.50 BILLY Kitaplık Beyaz 80x28x202 cm 2 4.299,00 TL 8.598,00 TL\n"
    "2 795.529.08 KALLAX Açık Raf Ünitesi Beyaz 147x77 cm, kapaklı 1 "
    "7.199,00 TL 7.199,00 TL\n"
    "3 200.114.08 LACK Yan Sehpa Siyah 55x55 cm 2 189,00 TL 378,00 TL\n"
    "4 802.130.74 MICKE Çalışma Masası Beyaz 105x50 cm 1 6.499,00 TL "
    "6.499,00 TL\n"
    "5 102.392.80 HEMNES 8 Çekmeceli Şifonyer Beyaz 160x95 cm 1 "
    "24.999,00 TL 24.999,00 TL\n"
    "6 405.821.81 RÅSKOG Tekerlekli Servis Arabası Siyah 35x45x77 cm 2 "
    "3.299,00 TL 6.598,00 TL\n"
    "7 003.208.03 SKÅDIS Çok Amaçlı Pano Beyaz 56x56 cm 2 1.199,00 TL "
    "2.398,00 TL\n"
    "8 306.376.31 FEJKA Yapay Bitki İç/Dış Mekan 15 cm 3 999,00 TL "
    "2.997,00 TL\n"
    "9 802.638.32 BILLY Kitaplık Beyaz 40x28x106 cm 1 1.699,00 TL 1.699,00 TL\n"
    "10 302.130.76 MICKE Çalışma Masası Beyaz 73x50 cm 1 4.299,00 TL "
    "4.299,00 TL"
)


class TestSatirTablosu:
    def test_on_satir_yapisal_okunur(self):
        satirlar = katalog.satir_tablosu(IKEA_TABLO)
        assert len(satirlar) == 10
        ilk = satirlar[0]
        assert ilk["sira"] == 1
        assert ilk["kod"] == "002.638.50"
        assert ilk["ad"] == "BILLY Kitaplık Beyaz 80x28x202 cm"
        assert ilk["miktar"] == 2
        assert ilk["birim_fiyat"] == pytest.approx(4299.0)
        assert ilk["tutar"] == pytest.approx(8598.0)
        assert ilk["tutar_tutarli"] is True

    def test_olcu_icerikleri_miktar_sayilmaz(self):
        """Açıklamadaki '15 cm' ve '80x28x202 cm' miktar sanılmamalı."""
        satirlar = katalog.satir_tablosu(IKEA_TABLO)
        assert satirlar[7]["miktar"] == 3
        assert satirlar[7]["ad"].endswith("15 cm")
        assert satirlar[0]["miktar"] == 2

    def test_tutarlar_toplami_belgeyle_ayni(self):
        satirlar = katalog.satir_tablosu(IKEA_TABLO)
        toplam = round(sum(s["tutar"] for s in satirlar), 2)
        assert toplam == pytest.approx(65664.0)

    def test_uymayan_satir_isaretlenir(self):
        satir = katalog.satir_tablosu(
            "1 200.114.08 LACK Yan Sehpa Siyah 55x55 cm 2 189,00 TL 999,00 TL")
        assert satir[0]["tutar_tutarli"] is False

    def test_tablo_olmayan_satir_donmez(self):
        assert katalog.satir_tablosu(
            "Fiş No : 59.2026.49048\nTK-102 Siyah S 5 ad 120,50 TL") == []
        assert katalog.satir_tablosu("") == []


def _kart_satirlari():
    """Satırlar modelden gelir (görsel okuma); burada boru hattı ölçülür."""
    return [{"marka": "IKEA", "kod": k, "urun_adi": ad,
             "adet": adet, "alis_fiyat": birim, "tutar": tutar,
             "kategori": "Mobilya", "renk": "Beyaz"}
            for k, ad, adet, birim, tutar in SATIRLAR_IKEA]


class TestFaturaDuzeyiTutar:
    def test_on_satir_ve_tutarlar_tutarli(self, tmp_path, monkeypatch):
        monkeypatch.setattr(katalog, "GELEN_KOK", str(tmp_path / "gelen"))
        monkeypatch.setattr(katalog, "KATALOG_KOK", str(tmp_path / "kat"))
        os.makedirs(tmp_path / "gelen", exist_ok=True)
        (tmp_path / "gelen" / "gln_i.jpeg").write_bytes(b"\xff\xd8x")
        r = katalog.katalog_kur("gln_i", _kart_satirlari(),
                                ustbilgi=katalog._ustbilgi_cikar(IKEA_FATURA))
        assert "result" in r, r
        ozet = json.loads(r["result"])
        assert ozet["kart_sayisi"] == 10
        assert ozet["toplam_adet"] == 16
        # Satır tutarları da belgenin genel toplamına eşit olmalı.
        assert ozet["sorulacaklar"] == []

    def test_satir_tutari_toplamla_celistiginde_soru_uretir(self, tmp_path,
                                                            monkeypatch):
        monkeypatch.setattr(katalog, "GELEN_KOK", str(tmp_path / "gelen"))
        monkeypatch.setattr(katalog, "KATALOG_KOK", str(tmp_path / "kat"))
        os.makedirs(tmp_path / "gelen", exist_ok=True)
        (tmp_path / "gelen" / "gln_i.jpeg").write_bytes(b"\xff\xd8x")
        satirlar = _kart_satirlari()
        # Satır düzeyi tutarlı kalır (miktar × birim = tutar), ama
        # basılı genel toplam artık tutmaz — fatura düzeyi uyarı çıkar.
        satirlar[0]["tutar"] = "8.098,00"
        satirlar[0]["alis_fiyat"] = "4.049,00"
        r = katalog.katalog_kur("gln_i", satirlar,
                                ustbilgi=katalog._ustbilgi_cikar(IKEA_FATURA))
        ozet = json.loads(r["result"])
        assert ozet["kart_sayisi"] == 10
        assert any("Fatura düzeyi" in s for s in ozet["sorulacaklar"])

    def test_tutar_eksikse_fatura_denetimi_sessiz(self, tmp_path,
                                                  monkeypatch):
        monkeypatch.setattr(katalog, "GELEN_KOK", str(tmp_path / "gelen"))
        monkeypatch.setattr(katalog, "KATALOG_KOK", str(tmp_path / "kat"))
        os.makedirs(tmp_path / "gelen", exist_ok=True)
        (tmp_path / "gelen" / "gln_i.jpeg").write_bytes(b"\xff\xd8x")
        satirlar = _kart_satirlari()
        for satir in satirlar:
            satir.pop("tutar")
        r = katalog.katalog_kur("gln_i", satirlar,
                                ustbilgi=katalog._ustbilgi_cikar(IKEA_FATURA))
        ozet = json.loads(r["result"])
        assert not any("Fatura düzeyi" in s for s in ozet["sorulacaklar"])
