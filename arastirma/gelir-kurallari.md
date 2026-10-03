# Para kazanma fazı — kurallar

Tarih: 2026-09-25 · Koyan: Claude · Onay: Casper

Bu kurallar Başak'tan gelir elde etme çalışmasının tamamında geçerlidir.
Hangi ajan, hangi araç, hangi oturum olursa olsun bağlayıcıdır.

## 1. Sıfır ön ödeme
Para isteyen hiçbir yol ilk adım olamaz: kayıt ücreti, yıllık üyelik, zorunlu
araç alımı, "önce şuna abone ol". Hepsi elenir. Ön ödemeli yollar ancak gelir
başladıktan sonra yeniden değerlendirilir.

## 2. Ödeme yolu önce, ürün sonra
Türkiye'ye para gönderemeyen platform liste dışıdır — ürün ne kadar hazır
olursa olsun. Bir kanal değerlendirilmeden önce şu kanıtlanır: platformun
**kendi resmî sayfasında** Türkiye desteklenen ülkeler arasında mı, ödeme
hangi yolla geliyor. PayPal Türkiye'de çalışmıyor; "PayPal ile öder" diyen
platform, Türkiye için ödeme yolu yok demektir (aksi resmî sayfada yazmıyorsa).

## 3. Şartlara aykırı yol yok
Ücretsiz katmanla ticari satış yasaksa o kapı kapalıdır. Gerekçe ahlak değil
ölçü: yakalanınca hesap kapanır, biriken emek gider. Kestirme aranmaz.

## 4. Tek kanal, tek seferde
Aynı anda birden fazla gelir kanalı açılmaz. Biri sonuna kadar götürülür,
sonuç ölçülür, sonra diğerine geçilir.

## 5. İlk hedef para değil, ilk ödeme
Kabul ölçütü "şu kadar lira" değil, **zincirin bir kez uçtan uca çalışması**:
biri ödedi, para hesaba geçti. Tutar önemsiz. Zincir kanıtlanmadan büyütme
yapılmaz.

## 6. Fatura kesemeyeceğin işe girme
Sonradan vergi/ceza borcu çıkaran yol gelir değil zarardır. Bir kanal
seçilmeden önce fatura/vergi tarafı resmî kaynaktan (gib.gov.tr) doğrulanır.

## 7. Başak bozulmaz
Gelir uğruna `AGENTS.md` §0 çiğnenmez. Kelime kuralı, çıktı düzenleme, tavan,
chatbot katmanı — hiçbiri "müşteri ister" gerekçesiyle geri gelmez.

## 8. Geri dönüşsüz taahhüt yok
Yıllık sözleşme, iptal edilemez anlaşma, kilitli platform taahhüdü imzalanmaz.

---

## Kanal seçme ölçüsü

Her aday kanal dört ölçüden geçer. Dördünü de geçmeyen kanal hedef olamaz.

| Ölçü | Soru | Kanıt nereden |
|---|---|---|
| Maliyet | Bugün sıfır lirayla başlanabilir mi? | Platformun fiyat sayfası |
| Ödeme | Türkiye'ye para geliyor mu? | Desteklenen ülkeler sayfası |
| Hız | İlk ödemeye kaç adım var? | Kayıt→satış akışı |
| Uyum | Başak değişmeden çalışır mı? | Kod + AGENTS.md §0 |

Dördünü geçen kanal yoksa bu **açıkça yazılır**, en yakını "hedef" diye
sunulmaz.

## Kaynak kuralı

Yalnız platformun/kurumun kendi resmî sayfası. Blog, forum, haber sitesi,
YouTube videosu, danışmanlık yazısı, başka yapay zekânın özeti kaynak
değildir. Bulunamayan bilgiye "bulunamadı" yazılır; tahmin yasaktır.
Rakamın tarihine bakılır — eski tutar güncel sanılmaz.

---

## Yayın ve gelir sırası (2026-09-29 · Casper kararı)

Sıra sabittir, atlanmaz:

1. **Koyeb'e taşınma** — Vercel Hobby ücretsiz planın şartları reklam/
   ticari kullanım kapalı tutuyor; AdSense kodu Vercel'de yayınlanmaz.
   (Kaynak: Vercel kendi kullanım şartları sayfası — 2026-09-29 araştırması.)
2. **AdSense kodu** taşındıktan sonra siteye eklenir (onaylı çerez akışıyla:
   yalnız kullanıcı onayından sonra).
3. **Domain** en sonda — gerekçeler:
   - Domain şimdi alınsa bile Google hemen reklam vermez; onay süreci,
     içerik ve site geçmişi gerektirir — yani domain bugünden gelir
     getirmez, acelesi yok.
   - Search Console mülkü şimdilik URL ön ekiyle kurulu; domain gelince
     Domain mülküne geçilir, kayıp olmaz.
   - Domain, AdSense başvurusundan **hemen önce** alınır (başvuru
     alan adına yapılır).
4. **AdSense başvurusu** — sıralamanın son adımı.

Ek kapı (kural 3 gereği, taşınma öncesi kontrol): ücretsiz AI sağlayıcılarının
(Groq, Gemini, GLM, Cloudflare, Cohere, Mistral, OpenRouter, NVIDIA, Kilo)
**ücretsiz katman maddeleri ticari/ücretsiz hizmet kullanımına izin veriyor mu**
— taşınma ve reklam öncesi resmî sayfalarından tek tek doğrulanır; "bulunamadı"
yazılırsa o sağlayıcı reklamlı dönemde zincirde tutulmaz.

Domain kararı ertelendi (2026-09-29): "Şimdi alan adı alsak bile hemen reklam
vermezler" — sıralamada 3. adım olarak kaldı, ilk adaylıkta değil.

### Base44 değerlendirildi ve elendi (2026-09-29 · Casper sorusu, resmî kaynakla)

Kaynak: base44.com/pricing, base44.com/terms-of-service,
docs.base44.com (Billing and plans / Credits).

- Base44 hosting değil, **içinde uygulama kurulan** yapay zekâ uygulama
  üretici platform (Wix). Mevcut `basak-vercel` FastAPI kodu oraya
  taşınamaz; yeniden kurmak **ikinci beyin** olur (`AGENTS.md` §9 yasak).
- Ücretsiz plan: **5 mesaj/gün, 25/ay** (çalışma alanı geneli — app
  kullanıcılarının sohbet mesajları da bunu harcar), 100 entegrasyon
  kredisi/ay, `xxx.base44.app` alt alan adı + platform rozeti, **kod
  düzenleme yok** (ücretli planda). Halka açık Başak için 1 gün bile yetmez.
- AdSense kodu ücretsiz planda eklenemez (kod düzenleme yok).
- "Beraber yönetme" avantajı doğru (üye daveti tüm planlarda ücretsiz),
  taşımaya yetmez.
- Sonuç: **Başak Koyeb'de kalır** (mevcut kod, kart yok, reklam/ticari
  serbest); Base44 yalnız ayrı bir mini prototip için değerlendirilebilir.
