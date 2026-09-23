# P1 Kararı — Kalıcı veri deposu

Tarih: 23 Eylül 2026 · Karar: Claude (yönetici) · Onay kapısı: Casper
Dayanak: `ARASTIRMA-P1-DEPO.md` + aşağıdaki bağımsız doğrulamalar

---

## 1. Ölçülen durum

| Ne | Gerçek |
|---|---|
| Taşınacak veri | **5,7 MB** — 2 kullanıcı, 4 sohbet, 61 anı, 13 fatura fotoğrafı |
| Bugün nerede duruyor | Vercel'in geçici klasöründe (`/tmp`), sunucu arşivlenince **siliniyor** |
| Kod kaç yerden yazıyor | **12 ayrı yer**, 7'si ortak kökü dinliyor, 5'i dinlemiyor |

Kapasite hiçbir seçenekte sorun değil. Karar **arama yeteneği** ve **uyuma**
üzerinden verildi.

---

## 2. Araştırma ajanının tavsiyesi DOĞRULANDI ve DÜZELTİLDİ

Ajan "Turso, FTS5'i bedava planda eklentisiz veriyor, motor yeniden yazılmaz,
sadece adres değişir" dedi. **Bu yanlış.** Resmî belge birebir şöyle diyor:

> "Full-text search (FTS) in Turso is powered by Tantivy, not SQLite's
> FTS3/FTS4/FTS5 modules. The syntax and functions differ from SQLite FTS."
> — https://docs.turso.tech/sql-reference/functions/fts

Yani Başak'ın hafıza motorundaki `MATCH` ve `bm25()` çağrıları Turso'da
**çalışmaz**; `fts_match()` ve `fts_score()` ile yeniden yazılmaları gerekir.
Bu "adres değişikliği" değil, gerçek iştir.

### Bağımsız doğruladıklarım (Claude, 23 Eylül)

| İddia | Sonuç | Kaynak |
|---|---|---|
| Turso bedava planı var | **DOĞRU** — 5 GB, 100 veritabanı, 500M satır okuma/ay, 10M yazma/ay | turso.tech/pricing |
| Bedava planda uyutma var mı | **Fiyat sayfasında yok** (garanti değil, ifade yok) | turso.tech/pricing |
| Vektör araması yerleşik mi | **DOĞRU** — eklentisiz, `vector_distance_cos`, `vector_top_k`, DiskANN | docs.turso.tech/features/ai-and-embeddings |
| FTS5 destekleniyor mu | **HAYIR** — Tantivy tabanlı, farklı işlevler | docs.turso.tech/sql-reference/functions/fts |
| Turso Cloud'da FTS bugün açık mı | **ÖLÇÜLEMEDİ** — belge söylemiyor | — |

---

## 3. Karar

**Ana depo: Turso. Ama gerçek ölçümden sonra.**

Gerekçe (düzeltilmiş hâliyle):

1. **Motor SQLite şeklinde kalıyor.** Tablolar, bağlantı biçimi, sorgu dili
   aynı. Değişen yalnız kelime aramasının çağrı biçimi. Neon'a geçmek bütün
   hafıza motorunu Postgres'e çevirmek demek — çalışan bir şeye çok daha büyük
   dokunuş. (Çalışan korunur.)
2. **Uyumuyor.** Supabase bedava planda **1 hafta** hareketsizlikte duruyor ve
   elle uyandırmak gerekiyor — kişisel asistan için kabul edilemez. Neon 5
   dakikada sıfıra iniyor ama kendiliğinden uyanıyor (sorun değil, sadece ilk
   istek yavaş).
3. **Alan bol:** 5 GB'a karşı Neon'un 0,5 GB'ı. Başak'ın verisi 5,7 MB, ikisi de
   yeter; ama fotoğraf ve hafıza büyürse fark eder.
4. **Cloudflare D1 elendi:** vektör araması yok, üstelik "5 GB" toplam —
   veritabanı başına 500 MB.

**Fotoğraf/büyük dosya: Cloudflare R2** (10 GB bedava, dışa veri çıkışı bedava).
Vercel istek gövdesi limiti **4,5 MB** olduğu için fotoğraf sunucudan geçemez;
tarayıcıdan doğrudan depoya yüklenmek zorunda.

---

## 4. Kararın açık riski

Turso, SQLite'ı Rust ile yeniden yazıyor ve kelime araması yeni motorda
Tantivy üzerinden. Belgedeki "şu an eksik" listesi:

- Bağlam parçası (snippet) işlevi yok
- Otomatik birleştirme yok — toplu yazmadan sonra `OPTIMIZE INDEX` gerekiyor
- İşlem (transaction) içinde kendi yazdığını okuma yok
- `MATCH` sözdizimi yok

Başak'ın 61 anısı için bunların hiçbiri engel değil. Ama **Turso Cloud'da bu
özelliğin bugün açık olup olmadığı belgede yazmıyor** — bu yüzden karar
ölçümsüz uygulanmayacak.

---

## 5. Uygulama sırası

| Adım | Ne | Durum |
|---|---|---|
| **P1-a** | Dağınık 12 yazma yerini tek köke bağla | Ajanda, sürüyor |
| **P1-b** | Depo arayüzü: çekirdek nereye yazdığını bilmez | Bekliyor |
| **P1-c** | **Turso'da bedava hesap + gerçek ölçüm**: Başak'ın kendi hafıza sorguları orada çalışıyor mu | Casper onayı bekliyor (hesap açma) |
| **P1-d** | Ölçüm tutarsa taşı; tutmazsa aynı arayüzle Neon'a geç | Bekliyor |

**P1-c atlanmaz.** Belge okumak ölçüm değildir. Hesap açılıp Başak'ın gerçek
hafıza sorgusu orada koşturulmadan taşıma yapılmayacak.

Arayüz önce kurulduğu için, ölçüm kötü çıkarsa arka ucu değiştirmek **tek
dosyalık** iş olur — bütün motoru yeniden yazmak değil.


---

## 6. KARAR DEĞİŞTİ — Neon (23 Eylül, ölçümle)

Casper itiraz etti: "Supabase kullanmıyor muyuz, paralel yapı kurma boşuna."
Haklıydı — ikinci bir sağlayıcı eklemek gereksiz karmaşa. Ölçüm yapıldı:

| Ölçüm | Sonuç |
|---|---|
| Supabase proje sayısı | 3 — `Vixrex Project` (aktif), `vixrex-dev` (aktif), `Catalog Bridge` (**uyutulmuş**) |
| Bedava plan sınırı | **2 aktif proje** — dolu. Supabase'in kendi hatası: *"2 project limit... delete, pause or upgrade"* |
| Catalog Bridge silmek yer açar mı | **Hayır** — zaten uyutulmuş, aktif yer tutmuyor |
| `vixrex-dev` boş mu | **Hayır** — 3 mağaza, 5 ürün, 81 konum kaydı, 18 denetim kaydı. Durdurulmaz. |

Başak'ı VixRex'in içine koymak denendi ve **Casper reddetti; haklıydı.** Gerekçe:
ayrı ürün, ayrı veritabanı. İş veritabanında bir taşıma/sıfırlama olursa
kişisel hafıza da etkilenir; VixRex devredilirse kişisel veri içinde gider.
**Kotanın mimariyi belirlemesine izin verilmedi.**

### Seçilen: Neon (Vercel Marketplace üzerinden)

Ayrı hesap açılmadı — Vercel'in kendi pazarından kuruldu, aynı hesap altında.
Kaynak adı: `neon-cyan-clock`, `basak-vercel` projesine bağlandı
(production + preview + development).

### Canlı ölçüm — belge okuma değil, gerçek çalıştırma

| Ne ölçüldü | Sonuç |
|---|---|
| Sunucu | PostgreSQL **18.6** (Neon, us-east-1) |
| `pgvector` | **0.8.6 kuruldu** |
| Türkçe arama ayarı | **var** (`turkish`) |
| Başak'ın gerçek anıları | **61/61 taşındı** (yereldeki sayıyla birebir) |
| Kelime araması | "Casper" → **24 sonuç**, "vixrex" → **12**, "hafıza" → **5** |
| Anlam araması | HNSW indeksi kuruldu, kosinüs uzaklığı doğru sıraladı (kendine uzaklık 0.0000) |
| İkisi aynı sorguda | **Çalışıyor** — kelime süzgeci + vektör aynı sorguda birleşti |

Ölçüm vektörleri sahteydi, ölçümden sonra temizlendi (`vek` kolonu boşaltıldı);
tablo ve indeks duruyor, gerçek gömme değerleri taşıma adımında yazılacak.

### Ölçemediğim tek şey
Neon kaynağının **ücret planı** CLI'dan okunamadı ("No balance information
found"). Kurulum Hobby hesabında ödeme sorulmadan tamamlandı — bedava plan
olduğu sonucu buradan çıkıyor ama **doğrulanmadı.** Dashboard'dan tek bakışta
teyit edilmeli:
https://vercel.com/d/dashboard/integrations/neon/icfg_l7pufkMsViDJLQjIzURh7NS5/resources/store_mp2PpFhAFhlC7Zoz

### Turso neden bırakıldı
Ayrı hesap gerektiriyordu (paralel yapı) ve kelime araması FTS5 değil Tantivy
— Turso Cloud'da bugün açık olduğu belgede yazmıyordu. Neon'da her iki arama
da **canlıda ölçülerek** doğrulandı.
