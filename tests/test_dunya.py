"""tests/test_dunya.py — DÜNYA-0: sorgulanabilir dünya modeli testleri.

Kilitli hedefin "Dünya Modeli" organının ilk halkası. Yeni depo YOK:
defter kayıtları iddia, karne güven, bayat tazelik — üçü tek
sorgulanabilir listede birleşir.
"""

import json
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from tools import bayat
from tools.dunya import dunya_ozet, dunya_sorgu, inanclari_topla


def _kayit_yaz(defter_dir, ad, konu, kim="casper", tarih="2026-08-24",
               tip="karar", omur="30g", kaynak="git", icerik="icerik metni"):
    ham = (
        "---\n"
        "kim:    %s\n"
        "tarih:  %s\n"
        "konu:   %s\n"
        "tip:    %s\n"
        "omur:   %s\n"
        "kaynak: %s\n"
        "---\n\n"
        "%s\n"
    ) % (kim, tarih, konu, tip, omur, kaynak, icerik)
    with open(os.path.join(defter_dir, ad), "w", encoding="utf-8") as f:
        f.write(ham)


@pytest.fixture
def defter(tmp_path):
    d = tmp_path / "defter"
    d.mkdir()
    return str(d)


@pytest.fixture
def karne(monkeypatch, tmp_path):
    yol = tmp_path / "karne.json"
    monkeypatch.setattr(bayat, "_KARNE_DOSYASI", str(yol))
    return yol


class TestToplama:
    def test_bos_defter_guvenli(self, defter, karne):
        assert inanclari_topla(defter) == []
        assert "boş" in dunya_ozet(defter)

    def test_taze_ve_bayat_ayrisir(self, defter, karne):
        bugun = datetime.now().strftime("%Y-%m-%d")
        eski = (datetime.now() - timedelta(days=40)).strftime("%Y-%m-%d")
        _kayit_yaz(defter, "yeni.md", "yeni karar", tarih=bugun,
                   omur="30g")
        _kayit_yaz(defter, "eski.md", "eski karar", tarih=eski,
                   omur="30g")
        inanclar = inanclari_topla(defter)
        durumlar = {i["dosya"]: i["durum"] for i in inanclar}
        assert durumlar["yeni.md"] == "taze"
        assert durumlar["eski.md"] == "bayat"


class TestGuven:
    def test_karne_verisiyle_guven_hesaplanir(self, defter, karne):
        karne.write_text(json.dumps(
            {"git": {"v50": {"dogru": 3, "yanlis": 1}}}),
            encoding="utf-8")
        _kayit_yaz(defter, "r.md", "konu", kaynak="git")
        inanclar = inanclari_topla(defter)
        assert inanclar[0]["guven"] == 0.75

    def test_karne_verisi_yoksa_notr(self, defter, karne):
        _kayit_yaz(defter, "r.md", "konu", kaynak="sohbet")
        assert inanclari_topla(defter)[0]["guven"] == 0.5


class TestSorgu:
    @pytest.fixture
    def dolu_defter(self, defter, karne):
        bugun = datetime.now().strftime("%Y-%m-%d")
        eski = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
        karne.write_text(json.dumps({"git": {"x": {"dogru": 4,
                                                   "yanlis": 0}}}),
                         encoding="utf-8")
        _kayit_yaz(defter, "a.md", "VixRex vitrin plani", kim="casper",
                   tarih=bugun, omur="sonsuz", kaynak="git",
                   icerik="kiralik vitrin ozellikleri")
        _kayit_yaz(defter, "b.md", "NumeraMatch notu", kim="claude",
                   tarih=eski, omur="30g", kaynak="sohbet",
                   icerik="18+ kapisi karari")

    def test_anahtar_filtresi(self, defter, karne, dolu_defter):
        sonuc = dunya_sorgu(defter, anahtar="vixrex")
        assert len(sonuc) == 1 and "VixRex" in sonuc[0]["konu"]

    def test_durum_filtresi(self, defter, karne, dolu_defter):
        bayatlar = dunya_sorgu(defter, durum="bayat")
        assert len(bayatlar) == 1 and "NumeraMatch" in bayatlar[0]["konu"]

    def test_kim_ve_min_guven(self, defter, karne, dolu_defter):
        assert len(dunya_sorgu(defter, kim="claude")) == 1
        yuksek = dunya_sorgu(defter, min_guven=0.9)
        assert all(i["guven"] >= 0.9 for i in yuksek)

    def test_ozet_sayilari_dogru(self, defter, karne, dolu_defter):
        ozet = dunya_ozet(defter)
        assert "2 inanç" in ozet or "2 inan" in ozet
        assert "1 bayat" in ozet
