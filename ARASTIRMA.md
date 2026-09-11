# BAŞAK ARAŞTIRMA DEFTERİ

Tarih: **12 Eylül 2026**  
Plan: `ANA-PLAN.md`  
Durum: **FAZ 0 / FAZ 1 araştırması başladı. Kod davranışı değiştirilmedi.**

## Araştırma sorusu

Neden Open Interpreter / Browser Use gibi ajanlar düşük maliyetli modellerle gerçek araç kullanımını sürdürebilirken Başak'a kişiselleştirme ve ek kontrol katmanları bağlandığında ücretsiz/yerel modellerin araç kullanımı ve doğal davranışı bozulabiliyor?

Bu belge yalnız doğrulanmış bulguları ve ayrıca işaretlenmiş hipotezleri tutar.

---

## 1. Open Interpreter — doğrulanan mimari

Resmî dokümana göre Open Interpreter üç şeyi ayrı katman olarak ele alıyor:

1. **Provider** — isteğin nereye gittiği ve bağlantı biçimi.
2. **Model** — kullanılan gerçek model.
3. **Harness** — modelin gördüğü ajan promptu, araçlar ve mesaj davranışı.

Aynı genel ajan kabuğu bütün ucuz/açık modellere zorlanmıyor. Kimi, Qwen, DeepSeek, GLM/ZCode gibi aileler için farklı harness seçenekleri var ve sağlayıcı/model ailesine uygun harness seçilebiliyor.

Kaynak:
- https://www.openinterpreter.com/docs/terminal/providers
- https://github.com/openinterpreter/openinterpreter
- https://www.openinterpreter.com/blog/open-interpreter

### Başak ile ilk fark

Başak'ta `brain/kapasite.py` model/havuzu yalnız temelde **küçük / güçlü** diye iki sınıfa ayırıyor. `chat/flow.py` ise model ailesinden bağımsız aynı ana prompt zincirini kuruyor:

- kimlik bloğu
- kişilik/system prompt
- tool yönlendirme
- ölçüm yönlendirme
- biçimlendirme yönlendirme
- varsa profil bloğu
- geçmiş

Küçük modellerde bazı parçalar azaltılıyor; ancak Qwen, GLM, Groq vb. için ayrı ajan harness davranışı yok.

**Doğrulanmış fark:** Open Interpreter model ailesi/harness ayrımı yapıyor; Başak şu anda esas olarak ikili kapasite sınıfı kullanıyor.

---

## 2. Başak'ın ilk cevap yolu — kritik doğrulanmış bulgu

`chat/flow.py` gerçek tool-call yoluna geçmeden önce `brain.cevapla_yayin(...)` ile streaming cevap deniyor.

`brain/brain.py::cevapla_yayin` sağlayıcı sırasını seçerken `tools=False` kullanıyor.

`brain/yayin.py` içindeki streaming çağrıları da modele gerçek tool şemalarını vermiyor; yalnız `messages` gönderiliyor.

Akışta model düz metin cevap üretirse `chat/flow.py` cevabı kaydedip **return** ediyor. Böylece alttaki `brain.cevapla(... tools=aktif_toollar)` yoluna hiç geçmeyebiliyor.

### Bunun anlamı

Araç gerektiren bir kullanıcı isteğinde bile ilk tur araçsızdır. Model araç çağırmak yerine metinden bir cevap üretirse gerçek araç yolu devreye girmeyebilir.

Bu, kullanıcının gözlediği "ücretsiz model özelliklerini/araçlarını kullanmıyor" sorunu için **somut bir adaydır**.

**Henüz kök neden ilan edilmedi.** Aynı görevler üzerinde ölçülmesi gerekiyor.

Doğrulanacak deney:

- aynı 20 araç-gerektiren görev
- streaming açık mevcut yol
- streaming atlanıp doğrudan tool yolu
- aynı model, aynı prompt, aynı görev

Ölçü: doğru tool çağrısı / düz metinle kaçış / doğru sonuç / süre.

---

## 3. Kişisel profil — doğrulanmış yük

`memory/profil.py::blok()` aktif profilin tamamını tek system bloğuna çeviriyor.

Profil yapısı:

- ad
- en fazla 30 tercih
- en fazla 30 bilgi

`chat/flow.py` profil boş değilse bu bloğu her mesaja ekliyor.

Dolayısıyla kişiselleştirme gerekli olmayan bir dosya, web veya görev isteğinde bile profil metni model bağlamına girebilir.

Bu, `ANA-PLAN.md` içindeki yeni kurala doğrudan gerekçe oluşturuyor:

**Tüm profil yerine görev için gerekli 0-3 kısa kişisel gerçek seçilecek.**

Bu değişiklik henüz uygulanmayacak; önce baz ölçüm yapılacak.

---

## 4. Araç yükü — Başak'ta mevcut azaltma var

Başak bu sorunu kısmen zaten tanımış durumda.

`tools/definitions.py`:

- normal core set: 5 araç
- küçük/ücretsiz model core set: 4 araç

Küçük core:

- `web_search`
- `add_task`
- `list_files`
- `read_file`

Diğer araçlar kelime tetikleyicileriyle ekleniyor.

Bu nedenle sorun yalnız "18 araç birden modele gidiyor" değildir. Mevcut kod araç sayısını azaltıyor.

Araştırılması gereken daha dar konu:

**Doğru dört araç verilse bile ilk streaming turunun araçsız olması ve prompt katmanlarının büyüklüğü küçük model davranışını bozuyor mu?**

---

## 5. Browser Use — doğrulanan mimari ders

Browser Use resmî skill dokümanı şu ayrımı öneriyor:

- basit halka açık sayfa/API/HTTP ile okunabiliyorsa browser kullanma
- tıklama, yazma, giriş, JavaScript ile çizilen sayfa veya oturum gerekiyorsa browser kullan

CLI kalıcı browser oturumu tutabiliyor; CDP üzerinden mevcut/running Chrome'a veya belirli profile bağlanabiliyor.

Kaynak:
- https://github.com/browser-use/browser-use
- https://github.com/browser-use/browser-use/blob/main/skills/browser-use/SKILL.md
- https://github.com/browser-use/browser-use/blob/main/browser_use/skill_cli/README.md

### Başak'taki mevcut durum

Başak'ta:

- `web_search` var
- `sayfa_oku` var (GET + HTML temizleme)

Ama kullanıcı oturumuyla çalışan gerçek etkileşimli browser aracı doğrulanmadı.

Bu yüzden Vixrex müşteri bulma için iki basamaklı yol araştırılacak:

1. ucuz/hafif araştırma: search + page read
2. yalnız gerektiğinde browser: Maps, dinamik site, form, tıklama, oturum

Browser Use doğrudan projeye kurulmayacak. Önce hangi Vixrex araştırma görevlerinin mevcut araçlarla yapılamadığı ölçülecek.

---

## 6. Mevcut ayrı hata — kimlik çelişkisi

Bu harness araştırmasından bağımsız bir mevcut hata var:

- `chat/prompts.py` kimlik bloğu: "Sen Edercanım'sın"
- `basak_app.py` kişilik metni aynı anda "Sen Başak'sın", "sen Edercanım'sın" ve "kendine asla Edercanım deme" diyor.

Bu çelişki ölçüm setini kirletebilir. FAZ 0 test sonuçlarında ayrı hata olarak işaretlenecek. Kullanıcı onayı olmadan bu araştırma commitinde davranış değiştirilmeyecek.

---

## 7. İlk test matrisi

Her satır aynı model ve aynı kullanıcı girdisiyle A/B çalıştırılacak.

| Görev | Mevcut yol | Doğrudan tool yolu | Minimum harness | Ölçü |
|---|---|---|---|---|
| sohbet | evet | evet | evet | doğallık/süre |
| klasör listele | evet | evet | evet | doğru tool |
| dosya oku | evet | evet | evet | doğru tool + gerçek içerik |
| web ara | evet | evet | evet | kaynaklı sonuç |
| sayfa oku | evet | evet | evet | gerçek sayfa |
| Vixrex işletme araştır | evet | evet | evet | doğrulanmış işletme profili |
| kişisel tercih gereken iş | evet | evet | seçilmiş 0-3 gerçek | doğru kişiselleştirme |
| kişisel tercih gerekmeyen iş | evet | evet | profil yok | profil sızıntısı var/yok |

## 8. Şu anda yapılmayacaklar

- Browser Use entegrasyonu yok.
- Open Interpreter kodunu kopyalama yok.
- Yeni hafıza sistemi yok.
- Yeni kişiselleştirme katmanı yok.
- `master` değişikliği yok.
- Para kazanma adına otomatik mesaj/form gönderme yok.

## 9. Sıradaki araştırma adımı

1. `chat/flow.py` mevcut streaming ve tool yolunun aynı görevlerde A/B ölçümünü çıkar.
2. Prompt parçalarının karakter/token yükünü ayrı ayrı ölç.
3. Profil açık/kapalı aynı görevleri karşılaştır.
4. Qwen/yerel ile en az bir ücretsiz bulut sağlayıcıyı aynı matrisle karşılaştır.
5. Sonuçtan sonra model-aile bazlı minimum harness tasarımına karar ver.
