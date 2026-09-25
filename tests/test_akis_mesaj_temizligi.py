"""tests/test_akis_mesaj_temizligi.py — akan yol Basak ic alanlarini sizdirmaz.

P2 onizleme kaydi (2026-09-25): arac turundan sonra asistan mesajina eklenen
`_provider` alani akan yolda temizlenmeden gonderiliyordu; Groq her turu
400 "'messages.6': property '_provider' is unsupported" ile reddetti, is
yavas saglayiciya kaldi ve 5 dakikalik sunucu suresi doldu.
"""

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain import brain as brain_mod
from brain.brain import Brain


class YakalayanAkis:
    """OpenAI SDK taklidi: stream=True cagrisini yakalar, tek metin parcasi doner."""

    def __init__(self):
        self.giden = None

    @property
    def chat(self):
        return SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kw):
        self.giden = kw["messages"]
        parca = SimpleNamespace(choices=[SimpleNamespace(
            delta=SimpleNamespace(content="tamam", tool_calls=None,
                                  reasoning_content=None),
            finish_reason="stop")])
        return iter([parca])


def test_akan_yol_ic_alanlari_saglayiciya_gondermez(monkeypatch, tmp_path):
    brain_mod._COOLDOWN.clear()
    monkeypatch.setattr(brain_mod, "STATE_DIR", str(tmp_path))
    monkeypatch.setattr(brain_mod, "_yerel_kota_doldu", lambda ad, istat: "")
    sdk = YakalayanAkis()
    istemci = SimpleNamespace(client=sdk, model="m")
    b = Brain.__new__(Brain)
    monkeypatch.setattr(b, "_bulut_zinciri", lambda tools=False: [("groq", istemci)])

    arac = [{"id": "c1", "type": "function",
             "function": {"name": "web_search", "arguments": "{}"}}]
    mesajlar = [
        {"role": "user", "content": "ara"},
        {"role": "assistant", "content": "", "tool_calls": arac,
         "_provider": "groq"},
        {"role": "tool", "tool_call_id": "c1", "name": "web_search",
         "content": "sonuc"},
    ]
    parcalar = list(b.cevapla_yayin(mesajlar, None, tercih=["groq"]))

    assert parcalar == [("groq", "tamam")]
    assert sdk.giden is not None
    assert all("_provider" not in m for m in sdk.giden)
    asistan = sdk.giden[1]
    assert asistan["tool_calls"][0]["id"] == "c1"
    assert sdk.giden[2]["tool_call_id"] == "c1"
