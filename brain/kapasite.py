"""brain/kapasite.py — Model kapasite sinifi.

Ucretsiz/kucuk modeller agir muhakeme katmanlarindan (her mesajda
embedding/hafiza aramasi, genis tool kisa listesi, uzun tool dongusu)
muaf tutulur; guclu modellerde katmanlar acik kalir.

2026-09-12 (P4): karar ARTIK provider havuzundan cikarilmaz.
Sira: gate_modu > acik aile > model_adi (aile cozucuyle) > tek kaynak
pini > tekduze-kucuk havuz > varsayilan (guclu — kilitli davranis).

Havuzda guclu saglayici olmasi turu guclu saydirmaz: fiilen secilecek
model bilinmiyorsa varsayilan gecerlidir; flow.py bilinen ilk adayın
ailesini ayrıca verir (yaklasik on-secim).
"""

import json
import os

from brain.model_family import coz as _aile_coz

import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTINGS_FILE = os.path.join(BASE, "ayarlar.json")

# Aileye gore guc: P3 cozucunun etiketleri. Bilinmeyen aile ASLA
# buraya yazilmaz — varsayilana (guclu) duser (kilitli davranis).
GUCLU_AILE = frozenset((
    "gpt-oss", "llama", "gemini-flash", "gemini-pro", "gemini",
    "command-a", "command-r", "nemotron", "glm", "glm-flash",
    "deepseek", "kimi",
))
KUCUK_AILE = frozenset((
    "llama-small", "gemini-flash-lite", "qwen", "phi", "kilo-auto",
))

# Tek kaynak pinleri (model bilinmiyorsa guvenli varsayim).
# 2026-09-12: cloudflare gucluden CIKARILDI (varsayilan 3B sinifi),
# openrouter iki setten de cikarildi (dinamik :free), nvidia kucukte
# KALDI (ucretsiz hatta kucuk/hizli varsayim guvenlidir; aile biliniyorsa
# aile gecerlidir).
GUCLU_KAYNAK = {"groq", "glm", "gemini", "deepseek", "cohere"}
KUCUK_KAYNAK = {"ollama", "yerel", "kilo", "qwen", "nvidia",
                "cloudflare"}


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


def mod_kapasite(model_adi=None, kaynak=None, kaynaklar=None,
                 aile=None):
    """Kapasite karari: gate_modu > aile > model_adi > kaynak > havuz.

    aile: model_family.coz() etiketi (örn. "llama-small"). Verildiyse
        tek başına karar verir (unknown → varsayilana duser).
    model_adi: aile cozucuyle siniflanir (alt-dizgi tuzagi yok).
    kaynak: tek provider pini (guvenli varsayim).
    kaynaklar: havuz YALNIZCA tekduze-kucukse kucuk saydirir; karisik
        veya bilinmeyen havuz varsayilana duser (havuzdaki guclu uye
        turu guclu yapmaz — P4 duzeltmesi).
    Belirsizlikte guclu (kilitli davranis korunur).
    """
    mod = _mod()
    if mod == "sikı" or mod == "siki":
        return Kapasite(True, mod)
    if mod == "gevsek" or mod == "gevsek":
        return Kapasite(False, mod)

    if aile:
        if aile in KUCUK_AILE:
            return Kapasite(False, mod)
        if aile in GUCLU_AILE:
            return Kapasite(True, mod)
        # unknown/dinamik-disi aile → varsayilana dus

    if model_adi:
        cozulen = _aile_coz(kaynak, model_adi)
        if cozulen in KUCUK_AILE:
            return Kapasite(False, mod)
        if cozulen in GUCLU_AILE:
            return Kapasite(True, mod)
        # cozulemedi → asagidaki kurallara dus

    # kaynak adi dogrudan kucuk/guclu pininde mi?
    if kaynak:
        if kaynak in GUCLU_KAYNAK:
            return Kapasite(True, mod)
        if kaynak in KUCUK_KAYNAK:
            return Kapasite(False, mod)

    # Havuz: yalniz TEKDUZE-kucukse kucuk; karisik/bilinmeyen varsayilan.
    if kaynaklar:
        havuz = [str(k).lower() for k in kaynaklar]
        if havuz and all(k in KUCUK_KAYNAK for k in havuz):
            return Kapasite(False, mod)

    # Belirsizlik: mevcut davranisi koru (agir katmanlar acik)
    return Kapasite(True, mod)
