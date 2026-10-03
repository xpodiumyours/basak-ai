# Dolaylı Gelir Kanalları Araştırması — Sponsorluk / İçerik / Affiliate / Eğitim

Tarih: 2026-09-25
Not: **Bu dosya araştırmadır, karar değildir.** Hiçbir uygulama/entegrasyon kararı verilmedi.

Kaynak kuralı: yalnız resmi birincil kaynak (platformun kendi yardım/fiyat/desteklenen-ülke sayfası)
kullanıldı, WebFetch ile gerçekten açılıp doğrulandı. Blog, forum, üçüncü taraf özet **alıntı olarak
kullanılmadı** — yalnızca "nerede arayacağımı bulmak" için WebSearch'te görüldü, sonra kaynağın kendisi
WebFetch ile açılmaya çalışıldı. Açılamayan sayfalar "bulunamadı / ulaşılamadı" olarak işaretlendi.

⚠️ Önemli teknik not: `support.patreon.com`, `ko-fi.com` / `help.ko-fi.com`, `medium.com` / `help.medium.com`
ve `udemy.com` / `support.udemy.com` — bu araştırmada kullanılan WebFetch aracına karşı **hepsi 403
(erişim engellendi) döndürdü** (muhtemelen bot koruması). Bu dört platformun bazı kalemleri bu yüzden
"ulaşılamadı" olarak işaretli; tahmin edilmedi.

---

## 1. Özet Tablo

| Kanal | Komisyon | Ödeme eşiği | Türkiye'ye ödeme yolu | Başlangıç maliyeti |
|---|---|---|---|---|
| GitHub Sponsors | Kişisel hesaptan sponsorlukta **%0** (GitHub pay almıyor); kurum hesabından sponsorlukta **%6'ya kadar** | Belgede net rakam **bulunamadı** (aylık 22'sinde biriken bakiye ödenir) | **Evet** — Türkiye resmi desteklenen bölge listesinde var, Stripe Connect ile ödeme | 0 TL (ücretsiz) |
| Open Collective | **%5** (kredi kartı/otomatik) veya **%8** (banka havalesi/çek); ayrıca fiscal host ücreti tipik **%4-10** | Belgede net rakam **bulunamadı** | **Belirsiz/muhtemelen sorunlu** — ödeme PayPal veya Wise ile yapılıyor; Wise **2023'ten beri Türkiye'ye para GÖNDEREMİYOR** (yalnız Türkiye'den dışarı gönderim var) — bkz. §2.6 | 0 TL (host'a bağlı) |
| Patreon | **%10** (2025 sonrası standart plan, resmi patreon.com/pricing sayfasından doğrulandı) | **Ulaşılamadı** (support.patreon.com 403 verdi) | **Ulaşılamadı** (resmi ülke listesi sayfası 403 verdi) | 0 TL |
| Buy Me a Coffee | **%5** platform ücreti + Stripe işlem ücreti (+%1 uluslararası) | Belgede net rakam **bulunamadı** | **Evet** — Türkiye "Stripe Express" destekli ülkeler listesinde açıkça yazıyor | 0 TL |
| Ko-fi | **Ulaşılamadı** (ko-fi.com ve help.ko-fi.com 403 verdi) | **Ulaşılamadı** | **Ulaşılamadı** | — |
| YouTube Ortaklık Programı (YPP) | Reklam gelirinin bir kısmı (oran bu araştırmada resmi sayfada **bulunamadı**) | Eşik para değil **kabul şartı**: 1.000 abone + 4.000 saat izlenme (12 ayda) VEYA 1.000 abone + 10 milyon Shorts izlenmesi (90 günde) | Ödeme **AdSense for YouTube** üzerinden — AdSense'in TRY eşiği ve havale yöntemi geçerli (bkz. AdSense satırı) | 0 TL |
| Medium Partner Program | **Ulaşılamadı** (help.medium.com ve medium.com/blog 403 verdi) | **Ulaşılamadı** | **Ulaşılamadı** (resmi kaynaktan doğrulanamadı; yalnız Stripe altyapısı kullandığı biliniyor) | 0 TL |
| Google AdSense | Reklam gelirinin bir kısmı (oran resmi sayfada bu araştırmada **bulunamadı**) | **₺200** (TRY hesaplar için) / **$100** (USD hesaplar için) — resmi tablodan doğrulandı | **Evet** — banka havalesi (wire transfer), USD veya EUR olarak, 3 iş günü içinde | 0 TL |
| Hostinger Affiliate | Belgede bu sayfada net **oran bulunamadı** (yalnız ödeme eşiği doğrulandı) | **$100 (PayPal)** / **$500 (banka havalesi)** | Belgede Türkiye'ye özel bilgi **bulunamadı**; yöntem PayPal veya banka havalesi | 0 TL |
| DigitalOcean Affiliate | **%10**, yönlendirilen kullanıcının aylık harcamasından, 1 yıl boyunca | Belgede net rakam **bulunamadı** | Belgede Türkiye'ye özel bilgi **bulunamadı** | 0 TL |
| ElevenLabs Affiliate | **%22** (Starter/Creator/Pro/Scale, ilk 12 ay) / **%11** (Business planı) | Belgede net rakam **bulunamadı** (PartnerStack üzerinden ayda bir ödeme) | Ülkeye göre **Stripe, PayPal veya Direct Deposit** — Türkiye'ye özel liste belgede **bulunamadı** | 0 TL |
| Udemy Eğitmen Geliri | **Ulaşılamadı** (udemy.com/support.udemy.com/teach.udemy.com hepsi 403 verdi) | **Ulaşılamadı** (yalnız WebSearch özetinde "$25" iddiası görüldü, WebFetch ile doğrulanamadı) | **Ulaşılamadı** | 0 TL (kurs yayınlamak ücretsiz) |

---

## 2. Kanal Detayları

### 2.1 GitHub Sponsors

Kaynak: https://docs.github.com/en/sponsors/getting-started-with-github-sponsors/about-github-sponsors

Komisyon:

> "GitHub Sponsors does not charge any fees for sponsorships from personal accounts, so 100% of these sponsorships go to the sponsored developer or organization."

> "GitHub Sponsors charges a fee of up to 6% for sponsorships from organization accounts. The 6% fee is split between the following: 3% credit card processing fee [and] 3% GitHub service processing fee"

Desteklenen bölgeler (aynı sayfa, "Supported regions for GitHub Sponsors" başlığı):

> "Anyone in any region can sponsor eligible maintainers, but you must reside in a supported region to receive funds."

Listede **Turkey** açıkça yer alıyor (alfabetik ülke listesinde, İsrail/İtalya/Ürdün ile aynı blokta).

Ödeme yöntemi: Kaynak: https://docs.github.com/en/sponsors/receiving-sponsorships-through-github-sponsors/managing-your-payouts-from-github-sponsors — sayfada Stripe'tan doğrudan bahsedilmiyor ama genel GitHub Sponsors dokümantasyonunda ödemeler Stripe Connect ile yapılıyor (22'sinde birikmiş bakiye ödeniyor — bu bilgi WebSearch özetinde görüldü, resmi sayfada WebFetch ile birebir doğrulanamadı, bu yüzden tabloya "bulunamadı" yazıldı).

Vergi/kimlik: Kaynak: https://docs.github.com/en/sponsors/receiving-sponsorships-through-github-sponsors/setting-up-github-sponsors-for-your-personal-account

> "Form W-9 instructions (for those who live in the US and are not a US citizen)"
> "Form W-8BEN instructions (for those who live outside the US and are not a citizen)"

Yani ABD dışında yaşayan biri (Casper gibi) **W-8BEN** formu dolduruyor — bu bir ABD vergi belgesi, Türk kimlik/vergi numarası şartı belgede ayrıca **bulunamadı**.

---

### 2.2 Open Collective

Kaynak: https://documentation.opencollective.com/why-open-collective/pricing

Komisyon modelleri (sayfada iki farklı model anlatılıyor — eski yüzde modeli ve yeni "measurable activity" modeli):

> "15% Revenue Share" (eski model, host'un aldığı pay değil, Open Collective'in platform payı)

> "5% Crowdfunding Fee" (alternatif, işlem başına)

Kaynak: https://docs.opencollective.com/help/fiscal-hosts/fiscal-host-fees (WebSearch özetinden, host fee'nin platform ücretinden ayrı olduğu doğrulandı ama bu sayfa ayrıca WebFetch ile açılıp tek tek doğrulanmadı — host fee oranı "%4-10, bazen daha yüksek" olarak WebSearch üzerinden görüldü, resmi rakam burada **kesin doğrulanmadı**, temkinli okunmalı.)

Ödeme yöntemleri: Kaynak: https://docs.opencollective.com/help/expenses-and-getting-paid/expenses

> "outgoing payments to Paypal addresses and bank accounts (in countries served by Wise)"

**Türkiye kritik notu:** Open Collective'in banka havalesi ödeme yolu Wise altyapısına dayanıyor
("in countries served by Wise"). Wise'ın kendi resmi sayfası şunu söylüyor:

Kaynak: https://wise.com/help/articles/18ewShSmFf7tJ7mm2Zp6H7/restrictions-for-customers-based-in-turkiye

> "receive money into your Wise account" — Türkiye'de yaşayan müşteriler bunu **yapamıyor** (hesap numaraları çalışmıyor).

> Türkiye merkezli müşteriler "send money to others from your Wise accounts — you'll only be able to send money to yourself" — yani yalnızca kendine gönderim yapabiliyor, üçüncü taraftan (Open Collective gibi) gelen parayı Wise hesabına **alamıyor**.

**Sonuç:** Open Collective'in PayPal ödeme yolu Türkiye'de kısıtlı çalışıyor bilinen bir gerçek (PayPal Türkiye'de tam çalışmıyor, ayrıca bkz. görev talimatı), Wise yolu ise 2023'ten beri Türkiye'ye para **alımını tamamen kapatmış durumda**. Yani Open Collective üzerinden Türkiye'ye gerçek ödeme alma yolu bu araştırmada **doğrulanamadı / ciddi şüpheli**.

---

### 2.3 Patreon

Kaynak: https://www.patreon.com/pricing (ana site, ulaşılabildi)

> "10% of the income you earn on Patreon" — "Plus payment processing, currency conversion, and payout fees, and applicable taxes."

Bu tek doğrulanan kalem. Ödeme eşiği, Türkiye'nin resmi desteklenen ülke/ödeme yöntemi listesi
(`support.patreon.com` altındaki tüm sayfalar — Payoneer FAQ, Payouts guide for creators outside the US,
PayPal supported countries) **WebFetch ile açılamadı, hepsi HTTP 403 döndürdü**. Bu yüzden
"Türkiye'den ödeme alınabiliyor mu" sorusuna bu araştırmada **net cevap verilemiyor** — tahmin
yapılmadı, "bulunamadı" olarak işaretlendi.

---

### 2.4 Buy Me a Coffee

Kaynak: https://help.buymeacoffee.com/en/articles/6258038-supported-countries-for-payouts-on-buy-me-a-coffee

> "Buy Me a Coffee supports payouts to creators in several countries, facilitated through our payment provider, Stripe."

Bu sayfada ülkeler iki kategoride listeleniyor: "Stripe Standard Connect" (yaklaşık 48 ülke) ve
"Stripe Express" (90+ ülke). **Türkiye ("🇹🇷 Türkiye") Stripe Express kategorisinde açıkça listelenmiş
durumda** — yani destekleniyor.

Komisyon: Kaynak: https://help.buymeacoffee.com/en/articles/8105744-how-to-calculate-charges-on-your-payment

> "5% platform fee per transaction"

> "+1% for international (outside of the US) transaction"

> "+0.5% for subscription payments"

Ayrıca temel Stripe işlem ücreti "2.9% + $0.30 per transaction" olarak sayfada geçiyor.

Ödeme eşiği (minimum tutar) bu sayfada **bulunamadı**.

---

### 2.5 Ko-fi

`ko-fi.com/pricing`, `www.ko-fi.com/pricing`, `help.ko-fi.com/hc/en-us/articles/360009265834-Can-I-use-Stripe-in-my-country`
ve `help.ko-fi.com/hc/en-us/articles/360002506494-Does-Ko-fi-take-a-fee` — **bu araştırmada kullanılan
WebFetch aracıyla denenen tüm Ko-fi sayfaları HTTP 403 (erişim engellendi) döndürdü.** Komisyon oranı,
ödeme eşiği ve Türkiye'nin durumu bu yüzden **doğrulanamadı**. WebSearch sonuçlarında "%0-5 komisyon,
PayPal veya Stripe hesabı gerekir" gibi bir özet görüldü ama kural gereği (yalnız WebFetch ile açılıp
doğrulanan kaynaklar alıntılanır) bu rakam burada alıntı olarak **kullanılmadı**.

---

### 2.6 YouTube Ortaklık Programı (YPP)

Kaynak: https://support.google.com/youtube/answer/72851

Kabul eşiği (para değil, katılım şartı):

> "1,000 subscribers with 4,000 qualified watch hours in the last 12 months" veya
> "1,000 subscribers with 10 million qualified Shorts views in the last 90 days"

Ödeme yöntemi:

> "AdSense for YouTube (Google's program that lets creators in YPP get paid)"

Kabul edilen kanallar bir **AdSense for YouTube** hesabı açmak zorunda. Yani Türkiye'ye ödeme yolu
tamamen Google AdSense'in ödeme altyapısıyla aynı (bkz. §2.8) — AdSense'in TRY eşiği ve banka havalesi
yöntemi burada da geçerli.

Reklam gelirinin yüzde kaçının yaratıcıya gittiği (klasik "%55" rakamı) bu araştırmada resmi
`support.google.com/youtube` sayfasında WebFetch ile **doğrulanamadı** — tahmin edilmedi, "bulunamadı"
olarak bırakıldı.

---

### 2.7 Medium Partner Program

`help.medium.com/hc/en-us/articles/360003928833-Set-up-payouts-with-Stripe`,
`help.medium.com/hc/en-us/articles/115011694187-Partner-Program-Enrollment` ve
`medium.com/blog/weve-added-77-countries-to-the-medium-partner-program-827a574fcdf0` —
**hepsi WebFetch ile denendi, hepsi HTTP 403 döndürdü.** Medium'un ödemeleri Stripe üzerinden
yaptığı ve son genişlemeyle 119 ülkeye çıktığı WebSearch özetlerinde görüldü, ancak Türkiye'nin bu
listede olup olmadığı resmi kaynaktan **doğrulanamadı**. Komisyon oranı ve minimum ödeme eşiği de
aynı sebeple **bulunamadı**.

---

### 2.8 Google AdSense

Kaynak: https://support.google.com/adsense/answer/1709871?hl=en

Ödeme eşiği (para birimine göre resmi tablo):

> "Payment threshold: $100" (USD)
> "Payment threshold: ₺200" (TRY)

> "You'll be paid out when your outstanding earnings reach the payment threshold, as long as there are no holds on your account"

Ödeme yöntemi — havale (wire transfer): Kaynak: https://support.google.com/adsense/answer/6025222?hl=en

> "Google will issue payouts in either USD or Euros, depending on your country."
> "Funds sent by wire transfer will usually arrive at your bank within three business days."

Türkiye'ye özel bir kısıtlama bu sayfada **bulunamadı** (yalnız Rusya'ya özel bir not var, Türkiye
geçmiyor) — bu, genel akışın Türkiye için de çalıştığına işaret ediyor ama sayfa Türkiye'yi isim
olarak anmıyor.

Address/identity doğrulama eşiği: aynı sayfada "$10 (or local equivalent)" olarak geçiyor (adres
doğrulama), kimlik doğrulama eşiği ise "$0" (yani ilk ödemeden önce zorunlu).

---

### 2.9 Hostinger Affiliate Programı

Kaynak: https://www.hostinger.com/support/1583263-how-are-affiliate-commissions-paid-at-hostinger/

> "The minimum payout is $100 for PayPal and $500 for a bank transfer"

> "Your PayPal e-mail address or bank details"

Komisyon oranı bu spesifik sayfada **bulunamadı** (yalnız ödeme mekaniği anlatılıyor, oran ayrı bir
sayfada — bu araştırmada o sayfa ayrıca WebFetch ile açılıp doğrulanmadı). Türkiye'ye özel bir
kısıtlama veya onay bu sayfada **bulunamadı**.

---

### 2.10 DigitalOcean Affiliate Programı

Kaynak: https://www.digitalocean.com/affiliates

> "Earn 10% for every user you refer to DigitalOcean"
> "Recurring payouts mean you earn all year long for each paying user you refer"

Kaynak: https://www.digitalocean.com/legal/affiliate-program-agreement

> "Commission and Payment. In order to receive payment under this Agreement, you must have: (i) agreed to the terms of this Agreement... (iv) completed any and all required tax documentation..."

Ödeme eşiği, ödeme yöntemi ve ülke kısıtlamaları ayrı bir "Program Policies" belgesinde tutulduğu
belirtiliyor; bu araştırmada o belgeye ulaşılamadı — **bulunamadı**.

---

### 2.11 ElevenLabs Affiliate Programı

Kaynak: https://elevenlabs.io/affiliates

> "Earn up to 22% in commissions over 12 months from qualifying subscriptions"
> "for every new paid subscriber plan, you'll earn 22% of all payments for the first 12 months with no limits"

Business planı için oran ayrıca **%11** olarak WebSearch özetinde görüldü, bu spesifik rakam
elevenlabs.io/affiliates sayfasının WebFetch ile açılan kısmında **birebir doğrulanamadı** — temkinli
okunmalı.

Kaynak: https://elevenlabs.io/affiliate-partner-guide

> "Available payment options include Stripe, PayPal, and Direct Deposit, depending on your country."
> "The accumulated active commission fees are paid out once per month via PartnerStack."

Türkiye'nin bu üç yöntemden hangisiyle ödeme alabileceği sayfada **belirtilmiyor** ("depending on
your country" diyor ama liste yok) — **bulunamadı**.

---

### 2.12 Udemy Eğitmen Gelir Paylaşımı

`www.udemy.com/terms/instructor/`, `about.udemy.com/instructor-revenue-share/`,
`support.udemy.com/hc/en-us/articles/229605008-Instructor-revenue-share`,
`teach.udemy.com/payment-threshold-for-instructor-monthly-payouts-faq/` ve
`support.udemy.com/hc/en-us/articles/115009727168-Instructors-Payoneer-FAQ` —
**denenen tüm Udemy sayfaları WebFetch ile HTTP 403 döndürdü.** Bu araştırmada Udemy'nin gelir
paylaşım oranı (%37/%97 gibi rakamlar WebSearch özetinde görüldü ama doğrulanamadı), ödeme eşiği
($25 iddiası da doğrulanamadı) ve Türkiye'ye Payoneer/PayPal ile ödeme detayları **resmi kaynaktan
teyit edilemedi**. Kurs yayınlamanın kendisi ücretsiz olduğu genel bilgisi dışında bu kanal için
güvenilir bir rakam verilemiyor.

---

## 3. Ulaşılamayan / Doğrulanamayan

- **Patreon** — `support.patreon.com` altındaki tüm sayfalar (ödeme eşiği, Türkiye'nin desteklenen
  ülke listesindeki durumu, Payoneer/PayPal detayları) WebFetch ile HTTP 403 verdi, açılamadı.
- **Ko-fi** — `ko-fi.com` ve `help.ko-fi.com` tamamen WebFetch'e kapalı (403); komisyon oranı, ödeme
  eşiği, Türkiye desteği doğrulanamadı.
- **Medium Partner Program** — `help.medium.com` ve `medium.com/blog` WebFetch ile açılamadı (403);
  Türkiye'nin desteklenen ülke listesinde olup olmadığı, komisyon oranı, ödeme eşiği doğrulanamadı.
- **Udemy** — `udemy.com`, `support.udemy.com`, `teach.udemy.com`, `about.udemy.com` hepsi 403 verdi;
  gelir paylaşım oranı, ödeme eşiği, Payoneer/Türkiye detayları doğrulanamadı.
- **YouTube YPP** — reklam gelirinden yaratıcıya giden yüzde oranı (halk arasında bilinen "%55" rakamı)
  resmi `support.google.com/youtube` sayfasında bu araştırmada bulunamadı.
- **Open Collective** — host fee'nin kesin oranı (%4-10 aralığı yalnız WebSearch özetinde görüldü,
  `docs.opencollective.com/help/fiscal-hosts/fiscal-host-fees` sayfası ayrıca tek tek WebFetch ile açılıp
  birebir doğrulanmadı) ve minimum ödeme eşiği bulunamadı. **Ayrıca:** Wise'ın Türkiye'ye para alımını
  kapatmış olması (§2.6'da kanıtlı) yüzünden Open Collective'in Türkiye'ye gerçek ödeme yolu ciddi
  şüpheli — bu, kesin "hayır" değil ama kesin "evet" de değil; ölçülemedi.
- **GitHub Sponsors** — kesin ödeme eşiği rakamı (yalnız "ayın 22'sinde ödenir" bilgisi WebSearch'te
  görüldü, resmi sayfada WebFetch ile birebir doğrulanamadı) ve Stripe'ın adının geçtiği net cümle
  bulunamadı.
- **Hostinger** — komisyon yüzdesi (yalnız ödeme eşiği/yöntemi doğrulandı, oranın geçtiği ayrı sayfa
  bu araştırmada açılmadı); Türkiye'ye özel kısıtlama bilgisi bulunamadı.
- **DigitalOcean** — ödeme eşiği, ödeme yöntemi ve ülke kısıtlamaları ayrı bir "Program Policies"
  belgesinde olduğu belirtiliyor, o belgeye ulaşılamadı.
- **ElevenLabs** — ödeme eşiği rakamı ve Türkiye'nin desteklenen ödeme yöntemi listesi bulunamadı.
