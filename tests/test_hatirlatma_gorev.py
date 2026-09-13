"""tests/test_hatirlatma_gorev.py — ARAC-PLANI Is 2: hatirlatma + gorev.

Sozlesme:
- get_reminders / add_task / list_tasks / complete_task uc yerde
  bagli (sema + calistir + DURUM_METNI), onaysiz kosar.
- Gorev yazma atomik + kilitli (eski guvence korundu).
- Gercek gorevler.json'a DOKUNULMAZ — testler tmp dosyada kosar.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import tasks, reminders
from tools.definitions import TANINMIS_TOOLLAR


class TestUcYer:
    def test_beyaz_listede(self):
        for ad in ("get_reminders", "add_task", "list_tasks",
                   "complete_task"):
            assert ad in TANINMIS_TOOLLAR, ad

    def test_durum_etiketleri_var(self):
        from chat.tools import DURUM_METNI
        for ad in ("get_reminders", "add_task", "list_tasks",
                   "complete_task"):
            assert ad in DURUM_METNI, ad


class TestGorevDongusu:
    def test_ekle_listele_bitir(self, tmp_path):
        dosya = str(tmp_path / "gorevler.json")
        ekle = tasks.add_task("sut al", dosya)
        assert "error" not in ekle, ekle
        liste = tasks.list_tasks(dosya)
        assert "sut al" in json.dumps(liste, ensure_ascii=False)
        no = ekle.get("id") or ekle.get("task_id") or 1
        bitir = tasks.complete_task(int(no), dosya)
        assert "error" not in bitir, bitir

    def test_bos_gorev_reddedilir(self, tmp_path):
        dosya = str(tmp_path / "gorevler.json")
        assert "error" in tasks.add_task("   ", dosya)

    def test_idler_benzersiz(self, tmp_path):
        dosya = str(tmp_path / "gorevler.json")
        for i in range(5):
            tasks.add_task("is %d" % i, dosya)
        with open(dosya, encoding="utf-8-sig") as f:
            kayitlar = json.load(f)
        idler = [g.get("id", g.get("task_id")) for g in kayitlar]
        assert len(set(idler)) == 5


class TestHatirlatma:
    def test_ozet_kosar(self, tmp_path):
        bilgi = tmp_path / "knowledge"
        bilgi.mkdir()
        (bilgi / "not.md").write_text("15 haziran dogum gunu partisi\n",
                                      encoding="utf-8")
        dosya = str(tmp_path / "gorevler.json")
        tasks.add_task("ornek is", dosya)
        ozet = reminders.bugunku_hatirlatmalar(str(bilgi), dosya)
        assert isinstance(ozet, dict)
        assert "error" not in ozet, ozet

    def test_calistir_hatti(self):
        from tools import calistir
        r = calistir("list_tasks", {})
        assert isinstance(r, dict)
        r = calistir("get_reminders", {})
        assert isinstance(r, dict)
