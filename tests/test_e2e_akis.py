"""tests/test_e2e_akis.py — Uçtan uca oturum senaryosu (E2E).

Ayrı ayrı test edilen parçaları TEK SIRADA zincirler; alt sistemler
arasındaki geçişleri (geçmiş ↔ hafıza ↔ kapı ↔ izin ↔ temizlik ↔ kapanış)
doğrular:

  Tur 1 sohbet          -> cevap + episodic(onem=1)
  Tur 2 "hatırla"       -> save_note ailesi sunulur, araç koşar, episodic(onem=3)
  Tur 3 ölçüm sorusu    -> git_durum koşar, [Ö] alıntılı cevap kapıdan geçer
  Temizlik              -> gecmis silinir + episodic unutulur, sayı raporlanır
  Kapanış               -> DB güvenle kapatılır
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import basak_app
import chat as c
from memory.engine import HafizaMotoru


def _schema(ad):
    return {"type": "function",
            "function": {"name": ad, "description": "",
                         "parameters": {"type": "object", "properties": {}}}}


class SenaryoBrain:
    """Script'li beyin: siradaki yaniti dondurur, sunulan araclari yakalar."""

    def __init__(self, yanitlar):
        self._yanitlar = list(yanitlar)
        self.sunulan = []

    def yerel_modeller(self):
        return ["sahte"]

    def bulut_musait(self):
        return True

    def cevapla(self, messages, yerel_model, tools=None,
                override_model=None):
        self.sunulan.append(
            sorted(t["function"]["name"] for t in (tools or [])))
        return self._yanitlar.pop(0), "sahte"


@pytest.fixture
def oturum(monkeypatch, tmp_path):
    motor = HafizaMotoru(db_yolu=str(tmp_path / "e2e.db"),
                         embed_fn=lambda m: None)
    monkeypatch.setattr(c, "_hafiza", motor)
    gecmis = str(tmp_path / "gecmis.json")
    ayarlar = str(tmp_path / "ayarlar.json")
    monkeypatch.setattr(c, "HISTORY_FILE", gecmis)
    monkeypatch.setattr(c, "SETTINGS_FILE", ayarlar)

    kosanlar = []
    def sahte_calistir(ad, args, *a, **kw):
        kosanlar.append(ad)
        return {"result": "%s OK (%s)" % (ad,
                json.dumps(args, ensure_ascii=False))}
    monkeypatch.setattr("tools.calistir", sahte_calistir)

    kutu = {"cevaplar": [], "hatalar": []}

    def cb(code):
        if not (code.startswith("BasakUI.reply")
                or code.startswith("BasakUI.error")):
            return
        ic = code[code.index("(") + 1: code.rindex(")")]
        m = json.loads("[" + ic + "]")
        if code.startswith("BasakUI.reply"):
            kutu["cevaplar"].append(m)
        else:
            kutu["hatalar"].append(m[0])

    return {"motor": motor, "gecmis": gecmis, "kosanlar": kosanlar,
            "kutu": kutu, "cb": cb, "tmp": tmp_path,
            "monkeypatch": monkeypatch}


TOOLLAR = [_schema(a) for a in (
    "web_search", "add_task", "list_tasks", "complete_task", "save_note",
    "deftere_kaydet", "read_file", "write_file_tool", "list_files",
    "ac_uygulama", "get_reminders", "git_durum", "belge_ara", "dosya_bilgi",
)]


def _cagri(ad, args_json="{}", cid="1"):
    return {"id": cid, "type": "function",
            "function": {"name": ad, "arguments": args_json}}


class TestUctanUcaOturum:
    def test_tum_akis_zinciri(self, oturum):
        motor, kutu = oturum["motor"], oturum["kutu"]

        # --- TUR 1: sohbet (araç yok) ---
        brain = SenaryoBrain([{"content": "İyiyim, teşekkürler!"}])
        c.mesaj_isle("bugün nasılsın?", brain, "SYS", oturum["cb"], TOOLLAR)
        assert kutu["cevaplar"][-1][0].endswith("teşekkürler!")
        assert kutu["hatalar"] == []
        assert motor.say() == 1                      # episodic(onem=1)
        onem1 = motor.conn.execute(
            "SELECT onem FROM memories").fetchone()[0]
        assert onem1 == 1
        # E2E bulgusu (2026-08-24): siradan sohbet TEK cagri olmali —
        # eskiden olcum-retry her mesajda ikinci cagri tetikliyordu.
        assert len(brain.sunulan) == 1

        # --- TUR 2: hatırla -> yazma aracı koşar ---
        brain = SenaryoBrain([
            {"content": "", "tool_calls": [_cagri(
                "save_note", '{"title":"sunucu","content":"10.0.0.5"}')]},
            {"content": "[B] Sunucu adresini kaydettim."},
        ])
        c.mesaj_isle("Bunu hatırla: sunucu 10.0.0.5", brain, "SYS",
                     oturum["cb"], TOOLLAR)
        assert "sunucu adresini kaydettim" in \
            kutu["cevaplar"][-1][0].lower()
        assert oturum["kosanlar"][-1] == "save_note"
        # yalnız ilgili aile + ölçüm üçlüsü sunulmalı (bağlam diyeti)
        assert brain.sunulan[-1] == ["belge_ara", "deftere_kaydet",
                                     "dosya_bilgi", "git_durum",
                                     "save_note"]
        onem3 = motor.conn.execute(
            "SELECT onem FROM memories ORDER BY id DESC LIMIT 1"
        ).fetchone()[0]
        assert onem3 == 3                            # hatırla sinyali

        # --- TUR 3: ölçüm sorusu -> git_durum + [Ö] kanıtlı cevap ---
        brain = SenaryoBrain([
            {"content": "", "tool_calls": [
                _cagri("git_durum", '{"proje":"vixrex"}', "2")]},
            {"content": '[Y] VixRex main dalında.\n'
                        '[Ö1] git_durum "Dal: main"'},
        ])
        c.mesaj_isle("VixRex'te durum ne?", brain, "SYS",
                     oturum["cb"], TOOLLAR)
        son_cevap = kutu["cevaplar"][-1][0]
        assert "badge::Ö::" in son_cevap             # kanıt yaşadı
        assert oturum["kosanlar"][-1] == "git_durum"

        # --- ara durum: geçmiş dosyası 3 çift tutuyor ---
        kayitlar = json.load(open(oturum["gecmis"], encoding="utf-8"))
        assert len(kayitlar) == 6

        # --- TEMİZLİK: gecmis + episodic birlikte unutulur ---
        oturum["monkeypatch"].setattr(basak_app, "HISTORY_FILE",
                                      oturum["gecmis"])
        api = basak_app.Api()
        r = api.clear()
        assert r["ok"] and r["unutulan_ani"] == 3
        assert not os.path.exists(oturum["gecmis"])
        assert motor.say() == 0

        # --- KAPANIŞ: DB güvenle kapanır ---
        api._hafizayi_kapat()

    def test_hata_yolu_gecmise_yazmaz(self, oturum):
        brain = SenaryoBrain([])
        brain.yerel_modeller = lambda: []
        brain.bulut_musait = lambda: False
        c.mesaj_isle("selam", brain, "SYS", oturum["cb"], None)
        assert any("beyin" in h for h in oturum["kutu"]["hatalar"])
        assert not os.path.exists(oturum["gecmis"])   # hicbir sey yazilmadi
