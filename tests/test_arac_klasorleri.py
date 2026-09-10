"""tests/test_arac_klasorleri.py — Araclara gercek klasorler gider.

2026-09-10 bulgusu (Casper suphesi dogru cikti): canli iki yolda da
tool_calling_multi knowledge_dir/gorevler_file BOS cagriliyordu.
Sonuc: gorev ekleme cokuyor (.tmp curufu birakiyordu), listeleme
"yok" diyordu, not kaydi patliyordu. Salt-okunur araclar sans eseri
calisiyordu (cwd). Bu test baglantiyi kilitler.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chat  # once tam paket (dairesel import onlemi)
import _chat_legacy as L


class TestKlasorTasima:
    def test_multi_klasorleri_calistirir(self):
        from chat.tools import tool_calling_multi
        yakalanan = {}

        def sahte(ad, args, knowledge_dir="", gorevler_file=""):
            yakalanan["kd"] = knowledge_dir
            yakalanan["gf"] = gorevler_file
            return {"result": "tamam"}

        class SahteBeyin:
            def _bulut_zinciri(self):
                return []

            def cevapla(self, messages, model, tools=None):
                return {"content": "ozet"}, "sahte"

        calls = [{"id": "c1", "type": "function",
                  "function": {"name": "list_tasks", "arguments": "{}"}}]
        tool_calling_multi(calls, [], SahteBeyin(), None, lambda c: None,
                           sahte, None,
                           knowledge_dir="BILGI", gorevler_file="GOREV")
        assert yakalanan["kd"] == "BILGI"
        assert yakalanan["gf"] == "GOREV"

    def test_deney_gercek_dosyalara_bakar(self, monkeypatch):
        monkeypatch.setattr(L, "_hafiza", False)

        class SahteBeyin:
            def yerel_modeller(self):
                return []

            def bulut_musait(self):
                return True

            def _bulut_zinciri(self):
                return []

            def cevapla(self, messages, model, tools=None):
                return {"content": "ozet"}, "sahte"

        bilesenler = L.orkestra_bilesenleri(SahteBeyin())
        calls = [{"id": "c1", "type": "function",
                  "function": {"name": "list_tasks", "arguments": "{}"}}]
        cevap, olc = bilesenler["deney_kos"](calls, [])
        # Gercek gorevler.json okunur: bos degilse "tamamlanmis" ya da
        # acik gorev satiri doner; asla "Henüz görev yok" yalanı olmaz.
        assert "Henüz görev yok" not in cevap


class TestBosYolKorumasi:
    def test_gorev_bos_yolda_acik_hata(self):
        from tools.tasks import add_task, list_tasks, complete_task
        assert "error" in add_task("deneme", "")
        assert "error" in list_tasks("")
        assert "error" in complete_task(1, "")

    def test_not_bos_klasorde_acik_hata(self):
        from tools.notes import save_note
        assert "error" in save_note("baslik", "icerik", "")
