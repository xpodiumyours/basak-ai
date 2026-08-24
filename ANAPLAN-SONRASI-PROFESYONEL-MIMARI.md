# ANA-PLAN sonrası profesyonel mimari ve gelişim programı

> **Plan zinciri:** Bu belge [ANA-PLAN.md](./ANA-PLAN.md) tamamlandıktan sonra
> devreye girer. İki planın OpenAI ve Anthropic resmî belgelerine göre ortak
> çalışma sözleşmesi, uyum açıkları ve kalite kapıları
> [Resmidökümanuyum.md](./Resmidökümanuyum.md) belgesinde tutulur.

> Tarih: 24 Ağustos 2026  
> Kapsam: `ANA-PLAN.md` tamamen tamamlandıktan sonra Başak'ı güçlü kişisel betadan uzun ömürlü, güvenilir, yerel/hibrit Windows ürününe taşıma.  
> Değişmez hedef: tek kullanıcı, Windows, local-first, mümkün olduğunca ücretsiz. Bu belge mevcut kilitli fazların yerine geçmez; onların devamıdır.

## Kısa hüküm

Başak'ın bir sonraki sıçraması daha büyük modelden veya daha fazla özellikten gelmeyecek. Profesyonel seviye; **karar veren model ile eylem yapan kodun kesin ayrılması, bütün bir turun izlenebilmesi, verinin yaşam döngüsünün yönetilmesi, her sürümün ölçülmesi ve kötü sürümden güvenle geri dönülebilmesi** ile gelecek.

Başak tek bilgisayarda çalışan kişisel bir ürün olduğu için doğru hedef bir bulut şirketi mimarisi değildir. Doğru hedef **tek süreçte çalışan modüler çekirdek + tek yazarlı SQLite + sınırları belirli yerel servisler + gerektiğinde bulut model adaptörleri**dir. Anthropic üretim deneyiminde basit ve birleştirilebilir örüntülerin karmaşık framework'lerden daha başarılı olduğunu, karmaşıklığın yalnız ölçülmüş fayda varsa artırılmasını öneriyor ([Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)).

## 1. Hedef işletim modeli

Başak'ın ürün tanımı şu olmalı:

- **Birincil çalışma:** çevrimdışı sohbet, hafıza, not, görev ve ses özellikleri yerelde çalışır.
- **Bulut istisnadır:** yalnız seçici/politika izin verirse, gönderilecek bağlam görünür ve küçültülmüş biçimde buluta çıkar.
- **Tek kullanıcı:** hesap sistemi, çok kiracılı veri izolasyonu ve sunucu filosu kurulmaz.
- **Tek aktif çekirdek:** UI, zamanlayıcı ve ses girişleri aynı iş kuyruğuna komut verir; kalıcı veriyi tek yazar değiştirir.
- **Arızada küçülerek çalışma:** bulut, STT, TTS, embedding veya web ayrı ayrı bozulduğunda uygulama bütünüyle kapanmaz; kullanılabilen yeteneklerle devam eder.
- **İnsan son karar sahibidir:** dış dünyada etkisi olan, geri alınması zor veya hassas her işlem kısa ve işlem-özel onay ister. OWASP; model çıktısına dayanarak yetki verilmemesini, en az yetkiyi, karar ile yürütmenin ayrılmasını ve yüksek etkili işlemlerde insan denetimini öneriyor ([AI Agent Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html)).

NIST AI RMF'nin `Govern → Map → Measure → Manage` döngüsü Başak'a hafif biçimde uygulanmalı: her özellik için amaç/sınır, risk, ölçüm ve geri alma yolu yazılmalı; kurumsal form yığını kurulmamlıdır ([NIST AI RMF](https://www.nist.gov/itl/ai-risk-management-framework), [NIST GenAI Profile](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf)).

## 2. Önerilen modüler sınırlar

Tek Python uygulaması korunur; ancak modüller birbirinin iç ayrıntısına değil açık sözleşmelere bağlanır.

| Sınır | Sahip olduğu şey | Sahip olmaması gereken şey |
|---|---|---|
| `ui/adapter` | Kullanıcı girdisi, durum gösterimi, onay/iptal | Model seçimi, doğrudan DB yazımı |
| `voice/pipeline` | Wake/STT/TTS aşamaları, ses oturumu, kesme | Araç yetkisi, hafıza politikası |
| `core/orchestrator` | Tur durum makinesi, kuyruk, iptal, zaman aşımı | Sağlayıcıya özel HTTP kodu, dosya erişimi |
| `brain/model_gateway` | Yerel/bulut adaptörleri, kota, retry, devre kesici | Eylem yürütme, kalıcı hafıza yazımı |
| `context/builder` | Geçmiş, bilgi, hafıza ve araç bağlamını bütçeye göre kurma | Ham sırları buluta taşıma kararı |
| `policy` | Araç sınıfı, veri hassasiyeti, onay gereği, kapsam | Modelin doğal dil gerekçesine güvenme |
| `tools/executor` | Şema doğrulanmış çağrıyı çalıştırma, idempotency, sonuç | Yeni yetki üretme, kullanıcıya cevap yazma |
| `memory/repository` | Kanonik gerçekler, episodik anı, indeks, ömür/silme | Prompt üretme, sağlayıcı seçme |
| `state/repository` | Görev, onay, ayar, sürüm/migrasyon, çalışma durumu | İş mantığı |
| `telemetry` | Tur izi, ölçüler, maskeli olaylar, sağlık özeti | Ham konuşma/sırların sınırsız loglanması |
| `release/recovery` | Paket, yükseltme, yedek, restore, rollback | Sohbet akışı |

Bu sınırların amacı mikroservis üretmek değil, parçaların ayrı test edilebilmesini sağlamaktır. Model adaptörü değiştiğinde hafıza ve izin katmanının; UI değiştiğinde yürütücünün değişmemesi gerekir. Anthropic'in güncel uzun çalışan ajan mimarisi de **oturum kaydı, harness/orchestrator ve yürütme alanını** ayrı kavramlar olarak ele alıyor ([Managed Agents: Decoupling the brain from the hands](https://www.anthropic.com/engineering/managed-agents)).

## 3. Tur, olay ve durum mimarisi

Her kullanıcı isteği bir `run_id`; her model/araç çağrısı bir `call_id`; aynı konuşma bir `conversation_id` taşımalı. Home Assistant'ın ses mimarisi wake word, STT, intent ve TTS'yi ayrı aşamalar olarak çalıştırıp aşama olayları yayımlar; Başak da aynı görünürlüğü kendi yerel akışına uygulamalıdır ([Assist pipeline](https://developers.home-assistant.io/docs/voice/pipelines/), [Voice architecture](https://developers.home-assistant.io/docs/voice/overview/)).

Önerilen tur durumları:

`queued → listening/transcribing → planning → awaiting_approval → executing → verifying → speaking → completed`

Her aşamadan `cancelled`, `timed_out` veya `failed` son durumuna geçilebilir. Geçişleri yalnız orchestrator yapar; UI yalnız olayları gösterir.

Üç mesaj türü yeterlidir:

1. **Command:** “bu isteği işle”, “iptal et”, “şu eylemi onayla”.
2. **Event:** “STT başladı”, “model seçildi”, “onay bekleniyor”, “araç bitti”.
3. **Result:** şemalı model cevabı veya şemalı araç sonucu.

Olay günlüğü ham düşünce zinciri tutmamalı; zaman, kimlikler, aşama, sağlayıcı/model sürümü, araç adı, politika sonucu, süre, token ve hata sınıfını tutmalıdır. Ham web/belge metni ile sırlar loga girmemelidir. OpenTelemetry'nin iz, ölçü ve log ayrımı bu ortak kimliklerle bir turun uçtan uca izlenmesine uygun standart bir sözlük sağlar; başlangıçta veriler yalnız yerel JSONL/SQLite'a yazılabilir, Collector veya bulut servisi gerekmez ([OpenTelemetry signals](https://opentelemetry.io/docs/concepts/signals/), [log correlation](https://opentelemetry.io/docs/specs/otel/logs/)).

**Bilinçli sınır:** bütün uygulamayı “event sourcing”e çevirmeyin. Kullanıcıya görünen görev, onay ve uzun iş durumları kalıcı; geçici ses paketleri ve ara tokenlar bellek içinde, sınırlı kuyrukta kalsın.

## 4. Güvenli araç yürütme ve gerçek onay

Profesyonel eylem hattı şu olmalıdır:

`model önerisi → şema doğrulama → politika kararı → gerekirse kullanıcı onayı → yürütme → gerçek sonuç doğrulama → kullanıcıya bildirim`

### Eylem sözleşmesi

Her araç çağrısı en az şu alanları taşımalı:

- `call_id`, araç ve sürümü;
- doğrulanmış argümanlar;
- hedef kaynak (tam çözümlenmiş dosya yolu/URL/uygulama);
- etki sınıfı: `read`, `write_reversible`, `external`, `system`, `destructive`;
- idempotency anahtarı ve zaman aşımı;
- onay gerekiyorsa **yalnız bu çağrıya, hedefe ve kısa süreye bağlı** onay bileti.

Onay ekranı teknik olmayan dille “ne yapılacak, nereye, hangi veri gidecek, geri alınabilir mi?” sorularını cevaplamalıdır. “Bu oturumda her şeye izin ver” varsayılan seçenek olmamalıdır. Onayın yokluğu ret sayılmalı; model onay veremez, onay kapsamını genişletemez. OpenAI de yüksek riskli işlemler ve retry/eylem sınırı aşımında insan müdahalesini; guardrail'lerin kimlik/yetki ve standart güvenlik kontrolleriyle katmanlanmasını öneriyor ([Practical Guide to Building Agents](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/)).

### Ek yapısal garantiler

- Executor yalnız kayıtlı araç ve şema kabul eder; serbest shell/Python çalıştırmaz.
- Bir turun ilk yetki kümesi tavan olmaya devam eder.
- Yazma işlemleri mümkünse atomik ve geri alınabilir yapılır; dış iletişim/gönderim için önce önizleme üretilir.
- Aynı `idempotency_key` ikinci kez geldiğinde işlem tekrarlanmaz.
- Araç zinciri, retry, süre, çıktı boyutu ve bulut tokenı kodla sınırlanır.
- Web, belge ve hafızadan gelen metin **talimat değil güvenilmeyen veri**dir; araç yetkisini etkileyemez. OWASP bunu doğrudan prompt injection, tool abuse, data exfiltration ve memory poisoning riskleri olarak tanımlar ([OWASP Agent Security](https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html)).

## 5. Hafıza ve veri yaşam döngüsü

Tek `memories` yığını yerine dört veri sınıfı görünür olmalıdır:

| Veri sınıfı | Örnek | Kaynak/ömür | Silme davranışı |
|---|---|---|---|
| Kanonik kullanıcı gerçeği | Tercih, kişi, kalıcı ayar | Kullanıcı onaylı; değişene kadar | Açık unutma ile sil/güncelle |
| Episodik anı | Geçmiş konuşma özeti | Otomatik; puan ve son kullanma | Limit/TTL ile buda |
| Kaynak belge indeksi | `knowledge/`, `defter/`, Obsidian | Dosyadan türetilir | İndeksi sil, kaynaktan yeniden üret |
| Operasyonel/audit veri | hata, çağrı, onay sonucu | Kısa ömürlü, maskeli | Otomatik rotasyon |

Her hafıza kaydı `source`, `created_at`, `last_used`, `expires_at`, `sensitivity`, `confidence`, `content_hash` ve sürüm taşımalı. Kullanıcının açıkça söylediği gerçek ile modelin çıkardığı tahmin ayrı tutulmalı; çıkarım, kullanıcı onayı olmadan kanonik gerçeğe yükselmemelidir.

Veri yaşam döngüsü `collect → classify → use → retain → export/delete` olarak belgelenmeli. NIST Privacy Framework, ürün tasarımında kişisel verinin tanınması ve yönetilmesi için risk-temelli bir yaşam döngüsü önerir ([NIST Privacy Framework](https://www.nist.gov/privacy-framework)). Başak için bunun hafif karşılığı bir “verilerim” ekranı/komutu, kaynak bazlı dışa aktarma, sohbet anılarını silme ve indeksleri yeniden kurabilmedir.

Buluta gönderilecek bağlam ayrı bir **outbound policy** kapısından geçmeli: varsayılan olarak sırlar, tam dosyalar, kişisel kanonik hafıza ve gereksiz geçmiş çıkmaz; yalnız görev için gerekli küçültülmüş parça çıkar. API anahtarları düz ayar dosyası yerine Windows kullanıcı hesabına bağlı DPAPI ile korunabilir; Microsoft'a göre DPAPI ile korunan veri normalde yalnız aynı oturum kimliğiyle ve aynı bilgisayarda çözülebilir ([CryptProtectData](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata)). DPAPI anahtar yedeği değildir; kullanıcı verisi yedeğinden ayrı ele alınmalıdır.

## 6. Eval, red-team ve canary sistemi

Unit testler gerekli fakat yeterli değildir. Bir ajanı değerlendirirken model ile harness, araçlar, durum değişiklikleri ve son gerçek sonuç birlikte ölçülmelidir. Anthropic; görev, çoklu deneme, tam transcript/trace ve **son ortam durumu** ayrımını öneriyor; başlangıç için gerçek hatalardan 20–50 görev yeterli olsa da olgun ürün bankası zamanla büyütülmelidir ([Demystifying Evals for AI Agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)).

### Dört ayrı paket

1. **Regresyon:** Daha önce yaptığı işleri hâlâ yapıyor mu? Hedef kritik işlerde yaklaşık %100.
2. **Kabiliyet:** Henüz zorlandığı gerçek görevler; ilerleme ölçer, başarısızlık normaldir.
3. **Güvenlik/red-team:** prompt injection, zehirli belge/hafıza, path/SSRF, sır sızıntısı, onay atlama, tekrar saldırısı, sınırsız araç zinciri.
4. **Dayanıklılık:** Ollama/bulut kapalı, DB kilitli, disk dolu, mikrofon yok, yarım güncelleme, süreç zorla kapandı, bozuk yedek.

Her kritik değişken görev en az 5 deneme çalıştırmalı; yalnız ortalama değil en kötü deneme ve p95 süre de raporlanmalı. Güvenlik maddeleri “puan” değil sert kapıdır: yetkisiz eylem, yanlış başarı iddiası ve sır sızıntısı **0** olmalıdır. Eval'lar sonucu ölçmeli; geçerli tek bir araç sırasını zorlamamalıdır. Anthropic, değişkenlik için çoklu trial ve mümkün olduğunda sonuç-temelli deterministik grader öneriyor ([agent eval rehberi](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)).

### Tek kullanıcı için canary

Sunucu filosu olmadığı için klasik yüzde dağıtımı kurulmaz:

- önce kayıtlı gerçek turlar üzerinde **replay/shadow**;
- sonra özellik bayrağıyla yalnız yeni bir test oturumu;
- sonra bir günlük elle açılan canary;
- sorun yoksa varsayılan açık.

Her model/prompt/tool değişikliği bir sürüm kimliği taşır. Sağlayıcıların davranışı değişebildiği için mümkün olduğunda model sürümü sabitlenmeli ve değişim eval kapısından geçmelidir; OpenAI da tutarlı davranış için sabit model sürümü ve eval öneriyor ([API backward compatibility](https://platform.openai.com/docs/api-reference/backward-compatibility)).

## 7. Gözlemlenebilirlik ve kişisel SLO'lar

Amaç “çok log” değil, “Başak neden bunu yaptı ve kullanıcı etkisi neydi?” sorusuna cevap vermektir.

Her turda en az şunlar ölçülmeli:

- uçtan uca ve aşama bazlı p50/p95 gecikme;
- başarılı/başarısız/iptal/timeout oranı;
- doğru araç çağırma, dürüst red, yanlış başarı iddiası;
- onay istenen/onaylanan/reddedilen eylem;
- yerel/bulut seçimi, token ve retry;
- DB boyutu, WAL boyutu/checkpoint, yedek yaşı ve son restore sonucu;
- açılış, kapanış ve çökme sonrası toparlanma.

Google SRE, kullanıcı için önemli az sayıda SLI seçmeyi; gecikme, hata, kullanılabilirlik, dayanıklılık ve doğruluğu ölçmeyi; ortalama yerine uzun kuyruğu görebilmek için yüzdelikleri kullanmayı önerir ([Service Level Objectives](https://sre.google/sre-book/service-level-objectives/)). Başak için ilk 30 günlük hedefler **başlangıç hipotezi** olarak yazılmalı ve gerçek tabandan sonra sıkılaştırılmalıdır:

- desteklenen yerel komutlarda başarılı sonuç ≥ %95;
- kullanıcı iptalinin etkili olması ≤ 1 saniye;
- yanlış “işlem yapıldı” iddiası, yetkisiz eylem ve sır sızıntısı = 0;
- son başarılı yedek yaşı ≤ 24 saat;
- 30 günde veri kaybı = 0;
- etkileşimli yazılı turlarda p95 süre donanıma göre ölçülmüş bütçenin altında.

SLO kaçırılırsa yeni özellik dondurulup güvenilirlik işi öne alınmalıdır. Yüzde 100 genel kullanılabilirlik gibi yapay hedefler konmamalıdır.

## 8. SQLite, sürümleme ve migrasyon

SQLite doğru seçimdir; ikinci bir veritabanı eklenmemelidir. Kalıcı yazma için **tek yazar**, kısa transaction, `busy_timeout`, açık foreign key politikası ve kontrollü WAL checkpoint kullanılmalı. SQLite WAL eşzamanlı okuyucu-yazıcıyı kolaylaştırır; ancak WAL dosyası kalıcı durumun parçasıdır ve canlı DB'yi yalnız ana `.db` dosyasını kopyalayarak yedeklemek veri kaybına yol açabilir ([SQLite WAL](https://sqlite.org/wal.html)). Ayrıca SQLite'ın 2026 WAL-reset düzeltmeleri nedeniyle kullanılan SQLite sürümü doğrulanmalı ve bilinen güvenli sürüm paketlenmelidir ([SQLite WAL, bölüm 11](https://sqlite.org/wal.html#walreset)).

### Migrasyon sözleşmesi

- Uygulama sürümü, DB şema sürümü, prompt sürümü, tool schema sürümü ve varsayılan model kartı ayrı sürümlenir.
- DB sürümü uygulamanın kontrolündeki `PRAGMA user_version` ile tutulabilir; SQLite bu alanı özellikle uygulamanın kullanımına bırakır ([SQLite PRAGMA user_version](https://www.sqlite.org/pragma.html#pragma_user_version)).
- Her göç `N → N+1` olarak, tek transaction içinde ve tekrar koşmaya dayanıklı yazılır.
- Göçten önce tutarlı yedek alınır; açılışta DB daha yeni sürümse eski uygulama yazmayı reddeder.
- Göç sonrası `foreign_key_check`, `quick_check/integrity_check` ve temel okuma-yazma smoke testi koşar ([SQLite integrity_check](https://www.sqlite.org/pragma.html#pragma_integrity_check)).
- En az önceki iki uygulama sürümünden güncelleme ve kötü güncellemeden geri dönüş provaları saklanır.

## 9. Yedekleme ve geri yükleme

`data/` klasörünü çalışırken sıradan dosya kopyasıyla çoğaltmak güvenli yedek sayılmamalıdır. SQLite'ın Online Backup API'si canlı veritabanından tutarlı snapshot alabilir; `VACUUM INTO` da tutarlı ve sıkıştırılmış kopya üretir ([SQLite Backup API](https://www.sqlite.org/backup.html), [VACUUM INTO](https://www.sqlite.org/lang_vacuum.html#vacuuminto)).

Önerilen kişisel politika:

- 7 günlük + 4 haftalık yerel snapshot;
- DB ile birlikte kullanıcı tarafından yazılmış `knowledge/`, `defter/`, ayarlar şeması ve görev ekleri;
- türetilmiş embedding/FTS indeksleri gerekiyorsa yeniden üretilebilir olarak işaretlenir;
- loglar ve cache yedeğe girmez;
- API anahtarları kullanıcı verisiyle düz biçimde yedeklenmez;
- her yedekte manifest, uygulama/şema sürümü, dosya hash'i ve oluşturma zamanı bulunur;
- yedek tamamlanınca bütünlük kontrolü; ayda bir boş geçici profile gerçek restore provası.

Yedek başarı mesajı restore kanıtı değildir. Çıkış kriteri: en son snapshot'tan yeni profile geri yükleme, uygulamanın açılması, kanonik hafıza/görev/not örneklerinin okunması ve indekslerin yeniden kurulmasıdır. Hedef başlangıç olarak `RPO ≤ 24 saat`, `RTO ≤ 15 dakika` olabilir.

## 10. Paketleme, güncelleme ve rollback

### Kişisel beta aşaması

Önce PyInstaller **onedir** paketi üretin. PyInstaller da tek dosyadan önce klasör paketinin doğrulanmasını öneriyor; onedir hata ayıklamayı kolaylaştırır, onefile ise daha yavaş açılır ve geçici klasöre çıkar ([PyInstaller operating mode](https://www.pyinstaller.org/en/stable/operating-mode.html)). Paket ayrı temiz Windows kullanıcı profilinde, Python/Ollama kapalı-açık senaryolarıyla denenmelidir.

### Güvenli güncelleme akışı

`manifest kontrolü → paketi staging'e indir → hash/imza doğrula → veri yedeği → uygulamayı kapat → yan yana kur → migrasyon/smoke test → etkinleştir`

Başarısızlıkta eski uygulama ve göç öncesi snapshot birlikte geri alınır. Güncelleme hiçbir zaman çalışan dosyaların üzerine parça parça yazmamalıdır. Bir sürüm “iyi bilinen” olarak saklanmalıdır.

Windows MSIX/App Installer, Store dışında da açılışta/arka planda güncelleme ve onarım ayarlarını; gerektiğinde daha düşük sürüme geçmeyi destekler ([MSIX auto-update](https://learn.microsoft.com/en-us/windows/msix/app-installer/auto-update-and-repair--overview), [update settings](https://learn.microsoft.com/en-us/windows/msix/app-installer/update-settings)). Fakat bu, ANA-PLAN biter bitmez zorunlu değildir; önce güvenilir onedir + elle güncelleme/rollback kanıtı kurulmalıdır.

### İmza gerçeği

Herkese dağıtımda Windows kod imzası ayrı bir ürün gereğidir. Microsoft'a göre imzasız veya self-signed uygulama SmartScreen uyarısı alır; Store dağıtımı Microsoft imzası sağlar, Store dışı güven için geçerli yayıncı sertifikası gerekir ([SmartScreen reputation](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation), [MSIX signing](https://learn.microsoft.com/en-us/windows/msix/package/signing-package-overview)). Sigstore/Cosign ücretsiz biçimde dosya ve doğrulama paketi imzalayabilir, ancak bu **Windows Authenticode/SmartScreen yerine geçmez**; geliştirici/testçi için kaynak→artifact doğrulaması sağlar ([Sigstore blob signing](https://docs.sigstore.dev/cosign/signing/signing_with_blobs/)). SLSA provenance da bir paketin nerede, ne zaman ve nasıl üretildiğini izlenebilir kılar ([SLSA provenance](https://slsa.dev/spec/v1.2/provenance)).

Tek kullanıcı ve ücretsiz hedefte doğru sıra: hash + sürümlü manifest + yerel doğrulanmış build → ücretsiz Sigstore/provenance isteğe bağlı → ancak geniş dağıtım kararı verilirse Authenticode/MSIX/Store maliyeti.

## 11. ANA-PLAN sonrası öncelikli yol haritası

### FAZ 6 — Mimari dikişleri sabitleme

**İşler:** modül sözleşmeleri, `run_id/call_id`, tek orchestrator, durum makinesi, ADR'ler; mevcut davranışı adaptörlerin arkasına alma.

**Çıkış:** mevcut tüm testler yeşil; metin ve ses turları aynı durum makinesinden geçiyor; her tur tek izde baştan sona görülebiliyor; UI/voice/model/tool katmanlarının doğrudan DB yazımı sözleşme testleriyle engelli; 20 kayıtlı tur replay sonucu tabanla aynı.

### FAZ 7 — Yetki ve onayı yapısallaştırma

**İşler:** etki sınıfları, çağrıya bağlı süreli onay bileti, idempotency, önizleme, timeout/retry/tool-chain sınırı.

**Çıkış:** `external/system/destructive` çağrıların %100'ü doğru onay gerektiriyor; süresi geçmiş, başka hedefe ait ve tekrar kullanılan onayların tamamı reddediliyor; 50+ saldırı senaryosunda yetkisiz eylem/sır sızıntısı 0; iptal edilen yazma işlemi yarım durum bırakmıyor.

### FAZ 8 — Veri ve hafıza yaşam döngüsü

**İşler:** veri envanteri, kanonik/episodik/türetilmiş/audit ayrımı, TTL, sensitivity, export/delete, outbound cloud policy, DPAPI sır deposu.

**Çıkış:** her kalıcı tablo/dosyanın sahibi ve ömrü belgeli; “beni unut” testleri silinen verinin retrieval ve bağlamda görünmediğini kanıtlıyor; indeks sıfırdan kurulabiliyor; bulut egress testinde yasak sınıfların sızıntısı 0; API anahtarı düz log/ayar/yedekte yok.

### FAZ 9 — Eval, red-team ve canary kapısı

**İşler:** regresyon/kabiliyet/güvenlik/dayanıklılık paketleri, çoklu trial, transcript ve outcome grader, replay/shadow, özellik bayrağı.

**Çıkış:** güvenlik paketinin tamamı 5 tekrarda geçiyor; yanlış başarı iddiası/yetkisiz eylem/sır sızıntısı 0; kritik regresyon görevleri önceden ilan edilen eşiği karşılıyor; model/prompt/tool değişimi sürümsüz yapılamıyor; canary tek ayarla kapanıp eski yola dönebiliyor.

### FAZ 10 — Gözlemleme, sağlık ve SLO

**İşler:** yerel trace/metric/log, maskeli hata sınıfları, DB/yedek sağlık kartı, SLI tabanı ve hata bütçesi.

**Çıkış:** turların ≥%99'unda tam korelasyonlu iz; telemetry sır testleri %100 geçiyor; p50/p95, hata, red, bulut ve onay metrikleri 30 gün saklanıyor; SLO ihlalinde özellik geliştirmeyi durdurma kuralı belgeli; tek komutla anonimleştirilmiş tanı paketi üretilebiliyor.

### FAZ 11 — Sürüm, paket, migrasyon ve kurtarma

**İşler:** deterministik onedir build, manifest/hash, DB migrasyon runner, online backup, side-by-side update ve rollback.

**Çıkış:** temiz Windows profilinde kurulum/açılış/kaldırma; son iki sürümden yükseltme; kasıtlı bozuk paket/hash/migrasyon reddi; kötü sürümden uygulama+veri rollback; ayda bir restore provası; `RPO ≤ 24 saat`, `RTO ≤ 15 dakika`; build artifact'i commit ve bağımlılık manifestine izlenebilir.

### FAZ 12 — Uzun kullanım ve ürün çıkış kapısı

**İşler:** en az 30 günlük kişisel dogfood, en az 200 gerçek tur, haftalık başarısız tur incelemesi, hata→eval dönüşümü, kullanım kılavuzu ve kurtarma ekranı.

**Çıkış:** 30 günde veri kaybı, yetkisiz eylem ve yanlış eylem başarı iddiası 0; kritik SLO'lar karşılanıyor; bulunan her ciddi hata için regresyon testi var; iki ardışık sürüm rollback gerektirmeden tamamlanmış; Casper yedek geri yükleme ve izin deneyimini canlı onaylamış.

Bu noktada doğru tanım **“kişisel kullanıma hazır profesyonel yerel asistan v1”** olur. Siri/Alexa ölçeği veya filmdeki Jarvis değildir; fakat sahibinin bilgisayarında ölçülebilir, güncellenebilir ve kurtarılabilir gerçek üründür.

## 12. Şimdi yapma listesi

ANA-PLAN tamamlanır tamamlanmaz aşağıdakiler ana darboğazı çözmez:

- mikroservis, Docker, Kubernetes, mesaj kuyruğu sunucusu;
- harici vector database veya ikinci bir ana veritabanı;
- çoklu ajan sürüsü ya da otonom “kendi kodunu değiştirme”;
- kendi temel modelini eğitme;
- mobil uygulama, akıllı ev ve çok oda ses uyduları;
- her şeyi sürekli dinleyen wake word sistemi;
- tüm konuşmaları bulut gözlemleme servisine gönderme;
- imza, rollback ve veri yedeği kanıtlanmadan sessiz otomatik güncelleme;
- güvenlik problemi ölçülmeden tüm DB'yi karmaşık özel şifreleme katmanına taşıma;
- yalnız model benchmark'ına bakarak varsayılan modeli değiştirme;
- framework değişimini mimari ilerleme sayma.

Bu özellikler ancak FAZ 12 sonrası gerçek kullanım verisi onların belirli bir sorunu çözdüğünü gösterirse ayrı karar olarak açılmalıdır.

## 13. Profesyonel gelişim süreci

Her değişiklik şu küçük döngüden geçmelidir:

1. Gerçek kullanıcı sorunu ve beklenen sonuç yazılır.
2. Önce eval/regresyon görevi ve risk sınıfı eklenir.
3. En küçük modül değişikliği yapılır; veri/sözleşme değişiyorsa migrasyon ve rollback birlikte yazılır.
4. Unit + eval + red-team + temiz profil smoke test çalışır.
5. Replay/shadow, ardından tek oturum canary yapılır.
6. SLO ve telemetry karşılaştırılır; kötüleşirse geri alınır.
7. Sonuç, sınırlama, sürüm ve kurtarma yolu deftere/ADR'ye kaydedilir.
8. Canlı kullanımda bulunan hata eval bankasına eklenir.

NIST SSDF güvenli geliştirme pratiklerinin mevcut geliştirme yaşam döngüsüne entegre edilmesini ve kök nedenlerin tekrarını önlemeyi önerir; Başak için bunun hafif uygulaması tam olarak “her gerçek hata → kalıcı test + düzeltme + kanıt” döngüsüdür ([NIST SSDF SP 800-218](https://csrc.nist.gov/pubs/sp/800/218/final)). Tedarik zinciri için ilk yeterli adım kilitli bağımlılıklar, SBOM/bağımlılık manifesti, commit'ten tekrarlanabilir build ve artifact hash/provenance'tır; ağır kurumsal sertifikasyon değildir ([SLSA v1.2](https://slsa.dev/spec/v1.2/)).

## Son karar

`ANA-PLAN.md` Başak'ı güvenilir betaya getirir. Bu devam programı ise onu profesyonel yapan görünmeyen kasları kurar: **sabit sınırlar, gerçek onay, kontrollü veri ömrü, sürekli eval, ölçülebilir hizmet kalitesi, sürümlü göç ve kanıtlanmış kurtarma**. Öncelik sırası korunursa Başak'ın local-first ve ücretsiz karakteri bozulmadan uzun ömürlü bir ürün elde edilir.
