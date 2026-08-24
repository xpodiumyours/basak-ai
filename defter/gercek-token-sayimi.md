---
kim:    opencode
tarih:  2026-08-24
konu:   Gercek token sayimi — adaptörler usage okuyor, stats doldu
tip:    karar
omur:   sonsuz
kaynak: brain/kullanim.py + tests/test_token_sayimi.py
---

Casper'in tespiti dogrulandi ve kapatildi: stats.py'de token_in/token_out
hazirdi; ama (1) hicbir adaptör usage okumuyordu, (2) ozet() token
toplamamiyordu. Groq'un 200k/gun hakki "80 istek" diye tahmin
ediliyordu.

Cozum:
- `brain/kullanim.py` yeni yardimci: OpenAI-SDK bicimi
  (resp.usage.prompt/completion_tokens) VE Cohere bicimi
  (resp.meta.tokens.input/output_tokens) destekler.
- 9 adaporun TUMUNUN donus noktalarina kullanim_ekle() baglandi
  (groq/glm/nvidia/kilo/openrouter/cohere/cloudflare/gemini/qwen).
- `brain.brain.cevapla` basarili cagrida _kullanim'i ayiklayip
  istat.kaydet(..., token_in, token_out)'a yazar; yanittan anahtari siler
  (asagi akisa sizmaz).
- `stats.py` ozet() artik token_in_toplam / token_out_toplam dondurur —
  model_stats aracindan gorunur.

KANIT: 9 yeni test (tests/test_token_sayimi.py): iki bicimin cikarimi,
usage-yok zararsizligi, Groq adaptorunun tasimasi, ozet toplamlari, ve
brain.cevapla'nin kullanimi istatige aktarmasi (sahte saglayiciyla).
Toplam 390/390 yesil.

Bilinen sinir / sonraki adim: kota.py hala ISTEK sayaciyla calisiyor —
gercek token butcesiyle baglanmasi (groq gunluk_istek=80 tahmininin
kaldirilmasi) yol haritasinin 2. adimiyla birlikte yapilacak ayri is.
Yerel Ollama cagrilari icin token olcumu eklenmedi (sinirsiz/ucuz).
