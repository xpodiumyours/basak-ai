"""tests/test_secici_karne.py — teknik sağlayıcı sırası regresyonu.

Secici kullanıcı metni, görev türü, karne, araç veya cooldown bilgisi almaz.
Yalnız registry sırasını korur; teknik atlama Brain katmanında yapılır.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain import secici
from brain import registry

MEVCUTLAR = ["nvidia", "glm", "groq", "kilo"]


def _beklenen(mevcutlar=None):
    mevcutlar = list(MEVCUTLAR if mevcutlar is None else mevcutlar)
    temel = [a for a in registry.VARSAYILAN_SIRA if a in mevcutlar]
    ekstra = [a for a in mevcutlar if a not in registry.VARSAYILAN_SIRA]
    return temel + ekstra


def test_secici_yalniz_registry_sirasini_korur():
    sirali, gerekce = secici.sec(mevcutlar=MEVCUTLAR)
    assert sirali == _beklenen()
    assert gerekce == "teknik registry sirasi"


def test_bilinmeyen_saglayici_sona_eklenir():
    sirali, _ = secici.sec(mevcutlar=["ozel", "glm", "nvidia"])
    assert sirali[:-1] == _beklenen(["glm", "nvidia"])
    assert sirali[-1] == "ozel"


def test_secici_imzasi_gizli_karar_parametresi_tasimaz():
    import inspect
    params = inspect.signature(secici.sec).parameters
    assert tuple(params) == ("mevcutlar",)
