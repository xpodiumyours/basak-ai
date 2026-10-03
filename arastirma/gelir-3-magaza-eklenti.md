# Başak — Uygulama Mağazaları ve Sohbet Platformları Araştırması

**Tarih:** 2026-09-25
**Not:** Bu bir **araştırmadır, karar değildir.** Hangi kanalın seçileceğine Casper karar verir.

**Yöntem notu:** Yalnız resmi/birincil kaynaklar kullanıldı (platformun kendi sayfası, sözleşmesi, yardım merkezi). Blog/forum/üçüncü parti özet bulunduğunda "DOĞRULANAMADI" diye işaretlendi ve resmi kaynak aranmaya devam edildi — bazı platformlarda (Shopier, Bionluk, Discord, Slack) bu oturumda resmi sayfaya tam erişim sağlanamadı, bu açıkça belirtildi.

---

## Özet Tablo

| Platform | Kayıt ücreti | Komisyon | Türkiye'den olur mu | Sıfır parayla başlanır mı |
|---|---|---|---|---|
| **Google Play** | **25 dolar, tek seferlik** | %15 (yıllık ilk 1 milyon dolar kazanç), üzeri %30 | EVET — hem geliştirici hem satıcı kaydı destekleniyor, TRY | **HAYIR** — ÖN ÖDEME İSTİYOR: 25 dolar |
| **Apple App Store** | **99 dolar/yıl** | %30 standart; Small Business Program'da %15 (yıllık kazanç ≤1 milyon dolarsa) | Kısmen doğrulandı — TRY para birimi destekleniyor, ama Türk banka kartlarında bazı sorunlar bildiriliyor (resmi kaynakta net liste bulunamadı) | **HAYIR** — ÖN ÖDEME İSTİYOR: 99 dolar/yıl |
| **Microsoft Store** | **ÜCRETSİZ** (hem bireysel hem şirket hesabı — yeni akış) | Kendi ödeme sistemini kullanırsan uygulamalarda **%0**; Microsoft'un ödeme sistemini kullanırsan %15 uygulama / %12 oyun | Muhtemelen (yaklaşık 200 pazarda kayıt açık), Türkiye'nin adı geçen resmi bir liste bu oturumda bulunamadı | **EVET** |
| **Chrome Web Store** | Tek seferlik ücret var; resmi sayfa tutarı net yazmıyor, ikincil resmi referansta **5 dolar** geçiyor | Ücretli eklenti satışı platformda kaldırılmış olabilir — bu oturumda resmi teyit **bulunamadı** | bulunamadı | **HAYIR** (muhtemelen 5 dolar ön ödeme var) |
| **Telegram (Stars)** | Yok | Telegram bot tarafında komisyon almıyor gibi görünüyor; Stars'ı gerçek paraya çevirme (Fragment/TON) maliyeti resmi sayfada tablo halinde var ama bu oturumda tam metne ulaşılamadı | bulunamadı (coğrafi kısıtlama görünmüyor) | **EVET** görünüyor (bot kurmak ücretsiz) |
| **Discord** | Yok (başvuru + ödeme bilgisi gerekli) | Resmi komisyon oranı bu oturumda **teknik erişim sorunu** (sertifika hatası) yüzünden doğrulanamadı | bulunamadı | bulunamadı (muhtemelen evet ama doğrulanamadı) |
| **Slack Marketplace** | bulunamadı | bulunamadı — resmi sayfada rakam yok | bulunamadı | bulunamadı |
| **WhatsApp Business Platform** | Yok — bu bir **MALİYET** kanalı, gelir kanalı değil | Mesaj başına ücret (1 Temmuz 2025'ten beri); kategoriler: Marketing (her zaman ücretli), Utility (bazen ücretsiz), Authentication (hacim indirimi), Service (her zaman ücretsiz) | Türkiye ayrı pazar olarak listelenmiş ama TL rakamı statik sayfada yok (interaktif araç gerekiyor) | Konu dışı — bu maliyet kanalı |
| **Gumroad** | Yok | Doğrudan satış: **%10 + 0,50 dolar**; Discover (pazar yeri) üzerinden: **%30** | Açık bir yasak yazmıyor, ama doğrulanamadı | muhtemelen EVET |
| **Lemon Squeezy** | Yok | **%5 + 0,50 dolar** | Açık bir yasak yazmıyor ("200+ ülke"), Türkiye adı geçmiyor | muhtemelen EVET |
| **Shopier (TR)** | Yok (üyelik ücretsiz) | Resmi yardım sayfası JavaScript ile yüklendiği için bu oturumda tam metin çekilemedi. Üçüncü parti kaynaklar %2,99–%5,99 + 0,49 TL aralığı söylüyor — **DOĞRULANAMADI (resmi kaynaktan değil)** | EVET (Türk platformu) | muhtemelen EVET |
| **Bionluk (TR)** | bulunamadı (bazı üçüncü parti kaynaklar giriş ücretinden bahsediyor — DOĞRULANAMADI) | Resmi komisyon oranı bu oturumda **bulunamadı**. Üçüncü parti kaynaklar %20 diyor — **DOĞRULANAMADI** | EVET (Türk platformu) | bulunamadı |

---

## 1. Uygulama Mağazaları

### 1.1 Google Play (Android)

**Kayıt ücreti:** 25 dolar, tek seferlik.
> "There is a US$25 one-time registration fee that you can pay with the following credit or debit cards: MasterCard, Visa, American Express, Discover (the U.S. only), Visa Electron (Outside of the U.S. only)"
Kaynak: https://support.google.com/googleplay/android-developer/answer/6112435

**ÖN ÖDEME İSTİYOR: 25 dolar**

**Komisyon (Service Fee):**
> "As of July 1, 2021, the service fee is 15% for the first $1M (USD) of earnings you make each year when you sell digital goods or services." ... "Once the total earnings exceed $1M (USD), the service fee is 30% for all ADAs for the rest of the year."
Kaynak: https://support.google.com/googleplay/android-developer/answer/10632485

**Türkiye'den olur mu:** Evet. Google'ın resmi desteklenen ülkeler tablosunda Türkiye hem geliştirici kaydı hem satıcı (merchant) kaydı için işaretli, para birimi TRY.
Kaynak: https://support.google.com/googleplay/android-developer/table/3539140

**Ödeme şartları:** Geliştirici hesabına ek olarak parayı almak için ayrı bir "payments profile" ve "merchant account" açman gerekiyor; yasal işletme adı ve gerçek fiziksel adres isteniyor (posta kutusu kabul edilmiyor).
Kaynak: https://support.google.com/googleplay/android-developer/answer/7161426 , https://support.google.com/googleplay/android-developer/answer/13628312

---

### 1.2 Apple App Store (iOS/iPadOS/macOS)

**Kayıt ücreti:** 99 dolar / yıl.
> "$99 annual membership — Includes all Apple developer account benefits... Distribute your apps and digital goods and services on Apple platforms"
Kaynak: https://developer.apple.com/programs/

**ÖN ÖDEME İSTİYOR: 99 dolar/yıl**

**Komisyon — resmi sözleşme metninden (Schedule 2, Apple Developer Program License Agreement, v126, 17 Aralık 2025):**
> "Apple shall be entitled to a commission equal to thirty percent (30%) of all prices payable by each End-User. Solely for auto-renewing subscription purchases made by customers who have accrued greater than one year of paid subscription service... Apple shall be entitled to a commission equal to fifteen percent (15%)..."

> "App Store Small Business Program. For Developers who have qualified and been approved by Apple for the App Store Small Business Program, Apple shall be entitled to a reduced commission of 15% of all prices payable by each End-User... You and Your Associated Developer Accounts must have earned no more than $1,000,000 in total proceeds... during the twelve (12) fiscal months occurring in the prior calendar year."

Kaynak (resmi PDF, doğrudan indirilip okundu): https://developer.apple.com/support/downloads/terms/schedules/Schedule-2-and-3-English.pdf

Small Business Program özet sayfası:
> "It features a reduced commission rate of 15% on paid apps and Apple In-App Purchases... For developers on the alternative terms in the EU in the App Store Small Business Program and for subscriptions after their first year, Apple will offer a further reduced commission of 10%."
Kaynak: https://developer.apple.com/app-store/small-business-program/

**Türkiye'den olur mu:** Kısmen doğrulandı. App Store 175 bölgede kullanılabiliyor (developer.apple.com/programs/ sayfasında geçiyor) ve Türk Lirası (TRY) uygulama içi satın alma için desteklenen bir para birimi. Ancak Apple'ın "hangi ülkelerden Developer Program'a kayıt olunabilir" konulu net, tek resmi liste sayfası bu oturumda bulunamadı — Apple'ın kendi forumlarında Türkiye bölgesinden kayıt konusunda geliştirici şikâyetleri var (bu resmi kaynak değil, sadece uyarı amaçlı not).

**Ödeme şartları:** Yıllık 99 dolar ön ödeme zorunlu; Apple ödemeleri "remittance currency" belirlediğin banka hesabına havale yoluyla yapıyor, asgari aylık tutar eşiği var.

---

### 1.3 Microsoft Store (Windows)

**Kayıt ücreti — ÖNEMLİ DEĞİŞİKLİK:** Hem bireysel hem şirket hesabı artık **ücretsiz** (yeni onboarding akışı üzerinden).

> "The new onboarding process is now live, allowing individual developers to publish apps to the Microsoft Store without any onboarding fees... No registration fee — The $19 registration fee is waived in the new flow."
Kaynak: https://learn.microsoft.com/en-us/windows/apps/publish/whats-new-individual-developer

> "The new onboarding process allows company developers to publish apps to the Microsoft Store without any onboarding fees... Free registration — The $99 registration fee is waived in the new flow."
Kaynak: https://learn.microsoft.com/en-us/windows/apps/publish/whats-new-company-developer

**Sıfır parayla başlanır mı: EVET** (bu üç mağaza arasında tek tam ücretsiz olan).

**Komisyon:**
> "Flexible revenue sharing options that let developers choose their own commerce platform and keep 100% of the revenue for non-gaming apps, or use Microsoft's commerce platform and pay a competitive fee of 12% for games and 15% for apps."
Kaynak: https://learn.microsoft.com/en-us/windows/apps/publish/publish-your-app/why-distribute-through-store

**Türkiye'den olur mu:** Yeni akış "nearly 200 markets" / "over 200 markets" diye tanımlanıyor ama Türkiye'nin adının geçtiği net bir resmi liste bu oturumda bulunamadı. Yüksek ihtimalle dahil, ama doğrulanamadı.

---

### 1.4 Chrome Web Store

**Kayıt ücreti:** Resmi sayfa yalnız "tek seferlik ücret" diyor, tutarı yazmıyor:
> "Before you can publish items on the Chrome Web Store, you must register as a CWS developer and pay a one-time registration fee."
Kaynak: https://developer.chrome.com/docs/webstore/register

Tutar (5 dolar) yalnız Chrome geliştirici dokümantasyonunun başka bir sayfasında dolaylı olarak geçiyor ("without paying the $5 registration fee" — üye davet etme bağlamında). Bu bir resmi Google kaynağıdır ama doğrudan "kayıt ücreti = 5 dolar" diyen tek cümleli net bir resmi paragraf bu oturumda bulunamadı.

**Komisyon / ücretli eklenti satışı:** Bilinen bilgi: Google, Chrome Web Store üzerinden ücretli eklenti/uygulama satışını (Chrome Web Store Payments/Transaction API) birkaç yıl önce kaldırmıştı; bu oturumda bunu doğrulayan resmi bir sayfa bulunamadı — **bulunamadı**.

---

## 2. Sohbet Platformları

### 2.1 Telegram (Bot ödemeleri / Stars)

Resmi sayfa: https://core.telegram.org/bots/payments-stars

Sayfa Stars sisteminin "ücretsiz ve açık bir platform" olduğunu, kullanıcıların Stars'ı Apple/Google uygulama içi satın alma yoluyla alıp botlara ödeme olarak kullandığını anlatıyor. Sayfada ücret/net kazanç tablosu olduğu görüldü ancak bu oturumda tablo içeriği tam metin olarak çekilemedi — **kesin oranlar doğrulanamadı**.

Bilinen (ama bu oturumda resmi kaynaktan tam doğrulanamayan) noktalar:
- Kullanıcı Stars'ı Apple/Google üzerinden satın aldığında, o adımda Apple/Google'ın kendi komisyonu (%30) devreye giriyor.
- Stars'ı gerçek paraya çevirmek (Fragment platformu, TON blok zinciri üzerinden) ayrı bir süreç ve maliyet — bu oturumda resmi Telegram/Fragment kaynağından net oran teyit edilemedi.

**Sıfır parayla başlanır mı:** Bot kurmak ücretsiz görünüyor; gelir kullanıcıdan Stars olarak geliyor. Coğrafi kısıtlama (Türkiye) belirten bir ifade bulunamadı.

### 2.2 Discord

Resmi kaynaklar bulundu ama bu oturumda **teknik erişim sorunu** (WebFetch aracı Discord domainlerinde "self signed certificate" hatası verdi) yüzünden tam metin çekilemedi:
- https://docs.discord.com/developers/monetization/enabling-monetization
- https://support.discord.com/hc/en-us/articles/10575066024983-Monetization-Policy
- https://support-dev.discord.com/hc/en-us/articles/17297949965079-How-Do-I-Monetize-My-App

Arama motoru özetlerinden (resmi sayfa başlıklarına dayanan, ama doğrudan alıntı doğrulanamamış) bilgiler:
- Ekim 2024'ten itibaren ödemeli özellik sunan geliştiricilerin Discord'un "Premium Apps" ürünü üzerinden satış yapması zorunlu.
- Monetization açmak için: geliştirici portalında bir takım (team), uygunluk kontrolü, ödeme bilgisi ve Monetization Terms/Policy kabulü gerekiyor.
- **Komisyon oranı, kayıt ücreti ve Türkiye desteği bu oturumda resmi kaynaktan doğrulanamadı — bulunamadı.**

### 2.3 Slack Marketplace

Resmi sayfalar bulundu ve kısmen okunabildi ama **ücret/komisyon rakamı hiçbirinde açıkça yer almıyordu**:
- https://docs.slack.dev/slack-marketplace/
- https://api.slack.com/slack-marketplace/guidelines

**Ücret/komisyon: bulunamadı.** Türkiye desteği: **bulunamadı.**

### 2.4 WhatsApp Business Platform

Bu bir **MALİYET kanalıdır, gelir kanalı değil** — kullanıcıya para tahsil etmek için değil, kullanıcıya mesaj göndermek için Meta'ya ödeme yapılıyor.

**1 Temmuz 2025'ten itibaren mesaj başına ücretlendirme** modeli geçerli:
> "Businesses using our platform are charged on a per-message basis for each message we deliver to users."
Kaynak: https://whatsappbusiness.com/products/platform-pricing/

Kategoriler:
- **Marketing** — her zaman ücretli
- **Utility** — müşteri hizmet penceresi içindeyse ücretsiz
- **Authentication** — hacim arttıkça indirim var
- **Service** — her zaman ücretsiz ("businesses can respond with service messages, at no charge")

Türkiye ayrı bir pazar olarak fiyat listesinde geçiyor ancak sabit TL rakamı statik sayfada verilmiyor — Meta interaktif bir fiyat aracı/PDF/CSV kullanıyor. **Kesin TL fiyatı bu oturumda bulunamadı.**

---

## 3. Hazır Dijital Satış Platformları

### 3.1 Gumroad

**Komisyon:**
> Doğrudan satış: "10% + $0.50" per transaction
> Discover (pazar yeri) üzerinden: "30%" per transaction
Kaynak: https://gumroad.com/pricing

**Kayıt/aylık ücret:** Bulunamadı — sayfada aylık sabit ücretten bahsedilmiyor (10%+0.50$ dışında).

**Türkiye:** Sayfada açık bir yasak/kısıtlama yazmıyor, ama ödeme yöntemi (PayPal/Stripe bağlantı şartı) ve Türkiye'nin bu platformda satıcı olarak kabul edilip edilmediği bu oturumda ayrıca doğrulanamadı.

**Sıfır parayla başlanır mı:** Muhtemelen evet, aylık sabit ücret yok.

### 3.2 Lemon Squeezy

**Komisyon:**
> "5% + 50¢" per transaction. "There is no monthly fee to use Lemon Squeezy for payment processing."
Kaynak: https://www.lemonsqueezy.com/pricing

**Türkiye:** Sayfa "130+ para birimi" ve "200'den fazla ülke destekleniyor" diyor ama Türkiye'nin adı açıkça geçmiyor — **doğrulanamadı**.

**Sıfır parayla başlanır mı:** Muhtemelen evet.

### 3.3 Shopier (Türk platformu)

Resmi yardım sayfası bulundu ama JavaScript ile yüklendiği için bu oturumdaki araçla tam metin çekilemedi:
- https://help.shopier.com/help/ucretlendirme
- https://help.shopier.com/help/shopier-ucretlendirmesi-nasil

Sayfa "üyelik ücretsiz, yalnız sipariş aldığında işlem ücreti kesiliyor" diyor, ama tam yüzdeler resmi kaynaktan bu oturumda çekilemedi.

**DOĞRULANAMADI (üçüncü parti kaynaklardan, resmi değil):** Yurtiçi %2,99 + 0,49 TL (aylık 15.000 TL altı yeni satıcılarda %5,99 + 0,49 TL), yurtdışı %3,99 + 0,49 TL. Bu rakamlar Shopier'in kendi sayfasından değil, üçüncü parti blog/rehber sitelerinden geliyor — **resmi olarak doğrulanmadı, kural gereği ihtiyatla okunmalı.**

**Türkiye:** Evet, Türk platformu — kayıt ve para çekme yerli.

### 3.4 Bionluk (Türk platformu, dijital ürün/hizmet)

Resmi komisyon/ücret sayfası bu oturumda **bulunamadı** — bionluk.com'un kendi hizmet şartları/komisyon sayfasına doğrudan erişilemedi.

**DOĞRULANAMADI (üçüncü parti kaynaktan):** Bazı bloglar %20 komisyon olduğunu yazıyor. Resmi kaynaktan teyit edilmedi.

**Türkiye:** Evet, Türk platformu.

---

## Ulaşılamayan / Doğrulanamayan Bilgiler (özet liste)

1. **Chrome Web Store** — kayıt ücretinin tam tutarı ($5 iddiası dolaylı/ikincil bir resmi referanstan; net cümle bulunamadı) ve ücretli eklenti satışının hâlâ var olup olmadığı.
2. **Telegram Stars** — withdraw/Fragment üzerinden gerçek paraya çevirme oranı tablosu (sayfada var ama tam metin çekilemedi).
3. **Discord** — komisyon oranı, ödeme yöntemi detayları, Türkiye desteği (teknik erişim hatası: "self signed certificate").
4. **Slack Marketplace** — ücret/komisyon oranı, Türkiye desteği.
5. **WhatsApp Business Platform** — Türkiye için kesin TL/mesaj fiyatı (interaktif araç gerekiyor, statik sayfada yok).
6. **Gumroad, Lemon Squeezy** — Türkiye'nin resmi olarak desteklenen ülke listesinde açıkça yazılı olup olmadığı.
7. **Shopier** — resmi komisyon yüzdeleri (sayfa JS ile yükleniyor, bu oturumda çekilemedi; yalnız üçüncü parti rakamlar var).
8. **Bionluk** — resmi komisyon oranı ve kayıt/giriş ücreti iddiası.
9. **Apple** — Türkiye'den Developer Program'a kayıt için net, resmi "desteklenen ülkeler" listesi (yalnız TRY para birimi desteği ve dolaylı forum bulguları var).
10. **Microsoft Store** — Türkiye'nin yeni ücretsiz kayıt akışındaki ~200 pazar listesinde açıkça yer alıp almadığı.
