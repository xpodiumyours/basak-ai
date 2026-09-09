import sys
sys.path.insert(0, '.')
import os
import logging
logging.basicConfig(level=logging.INFO)

from brain.brain import Brain

brain = Brain()

# Test sending a message directly through brain.cevapla
messages = [
    {"role": "system", "content": "Sen Başak'sın — Casper'ın kişisel asistanısın. Türkçe, kısa, emoji yok."},
    {"role": "user", "content": "merhaba nasilsin?"}
]

try:
    result, gosterim = brain.cevapla(messages, "qwen2.5:7b")
    print("Result:", result)
    print("Gosterim:", gosterim)
except Exception as e:
    print("Error:", type(e).__name__, str(e)[:300])