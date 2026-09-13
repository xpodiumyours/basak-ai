"""tests/test_testleri_kos.py — ARAC-PLANI Is 8: test kosturma.

Sozlesme:
- testleri_kos uc yerde bagli (sema + calistir + DURUM_METNI).
- Komut modelden gelmez (sabit tablo); shell acilmaz; cwd proje koku.
- vixrex tabloda YOK (islem yasagi) — "tanimli degil" doner.
- Kosucu sahte (runner enjeksiyonu); gercek suite burada kosmaz.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import calistir, testkos
from tools.definitions import TANINMIS_TOOLLAR


class SahteKosucu:
    def __init__(self, kod=0, cikti="OK"):
        self.kod = kod
        self.cikti = cikti
        self.argvler = []
        self.kwargs = []

    def __call__(self, argv, **kwargs):
        self.argvler.append(list(argv))
        self.kwargs.append(kwargs)

        class R:
            pass
        r = R()
        r.returncode = self.kod
        r.stdout = self.cikti
        r.stderr = ""
        return r


class TestUcYer:
    def test_beyaz_listede(self):
        assert "testleri_kos" in TANINMIS_TOOLLAR

    def test_durum_etiketi_var(self):
        from chat.tools import DURUM_METNI
        assert "testleri_kos" in DURUM_METNI


class TestSabitTablo:
    def test_basak_komutu_sabit(self):
        k = SahteKosucu()
        r = testkos.testleri_kos("basak", runner=k)
        assert "result" in r and "gecti" in r["result"]
        argv = k.argvler[0]
        assert argv[1:4] == ["-m", "pytest", "tests"]
        assert k.kwargs[0].get("shell") is False
        assert k.kwargs[0]["cwd"] == testkos.BASE

    def test_model_komut_veremez(self):
        import inspect
        kaynak = inspect.getsource(testkos.testleri_kos)
        assert "args.get" not in kaynak  # komut/dis yol modelden gelmez

    def test_kalan_ozet_kesilir(self):
        k = SahteKosucu(kod=1, cikti="x" * 5000)
        r = testkos.testleri_kos("xses", runner=k)
        assert "KALDI" in r["result"]
        assert len(r["result"]) < 3000

    def test_vixrex_tanimsiz(self):
        assert "vixrex" not in testkos.TEST_KOMUTLARI
        r = testkos.testleri_kos("vixrex")
        assert "error" in r and "tanimli degil" in r["error"]

    def test_bilinmeyen_proje(self):
        r = testkos.testleri_kos("yok-boyle-proje")
        assert "error" in r

    def test_calistir_hatti(self):
        r = calistir("testleri_kos", {"proje": "vixrex"})
        assert "error" in r
