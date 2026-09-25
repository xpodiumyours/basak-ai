"""Sohbet + arac zinciri cerrahi regresyon testleri.

Amaç:
- normal sohbet tool-call'a zorlanmaz,
- araci model auto modunda secer,
- cok turlu arac zincirinde ayni saglayici once korunur,
- OpenRouter arac istegi parametreyi destekleyen uca gider.
"""

import types


def _call(ad, args="{}", cid="c1"):
    return {
        "id": cid,
        "type": "function",
        "function": {"name": ad, "arguments": args},
    }


def test_normal_sohbet_arac_varken_bile_dogal_metinle_biter(
        tmp_path, monkeypatch):
    from chat import flow
    from chat import context as ctx

    monkeypatch.setattr(ctx, "HISTORY_FILE", str(tmp_path / "g.json"))
    monkeypatch.setattr(ctx, "yukle", lambda *a, **k: [])
    monkeypatch.setattr(ctx, "temizle_history", lambda g: list(g or []))
    monkeypatch.setattr(ctx, "ilgili_anilar", lambda *a, **k: [])
    monkeypatch.setattr(ctx, "hafiza_al", lambda: None)
    monkeypatch.setattr(ctx, "kaydet", lambda *a, **k: None)

    try:
        from chat import oturum
        monkeypatch.setattr(oturum, "kaydet_cift", lambda *a, **k: None)
    except Exception:
        pass

    gorulen = {}

    class Beyin:
        def bulut_musait(self):
            return True

        def ajan_musait(self):
            return True

        def cevapla(self, mesajlar, model, tools=None, tool_choice=None,
                    **kwargs):
            gorulen["tool_choice"] = tool_choice
            gorulen["tools"] = tools
            return {"content": "Merhaba, nasil yardimci olayim?"}, "groq"

    arac = {
        "type": "function",
        "function": {
            "name": "list_tasks",
            "description": "Gorevleri listeler",
            "parameters": {"type": "object", "properties": {}},
        },
    }
    olaylar = []
    flow.mesaj_isle(
        "merhaba",
        Beyin(),
        "sistem",
        olaylar.append,
        tools=[arac],
        misafir=True,
        gecmis_override=[],
        tool_policy="auto",
    )

    # AGENTS §0: ilk turda yalniz yetenek_ac sunulur; auto modunda model
    # ister alan acar, ister dogal final üretir.
    from chat.agent_protocol import baslangic_araclari
    assert gorulen["tool_choice"] == "auto"
    assert gorulen["tools"] == baslangic_araclari()
    assert any("Merhaba, nasil yardimci olayim?" in o for o in olaylar)


def test_arac_zinciri_baslayan_saglayiciyi_once_tutar_ve_fallbacki_devralir():
    from chat.tools import arac_dongusu
    tercihler = []
    turlar = {"n": 0}
    arac = {"type": "function", "function": {
        "name": "list_tasks", "description": "Gorevleri listeler",
        "parameters": {"type": "object", "properties": {}}}}
    class Beyin:
        def cevapla_yayin(self, *a, **k):
            from brain.yayin import SonHata
            raise SonHata("testte stream yok")
            yield
        def cevapla(self, mesajlar, model, tools=None, tool_choice=None, tercih=None):
            tercihler.append(list(tercih or []))
            assert tool_choice == "auto"
            turlar["n"] += 1
            if turlar["n"] == 1:
                return {"tool_calls": [_call("list_tasks", "{}", "c2")]}, "nvidia"
            return {"content": "1 gorev var."}, "nvidia"
    cevap, kosan = arac_dongusu(
        [_call("list_tasks", "{}", "c1")],
        [{"role": "user", "content": "gorevlerime bak"}],
        Beyin(), None, lambda kod: None,
        lambda ad, args: {"result": "1: sut al"},
        tools=[arac], tool_choice="auto", tercih=["gemini"],
    )
    assert cevap == "1 gorev var."
    assert kosan == 2
    assert tercihler == [["gemini"], ["nvidia"]]

def test_openrouter_arac_istegi_parametre_destekli_uclara_gider():
    from brain.openrouter import OpenRouterClient

    yakalanan = {}

    class Comp:
        def create(self, **kwargs):
            yakalanan.update(kwargs)
            msg = types.SimpleNamespace(content="tamam", tool_calls=None)
            return types.SimpleNamespace(
                choices=[types.SimpleNamespace(message=msg)],
                usage=None,
            )

    istemci = OpenRouterClient.__new__(OpenRouterClient)
    istemci.client = types.SimpleNamespace(
        chat=types.SimpleNamespace(completions=Comp()))
    istemci.model = "ornek/model:free"

    istemci.cevapla(
        [{"role": "user", "content": "s"}],
        tools=[{
            "type": "function",
            "function": {
                "name": "x",
                "description": "x",
                "parameters": {"type": "object", "properties": {}},
            },
        }],
        tool_choice="auto",
    )

    assert yakalanan["tool_choice"] == "auto"
    assert yakalanan["extra_body"] == {
        "provider": {"require_parameters": True}
    }
