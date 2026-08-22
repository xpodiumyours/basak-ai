"""voice/speaker_id.py — Konuşmacı tanıma (Speaker Identification).

pyannote/wespeaker-voxceleb-resnet34-LM modeli ile ses embedding üretir,
kayıtlı konuşmacılarla karşılaştırarak kimin konuştuğunu tanır.

Akış:
  1. Modeli yükle (lazy, ilk kullanımda)
  2. Sesi embedding'e dönüştür
  3. Kayıtlı konuşmacı embedding'leriyle cosine similarity hesapla
  4. Eşik üzerindeyse konuşmacıyı tanı, değilse "Bilinmeyen" de

Kullanım:
  tanıyıcı = KonusmaciTaniyici()
  isim = tanıyıcı.tanima("ornek.wav")
  # veya numpy array ile:
  isim = tanıyıcı.tanima_array(audio_array, sample_rate=16000)
"""

import logging
import os
import threading
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# Model sabitleri
MODEL_ID = "pyannote/wespeaker-voxceleb-resnet34-LM"
EMBED_DIM = 256  # wespeaker ResNet34 embedding boyutu
COSINE_ESIK = 0.65  # Kabul eşiği (optimal: 0.60-0.75 arası)

# HF token
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_AYARLAR_DOSYASI = os.path.join(_BASE, "ayarlar.json")


def _hf_token_oku() -> str:
    """ayarlar.json veya environment'dan HF token okur."""
    import json
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if token:
        return token
    try:
        with open(_AYARLAR_DOSYASI, "r", encoding="utf-8-sig") as f:
            ayarlar = json.load(f)
        return ayarlar.get("hf_token", "")
    except (OSError, json.JSONDecodeError):
        return ""


class KonusmaciTaniyici:
    """Konuşmacı tanıma motoru.

    wespeaker modeli ile ses embedding üretir ve kayıtlı
    konuşmacılarla cosine similarity ile eşleştirir.
    """

    def __init__(self, esik: float = COSINE_ESIK):
        self._model = None
        self._inference = None
        self._lock = threading.Lock()
        self.esik = esik
        self._konusmacilar: dict[str, np.ndarray] = {}  # isim -> ortalama embedding

    def _modeli_yukle(self):
        """Wespeaker modelini lazy-load eder (thread-safe)."""
        if self._model is not None:
            return

        with self._lock:
            if self._model is not None:
                return
            try:
                from pyannote.audio import Model, Inference

                hf_token = _hf_token_oku()
                kwargs = {"token": hf_token} if hf_token else {}

                self._model = Model.from_pretrained(MODEL_ID, **kwargs)
                self._inference = Inference(self._model, window="whole")
                logger.info("Wespeaker modeli yuklendi: %s", MODEL_ID)
            except Exception as e:
                logger.error("Wespeaker modeli yuklenemedi: %s", e)
                raise

    def embedding_uret(self, audio_path: str) -> Optional[np.ndarray]:
        """Ses dosyasından embedding üretir.

        Args:
            audio_path: WAV/MP3/etc. dosya yolu.

        Returns:
            (256,) boyutunda numpy array veya hata olursa None.
        """
        self._modeli_yukle()
        try:
            embedding = self._inference(audio_path)
            # Normalize et (cosine similarity için gerekli)
            norm = np.linalg.norm(embedding)
            if norm > 1e-8:
                embedding = embedding / norm
            return embedding
        except Exception as e:
            logger.error("Embedding uretimi hatasi (%s): %s", audio_path, e)
            return None

    def embedding_uret_array(self, audio: np.ndarray, sample_rate: int = 16000) -> Optional[np.ndarray]:
        """NumPy ses array'inden embedding üretir.

        Args:
            audio: float32 veya int16 ses verisi (1D).
            sample_rate: Örnekleme hızı (varsayılan 16000).

        Returns:
            (256,) boyutunda numpy array veya hata olursa None.
        """
        self._modeli_yukle()

        # Geçici dosyaya kaydet (Inference dosya bekler)
        import tempfile
        import soundfile as sf

        # float32'e çevir
        if audio.dtype == np.int16:
            audio = audio.astype(np.float32) / 32768.0

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_path = f.name
            sf.write(f.name, audio, sample_rate)

        try:
            return self.embedding_uret(tmp_path)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    def konusmaci_ekle(self, isim: str, audio_path: str) -> bool:
        """Yeni konuşmacı kaydeder.

        Args:
            isim: Konuşmacı adı (ör: "Casper", "Anne").
            audio_path: Konuşmacının ses örneği dosya yolu.

        Returns:
            True başarılıysa, False hata olursa.
        """
        embedding = self.embedding_uret(audio_path)
        if embedding is None:
            return False
        self._konusmacilar[isim] = embedding
        logger.info("Konusmaci eklendi: %s (dim=%d)", isim, len(embedding))
        return True

    def konusmaci_ekle_array(self, isim: str, audio: np.ndarray, sample_rate: int = 16000) -> bool:
        """NumPy ses array'inden konuşmacı kaydeder."""
        embedding = self.embedding_uret_array(audio, sample_rate)
        if embedding is None:
            return False
        self._konusmacilar[isim] = embedding
        logger.info("Konusmaci eklendi: %s (dim=%d)", isim, len(embedding))
        return True

    def tanima(self, audio_path: str) -> dict:
        """Ses dosyasındaki konuşmacıyı tanır.

        Args:
            audio_path: Tanınacak ses dosyası.

        Returns:
            {
                "isim": "Casper" veya "Bilinmeyen",
                "skor": 0.85,  # cosine similarity
                "esik": 0.65,
                "bilinen_konusmacilar": ["Casper", "Anne"]
            }
        """
        embedding = self.embedding_uret(audio_path)
        if embedding is None:
            return {
                "isim": "Hata",
                "skor": 0.0,
                "esik": self.esik,
                "bilinen_konusmacilar": list(self._konusmacilar.keys()),
                "hata": "Embedding uretilemedi",
            }
        return self._eslesme_bul(embedding)

    def tanima_array(self, audio: np.ndarray, sample_rate: int = 16000) -> dict:
        """NumPy ses array'inden konuşmacıyı tanır."""
        embedding = self.embedding_uret_array(audio, sample_rate)
        if embedding is None:
            return {
                "isim": "Hata",
                "skor": 0.0,
                "esik": self.esik,
                "bilinen_konusmacilar": list(self._konusmacilar.keys()),
                "hata": "Embedding uretilemedi",
            }
        return self._eslesme_bul(embedding)

    def _eslesme_bul(self, embedding: np.ndarray) -> dict:
        """Embedding ile en iyi eşleşen konuşmacıyı bulur."""
        if not self._konusmacilar:
            return {
                "isim": "Bilinmeyen",
                "skor": 0.0,
                "esik": self.esik,
                "bilinen_konusmacilar": [],
                "not": "Kayitli konusmaci yok",
            }

        en_iyi_isim = "Bilinmeyen"
        en_iyi_skor = 0.0

        for isim, kayitli in self._konusmacilar.items():
            # Cosine similarity (normalize edilmiş vektörler için dot product)
            skor = float(np.dot(embedding, kayitli))
            if skor > en_iyi_skor:
                en_iyi_skor = skor
                en_iyi_isim = isim

        if en_iyi_skor < self.esik:
            en_iyi_isim = "Bilinmeyen"

        return {
            "isim": en_iyi_isim,
            "skor": round(en_iyi_skor, 4),
            "esik": self.esik,
            "bilinen_konusmacilar": list(self._konusmacilar.keys()),
        }

    def kayitli_konusmacilar(self) -> list[str]:
        """Kayıtlı konuşmacı isimlerini döndürür."""
        return list(self._konusmacilar.keys())

    def konusmaci_sil(self, isim: str) -> bool:
        """Kayıtlı bir konuşmacıyı siler."""
        if isim in self._konusmacilar:
            del self._konusmacilar[isim]
            logger.info("Konusmaci silindi: %s", isim)
            return True
        return False


# --- Singleton (tüm uygulama boyunca tek model) ---
_taniyici = None
_taniyici_lock = threading.Lock()


def taniyici_al() -> Optional[KonusmaciTaniyici]:
    """Singleton taniyici olusturur; model yuklenemezse None doner."""
    global _taniyici
    if _taniyici is not None:
        return _taniyici
    with _taniyici_lock:
        if _taniyici is not None:
            return _taniyici
        try:
            _taniyici = KonusmaciTaniyici()
            return _taniyici
        except Exception as e:
            logger.warning("Konuşmacı tanıma motoru oluşturulamadı: %s", e)
            return None
