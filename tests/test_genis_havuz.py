"""Faz 3+4 kapı testleri: genis havuz, gemini yedek, bos yanit, durum kullanim."""

import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_nvidia_kara_liste_model_bul_disinda():
    from brain.nvidia import KARA_LISTE, NvidiaClient

    class _M:
        def __init__(self, i):
            self.id = i

    class _List:
        def list(self):
            return [
                _M("nvidia/nemotron-4-340b-instruct"),
                _M("nvidia/nemotron-nano-3-30b-a3b"),
                _M("meta/llama-3.2-11b-vision-instruct"),
            ]

    c = NvidiaClient.__new__(NvidiaClient)
    c.client = types.SimpleNamespace(models=_List())
    c.model = None
    secilen = NvidiaClient._model_bul(c)
    assert secilen == "meta/llama-3.2-11b-vision-instruct"
    assert secilen not in KARA_LISTE


def test_nvidia_cevapla_sirasi_genis_havuzu_icerir():
    from brain.nvidia import TERCIH_SIRASI, GENIS_HAVUZ, KARA_LISTE
    gorulen = []
    sirali = []
    for m in list(TERCIH_SIRASI) + list(GENIS_HAVUZ):
        if m.lower() in {k.lower() for k in KARA_LISTE} or m in sirali:
            continue
        sirali.append(m)
        gorulen.append(m)
    assert "meta/llama-3.2-11b-vision-instruct" in sirali
    assert "nvidia/nemotron-4-340b-instruct" not in sirali
    assert "nvidia/nemotron-3.5-lightning-30b-a3b" in sirali


def test_gemini_yadek_sirasi_korur():
    from brain.gemini import MODELLER, YADEK_SIRASI
    assert MODELLER["varsayilan"] == "gemini-3-flash-preview"
    assert YADEK_SIRASI[0] == "gemini-3-flash-preview"
    assert "gemini-2.5-flash" in YADEK_SIRASI
    assert "gemini-flash-lite-latest" in YADEK_SIRASI
    # olumu/429 adaylar yedekte yok
    assert "gemini-2.5-pro" not in YADEK_SIRASI
    assert "gemini-pro-latest" not in YADEK_SIRASI
    assert "gemini-3.8-flash" not in YADEK_SIRASI


def test_gemini_basarisiz_model_yedege_duser(monkeypatch):
    from brain.gemini import GeminiClient, YADEK_SIRASI

    cagrilan = []

    class _Comp:
        def create(self, **kwargs):
            cagrilan.append(kwargs.get("model"))
            if kwargs.get("model") == YADEK_SIRASI[0]:
                raise RuntimeError("503")
            msg = types.SimpleNamespace(
                content="OK", tool_calls=None,
                role="assistant")
            return types.SimpleNamespace(
                choices=[types.SimpleNamespace(message=msg)],
                usage=None)

    class _Chat:
        completions = _Comp()

    c = GeminiClient.__new__(GeminiClient)
    c.client = types.SimpleNamespace(chat=_Chat())
    c.model = YADEK_SIRASI[0]
    yanit = c.cevapla([{"role": "user", "content": "s"}])
    assert yanit["content"] == "OK"
    assert cagrilan[0] == YADEK_SIRASI[0]
    assert c.model == YADEK_SIRASI[1]
    assert len(cagrilan) >= 2


def test_brain_bos_yanit_siradaki_saglayiciye_duser():
    """tools varken bos yanit basari sayilmaz (Faz 4 aptallasma kapisi)."""
    from brain.brain import Brain

    class _Istemci:
        model = "m1"
        def musait(self):
            return True
        def cevapla(self, messages, tools=None, **kw):
            return {"content": "   "}

    class _Istemci2:
        model = "m2"
        def musait(self):
            return True
        def cevapla(self, messages, tools=None, **kw):
            return {"content": "cevap geldi"}

    b = Brain.__new__(Brain)
    b._providers = {}
    for ad in ("groq", "glm", "cloudflare", "cohere", "nvidia", "kilo",
               "openrouter", "mistral", "huggingface", "chutes", "qwen",
               "gemini", "genel", "deepseek", "kimi"):
        b._providers[ad] = None
    b._groq = _Istemci()
    b._glm = _Istemci2()
    b._cloudflare = None
    b._cohere = None
    b._nvidia = None
    b._kilo = None
    b._openrouter = None
    b._mistral = None
    b._huggingface = None
    b._chutes = None
    b._qwen = None
    b._gemini = None
    b._genel = None

    # secici'yi basit sira yap
    import brain.secici as secici
    import brain.brain as brain_mod

    def _sahte_sec(mevcutlar=None, **kw):
        return list(mevcutlar or []), "test"

    monkey = secici.sec
    secici.sec = _sahte_sec
    try:
        # zincir: groq once (bos), glm sonra (dolu)
        # _bulut_zinciri gercek — musait olanlar
        yanit, kaynak = b.cevapla(
            [{"role": "user", "content": "s"}],
            tools=[{"type": "function",
                    "function": {"name": "x", "parameters": {}}}],
            tool_choice="auto",
        )
    finally:
        secici.sec = monkey
    assert yanit["content"] == "cevap geldi"
    assert kaynak == "glm"


def test_durum_kullanim_alani_dolabiliyor():
    """app.py /api/durum kullanim bos dict degil olculebilir alan icerir."""
    import inspect
    import app as app_mod
    src = inspect.getsource(app_mod)
    assert "kalan_gunluk_istek" in src
    assert "istek_sayisi" in src
    assert '"kullanim": kullan' in src or '"kullanim": kullan,' in src


def test_cevapla_yayin_yerel_kota_kontrolu_var():
    import inspect
    from brain import brain as brain_mod
    src = inspect.getsource(brain_mod.Brain.cevapla_yayin)
    assert "_yerel_kota_doldu" in src
