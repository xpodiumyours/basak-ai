"""tests/test_adres_kontrol.py — ARAC-PLANI Is 7: canli adres kontrolu.

Sozlesme:
- adres_kontrol uc yerde bagli (sema + calistir + DURUM_METNI).
- Govde indirilmez (HEAD, olmazsa kisa GET).
- SSRF: ic ag / localhost / ozel port REDDEDILIR, ag acilmaz.
- Ag YOK — urllib katmani sahte.
"""

import io
import os
import sys
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import calistir, web_search as ws
from tools.definitions import TANINMIS_TOOLLAR


class SahteYanıt:
    def __init__(self, durum=200, adres="https://ornek.test/son"):
        self.status = durum
        self._adres = adres

    def geturl(self):
        return self._adres

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class SahteOpener:
    def __init__(self, davranis):
        self.davranis = davranis
        self.istekler = []

    def open(self, req, timeout=None):
        self.istekler.append(req)
        return self.davranis(req)


class TestUcYer:
    def test_beyaz_listede(self):
        assert "adres_kontrol" in TANINMIS_TOOLLAR

    def test_durum_etiketi_var(self):
        from chat.tools import DURUM_METNI
        assert "adres_kontrol" in DURUM_METNI


class TestKontrol:
    def test_head_basarii(self, monkeypatch):
        monkeypatch.setattr(ws, "_engelli_ip_nedeni", lambda h: None)
        acici = SahteOpener(lambda req: SahteYanıt(200, "https://ornek.test/"))
        monkeypatch.setattr(ws.urllib.request, "build_opener",
                            lambda *a: acici)
        r = ws.adres_kontrol("https://ornek.test/")
        assert "result" in r, r
        assert "durum: 200" in r["result"]
        assert "sn" in r["result"] and "adres:" in r["result"]
        assert acici.istekler[0].get_method() == "HEAD"

    def test_head_yoksa_get(self, monkeypatch):
        monkeypatch.setattr(ws, "_engelli_ip_nedeni", lambda h: None)

        def davranis(req):
            if req.get_method() == "HEAD":
                raise urllib.error.HTTPError(
                    req.full_url, 405, "Method Not Allowed", {}, None)
            return SahteYanıt(200, req.full_url)
        acici = SahteOpener(davranis)
        monkeypatch.setattr(ws.urllib.request, "build_opener",
                            lambda *a: acici)
        r = ws.adres_kontrol("https://ornek.test/sayfa")
        assert "result" in r and "durum: 200" in r["result"]
        assert [q.get_method() for q in acici.istekler] == ["HEAD", "GET"]

    def test_govde_okunmaz(self, monkeypatch):
        monkeypatch.setattr(ws, "_engelli_ip_nedeni", lambda h: None)
        okunan = []

        class OkuyanYanıt(SahteYanıt):
            def read(self, *a, **k):
                okunan.append(True)
                return b"x"

        acici = SahteOpener(lambda req: OkuyanYanıt())
        monkeypatch.setattr(ws.urllib.request, "build_opener",
                            lambda *a: acici)
        ws.adres_kontrol("https://ornek.test/")
        assert okunan == []

    def test_ssrf_reddedilir_ag_acilmaz(self, monkeypatch):
        acildi = []
        monkeypatch.setattr(ws.urllib.request, "build_opener",
                            lambda *a: (_ for _ in ()).throw(
                                AssertionError("ag acilmamali")))
        for kotu in ("http://localhost:8000/", "http://127.0.0.1/",
                     "http://192.168.1.1/", "ftp://ornek.test/",
                     "https://ornek.test:8080/"):
            r = ws.adres_kontrol(kotu)
            assert "error" in r, kotu

    def test_bos_url(self):
        assert "error" in ws.adres_kontrol("  ")

    def test_calistir_hatti_reddi(self):
        r = calistir("adres_kontrol", {"url": "http://localhost/"})
        assert "error" in r
