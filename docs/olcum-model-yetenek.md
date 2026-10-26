---
uretildi: 2026-10-26T00:58:31+00:00
commit: 42f4a8e-dirty
komut: python scripts/olcum/model_yetenek_olcumu.py --sadece glm --birlestir --kotasiz --ara 3
ttl_saat: 24
sonuc: {"saglayici": 8, "arac_tur1": "6/8", "arac_devam": "6/8", "goruntu": "1/8", "goruntu_araci": "gecti"}
---

# Model yetenek ölçümü

Bu dosya `scripts/olcum/model_yetenek_olcumu.py` tarafından üretilir; elle düzenlenmez. 24 saat sonra bayat sayılır.

## Sonuç

| Sağlayıcı | Model | Araç (tur 1) | Devam turu | Görüntü | Tur token (giriş/çıkış) | Kalan kota | Not |
|---|---|---|---|---|---|---|---|
| gemini | `gemini-3-flash-preview` | geçti | geçti | geçti | 59/14 | başlık yok | — |
| glm | `glm-4.7-flash` | geçti | geçti | kaldı | 174/87 | başlık yok | görüntü: 400 Error code: 400 - {'error': {'code': '1210', 'message': "messages.content.type is invalid, allowed values: ['text']"}}; kota: atlandı |
| groq | `openai/gpt-oss-120b` | geçti | geçti | kaldı | 135/55 | istek 989 / token 7844 | görüntü: 400 Error code: 400 - {'error': {'message': 'messages[0].content must be a string', 'type': 'invalid_request_error', 'param': 'messages[0].content'}} |
| kilo | `nvidia/nemotron-3-super-120b-a12b:free` | geçti | geçti | kaldı | 287/38 | başlık yok | görüntü: 401 Error code: 401 - {'error': {'code': 'PAID_MODEL_AUTH_REQUIRED', 'message': 'You need to sign in to use this model.'}, 'error_type': 'paid_model_auth_required'} |
| llm7 | `gpt-oss:20b` | geçti | geçti | kaldı | 136/44 | başlık yok | görüntü: 400 Error code: 400 - {'error': {'message': "Model 'gpt-oss:20b' does not support vision input.", 'type': 'invalid_request_error', 'param': None, 'code': 'unsupported_model_feature'}} |
| mistral | `mistral-small-latest` | kaldı | kaldı | kaldı | — | başlık yok | araç: 429 Error code: 429 - {'object': 'error', 'message': 'Rate limit exceeded', 'type': 'rate_limited', 'param': None, 'code': '1300', 'raw_status_code': 429}; devam: ilk tur yok; görüntü: 429 Error code: 429 - {'objec |
| nvidia | `openai/gpt-oss-20b` | geçti | geçti | kaldı | 135/42 | başlık yok | görüntü: beklenen kod cevapta yok |
| openrouter | `nvidia/nemotron-3-ultra-550b-a55b:free` | kaldı | kaldı | kaldı | — | hata 401 | araç: 401 Error code: 401 - {'error': {'message': 'User not found.', 'code': 401}}; devam: ilk tur yok; görüntü: 401 Error code: 401 - {'error': {'message': 'User not found.', 'code': 401}}; kota: 401 Error code: 401 - { |

## Görüntü aracı (üretim yolu)

`tools.image_analyzer.image_analyze` → **geçti** (4.2 sn, model: nvidia/nemotron-3-nano-omni-30b-a3b-reasoning)

## Yöntem ve sınırlar

- Araç turu, üretimdeki `tool_choice` değeriyle gerçek adaptör üzerinden koştu; metin içindeki JSON tool_call sayılmadı.
- Görüntü testi rastgele 5 karakterlik bir kod taşıyan PNG kullandı; yalnız kodu birebir okuyan yanıt geçti.
- Görüntü testi sağlayıcının **varsayılan sohbet modeliyle** yapıldı. Sağlayıcının ayrı bir görüntü modeli olabilir; o yol `image_analyze` satırında ölçülür.
- Kota: tur başına gerçek token ve sağlayıcının döndürdüğü rate-limit başlıkları kaydedildi. Günlük/aylık tavan bu ölçümde taranmadı; ölçülmeyen tavan bilinmeyen sayılır. "Limitsiz" denmez.
- Tek koşu, tek örnek. Tekrarlı ölçüm için script yeniden koşulur; sonuç `ttl_saat` sonrası bayat kabul edilir.
- Bu rapor `--birlestir` ile tamamlandı; her sağlayıcının ölçüm zamanı ham JSON'daki `olculdu` alanındadır.

## Ham kayıt

`data/model-yetenek-olcumu.json`
