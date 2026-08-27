"""tests/test_dinamik_araclar.py — Fren sokumu: tum araclar her zaman acik.

Eski baglam diyeti kaldirildi; _dinamik_araclar artik filtrelemez.
Testler yeni agen modunu dogrular.
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
    def test_sohbet_sorusu_tum_araclari_acar(self):
        assert adlar("Bugun kendini nasil hissediyorsun?") == {t["function"]["name"] for t in TUMU}

    def test_hava_sorusu_tum_araclari_acar(self):
        assert adlar("Istanbulda hava nasil?") == {t["function"]["name"] for t in TUMU}

    def test_gorev_ekleme_tum_araclari_acar(self):
        assert adlar("Yarin odevimi bitirmem lazim.") == {t["function"]["name"] for t in TUMU}

    def test_hatirla_tum_araclari_acar(self):
        assert adlar("Bunu hatırla: çay markam Çaykur.") == {t["function"]["name"] for t in TUMU}

    def test_dosya_kelimesi_tum_araclari_acar(self):
        assert adlar("Su dosyanin icine bak.") == {t["function"]["name"] for t in TUMU}

    def test_video_ve_fotograf_tum_araclari_acar(self):
        assert adlar("Bu videonun transkriptini cikar.") == {t["function"]["name"] for t in TUMU}
        assert adlar("Bu fotografi acikla.") == {t["function"]["name"] for t in TUMU}

    def test_verilmeyen_arac_bos_kalir(self):
        az = [_schema("git_durum"), _schema("add_task")]
        sonuc = _dinamik_araclar("bunu hatirla".lower(), az)
        assert set(t["function"]["name"] for t in sonuc) == {"git_durum", "add_task"}

    def test_olcum_uclusu_dahil_tum_araclar_acik(self):
        for metin in ("merhaba", "hava nasil", "gorevlerim ne", "VixRex'te durum ne"):
            assert {t["function"]["name"] for t in TUMU} == adlar(metin)

    def test_bosluk_listesi_none_kalir(self):
        assert _dinamik_araclar("hava", []) == []


class TestDosyaSinyali:
    """Fren sokumu: tum araclar her zaman acik — dosya sinyali ayrimi yok."""

    def test_windows_yolu_tum_araclari_acar(self):
        assert {t["function"]["name"] for t in _dinamik_araclar(r"c:\users\casper\source\numeramatch".lower(), TUMU)} == {t["function"]["name"] for t in TUMU}

    def test_dis_proje_adi_tum_araclari_acar(self):
        assert {t["function"]["name"] for t in _dinamik_araclar("numeramatch projesine bak", TUMU)} == {t["function"]["name"] for t in TUMU}

    def test_proje_kelimesi_tum_araclari_acar(self):
        assert {t["function"]["name"] for t in _dinamik_araclar("proje geliştirmek için", TUMU)} == {t["function"]["name"] for t in TUMU}

    def test_sade_sohbet_tum_araclari_acar(self):
        assert {t["function"]["name"] for t in _dinamik_araclar("bugün hava nasıl", TUMU)} == {t["function"]["name"] for t in TUMU}
