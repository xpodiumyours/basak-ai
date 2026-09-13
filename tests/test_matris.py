"""tests/test_matris.py — Yasayan agac (ilerleme tablosu) guvencesi.

Sozlesme:
- 9 alet uc yerde bagli (sema + calistir + DURUM_METNI).
- Sayi HICBIR yerde gecmez: semada adet alani yok, kod sayi dayatmaz.
- Kanitsiz satir kapanmaz; baglilari bitmemis kapanmaz.
- Silinen arsive gider (skor disi, metin korunur); dongu kurulamaz.
- Gercek tablo dosyasina DOKUNULMAZ — testler tmp kokte kosar.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tools.matris as matris
from tools.definitions import TANINMIS_TOOLLAR, TOOLS

ALETLER = ("matris_ac", "matris_liste", "satir_ekle", "kanit_ekle",
           "satir_kapat", "satir_ac", "satir_sil", "satir_tasi",
           "matris_durum")


class TestUcYer:
    def test_beyaz_listede(self):
        for ad in ALETLER:
            assert ad in TANINMIS_TOOLLAR, ad

    def test_durum_etiketleri_var(self):
        from chat.tools import DURUM_METNI
        for ad in ALETLER:
            assert ad in DURUM_METNI, ad

    def test_semada_sayi_alani_yok(self):
        yasak = ("adet", "sayi", "limit", "toplam", "derinlik", "tavan")
        for alet in TOOLS:
            fn = alet.get("function", {})
            if fn.get("name") not in ALETLER:
                continue
            ozellikler = fn.get("parameters", {}).get("properties", {})
            for alan in ozellikler:
                assert alan.lower() not in yasak, (fn["name"], alan)


class TestAgac:
    def test_ac_ekle_kanit_kapat(self, tmp_path, monkeypatch):
        monkeypatch.setattr(matris, "MATRIS_KOK", str(tmp_path))
        ac = matris.matris_ac("Date uygulamasi", "komşular arasi")
        assert "result" in ac, ac
        m = ac["matris"]
        a = matris.satir_ekle(m, "arastirma", "Rakipler kim?")
        k = matris.satir_ekle(m, "katman", "Guvenlik", neden="yasal sart")
        d = matris.satir_ekle(m, "adim", "Fotograf dogrulama",
                              ust=k["satir"], bagli=[a["satir"]])
        assert "error" in matris.satir_kapat(m, d["satir"])  # kanitsiz
        matris.kanit_ekle(m, a["satir"], "liste cikarildi")
        matris.satir_kapat(m, a["satir"])
        matris.kanit_ekle(m, d["satir"], "3 yontem notu")
        assert "result" in matris.satir_kapat(m, d["satir"])
        durum = matris.matris_durum(m)["result"]
        assert "skor: 2/3 kanitli" in durum
        assert "[x]" in durum and "once: #%d" % a["satir"] in durum

    def test_bagli_bitmeden_kapanmaz(self, tmp_path, monkeypatch):
        monkeypatch.setattr(matris, "MATRIS_KOK", str(tmp_path))
        m = matris.matris_ac("T", "")["matris"]
        a = matris.satir_ekle(m, "adim", "once bu")
        b = matris.satir_ekle(m, "adim", "sonra bu", bagli=[a["satir"]])
        matris.kanit_ekle(m, b["satir"], "erken kanit")
        r = matris.satir_kapat(m, b["satir"])
        assert "error" in r and str(a["satir"]) in r["error"]

    def test_sil_arsivler_skor_disi(self, tmp_path, monkeypatch):
        monkeypatch.setattr(matris, "MATRIS_KOK", str(tmp_path))
        m = matris.matris_ac("T", "")["matris"]
        a = matris.satir_ekle(m, "katman", "gereksiz dal")
        matris.satir_sil(m, a["satir"])
        durum = matris.matris_durum(m)["result"]
        assert "gereksiz" not in durum
        assert "arsivde: 1" in durum
        assert "skor: 0/0" in durum

    def test_tasi_dongu_kurar_reddedilir(self, tmp_path, monkeypatch):
        monkeypatch.setattr(matris, "MATRIS_KOK", str(tmp_path))
        m = matris.matris_ac("T", "")["matris"]
        a = matris.satir_ekle(m, "katman", "A")
        b = matris.satir_ekle(m, "adim", "B", ust=a["satir"])
        assert "error" in matris.satir_tasi(m, a["satir"], b["satir"])
        assert "result" in matris.satir_tasi(m, b["satir"], None)

    def test_gecersiz_girdiler(self, tmp_path, monkeypatch):
        monkeypatch.setattr(matris, "MATRIS_KOK", str(tmp_path))
        assert "error" in matris.matris_ac("   ")
        assert "error" in matris.matris_durum(999)
        m = matris.matris_ac("T", "")["matris"]
        assert "error" in matris.satir_ekle(m, "bolum", "x")
        assert "error" in matris.satir_ekle(m, "adim", "   ")
        assert "error" in matris.satir_ekle(m, "adim", "x", ust=999)
        assert "error" in matris.kanit_ekle(m, 1, "   ")

    def test_calistir_hatti(self, tmp_path, monkeypatch):
        from tools import calistir
        monkeypatch.setattr(matris, "MATRIS_KOK", str(tmp_path))
        r = calistir("matris_ac", {"baslik": "Hat", "fikir": "f"})
        assert "result" in r, r
        r = calistir("matris_durum", {"matris": r["matris"]})
        assert "skor: 0/0" in r["result"]
        r = calistir("matris_liste", {})
        assert "Hat" in r["result"]
