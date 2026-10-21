"""tests/test_eklenti_sohbeti.py — panel sohbeti çekirdeğe mi gidiyor?

AGENTS.md §9 (tek beyin): eklenti paneli kendi cevabını üretmez; mesaj
`chat.flow.mesaj_isle` yolundan geçer. Bu dosya o iddiayı model çağırmadan
ölçer: `mesaj_isle` sahtelenir, gerçek sarmalayıcı (`_eklenti_sohbet`)
çalışır ve dönen cevabın çekirdekten geldiği kanıtlanır.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import basak_web  # noqa: E402
from chat import flow  # noqa: E402


def _bitir(cevap, kaynak=""):
    return "BasakUI.bitir(%s, %s)" % (json.dumps(cevap), json.dumps(kaynak))


@pytest.fixture(autouse=True)
def _kimligi_geri_al():
    from chat.kimlik import aktif_kullanici, kullanici_kur
    onceki = aktif_kullanici()
    yield
    kullanici_kur(onceki)


@pytest.fixture
def cekirdek(monkeypatch):
    """Beyin/araç hazır gibi davran (gerçek model çağrılmaz)."""
    monkeypatch.setattr(basak_web, "BEYIN", object(), raising=False)
    monkeypatch.setattr(basak_web, "TOOLS", [], raising=False)


def test_cevap_cekirdekten_gelir(monkeypatch, cekirdek):
    gorulen = {}

    def sahte_mesaj_isle(metin, brain, prompt, ayikla, tools=None, **kw):
        gorulen["metin"] = metin
        gorulen["tools"] = tools
        ayikla(_bitir("merhaba, sayfayı okudum", "groq"))

    monkeypatch.setattr(flow, "mesaj_isle", sahte_mesaj_isle)

    sonuc = basak_web._eklenti_sohbet("   selam   ", "ayse")

    assert sonuc == {"cevap": "merhaba, sayfayı okudum", "kaynak": "groq"}
    assert gorulen["metin"] == "selam", "mesaj kırpılmadan çekirdeğe gitmeli"
    assert gorulen["tools"] == [], "araç kataloğu çekirdekten geçmeli"


def test_kullanici_kimligi_cekirdege_tasinir(monkeypatch, cekirdek):
    from chat.kimlik import aktif_kullanici

    def sahte_mesaj_isle(metin, brain, prompt, ayikla, tools=None, **kw):
        ayikla(_bitir("tamam"))

    monkeypatch.setattr(flow, "mesaj_isle", sahte_mesaj_isle)
    basak_web._eklenti_sohbet("selam", "mehmet")
    assert aktif_kullanici() == "mehmet"


def test_cekirdek_hatasi_acik_hata_olur(monkeypatch, cekirdek):
    def sahte_mesaj_isle(metin, brain, prompt, ayikla, tools=None, **kw):
        ayikla("BasakUI.error(" + json.dumps("kota bitti") + ")")

    monkeypatch.setattr(flow, "mesaj_isle", sahte_mesaj_isle)
    with pytest.raises(RuntimeError) as hata:
        basak_web._eklenti_sohbet("selam", "casper")
    assert "kota bitti" in str(hata.value)


def test_bos_mesaj_cekirdege_gitmez(monkeypatch, cekirdek):
    cagrildi = {"n": 0}

    def sahte_mesaj_isle(*a, **k):
        cagrildi["n"] += 1

    monkeypatch.setattr(flow, "mesaj_isle", sahte_mesaj_isle)
    with pytest.raises(ValueError):
        basak_web._eklenti_sohbet("   ", "casper")
    assert cagrildi["n"] == 0


def test_cekirdek_yoksa_uydurmaz(monkeypatch):
    monkeypatch.setattr(basak_web, "BEYIN", None, raising=False)
    monkeypatch.setattr(basak_web, "TOOLS", None, raising=False)
    with pytest.raises(RuntimeError) as hata:
        basak_web._eklenti_sohbet("selam", "casper")
    assert "cekirdek hazir degil" in str(hata.value)
