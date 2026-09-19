# Başak Gate

Kalıcı web kapısı ve kabul laboratuvarı.

## Ürün yüzeyleri

- `/` — giriş kapısı
- `/app/` — keşif sohbeti; Faz 5 kabulü değildir
- `/lab/` — sabit kabul zinciri
- `/api/health` — sağlayıcıların yalnız var/yok durumu
- `/api/chat` — ücretsiz sağlayıcı zinciri; gerekirse Workers AI ücretsiz fallback
- `/api/lab/phase1/:provider` — tek sağlayıcı için canlı tool protokol testi
- `/api/lab/phase2` — 52 araç katalog yapısı kontrolü

## Kilitli sıra

1. 8 protokol
2. 52 araç yapısı
3. 8 × 52 = 416 canlı hücre
4. ikinci tur
5. gerçek sohbet kabulü
6. tek kabul raporu

Web sohbeti Aşama 1–4 kapanmadan da keşif için kullanılabilir; **kabul kanıtı sayılmaz**.

## Ücretsiz çalışma kuralı

Workers Free kullanılır. Statik asset istekleri ücretsizdir. Worker/Workers AI ücretsiz kotaları aşılırsa işlem hata verir; sistem ücretli plana kendiliğinden geçmez. OpenRouter yalnız `:free` modelleri seçer. Diğer sağlayıcılarda Başak'ın ücretsiz model yolları korunur.

## Kimlik bilgileri

Tarayıcıda anahtar alanı yoktur. Worker yalnız Cloudflare ortamında tanımlanmış secret adlarını okur:

`GROQ_API_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY`, `ZAI_API_KEY`, `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN`, `COHERE_API_KEY`, `KILO_API_KEY`, `NVIDIA_API_KEY`.

Değerler API cevaplarına yazılmaz. Kilo anahtarsız çalışabilir. Workers AI binding ayrıca anahtar gerektirmez.

## 416 aşaması

`scripts/export_schemas.py` gerçek `tools.definitions.TOOLS` kaynağından tam şemaları üretir. Faz 3 bu çıktı bağlanmadan açılmaz; isim örneklemesi 416 testinin yerine geçmez.
