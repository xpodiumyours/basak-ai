"""tests/test_seviye0_sozlesme.py — Duzey 0 sozlesme testleri.

AGENTS.md §9 + knowledge/kabul-plani-web-gate.md "TEST DUZEYLERI" bolumunun
Duzey 0'ini uygular: cevrimdisi, kota harcamaz, GERCEK ag davranisini
kanitlamaz (o kanit Duzey 1-3 canli kosularindan gelir).

Uc bolum:
1. 8/8 saglayici sabit tablolari (ajan_tool_choice, registry kartlari).
2. 52/52/52 arac yapisal eslesmesi (sema/calistirma/ekran/katalog).
3. Ajan dongusu + kosucu sozlesmesi (simulasyon YASAK; anahtarsiz SKIP).
"""

import json

import pytest


# ── Yardimcilar ─────────────────────────────────────────────────────

class _YD:
    """Saglayici yanit kalibini taklit eden en kucuk sahte mesaj.

    Not: bu SAHTE ARAC SONUCU degil — yanit PAKETININ seklini tasir.
    Isin gercegi Duzey 1-3'te canli yanitlarla sabitlenir.
    """

    def __init__(self, content="", tool_calls=None, **ekstra):
        self.content = content
        self.tool_calls = tool_calls or []

        class _Tc:
            def __init__(self, c):
                self.id = c["id"]
                self.function = types.SimpleNamespace(
                    name=c["function"]["name"],
                    arguments=c["function"]["arguments"])
                for k, v in ekstra.items():
                    setattr(self, k, v)

        self._cagilar = [dict(c) for c in self.tool_calls]
        for alan, deger in ekstra.items():
            setattr(self, alan, deger)

    def cagilar(self):
        return self._cagilar


def _tc(ad, args='{"metin":"x"}', cid="c1", **ekstra):
    c = {"id": cid, "type": "function",
         "function": {"name": ad, "arguments": args}}
    if ekstra:
        c["extra"] = ekstra
    return c


def _tco(ad, args="{}", cid="c1"):
    """SDK-nesne bicimli tool_call (adaptörler .function bekler)."""
    import types
    return types.SimpleNamespace(
        id=cid, type="function",
        function=types.SimpleNamespace(name=ad, arguments=args))


class _Secim:
    def __init__(self, message):
        self.message = message


class _Yanit:
    def __init__(self, message, usage=None):
        self.choices = [_Secim(message)]
        self.usage = usage


def _mesaj(content="", tool_calls=None, **ekstra):
    import types
    m = types.SimpleNamespace()
    m.content = content
    m.tool_calls = tool_calls or []
    for k, v in ekstra.items():
        setattr(m, k, v)
    return m


def _fake_client(monkeypatch, hedef, yanit, yakalanan, sembol="OpenAI"):
    """OpenAI tabanli istemcilerin dis cagrisini yakalar (duz siniflar)."""

    class _Uc:
        def create(self, **kwargs):
            yakalanan.append(kwargs)
            return yanit

    class _Chat:
        completions = _Uc()

    class _Fabrika:
        def __init__(self, **kwargs):
            self.chat = _Chat()

    monkeypatch.setattr(hedef, sembol, _Fabrika)


# ── BOLUM 1: 8/8 saglayici sozlesmesi ───────────────────────────────

SEKIZLER = ("groq", "gemini", "openrouter", "glm", "cloudflare",
            "cohere", "kilo", "nvidia")


def test_sekiz_saglayici_ajan_destegi_beyan_eder():
    from brain import registry
    for ad in SEKIZLER:
        assert registry.ajan_destegi_var_mi(ad), ad
        assert registry.ajan_tool_modu(ad) in ("required", "auto_enforced"), ad


def test_sozlesme_degerleri_resmi_protokole_uygun():
    """required destekleyen saglayiciya 'required', auto saglayiciya
    'auto' gider — karisik tablo sapma isaretidir."""
    from brain import registry
    beklenen = {
        # 2026-09-19 Duzey 1 kaniti: groq required altinda 400 (hem 120b
        # hem 20b), auto'da dogal GERCEK tool_call — auto_enforced.
        "groq": "auto",
        "gemini": "auto",
        "openrouter": "auto",
        "glm": "auto",
        "cloudflare": "required",
        "cohere": "required",
        "kilo": "required",
        "nvidia": "auto",
    }
    for ad, deger in beklenen.items():
        assert registry.ajan_tool_choice(ad) == deger, ad


def test_ajan_akisi_auto_tool_choice_tasiyor():
    """Uretim sohbeti araci zorlamaz; model gerekirse native tool_call secer.

    Duzey-1'in zorunlu tool-call olcumu canli test kosucusunun isidir.
    Uretim sohbetinde 'required' kullanmak normal sohbeti ve dogal finali
    engeller; burada model karari icin 'auto' sozlesmesi kilitlenir.
    """
    icerik = open("chat/flow.py", encoding="utf-8").read()
    assert 'tool_choice="auto"' in icerik, (
        "ajan sohbeti model kontrollu auto secimini kaybetti")


def test_ucretsiz_kartlar_zincire_girer_ucretli_girmez():
    from brain import registry
    for ad in SEKIZLER:
        k = registry.kart(ad)
        assert k["ucretsiz"] is True, ad
        assert k["tools"] is True, ad


# ── BOLUM 2: 52/52/52 arac yapisal eslesmesi ────────────────────────

def test_52_arac_uchalida_birebir():
    """sema (definitions) <-> calistirma dali <-> ekran etiketi."""
    import re
    from tools.definitions import TOOLS, TANINMIS_TOOLLAR
    from chat.tools import DURUM_METNI

    sema = {t["function"]["name"] for t in TOOLS}
    kaynak = open("tools/__init__.py", encoding="utf-8").read()
    dallar = set(re.findall(r"tool_name == \"([a-z_]+)\"", kaynak))

    assert len(sema) == 53
    assert len(TANINMIS_TOOLLAR) == 53
    assert sema == dallar, ("sema/dal farki", sema ^ dallar)
    eksik_etiket = sema - set(DURUM_METNI)
    assert not eksik_etiket, ("etiketsiz arac", eksik_etiket)


def test_yetenek_katalogu_52_gercek_araci_kapsar():
    from tools.definitions import TOOLS
    from tools.capabilities import CAPABILITY_NAMESPACES

    gercek = {t["function"]["name"] for t in TOOLS}
    katalog = {ad for grup in CAPABILITY_NAMESPACES.values() for ad in grup}
    assert katalog == gercek
    assert len(katalog) == 53


def test_katalog_daki_her_arac_gercekten_kosabilir():
    """Katalogdaki her ad calistirici beyaz listesinde ve calistirma
    dalinda VAR — katalog hayalet arac icermez."""
    import re
    from tools.capabilities import CAPABILITY_NAMESPACES
    from tools.definitions import TANINMIS_TOOLLAR

    kaynak = open("tools/__init__.py", encoding="utf-8").read()
    for grup in CAPABILITY_NAMESPACES.values():
        for ad in grup:
            assert ad in TANINMIS_TOOLLAR, ad
            assert ('tool_name == "%s"' % ad) in kaynak, ad


# ── BOLUM 3: adaptor birim sozlesmeleri ─────────────────────────────

def test_groq_required_istegi_ve_tool_calls_cozumu(monkeypatch):
    """groq: tool_choice=required istekle gider; tool_calls OpenAI
    seklinde cozulur; metin-icinde-JSON tool_call SAYILMAZ."""
    import brain.groq as groq_mod
    from brain.groq import GroqClient

    yakalanan = []
    msg = _mesaj(tool_calls=[_tco("simdi", "{}", "g1")])
    _fake_client(monkeypatch, groq_mod, _Yanit(msg), yakalanan)

    c = GroqClient("test-anahtar")
    yanit = c.cevapla([{"role": "user", "content": "saat"}],
                      tools=[{"type": "function", "function": {
                          "name": "simdi", "parameters": {}}}],
                      tool_choice="required")

    assert yakalanan[0]["tool_choice"] == "required"
    assert yanit["tool_calls"][0]["function"]["name"] == "simdi"
    assert isinstance(yanit["tool_calls"][0]["function"]["arguments"], str)


def test_gemini_extra_content_imzasi_cagriya_tasinir(monkeypatch):
    """gemini: tool_call seviyesindeki extra_content (thought_signature
    tasiyici) yanit dict'ine AKTARILMALI — dusen imza tur-2 400'unun
    kokudur (Duzey 1 kanit: 2026-09-19 22:24 olcumu)."""
    import types
    import brain.gemini as gemini_mod
    from brain.gemini import GeminiClient

    tc = _tc("simdi", "{}", "m1")
    ekstra = types.SimpleNamespace(
        google=types.SimpleNamespace(thought_signature="IMZA123"))
    # Gercel SDK pydantic nesnesidir; adaptor model_dump cagirir.
    ekstra.model_dump = lambda exclude_none=True: {
        "google": {"thought_signature": "IMZA123"}}
    cagri = types.SimpleNamespace(**{**tc,
        "function": types.SimpleNamespace(name="simdi", arguments="{}"),
        "extra_content": ekstra})

    yakalanan = []
    _fake_client(monkeypatch, gemini_mod,
                 _Yanit(_mesaj(tool_calls=[cagri])), yakalanan)

    c = GeminiClient("test-anahtar")
    yanit = c.cevapla([{"role": "user", "content": "saat"}],
                      tools=[{"type": "function", "function": {
                          "name": "simdi", "parameters": {}}}],
                      tool_choice="auto")

    assert "extra_content" in yanit["tool_calls"][0], (
        "gemini imzasi tool_call'dan dustu")


def test_cohere_required_uzun_form_ve_tool_plan(monkeypatch):
    """cohere: tool_choice REQUIRED (uzun form) gider; tool_plan korunur."""
    import types
    import brain.cohere as cohere_mod
    from brain.cohere import CohereClient

    tc = types.SimpleNamespace(
        id="cc1",
        function=types.SimpleNamespace(name="simdi", arguments="{}"))
    mesaj = types.SimpleNamespace(
        content="", tool_calls=[tc], tool_plan="PLAN-1")
    yanit = types.SimpleNamespace(
        message=mesaj,
        meta=types.SimpleNamespace(tokens=types.SimpleNamespace(
            input_tokens=10, output_tokens=5)))

    yakalanan = []

    class _SahteClient:
        def __init__(self, *a, **k):
            pass

        def chat(self, **kwargs):
            yakalanan.append(kwargs)
            return yanit

    class _SahteCohereSDK:
        Client = _SahteClient
        ClientV2 = _SahteClient

    monkeypatch.setattr(cohere_mod, "cohere", _SahteCohereSDK)

    c = CohereClient("test-anahtar")
    sonuc = c.cevapla([{"role": "user", "content": "saat"}],
                      tools=[{"type": "function", "function": {
                          "name": "simdi", "parameters": {}}}],
                      tool_choice="required")

    assert yakalanan[0]["tool_choice"] == "REQUIRED"
    assert sonuc.get("tool_plan") == "PLAN-1"
    assert sonuc["tool_calls"][0]["function"]["name"] == "simdi"


def test_anahtarsiz_kilo_ajan_yuvasi_istegi_gonderir(monkeypatch):
    """kilo: anahtar yokken Authorization basligi kaldirilir ama istek
    tool_choice ile GONDERILIR — sessiz yuva sapmadir."""
    import types
    import brain.kilo as kilo_mod
    from brain.kilo import KiloClient

    yakalanan = []
    _fake_client(monkeypatch, kilo_mod,
                 _Yanit(_mesaj(tool_calls=[_tco("simdi", "{}", "k1")])),
                 yakalanan)

    c = KiloClient()
    yanit = c.cevapla([{"role": "user", "content": "saat"}],
                      tools=[{"type": "function", "function": {
                          "name": "simdi", "parameters": {}}}],
                      tool_choice="required")

    assert yakalanan, "kilo istegi hic gitmedi"
    assert yakalanan[0]["tool_choice"] == "required"
    assert yanit["tool_calls"][0]["function"]["name"] == "simdi"


# ── BOLUM 4: kosucu-kabul sozlesmesi ────────────────────────────────

def test_kosucu_anahtarsiz_hucreye_skip_yazar_tahmin_etmez():
    """Kabul sozlesmesi: anahtar yoksa hucre SKIP'tir. Bu test kosucu
    modulunun sozlesmesini sabitler (modul Duzey 1 oncesi yazilir)."""
    import pathlib
    kosucu = pathlib.Path("tests/live/kosucu.py")
    if not kosucu.exists():
        pytest.skip("kosucu modulu henüz yazilmadi (Duzey 1 adimi)")
    icerik = kosucu.read_text(encoding="utf-8")
    assert "SKIP" in icerik, "kosucu SKIP sozlesmesi tasimiyor"
    assert "sampleValue" not in icerik and "BASAK_CELL_OK" not in icerik, (
        "kosucuda simulasyon kalintisi var — AGENTS.md §9 ihlali")


def test_plan_dosyasi_kapsam_sozlesmesi_tasiyor():
    """Kapsam kucultme yasagi ve 6 adimli siralanis tek dogru kaynaktan
    okunabilir olmali — belge yoksa kabul zinciri kopar."""
    icerik = open("knowledge/kabul-plani-web-gate.md",
                  encoding="utf-8").read()
    for sart in ("kucultme YASAK", "364 HUCRE", "TEK kabul raporu",
                 "DUZEY 1", "SKIP", "KAPSAM DEĞİŞİKLİĞİ"):
        assert sart in icerik, sart


def test_openrouter_bos_choices_cokmez_anlasilir_hata_verir(monkeypatch):
    """2026-09-20 olcumu: free yonlendirici 200 + bos choices donduğunde
    adaptor 'NoneType' ile cokuyordu. Artik RuntimeError — zincirin
    zarif hata yolu devreye girer."""
    import types
    import brain.openrouter as or_mod
    from brain.openrouter import OpenRouterClient

    bos = types.SimpleNamespace(choices=[])   # 200 + bos secimler

    class _SahteCompletions:
        def create(self, **kwargs):
            return bos

    class _SahteChat:
        completions = _SahteCompletions()

    class _SahteSDK:
        def __init__(self, **kwargs):
            self.chat = _SahteChat()

    monkeypatch.setattr(or_mod, "OpenAI", _SahteSDK)
    monkeypatch.setattr(or_mod.OpenRouterClient, "_model_bul",
                        lambda self: "test/free")

    c = OpenRouterClient("test-anahtar")
    with pytest.raises(RuntimeError, match="bos yanit"):
        c.cevapla([{"role": "user", "content": "saat"}])


# ── BOLUM 5: duzey 2 matris kosucusu sozlesmesi ─────────────────────

def test_matris_kosucu_simulasyon_yasaklarini_tasiyor():
    """§9: kosucu dosyasinda simulasyon kalintisi olamaz; arac cagrisi
    beyaz liste kapisi (_guvenli_calistir) olmadan gecemez."""
    import pathlib
    yol = pathlib.Path("tests/live/matris_kosucu.py")
    assert yol.exists(), "matris kosucusu yok"
    icerik = yol.read_text(encoding="utf-8")
    assert "sampleValue" not in icerik and "BASAK_CELL_OK" not in icerik, (
        "matris kosucusunda simulasyon kalintisi — AGENTS.md §9 ihlali")
    assert "_guvenli_calistir" in icerik, "beyaz liste kapisi yok"
    assert "SKIP" in icerik, "anahtarsiz SKIP sozlesmesi yok"


def test_matris_kosucu_pilot_listesi_sekiz_arac_gercek_sema_es():
    """Pilot 8 temsilci arac: sayisi tam 8, taninmis ve semayla es."""
    from tests.live import matris_kosucu
    from tools import TANINMIS_TOOLLAR
    from tests.live import kosucu

    assert len(matris_kosucu.PILOT_ARACLAR) == 8
    for arac in matris_kosucu.PILOT_ARACLAR:
        assert arac in TANINMIS_TOOLLAR, "%s beyaz liste disi" % arac
        assert arac in kosucu.SEMALAR, "%s semasi yok" % arac


def test_matris_kosucu_52_semaya_bagli_tek_kaynak():
    """Koşucunun sema kaynagi tools.TOOLS'in kendisi — kopya tablo yok."""
    from tests.live import kosucu
    from tools import TANINMIS_TOOLLAR

    assert set(kosucu.SEMALAR.keys()) == set(TANINMIS_TOOLLAR)
    assert len(kosucu.SEMALAR) == 53


def test_matris_kosucu_hucre_kaydi_yapisi(tmp_path, monkeypatch):
    """YESIL hucre kaydi: tur1=native, tur2=tamam, sure/model/zaman alani.
    Sahte istemci yalniz yanit SEKLINI tasir; arac GERCEK kosar (simdi)."""
    import types
    from tests.live import kosucu, matris_kosucu

    monkeypatch.setattr(matris_kosucu, "MATRIS", tmp_path / "m.json")

    class _Sahte:
        model = "sahte-model"

        def __init__(self):
            self.n = 0

        def cevapla(self, mesajlar, tools=None, yapi=None,
                    tool_choice=None):
            self.n += 1
            if self.n == 1:
                return {"content": "", "tool_calls": [{
                    "id": "c1", "type": "function",
                    "function": {"name": "simdi", "arguments": "{}"}}]}
            return {"content": "Saat alindi."}

    kayit = matris_kosucu._hucre_kos("groq", "simdi",
                                     kosucu.SEMALAR["simdi"], _Sahte())
    assert kayit["durum"] == "YESIL"
    assert kayit["tur1"] == "native" and kayit["tur2"] == "tamam"
    assert kayit["model"] == "sahte-model"
    kayitli = matris_kosucu._yukle()
    assert kayitli["duzey2"]["groq"]["simdi"]["durum"] == "YESIL"


def test_matris_kosucu_arac_hatasi_tur2_ile_olculur(tmp_path, monkeypatch):
    """Pilot politikasi: arac error'u gercek sonuctur; tur-1 native +
    tur-2 tamamsa hucre YESIL'dir ve hata kayitta kanit olarak durur."""
    from tests.live import kosucu, matris_kosucu

    monkeypatch.setattr(matris_kosucu, "MATRIS", tmp_path / "m.json")

    class _Sahte:
        model = "sahte"

        def __init__(self):
            self.n = 0

        def cevapla(self, mesajlar, tools=None, yapi=None,
                    tool_choice=None):
            self.n += 1
            if self.n == 1:
                return {"content": "", "tool_calls": [{
                    "id": "c1", "type": "function",
                    "function": {"name": "hesapla",
                                 "arguments": "{\"ifade\":\"1/0\"}"}}]}
            return {"content": "Araç hata verdi, soyledim."}

    c = _Sahte()
    kayit = matris_kosucu._hucre_kos("groq", "hesapla",
                                     kosucu.SEMALAR["hesapla"], c)
    assert kayit["durum"] == "YESIL", kayit
    assert "arac_hatasi" in kayit, "hata kanitsiz kalmasin"


def test_matris_kosucu_sorularda_deger_var():
    """Pilot bulgusu: arguman isteyen araclarin sorusunda deger OLMALI —
    modelin 'hangi deger?' sorusu kirmizi sayilmaz."""
    from tests.live import matris_kosucu

    for arac in ("sayfa_oku", "hesapla", "git_durum", "list_files"):
        soru = matris_kosucu._soru_yaz(arac)
        assert "Degerler:" in soru, "%s sorusunda deger yok" % arac
    assert "Degerler:" not in matris_kosucu._soru_yaz("simdi")


def test_matris_kosucu_yesil_hucreyi_tekrar_kosmaz(tmp_path, monkeypatch):
    """Kesintiden devam: YESIL hucre olan saglayici icin istek GITMEZ."""
    from tests.live import kosucu, matris_kosucu

    monkeypatch.setattr(matris_kosucu, "MATRIS", tmp_path / "m.json")
    monkeypatch.setattr(matris_kosucu, "_add_task_temizle", lambda: None)
    monkeypatch.setattr(kosucu, "_anahtarlar", lambda ad: ["sahte"])

    class _Sayac:
        model = "sahte"
        cagrilar = []

        def cevapla(self, *a, **k):
            type(self).cagrilar.append(1)
            return {"content": "x"}

    _Sayac.cagrilar = []
    monkeypatch.setattr(kosucu, "_istemci", lambda ad: _Sayac())

    # simdi YESIL, diger 7 pilot araci bos: yalniz onlar denenir.
    matris_kosucu._hucre_yaz("groq", "simdi", {
        "durum": "YESIL", "zaman": "2026-09-19 10:00:00"})
    ozet = matris_kosucu.kos_tumu(["groq"], pilot=True, bekleme=0)

    # Sahte yalniz tur-1'de arac cagirmiyor -> hucre basi 1 istek.
    # YESIL olan simdi icin HIC istek gitmedi: 8 degil 7 cagri.
    assert len(_Sayac.cagrilar) == 7, (
        "YESIL hucre icin tekrar istek gitti veya bos hucre atlandi "
        "— devam sozlesmesi kirildi")
    assert ozet["YESIL"] == 1 and ozet["KIRMIZI"] == 7


def test_matris_kosucu_anahtarsiza_skip_yazar(tmp_path, monkeypatch):
    """Anahtar yoksa: pilot hucrelerin TAMAMI SKIP, tahmin doldurma yok."""
    from tests.live import kosucu, matris_kosucu

    monkeypatch.setattr(matris_kosucu, "MATRIS", tmp_path / "m.json")
    monkeypatch.setattr(kosucu, "_anahtarlar", lambda ad: None)

    ozet = matris_kosucu.kos_tumu(["cohere"], pilot=True, bekleme=0)

    assert ozet["SKIP"] == 8 and ozet["YESIL"] == 0 and ozet["KIRMIZI"] == 0
    m = matris_kosucu._yukle()
    hucreler = m["duzey2"]["cohere"]
    assert len(hucreler) == 8
    assert all(k["durum"] == "SKIP" for k in hucreler.values())


def test_matris_kapsami_elde_anahtari_olan_yedi_saglayici():
    """Duzey 2 kapsami: yalniz ELDE ANAHTARI OLAN saglayicilar (2026-09-22).

    cloudflare + cohere icin anahtar eklenmeyecegi bilindigi icin 104
    hucre kalici SKIP yaziyordu — olcum uretmiyor, tabloyu sisiriyordu.
    Kapsamdan cikarildilar; anahtari olan mistral kapsama girdi.
    Sira registry.VARSAYILAN_SIRA'dan FILTRELENIR, uydurulmaz.
    """
    from brain import registry
    from tests.live import matris_kosucu

    assert matris_kosucu.KAPSAM == (
        "groq", "gemini", "kilo", "nvidia", "glm", "openrouter",
        "mistral")
    assert len(matris_kosucu.KAPSAM) * 53 == 371     # 7x53=371 (eski 7x52=364)
    assert "cloudflare" not in matris_kosucu.KAPSAM
    assert "cohere" not in matris_kosucu.KAPSAM
    beklenen = tuple(ad for ad in registry.VARSAYILAN_SIRA
                     if ad in matris_kosucu.KAPSAM)
    assert matris_kosucu.KAPSAM == beklenen, (
        "kapsam sirasi registry sirasindan sapmis")


def test_matris_kapsamindaki_her_saglayici_kosucuda_desteklenir():
    """Kapsamdaki bir saglayici kosucuda tanimsizsa kosum KeyError ile patlar."""
    from tests.live import kosucu, matris_kosucu

    for ad in matris_kosucu.KAPSAM:
        assert ad in kosucu.ANAHTARLAR, "%s anahtar tablosunda yok" % ad
        assert ad in kosucu.ZORLAMA, "%s zorlama tablosunda yok" % ad
        assert ad in matris_kosucu._PACE, "%s pace tablosunda yok" % ad


def test_kapsam_temizle_yalniz_kapsam_disini_siler(tmp_path, monkeypatch):
    """Eski kapsamdan kalan cloudflare/cohere satirlari silinir; kapsam
    icindeki YESIL hucrelere DOKUNULMAZ."""
    import json
    from tests.live import matris_kosucu

    hedef = tmp_path / "m.json"
    hedef.write_text(json.dumps({
        "duzey1": {"cloudflare": {"durum": "SKIP"}},
        "duzey2": {
            "groq": {"simdi": {"durum": "YESIL"}},
            "cloudflare": {"simdi": {"durum": "SKIP"}},
            "cohere": {"simdi": {"durum": "SKIP"}},
        }}), encoding="utf-8")
    monkeypatch.setattr(matris_kosucu, "MATRIS", hedef)

    silinen = matris_kosucu.kapsam_temizle()

    assert sorted(silinen) == ["cloudflare", "cohere"]
    kalan = json.loads(hedef.read_text(encoding="utf-8"))
    assert set(kalan["duzey2"]) == {"groq"}
    assert kalan["duzey2"]["groq"]["simdi"]["durum"] == "YESIL"
    # Duzey 1 kayitlari bu isin konusu degil — dokunulmaz.
    assert "cloudflare" in kalan["duzey1"]

