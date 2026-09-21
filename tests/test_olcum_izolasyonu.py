"""tests/test_olcum_izolasyonu.py — Ölçü aletinin bekçisi.

2026-09-22 ölçümü: `data/audit/audit.log`'daki 321 satirin 169'u TEST
koşularindan geliyordu (0.0 sn'lik satirlar). O günlük iki kararin
kaynagi:
  1. "hangi saglayici iyi" (siralama/karne),
  2. "bugün kac istek harcadim" (kota sayaci — `model_stats.db`).
Test gürültüsü bu kararlari bozar. `conftest.py`'deki otomatik kapi
her testi geçici dosyaya yönlendirir; bu dosya o kapinin bekcisidir:
kapi bir gün sessizce kaldirilirsa paket KIRMIZI olur.
"""

import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _gercek_yol(*parcalar):
    import brain.brain as bb
    return os.path.join(bb.BASE, *parcalar)


class TestAuditIzolasyonu:
    def test_audit_gecici_dosyaya_yazar(self):
        """Kapi acikken yazilan yer GERCEK gunluk olmamali."""
        import brain.brain as bb

        gercek = _gercek_yol("data", "audit", "audit.log")
        assert os.path.abspath(bb.AUDIT_DOSYASI) != os.path.abspath(gercek), (
            "testler gercek denetim gunlugune yaziyor — conftest kapisi kapali")

    def test_audit_gercek_dosyayi_degistirmez(self):
        import brain.brain as bb

        gercek = _gercek_yol("data", "audit", "audit.log")
        onceki = os.path.getsize(gercek) if os.path.exists(gercek) else 0
        bb._audit("izolasyon-bekcisi")
        simdi = os.path.getsize(gercek) if os.path.exists(gercek) else 0
        assert simdi == onceki, "gercek audit gunlugu test kosusunda buyudu"
        # Yazi gercekten gecici dosyaya gitmis olmali (bos yere gecmemis).
        with open(bb.AUDIT_DOSYASI, encoding="utf-8") as f:
            assert "izolasyon-bekcisi" in f.read()


class TestKotaSayaciIzolasyonu:
    def test_stats_gecici_db_kullanir(self):
        from brain import stats

        gercek = _gercek_yol("data", "model_stats.db")
        assert os.path.abspath(stats.model_stats_al()._db_yolu) != \
            os.path.abspath(gercek), (
            "testler gercek kota sayacina yaziyor — conftest kapisi kapali")

    def test_stats_gercek_db_yazmaz(self):
        from brain import stats

        gercek = _gercek_yol("data", "model_stats.db")
        stats.model_stats_al().kaydet("izolasyon-bekcisi", 0.01)
        if not os.path.exists(gercek):
            return
        conn = sqlite3.connect(gercek)
        try:
            n = conn.execute(
                "SELECT COUNT(*) FROM calls WHERE model=?",
                ("izolasyon-bekcisi",)).fetchone()[0]
        finally:
            conn.close()
        assert n == 0, "gercek kota sayacina test satiri yazildi"

    def test_gecici_db_satiri_gercekten_tutar(self):
        from brain import stats

        stats.model_stats_al().kaydet("izolasyon-bekcisi", 0.01)
        satirlar = stats.model_stats_al().sonucun(5)
        assert any(s["model"] == "izolasyon-bekcisi" for s in satirlar), (
            "kayit hicbir yere yazilmamis — kapi yazmayi da engellemis")


class TestGercekDosyalarYerinde:
    def test_gercek_veri_dosyalari_hala_yolunda(self):
        """Kapı, gercek dosyalarin KENDISINI silmemeli/kaldirmamali."""
        from brain.brain import BASE

        assert os.path.isdir(os.path.join(BASE, "data"))
        assert os.path.isdir(os.path.join(BASE, "data", "audit"))
