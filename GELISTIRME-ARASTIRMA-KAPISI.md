# BAŞAK — ZORUNLU GELİŞTİRME ARAŞTIRMA KAPISI

Durum: **KİLİTLİ / BAĞLAYICI GÜVENLİK KAPSAMI**  
Tarih: **12 Eylül 2026**  
Kapsam: `xpodiumyours/basak-ai` için yapılacak bütün kod davranışı değişiklikleri  
Ana plan ilişkisi: Bu belge `ANA-PLAN.md` fazlarının üstünde çalışan zorunlu güvenlik kapısıdır.

Dayanak araştırması:
- `research/2026-09-12-degisiklik-boyutu-ve-guvenli-gelistirme.md`

## 1. Araştırma görev değildir

Araştırma; FAZ, TODO, teslim maddesi veya ürün geliştirme çıktısı olarak sayılmaz.

Araştırmanın amacı:

**Yapılacak değişikliğin gerçekten gerekli olduğunu, bugünkü Başak davranışıyla ilişkisini, uygulanabilir yöntemi, riskleri, kapsam sınırını ve kabul kanıtını değişiklik başlamadan önce doğrulamak.**

Araştırma bitmesi geliştirme bitmesi değildir. Araştırma güvenli geliştirme için zorunlu giriş kapısıdır.

## 2. Kod değişikliğinden önce ilgili araştırma metni zorunludur

Başak'ta davranışı etkileyen her kod değişikliğinden önce o değişiklikle doğrudan ilgili bir araştırma metni bulunmalıdır.

Araştırma metni en az şunları içerir:

1. **Hedef:** Tam olarak hangi davranış değiştirilecek?
2. **Kabul kriteri:** Başarı neyle kanıtlanacak?
3. **Mevcut durum kanıtı:** Bugünkü kod gerçekte ne yapıyor?
4. **Sorun kanıtı:** Değişiklik neden gerekli?
5. **Dış referans gerekiyorsa:** Resmî/birincil kaynak.
6. **Doğrulanan gerçekler.**
7. **Doğrulanamayanlar:** `DOĞRULANAMADI`.
8. **İzin verilen kapsam:** Araştırmanın kanıtladığı alan.
9. **Yasak kapsam:** Aynı işte değiştirilemeyecek alanlar.
10. **Korunacak davranışlar.**
11. **Risk sınıfı.**
12. **Kabul sensörleri:** Test/ölçüm/review/browser/log vb.
13. **Geri alma koşulu:** Hangi durumda değişiklik reddedilecek veya geri alınacak?

Hedef, mevcut durum kanıtı, sorun kanıtı veya kabul kriteri eksikse kod değişikliği başlamaz.

## 3. Tahmin / varsayım yasağı

Kod kararı verirken aşağıdakiler yasaktır:

- `muhtemelen`
- `bence böyle çalışıyordur`
- `genelde modeller böyle yapar`
- `bu değişiklik herhalde düzeltir`
- kanıt bulunmayan mimariyi gerçek kabul etmek
- dokümanda olmayan sağlayıcı/model özelliğini varsaymak
- test edilmemiş başarıyı tamamlanmış saymak
- korelasyonu kök neden ilan etmek

Bir bilgi doğrulanamıyorsa kayıt:

**`DOĞRULANAMADI`**

Doğrulanamayan bilgi değişiklik için gerekliyse işlem durur. Kanıt bulunamazsa o değişiklik yapılmaz.

## 4. Kaynak hiyerarşisi

Mümkün olan en doğrudan kaynak kullanılır:

1. Başak'ın bugünkü kodu ve gerçek çalışma çıktısı.
2. Mevcut test/log/ölçüm.
3. Sağlayıcının/framework'ün resmî dokümanı veya kaynak kodu.
4. Birincil veri / resmî kurum kaynağı.
5. İkincil makale/video/sosyal medya yalnız araştırma sorusu doğurabilir; tek başına kod kararı verdirmez.

## 5. Araştırma → kod geçiş kararı

Her değişiklik için karar yalnız üç sonuçtan biridir:

### `KANITLANDI — KOD DENEYİNE İZİN`

- Sorun doğrulandı.
- Yöntem kaynaklarla uyumlu.
- İzin verilen kapsam açık.
- Korunacak davranışlar tanımlı.
- Risk sınıfı belli.
- Önce/sonra kabul ölçümü belli.

### `KANITLANMADI — KOD YAZMA`

Sorun, neden, çözüm veya kabul kanıtı yeterli değilse kod değişikliği yapılmaz.

### `RİSK / ÇELİŞKİ — DUR`

Kaynaklar çelişiyorsa, mevcut çalışan akışın bozulma riski kabul edilemeyecek seviyedeyse veya doğrulama kurulamadıysa değişiklik yapılmaz; araştırma daraltılır.

## 6. Değişiklik boyutu kuralı — `küçük kod` zorunluluğu yok

Güvenlik kriteri kodun kaç satır olduğu değildir.

Bağlayıcı kavram:

**SINIRLI VE KENDİ İÇİNDE TAM DEĞİŞİKLİK PAKETİ**

Bir değişiklik paketi:

- tek bir doğrulanmış hedefe hizmet eder,
- araştırmanın izin verdiği alanı aşmaz,
- kendi içinde çalışır durumda tamamlanır,
- gerekli test/entegrasyon/ölçüm kanıtını içerir,
- bağımsız review edilebilir,
- başarısız olursa geri alınabilir,
- ilgisiz refactor veya özellik eklemez.

**Sabit satır veya dosya limiti yoktur.**

Karmaşık iş gerekiyorsa sırf küçük görünsün diye yarım yamaya bölünmez. Birden fazla aşamaya ayrılacaksa her aşama:

- çalışır,
- anlaşılır,
- bağımsız doğrulanabilir,
- build/test açısından geçerli

bir ara durum üretmelidir.

İşlevsel bütünlüğü bozacak kadar küçük değişiklik de yasaktır.

## 7. Kapsam büyütme yasağı

Araştırma yeni fikir bulmak için mevcut işi genişletmez.

Örneğin araştırma `streaming → tool-call` için yapılıyorsa aynı değişiklik paketinde kanıtlanmadıkça:

- hafıza mimarisi,
- UI,
- sağlayıcı sırası,
- kişiselleştirme,
- browser,
- yeni framework

değiştirilemez.

**Bir araştırma metni = bir doğrulanmış problem alanı.**

Bu problem alanı bir veya daha fazla çalışır/doğrulanabilir değişiklik paketi gerektirebilir. Paket sayısını line-count değil işlevsel bütünlük ve risk belirler.

## 8. Risk sınıfı zorunludur

Araştırma başlamadan değil, araştırma sonucunda değişiklik şu sınıflardan birine konur:

### Düşük risk

Lokal bug veya tek davranış; sınırlı etki alanı.

### Orta risk

Birden fazla modül, entegrasyon veya ortak sözleşme değişikliği.

### Yüksek risk

Mimari, kalıcı veri, migration, auth, güvenlik, provider routing, izin sistemi, dış dünya etkisi veya geniş kullanıcı davranışı değişikliği.

Risk yükseldikçe sensör sayısı ve doğrulama derinliği artar. Risk, satır sayısından türetilmez.

## 9. AI ile AI geliştirirken zorunlu steering loop

Başak'ı geliştiren AI ajanı aşağıdaki sırayı atlayamaz:

**hedef + kabul kriteri → mevcut kodu doğrula → ilgili araştırma metni → kanıt kararı → kapsam/risk sınıfı → güvenli dal/worktree → sınırlı ve kendi içinde tam değişiklik paketi → değişikliğe uygun test/sensör/review → baseline + kabul kriteriyle karşılaştırma → regresyon varsa geri al/düzelt → sonucu kullanıcıya kanıtla göster → açık onay olmadan main/merge yok**

AI ajanının kendi yazdığı kodu yalnız kendi açıklamasıyla doğru ilan etmesi yasaktır.

## 10. Sensörler değişikliğin riskine göre seçilir

Her değişiklikte bütün sensörler zorunlu değildir. Araştırma, ilgili sensörleri kanıtla seçer.

Olası sensörler:

- ünite testi
- integration/e2e testi
- lint/static analysis
- tip kontrolü
- CodeRabbit/bağımsız code review
- güvenlik kontrolü
- gerçek browser/UI doğrulaması
- tool-call logları
- timeout/fallback logları
- prompt/araç yükü ölçümü
- görev tamamlama oranı
- uydurma/doğrulanmamış cevap oranı
- süre ve tur sayısı
- migration/rollback doğrulaması
- feature flag/canary ölçümü

`Test geçti` tek başına her değişiklik için yeterli kanıt kabul edilmez; sensör değişikliğin gerçek riskini kapsamalıdır.

## 11. Test manipülasyonu yasağı

Bir değişiklik mevcut doğru testi bozarsa:

- testi silmek,
- beklentiyi yalnız yeni kod geçsin diye değiştirmek,
- testi skip etmek,
- daha dar test seçerek hatayı saklamak

yasaktır.

Testin yanlış olduğu iddia ediliyorsa bu ayrıca kanıtlanır. Test değişikliği kendi gerekçesiyle yapılır.

## 12. Regresyon ve geri alma kuralı

Değişiklik:

- korunacak davranışı bozarsa,
- kabul kriterini karşılamazsa,
- yeni kritik hata üretirse,
- ölçümde anlamlı gerileme yaratırsa

`tamamlandı` sayılmaz.

Önce değişikliğin kendisi düzeltilir; gerekirse paket geri alınır. Çalışan Başak, başarısız deney uğruna feda edilmez.

## 13. `Tamamlandı` kelimesinin kanıt şartı

Bir geliştirme yalnız şu durumda `tamamlandı` sayılabilir:

- araştırma kapısı `KANITLANDI` sonucu verdi,
- kod izin verilen kapsam içinde kaldı,
- değişiklik paketi kendi içinde tam ve çalışır,
- ilgili sensörler geçti,
- baseline'a göre kabul edilemez regresyon yok,
- gerekli bağımsız review yapıldı,
- dış dünya etkisi gerekiyorsa kullanıcı onayı alındı,
- sonuç gerçek diff/test/log/ekran/ölçüm ile gösterildi.

Bunlardan biri eksikse durum `tamamlandı` değildir.

## 14. Araştırma metni isimlendirme kuralı

Kod davranışı değişiklikleri için araştırma kaydı:

`research/<tarih>-<kisa-konu>.md`

Örnek:

`research/2026-09-12-streaming-tool-routing.md`

Genel araştırma belgeleri belirli kod değişikliği için ilgili araştırma metninin yerini tutmaz.

## 15. Değişmez kural

**Araştırma bir görev değildir. Araştırma, Başak gelişiminin güvenli kapsamıdır.**

**İlgili araştırma metni olmadan davranış değiştiren kod yazılmaz.**

**Tahmin/varsayım yapılmaz. Doğrulanamayan bilgi `DOĞRULANAMADI` kalır.**

**Güvenli değişiklik = küçük kod değildir. Güvenli değişiklik = sınırı belli, kendi içinde tam, bağımsız doğrulanabilir ve geri alınabilir değişiklik paketidir.**
