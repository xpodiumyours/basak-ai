"""tests/test_reasoning_zinciri.py — P0/P1 temizlik kilitleri.

Kapsar (2026-09-15):
- reasoning alanlari message_utils + provider + arac dongusunde korunur
- streaming tool_call biriktirilir, ayni soru ikinci kez dusundurulmez
- Cohere V2 native tool protokolu (role=tool + tool_call_id korunur)
- add_task keyword tarih tahmini yapmaz, acik date alanini dogrular
"""

import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestReasoningKorunur:
    def test_message_utils_reasoning_tasir(self):
        from brain.message_utils import mesajlari_temizle
        giris = [{"role": "assistant", "content": "",
                  "tool_calls": [{"id": "1"}],
                  "reasoning_content": "adim-adim",
                  "reasoning_details": [{"tip": "x"}]}]
        out = mesajlari_temizle(giris)
        assert out[0]["reasoning_content"] == "adim-adim"
        assert out[0]["reasoning_details"] == [{"tip": "x"}]
        assert out[0]["tool_calls"] == [{"id": "1"}]

    def test_reasoning_ayikla_bos_gecer(self):
        from brain.message_utils import reasoning_ayikla
        msg = types.SimpleNamespace(content="s", tool_calls=None)
        assert reasoning_ayikla(msg) == {}
        msg2 = types.SimpleNamespace(content="s",
                                     reasoning_content="dusundum")
        assert reasoning_ayikla(msg2) == {"reasoning_content": "dusundum"}

    def test_glm_reasoning_dondurur(self):
        from brain import glm as _glm

        class Msg:
            content = "selam"
            tool_calls = None
            reasoning_content = "muhakeme"

        class Choice:
            message = Msg()

        class Comp:
            def create(self, **kw):
                assert kw["extra_body"] == {"thinking": {"type": "enabled"}}
                return types.SimpleNamespace(choices=[Choice()], usage=None)

        class Chat:
            completions = Comp()

        class Client:
            chat = Chat()

        istemci = _glm.GLMClient.__new__(_glm.GLMClient)
        istemci.client = Client()
        istemci.model = "glm-4.7-flash"
        out = istemci.cevapla([{"role": "user", "content": "s"}])
        assert out["content"] == "selam"
        assert out["reasoning_content"] == "muhakeme"

    def test_arac_dongusu_assistant_reasoning_korur(self):
        from chat.tools import arac_dongusu
        gorulen = []

        class Beyin:
            def cevapla(self, mesajlar, model, tools=None):
                gorulen.append(list(mesajlar))
                return {"content": "bitti"}, "x"

        out, kosan = arac_dongusu(
            [{"id": "c1", "type": "function",
              "function": {"name": "list_tasks", "arguments": "{}"}}],
            [{"role": "user", "content": "sor"}],
            Beyin(), None, lambda kod: None,
            lambda ad, args: {"result": "tamam"},
            tools=[{"type": "function",
                    "function": {"name": "list_tasks"}}],
            yanit={"tool_calls": [{"id": "c1"}],
                   "reasoning_content": "ilk-muhakeme"})
        assert out == "bitti" and kosan == 1
        asistan = [m for m in gorulen[0]
                   if m.get("role") == "assistant"][0]
        assert asistan["tool_calls"][0]["id"] == "c1"
        assert asistan["reasoning_content"] == "ilk-muhakeme"


class TestCiftDusunmeYok:
    def _akim(self, parcalar):
        class Delta:
            def __init__(self, content=None, tools=None):
                self.content = content
                self.tool_calls = tools

        class TC:
            def __init__(self, idx, tid, name, args):
                self.index = idx
                self.id = tid
                self.function = types.SimpleNamespace(
                    name=name, arguments=args)

        class Chunk:
            def __init__(self, delta):
                self.choices = [types.SimpleNamespace(delta=delta)]

        class Comp:
            def create(self, **kw):
                assert kw.get("tools") is not None
                out = []
                for p in parcalar:
                    if isinstance(p, tuple):
                        out.append(Chunk(Delta(
                            tools=[TC(0, p[0], p[1], p[2])])))
                    else:
                        out.append(Chunk(Delta(content=p)))
                return out

        class Chat:
            completions = Comp()

        class Client:
            chat = Chat()
        return Client()

    def test_akit_tool_call_biriktirir(self):
        from brain.yayin import akit, AracIstegi
        client = self._akim([("call_1", "list_tasks", "{}")])
        try:
            list(akit(client, "m", [{"role": "user", "content": "s"}],
                       tools=[{"type": "function"}]))
            assert False, "AracIstegi bekleniyordu"
        except AracIstegi as e:
            assert e.tool_calls[0]["function"]["name"] == "list_tasks"
            assert e.tool_calls[0]["id"] == "call_1"

    def test_akit_parcali_arguman_birlestirir(self):
        from brain.yayin import akit, AracIstegi
        from brain.yayin import akit as _akit

        class Delta:
            def __init__(self, tools):
                self.content = None
                self.tool_calls = tools

        class TC:
            def __init__(self, idx, tid, name, args):
                self.index = idx
                self.id = tid
                self.function = types.SimpleNamespace(
                    name=name, arguments=args)

        class Chunk:
            def __init__(self, d):
                self.choices = [types.SimpleNamespace(delta=d)]

        class Comp:
            def create(self, **kw):
                return [Chunk(Delta([TC(0, "c1", "add_task", '{"text":')])) ,
                        Chunk(Delta([TC(0, None, "", ' "sut"}')]))]

        class Chat:
            completions = Comp()

        class Client:
            chat = Chat()

        try:
            list(_akit(Client(), "m",
                       [{"role": "user", "content": "s"}], tools=[{}]))
            assert False
        except Exception as e:
            from brain.yayin import AracIstegi as _A
            assert isinstance(e, _A)
            assert '"sut"' in e.tool_calls[0]["function"]["arguments"]

    def test_flow_akistaki_araci_dogrudan_calistirir(self, tmp_path,
                                                      monkeypatch):
        from chat import flow as _flow
        from chat import context as _ctx
        from brain.yayin import AracIstegi
        # AGENTS §0: ilk turda yalniz yetenek_ac acik; model once alani acar.
        karar = [{"id": "c1", "type": "function",
                  "function": {"name": "yetenek_ac",
                               "arguments": '{"alanlar": ["gorevler"]}'}}]
        ikinci = [{"id": "c9", "type": "function",
                   "function": {"name": "list_tasks", "arguments": "{}"}}]

        # Gercek gecmis/hafiza kullanma (yavas + kirilgan).
        monkeypatch.setattr(_ctx, "HISTORY_FILE", str(tmp_path / "g.json"))
        monkeypatch.setattr(_ctx, "ilgili_anilar", lambda sorgu, limit=20: [])
        monkeypatch.setattr(_ctx, "hafiza_al", lambda: None)
        monkeypatch.setattr(_ctx, "gecmis_pencere", lambda g, *a, **k: [])
        monkeypatch.setattr(_ctx, "temizle_history", lambda g: list(g or []))
        monkeypatch.setattr(_ctx, "kaydet", lambda p, v: None)
        monkeypatch.setattr(_ctx, "onem_puanla", lambda t: 1)
        try:
            from chat import oturum as _oturum
            monkeypatch.setattr(_oturum, "kaydet_cift",
                                lambda *a, **k: "test")
        except Exception:
            pass

        class Beyin:
            def bulut_musait(self):
                return True

            def cevapla_yayin(self, mesajlar, model, tools=None):
                yield "glm", "parca"
                raise AracIstegi(tool_calls=karar,
                                 muhakeme={"reasoning_content": "m"})

            def cevapla(self, mesajlar, model, tools=None):
                # Arac sonucu sonrasi devam — karar icin ikinci dusunme
                # DEGIL, zincirin devami. Akistaki muhakeme korunur.
                asistanlar = [m for m in mesajlar
                              if m.get("role") == "assistant"
                              and m.get("tool_calls")]
                assert asistanlar, "tool_calls tasiyan assistant yok"
                assert asistanlar[0].get("tool_calls") == karar
                assert asistanlar[0].get("reasoning_content") == "m"
                tool = [m for m in mesajlar if m.get("role") == "tool"]
                if tool[-1]["tool_call_id"] == "c1":
                    return {"tool_calls": ikinci}, "glm"
                assert tool[-1]["tool_call_id"] == "c9"
                return {"content": "ozet"}, "glm"

        cagrilar = []

        def calistir(ad, args):
            cagrilar.append(ad)
            return {"result": "tamam"}

        import chat.tools as _tools
        _eski = _tools.calistir if hasattr(_tools, "calistir") else None
        msgs = []
        try:
            import tools as _tmod
            _gercek = _tmod.calistir
            _tmod.calistir = calistir
            _flow.mesaj_isle(
                "gorevler ne", Beyin(), "sistem",
                lambda kod: msgs.append(kod),
                tools=[{"type": "function",
                        "function": {"name": "list_tasks"}}])
        finally:
            _tmod.calistir = _gercek
        assert cagrilar == ["list_tasks"]
        assert any("ozet" in m for m in msgs)


class TestCohereNative:
    def test_tool_mesaji_usera_cevrilmez(self):
        from brain import cohere as _cohere
        yakalanan = {}

        class SahteResp:
            message = types.SimpleNamespace(content="tamam",
                                            tool_calls=None)

        class SahteClient:
            def chat(self, **kwargs):
                yakalanan.update(kwargs)
                return SahteResp()

        istemci = _cohere.CohereClient.__new__(_cohere.CohereClient)
        istemci.client = SahteClient()
        istemci.model = "command-a-03-2025"
        out = istemci.cevapla([
            {"role": "user", "content": "sor"},
            {"role": "assistant", "content": "",
             "tool_calls": [{"id": "c1", "type": "function",
                             "function": {"name": "list_tasks",
                                          "arguments": "{}"}}]},
            {"role": "tool", "tool_call_id": "c1", "name": "list_tasks",
             "content": "sonuc"},
        ])
        assert out["content"] == "tamam"
        roller = [m["role"] for m in yakalanan["messages"]]
        assert roller == ["user", "assistant", "tool"]
        assert yakalanan["messages"][2]["tool_call_id"] == "c1"
        assert yakalanan["messages"][1]["tool_calls"][0]["id"] == "c1"


class TestGorevTarihi:
    def test_keyword_tarih_cikarmaz(self, tmp_path):
        from tools import tasks as _tasks
        dosya = str(tmp_path / "g.json")
        out = _tasks.add_task("yarin sut al", dosya)
        assert "error" not in out
        gorevler = _tasks._yukle(dosya)
        # Cumle aynen durur; kod "yarin"i silip tarih uydurmaz.
        assert gorevler[0]["text"] == "yarin sut al"

    def test_acik_date_dogrulanir(self, tmp_path):
        from tools import tasks as _tasks
        dosya = str(tmp_path / "g.json")
        out = _tasks.add_task("sut al", dosya, date="2026-09-20")
        assert "error" not in out
        assert _tasks._yukle(dosya)[0]["date"] == "2026-09-20"
        kotu = _tasks.add_task("sut al", dosya, date="20/09/2026")
        assert "error" in kotu


class TestEpisodikMaske:
    def test_sifre_episodige_aynen_girmez(self, tmp_path):
        from memory.engine import HafizaMotoru
        m = HafizaMotoru(db_yolu=str(tmp_path / "m.db"),
                         embed_fn=lambda t: None)
        assert m.episodik_kaydet("sifrem: gizli123", "tamam") is True
        metin = m.conn.execute(
            "SELECT text FROM memories").fetchone()[0]
        assert "gizli123" not in metin
        assert "***" in metin

    def test_normal_sohbet_maskelenmez(self, tmp_path):
        from memory.engine import HafizaMotoru
        m = HafizaMotoru(db_yolu=str(tmp_path / "m.db"),
                         embed_fn=lambda t: None)
        m.episodik_kaydet("bugun hava guzel", "evet guzel")
        metin = m.conn.execute(
            "SELECT text FROM memories").fetchone()[0]
        assert "bugun hava guzel" in metin
