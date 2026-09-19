"""Gercek ajan protokolu icin kotasiz birim testler."""

import inspect
import types

import pytest


def _call(ad, args="{}", cid="c1"):
    return {
        "id": cid,
        "type": "function",
        "function": {"name": ad, "arguments": args},
    }


def test_52_aracin_tamami_tek_yetenek_alaninda():
    from tools.definitions import TOOLS, TANINMIS_TOOLLAR
    from chat.agent_protocol import YETENEK_ALANLARI

    gercek = [t["function"]["name"] for t in TOOLS]
    katalog = [ad for grup in YETENEK_ALANLARI.values() for ad in grup]
    assert len(gercek) == 52
    assert len(TANINMIS_TOOLLAR) == 52
    assert len(katalog) == 52
    assert len(set(katalog)) == 52
    assert set(katalog) == set(gercek)


def test_ilk_turda_52_arac_modele_yigilmaz():
    from chat.agent_protocol import (
        baslangic_araclari, YETENEK_AC_ADI, SON_CEVAP_ADI,
    )

    adlar = [x["function"]["name"] for x in baslangic_araclari()]
    assert adlar == [YETENEK_AC_ADI, SON_CEVAP_ADI]


def test_tek_alan_en_faz_12_sema_tasir():
    from tools.definitions import TOOLS
    from chat.agent_protocol import YETENEK_ALANLARI, alan_araclari

    for alan in YETENEK_ALANLARI:
        secilen = alan_araclari(TOOLS, alan)
        # En buyuk alan 10 gercek arac + 2 kontrol araci.
        assert len(secilen) <= 12, (alan, len(secilen))


def test_ajan_sozlesmesi_kelime_routeri_degildir():
    from chat.agent_protocol import AJAN_SOZLESMESI

    for ad in ("web_search", "fatura_oku", "github_durum", "list_tasks"):
        assert ad not in AJAN_SOZLESMESI
    assert "kelime eslestirmesi" in AJAN_SOZLESMESI.lower()


def test_son_cevap_gercek_arac_calistirmadan_donguyu_bitirir():
    from chat.tools import arac_dongusu
    from chat.agent_protocol import SON_CEVAP_ADI

    class Beyin:
        def cevapla(self, *args, **kwargs):
            raise AssertionError("finalden sonra modele donulmemeli")

    def calistir(*args, **kwargs):
        raise AssertionError("son_cevap gercek arac degil")

    cevap, kosan = arac_dongusu(
        [_call(SON_CEVAP_ADI, '{"metin":"Tamamlandi."}')],
        [{"role": "user", "content": "merhaba"}],
        Beyin(), None, lambda kod: None, calistir,
        tools=[], tool_choice="required",
    )
    assert cevap == "Tamamlandi."
    assert kosan == 0


def test_model_yetenegi_acar_sonra_gercek_araci_kendi_secer():
    from chat.tools import arac_dongusu
    from tools.definitions import TOOLS
    from chat.agent_protocol import (
        YETENEK_AC_ADI, SON_CEVAP_ADI, baslangic_araclari,
    )

    gorulen = []
    class Beyin:
        def cevapla(self, mesajlar, model, tools=None, tool_choice=None):
            assert tool_choice == "required"
            adlar = [t["function"]["name"] for t in tools]
            gorulen.append(adlar)
            if len(gorulen) == 1:
                assert "list_tasks" in adlar
                assert "web_search" not in adlar
                return {"tool_calls": [_call("list_tasks", "{}", "c2")]}, "groq"
            assert len(gorulen) == 2
            return {"tool_calls": [
                _call(SON_CEVAP_ADI, '{"metin":"1 gorev var."}', "c3")
            ]}, "groq"

    kosulan = []
    cevap, kosan = arac_dongusu(
        [_call(YETENEK_AC_ADI, '{"alan":"gorevler"}')],
        [{"role": "user", "content": "gorevlerime bak"}],
        Beyin(), None, lambda kod: None,
        lambda ad, args: kosulan.append(ad) or {"result": "1: sut al"},
        tools=baslangic_araclari(), tool_choice="required", tum_tools=TOOLS,
    )
    assert kosulan == ["list_tasks"]
    assert kosan == 1
    assert cevap == "1 gorev var."


def test_acilmamis_gercek_arac_calistirilmaz():
    from chat.tools import arac_dongusu
    from tools.definitions import TOOLS
    from chat.agent_protocol import baslangic_araclari

    class Beyin:
        def cevapla(self, mesajlar, model, tools=None, tool_choice=None):
            # Hata sonucu modele geri donunce final yerine yine duz metin
            # donerse required kapi bunu kabul etmez.
            return {"content": "olmaz"}, "groq"

    kosulan = []
    cevap, kosan = arac_dongusu(
        [_call("list_tasks")],
        [{"role": "user", "content": "gorevler"}],
        Beyin(), None, lambda kod: None,
        lambda ad, args: kosulan.append(ad) or {"result": "x"},
        tools=baslangic_araclari(), tool_choice="required", tum_tools=TOOLS,
    )
    assert kosulan == []
    assert kosan == 0
    assert cevap == ""


def test_required_ajan_duz_metni_final_saymaz():
    from chat.tools import arac_dongusu

    class Beyin:
        def cevapla(self, mesajlar, model, tools=None, tool_choice=None):
            assert tool_choice == "required"
            return {"content": "Araci kullandim, bitti."}, "groq"

    cevap, kosan = arac_dongusu(
        [_call("list_tasks")],
        [{"role": "user", "content": "gorevleri kontrol et"}],
        Beyin(), None, lambda kod: None,
        lambda ad, args: {"result": "1: sut al"},
        tools=[{"type": "function",
                "function": {"name": "list_tasks"}}],
        tool_choice="required",
    )
    assert kosan == 1
    assert cevap == ""


AJAN_SAGLAYICILARI = (
    "groq", "gemini", "openrouter", "glm",
    "cloudflare", "cohere", "kilo", "nvidia",
)


def test_registry_8_ucretsiz_saglayicinin_tamamini_ajan_olarak_tanimlar():
    from brain import registry

    assert tuple(registry.VARSAYILAN_SIRA) == AJAN_SAGLAYICILARI
    for ad in AJAN_SAGLAYICILARI:
        assert registry.otomatik_ucretsiz_mi(ad) is True
        assert registry.tool_destegi_var_mi(ad) is True
        assert registry.ajan_destegi_var_mi(ad) is True

    assert registry.ajan_destegi_var_mi("qwen") is False
    assert registry.ajan_destegi_var_mi("genel") is False
    assert registry.ajan_destegi_var_mi("deepseek") is False
    assert registry.ajan_destegi_var_mi("kimi") is False


def test_8_saglayici_resmi_tool_choice_haritasi():
    from brain import registry

    beklenen = {
        # 2026-09-19 Duzey 1 kaniti: groq -> auto_enforced.
        "groq": "auto",
        "gemini": "auto",
        "openrouter": "auto",
        "glm": "auto",
        "cloudflare": "required",
        "cohere": "required",
        "kilo": "required",
        "nvidia": "auto",
    }
    assert {ad: registry.ajan_tool_choice(ad)
            for ad in AJAN_SAGLAYICILARI} == beklenen


def test_8_istemcinin_tamami_tool_choice_parametresini_kabul_ediyor():
    from brain.groq import GroqClient
    from brain.gemini import GeminiClient
    from brain.openrouter import OpenRouterClient
    from brain.glm import GLMClient
    from brain.cloudflare import CloudflareClient
    from brain.cohere import CohereClient
    from brain.kilo import KiloClient
    from brain.nvidia import NvidiaClient

    siniflar = (
        GroqClient, GeminiClient, OpenRouterClient, GLMClient,
        CloudflareClient, CohereClient, KiloClient, NvidiaClient,
    )
    for cls in siniflar:
        assert "tool_choice" in inspect.signature(cls.cevapla).parameters, cls


@pytest.mark.parametrize(
    "provider,beklenen",
    [
        # 2026-09-19 Duzey 1 kaniti: groq gpt-oss required altinda 400
        # veriyor, auto'da dogal tool_call uretiyor -> auto_enforced.
        ("groq", "auto"),
        ("gemini", "auto"),
        ("openrouter", "auto"),
        ("glm", "auto"),
        ("cloudflare", "required"),
        ("cohere", "required"),
        ("kilo", "required"),
        ("nvidia", "auto"),
    ],
)
def test_brain_required_sozlesmesini_saglayici_protokolune_cevirir(
        provider, beklenen):
    from brain.brain import Brain

    gorulen = {}

    class Istemci:
        def cevapla(self, messages, tools=None, yapi=None, tool_choice=None):
            gorulen["tool_choice"] = tool_choice
            return {"tool_calls": [_call("x")]}

    b = Brain.__new__(Brain)
    b._tek_cagri(
        Istemci(), provider,
        [{"role": "user", "content": "x"}],
        [{"type": "function", "function": {"name": "x"}}],
        None, None, tool_choice="required",
    )
    assert gorulen["tool_choice"] == beklenen


def test_groq_required_apiye_tasinir():
    from brain.groq import GroqClient
    yakalanan = {}

    class Comp:
        def create(self, **kwargs):
            yakalanan.update(kwargs)
            msg = types.SimpleNamespace(content="x", tool_calls=None)
            return types.SimpleNamespace(
                choices=[types.SimpleNamespace(message=msg)], usage=None)

    istemci = GroqClient.__new__(GroqClient)
    istemci.client = types.SimpleNamespace(
        chat=types.SimpleNamespace(completions=Comp()))
    istemci.model = "openai/gpt-oss-120b"

    istemci.cevapla(
        [{"role": "user", "content": "s"}],
        tools=[{"type": "function", "function": {"name": "x"}}],
        tool_choice="required",
    )
    assert yakalanan["tool_choice"] == "required"


def test_cohere_required_native_apiye_tasinir():
    from brain.cohere import CohereClient
    yakalanan = {}

    class Client:
        def chat(self, **kwargs):
            yakalanan.update(kwargs)
            msg = types.SimpleNamespace(content="tamam", tool_calls=None)
            return types.SimpleNamespace(message=msg, usage=None)

    istemci = CohereClient.__new__(CohereClient)
    istemci.client = Client()
    istemci.model = "command-a-03-2025"

    istemci.cevapla(
        [{"role": "user", "content": "s"}],
        tools=[{"type": "function",
                "function": {
                    "name": "x", "description": "x",
                    "parameters": {"type": "object", "properties": {}}}}],
        tool_choice="required",
    )
    assert yakalanan["tool_choice"] == "REQUIRED"



def test_cloudflare_required_apiye_tasinir():
    from brain.cloudflare import CloudflareClient
    yakalanan = {}

    class Comp:
        def create(self, **kwargs):
            yakalanan.update(kwargs)
            msg = types.SimpleNamespace(content="x", tool_calls=None)
            return types.SimpleNamespace(
                choices=[types.SimpleNamespace(message=msg)], usage=None)

    istemci = CloudflareClient.__new__(CloudflareClient)
    istemci.client = types.SimpleNamespace(
        chat=types.SimpleNamespace(completions=Comp()))
    istemci.model = "@cf/zai-org/glm-4.7-flash"

    istemci.cevapla(
        [{"role": "user", "content": "s"}],
        tools=[{"type": "function", "function": {"name": "x"}}],
        tool_choice="required",
    )
    assert yakalanan["tool_choice"] == "required"



def test_bilinmeyen_saglayici_fail_closed():
    from brain import registry

    k = registry.kart("gelecekteki_bilinmeyen")
    assert k["ucretsiz"] is False
    assert k["tools"] is False
    assert registry.otomatik_ucretsiz_mi("gelecekteki_bilinmeyen") is False


def test_qwen_sureli_kota_otomatik_zincirde_degil():
    from brain import registry

    assert registry.kart("qwen")["ucretsiz"] is True
    assert registry.otomatik_ucretsiz_mi("qwen") is False
    assert "qwen" not in registry.VARSAYILAN_SIRA


def test_otomatik_bulut_zinciri_ucretli_ve_qwen_sokmaz():
    from brain.brain import Brain

    class Saglayici:
        def musait(self):
            return True

    b = Brain.__new__(Brain)
    for ad in ("groq", "gemini", "glm", "nvidia", "kilo", "openrouter",
               "cloudflare", "cohere", "qwen", "genel"):
        setattr(b, "_" + ad, Saglayici())

    adlar = [ad for ad, _ in b._bulut_zinciri()]
    assert "genel" not in adlar
    assert "qwen" not in adlar
    assert "groq" in adlar


def test_ajan_zinciri_8_ucretsiz_saglayicinin_tamamini_kapsar():
    from brain.brain import Brain

    class Saglayici:
        def musait(self):
            return True

    b = Brain.__new__(Brain)
    for ad in ("groq", "gemini", "glm", "nvidia", "kilo", "openrouter",
               "cloudflare", "cohere", "qwen", "genel"):
        setattr(b, "_" + ad, Saglayici())

    adlar = [ad for ad, _ in b._bulut_zinciri(
        tools=True, tool_required=True)]
    assert set(adlar) == set(AJAN_SAGLAYICILARI)
    assert len(adlar) == 8


def test_52_arac_dort_yuz_on_alti_saglayici_arac_yolunda_erisebilir():
    """8 saglayici x 52 arac = 416 ajan yolu; kota kullanmaz."""
    from chat.agent_protocol import (
        YETENEK_AC_ADI, SON_CEVAP_ADI, YETENEK_ALANLARI,
        baslangic_araclari,
    )
    from chat.tools import arac_dongusu
    from tools.definitions import TOOLS

    araclar = [t["function"]["name"] for t in TOOLS]
    ters = {
        arac: alan
        for alan, alan_araclari in YETENEK_ALANLARI.items()
        for arac in alan_araclari
    }
    sayac = 0

    for provider in AJAN_SAGLAYICILARI:
        for hedef in araclar:
            alan = ters[hedef]
            turlar = {"n": 0}

            class Beyin:
                def cevapla(self, mesajlar, model, tools=None,
                            tool_choice=None):
                    assert tool_choice == "required"
                    adlar = [x["function"]["name"] for x in tools]
                    turlar["n"] += 1
                    if turlar["n"] == 1:
                        assert hedef in adlar, (provider, hedef, alan)
                        return {"tool_calls": [
                            _call(hedef, "{}", "gercek")
                        ]}, provider
                    return {"tool_calls": [
                        _call(SON_CEVAP_ADI,
                              '{"metin":"tamam"}', "final")
                    ]}, provider

            kosulan = []
            cevap, kosan = arac_dongusu(
                [_call(YETENEK_AC_ADI,
                       '{"alan":"%s"}' % alan, "alan")],
                [{"role": "user", "content": "dogrulama"}],
                Beyin(), None, lambda kod: None,
                lambda ad, args: (
                    kosulan.append(ad) or {"result": "ok"}),
                tools=baslangic_araclari(),
                tool_choice="required",
                tum_tools=TOOLS,
            )
            assert kosulan == [hedef], (provider, hedef)
            assert kosan == 1
            assert cevap == "tamam"
            sayac += 1

    assert sayac == 8 * 52



@pytest.mark.parametrize(
    "sinif_yolu,model,tool_choice",
    [
        ("brain.gemini.GeminiClient", "gemini-test", "auto"),
        ("brain.glm.GLMClient", "glm-test", "auto"),
        ("brain.openrouter.OpenRouterClient", "model:free", "auto"),
        ("brain.kilo.KiloClient", "kilo-auto/free", "required"),
    ],
)
def test_openai_uyumlu_ajan_istemcileri_tool_choice_http_istegine_yazar(
        sinif_yolu, model, tool_choice):
    import importlib

    modul_adi, sinif_adi = sinif_yolu.rsplit(".", 1)
    cls = getattr(importlib.import_module(modul_adi), sinif_adi)
    yakalanan = {}

    class Comp:
        def create(self, **kwargs):
            yakalanan.update(kwargs)
            msg = types.SimpleNamespace(content="", tool_calls=[
                types.SimpleNamespace(
                    id="c1",
                    function=types.SimpleNamespace(
                        name="x", arguments="{}"))
            ])
            return types.SimpleNamespace(
                choices=[types.SimpleNamespace(
                    message=msg, finish_reason="tool_calls")],
                usage=None)

    istemci = cls.__new__(cls)
    istemci.client = types.SimpleNamespace(
        chat=types.SimpleNamespace(completions=Comp()))
    istemci.model = model

    istemci.cevapla(
        [{"role": "user", "content": "s"}],
        tools=[{"type": "function", "function": {
            "name": "x",
            "parameters": {"type": "object", "properties": {}},
        }}],
        tool_choice=tool_choice,
    )
    assert yakalanan["tool_choice"] == tool_choice


def test_nvidia_ajan_istegi_auto_ve_gptoss20b_ile_gider():
    from brain.nvidia import NvidiaClient, GPTOSS_MODEL

    yakalanan = {}

    class Comp:
        def create(self, **kwargs):
            yakalanan.update(kwargs)
            msg = types.SimpleNamespace(content="", tool_calls=[
                types.SimpleNamespace(
                    id="c1",
                    function=types.SimpleNamespace(
                        name="x", arguments="{}"))
            ])
            return types.SimpleNamespace(
                choices=[types.SimpleNamespace(
                    message=msg, finish_reason="tool_calls")],
                usage=None)

    istemci = NvidiaClient.__new__(NvidiaClient)
    istemci.client = types.SimpleNamespace(
        chat=types.SimpleNamespace(completions=Comp()))
    istemci.model = "baska-model"

    istemci.cevapla(
        [{"role": "user", "content": "s"}],
        tools=[{"type": "function", "function": {
            "name": "x",
            "parameters": {"type": "object", "properties": {}},
        }}],
        tool_choice="auto",
    )
    assert yakalanan["tool_choice"] == "auto"
    assert yakalanan["model"] == GPTOSS_MODEL


def test_openrouter_ajan_yetenegi_model_katalogundan_dogrulanir():
    from brain.openrouter import OpenRouterClient

    class Modeller:
        def list(self):
            return [
                types.SimpleNamespace(
                    id="iyi:free",
                    supported_parameters=["tools", "tool_choice"]),
                types.SimpleNamespace(
                    id="eksik:free",
                    supported_parameters=["tools"]),
            ]

    istemci = OpenRouterClient.__new__(OpenRouterClient)
    istemci.client = types.SimpleNamespace(models=Modeller())
    istemci.model = "iyi:free"
    assert istemci.ajan_musait() is True
    istemci.model = "eksik:free"
    assert istemci.ajan_musait() is False



def test_52_aracin_semasi_eksiksiz_ve_tutarlı():
    from tools.definitions import TOOLS

    adlar = []
    for arac in TOOLS:
        assert arac.get("type") == "function"
        fn = arac.get("function") or {}
        ad = fn.get("name")
        assert isinstance(ad, str) and ad
        adlar.append(ad)
        assert isinstance(fn.get("description"), str) and fn["description"]
        p = fn.get("parameters") or {}
        assert p.get("type") == "object", ad
        props = p.get("properties") or {}
        required = p.get("required") or []
        assert set(required).issubset(set(props)), (ad, required, props)

    assert len(adlar) == 52
    assert len(set(adlar)) == 52


def test_52_aracin_dispatcher_dali_birebir_var():
    """Her arac semasi tools.calistir icinde gercek bir dispatch dalina sahip."""
    import ast
    import textwrap

    import tools
    from tools.definitions import TANINMIS_TOOLLAR

    agac = ast.parse(textwrap.dedent(inspect.getsource(tools.calistir)))
    dallar = set()

    for dugum in ast.walk(agac):
        if not isinstance(dugum, ast.Compare):
            continue
        if len(dugum.ops) != 1 or not isinstance(dugum.ops[0], ast.Eq):
            continue
        sol = dugum.left
        sag = dugum.comparators[0]
        if (isinstance(sol, ast.Name) and sol.id == "tool_name"
                and isinstance(sag, ast.Constant)
                and isinstance(sag.value, str)):
            dallar.add(sag.value)
        elif (isinstance(sag, ast.Name) and sag.id == "tool_name"
              and isinstance(sol, ast.Constant)
              and isinstance(sol.value, str)):
            dallar.add(sol.value)

    assert dallar == set(TANINMIS_TOOLLAR)
    assert len(dallar) == 52


def test_10_yetenek_alani_52_araci_eksiksiz_tasir():
    from chat.agent_protocol import YETENEK_ALANLARI
    from tools.definitions import TANINMIS_TOOLLAR

    assert len(YETENEK_ALANLARI) == 10
    duz = [ad for araclar in YETENEK_ALANLARI.values() for ad in araclar]
    assert len(duz) == 52
    assert len(set(duz)) == 52
    assert set(duz) == set(TANINMIS_TOOLLAR)



def test_gemini3_thought_signature_tool_call_icinde_korunur():
    """Google OpenAI uyumlulugundaki extra_content imzasi kaybolamaz."""
    from brain.gemini import GeminiClient
    from brain.message_utils import mesajlari_temizle

    class Comp:
        def create(self, **kwargs):
            tc = types.SimpleNamespace(
                id="g1",
                function=types.SimpleNamespace(name="x", arguments="{}"),
                extra_content={
                    "google": {"thought_signature": "SIG-A"}
                },
            )
            msg = types.SimpleNamespace(content="", tool_calls=[tc])
            return types.SimpleNamespace(
                choices=[types.SimpleNamespace(message=msg)], usage=None)

    istemci = GeminiClient.__new__(GeminiClient)
    istemci.client = types.SimpleNamespace(
        chat=types.SimpleNamespace(completions=Comp()))
    istemci.model = "gemini-3-flash-preview"

    yanit = istemci.cevapla(
        [{"role": "user", "content": "s"}],
        tools=[{"type": "function", "function": {"name": "x"}}],
        tool_choice="auto",
    )
    tc = yanit["tool_calls"][0]
    assert tc["extra_content"]["google"]["thought_signature"] == "SIG-A"

    tarihce = mesajlari_temizle([{
        "role": "assistant",
        "content": "",
        "tool_calls": yanit["tool_calls"],
    }])
    assert (tarihce[0]["tool_calls"][0]["extra_content"]["google"]
            ["thought_signature"] == "SIG-A")


def test_cohere_v2_tool_sonucu_document_bloguna_cevrilir():
    """Cohere V2 resmi role=tool content bicimini korur."""
    from brain.cohere import CohereClient

    yakalanan = {}

    class Client:
        def chat(self, **kwargs):
            yakalanan.update(kwargs)
            msg = types.SimpleNamespace(
                content=[types.SimpleNamespace(text="tamam")],
                tool_calls=None,
            )
            return types.SimpleNamespace(message=msg, usage=None)

    istemci = CohereClient.__new__(CohereClient)
    istemci.client = Client()
    istemci.model = "command-a-03-2025"

    istemci.cevapla(
        [
            {"role": "user", "content": "s"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [_call("x", "{}", "c1")],
            },
            {
                "role": "tool",
                "tool_call_id": "c1",
                "name": "x",
                "content": '{"result":"ok"}',
            },
        ],
        tools=[{
            "type": "function",
            "function": {
                "name": "x",
                "description": "x",
                "parameters": {"type": "object", "properties": {}},
            },
        }],
        tool_choice="required",
    )

    tool_msg = next(
        m for m in yakalanan["messages"] if m["role"] == "tool")
    assert tool_msg["tool_call_id"] == "c1"
    assert tool_msg["content"] == [{
        "type": "document",
        "document": {"data": '{"result":"ok"}'},
    }]



def test_cohere_v2_tool_plan_cok_turlu_akista_korunur():
    """Cohere resmi state: assistant tool_plan + tool_calls geri donmeli."""
    from brain.cohere import CohereClient

    kayitlar = []

    class Client:
        def chat(self, **kwargs):
            kayitlar.append(kwargs)
            if len(kayitlar) == 1:
                tc = types.SimpleNamespace(
                    id="c1",
                    function=types.SimpleNamespace(name="x", arguments="{}"),
                )
                msg = types.SimpleNamespace(
                    content=[],
                    tool_calls=[tc],
                    tool_plan="Once x aracini kullanacagim.",
                )
            else:
                msg = types.SimpleNamespace(
                    content=[types.SimpleNamespace(text="tamam")],
                    tool_calls=None,
                    tool_plan=None,
                )
            return types.SimpleNamespace(message=msg, usage=None)

    istemci = CohereClient.__new__(CohereClient)
    istemci.client = Client()
    istemci.model = "command-a-03-2025"
    arac = [{
        "type": "function",
        "function": {
            "name": "x",
            "description": "x",
            "parameters": {"type": "object", "properties": {}},
        },
    }]

    ilk = istemci.cevapla(
        [{"role": "user", "content": "s"}],
        tools=arac, tool_choice="required")
    assert ilk["tool_plan"] == "Once x aracini kullanacagim."

    istemci.cevapla(
        [
            {"role": "user", "content": "s"},
            {
                "role": "assistant",
                "content": "",
                "tool_plan": ilk["tool_plan"],
                "tool_calls": ilk["tool_calls"],
            },
            {
                "role": "tool",
                "tool_call_id": "c1",
                "name": "x",
                "content": '{"result":"ok"}',
            },
        ],
        tools=arac, tool_choice="required")

    assistant = next(
        m for m in kayitlar[1]["messages"] if m["role"] == "assistant")
    assert assistant["tool_plan"] == "Once x aracini kullanacagim."
    assert assistant["tool_calls"][0]["id"] == "c1"
