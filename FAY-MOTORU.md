# FAY MOTORU — Başak'a özel çelişki ve icat algoritması

*22 Ağustos 2026 — Casper (Furkan) için tasarlandı. Genel amaçlı bir ürün değil; bu algoritma başka birinde çalışmaz, çünkü yakıtı Casper'ın kendi dört projesi ve kendi cümleleridir.*

---

## Neden bu algoritma

Casper'ın hakkında biriken her not aynı yaraya işaret ediyor:

- "kod yazıldı ama commit/push YOK — her seferinde git ile doğrula"
- "reddedilen komut yine de çalışmış olabilir — 'yapmadım' demeden önce ölç"
- "dal analizinde önce fetch doğrula — bayat veriyle yanlış rapor verildi"
- "eski liste eskimiş, çoğu kapanmış görünüyor, doğrulanmadan güvenme"
- "kanıtsız 'çalışıyor' deme"
- "ölçmeden değiştirme"

Hepsi tek bir şeyin farklı yüzleri: **söylenen ile gerçek olan arasındaki kayma.**

Casper kod okuyamıyor, İngilizce bilmiyor, günde 10 dakikalık parçalarla çalışıyor, dört projeyi aynı anda yürütüyor ve kodu üç farklı yapay zekâ yazıyor. Bu şartlarda gerçeğin kayması kaçınılmaz. Ve kayma sessizdir — fark edildiğinde iş çoktan yanlış zemine kurulmuştur.

Fikir üreten bir asistan ona bir şey katmaz; fikri zaten fazla, vakti az. **Ona lazım olan, yalanı bulan bir ortak.**

## Metafor: fay hattı

Yer kabuğunda iki plaka birbirine sürtündüğünde fay hattı oluşur. Gerilim yıllarca sessizce birikir, sonra bir anda deprem olur.

Ama fay hatları aynı zamanda **dağların doğduğu yerdir.**

Bu algoritma iki işi birden yapar: gerilimi biriktiği yerde yakalar (risk), ve aynı çatlağı yeni bir şeyin doğduğu yer olarak kullanır (icat).

---

## Mekanizma — 6 organ

### Organ 0 — Tanıklar

Bir **tanık**, dünya hakkında iddia üretebilen her kaynaktır. Kayıtlı tanıklar:

| Tanık | Ne söyler | Nasıl ölçülür |
|---|---|---|
| `belge` | AGENTS.md, GOREV_LISTESI.md, CONTEXT.md, plan dosyaları | dosya okunur |
| `hafiza` | Casper'ın geçmişte söyledikleri | Başak'ın hafıza veritabanı |
| `git` | hangi dal, son commit ne zaman, commit edilmemiş dosya, push edilmemiş iş | `git` komutu |
| `dosya` | dosya gerçekten var mı, ne zaman değişmiş, boyutu | dosya sistemi |
| `canli` | yayındaki site gerçekten ne döndürüyor | HTTP isteği |
| `ajan` | Claude/Kilo/OpenCode raporları | metin |
| `casper` | Casper'ın az önce söylediği | sohbet |

**Kritik tasarım kararı:** `git`, `dosya`, `canli` tanıkları iddialarını **yapay zekâ olmadan** üretir — bunlar ölçülür, üretilmez. Motorun anlamı buradan gelir. Yoksa modellerin birbiriyle tartışmasından ibaret kalır.

Her tanığın konu türü başına bir **güven puanı** vardır. Hepsi 0.5'ten başlar, zamanla öğrenilir (bkz. Organ 5).

### Organ 1 — İddia çıkarma

Başak boştayken bir **konu** seçer (örn. "VixRex kiralık vitrin şu an nerede").

O konu için her ilgili tanıktan iddiasını ister, ve iddiayı **tek kısa cümleye + kaynak işaretine** indirger:

```
konu: vixrex-kiralik-vitrin
  belge  → "kiralık vitrin planı tamamlandı"            (GOREV_LISTESI.md:84)
  git    → "son commit 5 gün önce, 12 dosya commit edilmemiş"
  canli  → "kirala düğmesi yayında ve çalışıyor"        (HTTP 200)
  casper → "biz daha bir tanesini zar zor bu hale getirdik"
```

### Organ 2 — Çarpıştırıcı (paralel jüri)

Her iddia çifti için tek soru: **bunlar birbiriyle çelişiyor mu?**

Bu soru **aynı anda 3 farklı ücretsiz sağlayıcıya** gönderilir (Groq, Gemini, GLM — kotaları ayrı olduğu için 3 paralel çağrının parasal maliyeti 1 çağrıyla aynı: sıfır).

Sonuç 3 oy + 3 tek satırlık gerekçe:

- **3/3 "çelişiyor"** → kesin çatlak, sıraya girer
- **2/1 bölünme** → **asıl değerli olan bu.** Burası gerçek belirsizlik demektir; insan kararı tam olarak burada gerekir. Karşı çıkan gerekçeyle birlikte Casper'a gider.
- **3/3 "sorun yok"** → sessizce atılır, Casper hiç görmez

> **Bu, mevcut kurgunun tersine çevrilmesidir.** Şu an 7 sağlayıcı birbirinin *yedeği* olarak sırayla deneniyor. Burada birbirinin *jürisi* oluyorlar — ve aralarındaki anlaşmazlık bedava bir belirsizlik ölçeri hâline geliyor. Kimse yedek zincirini böyle kullanmıyor.

### Organ 3 — Gerilim puanı

Çatlaklar soyut "önem"e göre değil, **gerilime** göre sıralanır:

```
gerilim = yayılma × tazelik × maliyet
```

- **yayılma:** yanlış tarafa kaç başka plan maddesi / dosya / konu yaslanıyor (hafıza grafiği + belgelerde kaç kez atıf var)
- **tazelik:** Casper en son ne zaman bu yanlış tarafın üstüne iş yaptı (şu an üstüne inşa ediyorsa acildir)
- **maliyet:** düzeltme gecikirse ne kadar pahalılaşır — yanlış taraf ne kadar ileri gitmiş: *yayında > birleştirilmiş > commit edilmiş > yerel*

Eşiğin altındakiler gösterilmez ama **silinmez de** — o fay hattında sessizce gerilim birikir. Gerilim biriktikçe o çatlağın eşiği düşer. Yani küçük ama hiç çözülmeyen bir tutarsızlık, günler sonra kendiliğinden yüzeye çıkar.

Deprem modeli budur ve gerçek bir sıralama mekanizmasıdır, süs değil.

### Organ 4 — Aktarıcı (icat eden yarı)

En yüksek gerilimli çatlak sadece raporlanmaz — **çözülmeye çalışılır**:

1. Çatlak bir çelişki şekline indirgenir: *"X istiyorum ama Y engelliyor."*
2. **Önce Casper'ın kendi külliyatında** aranır: dört projenin belgeleri, hafızası, git geçmişi. Aynı *şekle* sahip ama farklı konuda, **daha önce çözülmüş** bir çelişki var mı?
3. İçerik değil, **mekanizma** aktarılır.
4. Kendi külliyatında eşleşme yoksa ancak o zaman dışarı (web/literatür) çıkılır.

Casper'ın kendi çözülmüş çelişki havuzundan örnekler:

| Proje | Çelişki | Casper'ın çözümü (mekanizma) |
|---|---|---|
| VixRex | kullanıcı kod bilmiyor ama site düzenlemeli | tıkla-değiştir + asistan taslak üretir + yayın ayrı onay kapısı |
| Xses | içerik otomatik çekilmeli ama izin alınamıyor | kullanıcı kendi hesabıyla kendi içeriğini onaylar + CSV alternatifi |
| Başak | bulut istemiyorum ama güçlü model lazım | ücretsiz zincir + yerel son çare, kimlik hep yerelde |
| VixRex | eksik özellik eleştirisi geliyor ama kapsam kasıtlı dar | eksikliği bilinçli ilan et, tam sürümü ayrı ürün yap |

Örnek aktarım: *"Xses'te izin sorununu 'kullanıcı kendi onaylasın' diye çözmüştün. NumeraMatch'teki 18+ kapısı aynı şekle sahip — orada da onayı kullanıcıya verip mağaza engelini kaldırabilirsin."*

> **Bu yarı yalnızca Casper'da çalışır.** Dört ayrı projeyi tek bir kafa, tek bir zevkle yürüttüğü için elinde başka kimsede olmayan bir çözülmüş-çelişki külliyatı var. Şu an dağınıklık gibi görünen çok-projelilik, burada **hammadde** hâline geliyor.

### Organ 5 — 10 dakikalık kapı

Çıktı biçimi kozmetik değil, **kodla dayatılan bir sözleşmedir**:

- Aynı anda **en fazla 1 fay hattı** gösterilir. Asla liste değil.
- Biçim: 1 cümle ne çatladı · 2 satır kanıt (her taraf, kaynağıyla) · 1 aktarım önerisi · 2-3 seçenekli tek soru.
- Tezgâhın başında, sesle, 10 dakikanın altında cevaplanabilir olmalı.
- Cevap gelmezse **dırdır etmez**. Gerilim birikir, sonra daha üst sırada döner.

Örnek kart:

```
FAY — VixRex kiralık vitrin

  Belge diyor:  "plan tamamlandı"            (GOREV_LISTESI.md)
  Git diyor:    "12 dosya 5 gündür commit edilmemiş"

  Jüri: 3/3 çelişiyor.
  Gerilim: yüksek — son 3 gündür bu planın üstüne iş yapıyorsun.

  Aktarım: Başak'ta "kanıt olmadan faz kapanmaz" kuralını koymuştun.
           VixRex'te aynı kural yok.

  Soru: Bu 12 dosya (a) bitti, kaydedilecek  (b) yarım, bekleyecek  (c) çöp
```

### Organ 6 — Karne (öğrenme)

Casper'ın cevabı **tek etikettir** — ve motorun tek öğrenme sinyali:

- *"haklısın, kırık"* → yanlış taraftaki tanık o konu türünde güven kaybeder
- *"yanlış alarm"* → çatlağı çıkaran kural / tanık güven kaybeder

Haftalar içinde motor şunu **veriden türetir**: *"belge tanığı 'tamamlandı' derken git tanığıyla %70 çelişiyor."* Bu, Casper'ın şu an kafasında tutmak zorunda olduğu dersin ta kendisi. Artık hatırlamak zorunda kalmaz.

Aynı sinyal jüri üyeleri için de tutulur: hangi sağlayıcı hangi konuda isabetli. Bu doğrudan mevcut model seçicisini besler (planındaki P3/P4).

---

## Neden tam olarak Casper'a uyuyor

| Casper'ın kısıtı | FAY'ın cevabı |
|---|---|
| Kod okuyamıyor | Okumayı tanıklar yapar; o sadece iki cümle arasında hakemlik eder |
| 10 dakikalık parçalar | Kapı zaten bu birime göre tasarlandı, tek kart tek karar |
| Parası yok | Jüri 3 ayrı ücretsiz kotayı paralel kullanır; ölçen tanıklar (git/dosya/http) bedava |
| Uzmandan çekiniyor | Jüri ikinci görüştür ve yaltaklanmaz; anlaşmazlığı dürüsttür |
| Küçümsenme korkusu | Sistem asla "bunu bilmen lazımdı" demez. "Bu iki kaynak çelişiyor, hangisi doğru?" der. Öğrenci değil, hakemdir |
| Dört proje, üç ajan, kayan gerçek | Motorun tam olarak saldırdığı sorun bu |
| Uzun kesintiden sonra dönüyor | Fay listesi zaten "şu an gerçekte neredeyim"in kendisi |

---

## Dürüst olan kısım: neyi icat ettik, neyi etmedik

Parçaların tek tek karşılıkları literatürde var:

- **Modeller arası anlaşmazlığı belirsizlik sinyali saymak** — var (LLM jürileri, DiscoUQ, CoE). Ama laboratuvarda, cevap kalitesi ölçmek için. Ücretsiz yedek zincirini jüriye çevirmek için değil.
- **Belge ↔ kod kayması yakalamak** — var (Mintlify, CI kontrolleri, şema kayması araçları). Ama yazılımcı ekipler için, kod okumayı gerektirir, tek projede çalışır, "ajan yaptım dedi" tanığını kapsamaz.
- **Bilgi tabanında çelişki avı** — var (KnowledgeBase Guardian, FAQ çakışma tespiti). Ama metin ↔ metin. Metin ↔ **gerçeklik** (git, dosya, canlı site) değil.
- **Çelişkiden icat çıkarmak (TRIZ)** — var (AutoTRIZ, TRIZ-RAGNER). Ama patent külliyatında, mühendislik alanında. Kişinin kendi projelerinden değil.

**Birleşimi yok.** Ölçen tanıklar + ücretsiz paralel jüri + gerilim sıralaması + kendi külliyatından mekanizma aktarımı + tek etiketle öğrenen güven karnesi — bu beşlinin bir arada olduğu bir şey bulunamadı.

Dahası: bu bir ürün olarak **var olamaz** da. Çünkü çalışması için Casper'ın özel külliyatına ihtiyacı var. Satılabilir bir kutu değil; tek kişiye ait bir organ.

Bu "süper zekâ" değil. Bu, kimsenin yapmadığı bir şeyi yapan küçük ve keskin bir motor.

---

## Kurulum sırası — küçük başla, kanıtla

Casper'ın kendi kuralı geçerli: kanıt olmadan sonraki faz açılmaz.

### FAY-0 — tek konu, üç tanık, jürisiz *(ilk hedef)*

En küçük çalışan hâl. Yapay zekâ neredeyse hiç yok — çoğu ölçüm.

- Tanıklar: `belge`, `git`, `dosya` (üçü de bedava, üçü de kesin)
- Konu: **tek bir tane** — "VixRex şu an gerçekten nerede"
- Çarpıştırma: tek yerel model, jüri yok
- Çıktı: tek kart, Başak sohbetinde
- **Kabul ölçütü:** kartta yazan çelişki gerçek çıkacak. Casper git'e bakıp "evet, öyleymiş" diyecek. Uydurma tek bir çelişki bile çıkarsa faz kapanmaz.

### FAY-1 — paralel jüri
3 ücretsiz sağlayıcı aynı anda oy verir, 2/1 bölünmeler işaretlenir.
**Kabul:** yanlış alarm sayısı FAY-0'a göre gözle görülür düşer; en az bir 2/1 bölünme yakalanır ve gerçekten tartışmalı çıkar.

### FAY-2 — gerilim ve kuyruk
Yayılma/tazelik/maliyet puanı, biriken gerilim, dırdır etmeyen kuyruk. Dört proje birden.
**Kabul:** günde en fazla 1 kart çıkar ve Casper "bu gerçekten en önemlisiydi" der.

### FAY-3 — aktarıcı
Kendi külliyatından mekanizma transferi.
**Kabul:** Casper'ın "bunu ben düşünmemiştim" dediği en az bir aktarım.

### FAY-4 — karne
Tanık güven puanları öğrenmeye başlar, model seçicisine bağlanır.

> Sonraki fazın ayrıntısı, o an kodun gerçek hâline bakılarak yazılır. Şimdiden hepsini yazma.

---

## Değişmeyecekler

- Her şey yerel kalır. Fay kayıtları Başak'ın kendi veritabanında.
- Ücretli çağrı varsayılan kapalı — jüri yalnız ücretsiz kotalarla çalışır.
- Motor **hiçbir şeyi kendi başına düzeltmez.** Sadece gösterir ve sorar. Kararı Casper verir.
- Kart sözleşmesi bozulamaz: tek fay, tek soru, 10 dakika.
- Güvenlik politikasını ve izin sistemini motor değiştiremez.

## Mevcut parçalardan yeniden kullanılacaklar

- `research-engine` kenarda duruyor ama iki parçası buraya uyar: **puanlı eleme turnuvası** (Organ 3) ve **özel külliyat okuyucu** (Organ 4). Motorun tamamını bağlamaya gerek yok, iki parçayı ödünç almak yeter.
- Hafıza motoru (`memory/engine.py`) zaten hem anlam hem kelime araması yapıyor — Organ 4'ün aradığı "aynı şekle sahip eski çelişki" araması bunun üstüne kurulur.
- Kota ve izin katmanı (`brain/kota.py`, `tools/permissions.py`) paralel jürinin ücretsiz kalmasını zaten garanti ediyor.
