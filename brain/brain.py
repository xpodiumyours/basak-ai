"""brain/brain.py — Basak'in ana beyin sinifi.

Faz 0 duzeltmesi: Yerel Ollama artik tool calling destekliyor.
Groq sadece gucte mod aciksa veya uzun sorularda kullaniliyor.
"""

import json
import logging
import os

from brain.groq import GroqClient, MODELLER
from brain.ollama import OllamaClient

logger = logging.getLogger(__name__)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTINGS_FILE = os.path.join(BASE, "ayarlar.json")


def _ayar_yukle() -> dict:
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _ayar_kaydet(veri: dict):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(veri, f, ensure_ascii=False, indent=2)
    except OSError as e:
        logger.error("Ayarlar kaydedilemedi: %s", e)


class Brain:
    def __init__(self):
        ayar = _ayar_yukle()
        self.groq_key = (
            os.environ.get("GROQ_API_KEY") or ayar.get("groq_key") or ""
        )
        self.groq_model = ayar.get("groq_model", MODELLER["varsayilan"])
        self.gucle_mod = bool(ayar.get("gucle_mod", False))
        self._groq = None
        self._ollama = OllamaClient()
        if self.groq_key:
            try:
                self._groq = GroqClient(self.groq_key, self.groq_model)
            except ValueError as e:
                logger.warning("Groq baslatilamadi: %s", e)

    def bulut_musait(self) -> bool:
        return self._groq is not None and self._groq.musait()

    def gucle_mod_ayarla(self, ac: bool):
        self.gucle_mod = bool(ac)
        ayar = _ayar_yukle()
        ayar["gucle_mod"] = self.gucle_mod
        _ayar_kaydet(ayar)

    def anahtar_ayarla(self, key: str):
        self.groq_key = key.strip()
        ayar = _ayar_yukle()
        ayar["groq_key"] = self.groq_key
        _ayar_kaydet(ayar)
        if self.groq_key:
            try:
                self._groq = GroqClient(self.groq_key, self.groq_model)
            except ValueError:
                self._groq = None
        else:
            self._groq = None

    def groq_model_ayarla(self, model_adi: str):
        if model_adi in MODELLER:
            self.groq_model = MODELLER[model_adi]
        else:
            self.groq_model = model_adi
        ayar = _ayar_yukle()
        ayar["groq_model"] = self.groq_model
        _ayar_kaydet(ayar)
        if self.groq_key:
            try:
                self._groq = GroqClient(self.groq_key, self.groq_model)
            except ValueError:
                self._groq = None

    def yerel_modeller(self) -> list:
        return self._ollama.modeller()

    def yerel_cevap(self, messages, model, tools=None):
        """Yerel modelden cevap alir (tools destekli)."""
        return self._ollama.cevapla(messages, model, tools=tools)

    def cevapla(self, messages, yerel_model, tools=None, force_groq=False):
        """Mesajlara cevap verir.

        Oncelik:
        1. Tools varsa → Groq dene (tool calling icin guclu model)
           Groq basarisizsa → Ollama'ya dus (tools ile)
        2. Guclu mod aciksa → Groq
        3. Uzun soru (15+ kelime) → Groq
        4. Diger → Ollama (hizli, ucretsiz, offline)
        """
        # 1. Tools varsa: once Groq dene
        if tools and self.bulut_musait():
            try:
                return self._groq.cevapla(messages, tools=tools), "groq"
            except Exception as e:
                logger.warning("Groq hatasi (tools fallback): %s", e)
                # Groq basarisizsa Ollama ile tools dene
                try:
                    return self._ollama.cevapla(messages, yerel_model, tools=tools), "yerel"
                except Exception as e2:
                    logger.warning("Ollama tools hatasi: %s", e2)

        # 2. Guclu mod veya uzun soru → Groq
        if self.bulut_musait():
            son_kullanici = ""
            for m in reversed(messages):
                if m.get("role") == "user":
                    son_kullanici = m.get("content", "")
                    break
            if force_groq or self.gucle_mod or len(son_kullanici.split()) >= 15:
                try:
                    return self._groq.cevapla(messages), "groq"
                except Exception as e:
                    logger.warning("Groq hatasi: %s", e)

        # 3. Varsayilan: Ollama
        try:
            yanit = self._ollama.cevapla(messages, yerel_model, tools=tools)
            return yanit, "yerel"
        except Exception as e:
            raise RuntimeError(f"Hicbir model calismadi: {e}") from e
