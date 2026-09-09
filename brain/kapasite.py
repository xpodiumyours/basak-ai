"""brain/kapasite.py — Model kapasite sinifi.

Ucretsiz/kucuk modeller agir muhakeme katmanlarindan (zorunlu tool
dayatmasi, her mesajda embedding/hafiza aramasi, uzun tool dongusu)
muaf tutulur; guclu modellerde katmanlar acik kalir.

Oncelik: ayarlar.json 'gate_modu' (sikı/gevsek) > kaynak/model deseniinden
cikarim. 'otomatik' ise mevcut saglayici havuzuna bakilir: havuzda guclu
bir bulut saglayici (groq/glm/gemini/...) varsa guclu, yalniz kucuk/yerel
varsa kucuk sayilir.

Kullanim:
    from brain.kapasite import mod_kapasite
    kap = mod_kapasite(kaynaklar=["groq", "ollama"])
    if kap.kucuk:
        ... hafif yollar ...
"""

import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTINGS_FILE = os.path.join(BASE, "ayarlar.json")

# Guclu sayilan bulut saglayicilari (buyuk/free-70b sinifi)
GUCLU_KAYNAK = {"groq", "glm", "gemini", "deepseek", "cohere",
                 "openrouter", "cloudflare"}
# Kucuk/yerel saglayicilar
KUCUK_KAYNAK = {"ollama", "nvidia", "kilo", "qwen", "yerel"}

GUCLU_MODEL = ("70b", "llama-3.3", "llama-3.1-70b", "llama-3-70b",
               "gemini-1.5-pro", "gemini-2", "gpt-", "claude")
KUCUK_MODEL = ("3b", "1.5b", "0.5b", "nemotron", "qwen", "llama-3.2",
               "llama3.2", "8b", "7b", "9b", "deepseek-r1-distill")


class Kapasite:
    def __init__(self, guclu, mod):
        self.guclu = bool(guclu)
        self.mod = mod

    @property
    def kucuk(self):
        return not self.guclu

    def __repr__(self):
        return "Kapasite(guclu=%s, mod=%s)" % (self.guclu, self.mod)


def _mod():
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8-sig") as f:
            return str(json.load(f).get("gate_modu", "otomatik")).lower()
    except (OSError, json.JSONDecodeError):
        return "otomatik"


def mod_kapasite(model_adi=None, kaynak=None, kaynaklar=None):
    """model_adi / kaynak / kaynaklar -> Kapasite.

    gate_modu='sikı' -> her zaman guclu; 'gevsek' -> her zaman kucuk.
    'otomatik': kaynak veya model adi deseninden; yoksa mevcut kaynaklar
    havuzuna bakilir (guclu saglayici varsa guclu). Belirsizlikte guclu
    (mevcut davranis korunur).
    """
    mod = _mod()
    if mod == "sikı" or mod == "siki":
        return Kapasite(True, mod)
    if mod == "gevsek" or mod == "gevsek":
        return Kapasite(False, mod)

    aranan = " ".join(str(x) for x in (kaynak, model_adi) if x).lower()
    if any(p in aranan for p in GUCLU_MODEL):
        return Kapasite(True, mod)
    if any(p in aranan for p in KUCUK_MODEL):
        return Kapasite(False, mod)

    # kaynak adi dogrudan kucuk/guclu havuzunda mi?
    if kaynak:
        if kaynak in GUCLU_KAYNAK:
            return Kapasite(True, mod)
        if kaynak in KUCUK_KAYNAK:
            return Kapasite(False, mod)

    if kaynaklar:
        if any(k in GUCLU_KAYNAK for k in kaynaklar):
            return Kapasite(True, mod)
        return Kapasite(False, mod)

    # Belirsizlik: mevcut davranisi koru (agir katmanlar acik)
    return Kapasite(True, mod)
