"""tests/test_secici_karne.py — ozgur-ajan: secici passthrough testleri.

2026-09-13 Faz 1: karne/token/shuffle siralama artiklari silindi.
Secici registry sirasini korur; karne/cooldown/tools siralamayi degistirmez.
Atlama (cooldown/429) brain/brain.py'de yapilir.
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
        _doldur(istat, "nvidia", 0, 8)   # kotu karneye ragmen sira degismez
        sirali, gerekce = secici.sec(gorev_tipi="kod",
                                     mevcutlar=MEVCUTLAR)
        assert sirali[0] == "glm"        # registry sirasi korunur
        assert "karne" not in gerekce

    def test_zayif_saglayici_sona_alinmaz(self, istat):
        # Faz 1: karne siralamayi degistirmez (passthrough)
        _doldur(istat, "nvidia", 2, 6)   # %25 — esik alti olsa da
        sirali, gerekce = secici.sec(gorev_tipi="kod",
                                     mevcutlar=MEVCUTLAR,
                                     karne_kullan=True)
        assert sirali == ["glm", "groq", "nvidia", "kilo"]
        assert "karne" not in gerekce

    def test_saglam_karne_sirayi_degistirmez(self, istat):
        _doldur(istat, "nvidia", 7, 1)   # %87.5
        sirali, gerekce = secici.sec(gorev_tipi="kod",
                                     mevcutlar=MEVCUTLAR,
                                     karne_kullan=True)
        assert sirali[0] == "glm"        # glm once, nvidia yakininda
        assert "karne" not in gerekce

    def test_az_ornekleme_sesi_cikarmaz(self, istat):
        _doldur(istat, "nvidia", 0, 3)   # 3 cagri < 5 orneklem
        sirali, gerekce = secici.sec(gorev_tipi="kod",
                                     mevcutlar=MEVCUTLAR,
                                     karne_kullan=True)
        assert sirali[0] == "glm"
        assert "karne" not in gerekce

    def test_stats_hatasi_sessiz_gecer(self, monkeypatch, istat):
        def patlak():
            raise RuntimeError("db yok")
        monkeypatch.setattr("brain.stats.model_stats_al", patlak)
        sirali, gerekce = secici.sec(gorev_tipi="kod",
                                     mevcutlar=MEVCUTLAR,
                                     karne_kullan=True)
        assert sirali[0] == "glm" and "karne" not in gerekce

    def test_birden_fazla_zayif_sonunca_sira_korunur(self, istat):
        _doldur(istat, "nvidia", 0, 8)
        _doldur(istat, "groq", 0, 8)
        sirali, gerekce = secici.sec(gorev_tipi="kod",
                                     mevcutlar=MEVCUTLAR,
                                     karne_kullan=True)
        # Faz 1: zayiflar da sona gitmez, registry sirasi korunur
        assert sirali[0] == "glm"
        assert "karne" not in gerekce

    def test_tools_ve_cooldown_sirayi_degistirmez(self, istat):
        sirali, _ = secici.sec(gorev_tipi="kod", mevcutlar=MEVCUTLAR,
                               tools=True, cooldown={"glm": 9999999999})
        assert sirali[0] == "glm"
