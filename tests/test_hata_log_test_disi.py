"""tests/test_hata_log_test_disi.py — test gurultusu hata.log'a gitmez.

Denetim bulgusu (2026-10-01): hata.log 36.016 satirdi; agirligi test
kosusundan geliyordu — basak_app import edildiginde basicConfig
RotatingFileHandler'i kurdugundan TUM test kayitlari teshis dosyasina
dusuyordu. Sayim: ~15.5k "testte stream yok" + ~13.5k httpx2 "HTTP
Request" satiri.

Kilitler:
1. conftest testten ONCE bayragi kurar (bu test onu dogrular),
2. basak_app kaynaginda bayrak kontrolu VAR (kaynak kilidi),
3. bayrak verildiginde dosya handler kurulmaz (kaynak kilidi).
"""

import os
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))


def test_conftest_bayragi_kurulmus():
    """Bu testin calisabilmesi conftest'in yuklendiginin kanitidir."""
    assert os.environ.get("BASAK_TEST_KOSUSU") == "1"


def test_basak_app_bayragi_okuyor_ve_dosya_handleri_bagli():
    kaynak = (KOK / "basak_app.py").read_text(encoding="utf-8")
    assert 'os.environ.get("BASAK_TEST_KOSUSU")' in kaynak
    assert "RotatingFileHandler(" in kaynak


def test_conftest_bayragi_yaziyor():
    kaynak = (KOK / "tests" / "conftest.py").read_text(encoding="utf-8")
    assert 'os.environ["BASAK_TEST_KOSUSU"] = "1"' in kaynak
