# Read-lite tool sonucu ve argüman normalizasyonu

Tarih: 2026-09-12
Dal: feature/task-model-harness-v1-20260912

## Hedef
Canlı smoke'ta kalan iki aktif read-lite kusurunu düzeltmek:
1. read_file sonucu doğru gelmesine rağmen final cevabın özetlenmesi,
2. git_durum çağrısında modelin `{"properties":{"proje":"Başak"}}` biçiminde hatalı argüman üretmesi.

## Kabul ölçütleri
- A/chat-lite mevcut davranışı korunur.
- B/read_file doğru aracı kullanır ve kullanıcının ilk talebini araç kanıtından doğrudan cevaplar; genel özet üretmez.
- C/git_durum `basak` proje anahtarıyla gerçek aracı çalıştırır ve gerçek commit kanıtını verir.
- Yazma/sistem araçlarına izin açılmaz.
- Provider sırası, fallback, izin sistemi, file security ve legacy kapsamı değişmez.

## Mevcut kanıt
Canlı smoke commit 2732642 ve tanı smoke'u üzerinde:
- A geçti.
- B: profil=read-lite, tool=read_file, path=`C:\Projects\Başak\ANA-PLAN.md`; tool doğru seçildi fakat final cevap dosyanın ilk başlığını vermek yerine planı özetledi.
- C: profil=read-lite, tool=git_durum; model argümanı `{"properties":{"proje":"Başak"}}`; beyaz liste anahtarı eşleşmedi.
- D legacy davranışında `ac_uygulama` denedi; bu ayrı legacy kusurudur ve bu değişikliğin kapsamı dışındadır.

## Kod kanıtı
`chat/tools.py::tool_calling_multi` araç sonucu sonrası modele sabit olarak `DETAYLI özetle` talimatı ekliyor. Bu talimat read-lite'ın tam/kanıta dayalı cevap hedefiyle çelişiyor.

`tools/definitions.py::git_durum` şeması doğrudan `parameters.properties.proje` tanımlar; gerçek tool argümanı `{"proje":"basak"}` olmalıdır. Canlı model çıktısındaki üst seviye `properties` katmanı şema değildir, model hatasıdır.

`brain/harness.py::HarnessProviderProxy` her gerçek provider çağrısından hemen önce ve sonra read-lite profilini görebiliyor. Düzeltmeyi burada yapmak ortak legacy tool-loop'u değiştirmeden yalnız read-lite çağrı yüzeyini düzeltmeye izin verir.

## Doğrulanmış gerçekler
- read_file için modelin gönderdiği mutlak yol doğru.
- B'deki sorun yol çözümü olduğuna dair kanıt yok; final özet talimatı doğrudan kodda mevcut.
- git_durum beyaz listesi `basak`, `vixrex`, `numeramatch`, `xses` anahtarlarını kullanır.
- Read-lite zaten provider proxy üzerinden model-family harness'a giriyor.
- Legacy `_dinamik_araclar()` bütün araçları modele verir; bu ayrı kusur bu pakette değiştirilmeyecektir.

## DOĞRULANAMADI
- Her ücretsiz modelin aynı malformed-argument biçimini üretip üretmediği doğrulanamadı.
- B'nin her sağlayıcıda aynı özet sapmasını üretip üretmediği doğrulanamadı.
Bu nedenle düzeltme provider özel değil, yalnız read-lite profilinde deterministik yapılacaktır.

## İzin verilen kapsam
- `brain/harness.py`: read-lite final tool-sonuç kullanıcı mesajındaki genel `DETAYLI özetle` talimatını, ilk kullanıcı talebini kanıttan doğrudan yerine getiren dar talimatla değiştirmek.
- `brain/harness.py`: yalnız read-lite tool-call dönüşlerinde tek katmanlık `properties` model hatasını açmak.
- `brain/harness.py`: yalnız read-lite ölçüm araçlarında proje anahtarını `basak|vixrex|numeramatch|xses` biçimine normalize etmek.

## Yasak kapsam
- `chat/tools.py` ortak legacy tool-loop davranışını değiştirmek.
- legacy `_dinamik_araclar` davranışını değiştirmek.
- D/Vixrex legacy riskini bu pakete karıştırmak.
- provider sırası/model listesi değiştirmek.
- file permission/security kurallarını değiştirmek.
- yeni test/eval altyapısı kurmak.

## Risk sınıfı
Orta. Provider proxy dönüşü ve mesaj yüzeyi değişir; fakat yalnız `current_profile()==read-lite` olduğunda aktif olmalıdır. Legacy ve chat-lite aynı kalmalıdır.

## Sensör
Mevcut tek gerçek sensör: `Harness-Smoke.cmd` canlı ücretsiz-provider smoke.
Beklenen aktif profil sonucu: A+B+C = 3/3.
D yalnız `LEGACY RİSK` olarak raporlanabilir ve read-lite kabulünü bloke etmez.

## Rollback / red koşulu
- A/chat-lite bozulursa geri al.
- B veya C gerçek tool kullanmadan cevap verirse geri al.
- Yazma/sistem aracı read-lite yüzeyine açılırsa geri al.
- Legacy/provider/file-security kapsamına istemeden etki çıkarsa geri al.

## Karar
KANITLANDI — KOD DENEYİNE İZİN
