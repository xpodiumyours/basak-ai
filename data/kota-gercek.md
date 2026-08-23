# KOTA — Gerçek kapasite ölçümü (D-3)

*22 Ağustos 2026. Kod değişikliği yok — yalnız ölçüm.*
*Kaynak: `data/audit/audit.log` (2026-08-22 satırları), `_run.err`, `data/provider_limits/durum.json`, `brain/registry.py` kartları, `düzenleme.md` alıntıları. Test çağrıları (0.0 sn sahte istemci satırları) ayıklandı.*

## Tablo

| Sağlayıcı | Gerçek günlük limit | Bugün kullanılan | Jüriye uygun mu |
|---|---|---|---|
| **groq** | ~200.000 token/gün + 8.000 token/dakika (TPM) | 23 başarılı çağrı; gün içinde 10+ TPM-429 | Evet, ama dar: uzun istekte dakikalık sınır bile tek çağrıyı zorluyor |
| **gemini** | 20 istek/gün (ücretsiz katman) | 15 başarılı; sabah 05:47–08:16 arası kota tükendi (TSİ ~10:00'de yenilendi) | Sınırda: tek kullanıcı bile gün içinde tükettiriyor |
| **glm** | Bilinmiyor (hiç limit hatası görülmedi) | 14 başarılı, 0 kota hatası | Evet (şartlı): üst sınır ölçülene dek "gözlemlenmemiş" kabul edilir |
| **deepseek** | Ücretli — bakiye yok | 0 (7 kez ATLANDI: ucretli cagri varsayilan engelli) | Hayır |
| **qwen** | Erişim yok — model etkinleşmemiş | 0 (1 kez 403 Access denied) | Hayır |
| **nvidia NIM** | Bilinmiyor (limit hatası görülmedi) | 5 başarılı, 0 kota hatası | Evet (şartlı) |
| **openrouter** | ~50 istek/gün (`:free` tipik değer; sağlayıcıdan doğrulanmadı) | 2 başarılı | Yedek |

## Sayıların kaynakları

- **groq 200.000 token/gün:** 429 kaydında `"Used 197.355 / Limit 200.000"` (`düzenleme.md` D-3 alıntısı; `brain/registry.py` satır 8 aynı kaydı referans verir). Kartın 80 istek/gün sayısı bu limitin tahmini türevi.
- **groq TPM 8.000:** bugünkü 429 metni: `"tokens per minute (TPM): Limit 8000, Used 4077, Requested 4125"` (`_run.err` + `audit.log` 12:12:11, 14:03:32, 14:05:08).
- **gemini 20 istek/gün:** 429 kaydında `"limit: 20"` alıntısı (`düzenleme.md`; `brain/registry.py` satır 9). Bugün sabah boyunca tekrar eden `"You exceeded your current quota"` satırları bunu doğruladı.
- **glm / nvidia "bilinmiyor":** `brain/registry.py` kartlarında `gunluk_istek=None`; bugüne dek hiçbir 429/kota hatası alınmadı, yani gerçek üst sınır henüz gözlemlenmedi.
- **deepseek ücretli:** `brain/registry.py` `"UCRETLI"`; audit'te tekrarlayan `ATLANDI kaynak=deepseek | neden=ucretli cagri varsayilan engelli`.
- **qwen 403:** `audit.log` 06:23:55 `"Access to model denied. Please make sure you are eligible..."`.
- **openrouter 50:** `brain/registry.py` yorumu — *varsayım*, ölçüm değil.
- **"bugün kullanılan" sütunu:** `audit.log` 2026-08-22 `OK kaynak=` satırları, 0.0 sn'lik sahte (pytest) satırlar dışlandı.

## Ölçüm güvenilirlik notu

`durum.json` sayacı **iki yazarlı**: canlı uygulama (12:07'den beri açık) kendi bellekteki eski durumu dosyanın üzerine yazıyor; betiklerin artırdığı sayaçlar eziliyor (14:08'de groq=11 görünürken 14:11'de 6'ya düştü). Bu yüzden kullanım sayıları **audit log'dan** alındı — append-only, tek yönlü. *(Ayrı küçük arıza: kota sayacında eşzamanlı yazma yarışı — karar defterine not edildi.)*

## Sonuç (tek cümle)

Paralel jüri güvenilir biçimde yalnız **3 sağlayıcıyla** (groq + glm + nvidia, gemini yalnız günün ilk saatlerinde dördüncü olur) kurulabilir ve **günde kabaca 1–2 tam turu** aşamaz: groq'un 8.000 TPM'i ile gemini'nin 20 isteği ikinci turdan sonra tükenme riskini keskinleştiriyor.
