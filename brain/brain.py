"""brain/brain.py — Başak'ın ana beyin sınıfı."""

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
                logger.warning("Groq başlatılamadı: %s", e)

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

    def yerel_cevap(self, messages, model):
        """Yerel modelden cevap alır (rate limit fallback)."""
        return self._ollama.cevapla(messages, model)

    def cevapla(self, messages, yerel_model, tools=None, force_groq=False):
        """Mesajlara cevap verir."""
        if tools and self.bulut_musait():
            try:
                return self._groq.cevapla(messages, tools=tools), "groq"
            except Exception as e:
                logger.warning("Groq hatası: %s", e)

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
                    logger.warning("Groq hatası: %s", e)

        try:
            yanit = self._ollama.cevapla(messages, yerel_model)
            return {"content": yanit}, "yerel"
        except Exception as e:
            raise RuntimeError(f"Hiçbir model çalışmadı: {e}") from e
