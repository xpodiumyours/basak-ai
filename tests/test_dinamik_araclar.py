"""tests/test_dinamik_araclar.py — Araç sunumu testleri.

2026-08-25: GOREV-asistan-kurgusu — 18 arac her turda modele verilir,
eleme yapilmaz. Izin katmani (permissions.py) ayri calisir.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chat import _OLCUM_TOOLLARI, _dinamik_araclar


def _schema(ad):
    return {"type": "function",
            "function": {"name": ad, "description": "",
                         "parameters": {"type": "object", "properties": {}}}}


TUMU = [_schema(a) for a in (
    "web_search", "sayfa_oku", "add_task", "list_tasks", "complete_task",
    "save_note", "deftere_kaydet", "read_file", "write_file_tool",
    "list_files", "ac_uygulama", "get_reminders", "video_analyze",
    "image_analyze", "model_stats", "git_durum", "belge_ara", "dosya_bilgi",
)]


def adlar(text):
    return {t["function"]["name"] for t in _dinamik_araclar(text.lower(), TUMU)}


class TestDinamikSunum:
    def test_18_arac_her_cumlede_donuyor(self):
        """Her turda 18 aracin tamami modele verilir."""
        for metin in ("merhaba", "hava nasil", "gorevlerim ne",
                      "bu sayfayi ozetle https://ornek.com",
                      "musteriye mail yaz"):
            sonuc = _dinamik_araclar(metin.lower(), TUMU)
            assert len(sonuc) == 18, f'{metin} icin {len(sonuc)} arac dondu'

    def test_bosluk_listesi_none_kalir(self):
        assert _dinamik_araclar("hava", []) == []


class TestDosyaSinyali:
    """2026-08-25: 18 arac her zaman doner; yazma izni permissions.py'de korunur."""

    def tumu_mu(self, metin):
        return len(_dinamik_araclar(metin.lower(), TUMU)) == 18

    def test_windows_yolu_18_arac_donuyor(self):
        assert self.tumu_mu(r"c:\users\casper\source\numeramatch")

    def test_dis_proje_adi_18_arac_donuyor(self):
        assert self.tumu_mu("numeramatch projesine bak")

    def test_proje_kelimesi_18_arac_donuyor(self):
        assert self.tumu_mu("proje gelistirmek icin")

    def test_sade_sohbet_18_arac_donuyor(self):
        assert self.tumu_mu("bugun hava nasil")
