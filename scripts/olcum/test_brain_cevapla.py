"""test_brain_cevapla.py — beyin gerçekten cevap veriyor mu? (elle kontrol)

Canlı ağ çağrısı yapar; CI koşmaz (bkz. .github/workflows/test.yml).
Kosum: python scripts/olcum/test_brain_cevapla.py
"""

import os
import sys

# Depo kokunu __file__ uzerinden bul; calisma dizinine bagimli degildir.
sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

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