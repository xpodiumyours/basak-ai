"""Provider-neutral ajan runtime icin kotasiz birim testler."""

import inspect
import types

import pytest


def _call(ad, args="{}", cid="c1"):
    return {
        "id": cid,
        "type": "function",
        "function": {"name": ad, "arguments": args},
    }


def test_53_arac_namespace_metadata_tam_katalogu_kapsar():
    from tools.capabilities import validate_registry
    from tools.definitions import TOOLS, TANINMIS_TOOLLAR
    sonuc = validate_registry(TOOLS)
    assert sonuc == {
        "ok": True, "tool_count": 53, "namespace_count": 10,
        "missing": [], "unknown": [], "duplicates": [],
    }
    assert len(TANINMIS_TOOLLAR) == 53

def test_auto_policy_tam_53_gercek_araci_modele_verir():
    from chat.agent_runtime import capability_surface
    from tools.definitions import TOOLS
    assert capability_surface(TOOLS, "auto") == TOOLS
    assert capability_surface(TOOLS, "required") == TOOLS
    assert capability_surface(TOOLS, "none") == []

def test_namespace_metadata_runtime_kapisi_degildir():
    from chat.agent_runtime import capability_surface
    from tools.capabilities import CAPABILITY_NAMESPACES, namespace_schemas
    from tools.definitions import TOOLS
    assert max(len(x) for x in CAPABILITY_NAMESPACES.values()) <= 11
    assert len(namespace_schemas("internet", TOOLS)) == 11
    assert len(capability_surface(TOOLS, "auto")) == 53

def test_ajan_sozlesmesi_kelime_routeri_degildir():
    from chat.agent_runtime import AGENT_CONTRACT
    for ad in ("web_search", "fatura_oku", "github_durum", "list_tasks"):
        assert ad not in AGENT_CONTRACT
    assert "gercek capability registry" in AGENT_CONTRACT.lower()

def test_meta_son_cevap_gercek_arac_degildir_ve_kosmaz():
    from chat.tools import arac_dongusu
    from tools.definitions import TOOLS
    kosulan = []
    class Beyin:
        def cevapla_yayin(self, *a, **k):
            from brain.yayin import SonHata
            raise SonHata("testte stream yok")
            yield
        def cevapla(self, mesajlar, model, tools=None, **kwargs):
            return {"content": "meta arac reddedildi"}, "groq"
    cevap, kosan = arac_dongusu(
        [_call("son_cevap", '{"metin":"uydurma"}')],
        [{"role": "user", "content": "merhaba"}],
        Beyin(), None, lambda kod: None,
        lambda ad, args: kosulan.append(ad) or {"result": "x"},
        tools=TOOLS, tool_choice="auto",
    )
    assert kosulan == []
    assert kosan == 0
    assert cevap == "meta arac reddedildi"

def test_model_gercek_araci_dogrudan_secer():
    from chat.tools import arac_dongusu
    from tools.definitions import TOOLS
    kosulan = []
    class Beyin:
        def cevapla_yayin(self, *a, **k):
            from brain.yayin import SonHata
            raise SonHata("testte stream yok")
            yield
        def cevapla(self, mesajlar, model, tools=None, tool_choice=None, **kwargs):
            assert tool_choice == "auto"
            assert len(tools) == 53
            return {"content": "1 gorev var."}, "groq"
    cevap, kosan = arac_dongusu(
        [_call("list_tasks", "{}", "c1")],
        [{"role": "user", "content": "gorevlerime bak"}],
        Beyin(), None, lambda kod: None,
        lambda ad, args: kosulan.append(ad) or {"result": "1: sut al"},
        tools=TOOLS, tool_choice="auto",
    )
    assert kosulan == ["list_tasks"]
    assert kosan == 1
    assert cevap == "1 gorev var."

def test_run_yuzeyinde_olmayan_gercek_arac_calistirilmaz():
    from chat.tools import arac_dongusu
    list_tasks = {"type": "function", "function": {
        "name": "list_tasks", "description": "x",
        "parameters": {"type": "object", "properties": {}}}}
    kosulan = []
    class Beyin:
        def cevapla_yayin(self, *a, **k):
            from brain.yayin import SonHata
            raise SonHata("testte stream yok")
            yield
        def cevapla(self, mesajlar, model, tools=None, **kwargs):
            return {"content": "reddedildi"}, "groq"
    cevap, kosan = arac_dongusu(
        [_call("web_search", '{"query":"x"}')],
        [{"role": "user", "content": "x"}],
        Beyin(), None, lambda kod: None,
        lambda ad, args: kosulan.append(ad) or {"result": "x"},
        tools=[list_tasks], tool_choice="auto",
    )
    assert kosulan == []
    assert kosan == 0
    assert cevap == "reddedildi"

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


# 2026-09-22: Mistral eklendi (Yol 1). glhf ayni gun olu ciktigi (HTTP
# 522) icin tamamen kaldirildi; listedeki 9 ucretsizdir: ucretsiz + tool
# destekli + ajan protokolune uygun. Sira sondadir cunku canli olcumu bekliyor.
AJAN_SAGLAYICILARI = (
    "groq", "gemini", "cloudflare", "kilo",
    "nvidia", "glm", "openrouter", "cohere",
    "mistral",
)


def test_registry_9_ucretsiz_saglayicinin_tamamini_ajan_olarak_tanimlar():
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
    # KAPALI kartlar: anahtar yazilsa bile otomatik zincire GIRMEZLER.
    # Hugging Face ucretsiz kredisi ayda 0,10 dolar; Chutes ucretlidir.
    assert registry.otomatik_ucretsiz_mi("huggingface") is False
    assert registry.otomatik_ucretsiz_mi("chutes") is False


def test_9_saglayici_resmi_tool_choice_haritasi():
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
        # 2026-09-22: Mistral da auto_enforced — resmi API auto tool-calling
        # destekler; Basak ajan turunda duz metni basari saymaz.
        # (glhf ayni gun olu cikti, cikarildi.)
        "mistral": "auto",
    }
    assert {ad: registry.ajan_tool_choice(ad)
            for ad in AJAN_SAGLAYICILARI} == beklenen


def test_tum_istemcinin_tool_choice_parametresini_kabul_ediyor():
    from brain.groq import GroqClient
    from brain.gemini import GeminiClient
    from brain.openrouter import OpenRouterClient
    from brain.glm import GLMClient
    from brain.cloudflare import CloudflareClient
    from brain.cohere import CohereClient
    from brain.kilo import KiloClient
    from brain.nvidia import NvidiaClient
    # 2026-09-22: Mistral, Hugging Face ve Chutes ayni genel
    # istemciyi (GenelClient) kullanir. Bu parametre bir kez eksikti ve
    # arac kullanan her cagriyi TypeError ile kiriyordu; test artik kapsar.
    # (glhf'ye ait kod olu oldugu icin kaldirildi.)
    from brain.genel import GenelClient

    siniflar = (
        GroqClient, GeminiClient, OpenRouterClient, GLMClient,
        CloudflareClient, CohereClient, KiloClient, NvidiaClient,
        GenelClient,
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
               "cloudflare", "cohere", "qwen", "genel",
               "mistral", "huggingface", "chutes"):
        setattr(b, "_" + ad, Saglayici())

    adlar = [ad for ad, _ in b._bulut_zinciri()]
    assert "genel" not in adlar
    assert "qwen" not in adlar
    assert "groq" in adlar
    # 2026-09-22: kartlari KAPALI oldugu icin istemci kurulu olsa da girmez.
    assert "huggingface" not in adlar
    assert "chutes" not in adlar
    # Bedava olan yeni platform girer.
    assert "mistral" in adlar


def test_ajan_zinciri_9_ucretsiz_saglayicinin_tamamini_kapsar():
    from brain.brain import Brain

    class Saglayici:
        def musait(self):
            return True

    b = Brain.__new__(Brain)
    for ad in ("groq", "gemini", "glm", "nvidia", "kilo", "openrouter",
               "cloudflare", "cohere", "qwen", "genel",
               "mistral", "huggingface", "chutes"):
        setattr(b, "_" + ad, Saglayici())

    adlar = [ad for ad, _ in b._bulut_zinciri(
        tools=True, tool_required=True)]
    assert set(adlar) == set(AJAN_SAGLAYICILARI)
    assert len(adlar) == 9


def test_9_saglayici_x_53_gercek_arac_dogrudan_ajan_yolunda_erisebilir():
    from chat.tools import arac_dongusu
    from tools.definitions import TOOLS
    araclar = [t["function"]["name"] for t in TOOLS]
    sayac = 0
    for provider in AJAN_SAGLAYICILARI:
        for hedef in araclar:
            class Beyin:
                def cevapla_yayin(self, *a, **k):
                    from brain.yayin import SonHata
                    raise SonHata("testte stream yok")
                    yield
                def cevapla(self, mesajlar, model, tools=None, tool_choice=None, **kwargs):
                    assert tool_choice == "auto"
                    assert len(tools) == 53
                    return {"content": "tamam"}, provider
            kosulan = []
            cevap, kosan = arac_dongusu(
                [_call(hedef, "{}", "gercek")],
                [{"role": "user", "content": "dogrulama"}],
                Beyin(), None, lambda kod: None,
                lambda ad, args: kosulan.append(ad) or {"result": "ok"},
                tools=TOOLS, tool_choice="auto",
            )
            assert kosulan == [hedef], (provider, hedef)
            assert kosan == 1
            assert cevap == "tamam"
            sayac += 1
    assert sayac == 9 * 53

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

    assert len(adlar) == 53
    assert len(set(adlar)) == 53


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
    assert len(dallar) == 53


def test_10_namespace_53_araci_eksiksiz_tasir():
    from tools.capabilities import CAPABILITY_NAMESPACES
    from tools.definitions import TANINMIS_TOOLLAR
    assert len(CAPABILITY_NAMESPACES) == 10
    duz = [ad for araclar in CAPABILITY_NAMESPACES.values() for ad in araclar]
    assert len(duz) == 53
    assert len(set(duz)) == 53
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
