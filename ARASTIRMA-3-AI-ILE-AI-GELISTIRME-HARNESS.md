# BAŞAK — KİLİTLİ ARAŞTIRMA 3

## AI ile AI geliştirirken vibe-coding hatalarını engelleyen geliştirme harness'ı

Durum: **KİLİTLİ ARAŞTIRMA SONUCU**  
Tarih: **12 Eylül 2026**  
Kapsam: Başak ürününün kendisinden ayrı olarak, Başak'ı geliştiren AI ajanlarının çalışma sınırları.

## 1. Problem

Başak doğru mimariye sahip olsa bile onu geliştiren AI ajanı:

- kapsamı büyütürse,
- çalışan kodu gereksiz refactor ederse,
- testleri kendi değişikliğine uydurursa,
- büyük context içinde ana hedefi kaybederse,
- yaptığı işi kendisi kanıtsız biçimde "tamamlandı" ilan ederse,
- main/master üzerinde doğrudan işlem yaparsa,

ürün yine geriler.

Bu nedenle güvenli geliştirme formülü yalnızca `Model + Prompt` değildir.

**Geliştirme ajanı = Model + sınırlar + repo bilgisi + araçlar + sensörler + geri besleme + insan onayı.**

## 2. OpenAI Harness Engineering araştırma sonucu

OpenAI'nin kendi Harness Engineering çalışmasının ana bulgusu:

- dev, monolitik bir `AGENTS.md` contexti doldurur ve önemli kuralların kaybolmasına yol açar;
- `AGENTS.md` ansiklopedi değil, kısa bir harita olmalıdır;
- gerçek ürün bilgisi repo içindeki düzenli `docs/` yapısında sistemin hakikati olarak tutulmalıdır;
- test, doğrulama, review, feedback ve recovery mekanik döngünün parçası olmalıdır.

Başak için sonuç:

**Tek büyük prompt / tek büyük talimat dosyası yasak.**

Yapı:

- kısa `AGENTS.md` = harita ve değişmez güvenlik kuralları,
- `ANA-PLAN.md` = ürün hedefi ve fazlar,
- araştırma dosyaları = kanıt,
- aktif iş dosyası = yalnız mevcut hedef,
- testler/sensörler = mekanik hakem.

Kaynak:
- https://openai.com/index/harness-engineering/

## 3. OpenAI Codex kullanım araştırma sonucu

OpenAI mühendislerinin yayımladığı pratikler:

- büyük değişiklikte önce Ask/Plan, sonra Code;
- görevi GitHub issue gibi açık kapsamla tarif et;
- mümkün olduğunca küçük ve iyi sınırlandırılmış görev ver;
- geliştirme ortamını gerçek ürüne yaklaştır;
- `AGENTS.md` ile kalıcı bağlam ver;
- agent çıktısını test/log/diff ile doğrula.

Başak için sonuç:

Her geliştirme görevi başlamadan önce şu dört şey yazılı olacak:

1. hedef,
2. dokunulabilecek dosyalar,
3. dokunulmayacak davranışlar,
4. kabul kriteri.

"Hazır buradayken şunu da düzelt" türü scope genişlemesi yasak.

Kaynaklar:
- https://openai.com/business/guides-and-resources/how-openai-uses-codex/
- https://openai.com/index/introducing-codex/

## 4. Sandbox, izin ve risk kapısı

OpenAI'nin gerçek Codex kullanımındaki ana ilke:

- ajan belirli teknik sınırlar içinde çalışır,
- düşük riskli işlemler serbest ilerleyebilir,
- yüksek riskli veya sınır aşan işlemler inceleme/onay ister,
- ağ erişimi sınırsız bırakılmaz,
- ajan davranışı log/telemetry ile denetlenir.

Başak geliştirmesine uyarlama:

- `master` yazılamaz,
- ayrı güvenli dal zorunlu,
- dış servis/mesaj/harcama/veri silme onay ister,
- testleri veya kabul kriterini değiştirmek ayrı onay ister,
- yeni bağımlılık/framework eklemek araştırma kanıtı ister.

Kaynak:
- https://openai.com/index/running-codex-safely/

## 5. GitHub araştırma sonucu — talimat da test edilmelidir

GitHub resmi dokümanı AI code review için şunları açıkça belirtiyor:

- model deterministik değildir;
- çok uzun instruction dosyalarında bazı kurallar gözden kaçabilir;
- kısa, net ve somut kurallar daha iyi çalışır;
- repo-geneli ile dosya/path-özel talimatlar ayrılmalıdır;
- AI review tek başına merge engeli değildir; gerçek branch/ruleset/CI kapısı ayrıca gerekir.

Başak için sonuç:

- Python/brain/chat/tool gibi alanlara gerektiğinde path-özel kurallar,
- genel dosyaya yalnız değişmez kurallar,
- review ajanı implementasyon ajanından bağımsız ikinci göz,
- review sonucu tek başına başarı kanıtı değil; test + diff + davranış ölçümüyle birlikte değerlendirilir.

Kaynaklar:
- https://docs.github.com/en/copilot/tutorials/customize-code-review
- https://docs.github.com/en/copilot/concepts/agents/code-review

## 6. Anthropic araştırma sonucu — ajan kendi testini eritmemeli

Anthropic'in ajan/prompt rehberinde uzun otonom geliştirmeler için:

- işe başlamadan testleri tanımlamak,
- testleri yapılandırılmış biçimde takip etmek,
- test geçsin diye testleri silmemek/değiştirmemek,
- başlangıç/setup scriptleri kullanmak,
- yeni contextte filesystem/git/testlerden gerçek durumu yeniden keşfetmek,
- ilerlemeden önce temel entegrasyon testini çalıştırmak,
- UI işi varsa browser/computer doğrulaması sağlamak,
- gereksiz subagent çoğalmasını sınırlamak

öneriliyor.

Başak için sonuç:

**Ajan kendi başarısının hakemi olamaz.**

Kaynak:
- https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/prompt-templates-and-variables

## 7. Başak için KİLİTLİ GELİŞTİRME STEERING LOOP

Her ürün değişikliği aşağıdaki sıradan geçecek:

### A. DURUM
- mevcut `master`/referans commit sabitlenir,
- çalışan davranış kaydedilir,
- hedefle ilgili mevcut test/ölçüm bulunur.

### B. KAPSAM KİLİDİ
- tek hipotez,
- tek küçük hedef,
- izinli dosyalar,
- yasak alanlar,
- kabul kriterleri.

### C. GÜVENLİ DAL
- doğrudan `master`/`main` yok,
- deney/feature dalında küçük diff.

### D. UYGULAMA
- yalnız kanıtlanan ihtiyaç uygulanır,
- yan refactor yok,
- yeni framework/katman yok (ayrı kanıt olmadıkça),
- çalışan test değiştirilmez/silinmez (test yanlışlığı ayrı kanıtlanmadıkça).

### E. SENSÖRLER
Değişikliğin türüne göre bağımsız sensörler:

- unit test,
- hedefli integration test,
- lint/static analysis,
- type/syntax check,
- bağımsız code review,
- tool-call ölçümü,
- timeout/fallback ölçümü,
- log/audit,
- UI/browser kontrolü,
- önce/sonra davranış karşılaştırması.

### F. GERİ BESLEME
Sensör sonucu:

- başarısız → düzelt veya deneyi reddet,
- regresyon → geri al,
- kanıt yok → ilerleme yok,
- başarılı → kullanıcıya kanıt göster.

### G. İNSAN KAPISI
Casper/Furkan görmeden:

- merge yok,
- prod yok,
- dış dünyaya etkili işlem yok.

## 8. Vibe-coding kırmızı bayrakları

Aşağıdakiler görülürse ajan DURUR:

- görev sırasında kapsamın kendiliğinden büyümesi,
- istenmeyen refactor/rename/cleanup,
- bir hatayı çözmek için çalışan başka davranışı değiştirme,
- testleri kolaylaştırma veya silme,
- uzun plan yazıp gerçek kanıt üretmeme,
- "testler yeşil" deyip gerçek koşum göstermeme,
- `master`a doğrudan push,
- kullanıcı istemeden dependency/framework ekleme,
- aynı turda çok sayıda bağımsız değişiklik,
- hata sonrası daha fazla prompt/katman ekleyerek problemi gizleme,
- AI review yorumunu gerçek test yerine başarı sayma,
- tarayıcı/UI işinde yalnız koddan başarı sonucu çıkarma.

## 9. Ölçülebilir geliştirme kalite metrikleri

Her deneyde mümkün olanlar kaydedilir:

- değişen dosya sayısı,
- diff satırı,
- hedef dışı dosya değişikliği sayısı,
- önce geçen test sayısı,
- sonra geçen test sayısı,
- yeni başarısız test,
- hedef davranış başarı oranı,
- eski davranış regresyon oranı,
- review issue sayısı/severity,
- yeniden çalışma sayısı,
- gerçek görev tamamlama oranı.

Amaç "AI çok kod yazdı" değil:

**daha küçük diff ile daha yüksek doğrulanmış görev başarısı.**

## 10. Başak planına etkisi

Bu araştırma FAZ 0–5'in üstünde çalışan bir **meta güvenlik katmanıdır**.

FAZ 0–5'in sırası değişmez.

Ancak bundan sonra hiçbir fazdaki kod geliştirmesi bu steering loop dışından yapılamaz.

Özet:

**Başak'ı sadece daha iyi modelle geliştirmeyeceğiz. Başak'ı geliştiren AI'yı da sınırlandıran, ölçen ve düzelten bir harness içinde çalıştıracağız.**
