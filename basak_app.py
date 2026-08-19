import json
import os
import threading
import time

import webview

from brain import Brain
from voice import TTS, STT

BASE = os.path.dirname(os.path.abspath(__file__))
UI_DIR = os.path.join(BASE, "ui")
INDEX_FILE = os.path.join(UI_DIR, "index.html")
HISTORY_FILE = os.path.join(BASE, "gecmis.json")
SETTINGS_FILE = os.path.join(BASE, "ayarlar.json")
KNOWLEDGE_DIR = os.path.join(BASE, "knowledge")
KNOWLEDGE_MAX_CHARS = 4000  # yerel modelin bağlamını şişirmesin diye üst sınır
HATA_LOG = os.path.join(BASE, "hata.log")


def _log_hata(mesaj):
    """Sessizce yutulan hataları kalıcı bir yere yazar — daha önce hiçbir
    yere kaydedilmiyordu, UI'a ulaşamayan hata tamamen görünmez oluyordu."""
    try:
        with open(HATA_LOG, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S") + " " + mesaj + "\n")
    except OSError:
        pass

KISILIK = (
    "Senin adın Başak. Sen 'Qwen' değilsin, 'Alibaba' değilsin, hiçbir şirketin ürünü değilsin. "
    "Adın sorulduğunda 'Başak' diye cevap ver. "
    "Kullanıcının kişisel yapay zekâ asistanısın. "
    "Türkçe konuş, kısa ve net cevaplar ver. "
    "Kullanıcının adını öğren ve sonraki konuşmalarda hatırla. "
    "Bilmediğini uydurma, dürüst ol."
)


def _yukle(path, varsayilan):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return varsayilan


def _kaydet(path, veri):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(veri, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def _knowledge_context(limit=KNOWLEDGE_MAX_CHARS):
    """knowledge/ altındaki .md/.txt dosyalarını okuyup tek metne birleştirir.
    README.md hariç — o kullanım talimatı, kişisel bilgi değil."""
    try:
        dosyalar = sorted(
            ad for ad in os.listdir(KNOWLEDGE_DIR)
            if ad.lower().endswith((".md", ".txt")) and ad != "README.md"
        )
    except OSError:
        return ""
    parcalar = []
    kalan = limit
    for ad in dosyalar:
        if kalan <= 0:
            break
        try:
            with open(os.path.join(KNOWLEDGE_DIR, ad), "r", encoding="utf-8", errors="replace") as f:
                icerik = f.read().strip()
        except OSError:
            continue
        if not icerik:
            continue
        if len(icerik) > kalan:
            icerik = icerik[:kalan].rstrip() + "\n[...devamı kısaltıldı]"
        parcalar.append("### " + ad + "\n" + icerik)
        kalan -= len(icerik)
    return "\n\n".join(parcalar)


class Api:
    def __init__(self):
        self.brain = Brain()
        self.tts = None
        self.stt = None
        self.tts_on = bool(_yukle(SETTINGS_FILE, {}).get("tts_on", False))

    # ---------- yardımcılar ----------
    def _js(self, code):
        try:
            if webview.windows:
                webview.windows[0].evaluate_js(code)
            else:
                _log_hata("JS cagrisi atlandi (pencere hazir degil): " + code[:80])
        except Exception as e:
            _log_hata("JS cagrisi hata: " + str(e))

    def _j(self, obj):
        return json.dumps(obj, ensure_ascii=False)

    def _settings(self):
        return _yukle(SETTINGS_FILE, {})

    def _save_setting(self, key, val):
        s = self._settings()
        s[key] = val
        _kaydet(SETTINGS_FILE, s)

    def _load_history(self):
        return _yukle(HISTORY_FILE, [])

    def _save_history(self, data):
        _kaydet(HISTORY_FILE, data)

    def _tts(self):
        if self.tts is None:
            self.tts = TTS()
        return self.tts

    # ---------- açılış ----------
    def boot(self):
        modeller = self.brain.yerel_modeller()
        model = None
        if modeller:
            kayitli = self._settings().get("model")
            model = kayitli if kayitli in modeller else modeller[0]
        return {
            "ok": bool(modeller),
            "models": modeller or [],
            "model": model,
            "cloud": self.brain.bulut_musait(),
            "gucle_mod": self.brain.gucle_mod,
            "tts_on": self.tts_on,
        }

    # ---------- sohbet ----------
    def mesaj(self, text):
        threading.Thread(target=self._chat, args=(text,), daemon=True).start()

    def _chat(self, text):
        text = (text or "").strip()
        self._js("BasakUI.thinking()")
        if not text:
            self._js("BasakUI.error(" + self._j("Boş mesaj") + ")")
            return
        modeller = self.brain.yerel_modeller()
        if not modeller:
            self._js("BasakUI.error(" + self._j("Ollama çalışmıyor") + ")")
            return
        model = self._settings().get("model")
        if model not in modeller:
            model = modeller[0]
        gecmis = [m for m in self._load_history() if m.get("role") != "system"]
        mesajlar = [{"role": "system", "content": KISILIK}]
        bilgi = _knowledge_context()
        if bilgi:
            mesajlar.append({
                "role": "system",
                "content": (
                    "Kullanıcının kişisel bilgi notları — gerekirse cevapta kullan, "
                    "sorulmadıkça kendiliğinden tekrarlama:\n\n" + bilgi
                ),
            })
        mesajlar += gecmis[-20:] + [{"role": "user", "content": text}]
        try:
            cevap, kaynak = self.brain.cevapla(mesajlar, model)
        except Exception as e:
            _log_hata("Beyin hatasi: " + str(e))
            self._js("BasakUI.error(" + self._j("Beyin hatası: " + str(e)) + ")")
            return
        gecmis += [{"role": "user", "content": text}, {"role": "assistant", "content": cevap}]
        self._save_history(gecmis[-40:])
        self._js("BasakUI.reply(" + self._j(cevap) + ")")
        if self.tts_on:
            try:
                self._tts().speak(cevap)
            except Exception:
                pass

    # ---------- sesli dinle ----------
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
            self._js("BasakUI.error(" + self._j("Mikrofon hatası: " + str(e)) + ")")
            return
        self._js("BasakUI.listening(false)")
        if text:
            self._js("BasakUI.sttResult(" + self._j(text) + ")")

    # ---------- ayarlar ----------
    def set_model(self, m):
        self._save_setting("model", m)
        return {"ok": True}

    def set_cloud(self, on):
        self.brain.gucle_mod_ayarla(on)
        return {"ok": True, "gucle_mod": self.brain.gucle_mod}

    def set_key(self, key):
        self.brain.anahtar_ayarla(key)
        return {"ok": True, "cloud": self.brain.bulut_musait()}

    def set_tts(self, on):
        self.tts_on = bool(on)
        self._save_setting("tts_on", self.tts_on)
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
    api = Api()
    webview.create_window(
        "Başak",
        INDEX_FILE,
        js_api=api,
        width=1100,
        height=720,
        min_size=(900, 600),
        background_color="#0E1117",
    )
    webview.start()


if __name__ == "__main__":
    main()
