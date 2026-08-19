from faster_whisper import WhisperModel
print("model yukleniyor...")
m = WhisperModel("base", device="cpu", compute_type="int8")
print("transcribe...")
segs, _ = m.transcribe("_tts_test.wav", language="tr", vad_filter=True)
txt = " ".join(s.text for s in segs).strip()
print("SONUC:", txt)
