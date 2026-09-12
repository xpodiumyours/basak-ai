"""telegram_bot.py — Basak telefonda (Telegram).

2026-09-10 (Casper): evdeki Basak'a disaridan erisim. Ayni beyin,
ayni hafiza, ayni gecmis (telefondan sor, PC'de gorunur).

Kullanim:
  1. Telegram'da @BotFather -> /newbot -> adi + kullanici adi ver.
  2. Verdigi bileti ayarlar.json'a "telegram_bot_token" diye yaz.
     (Istersen "telegram_izinli_id" ile sadece kendi hesabina kilitle:
     @userinfobot'a yaz, sana verdigi sayiyi yaz.)
  3. telegram-baslat.cmd'ye cift tikla (PC acik kalmali).

Notlar:
- v1 yalniz YAZI alir/verir (sesli mesaj sonra).
- Guvenli alan disi yazmalarda onay EKRANI olmadigi icin REDDEDILIR;
  knowledge/notlar serbesttir.
- Uzun cevaplar 4000 harflik parcalara bolunur (Telegram siniri).
"""

import asyncio
import json
import logging
import os

logger = logging.getLogger(__name__)

BASE = os.path.dirname(os.path.abspath(__file__))
AYARLAR = os.path.join(BASE, "ayarlar.json")
PARCA_LIMITI = 4000


def _ayar(anahtar, varsayilan=None):
    try:
        with open(AYARLAR, "r", encoding="utf-8-sig") as f:
            return json.load(f).get(anahtar, varsayilan)
    except (OSError, ValueError):
        return varsayilan


class Kaydedici:
    """js_callback yerine gecer: reply/bitir/error cagrilarini yakalar."""

    def __init__(self):
        self.cevap = ""
        self.hata = ""

    def __call__(self, kod):
        try:
            if kod.startswith("BasakUI.reply(") or kod.startswith("BasakUI.bitir("):
                icerik = kod.split("(", 1)[1].rsplit(")", 1)[0]
                self.cevap = json.loads("[%s]" % icerik)[0]
            elif kod.startswith("BasakUI.error("):
                icerik = kod.split("(", 1)[1].rsplit(")", 1)[0]
                self.hata = json.loads("[%s]" % icerik)[0]
        except Exception:
            pass


def _bol(metin):
    metin = metin or ""
    return [metin[i:i + PARCA_LIMITI]
            for i in range(0, max(len(metin), 1), PARCA_LIMITI)]


async def _islet(brain, kisilik, tools, metin):
    """Sohbet hattini ayri thread'de kostur, son cevabi dondur."""
    # Masaustu ile ayni public chat girisini kullan: TaskProfile/harness
    # davranisi kanal degistirince farklilasmasin.
    from chat import mesaj_isle

    kayit = Kaydedici()

    def _kos():
        try:
            mesaj_isle(metin, brain, kisilik, kayit, tools)
        except Exception as e:
            logger.warning("Telegram islem hatasi: %s", e)
            kayit.hata = kayit.hata or "Bir sorun oldu."
    await asyncio.to_thread(_kos)
    return kayit.cevap or ("⚠ %s" % kayit.hata if kayit.hata else "...")


def main():
    from telegram import Update
    from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

    from brain import Brain
    from basak_app import KISILIK, init_cache
    from tools import TOOLS

    bilet = _ayar("telegram_bot_token", "")
    if not bilet:
        print("ayarlar.json'da 'telegram_bot_token' yok.")
        print("Telegram'da @BotFather -> /newbot ile alip dosyaya yaz.")
        return
    izinli = str(_ayar("telegram_izinli_id", "") or "")

    init_cache()
    beyin = Brain()
    print("Telegram koprusu hazir. Kapatmak icin pencereyi kapat.")

    async def _karsila(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if izinli and str(update.effective_chat.id) != izinli:
            return
        metin = (update.message.text or "").strip()
        if not metin:
            return
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id, action="typing")
        cevap = await _islet(beyin, KISILIK, TOOLS, metin)
        for parca in _bol(cevap):
            await update.message.reply_text(parca)

    app = ApplicationBuilder().token(bilet).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _karsila))
    app.run_polling()


if __name__ == "__main__":
    main()
