# BAŞAK — ZORUNLU GELİŞTİRME ARAŞTIRMA KAPISI

Durum: **KİLİTLİ / BAĞLAYICI GÜVENLİK KAPSAMI**  
Tarih: **12 Eylül 2026**  
Kapsam: `xpodiumyours/basak-ai` için yapılacak bütün kod davranışı değişiklikleri  
Ana plan ilişkisi: Bu belge `ANA-PLAN.md` fazlarının üstünde çalışan zorunlu güvenlik kapısıdır.

## 1. Araştırma görev değildir

Araştırma; FAZ, TODO, teslim maddesi veya ürün geliştirme çıktısı olarak sayılmaz.

Araştırmanın görevi şudur:

**Yapılacak kod değişikliğinin gerçekten gerekli olduğunu, mevcut Başak davranışıyla uyumunu, uygulanabilir yöntemini, risklerini ve kabul sınırlarını değişiklik başlamadan önce kanıtlamak.**

Bu nedenle araştırma tamamlamak "geliştirme tamamlandı" anlamına gelmez. Araştırma yalnız güvenli geliştirme için zorunlu giriş kapısıdır.

## 2. Kod değişikliğinden önce araştırma metni zorunludur

Başak'ta davranışı etkileyen her kod değişikliğinden ÖNCE o değişiklikle doğrudan ilgili bir araştırma metni bulunmak zorundadır.

Araştırma metni en az şunları içerir:

1. **Hedef:** Tam olarak hangi davranış değiştirilecek?
2. **Mevcut durum kanıtı:** Bugünkü çalışan kod gerçekte ne yapıyor? Dosya/fonksiyon/test/ölçüm kanıtı.
3. **Sorun kanıtı:** Değişiklik neden gerekli? Gözlem, test, log, ölçüm veya doğrulanmış kullanıcı akışı.
4. **Dış referans gerekiyorsa:** Resmî doküman, model sağlayıcı dokümanı, framework dokümanı veya birincil kaynak.
5. **Doğrulanan gerçekler:** Kanıtla desteklenen maddeler.
6. **Doğrulanamayanlar:** Açıkça `doğrulanamadı` olarak yazılır.
7. **İzin verilen değişiklik:** Araştırmanın kanıtladığı en küçük kod kapsamı.
8. **Yasak kapsam:** Bu araştırmanın kanıtlamadığı ve aynı işte değiştirilemeyecek alanlar.
9. **Korunacak davranışlar:** Çalışan Başak'ta bozulmaması gereken özellikler.
10. **Kabul kanıtı:** Değişiklikten sonra hangi test/ölçüm önceki durumla karşılaştırılacak?

Bu maddelerden hedef, mevcut durum kanıtı, sorun kanıtı veya kabul kanıtı eksikse kod değişikliği başlamaz.

## 3. Tahmin / varsayım yasağı

Araştırmadan sonra kod kararı verirken aşağıdakiler yasaktır:

- "muhtemelen"
- "bence böyle çalışıyordur"
- "genelde modeller böyle yapar"
- "bu değişiklik herhalde düzeltir"
- kanıt bulunmayan mimariyi gerçek kabul etmek
- dokümanda olmayan sağlayıcı/model özelliğini varsaymak
- test edilmemiş başarıyı tamamlanmış saymak
- bir sorunun kök nedenini yalnız korelasyonla ilan etmek

Bir bilgi doğrulanamıyorsa tek doğru kayıt:

**`DOĞRULANAMADI`**

Doğrulanamayan bilgi kod değişikliği için gerekliyse işlem durur. Eksik bilgi araştırılır; bulunamazsa o değişiklik yapılmaz.

## 4. Kaynak hiyerarşisi

Araştırmada mümkün olan en doğrudan kaynak kullanılır:

1. **Başak'ın bugünkü kodu ve gerçek çalışma çıktısı** — mevcut davranışın hakikati.
2. **Mevcut test/log/ölçüm** — davranışın ölçülebilir kanıtı.
3. **Sağlayıcının/framework'ün resmî dokümanı veya kaynak kodu** — dış teknik davranış.
4. **Birincil veri / resmî kurum kaynağı** — iş, mevzuat veya platform sınırı.
5. İkincil makale/video/sosyal medya yalnız araştırma yönü bulmak için kullanılabilir; tek başına kod kararı verdirmez.

Sosyal medya paylaşımı, YouTube videosu veya üçüncü taraf yorum araştırma sorusu doğurabilir; **kanıt yerine geçmez.**

## 5. Araştırma → kod geçiş kapısı

Her değişiklik için karar yalnız üç sonuçtan biridir:

### `KANITLANDI — KOD DENEYİNE İZİN`

- Sorun doğrulandı.
- Değişiklik yöntemi kaynaklarla uyumlu.
- Kapsam küçük ve açık.
- Korunacak davranışlar tanımlı.
- Önce/sonra kabul ölçümü belli.

Yalnız bu durumda güvenli deney dalında kod değişikliği yapılabilir.

### `KANITLANMADI — KOD YAZMA`

Sorun, neden veya çözüm yeterli kanıt taşımıyorsa kod değişikliği yapılmaz.

### `RİSK / ÇELİŞKİ — DUR`

Kaynaklar çelişiyorsa, mevcut çalışan akışın bozulma riski yüksekse veya kabul ölçümü kurulamadıysa değişiklik yapılmaz; araştırma daraltılır.

## 6. Araştırmanın kapsam büyütmesi yasaktır

Araştırma yeni fikir bulmak için mevcut işi genişletmez.

Örnek:

Araştırma `streaming → tool-call` davranışı için yapılıyorsa aynı kod değişikliğinde:

- hafıza mimarisi,
- UI,
- sağlayıcı sırası,
- kişiselleştirme,
- browser,
- yeni framework

değiştirilemez; bunların her biri kendi araştırma kapısını gerektirir.

**Bir araştırma metni = bir doğrulanmış problem alanı = bir küçük deney kapsamı.**

## 7. AI ile AI geliştirirken zorunlu steering loop

Başak'ı geliştiren AI ajanı aşağıdaki sırayı atlayamaz:

**hedefi oku → mevcut kodu doğrula → ilgili araştırmayı yap/yaz → kanıt kararını ver → güvenli dal → en küçük kod değişikliği → test/sensör/review → önce/sonra karşılaştır → regresyon varsa geri al → sonucu kullanıcıya göster → açık onay olmadan main/merge yok**

AI ajanının kendi yazdığı kodu yalnız kendi açıklamasıyla doğru ilan etmesi yasaktır.

## 8. Zorunlu sensörler değişikliğe göre seçilir

Her değişiklikte bütün sensörleri çalıştırmak zorunlu değildir; ilgili olanlar araştırmada seçilir.

Olası sensörler:

- ünite/integration test
- lint/static analysis
- tip kontrolü
- CodeRabbit/code review
- güvenlik kontrolü
- gerçek browser/UI doğrulaması
- tool-call logları
- timeout/fallback logları
- prompt/araç yükü ölçümü
- görev tamamlama oranı
- uydurma/doğrulanmamış cevap oranı
- süre ve tur sayısı

Sensör seçimi de tahmine göre değil, değişikliğin riskine göre araştırma metninde gerekçelendirilir.

## 9. Test manipülasyonu yasağı

Bir kod değişikliği mevcut doğru testi bozarsa:

- testi silmek,
- beklentiyi sırf yeni kod geçsin diye değiştirmek,
- testi atlamak/skip etmek,
- daha dar test seçerek hatayı saklamak

yasaktır.

Testin kendisinin yanlış olduğu iddia ediliyorsa bunun için ayrıca kanıt gerekir. Önce test sözleşmesinin yanlış olduğu doğrulanır, sonra test değişikliği ayrı gerekçeyle yapılır.

## 10. Tamamlandı kelimesinin kanıt şartı

Bir geliştirme yalnız şu durumda `tamamlandı` sayılabilir:

- araştırma kapısı `KANITLANDI` sonucu verdi,
- kod yalnız izin verilen kapsamda değişti,
- ilgili test/ölçüm geçti,
- önceki çalışan davranışta regresyon görülmedi,
- dış dünyayı etkileyen işlem gerekiyorsa kullanıcı onayı alındı,
- sonuç gerçek çıktı/diff/test/log ile gösterildi.

Bunlardan biri eksikse durum `tamamlandı` değildir.

## 11. Araştırma metni isimlendirme kuralı

Kod değişikliği deneyleri için araştırma kaydı şu biçimde tutulur:

`research/<tarih>-<kisa-konu>.md`

Örnek:

`research/2026-09-12-streaming-tool-routing.md`

Mevcut üst seviye araştırma belgeleri (`ARASTIRMA.md`, `FAZ1-ARASTIRMA.md`, `ARASTIRMA-3-AI-ILE-AI-GELISTIRME-HARNESS.md`) genel ilkeleri destekler; fakat belirli kod değişikliği için **ilgili kısa araştırma metninin yerini tutmaz.**

## 12. Değişmez kural

**Araştırma bir görev değildir. Araştırma, Başak gelişiminin güvenli kapsamıdır.**

**İlgili araştırma metni olmadan davranış değiştiren kod yazılmaz.**

**Araştırma tamamlandıktan sonra da tahmin/varsayım yapılmaz; yalnız doğrulanmış gerçeklerle hareket edilir.**

**Doğrulanamayan bilgi `DOĞRULANAMADI` olarak kalır ve o bilgiye bağlı kod değişikliği yapılmaz.**
