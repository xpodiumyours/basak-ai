# Jarvis Yerel Asistan Araştırması (Windows + Python 3.12)

Ortam: Python 3.12, Ollama (qwen2.5:3b), faster-whisper 1.2.1, openai (Groq uyumlu), pywebview 6.2.1. GROQ_API_KEY yok. İnternet var.

---

## A) Türkçe için TAMAMEN YEREL TTS seçenekleri

| Motor | Türkçe ses | Ücretsizlik | Windows kurulumu | Python entegrasyonu |
|---|---|---|---|---|
| **Piper** (VITS/ONNX) | **Evet — `tr_TR` (örn. `tr_TR-fahrettin-medium`)** | Ücretsiz (MIT/GPL-3.0) | `pip install piper-tts`; `python -m piper.download_voices tr_TR-fahrettin-medium` | `echo "..." \| piper -m tr_TR-fahrettin-medium -f out.wav` ya da Python API; HTTP sunucu da var |
| **Coqui TTS (XTTS v2)** | Evet (`language="tr"`), 17 dil, ses klonlama | Açık kaynak, ücretsiz | `pip install coqui-tts` + espeak-ng + PyTorch; **Windows GPU desteği sorunlu (WSL öneriliyor)** | `from TTS.api import TTS` → `tts.tts_to_file(text=..., language="tr", ...)` |
| **Microsoft SAPI5** | **Türkçe ses Windows'ta varsayılan YOK**; yalnızca üçüncü parti (Ivona "Filiz", Nuance "Yelda/Cem") ücretli | Ücretsiz değil (lisanslı sesler) | Windows'a ses paketi kurulumu gerekir; varsayılan olarak en/tr yok | `pyttsx3` ile `voice.id` seçimi |
| **eSpeak NG** | Evet (Türkçe fonetik, robotik) | Ücretsiz (GPL) | `pip install pyttsx3` ya da `espeakng` binary | Çok düşük kalite, sadece yedek |

**Öneri:** Piper. En kaliteli + pratik: `pip install piper-tts`, tek komutla `tr_TR` ses iniyor, CPU'da gerçek zamanlı, dosya boyutu onlarca MB. SAPI5 Türkçe doğal ama ses paketi ücretli ve Windows'ta gömülü gelmiyor. Coqui XTTS v2 kaliteli ve klonlama sunar ama ağır (~2GB), Windows GPU desteği zayıf, CPU'da cümle başına 30-60 sn. eSpeak yalnızca fallback.

Kaynaklar:
- Piper ses listesi (tr_TR dahil): https://github.com/cdwiegand/piper-tts/blob/master/README.md
- Piper pip + HTTP sunucu: https://thedocs.io/piper1-gpl/installation ve https://pypi.org/project/piper-tts
- Türkçe Piper örneği (tr_TR-fahrettin-medium): https://github.com/dehalokmansahin/piper-tts
- Coqui XTTS v2 Türkçe + Windows GPU uyarısı: https://vantaige.io/ai-tool/coqui-tts ve https://coqui-tts.readthedocs.io/en/latest/cloning.html
- SAPI5 Türkçe sesler (ücretli, gömülü değil): https://limetech.uk/turkish-text-to-speech-voices
- Windows varsayılan TTS dilleri: https://support.microsoft.com/en-us/accessibility/windows/narrator/appendix-a-supported-languages-and-voices

---

## B) faster-whisper ile Türkçe STT

- **Model boyutu:** Gerçek zamanlı asistan için **`base` veya `small`** önerilir. tiny en hızlı ama WER yüksek (Türkçe için kelime hataları artar); small daha doğru, CPU'da yine de yaklaşık gerçek zamanlı. GPU yoksa `int8` quantization (`compute_type="int8"`) kullan. (Kaynak: https://www.promptquorum.com/power-local-llm/local-whisper-stt-comparison-2026 — gerçek zamanlı için small/base sweet spot.)
- **Mikrofon kütüphanesi:** faster-whisper sesi NumPy dizisi / WAV olarak alır; **`sounddevice` önerilir** (PyAudio'ya göre daha sade API, NumPy array doğrudan, Windows DirectSound/WASAPI seçimi kolay, PyAudio'da boş kayıt hatası sık görülüyor). PyAudio yalnızca düşük seviyeli kontrol gerekince. (Kaynak: https://realpython.com/playing-and-recording-sound-python ve https://stackoverflow.com/questions/76638153/recording-microphone-input-with-pyaudio-fails)
- **VAD:** faster-whisper **Silero VAD** entegre (`vad_filter=True`). Sessizlikleri keser, doğal chunk üretir. Önerilen başlangıç: `vad_parameters=dict(min_silence_duration_ms=500, threshold=0.5, min_speech_duration_ms=250)`. (Kaynak: https://pypi.org/project/faster-whisper ve https://github.com/jhj0517/Whisper-WebUI/wiki/VAD-Parameters)
- **Türkçe:** `model.transcribe(audio, language="tr", vad_filter=True)` ile dili sabitle (WER düşer, yanlış dil tespiti önlenir).

Kaynaklar:
- faster-whisper VAD + hız: https://www.saytowords.com/blogs/Faster-Whisper-Guide
- Model boyutu/gerçek zamanlı öneri: https://www.promptquorum.com/power-local-llm/local-whisper-stt-comparison-2026
- sounddevice vs pyaudio: https://realpython.com/playing-and-recording-sound-python
- VAD parametreleri: https://github.com/jhj0517/Whisper-WebUI/wiki/VAD-Parameters

---

## C) Hibrit beyin yönlendirmesi (Ollama yerel vs Groq bulut)

**Ne zaman buluta kaçmalı (yönlendirme kuralı):**
1. Yerel `qwen2.5:3b` yanıtı düşük güvenle gelirse / "bilmiyorum" derse → Groq.
2. Karmaşık akıl yürütme, uzun bağlam, kod üretimi, çok adımlı plan → Groq (`llama-3.3-70b-versatile`).
3. Güncel bilgi gereken sorular (model bilmez) → Groq (yine de kesin cevap garantisi yok, web aracı gerekir).
4. Basit sohbet, hatırlatma, yerel komut, kişisel notlar → Ollama (gizlilik + sıfır maliyet + offline).

**Groq kullanımı doğru mu?** Evet. `llama-3.3-70b-versatile` Groq'un OpenAI-uyumlu uç noktasında çalışır: `base_url="https://api.groq.com/openai/v1"`, `model="llama-3.3-70b-versatile"`. Mevcut `openai` kütüphanesiyle `OpenAI(api_key=GROQ_API_KEY, base_url=...)` yeterli. (Kaynak: https://console.groq.com/docs/openai ve https://www.freellms.org/providers/groq)

**Ücretsiz quota (2026, model bazlı, org seviyesi):**
- `llama-3.3-70b-versatile`: **30 RPM, 1.000 RPD, 12K TPM, 100K TPD** (ücretsiz, kredi kartı yok). (Kaynak: https://tokenmix.ai/blog/groq-api-access-2026-free-tier-rate-limits ve https://getaitools.dev/service/groq)
- Not: 2026'da günlük kota 14.400'ten 1.000'e düşürüldü; yoğun kullanımda yetersiz kalabilir. Daha yüksek hacim için `llama-3.1-8b-instant` (14.4K RPD) ya da Developer tier.
- Groq tam OpenAI uyumlu DEĞİL: `logprobs`, `logit_bias`, `top_logprobs`, `messages[].name` desteklenmez; `n` yalnızca 1. (Kaynak: https://console.groq.com/docs/openai)

**Öneri:** Varsayılan yerel Ollama; bir "router" fonksiyonu ile güven skoru/deterministik tetikleyiciyle Groq'a geç. Groq anahtarı yokken uygulama yalnızca yerel çalışsın (graceful degrade), anahtar eklenince hibrit açılsın.

Kaynaklar:
- Groq OpenAI uyumu + base URL: https://console.groq.com/docs/openai
- Groq free tier limitler (llama-3.3-70b): https://tokenmix.ai/blog/groq-api-access-2026-free-tier-rate-limits
- Groq kota değişim geçmişi: https://getaitools.dev/service/groq

---

## D) pywebview ile akıcı "Jarvis" UI

- **GUI döngüsü ana iş parçacığında blocking:** `webview.start()` çağıran thread'i kilitler. Tüm backend mantığı (LLM, STT, TTS, HTTP sunucu) **ayrı thread/process**'te olmalı. `webview.start(func, window)` fonksiyonu otomatik thread açar. (Kaynak: https://pywebview.flowrl.com/guide/usage.html ve https://github.com/r0x0r/pywebview/blob/master/docs/guide/usage.md)
- **İki yönlü köprü (önerilen yaklaşım):** `js_api=ApiClass` ile JS'ten `window.pywebview.api.method()` çağır; Python'dan sonuç döndürmek için `window.evaluate_js("updateUI(...)", callback)`. HTTP sunucu şart değil — köprü daha hafif ve CORS'suz. (Kaynak: https://pywebview.idepy.com/en/guide/interdomain)
- **CORS:** Saf pywebview köprüde CORS yok (aynı süreç). Eğer ayrı `http.server`/`Flask` kullanıyorsan, WebView2 (Windows varsayılan) `localhost`'a fetch izin verir ama生产 için `Access-Control-Allow-Origin` header'ı ekle; `file://` yerine yerel HTTP sunucu (pywebview'ın dahili bottle sunucusu `http_server=True`) kullan. (Kaynak: https://pywebview.flowrl.com/3.7/guide/usage.html)
- **Thread güvenliği:** `evaluate_js` dahili semaphore ile ana thread'e gönderilir; uzun işleri API metodunun içinde `concurrent.futures.ThreadPoolExecutor` ile çalıştır, bitince `webview.windows[0].evaluate_js(...)` ile UI'ı güncelle. Ana thread'i bloklayan kod **deadlock** yapar ("thinking" ekranında takılır). (Kaynak: https://github.com/r0x0r/pywebview/issues/1699)
- **WebGL/Three.js tuzakları:** Windows'ta varsayılan renderer Edge WebView2 → WebGL desteklenir. Ama (1) `debug=False` üretimde shader/log hatalarını gizler; (2) GPU olmayan makinelerde WebGL context başarısız olabilir → basit 2D canvas/CSS geçişi fallback planla; (3) ağır Three.js sahneleri UI thread'i bloklayıp "thinking" hissi verir — render'ı hafif tut, animasyonları `requestAnimationFrame` ile sınırla; (4) pywebview penceresinde `webgl` için ekstra flag gerekmez ama `gui="cef"` seçeneğinde donanım hızlanması açık olmalı.

Kaynaklar:
- Threading model + backend mantığı: https://pywebview.flowrl.com/guide/usage.html
- JS-Python köprü: https://pywebview.idepy.com/en/guide/interdomain ve https://pywebview.flowrl.com/examples/evaluate_js
- Deadlock uyarısı: https://github.com/r0x0r/pywebview/issues/1699
- HTTP sunucu (bottle, http_server=True): https://pywebview.flowrl.com/3.7/guide/usage.html

---

## E) Araç/eklenti (tool use) kazandırmanın en sade yolu

**Fonksiyon çağırma mı, komut ayrıştırma mı?** İkisi de mümkün, ancak:
- **Komut ayrıştırma (regex/anahtar kelime):** En sade, deterministik, küçük modelda güvenilir (ör. "hatırlatıcı kur <zaman> <metin>" → regex). Gizlilik dostu, yerel tam çalışır.
- **Fonksiyon/tool calling:** Daha esnek ama modele bağlı. `qwen2.5:3b` Ollama'da **native tool calling destekli** ama küçük modelde tek araçta bile güvenilirlik düşük (kaynak: https://docs.ollama.com/capabilities/tool-calling ve https://localaimaster.com/blog/ollama-function-calling-tools — qwen2.5:7b/14b 8-9/10, 3b sınırlı).
- **Öneri:** Hibrit. Kritik/yerel eylemler (tarayıcı aç, hatırlatıcı, dosya) için **sabit komut ayrıştırma**; serbest doğal dil araçları için Groq'ta **tool calling**. Böylece yerel kısım 3b ile bile sağlam çalışır.

**qwen2.5:3b araç kullanabilir mi?** Ollama üzerinden `tools` parametresiyle evet, native destek var; fakat 3B boyutunda çoklu-araç ve karmaşık JSON için güvenilir değil. Daha iyi sonuç için yerel tarafda `qwen2.5:7b` ya da `llama3.1:8b` önerilir.

**Groq llama modelleri function calling destekliyor mu?** Evet. `llama-3.3-70b-versatile` (ve `llama-3.1-8b` vb.) OpenAI-format `tools` şemasını destekler. Tool-use'a özelleşmiş `llama3-groq-8b/70b-tool-use` modelleri de Groq'ta mevcut (BFCL ~90%). (Kaynak: https://console.groq.com/docs/openai ve https://groq.com/blog/introducing-llama-3-groq-tool-use-models)
- Not: `llama-3.3-70b-versatile`'in tool calling'i bazı raporlarda sorunlu görülmüş; garanti için `llama-3.1-8b-instant` veya `llama3-groq-tool-use` ID'leri denenebilir. (Kaynak: https://github.com/openclaw/openclaw/issues/5794)

Kaynaklar:
- Ollama tool calling: https://docs.ollama.com/capabilities/tool-calling
- Ollama model karşılaştırması (qwen2.5 dahil): https://localaimaster.com/blog/ollama-function-calling-tools
- Qwen2.5 function calling: https://deepwiki.com/QwenLM/Qwen2.5/2.2-function-calling-and-tool-use
- Groq tool-use modelleri: https://groq.com/blog/introducing-llama-3-groq-tool-use-models

---

## F) "Thinking" ekranında sonsuza kadar takılma — teşhis listesi

Mevcut HTTPServer + pywebview sohbet uygulaması için olası nedenler:

1. **Backend thread block (en olası):** LLM/STT/TTS çağrısı pywebview'ın ana (GUI) thread'inde çalışıyorsa UI kilitlenir ve "thinking" hiç bitmez. Çözüm: işi `ThreadPoolExecutor`/ayrı thread'e taşı, sonucu `evaluate_js` ile pushla. (Kaynak: https://github.com/r0x0r/pywebview/issues/1699)
2. **Frontend fetch çözülmüyor (Promise askıda):** JS'te `await fetch(...)` sunucudan yanıt/connection kapanması gelmezse Promise pending kalır. Backend'in mutlaka yanıt döndürmesi (hatada bile 500 JSON) gerekir; streaming ise yanıtı kapatmalı. (Kaynak: https://pywebview.flowrl.com/3.7/guide/usage.html)
3. **Timeout yok → sonsuz bekleme:** Python `http.client`/`requests` varsayılan timeout'suzsa sunucu yanıt vermezse client sonsuza dek bloklar. `requests.post(..., timeout=30)` ve istemci tarafında `AbortController`/`Promise.race` ile üst sınır koy. (Kaynak: https://bugs.python.org/issue24486)
4. **Sunucu ayrı thread'de hazır değil:** `threading.Timer`/gecikmeyle başlatılan HTTP sunucu henüz dinlemiyorken fetch "thinking"de kalır. Sunucunun `serve_forever()` yaptığını ve port'un açık olduğunu doğrula; pencereyi açmadan önce kısa bir health-check bekle. (Kaynak: https://stackoverflow.com/questions/43368875/pywebview-blocks-flask-app-unless-i-open-two-webviews)
5. **Ollama/Groq çağrısı takılıyor:** `ollama.chat` ya da Groq isteği yerel model yüklenirken/ilk token'da takılabilir; LLM çağrılarına da timeout ekle, Groq 429/5xx'te retry + fallback yerele yap.
6. **Deadlock (evaluate_js içinde lock):** API metodunun içinde senkron `evaluate_js` bekleyen bir lock varsa ana thread kilitlenir → sonsuz thinking. Uzun işlerde `evaluate_js(callback=...)` (promise resolve) kullan. (Kaynak: https://github.com/r0x0r/pywebview/issues/1699)

**Hızlı düzeltme şablonu:** (a) tüm AI çağrılarını ayrı thread'e al, (b) her HTTP endpoint'inin hata durumunda dahi JSON döndürdüğünden emin ol, (c) istemci+sunucu tarafında 20-30 sn timeout koy, (d) sonucu `window.pywebview.api` yerine `evaluate_js` ile pushla (polling yapma).

Kaynaklar:
- pywebview blocking/deadlock: https://github.com/r0x0r/pywebview/issues/1699
- HTTP client sonsuz blok (timeout şart): https://bugs.python.org/issue24486
- pywebview + flask thread sorunu: https://stackoverflow.com/questions/43368875/pywebview-blocks-flask-app-unless-i-open-two-webviews
- JS fetch timeout (Promise.race): https://community.cloudflare.com/t/timeout-with-fetch/25249
