"""tests/test_aktarici.py — FAY-3: Aktarıcı (kendi külliyatından transfer).

Kabul ölçütü (FAY-MOTORU.md): Casper'ın "bunu ben düşünmemiştim"
dediği en az bir aktarım. v0'da motorun işi: çatlağın ŞEKLİNE benzeyen
çözülmüş kararı defter'den bulup mekanizmasını önermek.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from tools.aktarici import aktarim_onerisi, cozumlu_kayitlari


def kayit_yaz(defter_dir, ad, konu, tip, icerik, kim="casper"):
    ham = (
        "---\n"
        "kim:    %s\n"
        "tarih:  2026-08-01\n"
        "konu:   %s\n"
        "tip:    %s\n"
        "omur:   sonsuz\n"
        "kaynak: sohbet\n"
        "---\n\n"
        "%s\n"
    ) % (kim, konu, tip, icerik)
    with open(os.path.join(defter_dir, ad), "w", encoding="utf-8") as f:
        f.write(ham)


@pytest.fixture
def kulliyat(tmp_path):
    """Casper'ın çözülmüş-çelişki külliyatı + bir alıntı kaydı."""
    d = tmp_path / "defter"
    d.mkdir()
    kayit_yaz(d, "xsese-onay-mekanizmasi.md", "Xses onay sorunu",
             "karar",
             "icerik otomatik cekilmeli ama izin yok -> kullanici kendi "
             "hesabiyla kendi icerigini onayliyor")
    kayit_yaz(d, "vixrex-yayin-kapisi.md", "VixRex yayin kapisi",
              "karar",
              "kullanici kod bilmiyor ama site duzenlemeli -> tikla "
              "degistir + asistan taslak uretir + yayin ayri onay kapisi")
    kayit_yaz(d, "gunluk-not.md", "Gunluk not", "alinti",
              "bu bir karar degil sadece alinti kaydi")
    return str(d)


class TestAktarici:
    def test_karar_tipi_kayitlar_havuza_duser_alinti_degil(self, kulliyat):
        cozumler = cozumlu_kayitlari(kulliyat)
        konular = [c["konu"] for c in cozumler]
        assert len(cozumler) == 2
        assert all("Gunluk" not in k for k in konular)

    def test_benzer_sekildeki_cozumu_onerir(self, kulliyat):
        catlak = {
            "konu": "NumeraMatch 18+ kapısı",
            "gerekce": "icerik otomatik gelmeli ama izin alinamiyor",
            "cift": ("belge", "git"),
        }
        cozumlu = cozumlu_kayitlari(kulliyat)
        oneri = aktarim_onerisi(catlak, cozumlu)
        assert oneri["adaylar"], "benzer sekil bulunamadi"
        assert "onay" in json_str(oneri)

    def test_eslesme_yoksa_bos_doner(self, kulliyat):
        catlak = {"konu": "tamamen alakasiz konu xyz",
                  "gerekce": "hicbir ortak kelime yok burada qzxq",
                  "cift": ("belge", "git")}
        oneri = aktarim_onerisi(catlak, cozumlu_kayitlari(kulliyat))
        assert oneri["adaylar"] == []
        assert "dis arama" in oneri["not"]

    def test_limit_uygulanir(self, kulliyat):
        cozumlu = cozumlu_kayitlari(kulliyat)
        catlak = {"konu": "onay izin kapisi icerik",
                  "gerekce": "kullanici onayi icerik izin",
                  "cift": ("belge", "git")}
        oneri = aktarim_onerisi(catlak, cozumlu, limit=1)
        assert len(oneri["adaylar"]) <= 1

    def test_bos_kulliyat_guvenli(self, tmp_path):
        d = tmp_path / "bos"
        d.mkdir()
        oneri = aktarim_onerisi({"konu": "x", "gerekce": "y"},
                                cozumlu_kayitlari(str(d)))
        assert oneri["adaylar"] == []


def json_str(obj):
    import json
    return json.dumps(obj, ensure_ascii=False)
