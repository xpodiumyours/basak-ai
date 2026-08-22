"""brain/ollama.py — Ollama yerel model entegrasyonu.

Yerel bilgisayardaki Ollama sunucusuna HTTP API uzerinden baglanir.
Tool calling destekli (qwen2.5:3b tools parametresiyle calisir).
"""

import json
import logging

import requests

logger = logging.getLogger(__name__)

OLLAMA_URL = "http://127.0.0.1:11434"


class OllamaClient:
    """Ollama yerel model istemcisi."""

    def __init__(self, base_url: str = OLLAMA_URL):
        self.base_url = base_url.rstrip("/")

    def musait(self) -> bool:
        """Ollama'nin calisip calismadigini kontrol eder."""
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=5)
            r.raise_for_status()
            return True
        except requests.RequestException:
            return False

    def modeller(self) -> list:
        """Mevcut yerel modellerin listesini dondurur."""
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

    def cevapla(self, messages: list, model: str, tools: list = None) -> dict:
        """Yerel modele mesaj gonderir ve yanit alir.

        Args:
            messages: Mesaj listesi (OpenAI formatinda).
            model: Kullanilacak model ismi (orn: qwen2.5:3b).
            tools: Tool tanimlari (opsiyonel). Gecilirse Ollama tool calling kullanir.

        Returns:
            dict: {"content": str, "tool_calls": list} formatinda yanit.

        Raises:
            RuntimeError: Ollama calismiyorsa.
            Exception: API hatasi olursa.
        """
        if not self.musait():
            raise RuntimeError("Ollama calismiyor — Ollama'yı baslatin")

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        if tools:
            payload["tools"] = tools

        r = requests.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=(5, 180),
        )
        r.raise_for_status()

        data = r.json()
        msg = data.get("message", {})

        # Tool calls var mi?
        tool_calls_raw = msg.get("tool_calls")
        if tool_calls_raw:
            tool_calls = []
            for tc in tool_calls_raw:
                func = tc.get("function", {})
                args = func.get("arguments", {})
                if not isinstance(args, str):
                    args = json.dumps(args) if args else "{}"
                tool_calls.append({
                    "id": f"call_{id(tc)}",
                    "type": "function",
                    "function": {
                        "name": func.get("name", ""),
                        "arguments": args,
                    }
                })
            return {"content": msg.get("content", ""), "tool_calls": tool_calls}

        return {"content": msg.get("content", "")}
