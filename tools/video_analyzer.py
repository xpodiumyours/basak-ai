"""tools/video_analyzer.py — Video konuşma analizi.

Video dosyasından sesi çıkarır, faster-whisper ile transkript üretir,
pyannote.audio ile konuşmacı ayrıştırması (diarization) yapar.
pyannote/wespeaker ile konuşmacı tanıma (identification) ekler.

Çıktı: zaman damgalı transkript + konuşmacı listesi + tanıma sonuçları.

Kullanım: video_analyze(video_yolu) -> dict
"""

import json
import logging
import os
import subprocess
import tempfile

logger = logging.getLogger(__name__)

# Modeller lazy-load edilir (ilk kullanımda yüklenir, başlangıç hizini azaltır)
_whisper_model = None
_diarization_pipeline = None
_speaker_id = None  # Konuşmacı tanıma motoru (lazy-load)

# ayarlar.json'dan HF token oku
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_AYARLAR_DOSYASI = os.path.join(_BASE, "ayarlar.json")

def _hf_token_oku() -> str:
    """ayarlar.json veya environment'dan HF token okur."""
    import json
    # Önce environment'dan
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if token:
        return token
    # Sonra ayarlar.json'dan
    try:
        with open(_AYARLAR_DOSYASI, "r", encoding="utf-8-sig") as f:
            ayarlar = json.load(f)
        return ayarlar.get("hf_token", "")
    except (OSError, json.JSONDecodeError):
        return ""


def _ffmpeg_var_mi() -> bool:
    """ffmpeg'in kurulu olup olmadığını kontrol eder."""
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True, timeout=5
        )
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _ses_cikar(video_yolu: str, cikti_yolu: str) -> bool:
    """Videodan sesi WAV formatında çıkarır (16kHz, mono)."""
    try:
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", video_yolu,
                "-vn", "-acodec", "pcm_s16le",
                "-ar", "16000", "-ac", "1",
                cikti_yolu,
            ],
            capture_output=True, timeout=300,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        logger.error("FFmpeg ses cikarma hatasi: %s", e)
        return False


def _whisper_yukle():
    """faster-whisper modelini lazy-load eder."""
    global _whisper_model
    if _whisper_model is None:
        try:
            from faster_whisper import WhisperModel
            # CPU modu: small model yeterli ve hizli
            _whisper_model = WhisperModel("small", device="cpu", compute_type="int8")
            logger.info("Whisper modeli yuklendi (small, cpu)")
        except Exception as e:
            logger.error("Whisper modeli yuklenemedi: %s", e)
            raise
    return _whisper_model


def _diarization_yukle():
    """pyannote.audio diarization pipeline'ini lazy-load eder."""
    global _diarization_pipeline
    if _diarization_pipeline is None:
        try:
            from pyannote.audio import Pipeline
            import torch
            # HF token'ı oku (ayarlar.json veya environment)
            hf_token = _hf_token_oku()
            if hf_token:
                _diarization_pipeline = Pipeline.from_pretrained(
                    "pyannote/speaker-diarization-3.1",
                    token=hf_token,
                )
            else:
                # Tokensiz denenir (bazı modeller çalışabilir)
                _diarization_pipeline = Pipeline.from_pretrained(
                    "pyannote/speaker-diarization-3.1",
                )
            # CPU'da çalıştır
            _diarization_pipeline.to(torch.device("cpu"))
            logger.info("Diarization modeli yuklendi (pyannote/speaker-diarization-3.1)")
        except Exception as e:
            logger.warning("Diarization modeli yuklenemedi: %s (transkript yalniz calisir)", e)
            _diarization_pipeline = False
    return _diarization_pipeline if _diarization_pipeline is not False else None


def _speaker_id_yukle():
    """Konuşma tanıma motorunu lazy-load eder."""
    global _speaker_id
    if _speaker_id is not None:
        return _speaker_id
    try:
        from voice.speaker_id import taniyici_al
        _speaker_id = taniyici_al()
        if _speaker_id:
            logger.info("Konuşmacı tanıma motoru hazır")
    except Exception as e:
        logger.warning("Konuşmacı tanıma yüklenemedi: %s", e)
        _speaker_id = False
    return _speaker_id if _speaker_id is not False else None


def _sure_bekle(saniye: float) -> str:
    """Saniyeyi SS:DD formatına çevirir."""
    dakika = int(saniye // 60)
    saniye_kalan = int(saniye % 60)
    return "%02d:%02d" % (dakika, saniye_kalan)


def video_analyze(video_yolu: str) -> dict:
    """Video dosyasını analiz eder.

    Args:
        video_yolu: Video dosyasının mutlak yolu.

    Returns:
        dict: {
            "result": "insan-okunabilir özet",
            "transkript": [...],  # zaman damgalı cümleler
            "konusturmacilar": [...],  # tespit edilen konuşmacılar
            "sure": "SS:DD",  # video süresi
        }
    """
    # Dosya doğrulama
    if not video_yolu or not os.path.isfile(video_yolu):
        return {"error": f"Dosya bulunamadi: {video_yolu}"}

    # Uzantı kontrolu
    izinli_uzantilar = (".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wav", ".mp3", ".m4a")
    if not video_yolu.lower().endswith(izinli_uzantilar):
        return {"error": f"Desteklenmeyen format: {video_yolu}. İzin verilen: {', '.join(izinli_uzantilar)}"}

    # FFmpeg kontrolu
    if not _ffmpeg_var_mi():
        return {"error": "FFmpeg kurulu degil. Video analizi icin FFmpeg gerekli."}

    # Geçici ses dosyası
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        ses_dosyasi = tmp.name

    try:
        # 1. Videodan sesi çıkar
        if not _ses_cikar(video_yolu, ses_dosyasi):
            return {"error": "Videodan ses cikarilamadi."}

        # 2. Whisper ile transkript
        try:
            model = _whisper_yukle()
            segments, info = model.transcribe(
                ses_dosyasi,
                language="tr",  # Türkçe öncelikli
                beam_size=5,
                vad_filter=True,
            )
            transkript = []
            for seg in segments:
                transkript.append({
                    "baslangic": round(seg.start, 2),
                    "bitis": round(seg.end, 2),
                    "metin": seg.text.strip(),
                    "konusturmaci": None,  # diarization ile doldurulacak
                })
        except Exception as e:
            return {"error": f"Transkript hatasi: {str(e)[:200]}"}

        if not transkript:
            return {"error": "Ses icerigi bulunamadi veya cok kisa."}

        # 3. Konuşmacı ayrıştırması + tanıma (opsiyonel)
        konusturmacilar = []
        tanima_sonuclari = {}  # {"Konuşmacı_1": {"isim": "Casper", "skor": 0.85}, ...}
        diarization = _diarization_yukle()
        if diarization:
            try:
                diarization_sonuc = diarization(ses_dosyasi)
                # Her segmente konuşmacı ata
                for segment in transkript:
                    merkez = (segment["baslangic"] + segment["bitis"]) / 2
                    for turn, _, speaker in diarization_sonuc.itertracks(yield_label=True):
                        if turn.start <= merkez <= turn.end:
                            segment["konusturmaci"] = speaker
                            if speaker not in konusturmacilar:
                                konusturmacilar.append(speaker)
                            break
            except Exception as e:
                logger.warning("Diarization hatasi: %s (transkript yalniz doner)", e)

        # 3b. Konuşmacı tanıma (identification) — tanınmış isimlerle eşleştirme
        speaker_id = _speaker_id_yukle()
        if speaker_id and konusturmacilar:
            try:
                # Her benzersiz konuşmacı için tek bir embedding üret
                # (ilk segmentini temsilci olarak kullan)
                for spk in konusturmacilar:
                    # Bu konuşmacının ilk segmentini bul
                    spk_segmentleri = [s for s in transkript if s["konusturmaci"] == spk]
                    if not spk_segmentleri:
                        continue
                    ilk_seg = spk_segmentleri[0]

                    # WAV dosyasından bu segmentin sesini çıkar
                    import subprocess, tempfile
                    segment_dosyasi = None
                    try:
                        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                            segment_dosyasi = f.name
                        subprocess.run([
                            "ffmpeg", "-y", "-i", ses_dosyasi,
                            "-ss", str(ilk_seg["baslangic"]),
                            "-to", str(ilk_seg["bitis"]),
                            "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
                            segment_dosyasi,
                        ], capture_output=True, timeout=30, check=True)

                        tanima = speaker_id.tanima(segment_dosyasi)
                        tanima_sonuclari[spk] = {
                            "isim": tanima["isim"],
                            "skor": tanima["skor"],
                            "bilinen_konusmacilar": tanima.get("bilinen_konusmacilar", []),
                        }
                        # Transkripttede tanıma sonucunu ekle
                        for s in spk_segmentleri:
                            s["konusturmaci_adi"] = tanima["isim"]
                            s["tanima_skoru"] = tanima["skor"]
                    finally:
                        if segment_dosyasi:
                            try:
                                os.unlink(segment_dosyasi)
                            except OSError:
                                pass
            except Exception as e:
                logger.warning("Konuşmacı tanıma hatası: %s", e)

        # 4. Sonuç üret
        toplam_sure = transkript[-1]["bitis"] if transkript else 0
        konu_sayisi = len(konusturmacilar)

        ozet = "Video analizi tamamlandi.\n"
        ozet += f"Sure: {_sure_bekle(toplam_sure)}\n"
        if konu_sayisi > 0:
            ozet += f"Konusturmaci sayisi: {konu_sayisi}\n"
            ozet += f"Konusturmacilar: {', '.join(konusturmacilar)}\n"
        # Tanıma sonuçları varsa özete ekle
        if tanima_sonuclari:
            ozet += "\n--- KONUSMACI TANIMA ---\n"
            for spk, t in tanima_sonuclari.items():
                if t["isim"] != "Bilinmeyen":
                    ozet += f"  {spk} -> {t['isim']} (skor: {t['skor']})\n"
                else:
                    ozet += f"  {spk} -> Bilinmeyen\n"
        ozet += f"Transkript uzunlugu: {len(transkript)} cumle\n"
        ozet += "\n--- ILK 5 CUMLE ---\n"
        for seg in transkript[:5]:
            k = seg.get("konusturmaci_adi") or seg["konusturmaci"] or "?"
            ozet += f"[{_sure_bekle(seg['baslangic'])}] {k}: {seg['metin']}\n"

        return {
            "result": ozet,
            "transkript": transkript,
            "konusturmacilar": konusturmacilar,
            "tanima_sonuclari": tanima_sonuclari,
            "sure": _sure_bekle(toplam_sure),
        }

    finally:
        # Geçici dosyayı temizle
        try:
            os.unlink(ses_dosyasi)
        except OSError:
            pass
