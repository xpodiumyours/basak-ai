"""voice — Başak'ın ses modülleri.

- tts.py: Piper TTS (metin → ses)
- stt.py: Whisper STT (ses → metin)

TEMBEL YÜKLEME (2026-10-13). Neden:
  Bu paket önceden modül yüklenirken TTS ve STT'yi içe aktarıyordu.
  `voice/tts.py` -> `sounddevice` -> PortAudio sistem kütüphanesi.
  Windows'ta kurulu (requirements'ta `sys_platform == "win32"`), fakat
  sunucuda/başsız ortamda YOK. Sonuç: `import voice` — dolayısıyla
  `import basak_app` — Linux'ta hiç yüklenemiyordu ve test paketi daha
  TOPLANIRKEN düşüyordu ("PortAudio library not found"; 2026-10-13
  ölçümü). Ses kütüphanesi, ses kullanılana kadar yüklenmek zorunda
  değildir: isim yalnız istendiğinde çözülür (PEP 562).

  Davranış AYNI kalır: `from voice import TTS, STT` ve `voice.TTS`
  çalışır; yalnız içe aktarma anı ertelenir. Ses gerçekten kullanılırken
  eksik kütüphane yine aynı ImportError'ı verir — hata gizlenmez.
"""

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - yalnız tip denetimi
    from voice.stt import STT
    from voice.tts import TTS

__all__ = ["TTS", "STT"]

# isim -> (modul, sinif). Kopya değil, çözümleme tablosu.
_TEMBEL = {
    "TTS": ("voice.tts", "TTS"),
    "STT": ("voice.stt", "STT"),
}


def __getattr__(ad):
    try:
        modul_adi, sinif_adi = _TEMBEL[ad]
    except KeyError:
        raise AttributeError(
            "module %r has no attribute %r" % (__name__, ad)) from None
    deger = getattr(importlib.import_module(modul_adi), sinif_adi)
    globals()[ad] = deger          # ikinci erişimde tekrar çözme
    return deger


def __dir__():
    return sorted(set(globals()) | set(__all__))
