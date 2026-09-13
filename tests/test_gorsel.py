"""tests/test_gorsel.py — Gorsel uretme guvencesi.

Sozlesme: uc yerde bagli; adres sabit hosta gider (model adres
veremez); boyutlar kilitli; ag YOK (acici sahte).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import calistir, gorsel
from tools.definitions import TANINMIS_TOOLLAR


class SahteYanıt:
    headers = {"Content-Type": "image/jpeg"}

    def __init__(self, yakalayici):
        self._y = yakalayici

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self, n=-1):
        return b"\xff\xd8sahte"


class TestUcYer:
    def test_beyaz_listede(self):
        assert "gorsel_uret" in TANINMIS_TOOLLAR

    def test_durum_etiketi_var(self):
        from chat.tools import DURUM_METNI
        assert "gorsel_uret" in DURUM_METNI


class TestGorsel:
    def test_sabit_hosta_gider_dosyaya_yazar(self, tmp_path, monkeypatch):
        monkeypatch.setattr(gorsel, "URETILEN_KOK", str(tmp_path))
        yakalanan = {}

        def sahte_ac(istek, timeout=None):
            yakalanan["url"] = istek.full_url
            return SahteYanıt(yakalanan)

        r = gorsel.gorsel_uret("kedi", _acici=sahte_ac)
        assert "result" in r, r
        assert yakalanan["url"].startswith(
            "https://image.pollinations.ai/prompt/kedi?")
        assert os.path.exists(r["result"])
        assert open(r["result"], "rb").read() == b"\xff\xd8sahte"

    def test_boyut_kilidi_ve_bos_reddi(self, tmp_path, monkeypatch):
        monkeypatch.setattr(gorsel, "URETILEN_KOK", str(tmp_path))
        assert "error" in gorsel.gorsel_uret("   ")
        assert "error" in gorsel.gorsel_uret("x" * 501)
        assert "error" in gorsel.gorsel_uret("kedi", genislik="abc")

    def test_gorsel_degilse_reddedilir(self, tmp_path, monkeypatch):
        monkeypatch.setattr(gorsel, "URETILEN_KOK", str(tmp_path))

        class MetinYanıt(SahteYanıt):
            headers = {"Content-Type": "text/html"}

        r = gorsel.gorsel_uret(
            "kedi", _acici=lambda *a, **k: MetinYanıt(None))
        assert "error" in r

    def test_calistir_hatti(self):
        r = calistir("gorsel_uret", {"aciklama": ""})
        assert "error" in r
