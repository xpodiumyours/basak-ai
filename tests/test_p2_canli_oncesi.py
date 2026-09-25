"""P2 canlı öncesi 12-risk regresyon kapısı."""

import json
import types


def _tool(ad):
    return {
        "type": "function",
        "function": {
            "name": ad,
            "description": ad,
            "parameters": {"type": "object", "properties": {}},
        },
    }


def test_finish_reason_merkezi_tasinir():
    from brain.kullanim import kullanim_ekle
    resp = types.SimpleNamespace(
        choices=[types.SimpleNamespace(finish_reason="length")],
        usage=None,
    )
    y = kullanim_ekle({"content": "x"}, resp)
    assert y["_finish_reason"] == "length"


def test_context_modelden_mesaj_saklamaz():
    from chat import context as ctx
    g = [{"role": "user", "content": "x" * 5000} for _ in range(20)]
    asli = json.loads(json.dumps(g))
    pencere, bilgi = ctx.gecmis_model_penceresi(g)
    assert pencere == g
    assert bilgi["compact"] is False
    assert bilgi["atlanan_mesaj"] == 0
    assert g == asli


def test_sayfa_cursor_semasi_var():
    from tools.definitions import TOOLS
    d = {t["function"]["name"]: t for t in TOOLS}
    for ad in ("sayfa_oku", "derin_oku"):
        props = d[ad]["function"]["parameters"]["properties"]
        assert "baslangic" in props and "uzunluk" in props


def test_kaynaklar_yalniz_okunan_sayfa():
    from chat import tools as ct
    assert ct._KAYNAK_ARACLARI == {"sayfa_oku", "derin_oku"}
    assert ct._kaynaklari_cikar(
        "web_search", {"query": "x"},
        "Baslik\nhttps://aday.test/x\nmetin"
    ) == []
    assert ct._kaynaklari_cikar(
        "sayfa_oku",
        {"url": "https://okunan.test/x?token=gizli"},
        "icerik",
    ) == ["https://okunan.test/x"]


def test_preview_dsn_production_ile_ayni_olamaz(monkeypatch):
    import memory
    monkeypatch.setenv("VERCEL_ENV", "preview")
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("DATABASE_URL", "postgresql://prod/db")
    monkeypatch.setenv("BASAK_PREVIEW_DATABASE_URL", "postgresql://prod/db")
    assert memory.preview_hafiza_modu() == (
        "preview_dsn_rejected_same_as_production"
    )
    try:
        memory.HafizaMotoru(db_yolu="x.db")
        assert False, "ayni DSN reddedilmeliydi"
    except RuntimeError as e:
        assert "ayni olamaz" in str(e)


def test_output_marker_sessiz_kesilmeyi_engeller():
    from chat.output_control import kesik_mi
    assert kesik_mi({"_finish_reason": "length"})
    assert kesik_mi({"_finish_reason": "max_tokens"})
    assert not kesik_mi({"_finish_reason": "stop"})


def test_kesik_final_ham_kalir_ve_yapisal_durum_bildirir():
    from chat.output_control import kesik_cevabi_bildir

    olaylar = []

    class Js:
        def olay(self, tur, **veri):
            olaylar.append((tur, veri))

    cevap, kaynak, tamam = kesik_cevabi_bildir(
        {"content": "birinci", "_finish_reason": "length"},
        js_callback=Js(),
        tercih=["groq"],
    )
    assert cevap == "birinci"
    assert kaynak == "groq"
    assert tamam is False
    assert olaylar == [("truncated", {"reason": "length"})]

def test_gercek_provider_parcalari_ui_ya_aynen_akar():
    from chat.output_control import akan_final

    class Beyin:
        def cevapla_yayin(self, mesajlar, model, tercih=None, tools=None):
            assert tools is None
            yield "groq", "Mer"
            yield "groq", "haba"

    olaylar = []
    cevap, kaynak, tamam = akan_final(
        Beyin(), None, [{"role": "user", "content": "selam"}],
        olaylar.append,
    )
    assert cevap == "Merhaba"
    assert kaynak == "groq"
    assert tamam is True
    assert olaylar == [
        'BasakUI.parca("Mer")',
        'BasakUI.parca("haba")',
    ]


def test_ayni_tool_args_sonuc_ucuncu_kez_gercekten_kosmaz():
    from chat.tools import arac_dongusu

    def call(cid):
        return {
            "id": cid, "type": "function",
            "function": {"name": "list_tasks", "arguments": "{}"},
        }

    turlar = {"n": 0}
    gercek_kosum = {"n": 0}
    olaylar = []

    class Js:
        def __call__(self, kod):
            olaylar.append(("js", kod))
        def olay(self, tur, **veri):
            olaylar.append((tur, veri))

    class Beyin:
        def cevapla(self, mesajlar, model, tools=None, **kwargs):
            turlar["n"] += 1
            if turlar["n"] <= 2:
                return {"tool_calls": [call("c%d" % (turlar["n"] + 1))]}, "groq"
            return {"content": "döngüden çıktım"}, "groq"

    def calistir(ad, args):
        gercek_kosum["n"] += 1
        return {"result": "ayni"}

    cevap, kosan = arac_dongusu(
        [call("c1")],
        [{"role": "user", "content": "gorevleri kontrol et"}],
        Beyin(), None, Js(), calistir,
        tools=[_tool("list_tasks")],
        tool_choice="auto",
    )
    assert cevap == "döngüden çıktım"
    assert gercek_kosum["n"] == 2
    assert kosan == 2
    assert any(tur == "loopGuard" for tur, _ in olaylar)


def test_provider_degisim_olayi_gorunur():
    from chat.tools import arac_dongusu

    first = {
        "id": "c1", "type": "function",
        "function": {"name": "list_tasks", "arguments": "{}"},
    }
    olaylar = []

    class Js:
        def __call__(self, kod):
            pass
        def olay(self, tur, **veri):
            olaylar.append((tur, veri))

    class Beyin:
        def cevapla(self, mesajlar, model, tools=None, tercih=None, **kwargs):
            return {"content": "tamam"}, "gemini"

    cevap, _ = arac_dongusu(
        [first], [{"role": "user", "content": "x"}],
        Beyin(), None, Js(), lambda *_a: {"result": "ok"},
        tools=[_tool("list_tasks")], tool_choice="auto",
        tercih=["groq"],
    )
    assert cevap == "tamam"
    assert ("providerSwitch", {"onceki": "groq", "yeni": "gemini"}) in olaylar


def test_yonlendirme_baglami_backend_imzada_var():
    import inspect
    from chat.flow import mesaj_isle
    assert "yonlendirme_baglami" in inspect.signature(mesaj_isle).parameters


def test_live_matris_arac_sayisini_koddan_alir():
    from tests.live import matris_kosucu
    from tools import TOOLS
    assert len(matris_kosucu._hedef_araclar(False)) == len(TOOLS)
    assert len(TOOLS) == 53


def test_optional_agent_stream_native_tool_calli_kaybetmez():
    from chat.output_control import akan_ajan_adimi
    from brain.yayin import AracIstegi

    tc = {
        "id": "c1", "type": "function",
        "function": {"name": "web_search", "arguments": '{"query":"x"}'},
    }

    class Beyin:
        def cevapla_yayin(self, *a, **k):
            def _g():
                raise AracIstegi([tc], {"reasoning": "r"}, kaynak="gemini")
                yield
            return _g()

    yanit, kaynak, ok = akan_ajan_adimi(
        Beyin(), None, [{"role": "user", "content": "x"}],
        lambda _x: None, [_tool("web_search")],
    )
    assert ok is True
    assert kaynak == "gemini"
    assert yanit["tool_calls"] == [tc]
    assert yanit["reasoning"] == "r"


def test_provider_ozel_gemini_imzasi_failoverda_temizlenir():
    from brain.message_utils import mesajlari_temizle

    mesaj = {
        "role": "assistant",
        "content": "",
        "_provider": "gemini",
        "reasoning": "provider-ozel",
        "tool_calls": [{
            "id": "c1",
            "type": "function",
            "function": {"name": "web_search", "arguments": "{}"},
            "extra_content": {"google": {"thought_signature": "imza"}},
        }],
    }

    gemini = mesajlari_temizle([mesaj], provider="gemini")[0]
    assert gemini["tool_calls"][0]["extra_content"]["google"][
        "thought_signature"
    ] == "imza"
    assert gemini["reasoning"] == "provider-ozel"
    assert "_provider" not in gemini

    groq = mesajlari_temizle([mesaj], provider="groq")[0]
    assert "extra_content" not in groq["tool_calls"][0]
    assert "reasoning" not in groq
    assert groq["tool_calls"][0]["function"]["name"] == "web_search"


def test_preview_ayni_db_farkli_kullanici_ve_default_portla_da_reddedilir(
        monkeypatch):
    import memory

    monkeypatch.setenv("VERCEL_ENV", "preview")
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql://prod_user:s1@db.example.com/prod"
    )
    monkeypatch.setenv(
        "BASAK_PREVIEW_DATABASE_URL",
        "postgres://preview_user:s2@db.example.com:5432/prod",
    )
    assert memory.preview_hafiza_modu() == (
        "preview_dsn_rejected_same_as_production"
    )


def test_yonlendir_ui_resume_iddiasi_yapmaz():
    ekran = open("web/app.js", encoding="utf-8").read()
    assert (
        "Mevcut çalışma durduruldu · yeni yönle yeniden başlatılıyor."
        in ekran
    )


def test_full_test_p2_gercekten_p2_refini_hedefler():
    akis = open(
        ".github/workflows/basak-full-acceptance.yml", encoding="utf-8"
    ).read()
    assert "FULL TEST P2" in akis
    assert "preview/p2-arac-ara-profesyonel" in akis
    assert "MISTRAL_API_KEY" in akis

    from tests.live import github_full_acceptance as full
    from tests.live import matris_kosucu
    assert tuple(full.SAGLAYICILAR) == tuple(matris_kosucu.KAPSAM)


def test_p2_aktif_flow_hidden_resolver_kullanmaz():
    import inspect
    from chat import flow
    kaynak = inspect.getsource(flow.mesaj_isle)
    assert "arac_karari_coz" not in kaynak
    assert "tool_resolver" not in kaynak
    assert "capability_surface" in kaynak
    assert "ajan_tools = list(etkin_tools)" in kaynak


def test_auto_policy_ilk_turda_yalniz_yetenek_ac_sunar():
    # AGENTS §0: katalog modele tek seferde dokulmez; model alani acar.
    from chat.agent_protocol import baslangic_araclari
    from chat.flow import mesaj_isle
    from tools import TOOLS

    class Beyin:
        def bulut_musait(self): return True
        def ajan_musait(self): return True
        def cevapla_yayin(self, *a, **k):
            from brain.yayin import SonHata
            raise SonHata("testte stream yok")
            yield
        def cevapla(self, mesajlar, model, tools=None,
                    tool_choice=None, **kwargs):
            assert tool_choice == "auto"
            assert tools == baslangic_araclari()
            return {"content": "dogal final"}, "groq"

    olaylar = []
    mesaj_isle(
        "normal soru", Beyin(), "test", olaylar.append, TOOLS,
        misafir=True, gecmis_override=[], tool_policy="auto",
    )
    assert any(x.startswith("BasakUI.bitir(") for x in olaylar)


def test_required_policy_tool_call_olmadan_finali_reddeder():
    from chat.agent_protocol import baslangic_araclari
    from chat.flow import mesaj_isle
    from tools import TOOLS

    class Beyin:
        def bulut_musait(self): return True
        def ajan_musait(self): return True
        def cevapla(self, mesajlar, model, tools=None,
                    tool_choice=None, **kwargs):
            assert tool_choice == "required"
            assert tools == baslangic_araclari()
            return {"content": "aracsiz final"}, "groq"

    olaylar = []
    mesaj_isle(
        "arac zorunlu run", Beyin(), "test", olaylar.append, TOOLS,
        misafir=True, gecmis_override=[], tool_policy="required",
    )
    assert not any(x.startswith("BasakUI.bitir(") for x in olaylar)
    assert any(
        "required modunda" in x
        for x in olaylar if x.startswith("BasakUI.error(")
    )


def test_none_policy_arac_yuzeyini_tamamen_kapatir():
    from chat.agent_runtime import capability_surface
    from tools import TOOLS
    assert capability_surface(TOOLS, "none") == []
    assert len(capability_surface(TOOLS, "auto")) == 53
    assert len(capability_surface(TOOLS, "required")) == 53


def test_tool_policy_kelime_routeri_degil_acik_run_politikasidir():
    from chat.agent_runtime import normalize_tool_policy
    assert normalize_tool_policy("auto") == "auto"
    assert normalize_tool_policy("required") == "required"
    assert normalize_tool_policy("none") == "none"
    try:
        normalize_tool_policy("web_ara")
        assert False
    except ValueError:
        pass


def test_output_control_model_cevabina_metin_eklemez_sahte_devam_yapmaz():
    import inspect
    from chat import output_control

    kaynak = inspect.getsource(output_control)
    assert "TEKNIK DEVAM" not in kaynak
    assert "Yanıt teknik çıktı sınırına ulaştı; tamamı üretilemedi" not in kaynak
    assert "brain.cevapla(" not in kaynak
    assert "kesik_cevabi_tamamla" not in kaynak


def test_gizli_arac_secici_dosyasi_yok():
    # Yetenek alanlarini MODEL acar (chat/agent_protocol.py, AGENTS §0);
    # kullanici metnine bakip arac secen resolver yoktur.
    import pathlib

    assert not pathlib.Path("chat/tool_resolver.py").exists()

    tools_kaynak = pathlib.Path("chat/tools.py").read_text(encoding="utf-8")
    flow_kaynak = pathlib.Path("chat/flow.py").read_text(encoding="utf-8")
    for yasak in (
        "dinamik_resolver", "arac_karari_coz", "SON_CEVAP_ADI",
    ):
        assert yasak not in tools_kaynak
        assert yasak not in flow_kaynak


def test_agent_run_state_kesilmeyi_cevaptan_ayri_tasir():
    from chat.agent_runtime import AgentRunState

    s = AgentRunState("r1")
    s.provider_set("groq")
    s.tool_started("web_search", "c1", {"query": "x"})
    s.tool_done("web_search", "c1", True, {"query": "x"})
    s.evidence_add("https://ornek.test/x", "sayfa_oku", "c2")
    s.truncate("length")
    s.complete("groq")

    pub = s.public_snapshot()
    assert pub["runtime_version"] == "p2-provider-neutral-v3"
    assert pub["status"] == "incomplete"
    assert pub["truncated_reason"] == "length"
    assert pub["tool_count"] == 1
    assert pub["evidence_count"] == 1
    assert pub["resumable"] is False


def test_namespace_metadata_runtime_araclarini_daraltmaz():
    from chat.agent_runtime import capability_surface
    from tools.capabilities import CAPABILITY_NAMESPACES, validate_registry
    from tools import TOOLS

    assert validate_registry(TOOLS)["ok"] is True
    assert len(CAPABILITY_NAMESPACES) == 13
    # OpenAI tool search onerisi: grup basina 10'dan az arac.
    assert max(len(x) for x in CAPABILITY_NAMESPACES.values()) < 10
    assert len(capability_surface(TOOLS, "auto")) == len(TOOLS) == 53


def test_yonlendirme_baglami_ucltan_uca_kesilmez_ve_imzalanir():
    import inspect
    import app
    from chat import flow

    flow_kaynak = inspect.getsource(flow)
    ekran = open("web/app.js", encoding="utf-8").read()

    assert "[:12000]" not in flow_kaynak
    assert "YONLENDIRME_BAGLAMI_JSON" not in flow_kaynak
    assert "_yonlendirme_mesajlari" in flow_kaynak

    for yasak in (
        "onceki_istek: String(anaMetin || \"\").slice",
        "tamamlanan_adimlar: (kayit.adimlar || []).slice",
        "kullanilan_kaynaklar: (kayit.kaynaklar || []).slice",
        "kismi_cevap: String(b.dataset.ham || \"\").slice",
    ):
        assert yasak not in ekran

    anahtar = b"x" * 32
    run = {"istek": "r1", "tur": "runContext", "metin": "ilk is"}
    tool = {
        "istek": "r1", "tur": "toolDone", "id": "c1",
        "name": "web_search", "args": {"query": "x"},
        "result": "gercek-sonuc", "turn": 1, "ok": True,
    }
    token = app._handoff_tokeni(
        {"schema": "p2-handoff-v1", "olaylar": [run, tool]},
        anahtar,
    )
    baglam = app._yonlendirme_baglami_dogrula(
        {"schema": "p2-handoff-v1", "token": token},
        anahtar,
    )
    assert baglam["olaylar"][1]["result"] == "gercek-sonuc"

    mesajlar = flow._yonlendirme_mesajlari(baglam, [])
    assert mesajlar[0] == {"role": "user", "content": "ilk is"}
    assert mesajlar[1]["role"] == "assistant"
    assert mesajlar[1]["tool_calls"][0]["function"]["name"] == "web_search"
    assert mesajlar[2]["role"] == "tool"
    assert mesajlar[2]["content"] == "gercek-sonuc"

    bozuk = token[:-1] + ("0" if token[-1] != "0" else "1")
    try:
        app._yonlendirme_baglami_dogrula(
            {"schema": "p2-handoff-v1", "token": bozuk},
            anahtar,
        )
        assert False, "bozuk imza kabul edilmemeli"
    except ValueError:
        pass


def test_provider_cagri_yollarinda_yapay_cikti_ve_kisa_timeout_tavani_yok():
    import pathlib

    dosyalar = (
        "brain/yayin.py", "brain/genel.py", "brain/groq.py",
        "brain/gemini.py", "brain/openrouter.py", "brain/glm.py",
        "brain/cloudflare.py", "brain/cohere.py", "brain/kilo.py",
        "brain/nvidia.py", "brain/kimi.py", "brain/deepseek.py",
        "brain/qwen.py",
    )
    for yol in dosyalar:
        kaynak = pathlib.Path(yol).read_text(encoding="utf-8")
        # finish_reason degeri olarak "max_tokens" meşrudur; yasak olan
        # request'e yapay çıktı bütçesi yazılmasıdır.
        assert '"max_tokens":' not in kaynak, yol
        assert "max_tokens=" not in kaynak, yol
        assert 'kwargs["max_tokens"]' not in kaynak, yol

    # Provider/model cevabini 8/20/60 saniyede yapay olarak kesen
    # istemci tavanlari geri gelemez.
    for yol in dosyalar:
        kaynak = pathlib.Path(yol).read_text(encoding="utf-8")
        assert "timeout=8.0" not in kaynak, yol
        assert "timeout=20.0" not in kaynak, yol
        assert '"timeout": 60.0' not in kaynak, yol


def test_chatbot_akilli_motor_aktif_imza_kalintisi_yok():
    import inspect
    from brain import secici
    from brain import brain as brain_mod
    from memory import profil

    assert tuple(inspect.signature(secici.sec).parameters) == ("mevcutlar",)
    assert "gorev_tipi" not in inspect.signature(
        brain_mod.Brain.cevapla
    ).parameters
    assert "gorev_tipi" not in inspect.signature(
        brain_mod.Brain.cevapla_yayin
    ).parameters
    assert not hasattr(profil, "ogren")
    assert not hasattr(profil, "unut")


def test_nvidia_tool_varligi_modeli_zorla_degistirmez():
    import inspect
    from brain import nvidia

    kaynak = inspect.getsource(nvidia.NvidiaClient)
    assert "sirali = [GPTOSS_MODEL]" not in kaynak
    assert "_buyuk_model_mi" not in kaynak
    assert 'kwargs["timeout"]' not in kaynak


def test_web_gercek_run_politikasini_backend_e_tasir():
    ekran = open("web/app.js", encoding="utf-8").read()
    assert "tool_policy:toolPolicy" in ekran
    assert '["auto", "required", "none"]' in ekran
