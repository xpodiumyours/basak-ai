# Başak Gate

## Mimari sınır

Başak Gate yalnız web/test kapısıdır; ikinci bir Başak değildir. Ajan kararı ve 52 aracın gerçek çalıştırılması mevcut Python Başak çekirdeğinde kalır. Gate içinde ayrı ajan/router veya ayrı araç çalıştırıcısı kurulmaz. Düz metin içine yazılmış JSON, native `tool_call` kabul edilmez.

Kalıcı web kapısı ve kabul laboratuvarı. Aynı proje bugün test yüzeyi, daha sonra kullanıcı giriş/sohbet kapısı olabilir.

## Yüzeyler

- `/` giriş
- `/app/` normal keşif sohbeti
- `/lab/` kabul laboratuvarı
- `/api/health` sağlayıcıların yalnız var/yok durumu

## Sabit kabul zinciri

1. 8 sağlayıcı protokolü
2. 52 gerçek araç yapısı ve tam JSON şemaları
3. 8 × 52 = 416 canlı ilk-tur hücresi
4. aynı 416 hücrenin tool-result → ikinci tur devamı
5. laboratuvar oturumuna bağlı gerçek sohbet; en az iki başarılı turdan sonra kullanıcı kabulü
6. tek kabul raporu

Kapsam örneklenmez. Kota engeli çıkarsa laboratuvar durur ve aynı oturumdan daha sonra devam eder.

## Oturum durumu

Aşama 3'teki provider devam durumları (Gemini thought signature, Cohere tool_plan ve benzeri) tarayıcıya verilmez. SQLite-backed Durable Object içinde 24 saat tutulur ve alarm ile temizlenir. Free planda limit aşılırsa işlem hata verir; ücretli kullanıma otomatik geçiş yoktur.

## Sohbet

Normal `/app/` şu aşamada web erişim yüzeyidir; gerçek Başak çekirdeğine bağlanmadan ajan kabul kanıtı değildir. Aşama 4 tamamen geçince Faz 5, normal sohbet ekranından gerçek çekirdek ve gerçek araç zincirini ayrıca doğrular.

## Kimlik bilgileri

Tarayıcıda anahtar alanı yoktur. Worker yalnız Cloudflare secret/binding ortamını okur:
`GROQ_API_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY`, `ZAI_API_KEY`, `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN`, `COHERE_API_KEY`, `KILO_API_KEY`, `NVIDIA_API_KEY`.

Kilo anahtarsız çalışabilir. Workers AI binding normal sohbet için ücretsiz fallback'tir; 8-provider kabulünün yerine geçmez.

## Kaynak eşliği

`tool_catalog.json` ve `tool_schemas.json` CI'da doğrudan `tools.definitions.TOOLS` ve `chat.agent_protocol.YETENEK_ALANLARI` ile birebir karşılaştırılır.
