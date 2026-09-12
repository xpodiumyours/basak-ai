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
Canlı smoke commit 2732642 üzerinde:
- A geçti.
- B: profil=read-lite, tool=read_file, path=`C:\Projects\Başak\ANA-PLAN.md`; tool doğru seçildi fakat final cevap dosyanın ilk başlığını vermek yerine planı özetledi.
- C: profil=read-lite, tool=git_durum; model argümanı `{"properties":{"proje":"Başak"}}`; beyaz liste anahtarı eşleşmedi.
- D legacy davranışında `ac_uygulama` denedi; bu ayrı legacy kusurudur ve bu değişikliğin kapsamı dışındadır.

## Kod kanıtı
`chat/tools.py::tool_calling_multi` araç sonucu sonrası modele sabit olarak `DETAYLI özetle` talimatı ekliyor. Bu talimat read-lite'ın tam/kanıta dayalı cevap hedefiyle çelişiyor.

`tools/definitions.py::git_durum` şeması doğrudan `parameters.properties.proje` tanımlar; gerçek tool argümanı `{"proje":"basak"}` olmalıdır. Canlı model çıktısındaki üst seviye `properties` katmanı şema değildir, model hatasıdır.

## Doğrulanmış gerçekler
- read_file için modelin gönderdiği mutlak yol doğru.
- B'deki sorun yol çözümü olduğuna dair kanıt yok; final özet davranışı doğrudan kodda mevcut.
- git_durum beyaz listesi `basak`, `vixrex`, `numeramatch`, `xses` anahtarlarını kullanır.
- Tool argüman düzeltme katmanı zaten `chat/tools.py::tool_argumani_duzelt` içinde mevcuttur; yeni mimari gerekmez.

## DOĞRULANAMADI
- Her ücretsiz modelin aynı malformed-argument biçimini üretip üretmediği doğrulanamadı.
- B'nin her sağlayıcıda aynı özet sapmasını üretip üretmediği doğrulanamadı.
Bu nedenle düzeltme model/provider özel değil, mevcut tool-loop sözleşmesinde deterministik ve dar yapılacaktır.

## İzin verilen kapsam
- `chat/tools.py`: read-lite final tool-sonuç talimatını daraltmak.
- `chat/tools.py`: ölçüm araçlarında tek katmanlık `properties` argüman hatasını açmak ve proje anahtarını normalize etmek.

## Yasak kapsam
- legacy `_dinamik_araclar` davranışını değiştirmek.
- D/Vixrex legacy riskini bu pakete karıştırmak.
- provider sırası/model listesi değiştirmek.
- file permission/security kurallarını değiştirmek.
- yeni test/eval altyapısı kurmak.

## Risk sınıfı
Orta. Ortak tool-loop dosyası değişir; fakat yeni davranış yalnız mevcut `current_profile()==read-lite` ve ölçüm tool argümanı düzeltmesiyle sınırlanmalıdır.

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
