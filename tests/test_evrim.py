"""tests/test_evrim.py — EVRIM-0: hipotez havuzu + nüfus arşivi testleri.

Döngü: üret → deney/ölç → ele → hayatta kalanları tut → kombinasyon/mutasyon
→ tekrar. Puanlar DENEY-0 motorundan gelir; LLM puanı değildir.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from tools.evrim import Arsiv, evrim_turu


class TestHavuz:
    def test_ekle_ve_puanla(self, tmp_path):
        a = Arsiv(str(tmp_path / "arsiv.json"))
        hid = a.hipotez_ekle("vitrin siralamasi kart bazli olsun")
        a.puanla(hid, 0.83, "deney: tiklama orani %83")
        h = a.hipotez(hid)
        assert h["puan"] == 0.83 and h["durum"] == "test_edildi"

    def test_olmayan_id_puanlama_hata(self, tmp_path):
        a = Arsiv(str(tmp_path / "a.json"))
        with pytest.raises(ValueError):
            a.puanla("H999", 1.0)

    def test_en_iyiler_puana_gore_sirali(self, tmp_path):
        a = Arsiv(str(tmp_path / "a.json"))
        for i, p in enumerate((0.2, 0.9, 0.5)):
            hid = a.hipotez_ekle("h %d" % i)
            a.puanla(hid, p)
        en_iyi = a.en_iyiler(limit=2)
        assert [h["puan"] for h in en_iyi] == [0.9, 0.5]


class TestKombinasyon:
    def test_cocuk_ebeveynleri_tasir(self, tmp_path):
        a = Arsiv(str(tmp_path / "a.json"))
        ha = a.hipotez_ekle("kart bazli siralama")
        hb = a.hipotez_ekle("karanlik tema")
        hc = a.kombinasyon(ha, hb, "kart bazli siralama + karanlik tema")
        cocuk = a.hipotez(hc)
        assert cocuk["ebeveynler"] == [ha, hb]
        assert cocuk["nesil"] == 1

    def test_mutasyon_nesil_artirir(self, tmp_path):
        a = Arsiv(str(tmp_path / "a.json"))
        hk = a.hipotez_ekle("orijinal fikir")
        hm = a.mutasyon(hk, "orijinal fikir + kucuk degisiklik")
        assert a.hipotez(hm)["nesil"] == 1


class TestEvrimTuru:
    def test_eleme_hayatta_kalma_dongusu(self, tmp_path):
        """20 hipotez→ele→5 kalan mantığının küçük ölçekli kanıtı:
        6 aday üretilir, ölçüme göre en iyi 2 hayatta kalır."""
        a = Arsiv(str(tmp_path / "a.json"))

        adaylar = ["hipotez %d" % i for i in range(6)]

        def uretici():
            return adaylar

        def degerlendirici(hid, icerik):
            # olcum: icerikteki sayi ne kadar buyukse o kadar iyi
            sayi = int(icerik.split()[-1])
            return sayi / 5.0, "olcum puanı"

        kalanlar = evrim_turu(a, uretici, degerlendirici,
                              hayatta_limit=2)

        assert len(kalanlar) == 2
        # en yuksek sayili iki hipotez (4 ve 5) hayatta
        idler = {k["id"] for k in kalanlar}
        assert "H005" in idler and "H006" in idler
        # elenenler arsivde 'elenmis' isaretli — silinmemis
        elenmis = [h for h in a._yukle()["hipotezler"]
                   if h["durum"] == "elenmis"]
        assert len(elenmis) == 4

    def test_kombinasyonla_yeni_nesil_uretilir(self, tmp_path):
        a = Arsiv(str(tmp_path / "a.json"))
        h1 = a.hipotez_ekle("fikir A")
        h2 = a.hipotez_ekle("fikir B")
        a.puanla(h1, 0.8)
        a.puanla(h2, 0.7)
        hc = a.kombinasyon(h1, h2, "A+B hibrit")
        tur_sonucu = evrim_turu(
            a,
            lambda: ["A+B hibrit v2"],
            lambda hid, ic: (0.95, "hibrit daha iyi cikti"),
            hayatta_limit=3)
        assert tur_sonucu[0]["puan"] == 0.95
        cocuk = a.hipotez(hc)
        assert cocuk["nesil"] == 1


class TestKalicilik:
    def test_arsiv_dosyadan_yeniden_acilir(self, tmp_path):
        yol = str(tmp_path / "kalici.json")
        a1 = Arsiv(yol)
        hid = a1.hipotez_ekle("kalici fikir")
        a1.puanla(hid, 0.66)
        a2 = Arsiv(yol)
        h = a2.hipotez(hid)
        assert h and h["puan"] == 0.66

    def test_tmp_artigi_birakilmaz(self, tmp_path):
        a = Arsiv(str(tmp_path / "t.json"))
        a.hipotez_ekle("x")
        assert not os.path.exists(str(tmp_path / "t.json") + ".tmp")
