"""tests/test_mola_devam.py — sunucu suresi dolmadan mola, kullanici karari.

Vercel bir istege 300 sn verir. Arac turu bittikten sonra sure esigi
gectiyse run duraklar (checkpoint); is kesilmez, sonuclar imzali devam
kaydinda kalir. Devam kendiliginden olmaz: kullanici secer.
"""

import json
import time

from chat.agent_protocol import baslangic_araclari
from tools.definitions import TOOLS


def _cagri(ad, args, cid):
    return {"id": cid, "type": "function",
            "function": {"name": ad, "arguments": json.dumps(args)}}


class Beyin:
    def __init__(self):
        self.cagri = 0

    def cevapla_yayin(self, *a, **k):
        from brain.yayin import SonHata
        raise SonHata("akis yok")
        yield  # pragma: no cover

    def cevapla(self, mesajlar, model, tools=None, **kw):
        self.cagri += 1
        return {"content": "", "tool_calls": [
            _cagri("hesapla", {"ifade": "1+1"}, "c%d" % (self.cagri + 10))]}, "groq"


class Olaylar(list):
    def __call__(self, kod):
        self.append(kod)

    def olay(self, tur, **veri):
        self.append(("olay", tur, veri))


def test_sure_dolunca_mola_verir_model_turu_baslatmaz():
    from chat.agent_runtime import AgentRunState
    from chat.tools import arac_dongusu

    beyin = Beyin()
    js = Olaylar()
    state = AgentRunState("r1")
    kosan_araclar = []
    cevap, kosan = arac_dongusu(
        [_cagri("yetenek_ac", {"alanlar": ["hesap"]}, "c1")],
        [{"role": "user", "content": "x"}], beyin, None, js,
        lambda ad, a: kosan_araclar.append(ad) or {"result": "2"},
        tools=baslangic_araclari(), katalog=TOOLS, run_state=state,
        mola_zamani=time.monotonic() - 1)
    assert cevap == ""
    assert state.status == "paused"
    assert state.public_snapshot()["resumable"] is True
    assert any(o[1] == "checkpoint" for o in js if isinstance(o, tuple))
    assert beyin.cagri == 0  # yeni model turu acilmadi


def test_mola_zamani_yoksa_is_normal_surer():
    from chat.agent_runtime import AgentRunState
    from chat.tools import arac_dongusu

    class Biten(Beyin):
        def cevapla(self, mesajlar, model, tools=None, **kw):
            return {"content": "bitti"}, "groq"

    state = AgentRunState("r1")
    cevap, _ = arac_dongusu(
        [_cagri("yetenek_ac", {"alanlar": ["hesap"]}, "c1")],
        [{"role": "user", "content": "x"}], Biten(), None, Olaylar(),
        lambda ad, a: {"result": "2"},
        tools=baslangic_araclari(), katalog=TOOLS, run_state=state)
    assert cevap == "bitti"
    assert state.status == "running"


def test_devam_zinciri_onceki_runlarin_sonuclarini_tasir():
    from chat.flow import _yonlendirme_mesajlari

    olaylar = [
        {"istek": "r1", "tur": "runContext", "metin": "ilk soru"},
        {"istek": "r1", "tur": "toolDone", "id": "c1", "name": "web_search",
         "args": {"query": "a"}, "result": "sonuc-1", "turn": 1},
        {"istek": "r2", "tur": "runContext", "metin": "Kaldığın yerden devam et."},
        {"istek": "r2", "tur": "toolDone", "id": "c1", "name": "sayfa_oku",
         "args": {"url": "https://x.test"}, "result": "sonuc-2", "turn": 1},
    ]
    m = _yonlendirme_mesajlari({"olaylar": olaylar}, [])
    assert m[0] == {"role": "user", "content": "ilk soru"}
    assert m[2]["content"] == "sonuc-1"
    assert m[3] == {"role": "user", "content": "Kaldığın yerden devam et."}
    assert m[5]["content"] == "sonuc-2"
    idler = [c["id"] for x in m if x.get("tool_calls") for c in x["tool_calls"]]
    assert len(idler) == len(set(idler))


def test_imzali_cok_runlu_devam_kabul_edilir_runcontext_zorunlu():
    import app
    anahtar = b"k" * 32
    olaylar = [
        {"istek": "r1", "tur": "runContext", "metin": "ilk"},
        {"istek": "r2", "tur": "runContext", "metin": "devam"},
    ]
    token = app._handoff_tokeni({"schema": "p2-handoff-v1", "olaylar": olaylar}, anahtar)
    b = app._yonlendirme_baglami_dogrula({"schema": "p2-handoff-v1", "token": token}, anahtar)
    assert len(b["olaylar"]) == 2

    eksik = olaylar + [{"istek": "r3", "tur": "toolDone"}]
    token = app._handoff_tokeni({"schema": "p2-handoff-v1", "olaylar": eksik}, anahtar)
    try:
        app._yonlendirme_baglami_dogrula({"schema": "p2-handoff-v1", "token": token}, anahtar)
        assert False
    except ValueError:
        pass
