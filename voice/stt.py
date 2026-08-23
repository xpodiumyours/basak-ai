"""voice/stt.py — Whisper STT entegrasyonu.

faster-whisper ile mikrofondan veya dosyadan sesi metne dönüştürür.
VAD (Voice Activity Detection) kullanarak konuşma bittiğini algılar.
"""

import logging
import threading

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

WHISPER_BOYUT = "base"
WHISPER_DTYPE = "int8"
SAMPLE_RATE = 16000


class STT:
    """Whisper STT sınıfı.

    Mikrofondan veya dosyadan sesi metne dönüştürür.
    """

    def __init__(self, model_boyut: str = WHISPER_BOYUT, dtype: str = WHISPER_DTYPE):
        """Whisper modelini yükler.

        Args:
            model_boyut: Model boyutu ("tiny", "base", "small", "medium", "large").
            dtype: Hesaplama tipi ("int8", "float16", "float32").
        """
        self.model = WhisperModel(model_boyut, device="cpu", compute_type=dtype)
        self._lock = threading.Lock()

    def dinle(self, max_seconds: int = 8, silence_sec: float = 1.0,
              threshold: float = 0.012) -> str:
        """Mikrofondan kaydeder; konuşma bitince transcribe eder.

        Sessizlik algılama kullanır: konuşma başladıktan sonra sessizlik
        olursa kaydı durdurur.

        Args:
            max_seconds: Maksimum kayıt süresi (saniye).
            silence_sec: Sessizlik eşiği (saniye). Bu kadar sessizlik varsa durur.
            threshold: Ses enerjisi eşiği. Üzerinde ses varsa "konuşma" sayılır.

        Returns:
            Transcribe edilmiş metin. Hiç ses yoksa boş string.
        """
        block = 1024
        rec = []
        spoke = False
        silent_count = 0
        silence_limit = max(1, int(silence_sec * SAMPLE_RATE / block))

        with self._lock:
            with sd.InputStream(
                samplerate=SAMPLE_RATE, channels=1, dtype="int16", blocksize=block
            ) as stream:
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

    def dinle_and_id(self, max_seconds: int = 8, silence_sec: float = 1.0,
                      threshold: float = 0.012) -> tuple:
        """Mikrofondan kaydeder; hem metin hem ses array döndürür.

        Konuşmacı tanıması için ses verisi de saklanır.

        Args:
            max_seconds: Maksimum kayıt süresi (saniye).
            silence_sec: Sessizlik eşiği (saniye).
            threshold: Ses enerjisi eşiği.

        Returns:
            (text, audio_array, sample_rate) tuple.
            audio_array float32, 0..1 aralığında normalize edilmiş.
            Hiç ses yoksa ("", None, SAMPLE_RATE).
        """
        block = 1024
        rec = []
        spoke = False
        silent_count = 0
        silence_limit = max(1, int(silence_sec * SAMPLE_RATE / block))

        with self._lock:
            with sd.InputStream(
                samplerate=SAMPLE_RATE, channels=1, dtype="int16", blocksize=block
            ) as stream:
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
            return "", None, SAMPLE_RATE

        audio = np.concatenate(rec)
        with self._lock:
            segs, _ = self.model.transcribe(audio, language="tr", vad_filter=True)
            text = " ".join(s.text for s in segs).strip()
        return text, audio, SAMPLE_RATE

    def transcribe_dosya(self, path: str) -> str:
        """Bir ses dosyasını metne dönüştürür.

        Args:
            path: Ses dosyası yolu.

        Returns:
            Transcribe edilmiş metin.
        """
        with self._lock:
            segs, _ = self.model.transcribe(path, language="tr", vad_filter=True)
            return " ".join(s.text for s in segs).strip()
