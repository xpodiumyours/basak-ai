"""tests/test_belge_sagligi.py — Belgeler gerçeği söylüyor mu? (denetim
2026-08-24).

Ilke: belge bayatlamasi projenin 1 numarali bilgi riski. Bu testler
belgelerdeki iddialari gercekle karsilastirir:

- AGENTS.md artik "otomatik test yok" DEMEMELI (470+ test varken)
- ANALIZ-chatbot-vs-asistan.md basinda bayatlik notu OLMALI
- DURUM.md'deki sayilar gercek olcumle AYNI OLMALI — kod degisip
  belge guncellenmezse bu test kirilir ve yazarini zorlar.

Bu dosya bir "belge sagligi" kapisiydir: yeni bir bayat iddia yakalanmak
istenirse asagiya yeni bir test eklemek yeterli.
"""

import os
import re

from tools.durum import olc, uret

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _oku(ad):
    with open(os.path.join(BASE, ad), "r", encoding="utf-8",
              errors="replace") as f:
        return f.read()


class TestAgentsMd:
    def test_test_yok_iddiasi_kalmedi(self):
        """Eski 'Otomatik test yok' cümleleri tam haliyle yok olmali.
        (Tarihçe notu olarak KÜÇÜK harfli anma geçebilir; bu test yalnızca
        eski cümlenin kendisini arar.)"""
        metin = _oku("AGENTS.md")
        yasaklar = (
            "gerçek çalıştırma tek kanıt",
            "bu yüzden minimum kapı",
            "Proje küçük, otomatik test suite'i yok",
        )
        for yasak in yasaklar:
            assert yasak not in metin, (
                "AGENTS.md'de bayat iddia geri geldi: %r" % yasak)

    def test_pytest_kapisi_yaziyor(self):
        metin = _oku("AGENTS.md")
        assert "pytest tests" in metin, (
            "AGENTS.md doğrulama tablosunda pytest kapısı yok")


class TestAnalizBelgesi:
    def test_bayatlik_notu_var(self):
        bas = _oku("ANALIZ-chatbot-vs-asistan.md")[:2000]
        assert "BAYATLATILDI" in bas or "DURUM NOTU" in bas, (
            "ANALIZ belgesinin başındaki bayatlık notu kaybolmuş")


class TestDurumMd:
    def test_durum_md_gercegi_soyluyor(self):
        """DURUM.md içindeki ölçüler taze ölçümle birebir aynı olmalı.
        Kod değişince (araç ekleme, test yazma...) DURUM.md yeniden
        üretilmedikçe bu test KIRMIZI yanar — bilerek."""
        yol = os.path.join(BASE, "DURUM.md")
        assert os.path.exists(yol), (
            "DURUM.md yok: `python -m tools.durum` ile üret")
        mevcut = _oku("DURUM.md")

        o = olc()
        # Zaman damgası ve commit karşılaştırmanın dışında; sadece
        # ölçülebilir değerlere bakılır.
        taze = uret(olcum={**o, "commit": "-"},
                    simdi="KARSILASTIRMA")
        mevcut_cizgiler = {
            c for c in mevcut.splitlines()
            if c.startswith("|") and "Son commit" not in c
        }
        taze_cizgiler = {
            c for c in taze.splitlines() if c.startswith("|")
            and "Son commit" not in c
        }
        fark = taze_cizgiler - mevcut_cizgiler
        assert not fark, (
            "DURUM.md bayatlamış — güncelle: `python -m tools.durum`. "
            "Uyuşmayan satırlar: %s" % sorted(fark))

    def test_agents_rakam_gomme_yok(self):
        """AGENTS.md'in KURALLAR bölümünde kesin test sayısı taahhüt
        edilmemeli — kesin sayı DURUM.md'nin işidir. (§2'deki tarihî
        günlük kayıtları — "o gün 112/112 testti" — meşrudur; bu yüzden
        yalnızca '## 5.' sonrası denetlenir.)"""
        metin = _oku("AGENTS.md")
        kural_kismi = metin.split("## 5.", 1)[-1]
        kesin_sayi = re.findall(r"\b(\d{3,})/(\d{3,})\s*test\b", kural_kismi)
        assert not kesin_sayi, (
            "AGENTS.md kurallarına kesin test sayısı gömülmüş: %s — "
            "DURUM.md'ye yönlendir." % kesin_sayi)
