"""tests/test_not_benzersiz.py — Aynı adlı kayıtlar üzerine YAZILMAZ.

2026-08-24'te Casper'in bulgusu: save_note/deftere_kaydet başlıktan slug
üretip "w" modunda açıyordu; aynı slug eski kaydı EZİYOR — defterin
"üzerine yazılmaz" felsefesiyle çelişiyordu. INDEX güncelleyicisi üstüne
ikinci satır da eklemiyordu (kayıp sessizce oluyordu).

Yeni kural: mevcut dosya korunur; yeni kayıt '-2', '-3'... sonekli
dosyaya yazılır ve INDEX'e kendi satırı düşer.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.notes import deftere_kaydet, save_note


def oku(yol):
    with open(yol, encoding="utf-8") as f:
        return f.read()


class TestSaveNote:
    def test_ayni_baslik_iki_kez_her_iksi_yasar(self, tmp_path):
        kdir = str(tmp_path / "knowledge")
        r1 = save_note("Alışveriş", "süt al", kdir)
        r2 = save_note("Alışveriş", "ekmek al", kdir)
        assert r1["result"].endswith("alışveriş.md")
        assert r2["result"].endswith("alışveriş-2.md")
        # eski içerik sağlam
        assert "süt al" in oku(tmp_path / "knowledge" / "alışveriş.md")
        assert "ekmek al" in oku(tmp_path / "knowledge" / "alışveriş-2.md")

    def test_ucuncu_kayit_sira_ile_artar(self, tmp_path):
        kdir = str(tmp_path / "k")
        for i in range(3):
            save_note("Plan", "icerik %d" % i, kdir)
        dosyalar = sorted(os.listdir(kdir))
        assert "plan.md" in dosyalar and "plan-2.md" in dosyalar \
            and "plan-3.md" in dosyalar

    def test_index_her_not_icin_satir_tutar(self, tmp_path):
        kdir = str(tmp_path / "k")
        save_note("Not", "bir", kdir)
        save_note("Not", "iki", kdir)
        index = oku(os.path.join(kdir, "INDEX.md"))
        assert "not.md" in index and "not-2.md" in index


class TestDeftereKaydet:
    def test_defterde_uzerine_yazilmaz(self, tmp_path):
        ddir = str(tmp_path / "defter")
        r1 = deftere_kaydet("Test Kararı", "eski karar metni",
                            ddir, kim="casper", tip="karar", omur="sonsuz")
        r2 = deftere_kaydet("Test Kararı", "yeni karar metni",
                            ddir, kim="basak", tip="karar", omur="30g")
        assert r1["result"].endswith("test-kararı.md")
        assert r2["result"].endswith("test-kararı-2.md")
        eski = oku(tmp_path / "defter" / "test-kararı.md")
        yeni = oku(tmp_path / "defter" / "test-kararı-2.md")
        assert "eski karar metni" in eski and "kim:    casper" in eski
        assert "yeni karar metni" in yeni and "kim:    basak" in yeni

    def test_index_iki_satiri_da_tasar(self, tmp_path):
        ddir = str(tmp_path / "d")
        deftere_kaydet("Konu", "bir", ddir)
        deftere_kaydet("Konu", "iki", ddir)
        index = oku(os.path.join(ddir, "INDEX.md"))
        assert "konu.md" in index and "konu-2.md" in index

    def test_slug_bos_dusecekse_varsayilan_kullanilir(self, tmp_path):
        ddir = str(tmp_path / "d")
        r = deftere_kaydet("!!! ???", "içerik", ddir)
        assert "kayit.md" in r["result"]
