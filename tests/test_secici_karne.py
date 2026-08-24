"""tests/test_secici_karne.py — B1: Seçicinin karne katmanı testleri.

Kilitli hedefin ilk halkası: secici artık deneyimi okuyor.
Politika (bilinçli dar): yeterli örneklem (>=5) olan ve başarı oranı
%50 altına düşen sağlayıcı SONA alınır; terfi yok (sonraki dilim).
Karne kapalıysa davranış eskisi gibi — mevcut akış bozulmaz.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from brain import secici
from brain.stats import ModelIstatistik

MEVCUTLAR = ["nvidia", "glm", "groq", "kilo"]


@pytest.fixture
def istat(monkeypatch, tmp_path):
    """Secicinin okudugu istatistigi izole DB'ye baglar."""
    istat = ModelIstatistik(db_yolu=str(tmp_path / "karne.db"))
    monkeypatch.setattr("brain.stats.model_stats_al", lambda: istat)
    return istat


def _doldur(istat, model, basarili, basarisiz):
    for _ in range(basarili):
        istat.kaydet(model, 1.0, basarili=True)
    for _ in range(basarisiz):
        istat.kaydet(model, 1.0, basarili=False)


class TestKarneKatmani:
    def test_kapaliyken_davranis_eski_gibi(self, istat):
        _doldur(istat, "nvidia", 0, 8)   # kotu karnesine ragmen
        sirali, gerekce = secici.sec(gorev_tipi="kod",
                                     mevcutlar=MEVCUTLAR)
        assert sirali[0] == "nvidia"     # kurallar aynen isler
        assert "karne" not in gerekce

    def test_zayif_saglayici_sona_alinir(self, istat):
        _doldur(istat, "nvidia", 2, 6)   # %25 — esik alti
        sirali, gerekce = secici.sec(gorev_tipi="kod",
                                     mevcutlar=MEVCUTLAR,
                                     karne_kullan=True)
        # nvidia tercih listesindeydi ama karne onu sona atti
        assert sirali[-1] == "nvidia"
        assert sirali[0] == "glm"
        assert "karne" in gerekce and "%25.0" in gerekce

    def test_saglam_karne_sirayi_degistirmez(self, istat):
        _doldur(istat, "nvidia", 7, 1)   # %87.5
        sirali, gerekce = secici.sec(gorev_tipi="kod",
                                     mevcutlar=MEVCUTLAR,
                                     karne_kullan=True)
        assert sirali[0] == "nvidia"
        assert "karne" not in gerekce

    def test_az_ornekleme_sesi_cikarmaz(self, istat):
        _doldur(istat, "nvidia", 0, 3)   # 3 cagri < 5 orneklem
        sirali, gerekce = secici.sec(gorev_tipi="kod",
                                     mevcutlar=MEVCUTLAR,
                                     karne_kullan=True)
        assert sirali[0] == "nvidia"
        assert "karne" not in gerekce

    def test_stats_hatasi_sessiz_gecer(self, monkeypatch, istat):
        def patlak():
            raise RuntimeError("db yok")
        monkeypatch.setattr("brain.stats.model_stats_al", patlak)
        sirali, gerekce = secici.sec(gorev_tipi="kod",
                                     mevcutlar=MEVCUTLAR,
                                     karne_kullan=True)
        assert sirali[0] == "nvidia" and "karne" not in gerekce

    def test_birden_fazla_zayif_sonunca_sira_korunur(self, istat):
        _doldur(istat, "nvidia", 0, 8)
        _doldur(istat, "groq", 0, 8)
        sirali, gerekce = secici.sec(gorev_tipi="kod",
                                     mevcutlar=MEVCUTLAR,
                                     karne_kullan=True)
        # zayiflar kendi gorev-turu sirasini koruyarak sona gider:
        # nvidia once groq sonra
        assert sirali[-2:] == ["nvidia", "groq"]
        assert sirali[0] == "glm"
