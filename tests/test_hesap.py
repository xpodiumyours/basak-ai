"""tests/test_hesap.py — Saat + guvenli aritmetik guvencesi.

Sozlesme: uc yerde bagli; eval() yok; kotu girdi hesaplanmaz,
kod calismaz.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import calistir, hesap
from tools.definitions import TANINMIS_TOOLLAR


class TestUcYer:
    def test_beyaz_listede(self):
        assert "simdi" in TANINMIS_TOOLLAR
        assert "hesapla" in TANINMIS_TOOLLAR

    def test_durum_etiketleri_var(self):
        from chat.tools import DURUM_METNI
        assert "simdi" in DURUM_METNI
        assert "hesapla" in DURUM_METNI


class TestSimdi:
    def test_bicim(self):
        r = hesap.simdi()
        assert "result" in r and ":" in r["result"]


class TestHesapla:
    def test_dort_islem(self):
        assert hesap.hesapla("2+3*4") == {"result": "14"}
        assert hesap.hesapla("(120*18)/100") == {"result": "21.6"}
        assert hesap.hesapla("-5 + 2**3") == {"result": "3"}

    def test_reddedilenler(self):
        assert "error" in hesap.hesapla("")
        assert "error" in hesap.hesapla("1/0")
        for kotu in ("__import__('os')", "open('x')", "a+b", "2+",
                     "print(1)", "[1,2]", "x" * 201):
            assert "error" in hesap.hesapla(kotu), kotu

    def test_calistir_hatti(self):
        assert calistir("hesapla", {"ifade": "6*7"}) == {"result": "42"}
        assert "error" in calistir("hesapla", {"ifade": "kotu("})
        assert "result" in calistir("simdi", {})
