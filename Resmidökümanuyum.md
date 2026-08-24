# Başak.ai — İki Planın Resmî Doküman Uyum Raporu

> **Bağlı planlar:** [ANA-PLAN.md](./ANA-PLAN.md) →
> [ANAPLAN-SONRASI-PROFESYONEL-MIMARI.md](./ANAPLAN-SONRASI-PROFESYONEL-MIMARI.md)
>
> **Rolü:** Bu belge iki planın yerine geçmez. Her iki plan boyunca ve
> sonrasında Başak.ai, OpenAI/Codex ve Anthropic tabanlı ajanların uyması
> gereken sağlayıcıdan bağımsız güvenlik, kalite, şeffaflık, verimlilik ve
> çalışma sürekliliği üst sözleşmesidir. Bir plan maddesiyle çelişki görülürse
> ajan sessizce karar vermez; çelişkiyi kaydeder, güvenli tarafta durur ve
> gerekli plan düzeltmesini Casper'in onayına sunar.

**İncelenen belgeler:** `ANA-PLAN.md` ve `ANAPLAN-SONRASI-PROFESYONEL-MIMARI.md`  
**İnceleme tarihi:** 24 Ağustos 2026  
**Kapsam:** Yalnızca plan metinleri incelendi; kodun uygulanmış olduğu, testlerin gerçekten geçtiği veya güvenlik kontrollerinin çalıştığı varsayılmadı.  
**Kaynak sınırı:** OpenAI için yalnız `developers.openai.com` / `platform.openai.com`; Anthropic için yalnız `anthropic.com/engineering` / `docs.anthropic.com` kullanıldı.

## 1. Yönetici özeti

- `ANA-PLAN.md`, doğru yönde bir **prototipten kontrollü geliştirmeye geçiş planıdır**; fakat “mimar ajan tam yetkili” ifadesi, en az yetki ve kullanıcı niyetine bağlı yetkilendirme ilkeleriyle çelişmektedir. Evals, yapılandırılmış çıktı ve geri dönüş düşünülmüş olsa da izin sınırı, veri saklama, izleme, bağlam yönetimi ve gerçek izolasyon yeterince tanımlı değildir.
- `ANAPLAN-SONRASI-PROFESYONEL-MIMARI.md`, resmî kılavuzlarla büyük ölçüde uyumlu bir **profesyonel kişisel ajan mimarisi taslağıdır**. Model–politika–araç–yürütücü ayrımı, tek yazıcı, iz kimlikleri, sonuç doğrulaması, eval ve canary/rollback yaklaşımı güçlüdür.
- İkinci plandaki başlıca eksikler: sağlayıcıya özel veri saklama profili, riskli araçlar için gerçek dosya sistemi + ağ izolasyonu, uzun görevlerde yapılandırılmış devir/özetleme, yapılandırılmış çıktıların ret/yarım yanıt durumları ve resmî kaynak hijyeni.
- Hedef statü “mutlak garantili” değil, **koşullu ve kanıtlı kişisel v1** olmalıdır. Güvence; değişmez mimari sınırlar, tekrarlanabilir ölçüm, kayıt, canary ve denenmiş rollback birleşiminden gelir.

## 2. Puanlama yöntemi

Bu puanlar ürün olgunluğu veya çalışan kod güvenliği puanı değildir; plan metninin resmî rehberlerdeki ilkelere ne ölçüde karşılık verdiğini gösterir.

Her ölçüt sabit ağırlığa sahiptir:

- **Uyumlu:** ağırlığın %100'ü
- **Kısmi:** ağırlığın %50'si
- **Eksik** veya **Çelişki:** %0

Boyutlar ve ağırlıklar:

| Boyut | Ölçütler |
|---|---|
| Güvenlik | Araç/politika sınırı 25; kullanıcı niyeti–onay–en az yetki 20; güvenilmeyen veri/prompt injection 20; dosya+ağ izolasyonu 20; veri çıkışı/saklama 15 |
| Kalite | Eval hedefi/veri seti 25; çoklu deneme+sonuç derecelendirme 20; trace+insan kalibrasyonu 15; model/prompt/araç sürümü 15; canary/rollback 15; gerçek kullanım/uzun süre doğrulama 10 |
| Verimlilik | Basit mimari 20; bağlam bütçesi/JIT/özetleme 25; açık ve küçük araç kümesi 20; kalite kapılı token/istek/gecikme ölçümü 20; uzun görev devri 15 |
| Şeffaflık | İlişkili run/call kimlikleri 25; iddia–kanıt–sonuç–belirsizlik 25; sürüm/değişiklik/kaynak kaydı 20; onay önizlemesi/etki görünürlüğü 15; SLI/SLO/bilinen sınırlar 15 |

| Plan | Güvenlik | Kalite | Verimlilik | Şeffaflık | Eşit ağırlıklı toplam |
|---|---:|---:|---:|---:|---:|
| `ANA-PLAN.md` | 13 | 55 | 30 | 50 | **37/100** |
| `ANAPLAN-SONRASI-PROFESYONEL-MIMARI.md` | 83 | 95 | 73 | 90 | **85/100** |

Puanların yüksek olması uygulama kanıtı değildir. Özellikle güvenlikte bir metin maddesinin “var” olması, izolasyon veya yetki kontrolünün kodda doğru çalıştığını kanıtlamaz.

## 3. `ANA-PLAN.md` uyum matrisi

| Alan | Durum | Belgede görülen | Resmî dayanak / değerlendirme |
|---|---|---|---|
| Basit ve aşamalı mimari | **Uyumlu** | Fazlara ayrılmış, ölçerek ilerleyen yapı | Anthropic, en basit çözümle başlanmasını ve karmaşıklığın yalnız ölçülmüş ihtiyaçla eklenmesini önerir: [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents). |
| Yapılandırılmış çıktı | **Uyumlu** | `yanit` ve kanıtlı `iddialar` şeması, çıktı kapısı | OpenAI şema kısıtlarının veri akışını daralttığını; araç çağrısı ile kullanıcıya yapılandırılmış yanıtın ayrılmasını önerir: [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs), [Function calling](https://developers.openai.com/api/docs/guides/function-calling). |
| Yetki ve onay sınırı | **Çelişki** | “Mimar ajan tam yetkili” | Yetki, genel hedefle ilişkili olmak değil, kullanıcının açıkça amaçladığı eylemle sınırlı olmalıdır; geniş yetki blast radius'u büyütür: [Claude Code auto mode](https://www.anthropic.com/engineering/claude-code-auto-mode), [How we contain Claude](https://www.anthropic.com/engineering/how-we-contain-claude). |
| Güvenilmeyen veri / prompt injection | **Eksik** | Web, dosya, bellek ve araç çıktılarının talimat değil veri olduğu açık kural değil | OpenAI güvenilmeyen içeriğin ayrı tutulmasını, yapılandırılmış akış ve onayları; Anthropic dış içeriğin güvenilmeyen kabulünü önerir: [Safety in building agents](https://developers.openai.com/api/docs/guides/agent-builder-safety), [How we contain Claude](https://www.anthropic.com/engineering/how-we-contain-claude). |
| Eval tasarımı | **Kısmi** | Soru bankası, baseline, regresyon var; çoklu deneme, outcome grader ve insan kalibrasyonu açık değil | Eval; temsilî normal/uç/saldırgan örnekler, çoklu denemeler, sonuç durumu ve kod+model+insan grader birleşimi içermelidir: [Evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices), [Demystifying evals](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents). |
| Trace / gözlemlenebilirlik | **Eksik** | İlişkili `run_id`/`call_id`, karar izi ve maskelenmiş trace sözleşmesi yok | Trace; model, araç, guardrail ve handoff akışını birlikte göstermeli, regresyon veri setine dönüşebilmelidir: [Agent evals](https://developers.openai.com/api/docs/guides/agent-evals), [Observability](https://developers.openai.com/api/docs/guides/agents/integrations-observability). |
| Model sürümü davranışı | **Kısmi** | Model A/B ve varsayılan değiştirme var; snapshot pinleme ve sürüm kaydı açık değil | Model snapshot'ları arasında davranış değişebilir; sürüm sabitlenmeli ve değişiklik eval kapısından geçmelidir: [API backwards compatibility](https://developers.openai.com/api/reference/overview#backwards-compatibility). |
| Veri saklama ve dışa çıkış | **Eksik** | Yerel yaklaşım var; sağlayıcı saklama/abuse monitoring/üçüncü taraf profili yok | API verisinin eğitimde kullanılmaması, hiç saklanmadığı anlamına gelmez; varsayılan abuse monitoring ve ürün bazlı uygulama durumu ayrı değerlendirilmelidir: [OpenAI data controls](https://developers.openai.com/api/docs/guides/your-data). |
| Bağlam ve maliyet verimliliği | **Eksik** | Token/bağlam bütçesi, JIT erişim, özetleme ve cache düzeni planda tanımlı değil | En küçük yüksek-sinyalli bağlam, gerektiğinde erişim ve uzun görevlerde compaction/notes önerilir: [Context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents). Sabit önek ve dinamik içeriğin sona alınması cache'i iyileştirir: [Prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching). |
| Uzun görev ve geri kazanım | **Kısmi** | Yedek/geri yükleme ve faz kapıları var; oturumlar arası yapılandırılmış devir yok | Uzun görevler küçük artımlara, temiz checkpoint'e, dışarıda tutulan ilerleme kaydına ve uçtan uca doğrulamaya ihtiyaç duyar: [Long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents). |

## 4. `ANAPLAN-SONRASI-PROFESYONEL-MIMARI.md` uyum matrisi

| Alan | Durum | Belgede görülen | Resmî dayanak / değerlendirme |
|---|---|---|---|
| Basit mimari ve sorumluluk ayrımı | **Uyumlu** | Yerel modüler monolit; orchestrator/model/tool/policy ayrımı | Basit, birleşebilir bileşenler ve görünür kontrol akışı yaklaşımıyla uyumlu: [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents). |
| Araç sözleşmesi ve yürütme zinciri | **Uyumlu** | Proposal → schema → policy → approval → execute → verify → report; etki sınıfı ve idempotency | Açık amaç, ayrık parametreler, strict veri modelleri ve eval ile araç iyileştirme yaklaşımıyla uyumlu: [Writing tools for agents](https://www.anthropic.com/engineering/writing-tools-for-agents), [Function calling](https://developers.openai.com/api/docs/guides/function-calling). |
| En az yetki ve kullanıcı niyeti | **Uyumlu** | Hedefe bağlı kısa ömürlü onay, kayıtlı araçlar, serbest shell yok | Dar yetki, eylem etkisine göre sınıflandırma ve kullanıcı niyetine bağlı authorization ilkeleriyle uyumlu: [Claude Code auto mode](https://www.anthropic.com/engineering/claude-code-auto-mode). |
| Güvenilmeyen veri / prompt injection | **Kısmi** | Web/dosya/bellek “veri” kabul ediliyor; fakat riskli işlemler için sert ağ+dosya sınırı açık değil | Model/prompt katmanı tek başına yeterli değildir; güvenilmeyen içerik için üst üste savunma ve blast-radius sınırı gerekir: [Safety in building agents](https://developers.openai.com/api/docs/guides/agent-builder-safety), [How we contain Claude](https://www.anthropic.com/engineering/how-we-contain-claude). |
| Yapılandırılmış çıktı uç durumları | **Kısmi** | Şema doğrulama var; ret, yarım yanıt ve token sınırı davranışı eksik | Yapılandırılmış çıktıda refusal ve incomplete durumları ayrıca ele alınmalıdır: [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs). |
| Eval yöntemi | **Uyumlu** | Regresyon/capability/security/resilience, 5 deneme, outcome grading, sıfır kritik olay | Değişkenlik nedeniyle çoklu deneme, final environment state, farklı grader türleri ve sürekli eval yaklaşımıyla uyumlu: [Demystifying evals](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents), [Evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices). |
| Trace / gözlemlenebilirlik | **Uyumlu** | `run_id`, `call_id`, `conversation_id`, trace ve SLO | Uçtan uca akış, araçlar, guardrail'ler, handoff ve custom span görünürlüğüyle uyumlu: [Observability](https://developers.openai.com/api/docs/guides/agents/integrations-observability). |
| Model ve sürüm değişimi | **Uyumlu** | Pinlenmiş model, replay/shadow/canary/rollback | Model davranış değişikliğini sabit sürüm ve eval ile yönetme önerisiyle uyumlu: [API backwards compatibility](https://developers.openai.com/api/reference/overview#backwards-compatibility). |
| Veri yaşam döngüsü | **Kısmi** | Veri sınıfları ve outbound policy var; sağlayıcı/özellik bazlı saklama kartı yok | Saklama; abuse monitoring, application state, ZDR uygunluğu ve üçüncü taraflar açısından özellik bazında doğrulanmalıdır: [OpenAI data controls](https://developers.openai.com/api/docs/guides/your-data). |
| Bağlam verimliliği | **Kısmi** | Context builder ve bütçe var; JIT, compaction, yapılandırılmış handoff ve carry-over regresyonu net değil | Küçük yüksek-sinyalli bağlam, progressive disclosure, compaction ve yapılandırılmış not önerilir: [Context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents). |
| Uzun görev harness'i | **Kısmi** | Durum makinesi ve checkpoint temeli var; oturumlar arası devir sözleşmesi ve temiz yeniden başlatma testi eksik | Yalnız compaction yeterli değildir; açık görev listesi, ilerleme dosyası, temiz durum ve uçtan uca test gerekir: [Long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents). |
| Kurtarma / rollback | **Uyumlu** | Migration, backup/restore, canary ve rollback var | Hata etkisini sınırlandıran çok katmanlı savunma yaklaşımıyla uyumlu: [How we contain Claude](https://www.anthropic.com/engineering/how-we-contain-claude). |
| Kaynak hijyeni | **Çelişki** | Plan, bu kalite standardının izin verdiği alanlar dışındaki kaynaklara ve `openai.com/business` sayfasına dayanıyor | İçerik mutlaka yanlış değildir; ancak bu çalışmada tanımlanan resmî-kaynak politikasıyla biçimsel olarak çelişir. İlgili maddeler [OpenAI agent safety](https://developers.openai.com/api/docs/guides/agent-builder-safety) ve yukarıdaki Anthropic mühendislik kaynaklarıyla yeniden dayandırılmalıdır. |

## 5. Öncelikli açıklar

| Öncelik | Açık | Risk / kanıt | Gerekli kapanış |
|---|---|---|---|
| **P0** | İlk plandaki “tam yetki” | Geniş yetki, kullanıcı niyeti dışına taşma ve blast radius riskidir: [Auto mode](https://www.anthropic.com/engineering/claude-code-auto-mode). | Yetkiyi görev, hedef, araç, yol ve süreyle sınırla; modelin kendi yetkisini genişletmesini yasakla. |
| **P0** | Gerçek containment eksikliği | Prompt veya sınıflandırıcı tek başına hatasız değildir; ağ ve dosya sınırları birlikte gerekir: [Sandboxing](https://www.anthropic.com/engineering/claude-code-sandboxing), [Containment](https://www.anthropic.com/engineering/how-we-contain-claude). | Riskli yürütücüyü workspace yazma sınırı, ağ allowlist/egress broker, secret ayrımı ve süreç sınırıyla çalıştır. |
| **P0** | Sağlayıcı veri kartı yok | “Eğitimde kullanılmıyor” ile “saklanmıyor” aynı değildir: [OpenAI data controls](https://developers.openai.com/api/docs/guides/your-data). | Her model/özellik için gönderilen veri, `store`, saklama, abuse monitoring, ZDR uygunluğu, üçüncü taraf ve doğrulama tarihi kaydet. |
| **P0** | Yapısal güvenlik kapıları iki planda ortak norm değil | Yapılandırılmış çıktı riski azaltır ama ortadan kaldırmaz: [OpenAI agent safety](https://developers.openai.com/api/docs/guides/agent-builder-safety). | Şema + politika + gerekirse hedefe bağlı onay + yürütme + nihai durum doğrulaması zincirini değişmez kural yap. |
| **P1** | Eval harness sağlayıcı bağımsız değil | Eval; yaşayan ve sürekli bir süreç olmalıdır: [OpenAI eval best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices), [Anthropic evals](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents). | Yerel veri seti/runner/sonuç formatı kullan; hosted eval ürününü temel bağımlılık yapma. |
| **P1** | Bağlam devri yetersiz | Uzun görevlerde bağlam kirliliği ve karar kaybı oluşur: [Context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents). | JIT erişim, yapılandırılmış özet, kararlar/açıklar/sonraki adım şeması ve devir regresyon testi ekle. |
| **P1** | Yapılandırılmış çıktı hata sözleşmesi eksik | Şema uyumu, refusal/incomplete durumunu ortadan kaldırmaz: [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs). | `ok/refusal/incomplete/invalid` durumları; tek kontrollü retry; sonra güvenli durdurma veya kanıtlı fallback tanımla. |
| **P1** | Onay yorgunluğu ile güvenlik dengesi açık değil | Çok onay kullanıcıyı otomatik onaya iter; containment gereksiz istemleri azaltır: [Sandboxing](https://www.anthropic.com/engineering/claude-code-sandboxing). | Güvenli salt-okunur, sınırlı geri alınabilir yazma ve kritik/dış etki olmak üzere üç onay katmanı tanımla. |
| **P1** | Trace gizliliği sözleşmesi ayrıntısız | Trace faydalıdır ancak prompt/çıktı/araç argümanı kişisel veri içerebilir: [Observability](https://developers.openai.com/api/docs/guides/agents/integrations-observability). | Alan bazlı maskeleme, saklama süresi, erişim, silme ve raw içerik kapatma seçenekleri ekle. |
| **P2** | Sabit test sayısı | Test sayısı değiştikçe başarı ifadesi bayatlar. | “DURUM/CI tarafından listelenen güncel testlerin tamamı” ifadesini kullan. |
| **P2** | İkinci planda `RPO ≤24s` yazımı | Belgenin önceki `RPO ≤ 24 saat` hedefiyle tutarsızdır; muhtemel yazım hatasıdır. | Plan sahibi doğruladıktan sonra `RPO ≤ 24 saat` olarak düzelt. |
| **P2** | Kaynak politikası ve eskime takibi | Resmî sayfalar ve ürünler zamanla değişebilir. | Kaynak URL'si, erişim tarihi, planı etkileyen iddia ve deprecation notu için kaynak kayıt tablosu tut. |

## 6. Planlara önerilen net metin değişiklikleri

Bu bölüm öneri metnidir; iki plan dosyası değiştirilmemiştir.

### 6.1 `ANA-PLAN.md` için

**“Tam yetki” ifadesinin yerine:**

> Mimar ajan yalnız Casper'in açıkça verdiği görev kapsamı içinde yetkilidir. Salt-okunur inceleme değişiklik yetkisi vermez. Yazma, dış sistem etkisi, hassas veri gönderimi, geri döndürülemez işlem ve kapsam genişlemesi ayrı yetki sınıflarıdır. Model kendi yetkisini veremez, genişletemez veya başka ajana devredemez.

**Her faz için ortak çıkış kapısı olarak:**

> Faz ancak güncel CI/DURUM listesindeki tüm ilgili testler geçtiğinde; temsilî normal, uç ve saldırgan vakalarda en az 5 denemede ölçüm yapıldığında; kritik yetkisiz eylem, sır sızıntısı, veri kaybı ve yanlış başarı bildirimi sıfır olduğunda; sürüm ve trace kaydı üretildiğinde; geri dönüş adımı temiz profilde denendiğinde kapanır. Başarısızlıkta önceki kararlı sürüm varsayılan kalır.

**Faz 0'a eklenecek maddeler:**

> - Sağlayıcı veri kartı: model/snapshot, gönderilen alanlar, `store`, saklama süresi, abuse monitoring, ZDR uygunluğu, üçüncü taraf, doğrulama tarihi.  
> - İz sözleşmesi: `conversation_id`, `run_id`, `call_id`, model/prompt/araç/politika sürümü; kişisel veri maskeleme ve saklama süresi.  
> - Eval seti: normal/uç/saldırgan örnekler, beklenen nihai durum, çoklu deneme, kod+model+insan grader ve insan kalibrasyonu.

**Faz 1'e eklenecek maddeler:**

> Yapılandırılmış sonuç `ok`, `refusal`, `incomplete` veya `invalid` durumlarından birini taşır. Sağlayıcının strict şema desteği yoksa çıktı yerelde parse+validate edilir; en fazla bir kontrollü düzeltme denemesi yapılır; yeniden başarısızlıkta eylem yürütülmez ve kullanıcıya açık hata verilir. Şemaya uymak, iddianın doğru olduğu anlamına gelmez; dayanak ve nihai durum ayrıca doğrulanır.

**Yeni “Araç ve izin sınırı” maddesi:**

> Web, belge, bellek ve araç çıktıları güvenilmeyen veridir; ayrıcalıklı talimat alanına taşınamaz. Model yalnız teklif üretir. Yalnız kayıtlı araçlar, o çağrı için izin verilen alt küme, strict argüman şeması ve politika sonucu ile çalışır. Kritik, dış etkili veya geri döndürülemez işlem hedef+etki önizlemeli, kısa ömürlü ve tek çağrılık kullanıcı onayı ister. Riskli araçlar dosya sistemi çalışma alanı ve ağ allowlist sınırında yürütülür.

**Faz 4'e eklenecek madde:**

> Model, prompt, şema, araç ve politika sürümleri birlikte pinlenir. Değişiklik; aynı eval setinde shadow/canary karşılaştırması, kalite eşiği ve doğrulanmış rollback olmadan varsayılan olamaz. Doğruluk hedefi karşılandıktan sonra token/gecikme/maliyet optimize edilir.

**Faz 5'e eklenecek madde:**

> Yedekleme varlığı değil, temiz profilde geri yükleme sonucu ölçülür. Paket güncellemesi side-by-side kurulur; önceki çalışır paket, migration uyumluluğu ve kullanıcı verisi geri dönüş yolu doğrulanmadan silinmez.

### 6.2 `ANAPLAN-SONRASI-PROFESYONEL-MIMARI.md` için

**Kaynak politikası:**

> Normatif AI sağlayıcı kaynakları yalnız resmî geliştirici/mühendislik belgeleridir. Her kaynak için URL, erişim tarihi, desteklediği karar ve deprecation durumu kayıt edilir. OpenAI ajan güvenliği maddeleri `developers.openai.com/.../agent-builder-safety`; Anthropic ajan, context, eval ve containment maddeleri `anthropic.com/engineering/...` kaynaklarıyla dayandırılır.

**Sağlayıcı veri kartı:**

> Her adapter şu yetenek/profil kartını yayımlar: model ve snapshot; strict schema/tool calling/stream/cancel desteği; gönderilen veri alanları; eğitim tercihi; abuse monitoring; application-state saklama süresi; `store` davranışı; ZDR/MAM uygunluğu; üçüncü taraf aktarımı; bölge; son doğrulama tarihi. “Local-first”, buluta veri gönderilmediği anlamında kullanılmaz; her cloud çağrısı görünür veri çıkışıdır.

**Containment ve onay katmanları:**

> - Seviye A: yetkili çalışma alanındaki güvenli salt-okunur işlemler otomatik olabilir.  
> - Seviye B: kullanıcının açık değişiklik talebi içindeki geri alınabilir yerel yazmalar, hedef sınırı ve checkpoint ile yürütülebilir.  
> - Seviye C: dış sistem, hassas veri, sistem geneli, mali işlem, silme veya geri döndürülemez etki; hedef+etki+veri önizlemeli tek çağrılık onay ister.  
> Riskli yürütücü workspace yazma sınırı, ağ allowlist/egress broker, secret ayrımı, timeout ve kaynak kotası içinde çalışır. Serbest shell/interpreter yetkisi verilemez.

**Bağlam ve uzun görev devri:**

> Context builder en küçük yüksek-sinyalli bağlamı seçer; büyük belgeleri kimlik/özet ile tanıtır ve ayrıntıyı gerektiğinde getirir. Her checkpoint'te yapılandırılmış handoff üretilir: `amac`, `tamamlanan`, `degisen_dosyalar`, `kararlar_ve_kanit`, `acik_riskler`, `sonraki_adim`, `geri_donus_noktasi`. Özetleme mimari kararları ve çözülmemiş hataları korur; temiz oturumdan devam testi eval setine eklenir. Gizli düşünce zinciri kaydedilmez; yalnız karar, kanıt ve gözlenebilir sonuç kaydedilir.

**Sağlayıcıdan bağımsız eval:**

> Eval veri seti, runner, trace ve sonuç formatı yerel ve sağlayıcıdan bağımsızdır. Hosted eval hizmeti kolaylık olabilir, zorunlu bağımlılık olamaz. Aynı görev tanımı ve nihai-durum grader'ı bütün sağlayıcılara uygulanır; modelin aynı araç yolunu izlemesi değil doğru ve güvenli sonuç ölçülür.

**Ortak faz kapısı:**

> Değişiklik; tipik/uç/saldırgan vakalar, en az 5 deneme, nihai durum grader'ı, trace örneklemesi, kişisel veri maskesi, pinned sürümler, canary ve temiz ortam rollback kanıtı olmadan kararlı kanala geçemez. Kritik olaylardan herhangi biri görülürse oranına bakılmaksızın kapı kapanır.

**Muhtemel belge düzeltmesi:** Faz 11'deki `RPO ≤24s`, 9. bölümdeki `RPO ≤ 24 saat` hedefiyle tutarsızdır. Plan sahibi doğruladıktan sonra `RPO ≤ 24 saat` yapılmalıdır.

## 7. Sağlayıcıdan bağımsız Ortak Çalışma Sözleşmesi

Bu sözleşme Başak.ai, Anthropic tabanlı ajanlar, OpenAI/Codex tabanlı ajanlar ve gelecekteki sağlayıcılar için aynı tabanı tanımlar.

1. **Kapsam ve yetki:** Ajan yalnız kullanıcının açık görevi içinde çalışır. İnceleme talebi yazma yetkisi değildir. Kapsam, hedef, araç, dosya yolu, veri ve süre bakımından dar yorumlanır.
2. **Yetki devredilemez:** Model yalnız önerir; politika motoru ve deterministik yürütücü karar verir. Model kendi yetkisini veya araç kümesini genişletemez. Desteklenmeyen yetenek varmış gibi varsayılamaz.
3. **Güvenilmeyen veri ayrımı:** Web, e-posta, dosya, bellek, kullanıcıdan alıntı ve araç çıktısı veri kabul edilir; sistem/developer talimatına dönüşemez. Ayrıcalıklı alana kontrolsüz eklenemez.
4. **Araç sözleşmesi:** Her araç açık amaç, strict giriş/çıkış şeması, etki sınıfı, hedef sınırı, `call_id`, idempotency, timeout/retry sınırı ve nihai durum doğrulaması taşır. İzin verilen araç alt kümesi çağrı başında daraltılır.
5. **Onay:** Güvenli salt-okunur iş otomatik olabilir. Açık değişiklik isteği içindeki geri alınabilir yerel yazma checkpoint'le sınırlanır. Dış, hassas, sistem-geneli, yıkıcı veya geri döndürülemez eylem; hedef, veri ve etkiyi gösteren tek çağrılık onay ister. Genel ve süresiz onay geçersizdir.
6. **Containment:** Riskli işler yalnız yetkili çalışma alanında yazabilir; ağ çıkışı allowlist/egress broker ile sınırlandırılır; sırlar ayrı tutulur. Shell, interpreter veya süreç başlatma yetkisi yüzey adına göre değil gerçek etkisine göre değerlendirilir.
7. **Veri ve bulut:** Varsayılan yereldir. Buluta yalnız görev için gereken en az veri, mümkünse maskelenerek gönderilir. Sağlayıcı veri kartı güncel değilse hassas veri gönderilmez. “Eğitimde kullanılmıyor” ifadesi “saklanmıyor” anlamına gelmez.
8. **Bağlam:** En küçük yeterli ve yüksek-sinyalli bağlam kullanılır. Ayrıntı gerektiğinde getirilir. Uzun görevler checkpoint, yapılandırılmış not ve handoff ile sürdürülür. Gizli düşünce zinciri istenmez veya saklanmaz; karar özeti, dayanak ve sonuç kaydedilir.
9. **Doğruluk ve başarı bildirimi:** İddia; gözlem, dosya, araç çağrısı veya “dayanak yok” ile işaretlenir. Eylem kabul edildi diye başarılı sayılmaz; nihai sistem/dosya durumu doğrulanmadan başarı bildirilmez. Bilinmeyen açıkça bilinmeyen olarak kalır.
10. **Eval ve değişiklik:** Her davranış değişikliği temsilî normal, uç ve saldırgan örneklerde; değişkenlik olan yerde çoklu denemeyle ölçülür. Kod, model ve insan grader'ları uygun yerde birlikte kullanılır. Model/prompt/şema/araç/politika sürümü birlikte kayıt ve pin edilir.
11. **Gözlemlenebilirlik:** Her koşuda `conversation_id`, `run_id`, `call_id`, sürümler, politika/onay kararı, araç sonucu, hata, token ve gecikme kaydedilir. Hassas alanlar loglanmadan önce maskelenir; erişim, saklama ve silme süresi bellidir.
12. **Dağıtım ve kurtarma:** Değişiklik önce replay/shadow, sonra sınırlı canary görür. Eski kararlı sürüm ve veri geri dönüş yolu korunur. Rollback ve restore temiz profilde düzenli denenir.
13. **Durdurma:** Kullanıcı iptali derhal işlenir. Denial, retry, timeout, araç zinciri ve bütçe sınırı vardır. Kritik doğrulama yapılamazsa fail-closed uygulanır; üç tekrarlı ret/hata sonrası ajan durur ve kullanıcıya döner.
14. **Sağlayıcı eşdeğerliği varsayılmaz:** Her adapter gerçek yeteneklerini bildirir. Strict çıktı yoksa yerel validate + en fazla bir düzeltme + güvenli durma uygulanır. Aynı sonuç, güvenlik ve veri kapıları bütün sağlayıcılara uygulanır.

## 8. Hedef kalite statüsü ve ölçülebilir geçiş kapıları

Önerilen nihai ad: **Başak.ai — Koşullu, Kanıtlı Kişisel Ajan v1**.

| Kapı | Statü | Ölçülebilir geçiş koşulları |
|---|---|---|
| **G0** | Belgelenmiş prototip | Mimari, risk envanteri, yetki sınıfları, sağlayıcı veri kartı şeması ve baseline eval yazılıdır. Sabit test sayısı kullanılmaz. |
| **G1** | Yapısal beta | Güncel ilgili testlerin %100'ü geçer; strict şema/politika/sonuç doğrulama zinciri zorunludur; normal+uç+saldırgan set her modelde en az 5 kez çalışır; yetkisiz eylem, sır sızıntısı, veri kaybı, yanlış başarı = **0**; temiz profilde restore geçer. |
| **G2** | Kontrollü kişisel beta | Riskli araçlarda dosya+ağ containment kanıtlıdır; en az 50 saldırgan görev × 5 deneme; trace kapsama ≥%99; sağlayıcı veri kartları günceldir; model/prompt/araç/politika pinlidir; canary ve otomatik/tek-adım rollback tatbikatı geçer. |
| **G3** | Koşullu, kanıtlı kişisel v1 | En az 30 gün ve 200 gerçek kullanım koşusu; desteklenen görevlerde doğrulanmış başarı ≥%95; kritik olay = **0**; kullanıcı iptal başarısı %100; belirlenen p95 gecikme/token bütçesi aşılmaz; `RPO ≤24 saat`, `RTO ≤15 dakika`; iki ardışık sürüm geçişi kritik rollback olmadan tamamlanır; Casper canlı kabul verir. |

Ek kurallar:

- Bir kritik güvenlik olayı oranına bakılmaksızın kapıyı kapatır.
- Performans optimizasyonu kalite hedefi sağlandıktan sonra yapılır. OpenAI da önce doğruluk hedefi ve eval seti, sonra maliyet/gecikme optimizasyonu önerir: [Model selection](https://developers.openai.com/api/docs/guides/model-selection), [Latency optimization](https://developers.openai.com/api/docs/guides/latency-optimization).
- Geçmişte sıfır olay görülmesi gelecekte sıfır olay garantisi değildir; yalnız tanımlı test dağılımındaki kanıttır.

## 9. “Garanti” ne anlama gelmeli?

Bir üretken model için mutlak doğruluk veya mutlak güvenlik garantisi dürüstçe verilemez. OpenAI, ajanların hâlâ hata yapabildiğini ve prompt injection ile kandırılabildiğini belirtir: [Agent safety](https://developers.openai.com/api/docs/guides/agent-builder-safety). Anthropic de model katmanındaki savunmaların sıfır hata vermediğini, kalan riskin containment ve katmanlı savunmayla sınırlandırılması gerektiğini açıklar: [How we contain Claude](https://www.anthropic.com/engineering/how-we-contain-claude).

Başak için “garanti” üç ayrı anlamda kullanılmalıdır:

1. **Yapısal güvence:** Şema+politika geçmeden yürütücü çağrılamaz; model yetkisini genişletemez; kritik işlem hedefe bağlı onaysız çalışamaz; nihai durum görülmeden başarı yazılamaz.
2. **Ölçülmüş güven:** Tanımlı veri seti ve kullanım dağılımında başarı, hata, kritik olay, token ve gecikme oranları sürüm sürüm yayınlanır. Bu, yalnız ölçülen kapsam için güven verir.
3. **Operasyonel güvence:** Hata olduğunda etki containment ile sınırlanır; trace ile neden bulunur; canary yayılımı durdurur; denenmiş rollback/restore önceki güvenli duruma döndürür.

Dolayısıyla doğru ifade şudur:

> Başak.ai için mutlak hatasızlık vaat edilmez. Yetki ve veri sınırları mimari olarak zorlanır; kalite tekrarlanabilir eval ve gerçek kullanım ölçümleriyle kanıtlanır; kalan risk containment, kullanıcı onayı, canary ve denenmiş rollback ile yönetilir.

## 10. Son karar

- `ANA-PLAN.md`: **G0'a yakın, G1 için revizyon gerekli.** Özellikle tam yetki kaldırılmadan ve ortak güvenlik/eval kapısı eklenmeden yapı-garantili beta sayılmamalıdır.
- `ANAPLAN-SONRASI-PROFESYONEL-MIMARI.md`: **G1 tasarımını büyük ölçüde karşılıyor; uygulama kanıtı sonrası G2 adayıdır.** Sağlayıcı veri kartı, gerçek containment, uzun görev handoff'u, structured-output hata durumları ve kaynak hijyeni tamamlanmalıdır.
- İki planın üzerinde bağlayıcı norm olarak **Ortak Çalışma Sözleşmesi** kullanılmalıdır. Sağlayıcılar işçi/adapter olarak değişebilir; yetki, veri, eval, trace, doğrulama ve rollback kapıları değişmemelidir.
