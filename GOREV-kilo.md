# GÖREV — Kilo Gateway'i Başak'ın beyin zincirine bağla

> **TAMAMLANDI — 2026-08-23, Claude Code.** Bu görev uygulandı ve kanıtlandı:
> `brain/kilo.py` + registry kartı + `brain.py` zinciri, 231/231 test yeşil,
> gerçek ağda `audit.log`'da `OK kaynak=kilo` (16:54:30 ve 16:54:34).
> Kayıt: `defter/kilo-gateway-zincire-baglandi.md`.
> **Yeniden uygulama — bu dosya yalnız geçmiş kaydı.**

*Hazırlayan: Claude Code, 2026-08-23. Casper onayladı ("normal bağla").*
*Bu görevdeki tüm sayılar TAHMİN DEĞİL — bu makineden gerçek istek atılarak ölçüldü.*

## Hedef (tek cümle)

`brain/` altına yeni bir sağlayıcı ekle: **Kilo Gateway** — API anahtarı
gerektirmeyen, saatte 200 istek veren, araç çağırmayı (tool calling)
destekleyen ücretsiz bulut sağlayıcı.

## Neden değerli

Bugünkü ücretsiz kotalar dar: gemini 20 istek/gün, groq ~200.000 token/gün
(dakikada 8.000 tavanına takılıyor), openrouter ~50/gün
(`data/kota-gercek.md`). Kilo tek başına **saatte 200 istek** veriyor ve
hiçbir hesap/anahtar istemiyor.

## ÖLÇÜLEN GERÇEKLER (bunlara güvenebilirsin)

| Ne | Ölçülen değer |
|---|---|
| Uç adres | `https://api.kilo.ai/api/gateway/v1/chat/completions` |
| Kimlik doğrulama | **YOK** — `Authorization` başlığı göndermeden HTTP 200 |
| Biçim | OpenAI uyumlu (mevcut `openai` paketi aynen kullanılır) |
| Model | `kilo-auto/free` (ücretsiz modeller arasında kendi yönlendiriyor) |
| Ücretsiz model sayısı | 369 modelin 15'i `:free` + 4 `kilo-auto/*` |
| Araç çağırma | **ÇALIŞIYOR** — `tools` gönderildi, doğru `tool_calls` döndü |
| Gecikme | 3,4 – 4,6 saniye (3 ölçüm) |
| Sınır | IP başına saatte 200 istek (Kilo belgesi) |

## ÖLÇÜLEN TUZAK — bunu atlarsan Başak boş cevap verir

Ücretsiz modellerin çoğu **düşünen (reasoning) model**. Düşünme metni
`max_tokens` bütçesinden yiyor ve ayrı bir `reasoning` alanında dönüyor.

- `max_tokens: 150` → `finish_reason: "length"`, `content` **BOŞ**, 150
  jetonun 81'i düşünmeye gitti. Üç denemede de boş döndü.
- `max_tokens: 1024` → `finish_reason: "stop"`, gerçek Türkçe cevap geldi
  (367 jeton düşünmeye gitti, kalanı cevaba).
- `{"reasoning": {"enabled": false}}` göndermek **işe yaramadı**, yok sayıldı.

**Bu yüzden zorunlu:**
1. `max_tokens` en az **1500** olacak (`brain/openrouter.py`'deki 1024 bu
   sağlayıcı için sınırda; 1500 seç).
2. `content` boş **ve** `finish_reason == "length"` ise bu bir BAŞARISIZLIK
   sayılacak — kullanıcıya boş balon gitmeyecek, zincir sıradakine geçecek
   (`RuntimeError` fırlat, `brain.py` zaten yakalayıp devam ediyor).
3. `reasoning` / `reasoning_details` alanları kullanıcıya **asla**
   gösterilmeyecek, dönen sözlüğe konmayacak.

Ayrıca `nvidia/nemotron-3-super-120b-a12b:free` modelini seçme — düşünme
metnini doğrudan `content` içine sızdırıyor (ölçüldü). `kilo-auto/free`
kullan, o `stepfun/step-3.7-flash`'a yönlendiriyor ve temiz dönüyor.

## Dokunulacak dosyalar (sadece bunlar)

1. **`brain/kilo.py`** (yeni) — `brain/openrouter.py`'yi kalıp al.
   Fark: `api_key` parametresi YOK, `OpenAI(api_key="dummy", base_url=...)`
   ile kurulur (openai paketi boş anahtar kabul etmez, bu yüzden yer
   tutucu). Sınıf adı `KiloClient`, metotlar `musait()` ve
   `cevapla(messages, tools=None)`. Dönen sözlük şekli `openrouter.py`
   ile **birebir aynı** olacak (`{"content": ...}` veya
   `{"content": ..., "tool_calls": [...]}`).

2. **`brain/registry.py`** — `SAGLAYICILAR` sözlüğüne kart ekle:
   ```
   "kilo": {
       "ad": "Kilo Gateway",
       "ucretsiz": True,
       "tools": True,
       "gucleri": ["genel", "kod"],
       "gunluk_istek": None,   # limit saatlik (200/saat/IP), gunluk degil
       "not": "Anahtarsiz; 200 istek/saat/IP. Ucretsiz katman istekleri
               kaydedebilir — Casper 2026-08-23'te bunu bilerek onayladi.",
   }
   ```
   `VARSAYILAN_SIRA`'da yeri: `nvidia` ile `openrouter` arasında →
   `["groq", "glm", "cohere", "nvidia", "kilo", "openrouter", "qwen", "gemini"]`.
   Gerekçe: kotası en geniş olan bu, ama gecikmesi groq'tan yüksek (~4 sn),
   o yüzden hızlıların arkasında.

3. **`brain/brain.py`** — diğer sağlayıcılar gibi kur, **tek farkla:**
   anahtar kontrolü yok, koşulsuz kurulur. `_bulut_zinciri()` içinde
   `nvidia`'dan sonra, `openrouter`'dan önce eklenir. Sınıf başındaki
   sıra yorumunu da güncelle.

## Kota davranışı

`brain/kota.py` 429'u zaten yakalayıp soğumaya alıyor (`hata_isle`).
Kilo saatlik sınırı aşınca 429 dönecek ve bu mekanizma çalışacak —
**yeni kota kodu yazma**, mevcut olan yeterli. `gunluk_istek: None`
bırakman bunun içindir.

## Doğrulama kapısı — kanıtsız "bitti" deme (AGENTS.md §5)

1. `python -m pytest tests/ -q` → mevcut testlerin hepsi yeşil kalmalı.
2. `brain/kilo.py` için yeni testler yaz (`tests/test_kilo.py`): en az
   (a) boş `content` + `finish_reason="length"` → hata fırlatıyor mu,
   (b) `tool_calls` doğru biçime çevriliyor mu,
   (c) `reasoning` alanı dönen sözlüğe sızmıyor mu.
3. **Gerçek çalıştırma:** `python basak_app.py` ile aç, diğer sağlayıcıları
   geçici olarak devre dışı bırakıp (ya da `_bulut_zinciri()`'ni tek
   elemanla çağıran küçük bir betikle) Kilo'dan gerçek bir cevap al.
   `data/audit/audit.log`'da `OK kaynak=kilo` satırını göster.
4. Bitince `ORTAK-DEFTER.md` biçiminde `defter/` altına kayıt yaz.

## Yapma

- Puter.js bağlamaya çalışma — yalnız tarayıcı için, Python'dan
  kullanılabilir belgelenmiş bir yolu yok (2026-08-23'te bakıldı).
- Vercel AI Gateway / Hugging Face ekleme — bu görevin kapsamı dışı.
- Mevcut sağlayıcıların sırasını Kilo'yu eklemek dışında değiştirme.
