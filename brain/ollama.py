"""brain/ollama.py — Ollama yerel model entegrasyonu.

Yerel bilgisayardaki Ollama sunucusuna HTTP API üzerinden bağlanır.
Tool calling desteklemez — sadece düz metin sohbet.
"""

import logging

import requests

logger = logging.getLogger(__name__)

OLLAMA_URL = "http://127.0.0.1:11434"


class OllamaClient:
    """Ollama yerel model istemcisi.

    Ollama'nın REST API'sini kullanarak yerel modellerle konuşur.
    """

    def __init__(self, base_url: str = OLLAMA_URL):
        """Ollama client'ı başlatır.

        Args:
            base_url: Ollama API adresi. Varsayılan: http://127.0.0.1:11434
        """
        self.base_url = base_url.rstrip("/")

    def musait(self) -> bool:
        """Ollama'nın çalışıp çalışmadığını kontrol eder."""
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=5)
            r.raise_for_status()
            return True
        except requests.RequestException:
            return False

    def modeller(self) -> list:
        """Mevcut yerel modellerin listesini döndürür.

        Returns:
            Model isimleri listesi. Ollama çalışmıyorsa boş liste.
        """
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=5)
            r.raise_for_status()
            modeller = [
                m["name"]
                for m in r.json().get("models", [])
                if not m["name"].startswith("nomic")
            ]
            return modeller
        except requests.RequestException:
            return []

    def cevapla(self, messages: list, model: str) -> str:
        """Yerel modele mesaj gönderir ve yanıt alır.

        Args:
            messages: Mesaj listesi (OpenAI formatında).
            model: Kullanılacak model ismi (örn: qwen2.5:3b).

        Returns:
            Modelin yanıtı (string).

        Raises:
            RuntimeError: Ollama çalışmıyorsa.
            Exception: API hatası olursa.
        """
        if not self.musait():
            raise RuntimeError("Ollama çalışmıyor — Ollama'yı başlatın")

        r = requests.post(
            f"{self.base_url}/api/chat",
            json={"model": model, "messages": messages, "stream": False},
            timeout=(5, 180),
        )
        r.raise_for_status()
        return r.json()["message"]["content"]
