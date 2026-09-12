# BAŞAK — SIRADAKİ EN BÜYÜK SOMUT ADIM

Durum: **PLANLANDI — ÜRÜN KODU DEĞİŞMEDİ**  
Tarih: **12 Eylül 2026**  
Dayanak araştırması: `research/2026-09-12-basak-eval-omurgasi-v1.md`

# Hedef: BAŞAK EVAL OMURGASI v1

Amaç; Başak'ta yapılacak her sonraki değişiklik için aynı gerçek görevleri koşturup `iyileşti / aynı / regresyon / sonuçsuz` kararı verecek güvenilir ölçüm omurgasını kurmaktır.

Bu paket yeni özellik değildir. Başak'ın gelişimini güvenli ve ölçülebilir hale getiren temel altyapıdır.

## Neden şimdi?

Bugün Başak'ta:

- model çağrı istatistiği var,
- tool/deney motoru var,
- unit/integration testler var,
- provider fallback/routing var,

ama bunların hiçbiri tek başına şu soruyu cevaplamıyor:

> Aynı kullanıcı görevi, bu değişiklikten önce mi sonra mı daha doğru tamamlandı?

FAZ 0 baseline, FAZ 1 harness karşılaştırması ve sonraki bütün fazlar bu cevaba bağlıdır.

## Paket sınırı

Bu pakette yalnız ölçüm altyapısı yapılır. Başak'ın davranışı değiştirilmez.

### Paket A — Golden görev seti

İlk sürümde 24 sabit görev:

- 4 normal sohbet / tool gerekmiyor,
- 4 dosya listeleme-okuma,
- 4 web araştırma / sayfa okuma,
- 4 yanlış tool kullanmama / uydurma karşıtı görev,
- 4 timeout/fallback/routing senaryosu,
- 4 kişisel bağlam gerektiren-gerektirmeyen görev.

Her görev için önceden:

- beklenen davranış,
- izin verilen tool,
- yasak tool,
- başarı kriteri,
- kritik hata kriteri

yazılır.

Golden set, davranış koduyla aynı değişiklik paketinde sonuca uydurulamaz.

### Paket B — Deterministik regresyon runner'ı

Dış API gerektirmeyen test katmanı:

- kontrollü provider cevapları,
- kontrollü fixture dosyaları,
- kontrollü tool çıktıları,
- timeout/429/fallback simülasyonu.

Her committe çalıştırılabilir.

Ölçer:

- doğru tool seçildi mi,
- tool gerekmeyen görevde tool çağrıldı mı,
- doğru fallback yapıldı mı,
- sonuç beklenen veriye dayanıyor mu,
- görev tamamlandı mı.

### Paket C — Canlı ücretsiz-provider smoke

Otomatik CI'da çalışmaz. Elle ve sınırlı sayıda çalıştırılır.

Kurallar:

- yalnız `registry.ucretsiz == True` provider,
- ücretli provider kesin engel,
- her görev en fazla 1 ana deneme,
- gereksiz tekrar yok,
- write tool yok,
- ücretsiz kota bütçesi aşılırsa test durur.

Amaç tek tek model yarıştırmak değil, **Başak'ın gerçek ücretsiz provider zincirini** ölçmektir.

### Paket D — Tek rapor

Her koşum JSON + kısa Markdown rapor üretir.

Asgari alanlar:

- commit SHA,
- görev ID,
- seçilen provider,
- harness/varyant etiketi,
- modele verilen tool sayısı,
- çağrılan tool,
- doğru/yanlış tool,
- görev başarı durumu,
- latency,
- token in/out varsa,
- fallback sayısı,
- hata/timeout,
- prompt boyutu,
- kişisel bilgi sayısı,
- kritik uydurma/kanıtsız cevap işareti.

### Paket E — Baseline karşılaştırıcı

Bugünkü `master` ilk baseline olarak kaydedilir.

Sonraki aday dal sonucu baseline ile karşılaştırılır.

Karar yalnız:

- `İYİLEŞTİ`
- `AYNI`
- `REGRESYON`
- `SONUÇSUZ`

olabilir.

Tek toplam puan zorunlu değildir. Kritik metrikler ayrı tutulur; örneğin tool doğruluğu artarken sohbet kalitesi bozulursa bu `iyileşti` diye gizlenemez.

## Ana metrikler

1. Görev tamamlama oranı.
2. Doğru tool seçme oranı.
3. Gereksiz tool çağırmama oranı.
4. Doğrulanmış veriye dayanma oranı.
5. Kritik uydurma sayısı.
6. Timeout/fallback başarısı.
7. Ortalama süre.
8. Prompt boyutu.
9. Tool şeması/araç sayısı.
10. Ücretsiz kota tüketimi.

## Geliştirme sırası

- [ ] Eval veri şeması ve 24 golden görev tanımı.
- [ ] Deterministik grader ve karar kuralları.
- [ ] Üretim davranışına dokunmadan runner.
- [ ] `brain.stats` / mevcut loglardan veri toplama adaptörü.
- [ ] Deterministik timeout/fallback senaryoları.
- [ ] Ücretli-provider ve write-tool sert engelleri.
- [ ] JSON/Markdown raporu.
- [ ] `master` baseline koşumu.
- [ ] Canlı ücretsiz-provider smoke koşumu.
- [ ] Baseline karşılaştırıcı.
- [ ] Bağımsız code review + eval manipülasyonu kontrolü.

## İlk kabul kapısı

Omurga tamamlandı denmeden önce:

1. Bugünkü `master` için rapor üretilmeli.
2. Aynı deterministik koşum iki kez aynı sonucu vermeli.
3. Bilerek bozuk bir fixture değişikliği `REGRESYON` üretmeli.
4. Ücretli provider denemesi engellenmeli.
5. Write-tool denemesi engellenmeli.
6. Canlı smoke sadece ücretsiz havuzda çalışmalı.
7. Ürün davranışı diff'i sıfır olmalı.

## Bu paket bittikten sonra ilk gerçek davranış deneyi

Eval omurgası baseline ürettikten sonra ilk aday davranış değişikliği yeniden araştırma kapısından geçirilir.

Mevcut en güçlü aday:

**tool gerektiren görevlerde toolsuz streaming ile tool-aware yolun gerçek Başak görev başarısına etkisi.**

Ama eval sonucu çıkmadan bu değişiklik yapılmaz.

## Başarı sonucu

Bu adımın sonunda artık şu cümleyi kanıtla söyleyebilmeliyiz:

> `Bu commit Başak'ı şu görevlerde geliştirdi; şu görevlerde aynı kaldı; şu metrikte gerilemedi.`

Bundan sonra FAZ 1 harness, FAZ 2 kişiselleştirme ve FAZ 3 browser kararları aynı omurga üzerinden ölçülür.
