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
    monkeypatch.setattr(ctx, "gecmis_pencere", lambda g, *a, **k: [])
    monkeypatch.setattr(ctx, "ilgili_anilar", lambda *a, **k: [])
    monkeypatch.setattr(ctx, "hafiza_al", lambda: None)
    monkeypatch.setattr(ctx, "kaydet", lambda *a, **k: None)
    monkeypatch.setattr(flow, "_profil_isle", lambda *a, **k: ("", ""))

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
            gorulen["tools"] = [
                (t.get("function") or {}).get("name") for t in (tools or [])
            ]
            return {"content": "Merhaba, nasil yardimci olayim?"}, "groq"

    olaylar = []
    flow.mesaj_isle(
        "merhaba",
        Beyin(),
        "sistem",
        olaylar.append,
        tools=[{"type": "function",
                "function": {"name": "list_tasks"}}],
    )

    assert gorulen["tool_choice"] == "auto"
    assert gorulen["tools"] == ["yetenek_ac"]
    assert any("Merhaba, nasil yardimci olayim?" in o for o in olaylar)
    assert not any("Ajan protokolu bozuldu" in o for o in olaylar)


def test_arac_zinciri_baslayan_saglayiciyi_once_tutar_ve_fallbacki_devralir():
    from chat.tools import arac_dongusu
    from chat.agent_protocol import YETENEK_AC_ADI, baslangic_araclari

    tercihler = []
    turlar = {"n": 0}

    class Beyin:
        def cevapla(self, mesajlar, model, tools=None, tool_choice=None,
                    tercih=None):
            tercihler.append(list(tercih or []))
            assert tool_choice == "auto"
            turlar["n"] += 1
            if turlar["n"] == 1:
                # Ilk tercih gemini; Brain teknik nedenle nvidia'da basarmis
                # gibi davranir. Sonraki tur nvidia'yi oncelemeli.
                return {"tool_calls": [
                    _call("list_tasks", "{}", "c2")
                ]}, "nvidia"
            return {"content": "1 gorev var."}, "nvidia"

    tum_tools = [{
        "type": "function",
        "function": {
            "name": "list_tasks",
            "description": "Gorevleri listeler",
            "parameters": {"type": "object", "properties": {}},
        },
    }]

    cevap, kosan = arac_dongusu(
        [_call(YETENEK_AC_ADI, '{"alan":"gorevler"}', "c1")],
        [{"role": "user", "content": "gorevlerime bak"}],
        Beyin(),
        None,
        lambda kod: None,
        lambda ad, args: {"result": "1: sut al"},
        tools=baslangic_araclari(),
        tool_choice="auto",
        tum_tools=tum_tools,
        tercih=["gemini"],
    )

    assert cevap == "1 gorev var."
    assert kosan == 1
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
