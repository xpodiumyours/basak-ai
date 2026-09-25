# AGENTS.md — Başak P2 bağlayıcı mühendislik kuralları

Bu dosya Başak üzerinde kod değiştiren her ajan için yürürlükteki tek mimari sözleşmedir.
Tarihî mimari notları burada tutulmaz; geçmiş commitler yalnız tarihçedir.

## 0. Değişmez hedef

Başak bir kelime/niyet router'ı, chatbot kural motoru veya ikinci karar motoru değildir.

- Kullanıcının ne istediğini ve hangi gerçek aracı kullanacağını model belirler.
- Uygulama yalnız gerçek araç kataloğunu, teknik sağlayıcı erişimini, güvenliği,
  kota/bağlantı durumunu ve doğrulanabilir çalışma durumunu yönetir.
- Kullanıcı cümlesinden araç, sağlayıcı, görev türü veya yetenek alanı çıkaran kod yazılmaz.
- Gizli resolver, kategori kapısı, meta-tool, görev sınıflandırıcı veya profil regex'i yoktur.
- `chat/tool_resolver.py` ve `chat/agent_protocol.py` bulunamaz.
- `gorev_tipi`, `karne_kullan` gibi eski karar parametreleri aktif imzalarda bulunamaz.

## 1. Ajan döngüsü

Provider-neutral akış:

`user -> model -> native tool_call -> gerçek tool sonucu -> aynı run içinde model -> ... -> final`

- `tool_policy` yalnız açık run politikasıdır: `auto | required | none`.
- Politika kullanıcı metninden tahmin edilmez.
- `auto` ve `required` tam gerçek capability yüzeyini korur.
- Tool sonucu modele `assistant.tool_calls -> tool result` sırasıyla geri verilir.
- Genel tur tavanı yoktur.
- Aynı araç + aynı argüman + aynı sonuç sonsuz döngüsü yalnız teknik loop guard ile kesilebilir.
- Tool sonrası model tekrar araç çağırabilir veya final verebilir.
- Destekleyen sağlayıcılarda ileride native tool discovery/deferred loading kullanılabilir;
  uygulamaya ait gizli semantik resolver yazılamaz.

## 2. Araç şemaları

Gerçek araç ekleme noktaları:

1. `tools/definitions.py` — şema
2. `tools/__init__.py` — gerçek çalıştırıcı
3. `tools/capabilities.py` — metadata/test; runtime semantik filtresi değildir
4. `chat/tools.py` — kullanıcıya görünen çalışma durumu

Araç açıklaması yalnız ne yaptığı, parametreleri, dönüşü ve gerçek teknik sınırı anlatır.
"Önce bunu yap", "şunu kullanma", "şöyle cevapla" gibi davranış koçluğu yazılmaz.

## 3. Sağlayıcı katmanı

- Sağlayıcı sırası kullanıcı metnine göre değişmez.
- Teknik fallback yalnız erişilebilirlik, gerçek API/tool desteği, ücret politikası,
  rate limit/cooldown ve bağlantı hataları gibi altyapı gerçeklerine dayanabilir.
- Model adına bakıp "küçük/büyük", "kod modeli", "araştırma modeli" diye runtime davranışı değiştirilemez.
- Araç var diye belirli modele zorla geçilemez.
- Uygulama yapay `max_tokens` tavanı koymaz.
- Model cevabını 8/20/60 saniye gibi kısa uygulama timeout'larıyla kesmez.
- Sağlayıcının resmî `tool_choice` desteği kullanılır; desteklenmeyen değer taklit edilmez.
- Provider'a özel reasoning/imza metadata'sı başka sağlayıcıya taşınmaz; standart tool zinciri korunur.

## 4. Çıktı ve bağlam

- Model çıktısı sessizce kısaltılmaz, yeniden yazılmaz veya tamamlanmış gibi gösterilmez.
- `finish_reason` teknik durum olarak taşınır.
- Geçmiş, tool sonucu, sayfa sonucu veya Yönlendir bağlamı sessiz `slice`/karakter/adet tavanıyla budanmaz.
- Gerçek provider/context sınırı aşılırsa hata veya incomplete durumu görünür olur.
- Uygulama modele gizli "devam et", "araç çağırma", "önce doğrula" benzeri koçluk mesajı eklemez.

## 5. Yönlendir

Yönlendir yeni bir run başlatır fakat önceki tamamlanmamış run'ın doğrulanmış bağlamını kaybetmez.

- Önceki kullanıcı isteği korunur.
- Gerçek tool çağrıları, argümanları ve gerçek tool sonuçları korunur.
- Kaynaklar, partial output ve run-state korunur.
- Tarayıcıdan gelen handoff verisi sunucu doğrulaması olmadan gerçek kabul edilmez.
- Handoff sessiz kırpılmaz.
- "Resume ettim" gibi sahte devam iddiası yoktur; yeni run olduğu açık kalır.
- Yeni yönü yorumlayan yine modeldir; yönlendirme için ikinci karar motoru kurulmaz.

## 6. Hafıza ve profil

- Kullanıcı cümlesini regex/kelimeyle yorumlayıp otomatik profil üretmek veya silmek yasaktır.
- Kayıtlı profil yalnız salt-okunur bağlam olabilir.
- Hafızadaki eski Başak cevapları güncel dış dünya kanıtı değildir.
- Kullanıcı/oturum izolasyonu korunur; preview production hafızasına bağlanamaz.

## 7. Güvenlik istisnaları

Aşağıdakiler chatbotlaştırma sayılmaz ve korunur:

- sır/credential dosyası engelleri,
- path traversal ve sistem yolu koruması,
- SSRF ve ağ güvenliği,
- sunulmayan aracın çalıştırılmaması,
- kimlik doğrulama ve imza doğrulama,
- gerçek rate-limit/cooldown,
- aynı tool çağrısının doğrulanmış sonsuz tekrarını kesen loop guard.

Bu korumalar kullanıcı niyetini yorumlayamaz veya model adına iş kararı veremez.

## 8. P2 kabul kapısı

P2 "tamamlandı" sayılmaz; aşağıdakilerin tamamı gerekir:

1. 12 risk regresyon kapısının tamamı yeşil.
2. `tests/test_chatbot_yasagi.py` yeşil.
3. Tam kotasız pytest yeşil.
4. Python syntax/import collection yeşil.
5. Web Yönlendir uçtan uca: UI -> API -> doğrulanmış handoff -> agent context.
6. `auto|required|none` backend ve web taşıma sözleşmesi tutarlı.
7. Provider failover tool zincirini bozmuyor.
8. Preview hafızası production'dan izole.
9. Vercel preview build başarılı.
10. Code review/checkler başarılı.
11. Tek final FULL TEST P2 sağlayıcı matrisi başarılı.
12. Main/canlı ancak tüm kanıtlar tamamlandıktan sonra tek geçişle güncellenir.

## 9. Yayın disiplini

- Geliştirme yalnız `preview/p2-arac-ara-profesyonel` üzerinde yapılır.
- `main` ve production doğrulama bitmeden değiştirilmez.
- Deneme commitleriyle deploy kotası tüketilmez; mümkün olduğunca tek doğrulanmış commit kullanılır.
- PR draft kalabilir; test ve canlı kanıt bitmeden merge edilmez.
- Merge/deploy öncesi tetiklenecek CI, provider ve Vercel etkileri kontrol edilir.
- Canlıya geçişten önce rollback noktası mevcut canlı commit'tir.
