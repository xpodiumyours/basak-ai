"""Kaynak paneli köprüsü (Aşama 4): `source` olayı üç istemciye de ulaşır.

Çekirdek `chat/tools.py:_web_olay` yalnız `js_callback.olay` callable'ını
aranıyor; masaüstünde (`Api._js`) bu metod hiç yoktu — kaynaklar sessizce
kayboluyordu. Web köprüsünde (`_OlayAyiklayici`) da aynı boşluk vardı.

Sözleşme: cevap metnine dokunulmaz; kaynak ayrı bir `BasakUI.olay` olayıdır.
"""

import json
import re

import pytest


# ── Masaüstü köprüsü ────────────────────────────────────────────────

class TestMasaustuKopru:
    def _api(self, monkeypatch):
        import basak_app

        api = basak_app.Api.__new__(basak_app.Api)   # beyin kurmadan
        yazilan = []
        monkeypatch.setattr(api, "_js", lambda kod: yazilan.append(kod))
        return api, yazilan

    def test_kopru_olay_tasir(self, monkeypatch):
        import basak_app

        api, yazilan = self._api(monkeypatch)
        kopru = api._kopru()
        assert callable(getattr(kopru, "olay", None))
        assert kopru is api._kopru()          # tek nesne, tekrar kurulmaz

        kopru.olay("source", url="https://ornek.test/yazi", baslik="ornek.test")

        assert len(yazilan) == 1
        kod = yazilan[0]
        assert kod.startswith("BasakUI.olay(")

    def test_olay_json_gecerli_ve_alanlari_dogru(self, monkeypatch):
        import basak_app

        api, yazilan = self._api(monkeypatch)
        api._olay("source", url="https://ornek.test/yazi", baslik="ornek.test")

        kod = yazilan[0]
        icerik = kod[len("BasakUI.olay("):-1]
        tur, veri = json.loads("[%s]" % icerik)
        assert tur == "source"
        assert veri["url"] == "https://ornek.test/yazi"
        assert veri["baslik"] == "ornek.test"

    def test_olay_seriilestirilemezse_patlamaz(self, monkeypatch):
        api, yazilan = self._api(monkeypatch)

        class Patlak:
            def __repr__(self):
                raise RuntimeError("seriilestirilemez")

        # Varsayilan `default=str` __repr__'i de patlatabilir — yakinma
        # yayinlaya degil, hattin kirilmamasina yazar.
        api._olay("source", url="https://ornek.test/", bozuk=object())
        api._olay("source", bozuk=Patlak())
        # En azindan ilk olay cikti; istisna yukari tasinmadi.
        assert yazilan and yazilan[0].startswith("BasakUI.olay(")

    def test_kopru_normal_cagriyi_da_iletir(self, monkeypatch):
        api, yazilan = self._api(monkeypatch)
        kopru = api._kopru()
        kopru("BasakUI.bitir(\"cevap\", \"model\")")
        assert yazilan == ['BasakUI.bitir("cevap", "model")']


# ── Çekirdek akıştan kaynak üretimi ─────────────────────────────────

class TestCekirdekSource:
    def test_web_olay_masaustu_kopruya_source_yazar(self, monkeypatch):
        import basak_app
        from chat.tools import _web_olay

        api = basak_app.Api.__new__(basak_app.Api)
        yazilan = []
        monkeypatch.setattr(api, "_js", lambda kod: yazilan.append(kod))

        _web_olay(api._kopru(), "source",
                  url="https://ornek.test/yazi", baslik="ornek.test",
                  tool_id="c1")

        assert len(yazilan) == 1
        icerik = yazilan[0][len("BasakUI.olay("):-1]
        tur, veri = json.loads("[%s]" % icerik)
        assert (tur, veri["url"]) == ("source", "https://ornek.test/yazi")

    def test_olay_yokken_cekmecede_kalir(self):
        """`olay` callable olmayan istemci hata almaz (koruma getattr)."""
        from chat.tools import _web_olay

        class Olaysiz:
            def __call__(self, kod):
                return None

        _web_olay(Olaysiz(), "source", url="https://ornek.test/")  # hata yok


# ── Web köprüsü ─────────────────────────────────────────────────────

class TestWebOlayAyiklayici:
    def test_olay_sse_kaydina_duser(self):
        import basak_web

        ayik = basak_web._OlayAyiklayici("istek-42")
        basak_web._OLAYLAR.clear()
        try:
            ayik.olay("source", url="https://ornek.test/yazi",
                      baslik="ornek.test")
            kayit = basak_web._OLAYLAR["istek-42"]
            assert kayit == [{
                "istek": "istek-42", "tur": "source",
                "url": "https://ornek.test/yazi", "baslik": "ornek.test",
            }]
        finally:
            basak_web._OLAYLAR.clear()

    def test_run_state_de_ayar_gorur(self):
        """`emit_run_state` hasattr korumalidir; web'de artik calisir."""
        import basak_web
        from chat.agent_runtime import emit_run_state, AgentRunState

        ayik = basak_web._OlayAyiklayici("istek-43")
        basak_web._OLAYLAR.clear()
        try:
            emit_run_state(ayik, AgentRunState(run_id="r1"))
            kayit = basak_web._OLAYLAR["istek-43"]
            assert kayit and kayit[0]["tur"] == "runState"
        finally:
            basak_web._OLAYLAR.clear()


# ── Arayüz (statik sözleşmeler) ─────────────────────────────────────

@pytest.fixture(scope="module")
def js():
    """ui/app.js içeriği (arayüz sözleşmeleri statik olarak denetlenir)."""
    import os
    yol = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "ui", "app.js")
    with open(yol, encoding="utf-8") as f:
        return f.read()


class TestArayuzSozlesmesi:
    """UI davranışı pytest ile koşmaz (AGENTS §5); burada yalnızca
    dosyadaki sözleşmeler kilitlenir: olay işleyici var mı, kaynak
    cevap metnine mi yazılıyor, tur başında liste temizleniyor mu."""

    def test_olay_isleyici_var(self, js):
        assert re.search(r"olay\s*\(\s*tur\s*,\s*veri\s*\)", js)
        assert '"source"' in js or "'source'" in js

    def test_kaynak_ayri_blokta_metne_degil(self, js):
        # Kaynak, balon içeriğine concat edilmiyor; ayrı sınıf olarak ekleniyor.
        assert "msg-kaynaklar" in js
        assert "kaynaklariCiz" in js
        # Yalnızca reply() balonu bağlar — kaynak metne yapıştırılmaz.
        cevap = re.search(r"reply\s*\([^)]*\)\s*\{(.*?)\n  \},", js, re.S)
        assert cevap, "reply() bulundu"
        govde = cevap.group(1)
        assert "state.cevapDiv = div" in govde
        assert "kaynaklariCiz(div)" in govde

    def test_tur_basina_liste_sifirlanir(self, js):
        # Chat.thinking() ile karismasin diye BasakUI gecidi aranir.
        baslangic = js.index("window.BasakUI")
        dusunme = re.search(
            r"\n  thinking\s*\(\)\s*\{(.*?)\n  \},",
            js[baslangic:], re.S)
        assert dusunme, "BasakUI.thinking() bulundu"
        assert "state.kaynaklar = []" in dusunme.group(1)

    def test_url_dogrulamasi_var(self, js):
        # http/https disindaki ve bozuk URL'ler kaynak olamaz.
        eylem = re.search(r"function kaynakUrlTemizle.*?\n\}", js, re.S)
        assert eylem, "kaynakUrlTemizle bulundu"
        assert '"http:"' in eylem.group(0)
        assert '"https:"' in eylem.group(0)


class TestCssKimligi:
    def test_kaynak_stili_mevcut_degiskenleri_kullanir(self):
        import os
        yol = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "ui", "style.css")
        with open(yol, encoding="utf-8") as f:
            css = f.read()
        blok = re.search(r"\.msg-kaynaklar\s*\{.*?\}", css, re.S)
        assert blok, "kaynak paneli kurali style.css'te"
        # AGENTS §4: yeni palet icat etme — :root degiskenleri kaynak.
        for degisken in ("--border", "--text-dim", "--accent"):
            assert degisken in css
        assert "var(--accent)" in re.search(
            r"\.msg-kaynak\s*\{.*?\}", css, re.S).group(0)
