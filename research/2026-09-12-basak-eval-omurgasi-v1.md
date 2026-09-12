# BAŞAK — EVAL OMURGASI v1 ARAŞTIRMASI

Durum: **KANITLANDI — KOD DENEYİNE İZİN**  
Tarih: **12 Eylül 2026**  
Kapsam: Başak'ın mevcut davranışını ölçen, üretim davranışını değiştirmeyen eval/benchmark omurgası

## 1. Hedef

Başak'ta yapılacak sonraki davranış değişikliklerinin gerçekten iyileştirme mi yoksa gerileme mi olduğunu aynı görevler, aynı ölçütler ve aynı rapor biçimiyle kanıtlayabilmek.

## 2. Kabul kriteri

İlk değişiklik paketi başarılı sayılmak için:

- üretim sohbet/brain/tool davranışını değiştirmemeli,
- mevcut `master` için tekrar üretilebilir baseline üretmeli,
- gerçek Başak görevlerini sabit bir eval veri setiyle koşturabilmeli,
- tool seçimi, görev sonucu, süre, token, provider/fallback ve hata verisini tek raporda toplamalı,
- dış dünyaya yazan araçları çalıştırmamalı,
- ücretli provider çağırmamalı,
- deterministik regresyon sonucunu otomatik vermeli,
- canlı ücretsiz-provider smoke sonucunu ayrı raporlamalı,
- baseline ve aday dalı karşılaştırıp `İYİLEŞTİ / AYNI / REGRESYON / SONUÇSUZ` kararı üretebilmeli.

## 3. Mevcut durum kanıtı

### 3.1 `brain/stats.py` var ama görev doğruluğunu ölçmüyor

Mevcut sistem her model çağrısında:

- provider/model,
- başarılı/başarısız,
- süre,
- tool kullanımı,
- giriş/çıkış tokenı,
- hata

kaydını tutuyor.

Bu veri çağrı seviyesindedir. `Başak kullanıcının görevini doğru tamamladı mı?`, `doğru aracı mı seçti?`, `araç gerekmediğinde gereksiz araç kullandı mı?`, `cevap doğrulanabilir mi?` sorularını tek başına cevaplamaz.

Kaynak: `brain/stats.py`.

### 3.2 `tools/deney.py` var ama konuşma/task eval'i değil

DENEY-0 motoru read-only araç çıktıları üzerinde deterministik kurallar (`icerir`, `yok`, `esik_ust`, `esik_alt`) çalıştırıyor. Bu güçlü bir temel fakat gerçek `chat.flow` görev zincirini değerlendirmiyor.

Kaynak: `tools/deney.py`.

### 3.3 Mevcut E2E test gerçek sağlayıcı + gerçek sohbet eval'i değil

`tests/test_e2e_beyin.py`, FAY → gerilim → DENEY → evrim → dünya zincirini sahte `calistir` ve kontrollü cevaplarla test ediyor. Bu test organ entegrasyonu için değerlidir fakat gerçek kullanıcı mesajını `chat.flow.mesaj_isle_yeni` üzerinden ücretsiz provider zincirine gönderip görev başarısını ölçmüyor.

Kaynak: `tests/test_e2e_beyin.py`.

### 3.4 `chat.flow` testleri çoğunlukla kontrollü/fake brain kullanıyor

Mevcut testler streaming/raw tool gibi davranışları yapısal olarak doğruluyor. Bu, regresyon testidir; gerçek ücretsiz provider havuzunun aynı kullanıcı görevlerinde davranışını sayısallaştıran canlı baseline değildir.

Kaynak örnekleri: `tests/test_akis_ham_arac.py`, `tests/test_kapasite_kapi.py`.

### 3.5 Ücretsiz sağlayıcı havuzu zaten registry'de tanımlı

`brain/registry.py` ücretsiz/ücretli ayrımını ve limitleri içeriyor. DeepSeek/Kimi/özel provider ücretli olarak işaretli; mevcut ana ücretsiz havuz GLM, Cloudflare, Groq, NVIDIA, Cohere, Kilo, Gemini, OpenRouter ve uygun olduğunda QwenCloud; Ollama son çare.

Bu nedenle eval omurgası ücretli provider'ı ayrıca tahmin ederek değil registry gerçeğinden filtreleyebilir.

## 4. Dış referanslar

### OpenAI — contextual eval yaklaşımı

OpenAI, gerçek ürün/workflow için başarı tanımının açık yazılmasını, gerçek durumları temsil eden örnekler kullanılmasını ve `Specify → Measure → Improve` döngüsünü öneriyor. Ajan değerlendirmesinde yalnız model değil harness, araçlar, bütçe ve doğrulama yöntemi de sonucu etkiliyor.

Kaynaklar:
- https://openai.com/index/evals-drive-next-chapter-of-ai/
- https://openai.com/index/trustworthy-third-party-evaluations-foundations/
- https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/

### Anthropic — test ve verification ilkeleri

Anthropic'in ajan geliştirme rehberi; testlerin iş başlamadan tanımlanmasını, ajan testleri geçmek için testleri değiştirmemeli ilkesini, gerçek entegrasyon doğrulamasını ve browser/tool verification araçlarını öneriyor.

Kaynak:
- https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/prompt-templates-and-variables

## 5. Doğrulanan gerçekler

1. Başak'ta çağrı istatistiği vardır.
2. Başak'ta deterministik deney motoru vardır.
3. Bu iki sistem şu anda gerçek kullanıcı görevi seviyesinde birleşmiş bir eval omurgası değildir.
4. Mevcut E2E testi gerçek provider/harness görev başarısını ölçmez.
5. Provider ücretsiz/ücretli bilgisi registry'de mevcut olduğundan 0 TL kuralı kodla uygulanabilir.
6. OpenAI'nin güncel eval yaklaşımı, ürünün gerçek workflow'una özel baseline/eval kurulmasını önerir.

## 6. Doğrulanamayanlar

- Bugünkü ücretsiz provider havuzunun gerçek görev başarı oranı: **DOĞRULANAMADI**.
- Streaming yolunun toplam görev başarısına etkisinin yüzdesi: **DOĞRULANAMADI**.
- Hangi harness varyantının en iyi olduğu: **DOĞRULANAMADI**.

Bu üç sonuç eval omurgası kurulmadan güvenilir biçimde çıkarılamaz.

## 7. İzin verilen değişiklik kapsamı

İlk paket yalnız eval/benchmark altyapısı olabilir:

- sabit eval görev veri seti,
- runner,
- sonuç/trace toplama,
- deterministik grader,
- baseline karşılaştırıcı,
- rapor çıktısı,
- yalnız eval için güvenli fixture/test verisi.

Gerekirse mevcut `brain.stats` ve `tools.deney` read-only olarak yeniden kullanılabilir.

## 8. Yasak kapsam

Bu paket içinde aşağıdakiler değiştirilemez:

- `chat.flow` davranışı,
- streaming/tool routing kararı,
- provider sırası,
- prompt/personality içeriği,
- memory/profile davranışı,
- browser entegrasyonu,
- Vixrex lead akışı,
- izin sistemi,
- kullanıcı arayüzü.

Eval kurmak ile ürünü düzeltmek aynı commit/paket olmayacak.

## 9. Korunacak davranışlar

- Bugünkü çalışan Başak ana yolu değişmeyecek.
- Registry'deki ücretli provider'lar eval tarafından çağrılmayacak.
- Dış dünya yazma araçları eval'de kapalı olacak.
- Kullanıcı dosyaları yerine kontrollü fixture dosyaları kullanılacak.
- Gerçek provider smoke testi otomatik CI'da kotayı tüketmeyecek; elle çalıştırılacak.

## 10. Risk sınıfı

**ORTA RİSK.**

Üretim davranışını değiştirmese de yanlış eval tasarımı sonraki bütün geliştirme kararlarını yanlış yönlendirebilir. Ayrıca canlı smoke testi ücretsiz kotaları tüketebilir. Bu nedenle eval veri seti, grader ve bütçe açıkça sürümlenmelidir.

## 11. Kabul sensörleri

- eval runner unit testleri,
- grader unit testleri,
- fixture üzerinde deterministik tekrar üretilebilirlik,
- ücretli provider engel testi,
- write-tool engel testi,
- baseline rapor şema testi,
- aynı commit iki kez koşturulduğunda deterministik bölümün aynı sonuç vermesi,
- kontrollü canlı smoke raporu.

## 12. Geri alma koşulu

Paket:

- üretim davranışına müdahale ederse,
- ücretli provider çağırabilirse,
- dış dünyaya yazan tool çalıştırabilirse,
- baseline sonuçlarını tekrar üretemezse,
- grader testleri değiştirerek sonuca uydurulursa

reddedilir/geri alınır.

## 13. Araştırma kararı

**KANITLANDI — KOD DENEYİNE İZİN.**

Sıradaki en büyük somut geliştirme adımı:

# `BAŞAK EVAL OMURGASI v1`

Bu omurga kurulmadan streaming, harness, kişiselleştirme veya provider-routing değişikliklerinin hangisinin gerçekten Başak'ı iyileştirdiğini güvenilir biçimde söylemek mümkün değildir.
