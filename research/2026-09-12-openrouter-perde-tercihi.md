# ARAŞTIRMA — OPENROUTER İSTEĞE PERDE TERCİHİ

Tarih: 2026-09-12
Durum: KANITLANDI — KOD DENEYİNE İZİN
Risk sınıfı: Düşük (istekte 1 alan; davranış yalnız uymayan parti elenirse değişir)

## 1. Hedef

Sert perdenin OpenRouter ayağını karardan koda indirmek: her istekte
`provider: {data_collection: "deny", require_parameters: true}` gönderilir.
Veri saklayan üçüncü partiye yönlendirme kapanır; araç desteklemeyen partiye
araçlı istek gitmez. OpenAI SDK üzerinden `extra_body` ile taşınır.

## 2. Kabul kriteri

- Yeni test yeşil: sahte SDK'ya giden istekte `provider.data_collection ==
  "deny"` ve `provider.require_parameters is True`.
- `pytest tests -q` yeşil; araçsız istekte de perde gönderilir (perde görevden
  bağımsızdır).
- `:free` model seçimi, sıcaklık, tavan değişmez.

## 3. Mevcut durum kanıtı

- `brain/openrouter.py:109-126`: `cevapla` provider tercihi GÖNDERMEZ.
- Resmi doküman (`openrouter.ai/docs/guides/routing/provider-selection`):
  `data_collection: "deny"` saklayan partiyi eler; `require_parameters: true`
  parametreleri desteklemeyeni eler; uyan yoksa istek HATA verir (fail-closed).
- `data_collection` hesap-ayarından da kapatılabilir; istek-seviyesi OR ile
  çalışır (hesap açıkken bile istekte deny etkilidir).

## 4. Sorun kanıtı

OpenRouter `:free` istekleri bilinmeyen üçüncü partilere gider; loglama
politikası partiye göre değişir (resmi FAQ). Sert perde kararı (kullanıcı
onaylı) bugün bu yolda kod karşılığı olmadan duruyor.

## 5. Dış referans

Yukarıdaki resmi yönlendirme dokümanı + FAQ gizlilik bölümü
(zero-logging varsayılan, parti politikaları).

## 6. Doğrulanan gerçekler

- OpenAI SDK `extra_body` ile ek alan taşır (standart mekanizma).
- Mevcut testler istek gövdesini pinlemez (grep kanıtı).

## 7. DOĞRULANAMADI

- Uygun parti kalmazsa zincirin yerli son çareye düşüş sıklığı (canlıda
  gözlenecek; audit HATA satırları sensördür).

## 8. İzin verilen kapsam

- `brain/openrouter.py:cevapla`: `extra_body` provider tercihleri (sabit).
- Yeni test (sahte SDK, kwarg yakalama).

## 9. Yasak kapsam

- Model listesi, sıcaklık, tavan, `sort`/`order`/gecikme ayarı — dokunulmaz.
- Diğer 11 adaptör — dokunulmaz.

## 10. Korunacak davranışlar

- `:free` seçimi, fallback zinciri, yerel son çare aynen çalışır.
- Perde yüzünden parti bulunamazsa HATA → zincir devam eder (fail-closed,
  sessiz düşme yok).

## 11. Risk sınıfı

Düşük.

## 12. Kabul sensörleri

Yeni ünite testi + `pytest tests -q` + canlı auditte openrouter HATA artışı
takibi.

## 13. Geri alma koşulu

Openrouter başarı oranında anlamlı düşüş veya test gerilemesi olursa paket
geri alınır (tek commit).

## 14. Sonuç (2026-09-12 uygulandı)

- `PERDE_TERCIHI` sabiti + `extra_body` ile her istekte gönderilir.
- Yeni `tests/test_openrouter_perde.py` 3/3 yeşil; tam paket 569 geçti / 0 hata.
- KANITLANDI → paket tamamlandı (commit bekliyor).
