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


def test_context_butcesi_disk_gecmisini_silmez():
    from chat import context as ctx
    g = [{"role": "user", "content": "x" * 5000} for _ in range(20)]
    asli = json.loads(json.dumps(g))
    pencere, bilgi = ctx.gecmis_model_penceresi(g, token_butcesi=16000)
    assert bilgi["compact"] is True
    assert 0 < len(pencere) < len(g)
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


def test_kesik_final_teknik_olarak_devam_eder():
    from chat.output_control import kesik_cevabi_tamamla

    class Beyin:
        def cevapla(self, mesajlar, model, **kwargs):
            return {
                "content": " ikinci",
                "_finish_reason": "stop",
            }, "groq"

    cevap, kaynak, tamam = kesik_cevabi_tamamla(
        Beyin(), None, [{"role": "user", "content": "uzun yaz"}],
        {"content": "birinci", "_finish_reason": "length"},
        tercih=["groq"],
    )
    assert cevap == "birinci ikinci"
    assert kaynak == "groq"
    assert tamam is True


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
