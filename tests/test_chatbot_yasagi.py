"""tests/test_chatbot_yasagi.py — KALICI GUVENCE: chatbotlastirma yasagi.

Casper'in karari (2026-09-13): Basak'i chatbot'a cevirecek veya
benzetecek HER kural, HER katman, bundan sonraki BUTUN calismalarda
yasaktir. Bu dosya o yasagin makine bekcisidir — kural kodla geri
gelirse paket KIRMIZI olur, is birlesmez.

Insan dilindeki soz: CHATBOT-YASAGI.md (koku dizin).

Kapsananlar (davranisla olculur, yoruma degil):
1. Secici tarafsiz: bayraklar sirayi degistiremez.
2. Dongu ozgur: tur siniri yok, son turda arac kapanmaz.
3. Cikti oldugu gibi: model ne yazdiysa o cikar.
4. Gecmis korunur: arac kayitlari dusmez.
5. Saglayici bogulmaz: sicaklik sabiti, dusuk tavan, dusunme kapatma yok.
6. Yasak modul yok: orkestra/onay/izin/kapasite dosyalari donemez.
7. Yasak isim yok: kelime tetikleyici tanimlayicilar donemez.
8. Sozlesme zorunluluk tasir: arac gerektiren istekte araci tarif
   etmek is sayilmaz; baslangic araclari yalniz yetenek_ac'dir.
"""

import ast
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _okunan(ad):
    with open(os.path.join(KOK, ad), encoding="utf-8") as f:
        return f.read()


class TestSeciciTarafsiz:
    def test_bayraklar_sirayi_degistirmez(self):
        from brain import secici, registry
        beklenen = list(registry.VARSAYILAN_SIRA)
        for kw in ({"tools": True},
                   {"karne_kullan": True},
                   {"cooldown": {"glm": 9999999999}},
                   {"gorev_tipi": "kod", "tools": True,
                    "karne_kullan": True}):
            sirali, _ = secici.sec(mevcutlar=list(beklenen), **kw)
            assert sirali == beklenen, kw


class TestDonguOzgur:
    def test_otuz_tur_durmaz_arac_kapanmaz(self):
        from chat.tools import arac_dongusu

        gorulen_araclar = []
        kalan = {"n": 30}

        class IsrarciBeyin:
            def cevapla(self, mesajlar, model, tools=None):
                gorulen_araclar.append(tools)
                if kalan["n"] > 0:
                    kalan["n"] -= 1
                    return {"tool_calls": [{
                        "id": "c%d" % kalan["n"], "type": "function",
                        "function": {"name": "list_tasks",
                                     "arguments": "{}"}}]}, "x"
                return {"content": "bitti <think>ozet</think>  😀"}, "x"

        gercek_kosum = {"n": 0}

        def degisen_sonuc(ad, args):
            # Genel tur tavani olmadigini olcerken exact-loop guard'a
            # takilmamak icin her gercek arac sonucu farklidir.
            gercek_kosum["n"] += 1
            return {"result": "tamam-%d" % gercek_kosum["n"]}

        cevap, kosan = arac_dongusu(
            [{"id": "c0", "type": "function",
              "function": {"name": "list_tasks", "arguments": "{}"}}],
            [{"role": "user", "content": "sor"}],
            IsrarciBeyin(), None, lambda kod: None,
            degisen_sonuc,
            tools=[{"type": "function",
                    "function": {"name": "list_tasks"}}])
        assert kosan == 31
        assert gercek_kosum["n"] == 31
        assert all(g is not None and len(g) == 1 for g in gorulen_araclar)
        assert cevap == "bitti <think>ozet</think>  😀"


class TestCiktiOlduguGibi:
    def test_temizle_metne_dokunmaz(self):
        from chat.gate import temizle
        for metin in ("<think>dusundum</think>sonuc",
                      "merhaba 😀\n\n\nnasilsin",
                      "  bosluklu  "):
            assert temizle(metin) == metin
        assert temizle(None) == ""
        assert temizle({"content": "sozluk"}) == "sozluk"


class TestGecmisKorunur:
    def test_arac_kayitlari_dusmez(self):
        from chat.context import temizle_history, gecmis_pencere
        gecmis = [
            {"role": "assistant", "content": "",
             "tool_calls": [{"id": "1"}], "oturum": "a"},
            {"role": "tool", "content": "s", "tool_call_id": "1",
             "name": "web_search", "oturum": "a"},
            {"role": "user", "content": "devam"},
        ]
        temiz = temizle_history(gecmis)
        assert temiz[0]["tool_calls"] == [{"id": "1"}]
        assert temiz[1]["tool_call_id"] == "1"
        assert temiz[1]["name"] == "web_search"
        assert all("oturum" not in m for m in temiz)
        # Kirpma yok: ne verildiyse tamami doner
        uzun = [{"role": "user", "content": "x" * 5000}] * 50
        assert len(gecmis_pencere(uzun)) == 50


class TestSaglayiciBogulmaz:
    def _yakalayan(self, cls):
        from types import SimpleNamespace

        class Yakalayan:
            def __init__(self):
                self.kayit = []

            @property
            def chat(self):
                return SimpleNamespace(
                    completions=SimpleNamespace(create=self.create))

            def create(self, **kwargs):
                self.kayit.append(kwargs)
                return SimpleNamespace(
                    choices=[SimpleNamespace(
                        message=SimpleNamespace(content="t",
                                                tool_calls=None))],
                    usage=None)

        istemci = cls.__new__(cls)
        istemci.client = Yakalayan()
        istemci.model = "test-model"
        return istemci

    def test_acik_istemcilerde_tavan_yok(self):
        from brain.groq import GroqClient
        from brain.glm import GLMClient
        from brain.gemini import GeminiClient
        from brain.nvidia import NvidiaClient
        from brain.kilo import KiloClient
        from brain.kimi import KimiClient
        from brain.deepseek import DeepSeekClient
        from brain.qwen import QwenClient
        from brain.openrouter import OpenRouterClient
        from brain.cloudflare import CloudflareClient
        for cls in (GroqClient, GLMClient, GeminiClient, NvidiaClient,
                    KiloClient, KimiClient, DeepSeekClient, QwenClient,
                    OpenRouterClient, CloudflareClient):
            i = self._yakalayan(cls)
            i.cevapla([{"role": "user", "content": "s"}])
            kw = i.client.kayit[0]
            assert "temperature" not in kw, cls
            assert kw.get("max_tokens", 0) >= 4096, (cls, kw.get("max_tokens"))
            assert "disabled" not in str(kw.get("extra_body", "")), cls


class TestYasakModulYok:
    def test_donen_dosya_yok(self):
        import importlib.util
        for mod in ("brain.orkestra", "brain.kapasite", "chat.approval",
                    "tools.executor", "tools.permissions"):
            assert importlib.util.find_spec(mod) is None, mod


class TestYasakIsimYok:
    YASAK = ("ARAC_ISARET", "arac_gerek", "GOREV_KELIME", "TOOL_IYI",
             "dinamik_arac", "aktif_tool", "ham_tool_call",
             "tool_argumani", "raw_tool", "orkestra_aktif", "juri_acik",
             "mod_kapasite", "calistirilabilir", "cikis_kapisi",
             "PROMPT_BLOG", "TUR_SINIRI", "ARAC_SONUC_TAVAN",
             "onay_kuyrugu", "ApprovalSystem", "yetki_tavani")

    DOSYALAR = ("brain/secici.py", "brain/brain.py", "chat/flow.py",
                "chat/tools.py", "chat/context.py", "chat/prompts.py",
                "chat/gate.py", "tools/definitions.py",
                "tools/__init__.py", "tools/matris.py", "tools/hesap.py",
                "tools/hafiza.py", "tools/gorsel.py", "tools/saglik.py")

    def _isimler(self, agac):
        for dugum in ast.walk(agac):
            if isinstance(dugum, (ast.FunctionDef, ast.AsyncFunctionDef,
                                  ast.ClassDef)):
                yield dugum.name
            elif isinstance(dugum, ast.arg):
                yield dugum.arg
            elif isinstance(dugum, ast.Name):
                yield dugum.id
            elif isinstance(dugum, ast.Attribute):
                yield dugum.attr
            elif isinstance(dugum, ast.alias):
                yield (dugum.asname or dugum.name)

    def test_tanimlayici_donemez(self):
        for yol in self.DOSYALAR:
            agac = ast.parse(_okunan(yol))
            for isim in self._isimler(agac):
                for yasak in self.YASAK:
                    assert yasak not in isim, (yol, isim)


class TestSozlesmeZorunlulukTasir:
    """8. guvence (2026-09-22, Casper karari): sozlesme arac tarifini
    is sayilmaz der; baslangic araclari yalniz yetenek_ac'dir (model
    hala serbesttir — required/force YOK, kelime tetikleyici YOK)."""

    def test_sozlesme_tarifi_is_yapmaz_der(self):
        from chat.agent_protocol import AJAN_SOZLESMESI
        metin = AJAN_SOZLESMESI.lower()
        assert "yetenek_ac" in metin
        assert "zorunluluktur" in metin
        assert "tarif" in metin
        assert "sayilmaz" in metin

    def test_sozlesme_kelime_tetikleyici_icermaz(self):
        from chat.agent_protocol import AJAN_SOZLESMESI
        yasak = ("eger su kelime", "asagidaki kelime", "kelime gecerse",
                 "if the user says", "su araci ac")
        metin = AJAN_SOZLESMESI.lower()
        for cumle in yasak:
            assert cumle not in metin, cumle

    def test_baslangic_araclari_yalniz_yetenek_ac(self):
        from chat.agent_protocol import baslangic_araclari, YETENEK_AC_ADI
        araclar = baslangic_araclari()
        assert len(araclar) == 1
        assert araclar[0]["function"]["name"] == YETENEK_AC_ADI

    def test_flow_sozlesmeyi_arac_acikken_gonderir(self):
        import inspect
        from chat import flow
        kaynak = inspect.getsource(flow.mesaj_isle)
        assert "AJAN_SOZLESMESI" in kaynak
        assert "tool_choice=\"auto\"" in kaynak or \
               "tool_choice='auto'" in kaynak or \
               'tool_choice="auto"' in kaynak
