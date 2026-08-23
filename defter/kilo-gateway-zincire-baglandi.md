---
kim:    claude
tarih:  2026-08-23
konu:   Kilo Gateway zincire baglandi
tip:    olcum
omur:   30g
kaynak: olcum
---

Kilo Gateway ucretsiz katmani Basak'in bulut zincirine eklendi (brain/kilo.py, registry karti, brain.py zinciri). Anahtar gerektirmiyor: https://api.kilo.ai/api/gateway/v1 adresine Authorization basligi olmadan HTTP 200 donuyor; sinir 200 istek/saat/IP. Zincirdeki yeri nvidia ile openrouter arasi.

Olculen tuzak: ucretsiz modeller dusunen (reasoning) model; dusunme metni max_tokens butcesinden yiyor. max_tokens=150 ile ic ustuste denemede content BOS dondu (finish_reason=length, 150 jetonun 81i dusunmeye gitti); max_tokens=1024 ile duzgun cevap geldi. Bu yuzden VARSAYILAN_JETON=1500 ve bos content + tool_calls yoksa RuntimeError firlatiliyor — bos balon kullaniciya gitmiyor, zincir siradakine geciyor. reasoning alani donen sozluge konmuyor. {"reasoning": {"enabled": false}} gondermek ise yaramadi, yok sayildi.

Kanit: 231/231 test yesil (12 yeni test tests/test_kilo.py). Gercek agda zincir uzerinden iki cagri: audit.log 2026-08-23 16:54:30 OK kaynak=kilo | 3.7 sn | tools=False ve 16:54:34 OK kaynak=kilo | 3.6 sn | tools=True (arac cagrisi dogru bicimde dondu).

Gizlilik notu: Kilo belgesi ucretsiz katmanin gonderilen yazilari kaydedip egitimde kullanabilecegini soyluyor; Basak her soruya kisisel not ve hafiza ekliyor. Casper 2026-08-23te bunu bilerek onayladi ("fark etmez, normal bagla").

Elenen adaylar: Puter.js yalniz tarayici icin, Pythondan kullanilabilir belgelenmis yol yok. Vercel AI Gateway / OpenRouter / HuggingFace yeni degil — anahtarlari ayarlar.json'da zaten kayitli.
