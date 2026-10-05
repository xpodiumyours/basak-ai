# Gelir Kanalı 1: Bireysel/Esnaf Abonelik — Ödeme ve Hukuk Altyapısı Araştırması

Tarih: 2026-09-25
Not: **Bu dosya araştırmadır, karar değildir.** Hiçbir sağlayıcı seçilmedi, hiçbir uygulama kararı verilmedi.

Kaynak kuralı: yalnız resmi birincil kaynak kullanıldı — sağlayıcının kendi fiyat/komisyon/destek/dokümantasyon sayfası, ya da resmi mevzuat sayfası (gib.gov.tr, ticaret.gov.tr). Blog, forum, karşılaştırma sitesi, üçüncü taraf özet KAYNAK OLARAK KULLANILMADI (bazı arama sonuçlarında görüldü ama alıntı/iddia olarak yazılmadı). Bulunamayan yerler **"bulunamadı"** olarak işaretlendi, tahmin yapılmadı.

**Ön ödeme uyarısı:** Araştırılan 7 kanalın hiçbirinin resmi sayfasında kurulum ücreti veya aylık sabit ücret bulunamadı — hepsi yalnız satış olduğunda komisyon kesiyor (aşağıda kanıtlarıyla). Yani bu 7 kanaldan hiçbiri **"ÖN ÖDEME İSTİYOR"** işareti almadı. Ama Stripe zaten Türkiye'den hiç kullanılamıyor (bkz. ilgili bölüm) — bu ayrı bir engel, ön ödeme meselesi değil.

---

## 1. Özet Tablo

| Kanal | Komisyon | Ödeme eşiği | Türkiye'den olur mu | Şirket şart mı | Başlangıç maliyeti |
|---|---|---|---|---|---|
| iyzico | %4,29 + 0,25 TL (kurumsal satıcı, resmi teklif) | bulunamadı | EVET (yerli sağlayıcı) | Sanal POS için EVET; Link Yöntemi'nde bireysel başvuru mümkün | 0 — "başlangıç ücreti veya herhangi bir sabit ücret" yok |
| PayTR | Sabit oran resmi sayfada yok (hacme/iş modeline göre); kampanya: yeni üye %2,19, kadın girişimci %0 | bulunamadı | EVET (yerli sağlayıcı) | bulunamadı | 0 — "giriş ücreti, entegrasyon bedeli... gizli ücretlendirme... bulunmamaktadır" |
| Shopier | Resmi yardım sayfasında sayısal oran YOK (yalnız "hizmet bedeli kesintisi" ifadesi) | bulunamadı | EVET (yerli sağlayıcı) | bulunamadı | 0 — "üyelik oluşturmak ücretsizdir", aylık/yıllık ücret yok |
| Paddle | %5 + 0,50 $ / işlem | bulunamadı | EVET — Türkiye, Paddle'ın 28 ülkelik "desteklenmeyen ülkeler" listesinde YOK | bulunamadı (satıcı kayıt şartları sayfası bulunamadı) | 0 — "No migration fees, monthly fees, or hidden extras" |
| Lemon Squeezy | %5 + 0,50 $ / işlem (+ yurt dışı işlemde %1,5, PayPal'da %1,5, abonelikte %0,5 ek) | bulunamadı | EVET — Türkiye, banka havalesiyle ödeme alınabilen ülkeler listesinde var | bulunamadı | 0 — "There are no monthly charges for ecommerce features" |
| Stripe | uygulanamaz | uygulanamaz | **HAYIR** — Türkiye ne normal Stripe hesabı ne de Managed Payments (MoR) desteklenen iş yeri ülkeleri listesinde var | uygulanamaz | uygulanamaz |
| Gumroad | %10 + 0,50 $ (doğrudan satış); Discover pazaryerinden %30 | bulunamadı (resmi sayfaya erişilemedi, bkz. Ulaşılamayanlar) | bulunamadı (resmi sayfadan Türkiye'ye özel teyit alınamadı) | bulunamadı | 0 — "Gumroad doesn't charge you a monthly fee" |

---

## 2. Kanal Detayları

### iyzico

Kaynak: https://www.iyzico.com/destek/yardim-merkezi/genel-bilgiler/fiyatlandirma

> "Eğer kurumsal bir satıcıysanız, siteniz üzerinden gerçekleşen başarılı işlem başına %4,29 ve 0,25 TL işlem ücretiyle özel teklif alabilirsiniz."

Kurulum/sabit ücret yok:

> "Başlangıç ücreti veya herhangi bir sabit ücret" (yok)

Şirket şartı: Sanal POS için şirket sahibi olmak gerekiyor; Link Yöntemi'nde bireysel başvuru mümkün (aynı sayfadan). Web sitesi hazır olmalı, gizlilik politikası + mesafeli satış sözleşmesi + SSL zorunlu.

Para çekme eşiği: bu sayfada belirtilmiyor — **bulunamadı**.

---

### PayTR

Kaynak: https://www.paytr.com/

> "giriş ücreti, entegrasyon bedeli, verimsizlik ücreti, aylık, yıllık ücret, işlem başına ücret vb. herhangi bir gizli ücretlendirme uygulaması bulunmamaktadır"

Aynı sayfada kampanya oranları görüldü: yeni üyeler için %2,19, kadın girişimciler için %0 komisyon (birebir yüzde metni sayfada geçiyor, ama bunlar kampanya oranı — standart/genel oran resmi sayfada bir tablo halinde bulunamadı).

Kaynak: https://www.paytr.com/destek-merkezi/faturalandirma

> "PayTR'dan aldığınız ödeme hizmetlerine istinaden alınan komisyon ücretlerine dair tarafınıza fatura kesilecektir" — komisyonlar aylık faturalandırılıyor, ama sayfada somut yüzde tablosu yok.

Standart/genel komisyon yüzdesi, para çekme eşiği ve şirket/vergi levhası şartı resmi sayfalarda net biçimde **bulunamadı** — PayTR'nin kendi sayfaları oranın "aylık işlem hacmi/yıllık ciro hedefi ve iş modeline göre" değiştiğini söylüyor, teklif almak için başvuru gerekiyor.

---

### Shopier

Kaynak: https://help.shopier.com/help/shopier-ucretlendirmesi-nasil

> "Shopier'de üyelik oluşturmak ücretsizdir."
> "Kullanımınıza dayalı süreli (aylık, yıllık, vb.) bir ücretlendirme de bulunmaz."
> "Shopier'de sadece bir sipariş aldığınızda hizmet bedeli kesintisi oluşur."

Bu resmi sayfada **sayısal bir komisyon oranı (%) yazmıyor** — sayfa, güncel oranın hesaba giriş yapıp panelden ("Ayarlar > Ücretlendirme > İşlem Ücretleri") görülmesi gerektiğini söylüyor. Dolayısıyla kesin komisyon yüzdesi resmi kaynaktan **bulunamadı** (yalnız üçüncü taraf sitelerde %2,99–%5,99 aralığı görüldü, bunlar kaynak olarak kullanılmadı).

Para çekme eşiği ve şirket/vergi levhası şartı da bu resmi sayfada **bulunamadı**.

---

### Paddle

Kaynak: https://www.paddle.com/pricing

> "5% + 50¢ per Checkout transaction"
> "No migration fees, monthly fees, or hidden extras"

Kaynak: https://www.paddle.com/help/start/intro-to-paddle/which-countries-are-supported-by-paddle

> "Paddle works with software businesses anywhere in the world with the exception of the unsupported countries listed below."

Desteklenmeyen 28 ülke/bölge listesi (bu sayfadan, birebir): Afghanistan, Antarctica, Belarus, Burma (Myanmar), Central African Republic, Cuba, Crimea, Democratic Republic of Congo, Donetsk, Haiti, Iran, Iraq, Kherson, Libya, Luhansk, Mali, Netherlands Antilles, Nicaragua, North Korea, Russia, Somalia, South Sudan, Sudan, Syria, Venezuela, Yemen, Zaporizhzhia, Zimbabwe.

**Türkiye bu listede yok** — yani Paddle'ın kendi kuralına göre Türkiye desteklenen bir ülke.

Merchant of Record (MoR — satıcı kayıtlarda platformun görünmesi, vergiyi platformun toplayıp ödemesi) modeli için kaynak: https://developer.paddle.com/concepts/sell/supported-countries-locales/

> "As merchant of record, Paddle calculates, collects, and remits taxes for you."

Not: Türkiye'nin satıcı (seller) kaydı için ayrı bir şart sayfası (şirket zorunlu mu, şahıs olarak satıcı olunabiliyor mu) resmi kaynakta **bulunamadı** — bulunan sayfalar yalnızca "hangi ülkeden alışveriş yapılabilir" (alıcı/buyer) tarafını netleştiriyor. Para çekme eşiği de **bulunamadı**.

---

### Lemon Squeezy

Kaynak: https://www.lemonsqueezy.com/pricing

> "5% + 50¢" (işlem başına)
> "There are no monthly charges for ecommerce features"

Ek ücretler (aynı sayfa): yurt dışı işlemlerde %1,5 ek, PayPal işlemlerinde %1,5 ek, abonelik ödemelerinde %0,5 ek.

Kaynak: https://docs.lemonsqueezy.com/help/getting-started/supported-countries

> "Bank payouts supported in the following countries: ... Turkey ..."

Türkiye, banka havalesiyle ödeme alınabilen (satıcıya para çekme) ülkeler listesinde görüldü — yani satıcı tarafında da destekleniyor.

Şirket/vergi levhası şartı ve para çekme eşiği bu sayfalarda **bulunamadı**.

---

### Stripe (derinlemesine — görev özel talep)

**Türkiye desteklenen ülke listesinde değil.**

Kaynak: https://stripe.com/global

Sayfanın kendi başlığı: "Stripe global availability" / "Accept global payments, send payouts, and manage your business online." Sayfada listelenen ülkeler arasında (Kuzey Amerika, Avrupa, Asya-Pasifik tam liste + "Preview" — Hindistan/Endonezya + "Extended network" — Paystack ile Fildişi Sahili/Gana/Kenya/Nijerya/Güney Afrika) **Türkiye yok**.

**Merchant of Record (MoR) — Stripe Managed Payments — de Türkiye'den kullanılamıyor.**

Kaynak: https://docs.stripe.com/payments/managed-payments/eligibility

> "Geographic eligibility: Your business must be based in one of the supported business locations."

Desteklenen iş yeri (business location) ülkeleri, sayfadan birebir:

- **Kuzey Amerika:** CA, US
- **Avrupa:** AT, BE, BG, CH, CY, CZ, DE, DK, EE, ES, FI, FR, GB, GR, HR, HU, IE, IT, LI, LT, LU, LV, MT, NL, NO, PL, PT, RO, SE, SI, SK
- **Asya-Pasifik:** AU, HK, JP, SG

**Türkiye bu listede yok.** Sonuç: Stripe Managed Payments (MoR modeli), zaten desteklenen bir ülkede Stripe hesabı olmasını şart koşuyor — Türkiye'de kurulu bir işletme için ne standart Stripe ne de MoR seçeneği resmi olarak kullanılabilir durumda değil.

Not: Managed Payments sayfası ayrıca satılabilecek ürün kategorilerini de listeliyor — "Artificial Intelligence as a Service (AIaaS)" resmi kategoriler arasında var (`txcd_10105001`/`txcd_10105002`), yani ürün türü uygun olsa bile ülke şartı Türkiye'yi zaten dışarıda bırakıyor.

---

### Gumroad

Kaynak: https://gumroad.com/pricing

> "10% + $0.50" — doğrudan satışlar (profil/direkt link üzerinden) için işlem başına.
> "30%" — Discover pazaryerinden gelen satışlar için işlem başına.
> "Gumroad doesn't charge you a monthly fee. Instead, our fees are deducted as a small percentage of every sale, so we only make money when you do."

Para çekme eşiği, ilk ödeme bekleme süresi ve Türkiye'den hesap açılıp açılamadığı için resmi "Getting Paid" / "Balance" sayfalarına ulaşılmaya çalışıldı (https://gumroad.com/help/article/13-getting-paid , https://gumroad.com/help/article/269-balance-page) — bu sayfalar JavaScript ile yükleniyor, alınan içerik yalnızca sayfa başlığından ibaret kaldı, gövde metni okunamadı. Bu üç bilgi de resmi kaynaktan **bulunamadı** (bkz. Ulaşılamayanlar).

---

## 3. Vergi/Hukuk Bölümü (Türkiye)

### Şahıs şirketi (esnaf) kurmak zorunlu mu

Kaynak: https://ticaret.gov.tr/ic-ticaret/elektronik-ticaret/elektronik-ticaret-bilgi-sistemi-etbis

> "Elektronik ticaret veya aracılık faaliyetinde bulunan hizmet sağlayıcı veya aracı hizmet sağlayıcıların, faaliyete başlamadan önce e-Devlet kapısı üzerinden ETBİS'e kayıt olması gerekmektedir."

ETBİS'e kayıt olabilecek kişi kategorileri arasında "esnaf ve sanatkârlar" da sayılıyor; esnaf için kayıtta T.C. kimlik no + vergi kimlik no + alan adı bilgisi isteniyor. Bu, ETBİS kaydının şahıs (esnaf) düzeyinde de mümkün ve gerekli olduğunu gösteriyor — ama "şirket kurmak şart mı, yoksa yalnız vergi mükellefiyeti tesis etmek mi yeterli" sorusuna net cevap veren tek bir gib.gov.tr/ticaret.gov.tr cümlesi bu araştırmada **bulunamadı**. (Not: "şirket kurmadan e-ticaret" konusundaki üçüncü taraf blog sonuçları KAYNAK OLARAK KULLANILMADI, yalnız arama sırasında görüldü.)

### ETBİS kaydı bu iş modeli için gerekiyor mu

Kaynak: https://ticaret.gov.tr/ic-ticaret/sikca-sorulan-sorular/elektronik-ticaret (arama sonucunda görülen resmi metin, WebSearch üzerinden):

> "Ağ üzerinde mal veya hizmet satışına yönelik sözleşme yapılmasını veya sipariş verilmesini sağlayan elektronik ticaret hizmet sağlayıcı ve elektronik ticaret aracı hizmet sağlayıcılar, faaliyete başlamadan önce ETBİS'e kayıt yaptırmak zorundadır."

Başak gibi kendi sitesinden abonelik/ödeme sözleşmesi kuran bir dijital hizmet satıcısı, bu tanıma göre elektronik ticaret hizmet sağlayıcısı sayılır — yani **ETBİS kaydı gerekiyor** görünüyor. Ama bu cümlenin dijital/SaaS abonelik özelinde ayrıca teyit eden ikinci bir resmi cümle bu araştırmada bulunamadı; yorum, ETBİS'in genel tanımına dayanıyor.

### Genç girişimci vergi muafiyeti şartları

Kaynak (resmi PDF, gib.gov.tr CDN'i): https://cdn.gib.gov.tr/api/gibportal-file/file/getFile?objectKey=DUYURU/UNIVERSAL/2026/2026_genc_girisimciler_info.pdf ("Genç Girişimcilere Vergi Teşviki", Gelir İdaresi Başkanlığı Mükellef Hizmetleri Daire Başkanlığı)

Birebir alıntılar:

> "Ticari, zirai veya mesleki faaliyeti nedeniyle adlarına ilk defa gelir vergisi mükellefiyeti tesis olunan ve mükellefiyet başlangıç tarihi itibarıyla 29 yaşını doldurmamış tam mükellef gerçek kişiler teşvikten yararlanabilir."

> "Genç girişimcilerin faaliyete başladıkları takvim yılından itibaren üç vergilendirme dönemi boyunca elde ettikleri kazançlarının gelir vergisi tarifesinin ikinci diliminde yer alan tutara kadar olan kısmı gelir vergisinden istisna edilmiştir. 2025 yılı için uygulanacak istisna tutarı 330.000 TL (2026 yılı için 400.000 TL)'dir."

Yararlanma şartları (aynı belgeden, birebir madde listesi):
- "Mevcut bir işletmeye veya mesleki faaliyete sonradan ortak olunmaması"
- "İşe başlamanın kanuni süresi içinde bildirilmiş olması"
- "Kendi işinde bilfiil çalışması veya işin kendisi tarafından sevk ve idare edilmesi"
- "Faaliyetin adi ortaklık veya şahıs şirketi bünyesinde yapılması halinde işe başlama tarihi itibarıyla ortakların tamamının tüm şartları taşıması"
- "Faaliyeti durdurulan veya faaliyetine devam eden bir işletmenin ya da mesleki faaliyetin ... eş veya üçüncü dereceye kadar kan veya kayın hısımlarından devralınmamış olması"

Önemli ek not (aynı belgeden): 1/1/2026'dan itibaren genç girişimcilere sağlanan **sigorta prim teşviki kaldırıldı** (7566 sayılı Kanun'un 23. maddesiyle), ama **gelir vergisi istisnası (kazanç istisnası) aynen devam ediyor**.

### Dijital hizmet satışına özgü ayrı bir istisna (mükerrer 20/B) — bulundu ama tam teyit edilemedi

Arama sırasında GİB'in "318 Seri No'lu Gelir Vergisi Genel Tebliği" adlı resmi tebliğine referans veren bir sonuç görüldü (mevzuat sayfası: https://gib.gov.tr/mevzuat/kanun/433/teblig/6672) — bu tebliğ, "internet ve benzeri elektronik ortamlar üzerinden sunulan hizmetler" ile "mobil cihazlar için uygulama geliştiriciliği"nden elde edilen kazançlara (Gelir Vergisi Kanunu mükerrer 20/B) ayrı bir istisna tanıyor gibi görünüyor — bu, Başak gibi bir yazılım/abonelik ürünü için doğrudan ilgili olabilir. Ancak bu tebliğin sayfası fetch edilmeye çalışıldığında yalnızca "Gelir İdaresi Başkanlığı" başlığı döndü, madde metni (banka hesabı şartı, üst sınır tutarı) resmi kaynaktan **birebir doğrulanamadı** — bkz. Ulaşılamayanlar. Bu, ayrı ve daha derin bir araştırma gerektirir, burada yalnızca varlığı not edilmiştir; şart/tutar bilgisi teyitsizdir.

---

## 4. Türkiye'deki Benzer Ürünlerin Fiyat Bulgusu

Görev tarifi "ürünün kendi resmi fiyat sayfasından oku" diyordu. Arama sırasında bulunan sonuçlar iki gruba ayrılıyor:

1. **Küresel genel amaçlı asistanlar (ChatGPT, Google AI, Claude vb.) — bunlar Türkçe konuşan ama Türk yapılımı olmayan ürünler**, bu araştırmanın kapsamı dışında (görev "Türkiye'de satılan benzer yapay zekâ asistanı/chatbot ürünleri" diyor, bunlar küresel ürün); ayrıca bulunan bilgiler resmi fiyat sayfası değil, haber/blog özetiydi — kaynak olarak kullanılmadı.

2. **Türk yapımı kurumsal chatbot/asistan ürünleri** (LexChat.AI, Palmate AI, yapayzekachatbot.com/tr, Çebi Medya vb.) arama sonuçlarında göründü, ama bunların da resmi fiyat sayfalarına tek tek girilip birebir rakam/alıntı doğrulanmadı — yalnızca WebSearch özeti görüldü, resmi sayfa fetch edilmedi.

Sonuç: **Türkiye'de satılan, Casper'ınkine benzer bir "kişisel/bireysel AI asistan" ürününün kendi resmi fiyat sayfasından okunmuş, birebir alıntılı bir TL fiyatı bu araştırmada bulunamadı.** Bulunanlar ya kurumsal chatbot (işletmeye satılan, farklı segment) ya da resmi sayfası fetch edilmemiş arama özetleriydi. Bu bölüm için doğru cevap: **bulunamadı** — kaynak kuralına uymayan hiçbir rakam bu dosyaya yazılmadı.

---

## 5. Ulaşılamayan / Doğrulanamayan

- **PayTR** — genel/standart komisyon yüzdesi resmi sayfada tablo halinde yok; yalnız kampanya oranları (%2,19 yeni üye, %0 kadın girişimci) görüldü. Para çekme eşiği ve şirket/vergi levhası şartı resmi kaynakta bulunamadı. PayTR'nin otomatik/tekrarlayan (abonelik) tahsilat desteği olup olmadığı resmi sayfadan doğrulanamadı.
- **Shopier** — resmi yardım sayfasında (help.shopier.com) sayısal komisyon oranı (%) hiç yazmıyor; panel içinden görülebileceği söyleniyor, dışarıdan erişilemedi. Para çekme eşiği/sıklığı ve şirket/vergi levhası şartı da bulunamadı.
- **Paddle** — satıcı (seller) kaydı için şirket/şahıs ayrımı ve belge şartlarını anlatan resmi bir sayfa bulunamadı; yalnız alıcı (buyer) tarafının ülke desteği netleşti. Para çekme eşiği bulunamadı.
- **Lemon Squeezy** — şirket/vergi levhası şartı ve para çekme eşiği resmi sayfalarda bulunamadı.
- **Gumroad** — "Getting Paid" (https://gumroad.com/help/article/13-getting-paid) ve "Balance page" (https://gumroad.com/help/article/269-balance-page) sayfaları JavaScript ile yüklendiğinden WebFetch yalnızca sayfa başlığını getirdi; para çekme eşiği, ilk ödeme bekleme süresi ve Türkiye'den hesap açılıp açılamadığı resmi kaynaktan doğrulanamadı.
- **iyzico** — para çekme eşiği (varsa minimum tutar/bekleme süresi) fiyatlandırma sayfasında yazmıyor.
- **GİB — mükerrer 20/B (318 Seri No'lu Tebliğ)** — "internet üzerinden sunulan hizmetler / mobil uygulama geliştiriciliği kazanç istisnası"nın tam şart metni (banka hesabı şartı, üst sınır tutarı, muafiyet kapsamı) gib.gov.tr/mevzuat sayfasından fetch edilmeye çalışıldı, yalnız başlık döndü — madde metni birebir doğrulanamadı.
- **Şahıs şirketi kurmak şart mı** — ETBİS'in esnaf düzeyinde kayda izin verdiği görüldü, ama "vergi mükellefiyeti tesis etmek yeterli mi, yoksa ayrıca şirket kurmak (şahıs şirketi tescili) mi gerekiyor" sorusuna gib.gov.tr veya ticaret.gov.tr'den tek ve net bir cümle bulunamadı.
- **Türkiye'deki benzer AI asistan ürünlerinin resmi fiyat sayfası** — hiçbiri tek tek fetch edilip birebir alıntı ile doğrulanmadı; bu bölüm tamamen "bulunamadı" ile kapatıldı.
