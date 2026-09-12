# AGENTS.md — Başak geliştirme kuralları

Bu dosya Başak üzerinde çalışan kod ajanları için güncel ve bağlayıcı kuralları içerir.
Eski faz/roadmap kayıtları yürürlükte değildir; kod kararı verirken bu dosya ve mevcut kaynak kod esas alınır.

## 1. Ürün hedefi

Başak, Furkan'ın kişisel asistan katmanıdır.

Başak'ın geliştirdiğimiz kısmı yeni bir model zekâsı değildir. Amaç:

- mevcut ücretsiz bulut modellerinin hazır yeteneklerini mümkün olduğunca eksiksiz kullanmak,
- sağlayıcılar arasında ücretsiz ve hataya dayanıklı geçiş yapmak,
- Furkan'ın ilgili kişisel/proje bağlamını ve konuşma geçmişini taşımak,
- güvenli araçları modele sunup hangi aracı ne zaman kullanacağını modele bırakmak,
- uzun işleri kaybetmeden sürdürebilmek,
- tüm bunları otomatik ücretli model/özellik çağırmadan yapmak.

Yerel Ollama, ücretsiz bulutlar çalışmadığında son çaredir; bulut modelleri yalnız “zor soru” için ayrılmaz.

## 2. Modeli kısıtlama

Yasak:

- modeli “küçük/güçlü” diye sınıflandırıp daha az hafıza, daha az araç veya daha az çalışma turu vermek,
- kullanıcı mesajındaki kelimelerden `kod / araştırma / hız` türü çıkarıp sağlayıcı seçmek,
- geçmiş başarı yüzdesiyle modelin zekâsını puanlayıp semantik sıralama yapmak,
- güvenli araçları anahtar kelimeye göre modelden saklamak,
- modele “şimdi şu aracı kullan” veya “sonucu şu biçimde yaz” diye gereksiz zorlayıcı prompt eklemek,
- modelin düşünme/reasoning özelliğini sebepsiz kapatmak,
- sağlayıcının doğal çıktı kapasitesini sabit düşük `max_tokens` değeriyle kesmek,
- jüri, gölge model, çoklu-model tartışması veya kendini geliştiren meta-zeka katmanını ana sohbet yoluna sokmak.

Sağlayıcı sırası yalnız teknik nedenlerle değişebilir: kullanılabilirlik, desteklenen istek özelliği, 429/kota, zaman aşımı ve geçici hata.

## 3. Araç kullanımı

Araç şemaları modele sunulur. Model gerekli görürse araç çağırır.

Uygulama tarafının görevi:

1. araç adını ve argümanlarını doğrulamak,
2. izin kurallarını uygulamak,
3. aracı çalıştırmak,
4. sonucu standart araç sonucu olarak modele geri vermek,
5. model isterse sonraki araç çağrısına devam etmektir.

Ara sonuçtan sonra modele yapay bir kullanıcı mesajıyla cevap biçimi dayatılmaz.

### Güvenlik

Güvenlik model promptuna bırakılmaz.

- Hassas/sistem alanları mevcut izin katmanıyla korunur.
- Güvenli alan dışına yazma kullanıcı onayı gerektirir.
- Bilinmeyen araç çalıştırılmaz.
- İzin ve onay kontrolleri modelin isteğinden bağımsız deterministik kodda kalır.

## 4. Ücretsiz maliyet kuralı

Otomatik sağlayıcı zinciri ücretli sağlayıcı çağırmaz.

- OpenRouter kullanılıyorsa yalnız `:free` / `openrouter/free` yolları kullanılır.
- Kilo kullanılıyorsa yalnız ücretsiz model/`kilo-auto/free` yolu kullanılır.
- Sağlayıcıya ait ücretli web araması, ücretli ajan aracı veya ücretli özel özellik otomatik açılmaz.
- Bir özelliğin ücretsiz olduğu doğrulanamıyorsa otomatik zincire eklenmez.
- Ücretsiz kota biterse para harcamak yerine hata/fallback tercih edilir.

Not: Groq, Gemini, Cloudflare ve benzeri servislerde hesabın ücretsiz veya ücretli katmanda olması sağlayıcı hesabına bağlı olabilir. Kod yeni ücretli özellik açmamalı ve `registry` tarafından ücretli işaretlenen sağlayıcıyı otomatik zincire almamalıdır.

## 5. Hafıza ve bağlam

Başak kullanıcının her şeyi baştan anlatmasını istememelidir.

- Kalıcı profil/hafıza korunur.
- İlgili anılar ana sohbete eklenebilir.
- Konuşma geçmişi gereksiz derecede küçük sabit bir pencereye sıkıştırılmaz.
- Hassas bilgi mevcut gizlilik kuralları dışında profile alınmaz.
- Bağlam, modelin yerine karar veren bir “zeka katmanı” değildir; modele gerekli bilgiyi taşır.

## 6. Uzun görev sistemi

`tools/is_kuyrugu.py` korunur.

Bu sistem model zekâsı değildir; iş durumunu diskte tutar, yarım işi görünür kılar ve sonraki çalışmada devam etmeye temel sağlar. Yeniden yazılmamalı veya “meta-zeka temizliği” gerekçesiyle silinmemelidir.

## 7. Sağlayıcı entegrasyonları

Ortak arayüz ve adapter yapısı korunur.

Her sağlayıcı için mümkün olduğunda:

- native tool/function calling kullanılabilir olmalı,
- reasoning özelliği Başak tarafından sebepsiz kapatılmamalı,
- sabit düşük çıktı limiti konmamalı,
- gerçek modelin ihtiyacı olan makul zaman tanınmalı,
- hata/429 durumunda sıradaki ücretsiz sağlayıcıya geçilmeli.

Sağlayıcıya özel ücretli yetenekler bu hedefin parçası değildir.

## 8. Değişiklik disiplini

- `master` üzerinde doğrudan çalışma yapılmaz; ayrı dal kullanılır.
- İstenen kapsam dışı refactor yapılmaz.
- Bir davranış değişiyorsa eski davranışı kilitleyen test de yeni sözleşmeye çevrilir.
- Çalıştırılmamış test için “yeşil” denmez.
- Doğrulanamayan durum açıkça `doğrulanamadı` diye belirtilir.
- Güvenlik, ücretsiz maliyet kilidi, kalıcı hafıza ve uzun görev sistemi korunur.

## 9. Güncel mimari özeti

```text
Furkan
  ↓
Başak bağlamı + konuşma geçmişi
  ↓
ücretsiz sağlayıcı geçidi
  ↓
model + tüm güvenli araç şemaları
  ↓
model doğal olarak cevap verir veya araç ister
  ↓
izin/onay kontrolü → araç çalışır → sonuç modele döner
  ↓
gerekirse yeni araç çağrısı → final cevap
```

Temel ilke:

> Başak modeli yönetmeye çalışmaz; ücretsiz modellerin hazır zekâsına bağlam, araç erişimi, güvenlik ve kesintiye dayanıklılık sağlar.
