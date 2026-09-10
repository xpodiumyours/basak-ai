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
