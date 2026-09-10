# BAŞAK KİLİTLİ GELİŞİM PLANI

Durum: **KİLİTLİ**
Kilit tarihi: 10 Eylül 2026
Çalışma alanı: yalnızca `C:\Projects\Başak`

## Değiştirilemez hedef

Başak; ücretsiz ve küçük modelleri verimli kullanan, yerel çalışmayı önceleyen,
Casper'ı konuşarak tanıyan, yalnızca ilgili kişisel bilgiyi doğru zamanda
kullanan, düzeltmeleri öğrenen, unutma isteğine eksiksiz uyan ve yaptığı işi
doğrulamadan tamamlandı saymayan kişisel bir ajan olacaktır.

Başak'ın kişiliği ve hafızası kullanılan modele bırakılmayacaktır. Kimlik,
profil, yakın konuşma, düzeltme, unutma, görev devamlılığı ve işlem sonucu
proje kodunun doğrulanan sorumluluğudur. Model değiştirilebilir bir cevap
üreticisidir.

## Değiştirilemez çalışma kuralları

1. Plan genişletilemez ve daraltılamaz.
2. Yeni sağlayıcı, gösterişli muhakeme katmanı veya bağımsız özellik bu planın
   sırası tamamlanmadan eklenemez.
3. Her davranış önce başarısız bir sınamayla görünür kılınır, sonra en küçük
   değişiklikle düzeltilir.
4. Her küçük değişiklikten sonra ilgili sınamalar; her dilim sonunda bütün
   sınamalar çalıştırılır.
5. Gerçek kullanıcı davranışı yalnız parça sınamalarıyla değil, baştan sona
   konuşma örnekleriyle doğrulanır.
6. Mevcut çalışan davranış sebepsiz sökülmez. Geri dönüş yolu korunur.
7. Kullanıcının açık sözü, doğrulanmış araç sonucu ve kullanıcının onayladığı
   çıkarım dışında hiçbir şey kalıcı gerçek sayılmaz.
8. Başak'ın kendi cevabı kullanıcı gerçeği olarak profile yazılmaz.
9. Hassas bilgi kalıcı profile alınmaz; buluta yalnız görev için gereken en az
   kişisel bilgi gönderilir.
10. Başarı, yalnız sağlayıcının cevap vermesi değildir. Doğru hatırlama,
    doğru araç kullanımı, düzeltme, unutma ve kullanıcı sonucu ayrı ölçülür.
11. Proje dışındaki dosyalar ve projeler bu çalışmanın konusu değildir.
12. `ayarlar.json`, anahtarlar ve sır içeren dosyalar okunmaz veya rapora
    taşınmaz. Sırlar kaynak koda ve kayıtlara yazılmaz.
13. Çalışma ağacındaki önceden var olan kullanıcı değişiklikleri korunur.
14. Her döngü sonunda şu beş soru cevaplanır: Ne görüldü? Ne değişti? Nasıl
    sınandı? Ne başarısız oldu? Sıradaki kilitli adım nedir?

## Gelişim döngüsü

Her dilim aynı döngüyü izler:

1. **Bak:** Çalışan gerçek yol ve son kullanıcı sonucu gözlenir.
2. **Araştır:** Sorunun nedeni kod, kayıt ve mevcut sınamalarla kanıtlanır.
3. **Sına:** Beklenen davranış önce sınama olarak yazılır ve mevcut durumda
   başarısız olduğu gösterilir.
4. **Düzelt:** Yalnız o davranış için gereken en küçük değişiklik yapılır.
5. **Doğrula:** İlgili sınamalar, bütün sınamalar ve mümkünse gerçek konuşma
   sınaması çalıştırılır.
6. **Ölç:** Sonuç, önceki durumla aynı örnekler üzerinde karşılaştırılır.
7. **Bildir:** Kullanıcıya teknik terim kullanmadan ayrıntılı durum verilir.
8. **Devam et:** Yalnız aşağıdaki sıradaki tamamlanmamış dilime geçilir.

## Faz 1 — Tek ve eksiksiz konuşma yolu

Amaç: Hangi konuşma girişi kullanılırsa kullanılsın kişiselleştirme
özelliklerinin kaybolmaması.

- Profil öğrenme ve unutma ana konuşma yolundan bağımsız hâle getirilecek.
- Kalıcı profil bütün konuşma yollarında modele verilecek.
- Yakın konuşma geçmişi bütün konuşma yollarında korunacak.
- Başak için tek, çelişkisiz kimlik kaynağı kullanılacak.
- Küçük modele verilen geçmiş ve araç yükü azaltılacak.
- Arayüz, Telegram ve sesli yol aynı hazırlık düzenini kullanacak.

Çıkış ölçüsü: Orkestra açıkken bir tercih öğrenilir; uygulama yeniden
başlatıldıktan sonra doğru ve doğal biçimde kullanılır. Yakın konuşma
kaybolmaz. Selamlaşmada araç verilmez; açık bir dosya isteğinde yalnız gereken
araçlar verilir.

## Faz 2 — Yapılandırılmış kişisel profil

- Profil kayıtlarında tür, anahtar, değer, kapsam, kaynak, güven, zaman,
  geçerlilik ve hassasiyet tutulacak.
- Genel ve göreve özel tercihler ayrılacak.
- Yeni açık bilgi, çelişen eski aktif bilgiyi geçersiz kılacak.
- Belirsiz çıkarım doğrulanmadan kalıcı gerçek olmayacak.
- Tek bilgi ve tüm profil için eksiksiz unutma sağlanacak.

Çıkış ölçüsü: öğrenme, düzeltme, çelişki, hassas bilgi ve yeniden başlatmalı
unutma örneklerinin tamamı geçer.

## Faz 3 — Küçük ve ilgili kişisel bağlam

- Her soruya profilin tamamı değil, yalnız ilgili kayıtlar verilecek.
- Yakın konuşma, kişisel profil, eski anılar ve proje notları ayrı tutulacak.
- Küçük model için kısa ve yüksek anlamlı bir bilgi paketi hazırlanacak.
- Anlam araması çalışmadığında yerel kelime araması ve yapılandırılmış profil
  çalışmaya devam edecek.
- Alakasız kişisel bilgi cevaba sızmayacak.

Çıkış ölçüsü: Daha az metinle doğru hatırlama korunur; alakasız kişisel bilgi
kullanımı ölçülebilir biçimde azalır.

## Faz 4 — Göreve göre en az araç

- İstek günlük sohbet, kişisel hatırlama, dosya, internet, görev, proje veya
  uzun inceleme olarak ayrılacak.
- Açık isteklerde araç seçimini kod yapacak.
- Küçük model çoğu istekte sıfır ile iki araç görecek.
- Araç sonucu gerçekleşmeden Başak işlemi yapılmış saymayacak.
- Ağır inceleme yolu yalnız gerçekten ağır işlerde çalışacak.

Çıkış ölçüsü: Küçük model araç örneklerinde doğru aracı seçer; selamlaşmada
araç çağırmaz; yapılmamış işlemi yapılmış gibi bildirmez.

## Faz 5 — Gerçek sonuç karnesi

- Sağlayıcının çalışması ile cevabın doğru olması ayrı ölçülecek.
- Görev türü, kullanılan kişisel kayıtlar, araç sonucu, süre, kullanıcı
  düzeltmesi ve tekrar sorusu kaydedilecek.
- Genel sohbette rastgele sağlayıcı değişimi kaldırılacak.
- Model seçimi görev türündeki gerçek başarıya dayanacak.
- Kullanıcı geri bildirimi yerel ve açıklanabilir sinyal olacak.

Çıkış ölçüsü: Model sırası yalnız hız ve bağlantı başarısına değil, görev
sonucuna göre değişir ve bu karar açıklanabilir.

## Faz 6 — Kontrollü kişisel ajanlık

- Devam eden hedefler ve yarım işler korunacak.
- Sabah özeti, proje takibi ve tekrar eden rutinler mevcut izin düzeni içinde
  çalışacak.
- Başak kullanıcıyı gereksiz yere bölmeden işi mümkün olan son güvenli noktaya
  kadar hazırlayacak.
- Dış etkili ve geri alınamaz işlemler tek işlem için açık onay isteyecek.

Çıkış ölçüsü: Başak yalnız cevap üretmez; izin sınırları içinde yarım işi
hatırlar, sürdürür, sonucu doğrular ve kullanıcıya kısa bir sonuç özeti verir.

## Bitiş ölçüleri

Plan ancak aşağıdakilerin tamamı sağlandığında bitmiş sayılır:

- Aynı oturumda ve yeniden başlatma sonrasında doğru kişisel hatırlama.
- Düzeltmenin eski aktif bilgiyi geçersiz kılması.
- Unutulan bilginin hiçbir hazırlık veya arama yolundan geri gelmemesi.
- Sağlayıcı değişse de tek Başak kimliği ve davranışının korunması.
- Küçük yerel modelde kısa bilgi ve az araçla temel işlerin çalışması.
- Bulut ve anlam araması kapalıyken temel kişisel özelliklerin devam etmesi.
- Kullanıcı onayı olmadan hassas veya dış etkili işlem yapılmaması.
- Bütün otomatik sınamaların geçmesi ve kilitli kullanıcı örneklerinin gerçek
  uygulama yolunda doğrulanması.

## Güncel devir durumu

Son güncelleme: 10 Eylül 2026
Etkin faz: **Faz 1 — devam ediyor**
Sonraki ajan başka bir faza veya özelliğe geçemez.

### Tamamlanan ve kanıtlanan işler

- `chat/personal.py` ile profil öğrenme, unutma, yakın konuşma ve konuşmacı
  bilgisi bütün konuşma yollarının kullanabileceği tek hazırlıkta toplandı.
- Orkestra ana yolu kalıcı profil ile yakın konuşmayı modele taşıyor.
- Bilginin hafıza kapatılıp yeniden açıldıktan sonra tekrar hazırlandığı geçici
  veritabanıyla sınandı.
- Başak/Edercanım kimlik çelişkisi kaldırıldı; tek ad **Başak** oldu.
- Açık kimlik soruları modelden bağımsız cevaplanıyor; "Başak kimdir?" gibi
  araştırma soruları yanlışlıkla yakalanmıyor.
- Küçük model selamlaşmada sıfır araç, açık klasör sorusunda yalnız
  `list_files`, açık dosya okuma sorusunda yalnız `read_file` görüyor.
- Araç yoksa uzun araç açıklaması da modele gönderilmiyor.
- Telegram masaüstüyle aynı dış konuşma kapısına bağlandı.
- Sesli metnin ekrandan normal mesaj kapısına gönderildiği sınandı.
- Önceki kullanıcı değişiklikleri korunarak ilgili sınamalar geçirildi.
- Commit öncesi bütün paket sonucu: **563 geçti, 7 canlı sınama atlandı,
  0 başarısızlık**. Yakın alandaki 56 sınama da ayrıca geçti.

### Canlı yerel model bulguları

Kurulu yerel model: `qwen2.5:7b` (Ollama, yalnız işlemci).

- Temiz, kısa ve araçsız istek ilk yüklemede yaklaşık 18,5 saniye sürdü;
  model bellekteyken basit örnekler yaklaşık 2–4 saniye sürdü.
- Türkçe harfleri komut aktarımında bozan ilk ölçümler geçersiz sayıldı.
  Harfler güvenli gönderilince kişisel "çayı şekersiz içer" bilgisi doğru
  kullanıldı.
- Model açık kimlik talimatına rağmen "Sen kimsin?" sorusunda "Casper" dedi.
  Bu nedenle kimlik cevabı kodun sorumluluğuna alındı.
- Tam Başak konuşma yolunda doğal kişisel cevap henüz canlı olarak kabul
  ölçüsünü geçmedi. **Faz 1 tamamlandı denemez.**

### Bilinen ölçüm

Yalıtılmış ana yol ölçümünde, değişiklikten önce:

- Selamlaşma: 3 mesaj, 1.141 harf, 0 araç.
- Klasör sorusu: 5 mesaj, 1.178 harf, yalnız `list_files`.

Araçsız selamlaşmadan araç açıklaması kaldırıldı. Aynı yalıtılmış ölçümde yeni
yük 3 mesaj, **350 harf, 0 araç** oldu. Önceki 1.141 harfe göre yaklaşık yüzde
69 azalma sağlandı.

### Tek sıradaki adım

1. Gerçek kullanıcı hafızasına yazmadan, tam Başak konuşma yolunu kurulu
   `qwen2.5:7b` ile çalıştır: ilgili geçici tercih doğru kullanılmalı, cevap
   doğal Türkçe olmalı, kimlik karışmamalı ve araç sayısı sıfır olmalı.
2. Bu canlı örnek geçmeden Faz 1'i tamamlandı işaretleme ve Faz 2'ye geçme.

### Korunacak çalışma düzeni

- `ayarlar.json`, `gecmis.json` ve gerçek hafıza içeriği okunmaz/commit edilmez.
- Canlı sınamalar geçici bilgiyle ve gerçek profile yazmadan yapılır.
- Çalışma ağacında bu çalışmadan önce bulunan jüri, ham liste özeti ve ekran
  düzeltmeleri korunmuştur; kayıttan çıkarılmamalıdır.
- Geçici raporlar depo dışında tutulur; yeni plan belgesi açılmaz.
