# Başak — Kota Darbesi Kitabı (olay anı el kitapçığı)

Durum: canlı zincirde 9 sağlayıcı (2026-09-29 ölçümü: groq, glm,
cloudflare, cohere, nvidia, kilo, openrouter, mistral, gemini). Hepsi aynı
anda yorulursa sohbet yanıt üretemez. Bu dosya o an ne yapılacağını söyler.

## Belirti

- Sohbet ekranı günlük kotanın dışında "yanıt yok" veriyor:
  hata akışları `chat/flow.py` (`_beyin_hata_mesaji`) ve `brain/brain.py`
  (ZincirHatasi) üzerinden kullanıcıya açık anlatılır.
- 22 yerel araç **etkilenmez**: tarayıcıda hesaplanır, sağlayıcı istemez.
  Kullanıcıya söylenecek cümle: "Sohbet yoğunluktan yavaşladı; araçlar
  çalışmaya devam ediyor."

## Tanı (sırayla, 5 dakika)

1. `/api/olcum` raporuna bak (yönetici token'ı ile): trafik mi patladı?
2. Test hesabında `/api/durum` aç: `saglayicilar` listesi kısaldı mı?
   Kısaldıysa o sağlayıcının anahtarı/kotası ölmüştür.
3. `data/audit/audit.log` sonuna bak: hata türleri (429 kota / 400 şema /
   zaman aşımı) yazar.
4. `python doktor.py --canli` YALNIZ incelemede: 1 gerçek çağrı yapar
   (kota harcar).

## Müdahale

- Kota tükenmesi: ücretsiz limitler günde/saatte sıfırlanır — bekle ve
  kullanıcıya net söyle (sohbet bunu zaten yapar: 429 + geri sayım).
- Anahtar ölümü (403/401): ilgili anahtarı yenile → ortam değişkenini
  yaz → yeni deployment (üretimde env değişimi yeni deploy gerektirir).
- Şema değişimi (400): sağlayıcı dökümanına bak → ilgili adaptörü düzelt
  + regresyon testini ekle.
- Şüpheli trafik (ölçümde anormal artış): rate-window tartışması aç;
  kota tavanını geçici düşür (env: BASAK_ANONIM_KOTA_TAVAN).

## Önleyici düzen (şu an canlıda aktif)

- 9 sağlayıcılı zincir + soğuma süreleri + yerel kota koruma (kilo/cohere).
- Yerel araçlar sunucu kotasından bağımsız (doğal afet planı).
- Tatbikat: sağlayıcı kaybı provası (bakım tatbikatı planı madde 3).
