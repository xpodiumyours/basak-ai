"""tests/test_akis_ham_arac.py — Akis ham arac gorurse tam yola duser.

2026-09-10 canli sinav bulgusu: model araci METIN olarak yazdiginda
(```list_files(...)```) akis yolu onu normal yazi sanip araci hic
kosturmadan ekrana veriyordu ("bilgisayari goremez" sikayeti).
Simdi ham arac iceren akis metin COP sayilir, cevap verilmeden
tam yola dusulur.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chat as _c
import _chat_legacy as _L
import chat.context as _ctx
import chat.oturum as _oturum
from chat.flow import mesaj_isle_yeni as mesaj_isle
from tools import TOOLS


class SahteBeyin:
    def __init__(self, parcalar, tam_cevap="TAM-YOL-CEVAP"):
        self._parcalar = parcalar
        self._tam = tam_cevap
        self.cevapla_cagrildi = 0

    def yerel_modeller(self):
        return ["qwen2.5:7b"]

    def bulut_musait(self):
        return True

    def _bulut_zinciri(self):
        return []

    def cevapla_yayin(self, messages, model):
        for p in self._parcalar:
            yield "sahte", p

    def cevapla(self, messages, model, tools=None):
        self.cevapla_cagrildi += 1
        return {"content": self._tam}, "sahte"


def _toplayici():
    kutu = {"reply": None, "bitir": None, "error": None}

    def _ilk(code, prefix):
        ic = code[len(prefix):]
        if ic.endswith(")"):
            ic = ic[:-1]
        return json.JSONDecoder().raw_decode(ic.strip())[0]

    def cb(code):
        if code.startswith("BasakUI.reply("):
            kutu["reply"] = _ilk(code, "BasakUI.reply(")
        elif code.startswith("BasakUI.bitir("):
            kutu["bitir"] = _ilk(code, "BasakUI.bitir(")
        elif code.startswith("BasakUI.error("):
            kutu["error"] = _ilk(code, "BasakUI.error(")
    return kutu, cb


def _izole(monkeypatch, tmp_path):
    gecmis = tmp_path / "g.json"
    gecmis.write_text("[]", encoding="utf-8")
    ayar = tmp_path / "a.json"
    ayar.write_text(json.dumps({"model": "qwen2.5:7b"}), encoding="utf-8")
    gorev = tmp_path / "t.json"
    gorev.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(_L, "HISTORY_FILE", str(gecmis))
    monkeypatch.setattr(_L, "SETTINGS_FILE", str(ayar))
    monkeypatch.setattr(_L, "GOREVLER_FILE", str(gorev))
    monkeypatch.setattr(_L, "_hafiza", False)
    monkeypatch.setattr(_ctx, "_hafiza", False)
    monkeypatch.setattr(_oturum, "kaydet_cift", lambda *a, **k: None)


class TestAkisHamArac:
    def test_ham_arac_tam_yola_duser(self, monkeypatch, tmp_path):
        _izole(monkeypatch, tmp_path)
        beyin = SahteBeyin(['bak:\n', 'list_files(folder="belgeler")'])
        kutu, cb = _toplayici()
        mesaj_isle("belgelerimde ne var", beyin, "SYS", cb, TOOLS)
        assert kutu["error"] is None
        assert beyin.cevapla_cagrildi == 1
        assert kutu["bitir"] is None
        assert kutu["reply"] == "TAM-YOL-CEVAP"

    def test_temiz_akis_dogrudan_biter(self, monkeypatch, tmp_path):
        _izole(monkeypatch, tmp_path)
        beyin = SahteBeyin(["merhaba Casper"])
        kutu, cb = _toplayici()
        mesaj_isle("merhaba", beyin, "SYS", cb, TOOLS)
        assert kutu["error"] is None
        assert beyin.cevapla_cagrildi == 0
        assert kutu["bitir"] == "merhaba Casper"
        assert kutu["reply"] is None

    def test_sayi_parca_patlamaz(self, monkeypatch, tmp_path):
        _izole(monkeypatch, tmp_path)
        beyin = SahteBeyin(["sayi ", 42])
        kutu, cb = _toplayici()
        mesaj_isle("merhaba", beyin, "SYS", cb, TOOLS)
        assert kutu["error"] is None
        assert kutu["bitir"] == "sayi 42"
