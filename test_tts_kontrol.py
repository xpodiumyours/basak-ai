"""test_tts_kontrol.py — Piper ses dosyası yerinde mi? (tek seferlik kontrol)

2026-09-19: Başak konuşmuyordu çünkü `tr_TR-dfki-medium.onnx` dosyası
proje kökünde YOKTU; TTS() çağrısı sessizce patlıyordu. Bu script
dosyanın varlığını ve modelin yüklenebildiğini doğrular.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BASE = os.path.dirname(os.path.abspath(__file__))
ONNX = os.path.join(BASE, "tr_TR-dfki-medium.onnx")
JSON = os.path.join(BASE, "tr_TR-dfki-medium.onnx.json")

print("onnx var mi :", os.path.isfile(ONNX),
      os.path.getsize(ONNX) if os.path.isfile(ONNX) else "-")
print("json var mi :", os.path.isfile(JSON))

try:
    from voice.tts import TTS
    tts = TTS()
    print("TTS yuklendi, ornekleme frekansi:", tts.voice.config.sample_rate)
except Exception as e:
    print("TTS HATA:", type(e).__name__, e)
