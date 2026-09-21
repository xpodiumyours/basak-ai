"""tests/test_onbellek.py — Tekrarlanan mesaj önbelleği testleri.

Çevrimdışı: gerçek model yok. Önbellek yalnızca ARKA ARKAYA aynı mesajı
yakalar; tam eşitlik dışında hiçbir şeye bakmaz (chatbot yasağı) ve
araç koşan turun sonucunu saklamaz (yan etki riski).
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chat as c
from chat import onbellek


@pytest.fixture(autouse=True)
def _temiz_onbellek():
    onbellek.temizle()
    yield
    onbellek.temizle()


@pytest.fixture
def izole(monkeypatch, tmp_path):
    from chat import context as cc
    monkeypatch.setattr(cc, "HISTORY_FILE", str(tmp_path / "g.json"))
    monkeypatch.setattr(cc, "SETTINGS_FILE", str(tmp_path / "a.json"))
    monkeypatch.setattr(cc, "_hafiza", False)
    return tmp_path


def _toplayici():
    kutu = {"cevap": None, "hata": None, "kaynak": None}

    def cb(code):
        if not (code.startswith("BasakUI.bitir")
                or code.startswith("BasakUI.error")):
            return
        ic = code[code.index("(") + 1: code.rindex(")")]
        m = json.loads("[" + ic + "]")
        if code.startswith("BasakUI.bitir"):
            kutu["cevap"] = m[0]
            kutu["kaynak"] = m[1] if len(m) > 1 else None
        else:
            kutu["hata"] = m[0]
    return kutu, cb


class SayanBeyin:
    """Kaç kez çağrıldığını sayan sahte beyin (ajan yolu YOK)."""

    def __init__(self):
        self.cagri = 0

    def bulut_musait(self):
        return True

    def cevapla(self, mesajlar, model=None, tools=None, tool_choice=None):
        self.cagri += 1
        return {"content": "cevap %d" % self.cagri}, "sahte"


class TestAnahtar:
    def test_bos_metin_bos_anahtar(self):
        assert onbellek.anahtar("") == ""
        assert onbellek.anahtar("   ") == ""
        assert onbellek.anahtar(None) == ""

    def test_yazim_farki_esitlenir(self):
        assert onbellek.anahtar("Merhaba   Dünya") == \
            onbellek.anahtar("merhaba dünya")

    def test_farkli_metin_farkli_anahtar(self):
        assert onbellek.anahtar("merhaba") != onbellek.anahtar("merhaba!")


class TestAlKoy:
    def test_onceki_mesaj_ayniysa_doner(self):
        onbellek.koy("merhaba", "selam")
        gecmis = [{"role": "user", "content": "merhaba"},
                  {"role": "assistant", "content": "selam"}]
        assert onbellek.al("merhaba", gecmis) == "selam"

    def test_onceki_mesaj_farkliysa_donmez(self):
        onbellek.koy("merhaba", "selam")
        gecmis = [{"role": "user", "content": "baska soru"}]
        assert onbellek.al("merhaba", gecmis) == ""

    def test_gecmis_bossa_donmez(self):
        onbellek.koy("merhaba", "selam")
        assert onbellek.al("merhaba", []) == ""

    def test_suresi_dolunca_donmez(self, monkeypatch):
        onbellek.koy("merhaba", "selam")
        monkeypatch.setattr(onbellek, "OMUR_SN", -1)
        gecmis = [{"role": "user", "content": "merhaba"}]
        assert onbellek.al("merhaba", gecmis) == ""

    def test_bos_cevap_saklanmaz(self):
        assert onbellek.koy("merhaba", "") is False
        assert onbellek.koy("", "selam") is False

    def test_temizle(self):
        onbellek.koy("merhaba", "selam")
        onbellek.temizle()
        assert onbellek.al("merhaba",
                           [{"role": "user", "content": "merhaba"}]) == ""


class TestAkimIcinde:
    def test_ayni_mesaj_ikinci_kez_modele_gitmez(self, izole):
        brain = SayanBeyin()
        kutu1, cb1 = _toplayici()
        c.mesaj_isle("merhaba", brain, "SYS", cb1)
        assert brain.cagri == 1 and kutu1["cevap"] == "cevap 1"

        kutu2, cb2 = _toplayici()
        c.mesaj_isle("merhaba", brain, "SYS", cb2)
        assert brain.cagri == 1, "ayni mesaj icin model YENIDEN cagrildi"
        assert kutu2["cevap"] == "cevap 1"
        assert kutu2["kaynak"] == "onbellek"

    def test_farkli_mesaj_onbellege_takilmaz(self, izole):
        brain = SayanBeyin()
        _, cb1 = _toplayici()
        c.mesaj_isle("merhaba", brain, "SYS", cb1)
        _, cb2 = _toplayici()
        c.mesaj_isle("nasilsin", brain, "SYS", cb2)
        assert brain.cagri == 2

    def test_araya_baska_soru_girerse_onbellek_devreye_girmez(self, izole):
        brain = SayanBeyin()
        _, cb1 = _toplayici()
        c.mesaj_isle("merhaba", brain, "SYS", cb1)
        _, cb2 = _toplayici()
        c.mesaj_isle("nasilsin", brain, "SYS", cb2)
        _, cb3 = _toplayici()
        c.mesaj_isle("merhaba", brain, "SYS", cb3)
        assert brain.cagri == 3, "arka arkaya olmayan tekrar onbellekten geldi"

    def test_misafirde_onbellek_yok(self, izole):
        brain = SayanBeyin()
        _, cb1 = _toplayici()
        c.mesaj_isle("merhaba", brain, "SYS", cb1, misafir=True)
        _, cb2 = _toplayici()
        c.mesaj_isle("merhaba", brain, "SYS", cb2, misafir=True)
        assert brain.cagri == 2, "misafir izsizligi bozuldu"


class TestKaydetBayragi:
    def test_onbellekle_false_saklamaz(self, izole):
        from chat.flow import _kaydet
        _kaydet("soru", "cevap", "x", [], lambda k: None, "",
                onbellekle=False)
        assert onbellek.al("soru",
                           [{"role": "user", "content": "soru"}]) == ""

    def test_onbellekle_true_saklar(self, izole):
        from chat.flow import _kaydet
        _kaydet("soru", "cevap", "x", [], lambda k: None, "",
                onbellekle=True)
        assert onbellek.al("soru",
                           [{"role": "user", "content": "soru"}]) == "cevap"

    def test_misafirde_bayrak_yok_sayilir(self, izole):
        from chat.flow import _kaydet
        _kaydet("soru", "cevap", "x", [], lambda k: None, "",
                misafir=True, onbellekle=True)
        assert onbellek.al("soru",
                           [{"role": "user", "content": "soru"}]) == ""
