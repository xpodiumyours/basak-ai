"""tests/test_ollama_bagimsizlik.py — bulut-only sohbet sozlesmesi.

Faz 2 (ozgur-ajan): yerel model TAMAMEN kaldirildi. Brain SADECE
bulut zinciridir; mesaj_isle() yerel kontrol yapmaz, boot() ok'u
yalniz buluta baglar.

Kural: bulut YOKSA durur; bulut VARSA model adi tasiyarak konusur.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json

import pytest

import chat as c


class BulutluBrain:
    """Bulut zinciri ayakta (sahte). Yerel kavrami yok."""

    def __init__(self, cevap="buluttan cevap"):
        self._cevap = cevap

    def bulut_musait(self):
        return True

    def cevapla(self, messages, model=None, tools=None,
                override_model=None):
        assert model is None   # disaridan model adi tasinmaz
        return {"content": self._cevap}, "groq"


class CeholBrain:
    def bulut_musait(self):
        return False

    def cevapla(self, *a, **kw):
        raise AssertionError("hicbir beyin yokken cagrilMAMALI")


def _toplayici():
    kutu = {"cevap": None, "hata": None}

    def cb(code):
        # 2026-09-13: cevap tek kapidan cikar — bitir(). Akan cevapta da
        # tek seferlik yolda da ayni cagri kullanilir.
        if not (code.startswith("BasakUI.bitir")
                or code.startswith("BasakUI.error")):
            return   # thinking/parca gibi diger UI cagrilarini yoksay
        ic = code[code.index("(") + 1: code.rindex(")")]
        m = json.loads("[" + ic + "]")
        if code.startswith("BasakUI.bitir"):
            kutu["cevap"] = m[0]
        else:
            kutu["hata"] = m[0]
    return kutu, cb


@pytest.fixture
def izole(monkeypatch, tmp_path):
    from chat import context as cc
    # Akis ctx.HISTORY_FILE'i okur — yama paket degil MODUL uzerinde olmali
    monkeypatch.setattr(cc, "HISTORY_FILE", str(tmp_path / "g.json"))
    monkeypatch.setattr(cc, "SETTINGS_FILE", str(tmp_path / "a.json"))
    monkeypatch.setattr(cc, "_hafiza", False)
    return tmp_path


class TestBulutOnly:
    def test_bulut_acik_sohbet_surer(self, izole):
        brain = BulutluBrain()
        kutu, cb = _toplayici()
        c.mesaj_isle("merhaba nasilsin?", brain, "SYS", cb)
        assert kutu["hata"] is None
        assert kutu["cevap"] == "buluttan cevap"

    def test_hicbir_beyin_yoksa_durur(self, izole):
        kutu, cb = _toplayici()
        c.mesaj_isle("merhaba", CeholBrain(), "SYS", cb)
        assert kutu["cevap"] is None
        assert "beyin" in (kutu["hata"] or "")

    def test_yerel_modeller_cagrilmaz(self, izole):
        # Faz 2: akis brain.yerel_modeller()'e HIC bakmaz.
        class SikiBrain(BulutluBrain):
            def __getattr__(self, ad):
                assert ad != "yerel_modeller", "yerel kontrol geri geldi!"
                raise AttributeError(ad)
        kutu, cb = _toplayici()
        c.mesaj_isle("selam", SikiBrain(), "SYS", cb)
        assert kutu["cevap"] == "buluttan cevap"


class TestBoot:
    def test_boot_ok_bulutla_acilir(self, monkeypatch):
        import basak_app

        api = basak_app.Api.__new__(basak_app.Api)   # Brain'siz kurulum

        class Sahte:
            def bulut_musait(self):
                return True
            def ajan_musait(self):
                return True

        api.brain = Sahte()
        api.tts_on = False
        r = api.boot()
        assert (r["ok"] is True and r["cloud"] is True
                and r["agent"] is True and r["models"] == [])

    def test_boot_ok_hicbiri_yoksa_false(self, monkeypatch):
        import basak_app

        api = basak_app.Api.__new__(basak_app.Api)

        class Sahte:
            def bulut_musait(self):
                return False
            def ajan_musait(self):
                return False

        api.brain = Sahte()
        api.tts_on = False
        r = api.boot()
        assert r["ok"] is False


class TestBeyinYokkenMesaj:
    """2026-09-22: 'hicbir beyin yok' iki AYRI durumu ayirt etmeli.

    Eski tek cumle, anahtar hic yokken de anahtar yanlisken de ayni seyi
    soyluyordu — teshis edilemiyordu. Ayrim KULLANICI METNINE bakmadan,
    yalniz beyin nesnesinin durumundan yapilir (chatbot yasagi).
    """

    class Anahtarsiz:
        """Hicbir saglayici kurulamadi: anahtar eksigi."""

        def __init__(self):
            self._providers = {}

        def bulut_musait(self):
            return False

    class Zincirsiz:
        """Saglayici kuruldu ama zincire giremedi (ucretli/kapali)."""

        def __init__(self):
            self._providers = {"deepseek": object()}

        def bulut_musait(self):
            return False

    def test_anahtar_hic_yoksa_cozum_yolu_soyler(self, izole):
        kutu, cb = _toplayici()
        c.mesaj_isle("merhaba", self.Anahtarsiz(), "SYS", cb)
        hata = kutu["hata"] or ""
        assert "ayarlar.json" in hata and "doktor.py" in hata

    def test_zincir_kurulamazsa_kok_neden_soylenir(self, izole):
        kutu, cb = _toplayici()
        c.mesaj_isle("merhaba", self.Zincirsiz(), "SYS", cb)
        hata = kutu["hata"] or ""
        assert "beyin" in hata
        assert "ayarlar.json'a" not in hata

    def test_mesaj_kullanici_cumlesine_gore_degismez(self, izole):
        toplanan = []
        for metin in ("merhaba", "ayarlar.json dosyami ac",
                      "anahtar eklemen lazim"):
            kutu, cb = _toplayici()
            c.mesaj_isle(metin, self.Anahtarsiz(), "SYS", cb)
            toplanan.append(kutu["hata"])
        assert len(set(toplanan)) == 1, toplanan
