"""voice/tts.py — Piper TTS entegrasyonu.

Piper'ın Türkçe ses modeli ile metni sese dönüştürür.
Thread-safe: aynı anda birden fazla çağrıda kilit kullanır.
"""

import io
import logging
import os
import threading
import time

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
    İsteğe bağlı on_level geri çağrısıyla çalma sırasında 50 ms'lik
    pencereler hâlinde ses yüksekliğini (0..1) dışarıya bildirir.
    """

    def __init__(self, on_level=None):
        cfg = VOICE_JSON if os.path.exists(VOICE_JSON) else None
        self.voice = PiperVoice.load(VOICE_ONNX, config_path=cfg)
        self._lock = threading.Lock()
        self.on_level = on_level

    def speak(self, text: str):
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

            adim = max(1, int(sr * 0.05))
            parca = len(data) // adim
            zarf = None
            if parca > 0 and self.on_level is not None:
                import numpy as np

                kesit = data[: parca * adim].reshape(parca, adim)
                zarf = np.sqrt(np.mean(kesit.astype("float64") ** 2, axis=1))
                tepe = float(zarf.max())
                if tepe > 1e-6:
                    zarf = np.clip(zarf / tepe, 0.0, 1.0)

            sd.play(data, sr)
            if zarf is not None:
                for seviye in zarf:
                    try:
                        self.on_level(float(seviye))
                    except Exception:
                        pass
                    time.sleep(adim / sr)
            else:
                sd.wait()
                return
            sd.wait()
            try:
                self.on_level(0.0)
            except Exception:
                pass


# ---- DIS SES KOLU (yan kol, varsayilan kapali) ----
# Yerli Piper TTS aynen kalir; bu kol yalniz acikca cagrilinca calisir.
# Varsayilan kapali oldugu icin mevcut akis hic degismez.
_DIS_SES_ACIK = False


def dis_ses_acik_mi():
    """Dis ses kolu acik mi? Varsayilan False."""
    return bool(_DIS_SES_ACIK)


def dis_ses_oku(metin):
    """Dis ses kolu: henuz bagli dis servis yok, is yapmaz.

    Kol olarak durur; yerli TTS'e dokunmaz. Acikca acilmadikca
    hata vermeden bos doner.
    """
    if not _DIS_SES_ACIK:
        return {"ok": False, "neden": "dis ses kolu kapali"}
    metin = (metin or "").strip()
    if not metin:
        return {"ok": False, "neden": "bos metin"}
    return {"ok": False, "neden": "dis servis bagli degil"}
