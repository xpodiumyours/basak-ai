"""tests/test_kapasite_kapi.py — Kapasiteye göre katman kademe testleri.

Ucretsiz/kucuk modellerde agir katmanlar (zorunlu tool dayatmasi, her
mesajda embedding/hafiza, uzun tool dongusu) kapanir; guclu modellerde
acik kalir. Bu test yalnizca siniflandirma + sozlesme gerekliliklerini
dogrular; canli zincir davranisi mevcut 442 test ile korunur.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain.kapasite import mod_kapasite, Kapasite  # noqa: E402
from tools.definitions import CORE_TOOL_NAMES, SMALL_CORE_TOOL_NAMES  # noqa: E402


def test_kucuk_kaynak_havuzu():
    kap = mod_kapasite(kaynaklar=["ollama"])
    assert kap.kucuk is True
    assert kap.guclu is False


def test_guclu_kaynak_havuzu():
    kap = mod_kapasite(kaynaklar=["groq", "ollama"])
    assert kap.guclu is True


def test_model_adi_deseni_kucuk():
    kap = mod_kapasite(model_adi="qwen2.5:3b")
    assert kap.kucuk is True


def test_model_adi_deseni_guclu():
    kap = mod_kapasite(model_adi="llama-3.3-70b")
    assert kap.guclu is True


def test_kaynak_ile_siniflandirma():
    kap = mod_kapasite(kaynak="nvidia")
    assert kap.kucuk is True
    kap2 = mod_kapasite(kaynak="groq")
    assert kap2.guclu is True


def test_gate_modu_sikı_gevsek(tmp_path):
    # SETTINGS_FILE'i gecici dosyaya yonlendir
    import brain.kapasite as kmod
    cfg = tmp_path / "ayarlar.json"
    cfg.write_text('{"gate_modu": "sikı"}', encoding="utf-8")
    orig = kmod.SETTINGS_FILE
    kmod.SETTINGS_FILE = str(cfg)
    try:
        assert mod_kapasite(kaynaklar=["ollama"]).guclu is True
        cfg.write_text('{"gate_modu": "gevsek"}', encoding="utf-8")
        assert mod_kapasite(kaynaklar=["groq"]).kucuk is True
    finally:
        kmod.SETTINGS_FILE = orig


def test_belirsizlik_guclu_varsayar():
    # kaynaklar bos, model yok -> mevcut davranis korunur (guclu)
    kap = mod_kapasite()
    assert kap.guclu is True


def test_small_core_core_daha_dar():
    # Kucuk model icin daha dar ve basit bir core seti: okuma + arama +
    # en basit yazma. CORE'a gore daha az arac, guclu modelde kullanilmaz.
    assert len(SMALL_CORE_TOOL_NAMES) < len(CORE_TOOL_NAMES)
    assert "read_file" in SMALL_CORE_TOOL_NAMES
    assert "save_note" not in SMALL_CORE_TOOL_NAMES
    assert "list_tasks" not in SMALL_CORE_TOOL_NAMES


def test_moduller_derleniyor():
    import py_compile
    kok = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for rel in ("brain/kapasite.py", "chat/flow.py",
               "_chat_legacy.py", "chat/tools.py", "tools/definitions.py"):
        py_compile.compile(os.path.join(kok, rel), doraise=True)


def test_kucuk_modelde_tool_yonlendirme_korunur(monkeypatch):
    """Regresyon: ucretsiz/kucuk modelde (kilo-only) TOOL_YONLENDIRME
    prompttan dusmemeli — aksi halde model araci tutar ama kullanmaz,
    dosya sorularinda bilgisayari 'gormeden' uydurur."""
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
            return {"content": "ok", "role": "assistant"}, "kilo"

    from chat.prompts import TOOL_YONLENDIRME, KIMLIK_BLOGU
    from tools import TOOLS
    flow.mesaj_isle_yeni("masaüstünde ne var", FakeBrain(),
                         "SYS", lambda c: None, TOOLS)
    birlesik = "\n".join(m.get("content", "") for m in captured["messages"]
                         if m.get("role") == "system")
    assert TOOL_YONLENDIRME in birlesik, "kucuk modelde tool dayatmasi dustu!"
    # 2026-09-10: kimlik ayri ilk mesajdir (kimlik karisikligi arastirmasi).
    assert captured["messages"][0]["content"] == KIMLIK_BLOGU
