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
                   "complete_task", "update_task_status"):
            assert ad in TANINMIS_TOOLLAR, ad

    def test_durum_etiketleri_var(self):
        from chat.tools import DURUM_METNI
        for ad in ("get_reminders", "add_task", "list_tasks",
                   "complete_task", "update_task_status"):
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


class TestGorevDurumu:
    """Yarim gorev: durum alani + update_task_status (2026-10-17)."""

    def test_ekleme_pending_yazar(self, tmp_path):
        dosya = str(tmp_path / "gorevler.json")
        tasks.add_task("makale yaz", dosya)
        with open(dosya, encoding="utf-8-sig") as f:
            g = json.load(f)[0]
        assert g["status"] == "pending"
        assert g.get("updated")

    def test_durum_yasam_dongusu(self, tmp_path):
        dosya = str(tmp_path / "gorevler.json")
        tasks.add_task("veri temizle", dosya)

        r = tasks.update_task_status(1, "in_progress", dosya)
        assert "error" not in r, r
        assert "in_progress" in tasks.list_tasks(dosya)["result"]

        r = tasks.update_task_status(1, "paused", dosya, "tablo bekleniyor")
        assert "error" not in r, r
        with open(dosya, encoding="utf-8-sig") as f:
            g = json.load(f)[0]
        assert g["status"] == "paused"
        assert g["note"] == "tablo bekleniyor"
        assert g["done"] is False

        r = tasks.update_task_status(1, "done", dosya)
        assert "error" not in r, r
        with open(dosya, encoding="utf-8-sig") as f:
            g = json.load(f)[0]
        assert g["done"] is True
        assert g.get("completed_at")
        # Kapanan gorev acik listede gorunmez.
        assert "veri temizle" not in tasks.list_tasks(dosya)["result"]

    def test_durum_geri_alinabilir(self, tmp_path):
        dosya = str(tmp_path / "gorevler.json")
        tasks.add_task("rapor", dosya)
        tasks.complete_task(1, dosya)
        r = tasks.update_task_status(1, "pending", dosya)
        assert "error" not in r, r
        assert "rapor" in tasks.list_tasks(dosya)["result"]
        with open(dosya, encoding="utf-8-sig") as f:
            g = json.load(f)[0]
        assert "completed_at" not in g

    def test_gecersiz_durum_reddedilir(self, tmp_path):
        dosya = str(tmp_path / "gorevler.json")
        tasks.add_task("is", dosya)
        r = tasks.update_task_status(1, "yarim", dosya)
        assert "error" in r, r
        with open(dosya, encoding="utf-8-sig") as f:
            assert json.load(f)[0]["status"] == "pending"

    def test_olmayan_gorev_hata_doner(self, tmp_path):
        dosya = str(tmp_path / "gorevler.json")
        tasks.add_task("is", dosya)
        assert "error" in tasks.update_task_status(99, "paused", dosya)

    def test_dispatch_dali_ayni_dosyaya_yazar(self, tmp_path, monkeypatch):
        import tools
        dosya = str(tmp_path / "gorevler.json")
        monkeypatch.setattr(tools, "GOREVLER_FILE", dosya)
        tools.calistir("add_task", {"text": "dispatcher isi"})
        r = tools.calistir("update_task_status",
                           {"task_id": 1, "status": "paused"})
        assert "error" not in r, r
        with open(dosya, encoding="utf-8-sig") as f:
            assert json.load(f)[0]["status"] == "paused"
        # Durum zorunlu: eksik cagri gorevi pending'e geri cevirmez.
        r = tools.calistir("update_task_status", {"task_id": 1})
        assert "error" in r, r
        with open(dosya, encoding="utf-8-sig") as f:
            assert json.load(f)[0]["status"] == "paused"


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
