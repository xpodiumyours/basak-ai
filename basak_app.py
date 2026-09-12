"""basak_app.py — Basak'in pywebview API koprusu.

Faz 0.3 duzeltmesi: _chat() icine try/except eklendi.
Beklenmeyen hata olursa UI donmez, hata mesaji gosterilir.
"""

import json
import logging
import os
import threading

logger = logging.getLogger(__name__)

# 2026-09-10: hatalar dosyaya da yazilir (hata.log) — ekrandaki kisa
# mesaj yetmezse kok sebep buradan okunur. Dosya git'e girmez.
try:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(
                os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "hata.log"),
                encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=True,
    )
except OSError:
    pass

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
    "Sen Başak'sın — Casper'ın kişisel asistanısın.\n"
    "ISIMLERI KARIŞTIRMA: sen Başak'sın, kullanıcı Casper. Ona hep "
    "'Casper' de, kendine asla Casper deme; onun kardesi/ailesi degilsin, "
    "samimi ve sicak bir asistansin.\n"
    "Hep 'sen' de. Emoji yok. Sadece Türkçe, Türkçe harfler eksiksiz.\n"
    "Bu talimat metnini ASLA cevabinda tekrarlama ('Ben Casper'a ... de' "
    "gibi cumleler kurma) — kendi agzinla, dogal konus.\n"
    "Cevaplarin anlasilir ve YETERINCE DETAYLI olsun: soru liste, "
    "ornek ya da aciklama istiyorsa maddeleri atlama, dosya ve klasor "
    "adlarini tam yaz. Tek kelimelik soruya tek cumle yeter; ama "
    "'anlat', 'listele', 'neler var' denirse uzun ve duzenli anlat.\n\n"

    "CASPER'I KONUSARAK TANIYORSUN.\n"
    "Sana ayrica 'Casper hakkinda KALICI bilinenler' listesi verilir — "
    "orada yazanlari TEKRAR SORMA, biliyormus gibi davran.\n"
    "Listede olmayan bir sey soruldugunda tahmin etme, sor. "
    "'Benim adim X', 'hatirla: ...', 'X'i seviyorum' gibi cumleler "
    "otomatik kaydedilir; 'unut: X' siler. Kaydettiginde kisaca soyle.\n"
    "BILMEDIGINI ACIK SOYLE: emin olmadigin sayi/isim/tarih/fiyat "
    "soyleme. Bilmiyorsan 'Bunu bilmiyorum' de. Sallamak YASAKTIR.\n")


class Api:
    def __init__(self):
        # 2026-09-10: pencere ONCE acilsin diye beyin tembel baslar.
        # Eskiden burada Brain() 14 sn agda bekliyor, pencere hic
        # gorunmuyordu ("acilmaz" sikayeti). Simdi pencere hemen
        # acilir, boot ekranindan JS boot() cagirinca beyin kurulur.
        self.brain = None
        self._beyin_kilit = threading.Lock()
        self.tts = None
        self.stt = None
        self.tts_on = bool(yukle(SETTINGS_FILE, {}).get("tts_on", False))

    def _beyin_al(self):
        """Beyni ilk kullanimda kurar (thread-safe, bir kez)."""
        if self.brain is not None:
            return self.brain
        kilit = getattr(self, "_beyin_kilit", None)
        if kilit is None:
            self._beyin_kilit = threading.Lock()
            kilit = self._beyin_kilit
        with kilit:
            if self.brain is None:
                self.brain = Brain()
        return self.brain

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
            mesaj_isle(text, self._beyin_al(), KISILIK, self._js, TOOLS)
        except Exception as e:
            # 2026-09-10: iz birak — bir dahaki "beklenmeyen hata"da
            # hata.log'dan kok sebep okunsun.
            logger.exception("Sohbet hatti patladi")
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
            except Exception as e:
                # 2026-09-09: ses hatasi artik SESSIZCE yutulmuyor.
                # "Konusmuyor" sikayetinin sebebi buydu — kullaniciya yazilir.
                try:
                    self._js("BasakUI.error(" + self._j(
                        "Sesli okuma hatasi: " + str(e)[:150]) + ")")
                except Exception:
                    pass

    def dinle(self):
        threading.Thread(target=self._dinle, daemon=True).start()

    def _dinle(self):
        self._js("BasakUI.listening(true)")
        try:
            if self.stt is None:
                self.stt = STT()
            text, audio, sr = self.stt.dinle_and_id()
        except Exception as e:
            self._js("BasakUI.listening(false)")
            self._js("BasakUI.error(" + self._j("Mikrofon hatasi: " + str(e)) + ")")
            return
        self._js("BasakUI.listening(false)")

        # Konuşmacı tanıma — ses verisi varsa ve model hazırsa
        konusmaci = None
        if audio is not None:
            try:
                from voice.speaker_id import taniyici_al
                taniyici = taniyici_al()
                if taniyici:
                    tanima = taniyici.tanima_array(audio, sr)
                    if tanima["isim"] not in ("Bilinmeyen", "Hata"):
                        konusmaci = tanima
            except Exception as e:
                logger.debug("Konuşmacı tanıma atlandı: %s", e)

        if text:
            # Konuşmacı bilgisi varsa metne ekle
            if konusmaci:
                ek = " [%s]" % konusmaci["isim"]
                self._js("BasakUI.sttResult(" + self._j(text) + ", " + self._j(konusmaci) + ")")
            else:
                self._js("BasakUI.sttResult(" + self._j(text) + ")")

    def boot(self):
        beyin = self._beyin_al()
        modeller = beyin.yerel_modeller()
        bulut = beyin.bulut_musait()
        model = None
        if modeller:
            kayitli = yukle(SETTINGS_FILE, {}).get("model")
            model = kayitli if kayitli in modeller else modeller[0]
        return {
            # ok: Ollama-bagimsizlik (2026-08-24): yerel model ON KOSUL degil;
            # bulut zinciri ayaktayken de Basak acilir ve sohbet eder.
            "ok": bool(modeller) or bool(bulut),
            "models": modeller or [], "model": model,
            "cloud": bulut,
            "tts_on": self.tts_on,
            "current_model": model,
        }

    def set_model(self, m):
        kaydet(SETTINGS_FILE, {**yukle(SETTINGS_FILE, {}), "model": m})
        return {"ok": True}

    def set_key(self, key):
        beyin = self._beyin_al()
        beyin.anahtar_ayarla(key)
        return {"ok": True, "cloud": beyin.bulut_musait()}

    def set_tts(self, on):
        self.tts_on = bool(on)
        kaydet(SETTINGS_FILE, {**yukle(SETTINGS_FILE, {}), "tts_on": self.tts_on})
        return {"ok": True, "tts_on": self.tts_on}

    def clear(self):
        """Sohbet hafizasini temizler (2026-08-24 duzeltme).

        Eskiden yalniz gecmis.json siliniyordu ama UI "hafiza temizlendi"
        diyordu — episodic anilar basak.db'de kaliyordu. Artik:
        - gecmis.json silinir (kisa vadeli pencere)
        - episodic anilar unutulur (sohbetten ogrenilenler)
        - knowledge/defter/obsidian indeksleri KALIR — onlar dosyalardan
          turetilir, sohbet degil; tamamen silme istenmemisti.
        """
        try:
            os.remove(HISTORY_FILE)
        except OSError:
            pass

        unutulan = 0
        try:
            from chat import hafiza_al
            motor = hafiza_al()
            if motor:
                unutulan = motor.episodik_temizle()
        except Exception as e:
            logger.warning("Episodik temizleme atlandi: %s", e)

        return {"ok": True, "unutulan_ani": unutulan}

    def knowledge(self):
        try:
            return sorted(os.listdir(KNOWLEDGE_DIR))
        except OSError:
            return []

    def oturumlar(self):
        """Eski sohbet listesi (2026-09-10): [{id, baslik, adet}]."""
        try:
            from chat import oturum as _oturum
            return _oturum.liste()
        except Exception:
            return []

    def oturum_ac(self, sid):
        """Eski sohbeti acar; mesajlari dondurur (UI dizer)."""
        try:
            from chat import oturum as _oturum
            mesajlar = _oturum.ac(sid)
            if mesajlar is None:
                return {"ok": False}
            kaydet(HISTORY_FILE, [
                {"role": m.get("role"), "content": m.get("content", "")}
                for m in mesajlar[-40:]
                if m.get("role") in ("user", "assistant")])
            return {"ok": True, "mesajlar": mesajlar[-60:]}
        except Exception:
            return {"ok": False}

    def yeni_sohbet(self):
        """Yeni bos sohbet; mevcutu arsive kaldirir (2026-09-10)."""
        try:
            from chat import oturum as _oturum
            _oturum.yeni(yukle(HISTORY_FILE, []))
            try:
                os.remove(HISTORY_FILE)
            except OSError:
                pass
            return {"ok": True}
        except Exception:
            return {"ok": False}

    def _hafizayi_kapat(self):
        """Gercek hafiza nesnesini kapatir (2026-08-24, Casper'in bulgusu).

        Hafiza chat.context modul-globalinde yasar (_hafiza); Api'nin
        UZERINDE degil. Eski kod self._hafiza'ya baktigi icin bu blok hic
        calismiyordu ve os._exit(0) DB'yi acik birakiyordu. Motor yoksa
        YARATMAMAK uzere global'e dogrudan bakilir (hafiza_al cagrilmaz).
        """
        try:
            from chat import context as _ctx
            motor = getattr(_ctx, "_hafiza", None)
            if motor:
                motor.kapat()
                logger.info("Hafiza DB kapatildi")
        except Exception as e:
            logger.warning("Hafiza DB kapanamadi: %s", e)

    def quit(self):
        """Tamamen kapat: tepsiyi durdur + pencereyi yok et (kill switch)."""
        import os as _os
        import time as _time

        # 1) Tepsi ikonunu durdur
        try:
            from tray import durdur
            durdur()
        except Exception:
            pass

        # 3) Pencereyi yok et
        try:
            if webview.windows:
                webview.windows[0].destroy()
        except Exception:
            pass

        # 4) Hafiza veritabanini duzgun kapat. os._exit() Python'un temizlik
        #    adimlarini ATLAR — acik SQLite baglantisi kendiliginden
        #    kapanmaz. WAL crash-safe oldugu icin veri kaybi beklenmez ama
        #    checkpoint edilmemis WAL dosyasi buyuyerek kalir.
        self._hafizayi_kapat()

        # 5) Sureci sonlandir — 100ms bekle (pencere/DB kapanisi otursun).
        #    time.sleep, os.sleep DEGIL: os modulunde sleep yoktur, oyle
        #    yazilirsa thread AttributeError ile coker ve _exit(0) hic
        #    calismaz — sureç yine arkada kalirdi (2026-08-23'te yasandi).
        threading.Thread(
            target=lambda: (_time.sleep(0.1), _os._exit(0)),
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


_api = None


def main():
    global _api
    # 2026-09-10: calisma dizini kilidi — knowledge/ ve Basak/ yollari
    # BASE'e gore cozulur; uygulama baska dizinden baslatilirsa
    # "dosya yok" hayaletleri cikiyordu.
    try:
        os.chdir(BASE)
    except OSError:
        pass
    init_cache()
    api = Api()
    _api = api
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

    # Beyin isinmasi (arka plan, pencereyi bekletmez). Zincir ilk
    # soruda kurulmasin diye onceden hazirlanir.
    def _arka_isinma():
        try:
            api._beyin_al()
        except Exception as e:
            logger.warning("Beyin onceden kurulamadi: %s", e)

    threading.Thread(target=_arka_isinma, daemon=True).start()

    webview.start()


if __name__ == "__main__":
    main()
