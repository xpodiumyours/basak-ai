import os
import json

import requests
from openai import OpenAI

OLLAMA_URL = "http://127.0.0.1:11434"
BASE = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(BASE, "ayarlar.json")

# Groq'un ücretsiz, güçlü modelleri
GROQ_MODEL = "llama-3.3-70b-versatile"

# Yerel model yetmez, buluta kaçılması gereken ipuçları
ZOR_IPUCU = [
    "kod", "code", "python", "javascript", "sql", "algoritma", "fonksiyon",
    "hesapla", "hesaplama", "analiz", "mantık", "çözümle", "neden", "karmaşık",
    "karşılaştır", "özetle", "araştır", "plan", "tasarla", "matematik", "denklem",
    "felsefe", "hukuk", "tıbbi", "teknik", "derin", "detaylı",
]


def _yukle_ayar():
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _kaydet_ayar(veri):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(veri, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


class Brain:
    def __init__(self):
        ayar = _yukle_ayar()
        self.groq_key = os.environ.get("GROQ_API_KEY") or ayar.get("groq_key") or ""
        self.gucle_mod = bool(ayar.get("gucle_mod", False))
        self.client = None
        if self.groq_key:
            try:
                self.client = OpenAI(
                    api_key=self.groq_key,
                    base_url="https://api.groq.com/openai/v1",
                )
            except Exception:
                self.client = None

    # ---- ayarlar ----
    def bulut_musait(self):
        return self.client is not None

    def gucle_mod_ayarla(self, ac):
        self.gucle_mod = bool(ac)
        ayar = _yukle_ayar()
        ayar["gucle_mod"] = self.gucle_mod
        _kaydet_ayar(ayar)

    def anahtar_ayarla(self, key):
        self.groq_key = key.strip()
        ayar = _yukle_ayar()
        ayar["groq_key"] = self.groq_key
        _kaydet_ayar(ayar)
        if self.groq_key:
            try:
                self.client = OpenAI(
                    api_key=self.groq_key,
                    base_url="https://api.groq.com/openai/v1",
                )
            except Exception:
                self.client = None
        else:
            self.client = None

    # ---- karar ----
    def bulut_mu(self, prompt):
        if not self.bulut_musait():
            return False
        if self.gucle_mod:
            return True
        p = (prompt or "").lower()
        kelime = p.split()
        # uzun soru veya ipucu kelimesi varsa buluta
        if len(kelime) >= 25:
            return True
        if any(ip in p for ip in ZOR_IPUCU):
            return True
        return False

    # ---- yerel (Ollama) ----
    def yerel_modeller(self):
        try:
            r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
            r.raise_for_status()
            return [m["name"] for m in r.json().get("models", []) if not m["name"].startswith("nomic")]
        except requests.RequestException:
            return None

    def yerel_cevap(self, messages, model):
        r = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={"model": model, "messages": messages, "stream": False},
            timeout=(5, 180),
        )
        r.raise_for_status()
        return r.json()["message"]["content"]

    # ---- bulut (Groq) ----
    def bulut_cevap(self, messages):
        resp = self.client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=2048,
        )
        return resp.choices[0].message.content

    # ---- birleşik ----
    def cevapla(self, messages, yerel_model):
        son_kullanici = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                son_kullanici = m.get("content", "")
                break
        if self.bulut_mu(son_kullanici):
            try:
                return self.bulut_cevap(messages), "groq"
            except Exception:
                # bulut patlarsa yerele düş
                pass
        return self.yerel_cevap(messages, yerel_model), "yerel"
