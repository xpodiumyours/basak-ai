# BAŞAK — BEYİN VERİMLİLİĞİ VE GELİR ARAŞTIRMASI

Tarih: 2026-09-22 | Yazan: Buffy (Codebuff) | Onay: Casper (bekliyor)
Amaç: "kota yetmiyor" şikâyetini ölçüye çevirmek ve sıfır bütçeyle
uygulanabilir, küçük ama etkili dokunuşları sıraya koymak.
Bu dosya bir GELİŞTİRME PLANI değildir (o: `ANA-PLAN.md` kuralı geçerli);
bir araştırma ve karar notudur.

---

## 0. ÖLÇÜM — şikâyetin sayısı (kanıt: `data/audit/audit.log`)

Log'daki 321 satırın **169'u test/probe gürültüsü** (0.0 sn'lik satırlar).
Gerçek trafik yalnız 152 satır. Yani kendi ölçü aletimiz yarıdan fazla kirli.

Temiz 152 kaydın tablosu:

| Durum | Adet |
|---|---|
| OK | 89 |
| HATA (tek sağlayıcı düştü, sıradaki devraldı) | 38 |
| **TAM BAŞARISIZLIK (hiçbir sağlayıcı cevap veremedi)** | **25** |

**25 tam başarısızlık ≈ her 4-5 mesajdan biri hiç cevap alamıyor.**
"Kota yetmiyor" şikâyeti bu sayıdır.

Sağlayıcı başına (temiz kayıt):

| Sağlayıcı | Deneme | Hata | Hata oranı | Not |
|---|---|---|---|---|
| groq | 71 | 19 | %27 | hataların 14'ü **429 kota** — iş yükünü o çekiyor |
| gemini | 27 | 7 | %26 | 429; ücretsiz katmanda `gemini-3-flash` **günde 20 istek** |
| kilo | 10 | 1 | %10 | anahtarsız, en temiz ikinci hat |
| glm | 8 | 6 | **%75** | 429 + okuma zaman aşımı |
| nvidia | 4 | 3 | **%75** | yalnız zaman aşımı |
| openrouter | 7 | 2 | %29 | günde 50 istek |
| TAM BAŞARISIZLIK | 25 | — | — | zincir tümden boş |

Ayrıca log'da tekrar eden somut bir hata var (2026-09-20, birkaç kez):

```
HATA kaynak=groq (0.6 sn): Error code: 400 -
"Tool call validation failed: attempted to call tool 'gorevler'
 which was not in request.tools"
```

Model `yetenek_ac` aracını çağıracağına, **alan adını bir araç sanıp**
çağırıyor. Böyle her tur: 1 istek + token harcanıyor, karşılığında hiçbir
şey üretilmiyor. Ölü kota budur.

---

## 1. KÜÇÜK AMA BÜYÜK ETKİLİ DOKUNUŞLAR (öncelik sırası)

### A. Cloudflare Workers AI anahtarını geri koy (EN BÜYÜK TEK KAZANÇ)
Ölçüm (2026-09-11 kaynağı): Cloudflare ücretsiz planı **günde 10.000 Neuron**,
**kart istemez**, 300 istek/dakika, ve **verini eğitimde kullanmaz**.
Bu bütçe yaklaşık olarak: gpt-oss-120b'de ~147.000 çıktı token'ı,
Llama 3.3 70B'de ~49.000 — yani Groq'un günlük 200.000 token'ından
sonra ikinci büyük bedava hat.

Kod **zaten hazır**: `brain/adapters/cloudflare_adapter.py` + registry kartı
(`gunluk_neuron: 10000`). Yapılacak tek şey `ayarlar.json`'a
`cloudflare_account_id` + `cloudflare_api_token` yazmak.
Süre: ~15 dakika. Bugünkü %22 başarısızlığı tek başına yarıya indirebilecek
hamle budur.

> Karar bekliyor: anahtar eklenirse matris kapsamı 7 → 8 sağlayıcıya çıkar
> (8 × 52 = 416 hücre) ve `tests/live/matris_kosucu.py` → `KAPSAM` ile plan
> dokümanı birlikte güncellenir.

### B. Boşa yanan kotayı kes
1. **`gorevler` hatası**: model alan adını araç sanıyor. Ya `yetenek_ac`
   şeması ikinci turda daha net sunulur, ya da bu 400'ü aldığımızda aynı
   istek körü körüne 4 kez tekrarlanmaz (bugünkü log'da ard arda 4 kez
   denendiği görünüyor).
2. **gemini'yi zincirin başına koymak kâr değil zarar**: günde 20 istek
   olan bir hattı 2. sıraya koymak, her mesajda 1 isteği çöpe atıyor.
   Ölçülen gerçek limit registry kartına yazılmalı (şu an "model/proje
   bazlı" diyor — pratikte 20).
3. **glm + nvidia**: ikisi de %75 hatalı. Zincirde tutulacaklarsa en sona;
   zaman aşımı soğumaları uzatılmalı (zaten 300 sn soğuma var, yetmiyor).

### C. Ölçü aletini ayır
Test ve probe koşuları gerçek audit dosyasına yazdığı sürece "hangi
sağlayıcı iyi" kararı kirli veriyle verilir. Testler kendi log dosyasına
yazmalı. (Bugünkü sayıların %53'ü bu yüzden çöptü.)

### D. Aynı cevabı iki kez satın alma
Prompt/prefix önbelleği zaten var. Eksik olan: **cevap önbelleği** —
aynı soru (özellikle "saat kaç", "hava nasıl") tekrar gelirse kota
harcamadan önceki cevap döner. Küçük iş, doğrudan kota tasarrufu.

### E. Yerel küçük model = bekleme değil, ucuz işçi
Ölçülen: yerel 7B CPU'da ~13 sn. Bu yüzden yerel model *sohbeti* taşıyamaz.
Ama **özetleme / etiketleme / hafıza damıtma** gibi kısa ve ardışık
işler için yeterli. Pahalı muhakeme bulutta kalır; sıkıcı iş yerelde.

---

## 2. "DAHA ÇOK MODEL BAĞLAMAK" NEDEN TEK BAŞINA ÇÖZMEZ

Sayıyı artırmak üç bedel getiriyor: (1) her yeni sağlayıcı kendi
başarısızlık oranını getiriyor (nvidia %75), (2) kurulum/bakım yükü
artıyor, (3) asıl darboğaz **istek sayısı değil, kullanılabilir kaliteli
kota**. Doğru yön: **az sayıda geniş kotalı hat + kalanı yedek** — bugünkü
sıra bunun tersi (groq işi çekiyor, gemini sürekli 429).

---

## 3. ADAY SAĞLAYICILAR (kaynak: 2026-09-11 tarihli bağımsız test listesi)

| Sağlayıcı | Bedava ne veriyor | Kart | Bizdeki durum |
|---|---|---|---|
| **Cloudflare Workers AI** | 10.000 Neuron/gün, ~147K token | yok | kod var, **anahtar yok** |
| Google Gemini | Flash modeller, limit AI Studio'da | yok | var; pratikte **günde 20** |
| Groq | 30/dk, 1000/gün, **8.000 token/dk** | yok | var; TPM dar |
| OpenRouter | 19 `:free` model, **50/gün** | yok | var (dar) |
| Mistral | **ayda 10 dolar kredi** | yok | var (sonda) |
| Cohere | 1000 çağrı/ay | yok | **anahtar yok**; *ticari kullanım YASAK* |
| Hugging Face | ayda 0,10 dolar kredi | yok | kapalı (anlamsız) |
| NVIDIA | 40 istek/dk, prototip amaçlı | sorulmuyor | var; %75 hata |
| Z.ai (GLM) | GLM-4.7-Flash, 4.5-Flash bedava | belirsiz | var; %75 hata |

**Kapananlar (2026 Haziran'dan beri):** SambaNova, Cerebras, GitHub Models,
Together AI — bedava tekliflerini bitirdiler.
Ders: "yeni sağlayıcı ekle" tavsiyesi **her ay yeniden doğrulanmalı**;
hafızadan öneri yapılmaz.

> Cohere ticari kullanımı yasakladığı için **para kazanma yolunda
> kullanılamaz** — bunu zincire koyarken bilmek gerekir.

---

## 4. GELİR YOLLARI (Türkiye gerçeğiyle)

**Önce kısıt (araştırıldı):** PayPal Türkiye'de 2016'dan beri kapalı;
Wise Türkiye'den para **kabul ettirmiyor**; Stripe yok. Yani "GitHub
Sponsors açalım" tipi planlar ödeme altyapısına takılır. **Her yol, para
akışı 1 TL'lik denemeyle doğrulanmadan plana yazılmaz.**

Sırayla (en kolaydan):

1. **Türkiye içi hizmet satışı (en yüksek olasılık).**
   Ürün: "Başak'ı bilgisayarına kuruyorum + 1 saat kullanım desteği."
   Ödeme: IBAN/havale — hiçbir yabancı altyapı gerekmez.
   Kanal: çevre, esnaf, Bionluk/Armut gibi Türk platformları.
   Neden bu: kod yazmayı bilmeden **kurulum ve destek** satılabilir;
   AI zaten işi yapıyor. Sıfır maliyet, aynı gün başlanabilir.
2. **Türk bağış platformları:** Kreosus, Shopier (destek ürünü).
   Türk banka hesabına ödeme yapar; yabancı rail gerekmez.
3. **Yurt dışı freelance:** platform (Fiverr/Upwork) ödemeyi **Payoneer**'e
   yatırır; oradan Türk bankasına. Kurulum 1-2 gün, kesinti yüksek.
4. **İçerik + kitle:** Türkçe günlük "sıfır bütçeyle kendi Jarvis'imi
   yapıyorum". Geliri reklam değil, **güven**: danışmanlık, kurulum talebi,
   sponsor. Aylarca sürer, ama 1. ve 3. maddeyi besler.
5. **Ürünleştirme:** "Vitrin asistanı" paketi (Vixrex tarafı) — kurulum
   paketi + destek satışı. AGPL engel değil: **kod açık kaldığı sürece
   satmak serbest**, yalnız kapalı kutuya çevirip satmak yasak.

---

## 5. AÇIK KAYNAK (halka açma) STRATEJİSİ

Lisans zaten uygun (AGPL-3.0): indir, değiştir, paylaş, hatta hizmet olarak
sun — yeter ki kod açık kalsın.

Ama "halka açmak" kendiliğinden para getirmez. Para getiren hâli:

- **Anlaşılır kapı**: İngilizce 10 satırlık özet + tek ekran görüntüsü +
  "kendi makinene 5 dakikada kur" rehberi (README'nin İngilizce özeti).
- **Kanıt vitrini**: ekran görüntüsü/GIF, `doktor.py` çıktısı, test rozeti.
  (Bu proje kanıt kültürüyle yazılmış; en güçlü satış argümanı bu.)
- **Katkı kapısı**: issue şablonu + "good first issue" etiketleri.
- **Sürüm notları**: her hafta kısa bir "bu hafta ne değişti" yazısı.

Gerçek beklenti: açık kaynak **doğrudan para getirmez**, **talep getirir**.
Para 4. maddedeki hizmetlerden gelir.

---

## 6. SIRADAKİ 5 İŞ (ucuzdan pahalıya, öneri)

| # | İş | Süre | Beklenen etki |
|---|---|---|---|
| 1 | Test/probe log'unu gerçek audit'ten ayır | 30 dk | Ölçüm güvenilir olur; her karar düzelir |
| 2 | Cloudflare anahtarını ekle | 15 dk | %22 başarısızlık belirgin düşer |
| 3 | gemini'nin gerçek limitini karta yaz + sıradaki yerini ölçüme göre düzelt | 1 saat | Her mesajda yanan 1 istek durur |
| 4 | Cevap önbelleği (tekrar sorular) | 2 saat | Doğrudan kota tasarrufu |
| 5 | Kurulum hizmeti denemesi (1 müşteri, IBAN) | 1 gün | İlk gerçek gelir sinyali |

Hepsi Casper onayı bekler. Hiçbiri "cevaba dokunan kod" değildir; hepsi
ölçüm/kapasite işidir.
