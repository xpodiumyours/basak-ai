import sys
sys.path.insert(0, '.')
import os
import logging
logging.basicConfig(level=logging.INFO)

from brain.ollama import OllamaClient

client = OllamaClient()
print("Ollama musait:", client.musait())
print("Modeller:", client.modeller())

# Test a simple chat
messages = [
    {"role": "system", "content": "Sen Başak'sın — Casper'ın kişisel asistanısın. Türkçe, kısa, emoji yok."},
    {"role": "user", "content": "merhaba nasilsin?"}
]

try:
    result = client.cevapla(messages, "qwen2.5:7b")
    print("Cevap:", result)
except Exception as e:
    print("Hata:", type(e).__name__, str(e)[:200])