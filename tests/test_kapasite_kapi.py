"""tests/test_kapasite_kapi.py — tüm modeller için tam kapasite sözleşmesi.

Başak sağlayıcıyı küçük/güçlü diye sınıflandırıp hafıza, araç veya çok-adımlı
çalışma hakkını azaltmaz. Güvenlik ve izinler ayrı katmanda kalır.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain.kapasite import mod_kapasite  # noqa: E402
from tools import TOOLS  # noqa: E402
from tools.definitions import CORE_TOOL_NAMES, SMALL_CORE_TOOL_NAMES  # noqa: E402


def test_tum_kaynaklar_tam_kapasite():
    for kaynak in ("ollama", "kilo", "nvidia", "groq", "glm", "gemini"):
        kap = mod_kapasite(kaynak=kaynak)
        assert kap.guclu is True
        assert kap.kucuk is False


def test_model_adi_kapasiteyi_dusurmez():
    for model in ("qwen2.5:3b", "llama-3.2-3b", "llama-3.3-70b"):
        kap = mod_kapasite(model_adi=model)
        assert kap.guclu is True
        assert kap.kucuk is False


def test_kaynak_havuzu_kapasiteyi_dusurmez():
    assert mod_kapasite(kaynaklar=["ollama"]).guclu is True
    assert mod_kapasite(kaynaklar=["kilo"]).guclu is True


def test_tum_araclar_her_modele_acik():
    tum = {t["function"]["name"] for t in TOOLS}
    assert CORE_TOOL_NAMES == tum
    assert SMALL_CORE_TOOL_NAMES == tum


def test_moduller_derleniyor():
    import py_compile
    kok = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for rel in ("brain/kapasite.py", "chat/flow.py",
                "_chat_legacy.py", "chat/tools.py", "tools/__init__.py"):
        py_compile.compile(os.path.join(kok, rel), doraise=True)


def test_model_tum_araclari_gorur(monkeypatch):
    import chat.flow as flow
    import _chat_legacy as legacy

    monkeypatch.setattr(legacy, "yukle", lambda *a, **k: {})
    monkeypatch.setattr(legacy, "kaydet", lambda *a, **k: None)
    monkeypatch.setattr(legacy, "_save_and_reply", lambda *a, **k: None)
    monkeypatch.setattr(legacy, "_hafiza_al", lambda: None)
    monkeypatch.setattr(legacy, "_ilgili_anilar", lambda *a, **k: [])

    captured = {}

    class FakeBrain:
        def yerel_modeller(self):
            return []

        def bulut_musait(self):
            return True

        def _bulut_zinciri(self):
            return [("kilo", object())]

        def cevapla(self, messages, yerel_model, tools=None, **kw):
            captured["messages"] = messages
            captured["tools"] = tools
            return {"content": "ok"}, "kilo"

    flow.mesaj_isle_yeni(
        "masaüstünde ne var", FakeBrain(), "", lambda c: None, TOOLS)

    verilen = {t["function"]["name"] for t in captured["tools"]}
    beklenen = {t["function"]["name"] for t in TOOLS}
    assert verilen == beklenen


def test_arac_promptu_dayatilmaz():
    from chat.prompts import TOOL_YONLENDIRME, BIKIMLONDIRME_YONLENDIRME
    assert TOOL_YONLENDIRME == ""
    assert BIKIMLONDIRME_YONLENDIRME == ""
