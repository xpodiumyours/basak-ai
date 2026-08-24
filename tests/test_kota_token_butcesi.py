"""tests/test_kota_token_butcesi.py — B3: Gerçek token bütçesi testleri.

Eski durum: Groq'un 200k token/gün limiti registry'de "80 istek" diye
tahmin edilmişti; gerçek usage hiç ölçülmüyordu.
Yeni: kart'ta gunluk_token varsa kota BUGÜNÜN gerçek token toplamına
bakar (stats.py'den); bütçe dolunca engellenir. Ölçüm hatası engel kurmaz.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from brain.kota import KotaYoneticisi
from brain.stats import ModelIstatistik

KART = {"ucretsiz": True, "gunluk_istek": 100, "gunluk_token": 500}


@pytest.fixture
def ortam(monkeypatch, tmp_path):
    istat = ModelIstatistik(db_yolu=str(tmp_path / "ist.db"))
    monkeypatch.setattr("brain.stats.model_stats_al", lambda: istat)
    kota = KotaYoneticisi(dosya=str(tmp_path / "durum.json"),
                          ucretli_engelli=True)
    return istat, kota


class TestTokenButcesi:
    def test_butce_altinda_engel_yok(self, ortam):
        istat, kota = ortam
        istat.kaydet("groq", 1.0, basarili=True, token_in=300,
                     token_out=150)
        assert kota.engel_nedeni("groq", KART) is None

    def test_butce_dolunca_engellenir(self, ortam):
        istat, kota = ortam
        istat.kaydet("groq", 1.0, basarili=True, token_in=300,
                     token_out=150)
        istat.kaydet("groq", 1.0, basarili=True, token_in=60, token_out=0)
        engel = kota.engel_nedeni("groq", KART)
        # 300+150+60 = 510 >= 500
        assert "token butcesi" in engel and "(510/500)" in engel

    def test_diger_saglayicinin_butcesi_etkilemez(self, ortam):
        istat, kota = ortam
        istat.kaydet("groq", 1.0, basarili=True, token_in=900,
                     token_out=100)
        kilo_kart = {"ucretsiz": True}
        assert kota.engel_nedeni("kilo", kilo_kart) is None

    def test_gunluk_token_olmayan_arac_istek_sayaciyla_surur(self, ortam):
        istat, kota = ortam
        istat.kaydet("glm", 1.0, basarili=True, token_in=999999)
        glm_kart = {"ucretsiz": True}   # gunluk_token tanimli degil
        assert kota.engel_nedeni("glm", glm_kart) is None

    def test_istek_limiti_bagimsiz_calisir(self, ortam):
        istat, kota = ortam
        kart = {"ucretsiz": True, "gunluk_istek": 2}   # token butcesi yok
        kota.harca("glm")
        kota.harca("glm")
        assert "istek limiti" in kota.engel_nedeni("glm", kart)

    def test_stats_cokerse_engel_kurulmaz(self, monkeypatch, tmp_path):
        """Olcum sohbeti bozmaz — hata halinde politika izin verir."""
        kota = KotaYoneticisi(dosya=str(tmp_path / "d.json"))

        def patlak():
            raise RuntimeError("db yok")
        monkeypatch.setattr("brain.stats.model_stats_al", patlak)
        assert kota.engel_nedeni("groq", KART) is None

    def test_registry_groq_kartinda_gercek_butce_var(self):
        from brain import registry
        kart = registry.kart("groq")
        assert kart["gunluk_token"] == 200000
