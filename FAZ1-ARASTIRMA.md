# BAŞAK — FAZ 1 HARNESS ARAŞTIRMASI

Durum: **BAŞLADI — KAPSAM DÜZELTİLDİ**  
Tarih: **12 Eylül 2026**  
Maliyet kuralı: **0 TL — ücretli sağlayıcı kullanılmaz**

## 1. Gerçek araştırma hedefi

Başak'ın ana çalışma hattı tek bir yerel model değildir. Ana hedef, mevcut **ücretsiz sağlayıcı zincirinin** araç kullanımı, timeout, fallback ve limit davranışını daha güvenilir hale getirmektir.

Bugünkü `master` registry sırası:

`GLM → Cloudflare → Groq → NVIDIA → Cohere → Kilo → Gemini → OpenRouter → QwenCloud`

Görev tipine göre seçim motoru bu sırayı yeniden düzenleyebilir.

`Ollama (yerel)` internet/kota bittiğinde **son çare/fallback** olarak tutulur; FAZ 1'in ana benchmark hedefi değildir.

QwenCloud ayrıca mevcut registry'de uyku durumundadır (`etkin: false`) ve hesap etkinleşmeden zincire girmez.

## 2. Karşılaştırılacak çalışma biçimleri

A. Mevcut Başak: önce araçsız streaming, sonra gerekirse tool-call.  
B. Araç gerektiren görevde doğrudan tool-aware istek.  
C. Sağlayıcı/model ailesine göre minimum harness.  
D. Yalnız görev için gerekli 0–3 kişisel gerçek.

Karşılaştırma tek modele göre değil, kullanılabilir ücretsiz sağlayıcılar üzerinde yapılır.

Ölçülecekler:

- doğru araç seçimi,
- araçsız düz metinle kaçış,
- görevi gerçekten tamamlama,
- timeout,
- fallback başarısı,
- kaç sağlayıcı denendiği,
- cevap süresi,
- uydurma/doğrulanmamış bilgi,
- tüketilen ücretsiz kota/istek sayısı.

## 3. Mevcut koddan doğrulanan yapısal sorun adayı

`chat/flow.py` araçsız streaming turunu önce çalıştırır.

Bu ilk tur araç şemalarını modele vermeden temiz bir düz metin üretirse akış orada bitebilir ve gerçek tool-aware yol hiç çalışmayabilir.

Bu durum yalnız Ollama/Qwen'e özgü bir problem olarak ele alınmayacaktır. Aynı davranış ücretsiz bulut sağlayıcı zincirinde de ölçülecektir.

## 4. Qwen araştırmasının doğru yeri

Qwen araştırması iptal edilmedi; kapsamı düzeltildi.

Qwen function-calling dokümanı, tool-aware şema/chat-template kullanımının önemli olduğunu gösterdi. Bu bulgu **genel harness tasarımı için referanstır**, fakat yerel qwen2.5:7b sonucu Başak'ın genel mimarisini tek başına belirleyemez.

Yerel Qwen testi yalnız şunlar için tutulur:

- internetsiz fallback kontrolü,
- ücretli servis olmadan izole tool-call testi,
- ana bulut zinciri bozulursa son çare davranışı.

## 5. Maliyetsiz sağlayıcı zinciri

`brain/registry.py` mevcut kartlarına göre ücretsiz ana sağlayıcılar:

- GLM
- Cloudflare
- Groq
- NVIDIA
- Cohere trial
- Kilo
- Gemini free tier
- OpenRouter `:free`
- QwenCloud (şu an uyku durumunda)
- Ollama yerel fallback

Ücretli `deepseek`, `kimi` ve `genel/özel sağlayıcı` FAZ 0–1 benchmarkına dahil edilmez.

## 6. Limit koruması

Benchmark kota yakmayacak şekilde küçük tutulur.

İlk turda her kullanılabilir ücretsiz sağlayıcı için aynı 4 görev en fazla 1–3 tekrar çalıştırılır:

1. `Masaüstündeki dosyaları göster.`
2. `Şu dosyanın içinde ne yazıyor?`
3. `Bugünkü güncel bir bilgiyi webde araştır ve kaynağını söyle.`
4. `Merhaba, nasılsın?` — araçsız kontrol.

Limitli sağlayıcılar gereksiz tekrar için kullanılmaz. Gemini/OpenRouter gibi sınırlı sağlayıcıların kotası korunur.

## 7. Karar kapısı

Yerel Qwen benchmarkı artık **geliştirme kapısı değildir**.

Yeni karar kapısı:

1. Gerçek ücretsiz sağlayıcı zincirinin mevcut A yolu ölçülür.
2. Aynı sağlayıcılar mümkün olduğunda B/tool-aware yolda ölçülür.
3. Tool-aware yol görev başarısını artırıyor ve normal sohbeti bozmuyorsa küçük deney koduna geçilir.
4. Fark yoksa streaming değiştirilmez; prompt/harness yükü incelenir.
5. Gerileme varsa deney reddedilir.

**Çalışan Başak kanıt olmadan değiştirilmeyecek. Yerel Ollama/Qwen son çare olarak korunacak; ana geliştirme ücretsiz sağlayıcı zincirine göre yapılacak.**
