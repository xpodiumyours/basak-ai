# -*- coding: utf-8 -*-
"""beyin.cevapla_yayin -> ilerleme bildirimi (saglayici + muhakeme).

Canli olcum (2026-11-04): groq/gpt-oss cevap metninden ONCE muhakeme
jetonu uretiyor; akis onlari atmadigi icin ekran 43 sn bos kaliyordu.
Bu test, gercek Brain akisinda saglayici adinin ve muhakeme suresinin
ilerleme geri cagrisina dustugunu ve cevap metninin DEGISMEDIGINI kilitler.
"""

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain import brain as brain_mod
from brain.brain import Brain


class SahteSDK:
    """OpenAI SDK taklidi: once muhakeme, sonra metin parcalari."""

    def __init__(self, muhakeme="dusunuyorum", parcalar=("sel", "am")):
        self._muhakeme = muhakeme
        self._parcalar = list(parcalar)
        self.model = "test-model"
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        def _uretici():
            yield SimpleNamespace(choices=[SimpleNamespace(
                delta=SimpleNamespace(content=None, tool_calls=None,
                                      reasoning_content=self._muhakeme),
                finish_reason=None)])
            for p in self._parcalar:
                yield SimpleNamespace(choices=[SimpleNamespace(
                    delta=SimpleNamespace(content=p, tool_calls=None,
                                          reasoning_content=None),
                    finish_reason=None)])
            yield SimpleNamespace(choices=[SimpleNamespace(
                delta=SimpleNamespace(content=None, tool_calls=None,
                                      reasoning_content=None),
                finish_reason="stop")])
        return _uretici()


def _beyin(monkeypatch, tmp_path):
    brain_mod._COOLDOWN.clear()
    monkeypatch.setattr(brain_mod, "STATE_DIR", str(tmp_path))
    monkeypatch.setattr(brain_mod, "_yerel_kota_doldu",
                        lambda ad, istat: "")
    b = Brain.__new__(Brain)
    monkeypatch.setattr(
        b, "_bulut_zinciri", lambda tools=False: [("groq", SimpleNamespace(client=SahteSDK(), model="test-model"))])
    return b


def test_akis_saglayiciyi_ve_muhakemeyi_bildirir(monkeypatch, tmp_path):
    b = _beyin(monkeypatch, tmp_path)
    olaylar = []
    parcalar = list(b.cevapla_yayin(
        [{"role": "user", "content": "selam"}], None, tools=None,
        ilerleme=olaylar.append))

    assert "".join(p for _, p in parcalar) == "selam"
    turler = [o.get("tur") for o in olaylar]
    assert turler[0] == "saglayici"
    assert olaylar[0]["saglayici"] == "groq"
    assert "muhakeme" in turler
    assert "metin" in turler


def test_ilerleme_bozulsa_da_akis_ve_metin_korunur(monkeypatch, tmp_path):
    b = _beyin(monkeypatch, tmp_path)

    def bozuk(veri):
        raise RuntimeError("UI kapali")

    parcalar = list(b.cevapla_yayin(
        [{"role": "user", "content": "selam"}], None, tools=None,
        ilerleme=bozuk))

    assert "".join(p for _, p in parcalar) == "selam"
