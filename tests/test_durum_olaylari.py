# -*- coding: utf-8 -*-
"""tests/test_durum_olaylari.py — sessiz bekleme yerine gercek durum bildirimi.

2026-10-10 olcumu: bir soru 4,5 dakika sessiz "bekliyorum" durumunda kalmisti
(kota kuyrugu + yedek beyin denemeleri kullaniciya soylenmiyordu). Bu testler
kilitleyen davranis:
  - zincir bir saglayiciyi kota/cooldown/hata ile atladiginda durum geri
    cagrisina tek satir teknik gercek duser
  - akis bos donup tam yola dusulurken bildirim verilir
  - bildirim BOZULURSA bile zincir ASLA kirilmaz (yalnizca gosterge)
  - js_callback.olay desteklemiyorsa gozlemci sessizce None doner
"""

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain import brain as brain_mod
from brain.brain import Brain, ZincirHatasi
from brain.yayin import SonHata
from chat.output_control import durum_gozlemcisi


class SahteAkis:
    """OpenAI SDK taklidi: stream cagrisini donen parcalari uretir."""

    def __init__(self, parcalar):
        self.parcalar = list(parcalar)

    @property
    def chat(self):
        return SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kw):
        def _uretici():
            for p in self.parcalar:
                yield SimpleNamespace(choices=[SimpleNamespace(
                    delta=SimpleNamespace(content=p, tool_calls=None,
                                          reasoning_content=None),
                    finish_reason=None)])
            yield SimpleNamespace(choices=[SimpleNamespace(
                delta=SimpleNamespace(content=None, tool_calls=None,
                                      reasoning_content=None),
                finish_reason="stop")])
        return _uretici()


def _hazirla(monkeypatch, tmp_path, zincir, kota_nedeni=None):
    brain_mod._COOLDOWN.clear()
    monkeypatch.setattr(brain_mod, "STATE_DIR", str(tmp_path))
    monkeypatch.setattr(brain_mod, "_yerel_kota_doldu",
                        kota_nedeni or (lambda ad, istat: ""))
    b = Brain.__new__(Brain)
    monkeypatch.setattr(b, "_bulut_zinciri", lambda tools=False: zincir)
    return b


def _tek_cagri_sdk(cevap):
    return SimpleNamespace(cevapla=lambda messages, **kw: {"content": cevap},
                           model="m")


class TestDurumBildirimi:
    def test_kota_atlamasi_durum_olayi_verir(self, monkeypatch, tmp_path):
        # Kota ongorulu siralamada (C) saglikli saglayici one gecer; kota
        # dolu olan sona kalir ve ANCAK ulasilinca atlama olayi verir.
        # Bu yuzden saglikli gorunen de patlar: groq'ya ulasilir, atlanir.
        def patlar(messages, **kw):
            raise RuntimeError("baglanti koptu")

        zincir = [("groq", _tek_cagri_sdk("a")),
                  ("gemini", SimpleNamespace(cevapla=patlar, model="m2"))]
        kota = lambda ad, istat: ("gunluk istek kotasi"
                                  if ad == "groq" else "")
        b = _hazirla(monkeypatch, tmp_path, zincir, kota)
        gorulen = []
        try:
            b.cevapla([{"role": "user", "content": "selam"}],
                      durum=lambda m: gorulen.append(m))
            assert False, "zincir patlamaliydi"
        except ZincirHatasi:
            pass
        assert any("groq" in m and "kota" in m for m in gorulen), gorulen

    def test_hata_failover_durum_olayi_verir(self, monkeypatch, tmp_path):
        def patlar(messages, **kw):
            raise RuntimeError("baglanti koptu")
        zincir = [("groq", SimpleNamespace(cevapla=patlar, model="m1")),
                  ("gemini", _tek_cagri_sdk("selam"))]
        b = _hazirla(monkeypatch, tmp_path, zincir)
        gorulen = []
        yanit, kaynak = b.cevapla(
            [{"role": "user", "content": "selam"}],
            durum=lambda m: gorulen.append(m))

        assert kaynak == "gemini"
        assert any("groq" in m and "cevap veremedi" in m for m in gorulen), \
            gorulen

    def test_akis_kota_atlamasi_durum_olayi_verir(self, monkeypatch, tmp_path):
        # Ayni siralama sebebi: one gecen saglikli akis hizlica patlarsa
        # kota dolu olana ulasilir ve atlama olayi verir; sonucta SonHata.
        class PatlayanAkis:
            @property
            def chat(self):
                return SimpleNamespace(
                    completions=SimpleNamespace(create=self.create))

            def create(self, **kw):
                raise RuntimeError("akis acilmadi")

        zincir = [("groq", SimpleNamespace(client=SahteAkis(["a"]),
                                             model="m1")),
                  ("gemini", SimpleNamespace(client=PatlayanAkis(),
                                               model="m2"))]
        kota = lambda ad, istat: ("gunluk istek kotasi"
                                  if ad == "groq" else "")
        b = _hazirla(monkeypatch, tmp_path, zincir, kota)
        gorulen = []
        try:
            list(b.cevapla_yayin(
                [{"role": "user", "content": "selam"}], None, tools=None,
                durum=lambda m: gorulen.append(m)))
            assert False, "akis patlamaliydi"
        except SonHata:
            pass
        assert any("groq" in m and "kota" in m for m in gorulen), gorulen

    def test_durum_bozulursa_zincir_kirilmaz(self, monkeypatch, tmp_path):
        def bozuk(m):
            raise RuntimeError("UI patladi")
        zincir = [("groq", _tek_cagri_sdk("a")),
                  ("gemini", _tek_cagri_sdk("selam"))]
        kota = lambda ad, istat: "saatlik istek kotasi" if ad == "groq" else ""
        b = _hazirla(monkeypatch, tmp_path, zincir, kota)
        yanit, kaynak = b.cevapla(
            [{"role": "user", "content": "selam"}], durum=bozuk)

        assert kaynak == "gemini"
        assert yanit["content"] == "selam"


class TestGozlemci:
    def test_olay_yayinlar(self):
        kayitlar = []

        def olay(tur, **veri):
            kayitlar.append((tur, veri))
        gosterge = durum_gozlemcisi(SimpleNamespace(olay=olay))
        assert gosterge is not None
        gosterge("groq atlandi (kota)")
        assert kayitlar == [("durum", {"metin": "groq atlandi (kota)"})]

    def test_olaysiz_cagricida_none_don(self):
        assert durum_gozlemcisi(lambda kod: None) is None

    def test_olay_bozulursa_yutulur(self):
        def olay(tur, **veri):
            raise RuntimeError("yayin kapali")
        gosterge = durum_gozlemcisi(SimpleNamespace(olay=olay))
        gosterge("bir sey")  # patlamamali
