import io
import json
import os
import threading

import numpy as np
import sounddevice as sd
import soundfile as sf
from faster_whisper import WhisperModel
from piper import PiperVoice

BASE = os.path.dirname(os.path.abspath(__file__))
VOICE_ONNX = os.path.join(BASE, "tr_TR-dfki-medium.onnx")
VOICE_JSON = os.path.join(BASE, "tr_TR-dfki-medium.onnx.json")
WHISPER_BOYUT = "base"
WHISPER_DTYPE = "int8"
SAMPLE_RATE = 16000


class TTS:
    def __init__(self):
        cfg = VOICE_JSON if os.path.exists(VOICE_JSON) else None
        self.voice = PiperVoice.load(VOICE_ONNX, config_path=cfg)
        self._lock = threading.Lock()

    def speak(self, text):
        text = (text or "").strip()
        if not text:
            return
        with self._lock:
            buf = io.BytesIO()
            with sf.SoundFile(
                buf, mode="w", samplerate=self.voice.config.sample_rate,
                channels=1, format="WAV",
            ) as f:
                self.voice.synthesize(text, f)
            buf.seek(0)
            data, sr = sf.read(buf, dtype="float32")
            sd.play(data, sr)
            sd.wait()


class STT:
    def __init__(self, model_boyut=WHISPER_BOYUT, dtype=WHISPER_DTYPE):
        self.model = WhisperModel(model_boyut, device="cpu", compute_type=dtype)
        self._lock = threading.Lock()

    def dinle(self, max_seconds=8, silence_sec=1.0, threshold=0.012):
        """Mikrofondan kaydeder; konuşma bitince (sessizlik) ya da süre dolunca transcribe eder."""
        block = 1024
        rec = []
        spoke = False
        silent_count = 0
        silence_limit = max(1, int(silence_sec * SAMPLE_RATE / block))
        with self._lock:
            with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16", blocksize=block) as stream:
                for _ in range(int(max_seconds * SAMPLE_RATE / block)):
                    data, _ = stream.read(block)
                    arr = data.flatten().astype("float32") / 32768.0
                    rec.append(arr)
                    energy = float(np.sqrt(np.mean(arr ** 2)))
                    if energy > threshold:
                        spoke = True
                        silent_count = 0
                    elif spoke:
                        silent_count += 1
                        if silent_count > silence_limit:
                            break
        if not rec:
            return ""
        audio = np.concatenate(rec)
        with self._lock:
            segs, _ = self.model.transcribe(audio, language="tr", vad_filter=True)
            text = " ".join(s.text for s in segs).strip()
        return text

    def transcribe_dosya(self, path):
        with self._lock:
            segs, _ = self.model.transcribe(path, language="tr", vad_filter=True)
            return " ".join(s.text for s in segs).strip()
