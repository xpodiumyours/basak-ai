"""tests/test_telegram.py — Telegram koprusu birim testleri (2026-09-10)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram_bot import Kaydedici, _bol


class TestKaydedici:
    def test_reply_yakalar(self):
        k = Kaydedici()
        k('BasakUI.reply("selam Casper", "glm")')
        assert k.cevap == "selam Casper"

    def test_bitir_yakalar(self):
        k = Kaydedici()
        k('BasakUI.bitir("tamamdir", "groq")')
        assert k.cevap == "tamamdir"

    def test_error_yakalar(self):
        k = Kaydedici()
        k('BasakUI.error("patladi")')
        assert k.cevap == "" and k.hata == "patladi"

    def test_bilinmeyen_gormezden(self):
        k = Kaydedici()
        k("BasakUI.thinking()")
        assert k.cevap == "" and k.hata == ""


class TestBol:
    def test_kisa_tek_parca(self):
        assert _bol("selam") == ["selam"]

    def test_uzun_bolunur(self):
        out = _bol("x" * 9000)
        assert len(out) == 3 and all(len(p) <= 4000 for p in out)

    def test_bos(self):
        assert _bol("") == [""]


class TestKimlikBul:
    """2026-09-29: telegram artik her sohbete kendi kimligini verir."""

    def test_izinli_casper_kimligini_korur(self, monkeypatch):
        from telegram_bot import _kimlik_bul
        assert _kimlik_bul("555", "555") == "casper"

    def test_diger_sohbet_ayri_kimlik_kazanir(self, monkeypatch):
        from telegram_bot import _kimlik_bul
        assert _kimlik_bul("777", "555") == "tg-777"
        assert _kimlik_bul("777", "555") != _kimlik_bul("888", "555")

    def test_izinsiz_kurulumda_herkes_ayri_kimlik(self, monkeypatch):
        from telegram_bot import _kimlik_bul
        assert _kimlik_bul("777", "") == "tg-777"

    def test_acik_ayar_eslemeyi_oncelikli_kilar(self, monkeypatch):
        import json
        import telegram_bot
        ayar = {"telegram_kimlikler": {"777": "ayse"}}
        monkeypatch.setattr(
            telegram_bot, "_ayar",
            lambda k, v=None: ayar.get(k, v))
        assert telegram_bot._kimlik_bul("777", "555") == "ayse"
        # eslesmeyen sohbet kendi kimligine duser
        assert telegram_bot._kimlik_bul("888", "555") == "tg-888"

    def test_hardcode_casper_kalmadi(self):
        import inspect
        import telegram_bot
        kaynak = inspect.getsource(telegram_bot)
        assert 'kullanici_kur("casper")' not in kaynak
