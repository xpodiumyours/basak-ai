"""tests/test_dinamik_araclar.py — Bağlam diyeti Adım 1 testleri.

Eski davranis: tek anahtar kelime 18 aracin TAM kilavuzunu aciyordu
(~3.000 token her istekte). Yeni kural: soru yalniz ilgili arac ailesinin
kilavuzunu acar; olcum uclusu (git_durum/belge_ara/dosya_bilgi) HER ZAMAN
aciktir (O-1 kurali).
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
    def test_sohbet_sorusu_yalniz_olcum_uclusu(self):
        assert adlar("Bugun kendini nasil hissediyorsun?") == set(_OLCUM_TOOLLARI)

    def test_hava_sorusu_arama_ailesini_acar(self):
        sonuc = adlar("Istanbulda hava nasil?")
        assert {"web_search", "sayfa_oku"} <= sonuc
        assert "add_task" not in sonuc and "save_note" not in sonuc

    def test_gorev_ekleme_yalniz_gorev_ailesi(self):
        sonuc = adlar("Yarin odevimi bitirmem lazim.")
        assert "add_task" in sonuc
        assert "web_search" not in sonuc and "write_file_tool" not in sonuc

    def test_hatirla_defter_ikilisini_acar(self):
        sonuc = adlar("Bunu hatırla: çay markam Çaykur.")
        assert {"save_note", "deftere_kaydet"} <= sonuc

    def test_dosya_kelimesi_dosya_ailesini_acar(self):
        sonuc = adlar("Su dosyanin icine bak.")
        assert {"read_file", "write_file_tool", "list_files"} <= sonuc

    def test_video_ve_fotograf_tetikleyicileri(self):
        assert "video_analyze" in adlar("Bu videonun transkriptini cikar.")
        assert "image_analyze" in adlar("Bu fotografi acikla.")

    def test_verilmeyen_arac_sessizce_elinir(self):
        """Aile tetiklendi ama o turda sunulmadiysa liste daralir — hata yok."""
        az = [_schema("git_durum"), _schema("add_task")]
        sonuc = _dinamik_araclar("bunu hatirla".lower(), az)
        assert [t["function"]["name"] for t in sonuc] == ["git_durum"]

    def test_olcum_uclusu_her_kosulda_acik(self):
        for metin in ("merhaba", "hava nasil", "gorevlerim ne",
                      "VixRex'te durum ne"):
            assert set(_OLCUM_TOOLLARI) <= adlar(metin), metin

    def test_bosluk_listesi_none_kalir(self):
        assert _dinamik_araclar("hava", []) == []
