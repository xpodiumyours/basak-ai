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
from brain import registry
from brain.stats import ModelIstatistik

MEVCUTLAR = ["nvidia", "glm", "groq", "kilo"]


def _beklenen(mevcutlar=None):
    """Registry sirasina gore beklenen siralama (bilinmeyen adlar sona).

    Bu testler eskiden `sirali[0] == "glm"` diye SABIT yaziyordu.
    Saglayici sirasi 2026-09-19'da olcumle degisince (groq one alindi:
    glm her istekte zaman asimina ugruyordu) yedi test birden kirildi —
    oysa katmanlarin davranisi degismemisti. Beklenti artik registry'den
    TURETILIR: olculen sey "kim onde" degil, "katman sirayi BOZMUYOR"
    olgusudur. Boylece niyet korunur, sira guncellendiginde test
    kirilmaz — ve beklenmedik bir yeniden siralama yine yakalanir.
    """
    mevcutlar = list(MEVCUTLAR if mevcutlar is None else mevcutlar)
    temel = [a for a in registry.VARSAYILAN_SIRA if a in mevcutlar]
    ekstra = [a for a in mevcutlar if a not in registry.VARSAYILAN_SIRA]
    return temel + ekstra


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
        assert sirali == _beklenen()     # registry sirasi korunur
        assert "karne" not in gerekce

    def test_zayif_saglayici_sona_alinmaz(self, istat):
        # Faz 1: karne siralamayi degistirmez (passthrough)
        _doldur(istat, "nvidia", 2, 6)   # %25 — esik alti olsa da
        sirali, gerekce = secici.sec(gorev_tipi="kod",
                                     mevcutlar=MEVCUTLAR,
                                     karne_kullan=True)
        assert sirali == _beklenen()
        assert "karne" not in gerekce

    def test_saglam_karne_sirayi_degistirmez(self, istat):
        _doldur(istat, "nvidia", 7, 1)   # %87.5
        sirali, gerekce = secici.sec(gorev_tipi="kod",
                                     mevcutlar=MEVCUTLAR,
                                     karne_kullan=True)
        assert sirali == _beklenen()     # nvidia karneye ragmen yerinde
        assert "karne" not in gerekce

    def test_az_ornekleme_sesi_cikarmaz(self, istat):
        _doldur(istat, "nvidia", 0, 3)   # 3 cagri < 5 orneklem
        sirali, gerekce = secici.sec(gorev_tipi="kod",
                                     mevcutlar=MEVCUTLAR,
                                     karne_kullan=True)
        assert sirali == _beklenen()
        assert "karne" not in gerekce

    def test_stats_hatasi_sessiz_gecer(self, monkeypatch, istat):
        def patlak():
            raise RuntimeError("db yok")
        monkeypatch.setattr("brain.stats.model_stats_al", patlak)
        sirali, gerekce = secici.sec(gorev_tipi="kod",
                                     mevcutlar=MEVCUTLAR,
                                     karne_kullan=True)
        assert sirali == _beklenen() and "karne" not in gerekce

    def test_birden_fazla_zayif_sonunca_sira_korunur(self, istat):
        _doldur(istat, "nvidia", 0, 8)
        _doldur(istat, "groq", 0, 8)
        sirali, gerekce = secici.sec(gorev_tipi="kod",
                                     mevcutlar=MEVCUTLAR,
                                     karne_kullan=True)
        # Faz 1: zayiflar da sona gitmez, registry sirasi korunur
        assert sirali == _beklenen()
        assert "karne" not in gerekce

    def test_tools_ve_cooldown_sirayi_degistirmez(self, istat):
        sirali, _ = secici.sec(gorev_tipi="kod", mevcutlar=MEVCUTLAR,
                               tools=True, cooldown={"glm": 9999999999})
        assert sirali == _beklenen()
