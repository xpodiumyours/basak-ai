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

## 5. Bugünkü Başak — korunacak referans durum

12 Eylül 2026 itibarıyla `master` referans alınır. Yeni çalışma bu sürümün "idare eder çalışan" davranışını bozmayacak.

Mevcut kodda doğrulananlar:

- `chat/flow.py` küçük modellerde hafıza embedding aramasını kapatıyor.
- Küçük modeller için araç seti daraltılıyor.
- Ana yol yine kimlik + kişilik + araç yönlendirme + ölçüm yönlendirme + biçimlendirme promptlarını birlikte taşıyor.
- Kalıcı profil bloğu varsa modele ayrıca ekleniyor.
- `tools/definitions.py` küçük model için dört temel araç tanımlıyor: `web_search`, `add_task`, `list_files`, `read_file`.
- Başak'ın şu an etkileşimli web tarayıcı aracı yok; `web_search` ve GET tabanlı `sayfa_oku` var.
- Kimlik promptlarında Başak/Edercanım çelişkisi var; bu ayrı bir mevcut hata olarak ölçülecek, araştırma sonucuymuş gibi yorumlanmayacak.

## 6. FAZ 0 — Ölçüm zemini

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

## 7. FAZ 1 — Harness karşılaştırması

Amaç: Open Interpreter'ın ilkesini Başak üzerinde küçük deneylerle sınamak.

En az şu varyantlar aynı görev kümesinde karşılaştırılır:

A. Bugünkü Başak yolu.  
B. Minimum harness: kimlik + görev + yalnız gereken araç.  
C. Model ailesine göre ayrı küçük harness.  
D. Kişisel bilgi yalnız gerektiğinde eklenen harness.

Tek seferde bütün mimari değiştirilmez. Önce deney/benchmark katmanı kurulur.

**FAZ 1 çıkış kapısı:** En az bir ücretsiz/yerel modelde başarı oranı yükselirken sohbet kalitesi ve araç kullanımı gerilemeyecek. Ölçülmeyen varyant ana yola alınmayacak.

## 8. FAZ 2 — Küçük kişisel bağlam

Kişiselleştirme tekrar ancak FAZ 1'den sonra ele alınır.

Kural:

- Başak Casper hakkındaki her şeyi modele vermez.
- Görev için gerçekten gerekli 0-3 kısa kişisel gerçek seçilir.
- Hassas bilgi varsayılan olarak modele verilmez.
- Açık kullanıcı sözü ile çıkarım birbirinden ayrılır.
- Unutma gerçekten silme davranışıyla doğrulanır.

**FAZ 2 çıkış kapısı:** Kişiselleştirilmiş görevler iyileşirken kişiselleştirme gerektirmeyen benchmark sonuçları düşmeyecek.

## 9. FAZ 3 — Web araştırma katmanı

Önce mevcut `web_search` + `sayfa_oku` yetenekleri ölçülür.

Sonra yalnız gerçekten gerekiyorsa Browser Use benzeri etkileşimli browser katmanı denenir.

Yönlendirme kuralı:

- halka açık veri/API/statik sayfa → mevcut hafif yol
- JS uygulaması/giriş/tıklama/form/oturum → browser yolu

**FAZ 3 çıkış kapısı:** Başak bir işletmeyi en az iki bağımsız halka açık kaynaktan araştırıp kanıtlı kısa profil çıkarabilecek; etkileşim gereken sayfada browser aracına geçebilecek; kullanıcı onayı olmadan mesaj/form gönderemeyecek.

## 10. FAZ 4 — Vixrex müşteri bulma pilotu

Gerçek pilot küçük başlar.

1. Tek İstanbul ilçesi.
2. Tek işletme kategorisi.
3. 10 gerçek işletme.
4. Her işletme için kanıtlı uygunluk notu.
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

## 11. FAZ 5 — Tekrarlanabilir para işleri

Vixrex pilotundan sonra aynı mimari başka para akışlarına uygulanabilir:

- freelance/Bionluk fırsat araştırması
- affiliate/partner araştırması
- potansiyel iş ortağı araştırması
- içerik ve teklif hazırlama

Yeni gelir hattı, Vixrex pilotunun ölçüm sistemi çalışmadan açılmaz.

## 12. Güvenlik ve onay kapıları

Başak aşağıdakileri Casper'ın açık onayı olmadan yapamaz:

- mesaj/e-posta/form gönderme
- hesap açma veya hesap ayarı değiştirme
- para harcama/ödeme/satın alma
- sözleşme veya taahhüt oluşturma
- dosya silme veya geri döndürülemez işlem
- üçüncü taraf sisteme kişisel/veri yükleme

Araştırma, taslak hazırlama ve yerel analiz onaysız yapılabilir; dış dünyayı değiştiren adım onay ister.

## 13. Geliştirme disiplini

- `master`a doğrudan yazılmaz.
- Çalışma küçük güvenli dallarda yapılır.
- Her davranış değişikliği önce/sonra aynı görevle ölçülür.
- Büyük refactor yasak; tek hipotez → tek küçük değişiklik → ölçüm.
- Başarısız deney ana yola alınmaz.
- PR/merge yalnız Casper'a kanıt sunulduktan sonra yapılır.
- Planın hedefi, faz sırası veya çıkış ölçüsü Casper'ın açık kararı olmadan değiştirilemez.

## 14. Şu anki tek sıradaki iş

**FAZ 0 + FAZ 1 araştırması.**

Önce Başak'ın bugünkü ana konuşma hattı, prompt yükü, araç seçimi ve kişisel bağlam davranışı ölçülecek. Ardından Open Interpreter harness yaklaşımıyla karşılaştırılacak. Browser Use entegrasyonu henüz yapılmayacak; yalnız mimarisi ve Başak'taki eksik yetenekler çıkarılacak.

Bu kapı tamamlanmadan yeni kişiselleştirme mimarisi ana yola bağlanmaz.
