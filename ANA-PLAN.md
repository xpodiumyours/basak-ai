# BAŞAK — KİLİTLİ ANA PLAN

Durum: **KİLİTLİ**  
Kilit tarihi: **12 Eylül 2026**  
Çalışma alanı: **yalnız `xpodiumyours/basak-ai`**  
Çalışma dalı: **`plan/basak-para-kazandiran-asistan-20260912`**

## 1. Değiştirilemez ana hedef

Başak yalnız sohbet eden veya yalnız kişisel bilgi hatırlayan bir asistan olmayacak.

Başak'ın ana işi şu zinciri güvenilir biçimde yürütmektir:

**Casper'ı yeterince tanı → para getirebilecek fırsatı bul → araştır ve doğrula → işi hazırla → riskli/dış dünyaya etkili adımda Casper'dan onay al → işi tamamla → sonucu ölç.**

Kişiselleştirme bu zinciri güçlendirdiği kadar vardır. Küçük/ücretsiz modellerin araç kullanma, araştırma, akıl yürütme veya doğal konuşma becerisini düşüren kişiselleştirme katmanı kabul edilmez.

## 2. İlk para kazanma motoru — Vixrex müşteri bulma

İlk somut gelir akışı Vixrex için gerçek müşteri bulmadır.

Başak:

1. İstanbul'daki uygun işletmeleri araştırır.
2. Her işletme için yalnız doğrulanabilir halka açık bilgileri toplar.
3. Vixrex vitrininin gerçekten fayda sağlayabileceği işletmeleri ayırır.
4. İşletmeye özel kısa gerekçe ve iletişim taslağı hazırlar.
5. Mesaj gönderme, form doldurma, hesap kullanma veya dış dünyaya etkili işlem öncesinde Casper'dan açık onay ister.
6. Onaydan sonra izin verilen işlemi yapar.
7. Sonucu kaydeder: ulaşıldı mı, cevap geldi mi, görüşme oldu mu, vitrin kiralandı mı.
8. Hangi işletme tiplerinin dönüşüm ürettiğini ölçerek sonraki araştırma sırasını geliştirir.

Başarı yalnız "işletme listesi bulmak" değildir. Başarı ölçüsü **gerçek temas, gerçek cevap, gerçek görüşme ve mümkünse gelir**dir.

## 3. Kilitli teknik ilke — modeli katmanlarla boğma

Dünkü arıza tekrar edilmeyecek.

Başak'a yeni hafıza, profil, planlama veya kontrol katmanı eklenmeden önce şu soru cevaplanır:

> Bu katman, aynı ücretsiz/yerel modelin mevcut çalışan davranışını iyileştiriyor mu; yoksa aracını, muhakemesini ve doğal cevabını kötüleştiriyor mu?

Kanıt yoksa katman ana yola bağlanmaz.

### Yasaklar

- Tüm kişisel profili her mesaja yığmak yasak.
- Her modele aynı büyük system prompt + aynı araç seti + aynı mesaj biçimini zorlamak yasak.
- "Daha çok bağlam = daha iyi kişiselleştirme" varsayımı yasak.
- Küçük modelin başarısız olduğu görevi daha fazla talimat ekleyerek gizlemek yasak.
- Araştırma kanıtı olmadan yeni framework/ajan katmanı kurmak yasak.
- Mevcut çalışan Başak yolunu tek seferde büyük refactor ile değiştirmek yasak.

## 4. Öğrenilecek referans mimariler

### 4.1 Open Interpreter

Resmî kaynaklardan doğrulanan ana ders:

Open Interpreter; provider, model ve **harness** katmanlarını ayrı tutuyor. Harness; modelin gördüğü ajan promptunu, araçları ve mesaj davranışını belirliyor. Kimi, Qwen, DeepSeek, GLM gibi aileler için aynı genel ajan kabuğunu dayatmak yerine modele uygun harness seçilebiliyor.

Başak için araştırılacak soru:

**"Ücretsiz/yerel model hangi prompt, araç sayısı, araç şeması, geçmiş uzunluğu ve mesaj biçiminde en iyi çalışıyor?"**

Open Interpreter Başak'a doğrudan kopyalanmayacak. Önce mimari ilke ölçülecek.

Kaynaklar:
- https://www.openinterpreter.com/docs/terminal/providers
- https://github.com/openinterpreter/openinterpreter
- https://www.openinterpreter.com/blog/open-interpreter

### 4.2 Browser Use

Resmî kaynaklardan doğrulanan ana ders:

Browser Use basit halka açık veri okumayla gerçek tarayıcı etkileşimini ayırıyor. Düz HTTP/fetch yeterliyse tarayıcı kullanılmıyor; tıklama, yazma, giriş, JavaScript ile çizilen ekran veya oturum gerekiyorsa gerçek browser katmanına çıkılıyor. Kalıcı browser oturumu ve CDP tabanlı araçlar kullanılabiliyor.

Başak için araştırılacak soru:

**"Web araştırması ne zaman mevcut `web_search`/`sayfa_oku` ile yapılmalı, ne zaman etkileşimli browser gerekir?"**

Kaynaklar:
- https://github.com/browser-use/browser-use
- https://github.com/browser-use/browser-use/blob/main/skills/browser-use/SKILL.md
- https://github.com/browser-use/browser-use/blob/main/browser_use/skill_cli/README.md

## 5. KİLİTLİ ARAŞTIRMA SONUCU 1 — küçük/ücretsiz modeli boğmadan görev yapan Başak

Bu bölüm ilk kapsamlı araştırmanın planı değiştiren sonucudur ve bağlayıcıdır.

### 5.1 Araştırmanın yön değişikliği

Eski yön:

**"Başak daha fazla kişisel bilgi, hafıza ve kontrol katmanı taşısın."**

Yeni kilitli yön:

**"Başak, küçük/ücretsiz modelin görev yapma ve araç kullanma becerisini bozmadan kişiselleşsin."**

Kişiselleştirme artık ana ürün değildir; para kazandıran görev zincirini güçlendiren yardımcı katmandır.

### 5.2 Open Interpreter'dan alınan ilke

Aynı büyük ajan kabuğu bütün modellere zorlanmayacak.

Başak'ta araştırılacak ve ölçülecek ayrım:

- sağlayıcı
- gerçek model
- model ailesi
- modelin gördüğü prompt/harness
- modelin gördüğü araç sayısı ve araç şeması
- geçmiş uzunluğu
- kişisel bağlam miktarı

Qwen, GLM, DeepSeek, Kimi veya başka ücretsiz/yerel modellerin aynı harness ile en iyi çalıştığı varsayılmayacak.

### 5.3 Başak kodunda doğrulanan kritik aday sorun

Mevcut ana konuşma akışı gerçek tool-call yoluna geçmeden önce araçsız streaming cevap deniyor.

Doğrulanan mevcut davranış:

- `chat/flow.py` önce `brain.cevapla_yayin(...)` çağırıyor.
- `brain/brain.py::cevapla_yayin` sağlayıcı seçimini `tools=False` ile yapıyor.
- `brain/yayin.py` streaming isteğinde gerçek tool şemalarını modele vermiyor.
- Model düz metin cevap üretirse cevap kaydedilip akış sonlanabiliyor.
- Böylece aşağıdaki gerçek `brain.cevapla(... tools=aktif_toollar)` yoluna hiç inilmemesi mümkün.

Bu henüz kök neden ilan edilmez; **A/B ölçüm adayıdır.**

Zorunlu deney:

- aynı model
- aynı görev
- aynı prompt
- mevcut araçsız-streaming yolu
- streaming atlanıp doğrudan araçlı yol

Ölçülecek: doğru araç çağrısı, düz metinle kaçış, doğru sonuç, süre ve görevin tamamlanması.

### 5.4 Kişiselleştirme için yeni kilit

Başak tüm profili her mesaja taşımayacak.

Yeni hedef:

- görev kişiselleştirme gerektirmiyorsa **0 kişisel gerçek**
- gerekiyorsa **en fazla 0-3 kısa ve ilgili kişisel gerçek**
- hassas bilgi varsayılan olarak dış modele verilmez
- kişisel bağlam, araç veya görev performansını düşürüyorsa ana yola alınmaz

### 5.5 Araç yükü ilkesi

Sorun yalnız toplam araç sayısı değildir; Başak zaten küçük modellerde araç setini daraltıyor.

Buna rağmen şu parçalar birlikte ölçülecek:

- prompt büyüklüğü
- araç şeması büyüklüğü
- araç sayısı
- araçların modele hangi turda verildiği
- geçmiş uzunluğu
- kişisel profil yükü
- streaming / tool-call sırası

### 5.6 Araştırma 1'in kilitli sonucu

Başak'ın gelişim yönü artık:

**"Kişiselleştirilmiş Başak" değil → "küçük/ücretsiz modelleri boğmadan gerçek görev yapan ve gerektiği kadar kişiselleşen Başak"tır.**

Bu sonuç değiştirilmeden yeni kişiselleştirme mimarisi ana yola bağlanamaz.

## 6. KİLİTLİ ARAŞTIRMA SONUCU 2 — Vixrex müşteri istihbarat motoru

Bu bölüm ikinci kapsamlı araştırmanın planı değiştiren sonucudur ve bağlayıcıdır.

### 6.1 Araştırmanın yön değişikliği

Eski yön:

**"İstanbul'da işletme bul → kişisel mesaj hazırla → iletişime geç."**

Yeni kilitli yön:

**"Aday işletmeyi güvenli/veriye uygun kaynaklardan bul → kanıt topla → deterministik uygunluk puanı hesapla → kısa işletme dosyası çıkar → yalnız iyi aday için kişisel iletişim hazırla → Casper onayı → temas → ticari sonucu ölç."**

Başak yalnız lead listesi üreten araç olmayacak; **Vixrex müşteri istihbarat ve satış hazırlık sistemi** olacak.

### 6.2 Veri kaynaklarının kilitli rolleri

#### OpenStreetMap / açık coğrafi veri

Rolü: **ana aday keşif kaynaklarından biri.**

Amaç:

- İstanbul
- ilçe
- işletme kategorisi
- fiziksel işletme

filtreleriyle ilk aday havuzunu üretmek.

Açık veri toplu kullanılacaksa ilgili lisans/atıf şartlarına uyulur. Ücretsiz kamu Nominatim servisi sistematik toplu POI indirme motoru olarak kullanılmaz; gerektiğinde uygun açık veri dosyası/uygun altyapı kullanılır.

#### ETBİS

Rolü: **resmî ikinci segment / doğrulama kaynağı.**

Özellikle:

- İstanbul
- ilçe
- sektör
- e-ticaret yapan işletme

ayrımı için kullanılır.

ETBİS'teki işletme ile dijitalleşmesi zayıf fiziksel esnaf aynı satış mesajını almaz.

#### İşletmenin kendi sitesi

Rolü: **ana ihtiyaç doğrulama kaynağı.**

Kontroller:

- site var mı
- ürünler görünür mü
- fiyat var mı
- ürün/katalog sayfası var mı
- iletişim kanalı var mı
- fiziksel adres var mı
- mobil deneyim ölçülebiliyor mu
- site performansı ölçülebiliyor mu

Başak "site kötü" gibi kanıtsız hüküm vermez; yalnız ölçülen veya görülen eksikleri yazar.

#### PageSpeed / teknik web ölçümü

Rolü: **objektif satış sinyali.**

Başak yalnız ölçülebilir sonuçları kullanır; performans/SEO/mobil durum kanıtsız tahmin edilmez.

#### Google Maps / Places

Rolü: **ana kalıcı CRM kaynağı değil, tekil canlı doğrulama yardımcısı.**

Google içeriği topluca kendi kalıcı lead veritabanımıza dönüştürülmeyecek. Gerekli tekil doğrulamada işletmenin varlığı, konumu veya güncel halka açık bilgisi kontrol edilebilir.

#### Instagram

Rolü: **ana scraping/lead veritabanı değil, yardımcı dijital aktivite sinyali.**

Otomatik toplu scraping ve otomatik soğuk DM ana plana girmez.

#### WhatsApp / e-posta / form

Rolü: **keşif değil, onay sonrası iletişim.**

Başak otomatik toplu soğuk gönderim motoru olmayacak. İletişim kanalı kullanılırken ilgili platform kuralları, ticari ileti mevzuatı, İYS/KVKK yükümlülükleri ve ret hakkı gözetilir.

### 6.3 Deterministik Vixrex Uygunluk Puanı

LLM tek başına "bu işletme uygundur" kararı vermez.

Başak kanıtları çıkarır; puanı kural/kod hesaplar.

İlk araştırma için örnek sinyaller:

- İstanbul'da doğrulanmış fiziksel işletme
- görsel olarak sergilenebilir ürün
- düzenli ürün/katalog ihtiyacı
- kendi sitesi yok
- sitesi var ama ürün vitrini zayıf
- kamuya açık işletme iletişim kanalı
- WhatsApp/telefon üzerinden müşteri kabulü
- doğrulanmış dijital aktivite
- güçlü güncel tam e-ticaret sitesi varsa negatif sinyal
- büyük zincir/kurumsal yapı negatif sinyal
- Vixrex'in mevcut özelliklerinin çözemediği sektör negatif sinyal

Puanlar pilot ölçüm sonucuna göre kalibre edilir; ilk değerler hakikat kabul edilmez.

Başak her aday için neden seçildiğini ve neden elendiğini açıklayabilmelidir.

### 6.4 Müşteri istihbarat zinciri

Kilitli zincir:

**Aday kaynağı → kanıt toplama → uygunluk puanı → kısa işletme dosyası → iletişim açısı → Casper onayı → iletişim → cevap/görüşme/satış → sonuç ölçümü.**

Örnek nihai aday kartı:

- işletme adı
- ilçe/kategori
- kullanılan kaynaklar
- doğrulanan fiziksel işletme durumu
- ürün tipi
- mevcut web vitrini durumu
- iletişim kanalı
- Vixrex uygunluk puanı
- uygunluk nedenleri
- risk/eksik kanıt
- önerilen kişisel temas açısı
- **ONAYLA / GEÇ** kararı

### 6.5 Modelin rolü küçülür, sistemin güvenilirliği artar

Kod/kurallar:

- adayları toplar
- filtreler
- kanıtları sınıflar
- puanı hesaplar
- sonuçları takip eder

Model:

- kanıtları kısa ve doğal Türkçe özetler
- işletmeye özel iletişim taslağı üretir
- kullanıcıyla doğal konuşur

Model, CRM mantığının veya uygunluk kararının tek hakemi değildir.

### 6.6 Kanal çeşitliliği

Vixrex müşteri kazanımı yalnız soğuk dijital iletişim değildir.

Araştırılacak kanallar:

- açık veri tabanlı yerel işletme keşfi
- ETBİS tabanlı e-ticaret işletmesi keşfi
- işletmenin kendi sitesi üzerinden ihtiyaç tespiti
- fiziksel saha için rota + işletme özeti
- mevcut Vixrex sahibinin yakın/tamamlayıcı esnafı davet etmesi
- Vixrex vitrin hediye/davet modeli

Her kanal aynı metriklerle ölçülür: temas, cevap, görüşme, vitrin oluşturma ve gelir.

### 6.7 Pilot kapsamı

Kodlamaya geçmeden veya ölçeği büyütmeden önce masa başı pilot yapılır.

İlk araştırma pilotu:

- İstanbul
- 1 veya birkaç karşılaştırılabilir ilçe/kategori
- toplam en az 20 gerçek işletme üzerinde masa başı değerlendirme
- kaynak erişilebilirliği
- kanıt kalitesi
- uygunluk puanının doğru ayırma gücü
- kişiselleştirilmiş iletişim açısının gerçekten işletmeye özel olup olmadığı

Bu pilot, daha sonra yapılacak 10 işletmelik gerçek iletişim pilotunun hangi sektör/ilçede yapılacağını seçmek için kullanılır.

### 6.8 Araştırma 2'nin kilitli sonucu

Başak'ın Vixrex yönü artık:

**"İşletme bulup mesaj atan Başak" değil → "kanıtlı müşteri istihbaratı çıkaran, uygunluğu kuralla ölçen, satışa hazırlayan ve dış iletişimi insan onayına bırakan Başak"tır.**

Bu sonuç değiştirilmeden toplu mesaj, scraping veya otomatik satış sistemi ana yola alınamaz.

## 7. Bugünkü Başak — korunacak referans durum

12 Eylül 2026 itibarıyla `master` referans alınır. Yeni çalışma bu sürümün "idare eder çalışan" davranışını bozmayacak.

Mevcut kodda doğrulananlar:

- `chat/flow.py` küçük modellerde hafıza embedding aramasını kapatıyor.
- Küçük modeller için araç seti daraltılıyor.
- Ana yol yine kimlik + kişilik + araç yönlendirme + ölçüm yönlendirme + biçimlendirme promptlarını birlikte taşıyor.
- Kalıcı profil bloğu varsa modele ayrıca ekleniyor.
- `tools/definitions.py` küçük model için dört temel araç tanımlıyor: `web_search`, `add_task`, `list_files`, `read_file`.
- Başak'ın şu an etkileşimli web tarayıcı aracı yok; `web_search` ve GET tabanlı `sayfa_oku` var.
- Kimlik promptlarında Başak/Edercanım çelişkisi var; bu ayrı bir mevcut hata olarak ölçülecek, araştırma sonucuymuş gibi yorumlanmayacak.

## 8. FAZ 0 — Ölçüm zemini

Kod değiştirmeden önce bugünkü davranış ölçülecek.

Aynı görev kümesi her sağlayıcı/modelde ayrı çalıştırılır:

1. Normal sohbet.
2. Casper hakkında gerekli tek kişisel bilgiyi kullanma.
3. Alakasız kişisel bilgiyi kullanmama.
4. Dosya bulma ve okuma.
5. Web araması ve kaynak doğrulama.
6. Bir işletmeyi araştırma.
7. Araç gerektirmeyen soruda araç çağırmama.
8. Araç gereken soruda doğru aracı seçme.
9. Çok adımlı işi tamamlayabilme.
10. Hata/timeout sonrası sağlam sağlayıcıya geçebilme.

Her testte kaydedilecek:

- doğru sonuç / yanlış sonuç
- doğru araç / yanlış araç / araç yok
- toplam tur sayısı
- modele gönderilen prompt büyüklüğü
- gönderilen araç sayısı
- cevap süresi
- uydurma olup olmadığı
- görevin tamamlanıp tamamlanmadığı

**FAZ 0 çıkış kapısı:** Bugünkü Başak'ın gerçek baz çizgisi sayıyla görülmeden yeni kişiselleştirme veya browser katmanı eklenmez.

## 9. FAZ 1 — Harness karşılaştırması

Amaç: Open Interpreter'ın ilkesini Başak üzerinde küçük deneylerle sınamak.

En az şu varyantlar aynı görev kümesinde karşılaştırılır:

A. Bugünkü Başak yolu.  
B. Minimum harness: kimlik + görev + yalnız gereken araç.  
C. Model ailesine göre ayrı küçük harness.  
D. Kişisel bilgi yalnız gerektiğinde eklenen harness.

Tek seferde bütün mimari değiştirilmez. Önce deney/benchmark katmanı kurulur.

**FAZ 1 çıkış kapısı:** En az bir ücretsiz/yerel modelde başarı oranı yükselirken sohbet kalitesi ve araç kullanımı gerilemeyecek. Ölçülmeyen varyant ana yola alınmayacak.

## 10. FAZ 2 — Küçük kişisel bağlam

Kişiselleştirme tekrar ancak FAZ 1'den sonra ele alınır.

Kural:

- Başak Casper hakkındaki her şeyi modele vermez.
- Görev için gerçekten gerekli 0-3 kısa kişisel gerçek seçilir.
- Hassas bilgi varsayılan olarak modele verilmez.
- Açık kullanıcı sözü ile çıkarım birbirinden ayrılır.
- Unutma gerçekten silme davranışıyla doğrulanır.

**FAZ 2 çıkış kapısı:** Kişiselleştirilmiş görevler iyileşirken kişiselleştirme gerektirmeyen benchmark sonuçları düşmeyecek.

## 11. FAZ 3 — Web araştırma ve müşteri istihbarat katmanı

Önce mevcut `web_search` + `sayfa_oku` yetenekleri ölçülür.

Sonra müşteri istihbaratı için veri kaynaklarının rolleri ayrı tutulur:

- açık/coğrafi aday kaynağı → aday keşfi
- ETBİS → resmî e-ticaret segmenti
- işletmenin kendi sitesi → ana ihtiyaç doğrulama
- PageSpeed/teknik ölçüm → objektif web sinyali
- Google Maps/Places → gerektiğinde tekil canlı doğrulama
- Instagram → yardımcı dijital aktivite sinyali

Sonra yalnız gerçekten gerekiyorsa Browser Use benzeri etkileşimli browser katmanı denenir.

Yönlendirme kuralı:

- halka açık veri/API/statik sayfa → mevcut hafif yol
- JS uygulaması/giriş/tıklama/form/oturum → browser yolu

**FAZ 3 çıkış kapısı:** Başak bir işletmeyi en az iki bağımsız uygun halka açık kaynaktan araştırıp kanıtlı kısa profil çıkarabilecek; deterministik uygunluk puanına girdi sağlayabilecek; etkileşim gereken sayfada browser aracına geçebilecek; kullanıcı onayı olmadan mesaj/form gönderemeyecek.

## 12. FAZ 4 — Vixrex müşteri bulma pilotu

FAZ 4 iki aşamalıdır.

### 12.1 Masa başı doğrulama pilotu

- en az 20 gerçek İstanbul işletmesi
- birden fazla kaynak türünün erişilebilirliği
- uygunluk sinyallerinin kanıt kalitesi
- puanlama sisteminin ayırma gücü
- hangi ilçe/kategorinin gerçek iletişim pilotuna uygun olduğunun seçimi

### 12.2 Gerçek iletişim pilotu

1. Seçilen tek İstanbul ilçesi.
2. Seçilen tek işletme kategorisi.
3. 10 yüksek uygunluklu gerçek işletme.
4. Her işletme için kanıtlı uygunluk notu ve puanı.
5. Uygun bulunanlar için kişiye özel iletişim taslağı.
6. Dış iletişim yalnız Casper onayıyla.
7. Sonuç kaydı.

Ölçüler:

- araştırılan işletme
- uygun bulunan işletme
- onaylanan iletişim
- gönderilen iletişim
- cevap
- görüşme
- vitrin kiralama/satın alma
- gelir

**FAZ 4 çıkış kapısı:** Başak'ın ürettiği zincir gerçek dünyada en az bir ölçülebilir ticari sonuç üretmeli veya hangi adımın dönüşümü engellediğini kanıtla göstermeli.

## 13. FAZ 5 — Tekrarlanabilir para işleri

Vixrex pilotundan sonra aynı mimari başka para akışlarına uygulanabilir:

- freelance/Bionluk fırsat araştırması
- affiliate/partner araştırması
- potansiyel iş ortağı araştırması
- içerik ve teklif hazırlama

Yeni gelir hattı, Vixrex pilotunun ölçüm sistemi çalışmadan açılmaz.

## 14. Güvenlik ve onay kapıları

Başak aşağıdakileri Casper'ın açık onayı olmadan yapamaz:

- mesaj/e-posta/form gönderme
- hesap açma veya hesap ayarı değiştirme
- para harcama/ödeme/satın alma
- sözleşme veya taahhüt oluşturma
- dosya silme veya geri döndürülemez işlem
- üçüncü taraf sisteme kişisel/veri yükleme

Araştırma, taslak hazırlama ve yerel analiz onaysız yapılabilir; dış dünyayı değiştiren adım onay ister.

Ticari iletişim kanalları kullanılırken platform kuralları, ret hakkı ve uygulanabilir İYS/KVKK/ticari elektronik ileti yükümlülükleri ayrıca kontrol edilir.

## 15. Geliştirme disiplini

- `master`a doğrudan yazılmaz.
- Çalışma küçük güvenli dallarda yapılır.
- Her davranış değişikliği önce/sonra aynı görevle ölçülür.
- Büyük refactor yasak; tek hipotez → tek küçük değişiklik → ölçüm.
- Başarısız deney ana yola alınmaz.
- PR/merge yalnız Casper'a kanıt sunulduktan sonra yapılır.
- Planın hedefi, faz sırası, kilitli araştırma sonuçları veya çıkış ölçüsü Casper'ın açık kararı olmadan değiştirilemez.

## 16. Şu anki tek sıradaki iş

**İlerleme kodlaması başlamadan önce araştırma ve ölçüm zemini tamamlanacak.**

Sıra:

1. Başak'ın bugünkü ana konuşma hattı, prompt yükü, araç seçimi ve kişisel bağlam davranışını ölçmek.
2. Open Interpreter harness yaklaşımını aynı görevlerde karşılaştırmak.
3. Vixrex müşteri istihbaratı için OSM/açık veri, ETBİS, işletme sitesi, teknik web ölçümü ve yardımcı doğrulama kanallarını gerçek işletmeler üzerinde sınamak.
4. En az 20 gerçek İstanbul işletmesiyle masa başı müşteri-istihbarat pilotu yapmak.
5. Ancak bu kanıtlar tamamlandıktan sonra yeni kişiselleştirme, browser entegrasyonu veya gerçek satış pilotu için kod değişikliği yapmak.

Bu kapı tamamlanmadan yeni kişiselleştirme mimarisi, browser otomasyonu, toplu lead sistemi veya otomatik dış iletişim ana yola bağlanmaz.
