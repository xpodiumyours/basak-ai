"""tests/test_github_durum.py — ARAC-PLANI Is 5: GitHub salt-okunur.

Sozlesme:
- github_durum uc yerde bagli (sema + calistir + DURUM_METNI).
- Depo adi modelden gelmez (sabit tablo); bilinmeyen proje reddedilir.
- Calisan komutlar YALNIZ pr list / pr view / run list; shell acilmaz.
- Ag YOK — kosucu sahte (runner enjeksiyonu).
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import github
from tools.definitions import TANINMIS_TOOLLAR

YASAK = ("merge", "create", "close", "delete", "push", "reopen")


class SahteKosucu:
    def __init__(self, cikti="[]"):
        self.argvler = []
        self.kwargs = []
        self.cikti = cikti

    def __call__(self, argv, **kwargs):
        self.argvler.append(list(argv))
        self.kwargs.append(kwargs)
        class R:
            returncode = 0
            stdout = self.cikti
            stderr = ""
        r = R()
        r.stdout = self.cikti
        return r


class TestUcYer:
    def test_beyaz_listede(self):
        assert "github_durum" in TANINMIS_TOOLLAR

    def test_durum_etiketi_var(self):
        from chat.tools import DURUM_METNI
        assert "github_durum" in DURUM_METNI


class TestSabitKomut:
    def test_pr_liste_argv(self):
        k = SahteKosucu('[{"number": 3}]')
        r = github.github_durum("pr_liste", "basak", runner=k)
        assert r == {"result": [{"number": 3}]}
        assert k.argvler[0][:4] == ["gh", "pr", "list", "--repo"]
        assert "xpodiumyours/basak-ai" in k.argvler[0]
        assert k.kwargs[0].get("shell") is False

    def test_pr_goruntule_argv(self):
        k = SahteKosucu('{"number": 3}')
        r = github.github_durum("pr_goruntule", "vixrex", no=3, runner=k)
        assert k.argvler[0][1:3] == ["pr", "view"]
        assert "xpodiumyours/vixrex" in k.argvler[0]
        assert r == {"result": {"number": 3}}

    def test_calisma_liste_argv(self):
        k = SahteKosucu()
        github.github_durum("calisma_liste", "xses", runner=k)
        assert k.argvler[0][1:3] == ["run", "list"]
        assert "xpodiumyours/xses" in k.argvler[0]

    def test_yazan_komut_yok(self):
        import inspect
        kaynak = inspect.getsource(github)
        for w in YASAK:
            assert '"%s"' % w not in kaynak and "'%s'" % w not in kaynak, w

    def test_bilinmeyen_proje_reddedilir(self):
        k = SahteKosucu()
        r = github.github_durum("pr_liste", "xpodiumyours/basak-ai", runner=k)
        assert "error" in r
        assert k.argvler == []  # gh HIC cagrilmadi

    def test_pr_no_sayi_olmali(self):
        k = SahteKosucu()
        assert "error" in github.github_durum(
            "pr_goruntule", "basak", no="abc", runner=k)
        assert k.argvler == []

    def test_gecersiz_islem_ve_durum(self):
        k = SahteKosucu()
        assert "error" in github.github_durum("merge", "basak", runner=k)
        assert "error" in github.github_durum(
            "pr_liste", "basak", durum="yarim", runner=k)
        assert k.argvler == []

    def test_gh_hatasi_tasinir(self):
        class Bozuk:
            def __call__(self, argv, **kwargs):
                class R:
                    returncode = 1
                    stdout = ""
                    stderr = "Not Found"
                return R()
        r = github.github_durum("pr_liste", "basak", runner=Bozuk())
        assert "error" in r

    def test_calistir_hatti(self):
        from tools import calistir
        r = calistir("github_durum", {"islem": "bogus", "proje": "basak"})
        assert "error" in r
