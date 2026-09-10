"""tests/test_telegram.py — Telegram koprusu birim testleri (2026-09-10)."""
import asyncio
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


def test_telegram_ortak_kisisel_konusma_kapisini_kullanir(monkeypatch):
    """Telegram, masaüstüyle aynı dış konuşma kapısından geçmeli."""
    import chat
    from telegram_bot import _islet

    gorulen = []

    def sahte_mesaj_isle(metin, brain, kisilik, kayit, tools):
        gorulen.append(metin)
        kayit('BasakUI.reply("Hatırladım.", "yerel")')

    monkeypatch.setattr(chat, "mesaj_isle", sahte_mesaj_isle)
    cevap = asyncio.run(_islet(object(), "KİMLİK", [],
                               "Ben çayı seviyorum"))

    assert gorulen == ["Ben çayı seviyorum"]
    assert cevap == "Hatırladım."
