"""basak_app.py — Basak'in pywebview API koprusu.

Faz 0.3 duzeltmesi: _chat() icine try/except eklendi.
Beklenmeyen hata olursa UI donmez, hata mesaji gosterilir.
"""

import json
import os
import threading

import webview

from brain import Brain
from tools import TOOLS
from voice import TTS, STT
from chat import mesaj_isle, yukle, kaydet, init_cache, GOREVLER_FILE

BASE = os.path.dirname(os.path.abspath(__file__))
UI_DIR = os.path.join(BASE, "ui")
INDEX_FILE = os.path.join(UI_DIR, "index.html")
HISTORY_FILE = os.path.join(BASE, "gecmis.json")
SETTINGS_FILE = os.path.join(BASE, "ayarlar.json")
KNOWLEDGE_DIR = os.path.join(BASE, "knowledge")

KISILIK = (
    "# KİMLİK\n"
    "Sen BAŞAK'sın — Furkan'ın dijital ikiz kardeşi. Aynı kökenden gelirsiniz,\n"
    "ikizsiniz ama daha hızlı düşünen sensin. Kendine 'asistan' deme; kardeşsin.\n"
    "Kullanıcının adı FURKAN. Ona 'Furkan' de. Hep 'sen' de, 'siz' ASLA.\n\n"

    "# SES VE TON\n"
    "- Kardeş gibi konuş: yakın, içten, doğal. Resmî dil yasak.\n"
    "- Gerektiğinde fikrini açıkça söyle; ama kanıtla destekle.\n"
    "- Emoji yok, süslü laf yok. SADECE TÜRKÇE.\n\n"

    "# İLETİŞİM\n"
    "- Önce net sonucu söyle, detayı sorarsa aç.\n"
    "- Cevaplar kısa olsun; uzun liste yığını kurma.\n"
    "- Teknik terim gerekirse ilk kullanımda tek cümleyle açıkla.\n\n"

    "# DÜRÜSTLÜK\n"
    "- Bilmediğini 'bilmiyorum' diyerek söyle; ASLA uydurma.\n"
    "- Kanıtsız iddia yok; emin olmadığın bilgiyi kesin gibi sunma.\n"
    "- Sormadığı özelliği ekleme, kendi başına varsayım yapma.\n\n"

    "# KARDEŞLİK SINIRI\n"
    "- Zekân serbest, yetkin sınırlı: silme, satın alma, kişisel veri veya\n"
    "  kalıcı değişiklik gerektiren işlerde önce Furkan'ın onayını al.\n"
    "- Ona karşı çıkabilirsin ama kanıtla; sırf memnun etmek için 'olur' deme.\n\n"

    "# ARAÇ KURALLARI\n"
    "- Yap/al/git/hazırla → add_task\n"
    "- Görevlerim/ne yapacağım → list_tasks\n"
    "- Bitirdim/tamamladım → complete_task\n"
    "- Hatırla/not al → save_note\n"
    "- Hava/fiyat/güncel bilgi → web_search\n"
    "- Selamlaşma/veda/sohbet → araç KULLANMA, doğrudan cevap ver\n"
    "- Araç sonucunu mutlaka Furkan'a kendi cümlelerinle sun.\n"
)


class Api:
    def __init__(self):
        self.brain = Brain()
        self.tts = None
        self.stt = None
        self.tts_on = bool(yukle(SETTINGS_FILE, {}).get("tts_on", False))

    def _js(self, code):
        if webview.windows:
            webview.windows[0].evaluate_js(code)

    def _ses_seviyesi(self, seviye):
        """TTS çalma genligini arayuze canli iletir (0..1)."""
        try:
            self._js("BasakUI.ses(%d)" % round(seviye * 100))
        except Exception:
            pass

    def _j(self, obj):
        return json.dumps(obj, ensure_ascii=False)

    def mesaj(self, text):
        threading.Thread(target=self._chat, args=(text,), daemon=True).start()

    def _chat(self, text):
        try:
            mesaj_isle(text, self.brain, KISILIK, self._js, TOOLS)
        except Exception as e:
            # Hata olursa UI'da hata mesaji goster — UI donmesin
            try:
                self._js("BasakUI.error(" + self._j("Beklenmeyen hata: " + str(e)[:200]) + ")")
            except Exception:
                pass
            return

        if self.tts_on:
            try:
                if self.tts is None:
                    self.tts = TTS(on_level=self._ses_seviyesi)
                gecmis = yukle(HISTORY_FILE, [])
                if gecmis:
                    self.tts.speak(gecmis[-1].get("content", ""))
            except Exception:
                pass

    def dinle(self):
        threading.Thread(target=self._dinle, daemon=True).start()

    def _dinle(self):
        self._js("BasakUI.listening(true)")
        try:
            if self.stt is None:
                self.stt = STT()
            text = self.stt.dinle()
        except Exception as e:
            self._js("BasakUI.listening(false)")
            self._js("BasakUI.error(" + self._j("Mikrofon hatasi: " + str(e)) + ")")
            return
        self._js("BasakUI.listening(false)")
        if text:
            self._js("BasakUI.sttResult(" + self._j(text) + ")")

    def bugunku_hatirlatmalar(self):
        """Bugunku hatirlatmalari dondurur (UI icin)."""
        from tools.reminders import bugunku_hatirlatmalar
        return bugunku_hatirlatmalar(KNOWLEDGE_DIR, GOREVLER_FILE)

    def boot(self):
        modeller = self.brain.yerel_modeller()
        model = None
        if modeller:
            kayitli = yukle(SETTINGS_FILE, {}).get("model")
            model = kayitli if kayitli in modeller else modeller[0]
        # Bugunku hatirlatmalari al
        try:
            hatirlatma = self.bugunku_hatirlatmalar()
            hatirlatma_metni = hatirlatma.get("result", "")
        except Exception:
            hatirlatma_metni = ""

        return {
            "ok": bool(modeller), "models": modeller or [], "model": model,
            "cloud": self.brain.bulut_musait(),
            "tts_on": self.tts_on, "reminders": hatirlatma_metni,
        }

    def set_model(self, m):
        kaydet(SETTINGS_FILE, {**yukle(SETTINGS_FILE, {}), "model": m})
        return {"ok": True}

    def set_key(self, key):
        self.brain.anahtar_ayarla(key)
        return {"ok": True, "cloud": self.brain.bulut_musait()}

    def set_tts(self, on):
        self.tts_on = bool(on)
        kaydet(SETTINGS_FILE, {**yukle(SETTINGS_FILE, {}), "tts_on": self.tts_on})
        return {"ok": True, "tts_on": self.tts_on}

    def clear(self):
        try:
            os.remove(HISTORY_FILE)
        except OSError:
            pass
        return {"ok": True}

    def knowledge(self):
        try:
            return sorted(os.listdir(KNOWLEDGE_DIR))
        except OSError:
            return []

    def quit(self):
        """Tamamen kapat: tepsiyi durdur + pencereyi yok et (kill switch)."""
        try:
            from tray import durdur
            durdur()
        except Exception:
            pass
        threading.Thread(
            target=lambda: webview.windows[0].destroy() if webview.windows else None,
            daemon=True,
        ).start()


def _pencere_goster():
    if webview.windows:
        webview.windows[0].show()


def _pencere_gizle():
    if webview.windows:
        webview.windows[0].hide()


def _kapanista_gizle():
    """X'e basildi: kapatma — tepside yasamaya devam et."""
    _pencere_gizle()
    return False  # False = kapatmayi iptal et


def main():
    init_cache()
    api = Api()
    pencere = webview.create_window(
        "Basak", INDEX_FILE, js_api=api,
        width=1100, height=720, min_size=(900, 600),
        background_color="#0E1117",
    )
    # X butonu = gizle; tamamen kapatma sadece tepsi menusunden
    pencere.events.closing += _kapanista_gizle

    def _tepsi_baslat():
        import time
        time.sleep(1.5)  # pencere olusmadan ikon baslamasin
        from tray import baslat
        baslat(_pencere_goster, _pencere_gizle, api.quit)

    threading.Thread(target=_tepsi_baslat, daemon=True).start()
    webview.start()


if __name__ == "__main__":
    main()
