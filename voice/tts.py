"""voice/tts.py — Piper TTS entegrasyonu.

Piper'ın Türkçe ses modeli ile metni sese dönüştürür.
Thread-safe: aynı anda birden fazla çağrıda kilit kullanır.
"""

import io
import logging
import os
import threading

import sounddevice as sd
import soundfile as sf
from piper import PiperVoice

logger = logging.getLogger(__name__)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOICE_ONNX = os.path.join(BASE, "tr_TR-dfki-medium.onnx")
VOICE_JSON = os.path.join(BASE, "tr_TR-dfki-medium.onnx.json")


class TTS:
    """Piper TTS sınıfı.

    Metni sese dönüştürür ve doğrudan hoparlöre çalar.
    """

    def __init__(self):
        """TTS modelini yükler.

        Raises:
            FileNotFoundError: Ses modeli dosyası bulunamazsa.
        """
        cfg = VOICE_JSON if os.path.exists(VOICE_JSON) else None
        self.voice = PiperVoice.load(VOICE_ONNX, config_path=cfg)
        self._lock = threading.Lock()

    def speak(self, text: str):
        """Verilen metni seslendirir.

        Args:
            text: Seslendirilecek metin. Boşsa hiçbir şey yapmaz.
        """
        text = (text or "").strip()
        if not text:
            return

        with self._lock:
            buf = io.BytesIO()
            with sf.SoundFile(
                buf,
                mode="w",
                samplerate=self.voice.config.sample_rate,
                channels=1,
                format="WAV",
            ) as f:
                self.voice.synthesize(text, f)
            buf.seek(0)
            data, sr = sf.read(buf, dtype="float32")
            sd.play(data, sr)
            sd.wait()
