# -*- coding: utf-8 -*-
"""tests/test_bos_cevap_failover.py — bos yanit/akis basari degildir.

2026-10-10 canli olcumu (scripts/olcum/_yakin_cevre_probe.py): 20 turun
4'u "Model bos cevap dondu" ile bitti. Kok neden: akan yol hic metin
uretmezse akis "basarili" sayiliyor ve Faz 4 kurali ("bos yanit basari
degildir, siradaki saglayici denenir") yalniz aracili tek-seferlik cagrida
vardi.

Bu testler kilitleyen davranis:
  - hic metin uretmeyen akis basari DEGILDIR, siradaki saglayici devralir
  - tum zincir bos donerse SonHata (cagiran acik hata gosterir)
  - yari metin sonrasi kopma ESKI davranisi korur (SonHata, ikileme yok)
  - aracsiz tek-seferlik cagrida bos yanit da failover tetikler
"""

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain import brain as brain_mod
from brain.brain import Brain
from brain.yayin import SonHata


class SahteAkis:
    """OpenAI SDK taklidi: stream cagrisini donen parcalari uretir."""

    def __init__(self, parcalar, kopma=None):
        self.parcalar = list(parcalar)
        self.kopma = kopma
        self.giden = None

    @property
    def chat(self):
        return SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kw):
        self.giden = kw.get("messages")
        return self._uretici()

    def _uretici(self):
        for p in self.parcalar:
            yield SimpleNamespace(choices=[SimpleNamespace(
                delta=SimpleNamespace(content=p, tool_calls=None,
                                      reasoning_content=None),
                finish_reason="stop")])
        if self.kopma is not None:
            raise self.kopma


def _hazirla(monkeypatch, tmp_path, zincir):
    brain_mod._COOLDOWN.clear()
    monkeypatch.setattr(brain_mod, "STATE_DIR", str(tmp_path))
    monkeypatch.setattr(brain_mod, "_yerel_kota_doldu",
                        lambda ad, istat: "")
    b = Brain.__new__(Brain)
    monkeypatch.setattr(b, "_bulut_zinciri", lambda tools=False: zincir)
    return b


def test_bos_akis_sonraki_saglayiciye_gecer(monkeypatch, tmp_path):
    bos_sdk = SahteAkis([])
    dolu_sdk = SahteAkis(["merhaba"])
    zincir = [("groq", SimpleNamespace(client=bos_sdk, model="m1")),
              ("gemini", SimpleNamespace(client=dolu_sdk, model="m2"))]
    b = _hazirla(monkeypatch, tmp_path, zincir)

    parcalar = list(b.cevapla_yayin(
        [{"role": "user", "content": "selam"}], None, tools=None))

    assert parcalar == [("gemini", "merhaba")]


def test_bos_akis_tum_zincirde_sonhata(monkeypatch, tmp_path):
    zincir = [("groq", SimpleNamespace(client=SahteAkis([]), model="m1")),
              ("gemini", SimpleNamespace(client=SahteAkis([]), model="m2"))]
    b = _hazirla(monkeypatch, tmp_path, zincir)

    try:
        list(b.cevapla_yayin(
            [{"role": "user", "content": "selam"}], None, tools=None))
    except SonHata:
        return
    raise AssertionError("tum zincir bos dondu ama SonHata firlamadi")


def test_yari_akis_kesilirse_sonhata_ikileme_yok(monkeypatch, tmp_path):
    """Metin gorundukten sonra kopma eski davranis: baska saglayiciya gecilmez."""
    kopan = SahteAkis(["yarim cumle"], kopma=ValueError("baglanti koptu"))
    zincir = [
        ("groq", SimpleNamespace(client=kopan, model="m1")),
        ("gemini", SimpleNamespace(client=SahteAkis(["ikinci"]), model="m2")),
    ]
    b = _hazirla(monkeypatch, tmp_path, zincir)

    try:
        list(b.cevapla_yayin(
            [{"role": "user", "content": "selam"}], None, tools=None))
    except SonHata:
        pass
    else:
        raise AssertionError("yari akis kesilmesi SonHata olmali")
    # Ikinci saglayici HIC aranmamali (metin ikilenmesin).
    assert zincir[1][1].client.giden is None


def test_aracsiz_tek_seferlik_bos_yanit_failover(monkeypatch, tmp_path):
    """tools=None cagrisinda bos content artik basari degildir."""

    class Bos:
        def cevapla(self, messages, **kw):
            return {"content": ""}

    class Dolu:
        def cevapla(self, messages, **kw):
            return {"content": "tamam"}

    zincir = [("groq", Bos()), ("gemini", Dolu())]
    b = _hazirla(monkeypatch, tmp_path, zincir)

    yanit, kaynak = b.cevapla([{"role": "user", "content": "selam"}],
                              tercih=["groq", "gemini"])
    assert yanit.get("content") == "tamam"
    assert kaynak == "gemini"
