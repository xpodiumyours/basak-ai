# Gelir modeli araştırması 2: API / Altyapı satışı (geliştiriciye satmak)

Tarih: 2026-09-25
**Bu bir araştırmadır, karar değildir.** Aşağıdaki bilgiler yalnızca resmî birincil kaynaklardan (platformların kendi sözleşme/fiyatlandırma/kullanım şartları sayfaları) derlenmiştir. Bir kanalın burada yer alması onun Başak için doğru veya uygulanabilir olduğu anlamına gelmez.

---

## 1. Özet tablo — API ve model pazaryerleri

| Kanal | Komisyon | Ödeme eşiği | Türkiye'den olur mu | Başlangıç maliyeti |
|---|---|---|---|---|
| RapidAPI | %25 (sabit, "flat 25% marketplace fee") | Belirtilmemiş (yalnız "$2 altındaki ödemeler başka ödemeyle birleştirilebilir" notu var) | Bulunamadı (ülke kısıtı açıkça yazılmamış) | Bulunamadı (listelenme ücreti belirtilmemiş) |
| Apify Store | %20 (satıcı %80 alır) | 20 USD (PayPal) / 100 USD (diğer yöntemler) | Bulunamadı (açık ülke listesi yok; KYC/yaptırım listesi kontrolü var) | Belirtilmemiş (yayınlama ücretine dair madde yok) |
| Zapier Integration Partner Program | Doğrudan gelir paylaşımı **bulunamadı** — program "dağıtım" (kullanıcıya erişim) sağlıyor, para akışı yok | Yok (ücret modeli yok) | Bulunamadı (kayıt ücretsiz, ülke kısıtı belirtilmemiş) | Ücretsiz ("no fees for joining any of Zapier's partner programs") |
| Zapier Solution/Affiliate Partner | Referans komisyonu var ama oranı resmî sayfada bulunamadı | Bulunamadı | Bulunamadı | Ücretsiz |
| Make.com Apps Marketplace | Komisyon oranı **bulunamadı** — resmî şartlar sayfası geliştiricinin bakım/sorumluluk yükümlülüklerini anlatıyor, ödeme yüzdesi yazmıyor | Bulunamadı | Bulunamadı | Bulunamadı (Beta Program, ücret maddesi yok) |
| n8n community node marketplace | Resmî bir gelir paylaşımı/komisyon mekanizması **bulunamadı** — bu resmî bir "sat" pazaryeri değil, npm üzerinden ücretsiz yayınlanan, n8n tarafından "doğrulanan" (verified) bir katalog | Yok | Herkese açık (npm üzerinden yayın; ülke kısıtı yok) | Ücretsiz (npm yayını) |
| OpenRouter (model sağlayıcı olarak listelenme) | Komisyon/ödeme oranı resmî sayfada **bulunamadı** — başvuru onaya tabi, "büyük bir başvuru birikimi var, öncelik kendi/özel modeli olan sağlayıcılarda" | Bulunamadı | Bulunamadı | Başvuru ücretsiz (openrouter.ai/providers/apply) |
| Hugging Face — Inference Providers (sağlayıcı olarak listelenme) | Şu an **komisyon/gelir paylaşımı yok** — HF sağlayıcı maliyetini olduğu gibi (markup'sız) yansıtıyor; ileride paylaşım anlaşması yapılabileceği belirtiliyor ama henüz yok | Yok | Bulunamadı | Bulunamadı |
| Hugging Face — Spaces (ücretli sunma) | Kendi ürününü satan bir "yaratıcı gelir paylaşımı" programı **bulunamadı**; Spaces donanım ücreti doğrudan kullanıcıdan/kredi kartından tahsil ediliyor, Space sahibine pay verilmiyor | — | — | — |
| Replicate (model yayınlama) | Resmî bir "yaratıcı geliri/revenue share" programı **bulunamadı** — dokümantasyon yalnız teknik yayınlama ve kullanıcı faturalandırmasını anlatıyor | Bulunamadı | Bulunamadı | Bulunamadı |

---

## Ücretsiz sağlayıcılarla ticari satış yapılabilir mi?

### Groq (GroqCloud API)

**Sonuç: YASAK** — üçüncü taraflara yeniden satış açıkça engellenmiş.

Groq Services Agreement (resmî sözleşme, GroqCloud/API kullanımını kapsıyor):

> "Customer may not resell or lease access to its Account." (Bölüm 3.2 — Accounts)

> "sell, resell, sublicense, transfer, or distribute any of the Cloud Services except as expressly approved by Groq" (Bölüm 6.3(c) — Restrictions)

Yalnızca Groq'un onayladığı resmî "yeniden satıcı" (reseller) sözleşmesi olan taraflar istisna — bu, Groq'la ayrı bir anlaşma gerektiriyor, bir geliştiricinin kendi API anahtarıyla tek taraflı yapabileceği bir şey değil (Bölüm 18 — Resold Customers).

Kaynak: [Groq Services Agreement](https://console.groq.com/docs/legal/services-agreement)

Not: `groq.com/terms-of-use` sayfası (genel web sitesi kullanım şartları) da benzer şekilde "personal, non-commercial use only" diyor ama bu sayfa GroqCloud API'sini kapsamıyor — kendisi şöyle diyor: "These Terms do not apply to you in connection with your use of Groq's cloud services... If you are interacting with Groq as a customer of our services, the Groq Services Agreement governs." Yani asıl bağlayıcı olan, yukarıdaki Services Agreement.

Kaynak: [Groq Terms of Use](https://groq.com/terms-of-use)

---

### Google Gemini API ücretsiz katman (Google AI Studio / unpaid quota)

**Sonuç: BELİRSİZ / muhtemelen izinli, ama ciddi bir veri kullanımı riski var.**

Gemini API Additional Terms of Service'in tamamında "resell" (yeniden sat) kelimesi yalnızca iki yerde geçiyor ve ikisi de genel API kullanımını değil, özel iki alt özelliği kapsıyor:

> "You will not, and will not allow your end user or any third party to, cache, frame, syndicate, resell, analyze, train on, or otherwise learn from Grounded Results or Search Suggestions." (Grounding with Google Search — Use Restrictions bölümü)

Bu madde yalnızca "Grounding with Google Search" ve "Grounding with Google Maps" özelliklerinin çıktılarını kapsıyor. Genel metin üretimi (chat/completion) için ayrı bir "yeniden satış yasak" maddesi **bulunamadı**.

Ücretsiz katman tanımı:

> "Any Services that are offered free of charge like direct interactions with Google AI Studio or unpaid quota in Gemini API are unpaid Services."

Kullanım amacı:

> "Use of Google AI Studio and Gemini API is for developers building with Google AI models for professional or business purposes, not for consumer use."

**En kritik kısım — veri kullanımı (gizlilik/güven riski, yasak değil ama önemli):**

> "When you use Unpaid Services, including, for example, Google AI Studio and the unpaid quota on Gemini API, Google uses the content you submit to the Services and any generated responses to provide, improve, and develop Google products and services and machine learning technologies."

> "To help with quality and improve our products, human reviewers may read, annotate, and process your API input and output."

Yani: genel ticari kullanım açıkça yasaklanmamış görünüyor, ama ücretsiz katımda gönderilen her şey (kullanıcı mesajları dahil) Google tarafından ürün geliştirme amacıyla kullanılabiliyor ve insan gözden geçiriciler tarafından okunabiliyor. Bu, Başak üzerinden geçen kullanıcı verileri için önemli bir gizlilik sorunu olabilir — resmî olarak "yasak" değil ama "güvenli/gizli" de değil.

Kaynak: [Gemini API Additional Terms of Service](https://ai.google.dev/gemini-api/terms)

---

### OpenRouter ücretsiz modeller (":free" etiketli)

**Sonuç: YASAK** (yeniden satış açısından) — OpenRouter'ın kendi şartları erişimi yeniden satmayı yasaklıyor; ayrıca her modelin kendi sağlayıcı şartlarına da uyulması zorunlu.

OpenRouter Terms of Service:

> "access the Site or Service for purposes of reselling API access to Models or otherwise developing a competing service" — Bölüm 7(4), yasaklanan davranışlar arasında sayılmış.

Model bazlı ek şartlara uyma zorunluluğu:

> "you agree, and will ensure that your Authorized Users and customers agree, to comply with the applicable terms for each Model ('Model Terms')" — Bölüm 5.1

Kaynak: [OpenRouter Terms of Service](https://openrouter.ai/terms)

**Model sağlayıcı ek şartı örneği — Meta Llama:** OpenRouter'daki birçok ücretsiz model (ör. Llama tabanlı olanlar) Meta'nın kendi lisansına tabi. Llama Community License ticari kullanıma izin veriyor ama bir eşik koyuyor:

> Lisansı alan tarafın (veya bağlı kuruluşlarının) ürün/hizmetlerinin önceki takvim ayında 700 milyon aylık aktif kullanıcıyı (MAU) aşması durumunda Meta'dan ayrı bir lisans istenmesi gerekiyor.

Kaynak: [Meta Llama 3 License](https://www.llama.com/llama3/license/) / [Llama 3.3 Community License Agreement](https://www.llama.com/llama3_3/license/)

Başak'ın ölçeği (tek geliştirici, sıfır sermaye) için 700M MAU eşiği pratikte alakasız — ama OpenRouter'ın kendi "yeniden satış yasak" maddesi (Bölüm 7.4) doğrudan alakalı: Başak'ın çekirdek modeli olarak OpenRouter'ın ücretsiz modellerini kullanıp bunu ayrı bir ürün olarak (API erişimi şeklinde) üçüncü taraflara satmak bu maddeye takılabilir. Kendi ürününün İÇİNDE (son kullanıcıya konuşma asistanı olarak) kullanmak farklı bir şey — ama bu, "API erişimini yeniden satmak" ile "modelin çıktısını kullanan bir uygulama satmak" arasındaki ayrım net biçimde yazılmamış; resmî metinde bu ayrımı netleştiren ek bir cümle bulunamadı.

---

### Cloudflare Workers AI (ücretsiz katman / free allocation)

**Sonuç: BELİRSİZ — açık bir yasak bulunamadı.**

Cloudflare Developer Platform Service-Specific Terms belgesinde (Workers, Workers AI, AI Gateway dahil) yeniden satışı veya ücretsiz katmanın üzerine ücretli ürün kurmayı açıkça yasaklayan bir madde **bulunamadı**. Belgede yer alan ilgili maddeler:

> "Cloudflare has the right to make, use, develop, acquire, license, market, promote, or distribute products, software, or technologies that perform the same or similar functions as, or otherwise compete with your products..." (Bölüm 9 — rekabetçi ürün hakkı, ama bu Cloudflare'in kendi hakkı, kullanıcıya yasak koymuyor)

> "You may use Workers for Platforms to make available certain Workers functionality for use by your End Users..." (Bölüm 10 — Workers for Platforms özelinde son kullanıcıya sunum açıkça izinli)

Ücretsiz katman tanımı (ayrı sayfa):

> "Our free allocation allows anyone to use a total of 10,000 Neurons per day at no charge."

Bu sayfada da ticari kullanımı kısıtlayan bir not yok.

**Önemli ek nokta:** Workers AI üzerinden çalıştırılan modeller (Llama, Mistral vb.) Cloudflare'in kendi modelleri değil, üçüncü taraf modeller sayılıyor ve o modellerin kendi lisans şartlarına tabi:

> "The models constitute Third-Party Services and may be subject to open source or other license terms that apply between you and the model provider, and you should review the license terms applicable to each model."

Yani Cloudflare tarafı açık bir yasak koymamış, ama üzerinde çalışan model kendi lisansını (ör. yine Llama → 700M MAU eşiği) getiriyor.

Kaynaklar: [Cloudflare Service-Specific Terms — Developer Platform](https://www.cloudflare.com/service-specific-terms-developer-platform/), [Cloudflare Workers AI — Your Data and Workers AI](https://developers.cloudflare.com/workers-ai/platform/data-usage/), [Cloudflare Workers AI Pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/)

Not: Cloudflare'in genel "Self-Serve Subscription Agreement" (ana sözleşme) ayrıca kontrol edilmedi — Service-Specific Terms bunu referans veriyor ama tam metni bu araştırmada okunmadı. Bu bir eksik — aşağıda "Ulaşılamayan" bölümünde işaretlendi.

---

### Cohere Trial key

**Sonuç: YASAK** — trial key açıkça production/ticari kullanım için yasaklanmış.

Cohere resmî fiyatlandırma sayfası:

> "API calls made from a Trial API key are free. However, trial keys are rate limited and are not permitted to be used for production or commercial purposes."

Kaynak: [Cohere Pricing](https://cohere.com/pricing)

Ticari/production kullanım için Cohere ayrı bir "Production key" istiyor ve bu, kullanım başına ücretlendiriliyor (pay-as-you-go) — yani "ücretsiz" olan trial key zaten ticari kullanım için tasarlanmamış, bir sınama/prototip anahtarı.

Kaynak: [Cohere — Going Live](https://docs.cohere.com/docs/going-live)

---

## Özet — ücretsiz sağlayıcı ticari kullanım tablosu

| Sağlayıcı | Sonuç | Dayanak |
|---|---|---|
| Groq (GroqCloud) | **YASAK** | Services Agreement §3.2, §6.3(c): yeniden satış / erişim kiralama yasak |
| Google Gemini API ücretsiz katman | **BELİRSİZ** (genel yasak yok, ama veri Google tarafından kullanılıyor + insan gözden geçiriyor) | Additional ToS — "resell" yalnız Grounding/Maps özelinde geçiyor; genel kullanım metni yasaklamıyor |
| OpenRouter ücretsiz modeller | **YASAK** (API erişimini yeniden satma açısından) | ToS §7(4): "reselling API access to Models" yasak + her modelin kendi lisansına uyma zorunluluğu (§5.1) |
| Cloudflare Workers AI ücretsiz katman | **BELİRSİZ** (açık yasak bulunamadı, ama üstteki model lisansları kendi kısıtını getirebilir) | Developer Platform Service-Specific Terms'de resale yasağı bulunamadı |
| Cohere Trial key | **YASAK** | Resmî pricing sayfası: "not permitted to be used for production or commercial purposes" |

---

## 2. MCP / eklenti ekosistemi — resmî ücretli pazaryeri var mı?

**Sonuç: Resmî, ücretli bir MCP pazaryeri/ödeme yolu bulunamadı.**

Anthropic'in de destekçisi olduğu **resmî MCP Registry** (modelcontextprotocol.io) yalnızca bir **metadata kataloğu** — para akışı, komisyon veya ödeme mekanizması içermiyor:

> "The MCP Registry is the official centralized metadata repository for publicly accessible MCP servers, backed by major trusted contributors to the MCP ecosystem such as Anthropic, GitHub, PulseMCP, and Microsoft."

> "The MCP Registry provides: A single place for server creators to publish metadata about their servers... A REST API for MCP clients and aggregators to discover available servers..."

Registry, sunucunun kendi kodunu barındırmıyor, yalnızca nerede bulunduğuna dair bilgiyi (npm paketi, Docker image, uzak sunucu URL'si) tutuyor. Ücretlendirme, komisyon veya "satış" kavramı bu resmî belgede hiç geçmiyor.

Kaynak: [The MCP Registry — resmî döküman](https://modelcontextprotocol.io/registry/about)

**Smithery** üçüncü taraf bir MCP dizini/barındırma servisi — resmî Anthropic kanalı değil. Kendi pricing sayfası (smithery.ai/pricing) WebFetch ile denendi ama sayfa içeriği (muhtemelen JavaScript ile yüklendiği için) çekilemedi; yalnızca "Smithery is now a part of Arcade.dev" duyurusu ve navigasyon görüldü, fiyatlandırma/komisyon detaylarına ulaşılamadı. Bu nedenle Smithery'nin geliştiriciye ödeme yapıp yapmadığı bu araştırmada **doğrulanamadı** — ikinci elden (blog) kaynaklarda "geliştiriciye gelir paylaşımı yok, aksine listelenmek için geliştirici Smithery'ye ücret ödüyor" iddiası var, ama görev kuralı gereği blog kaynağı kullanılmadığı için bu satıra girmedi, yalnızca not olarak düşülüyor.

**Sonuç:** Şu an MCP sunucusu satmak için resmî/birincil bir ödeme/komisyon altyapısı yok. Bir MCP sunucusunu "satmak" isteyen geliştirici bunu kendi API anahtarı/abonelik sistemiyle kendisi kurmak zorunda — hazır bir pazaryeri değil.

---

## 3. Ayrıntılar — API pazaryerleri

### RapidAPI
- Komisyon: **%25 sabit** — "Rapid takes a flat 25% marketplace fee on all payments made through the API Hub." Örnek: 100 USD'lik bir plan için sağlayıcı 75 USD alır.
- Ödeme yöntemi: **Yalnızca PayPal** — "Rapid currently only pays out API providers via PayPal."
- Ödeme eşiği: Belirtilmemiş; yalnızca "2 USD altındaki ödemeler başka bir ödemeyle birleştirilebilir" notu var.
- Türkiye kısıtı: Bulunamadı — sayfada ülke bazlı bir kısıtlama maddesi yok (PayPal'ın kendi ülke kısıtları ayrı bir konu, RapidAPI'nin kendi sayfasında yazmıyor).
- Başlangıç ücreti: Bulunamadı.
- Kaynaklar: [Monetizing Your API on rapidapi.com](https://docs.rapidapi.com/docs/monetizing-your-api-on-rapidapicom), [Payouts and Finance](https://docs.rapidapi.com/docs/payouts-and-finance)

### Apify Store
- Komisyon: **%20** — "Your payout for a monetized Actor will be calculated as 80% of the fees paid by Users for your Actor, minus Platform usage costs" (Bölüm 10.2.1).
- Ödeme eşiği: **20 USD (PayPal) / 100 USD (diğer yöntemler)** — "The minimum amount payable is USD 20 for PayPal and USD 100 for any other payout option" (Bölüm 10.3.2). Eşiğin altındaki tutarlar bir sonraki aya devrediyor.
- Ödeme yöntemi: PayPal, banka transferi, Wise (KYC/kimlik doğrulama zorunlu).
- Türkiye kısıtı: Açık bir ülke listesi bulunamadı; yalnızca yaptırım/izleme listelerinde olmama şartı var (Bölüm 10.1.5).
- Başlangıç ücreti: Yok.
- Kaynak: [Apify Store Publishing Terms and Conditions](https://docs.apify.com/legal/store-publishing-terms-and-conditions)

### Zapier Partner Program
- Zapier üç ayrı program sunuyor: Integration Partner (kendi entegrasyonunu yayınla), Solution Partner (danışmanlık), Affiliate (referans linki).
- **Integration Partner Program'da doğrudan bir gelir paylaşımı/komisyon modeli bulunamadı** — program dört seviyeli (Bronze/Silver/Gold/Platinum) bir performans/destek kademelendirmesi, para akışı içermiyor.
- Maliyet: "no fees for joining any of Zapier's partner programs" — ücretsiz.
- Affiliate programında referans komisyonu var ama oranı resmî sayfada bulunamadı.
- Kaynak: [Zapier Partner Program — tier sistemi](https://docs.zapier.com/integrations/publish/partner-program), [Zapier Developer Platform Partner Program](https://zapier.com/developer-platform/partner-program)

### Make.com Apps Marketplace
- Resmî şartlar sayfası (developers.make.com/custom-apps-documentation/apps-marketplace/terms-and-conditions) geliştiricinin **sorumluluklarını** anlatıyor (bakım, üçüncü taraf talepleri karşısında savunma), ama **komisyon oranı, ödeme eşiği veya ödeme yöntemi belirtmiyor**.
- Marketplace "Beta Program" olarak tanımlanıyor: "a Beta Program for partners to publish their apps easily, monetize them as well as increase their brand awareness."
- "Monetize" kelimesi geçiyor ama nasıl/ne oranda olduğu bu belgede yazmıyor.
- Kaynak: [Make Apps Marketplace — Terms and Conditions](https://developers.make.com/custom-apps-documentation/apps-marketplace/terms-and-conditions)

### n8n community node marketplace
- n8n'in resmî, ücretli bir "sat" pazaryeri **bulunamadı**. Var olan sistem: geliştirici node'unu npm'e yayınlar, n8n bunu keşfeder ve belirli teknik/dokümantasyon kriterlerini karşılarsa "doğrulanmış" (verified) olarak arayüzde listeler. Bu tamamen ücretsiz ve açık kaynak modelidir — para akışı yok.
- Resmî doküman ayrıca n8n'in kendi ücretli (enterprise) özellikleriyle rekabet eden node'ları reddetme hakkını saklı tutuyor.
- Kaynaklar: [Submit community nodes](https://docs.n8n.io/integrations/creating-nodes/deploy/submit-community-nodes/), [Community Node Verification Guidelines](https://docs.n8n.io/integrations/creating-nodes/build/reference/verification-guidelines/)

---

## Ayrıntılar — yapay zekâ modeli / ajan pazaryerleri

### OpenRouter'a sağlayıcı olarak listelenme
- Başvuru: [openrouter.ai/providers/apply](https://openrouter.ai/providers/apply) — ücretsiz başvuru, ama onaya tabi. "OpenRouter currently has a large backlog of provider applications while prioritizing providers with proprietary models."
- Komisyon/ödeme oranı resmî teknik dokümanda (openrouter.ai/docs/guides/community/for-providers) **bulunamadı** — sayfa yalnızca teknik entegrasyon (endpoint, fiyat bildirimi formatı, kapasite limitleri) anlatıyor, finansal koşulları içermiyor.
- Fatura: "Usage-based billing is handled via monthly invoicing, with token counts reconciled automatically" deniyor ama yüzde/oran yazmıyor.
- Kaynak: [OpenRouter — For Providers](https://openrouter.ai/docs/guides/community/for-providers)

### Hugging Face
- **Inference Providers** (kendi altyapını HF üzerinden sağlayıcı olarak sunmak): Şu an **komisyon yok, markup yok** — "For routed requests through the Hugging Face Hub, there's no additional markup from Hugging Face; they just pass through the provider costs directly." İleride gelir paylaşımı anlaşmaları yapılabileceği belirtiliyor ama şu an resmî olarak yok.
- **Spaces (ücretli sunma):** Space sahibinin kendi ürününü kullanıcıya "satmasını" sağlayan resmî bir gelir paylaşımı mekanizması bulunamadı. Spaces'in donanım maliyeti (ör. T4 GPU $0.50/saat) doğrudan Space'i çalıştıran hesaptan tahsil ediliyor — bu bir "host etme maliyeti", geliştiriciye ödeme değil.
- Kaynaklar: [Hugging Face — Inference Endpoints Pricing](https://huggingface.co/docs/inference-endpoints/en/pricing), [Hugging Face Inference Providers — Deep Infra örneği](https://huggingface.co/blog/inference-providers-deepinfra)

### Replicate
- Model yayınlama teknik olarak açık (herkes public model yayınlayabilir), ama **resmî bir "yaratıcı geliri" / revenue share programı bulunamadı**. Dokümantasyon yalnızca kullanıcı faturalandırmasını (donanım + süre bazlı) ve "Official Models" programını (Replicate'in kendi bakımını yaptığı, sabit fiyatlı modeller) anlatıyor — model sahibine ödeme yapılıp yapılmadığına dair hiçbir madde yok.
- Kaynaklar: [Replicate — Official Models](https://replicate.com/docs/topics/models/official-models), [Replicate — How does Replicate work?](https://replicate.com/docs/reference/how-does-replicate-work)

---

## Ulaşılamayan / doğrulanamayan

- **RapidAPI**: ödeme eşiği (minimum çekim tutarı) net değil; Türkiye'den satıcı olarak kayıt olma kısıtı bulunamadı; listelenme ücreti olup olmadığı bulunamadı.
- **Apify Store**: Türkiye'nin açık şekilde yasaklı/izinli ülke listesinde olup olmadığı bulunamadı (yalnız genel yaptırım listesi maddesi var).
- **Zapier**: Integration Partner Program'da doğrudan bir para akışı olup olmadığı (yalnızca "dağıtım" faydası mı, yoksa gizli bir ücret paylaşımı mı) net değil; affiliate komisyon oranı resmî sayfada bulunamadı.
- **Make.com**: Apps Marketplace'in komisyon oranı, ödeme eşiği, ödeme yöntemi ve Türkiye kısıtı — hiçbiri resmî "Terms and Conditions" sayfasında bulunamadı. Bu, Make'in bu konuda ayrı, herkese açık olmayan bir sözleşme kullanıyor olabileceğini düşündürüyor ama bu doğrulanamadı.
- **OpenRouter sağlayıcı programı**: Komisyon oranı, ödeme yöntemi, ödeme eşiği, Türkiye kısıtı — hiçbiri resmî teknik dokümanda bulunamadı.
- **Hugging Face / Replicate**: Yaratıcıya doğrudan ödeme yapan resmî bir program olup olmadığı net şekilde "yok" olarak doğrulandı (mevcut dokümanlarda hiç geçmiyor), ama bunun gelecekte değişebileceği HF tarafından açıkça belirtiliyor.
- **Smithery (MCP)**: Resmî pricing/terms sayfası WebFetch ile açılamadı (JavaScript ile yüklenen içerik, sayfa boş geldi) — geliştiriciye ödeme yapılıp yapılmadığı bu araştırmada doğrulanamadı.
- **Cloudflare Workers AI**: Genel "Self-Serve Subscription Agreement" (ana sözleşme, Service-Specific Terms'in referans verdiği üst belge) bu araştırmada okunmadı — yalnızca Developer Platform'a özel ek şartlar okundu. Ana sözleşmede ayrı bir resale/ticari kullanım maddesi olabilir, doğrulanmadı.
- **Cohere**: Trial key'in yasak olduğu net, ama Production key'e geçtikten sonra "ücretsiz kredi" döneminde (varsa) ticari kullanım şartları ayrıca kontrol edilmedi — bu araştırma yalnızca Trial key'i kapsıyor.
- **n8n**: Resmî, ücretli bir pazaryerinin gerçekten var olmadığı makul güvenle doğrulandı (dokümantasyonda hiç geçmiyor, yalnızca ücretsiz npm+doğrulama akışı var), ama n8n'in ileride böyle bir şey planlayıp planlamadığı bilinmiyor.
