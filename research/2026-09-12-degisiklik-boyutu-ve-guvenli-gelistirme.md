# ARAŞTIRMA — Değişiklik boyutu ve güvenli geliştirme akışı

Tarih: 12 Eylül 2026
Durum: KANITLANDI — süreç kuralı düzeltmesi gerekli
Kapsam: Başak'ı AI ajanlarıyla geliştirirken değişiklik boyutu ve doğrulama akışı

## Araştırma sorusu

`ilgili araştırma → kanıt → kapsam sınırı → güvenli dal → küçük kod değişikliği → test/review/ölçüm → karşılaştırma → onay` sırası doğru mu? Özellikle `küçük kod değişikliği` ifadesi güvenli mi, yoksa gelişimi gereksiz biçimde kilitleyebilir mi?

## Kaynaklar

1. OpenAI — Harness engineering: leveraging Codex in an agent-first world
   https://openai.com/index/harness-engineering/
2. OpenAI — Codex in ChatGPT for Software Engineering teams
   https://openai.com/business/solutions/engineering/
3. GitHub Docs — About GitHub Copilot code review
   https://docs.github.com/en/copilot/concepts/agents/code-review
4. GitHub Docs — Application card: GitHub Copilot Agents
   https://docs.github.com/en/copilot/responsible-use/agents
5. Google Engineering Practices — Small CLs
   https://google.github.io/eng-practices/review/developer/small-cls.html
6. Google Engineering Practices — What to look for in a code review
   https://google.github.io/eng-practices/review/reviewer/looking-for.html
7. Google — Building Secure and Reliable Systems, Chapter 7
   https://google.github.io/building-secure-and-reliable-systems/raw/ch07.html

## Doğrulanan gerçekler

### 1. `Küçük` satır sayısı değildir

Google'ın resmi code-review rehberi doğru değişiklik boyutunu `one self-contained change` olarak tanımlar. Aynı rehber, değişikliğin aşırı küçültülüp etkisinin anlaşılmaz hale gelmemesi gerektiğini de açıkça söyler. İlgili testlerin aynı değişiklikle gelmesini ve her değişiklik sonrasında sistemin çalışır halde kalmasını ister.

Sonuç: güvenlik kuralı `az satır yaz` olamaz.

### 2. Karmaşık işler bazen daha büyük ama kontrollü değişiklik gerektirir

OpenAI Harness Engineering yazısı küçük işler için hafif planların, karmaşık işler için ise repo içinde izlenen execution planların kullanılmasını anlatır. Aynı yazı `invariants`ın mekanik olarak zorlanmasını, ancak implementasyonun mikro-yönetilmemesini önerir.

Sonuç: `her iş mutlaka küçük kod değişikliğine indirgenecek` kuralı doğru değildir.

### 3. Büyük iş güvenli biçimde aşamalara bölünebilir; ama her aşama kendi içinde tam olmalıdır

Google, büyük değişikliklerin birbiri üzerine kurulabilen self-contained değişikliklere bölünmesini önerir. Ancak her ara değişiklikten sonra build/sistem çalışır kalmalıdır. İlgisiz refactor ile feature/bug fix karıştırılmamalıdır.

Sonuç: hedef `mikro patch` değil, `çalışır ve doğrulanabilir ara aşama`dır.

### 4. Doğrulama değişikliğin riskine göre seçilmelidir

OpenAI; agentın uygulamayı çalıştırabilmesi, UI'ı tarayıcıyla kullanabilmesi, log/metric/trace okuyabilmesi ve kendi değişikliğini tekrar inceleyebilmesi gibi sensörleri kullanır. GitHub, AI code review'un tüm sorunları bulacağının garanti olmadığını ve insan/başka doğrulama yöntemleriyle desteklenmesi gerektiğini belirtir. Google da design, functionality, complexity ve testleri review'un parçası sayar.

Sonuç: tek bir `test geçti` kanıtı her değişiklik için yeterli değildir.

### 5. Güvenli geliştirme için izolasyon ve geri alınabilirlik önemlidir

Google'ın güvenli/reliable sistem rehberi değişikliklerin incremental, documented, tested ve isolated olmasını; gerekiyorsa staged rollout ve instrumentation kullanılmasını önerir. Bu `küçük satır` zorunluluğu değil, değişikliğin etkisinin izole ve gözlenebilir olmasıdır.

## Risk

`küçük kod değişikliği` ifadesi şu yanlış davranışları teşvik edebilir:

- doğru çözümü yapay olarak parçalamak,
- yarım mimari/yarım feature bırakmak,
- birbirine bağlı mikro patch'ler nedeniyle ara durumlarda sistemi bozmak,
- kök nedeni çözmek yerine yüzeysel lokal yamalar biriktirmek,
- sadece line-count küçük olsun diye gerekli test/migration/adapter değişikliklerini ayrı bırakmak,
- teknik borcu artıran patch zinciri üretmek.

Bu nedenle ifade bağlayıcı süreçten çıkarılmalıdır.

## Yeni doğru kavram

**SINIRLI VE KENDİ İÇİNDE TAM DEĞİŞİKLİK PAKETİ**

Bir değişiklik paketi:

- tek bir doğrulanmış hedefe hizmet eder,
- araştırmanın izin verdiği alanı aşmaz,
- kendi içinde çalışır durumda tamamlanır,
- ilgili test/ölçüm/entegrasyon kanıtını içerir,
- bağımsız review edilebilir,
- başarısız olursa geri alınabilir,
- ilgisiz refactor/özellik eklemez.

Boyut için sabit satır/dosya limiti yoktur.

Karmaşık değişiklik birden fazla pakete ayrılacaksa her paket çalışır ve doğrulanabilir ara durum üretmelidir. Sadece `küçük görünsün` diye işlevsel bütünlük parçalanmaz.

## Güncellenmiş güvenli akış

**hedef + kabul kriteri → mevcut durum ve ilgili araştırma → kanıt kararı → kapsam/risk sınıfı → güvenli dal/worktree → sınırlı ve kendi içinde tam değişiklik paketi → değişikliğe uygun test/sensör/review → baseline ve kabul kriteriyle karşılaştırma → regresyon varsa geri al/düzelt → kullanıcıya kanıtı göster → açık onay → merge**

## Risk sınıfı

Araştırma metni değişiklik başlamadan önce şu sınıflardan birini seçer:

- düşük: lokal bug/tek davranış
- orta: birden fazla modülün birlikte değişmesi / entegrasyon
- yüksek: mimari, veri modeli, auth, güvenlik, migration, provider routing, kalıcı veri, dış dünya etkisi

Risk yükseldikçe daha fazla sensör ve gerekirse aşamalı rollout gerekir. Risk sınıfı kod satırı sayısından türetilmez.

## Karar

**KANITLANDI — süreç kuralı düzeltilecek.**

`küçük kod değişikliği` ifadesi güvenli geliştirme kuralı olarak kullanılmayacak.

Yerine:

**`araştırmanın izin verdiği sınırlar içinde, tek amaçlı, kendi içinde tam, bağımsız doğrulanabilir ve geri alınabilir değişiklik paketi`**

kullanılacak.

Bu araştırma ürün davranışı değişikliği değildir; yalnız geliştirme güvenlik sözleşmesini düzeltir.
