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
from chat import mesaj_isle, yukle, kaydet, init_cache

BASE = os.path.dirname(os.path.abspath(__file__))
UI_DIR = os.path.join(BASE, "ui")
INDEX_FILE = os.path.join(UI_DIR, "index.html")
HISTORY_FILE = os.path.join(BASE, "gecmis.json")
SETTINGS_FILE = os.path.join(BASE, "ayarlar.json")
KNOWLEDGE_DIR = os.path.join(BASE, "knowledge")

KISILIK = (
    "Sen Basak'sin — Casper'in kisisel yapay zeka asistani.\n\n"
    "KISILIK:\n"
    "OM KIMLIK: Senin adin BASAK. Asla Casper deme.\n"
    "- Kendini tanitirken Ben Basak, senin kisisel asistaniyim de.\n"
    "- Kullaniciya HER ZAMAN sen de, siz ASLA.\n"
    "- Samimi, sicak, arkadas gibi konus.\n"
    "- Kullanicinin adi Casper. Ona 'Casper' de.\n"
    "- HER ZAMAN 'sen' kullan, 'siz' ASLA.\n"
    "- Resmi konusma yapma.\n"
    "- Kisa, net, dogal cevaplar ver.\n"
    "- Emoji kullanma. Duz metin yaz. SADECE TURKCE.\n\n"
    "TOOL KURALLARI:\n"
    "- Yap/al/git/hazirla → add_task\n"
    "- Gorevlerim/ne yapacagim → list_tasks\n"
    "- Bitirdim/tamamladim → complete_task\n"
    "- Hatirla/not al → save_note\n"
    "- Hava/fiyat → web_search\n"
    "- Selam/veda → tool KULLANMA\n\n"
    "KISITLAR:\n"
    "- Bilmedigini soyle, uydurma.\n"
    "- Kisa ve oz ol."
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
                    self.tts = TTS()
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
            "cloud": self.brain.bulut_musait(), "gucle_mod": self.brain.gucle_mod,
            "tts_on": self.tts_on, "reminders": hatirlatma_metni,
        }

    def set_model(self, m):
        kaydet(SETTINGS_FILE, {**yukle(SETTINGS_FILE, {}), "model": m})
        return {"ok": True}

    def set_cloud(self, on):
        self.brain.gucle_mod_ayarla(on)
        return {"ok": True, "gucle_mod": self.brain.gucle_mod}

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
        threading.Thread(
            target=lambda: webview.windows[0].destroy() if webview.windows else None,
            daemon=True,
        ).start()


def main():
    init_cache()
    api = Api()
    webview.create_window(
        "Basak", INDEX_FILE, js_api=api,
        width=1100, height=720, min_size=(900, 600),
        background_color="#0E1117",
    )
    webview.start()


if __name__ == "__main__":
    main()
