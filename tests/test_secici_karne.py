"""tests/test_secici_karne.py — performans karnesi semantik router değildir.

Başak ölçüm tutabilir ama geçmiş başarı yüzdesi modelin görevdeki zekâsını
yargılayıp sağlayıcı sırasını değiştiremez. Yalnız gerçek teknik cooldown
sırayı geçici olarak değiştirebilir.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain import registry, secici

MEVCUTLAR = ["nvidia", "glm", "groq", "kilo"]


def _beklenen():
    return [a for a in registry.VARSAYILAN_SIRA if a in MEVCUTLAR]


class TestKarneSemantikDegil:
    def test_karne_bayragi_sirayi_degistirmez(self):
        kapali, _ = secici.sec(mevcutlar=MEVCUTLAR, karne_kullan=False)
        acik, gerekce = secici.sec(mevcutlar=MEVCUTLAR, karne_kullan=True)
        assert kapali == acik == _beklenen()
        assert "karne" not in gerekce

    def test_gorev_tipi_sirayi_degistirmez(self):
        for tip in ("kod", "arastirma", "hiz", "genel"):
            sirali, _ = secici.sec(
                gorev_tipi=tip, mevcutlar=MEVCUTLAR, karne_kullan=True)
            assert sirali == _beklenen()

    def test_kullanici_metni_sirayi_degistirmez(self):
        for metin in ("kod yaz", "müşteri araştır", "hızlı ol", "selam"):
            sirali, _ = secici.sec(
                text=metin, mevcutlar=MEVCUTLAR, karne_kullan=True)
            assert sirali == _beklenen()

    def test_cooldown_teknik_istisnadir(self):
        sirali, gerekce = secici.sec(
            mevcutlar=MEVCUTLAR,
            cooldown={"glm": time.time() + 30},
            karne_kullan=True,
        )
        assert sirali[-1] == "glm"
        assert "cooldown" in gerekce
