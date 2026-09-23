# Başak — Kalıcı Depo Araştırması (Faz 1)

Araştırma tarihi: 23 Eylül 2026
Kural: yalnız ürünün kendi resmî belgesi/fiyat sayfası kullanıldı. Bulunamayan her şey açıkça "BULUNAMADI" yazıldı.

---

## Özet — 5 madde

1. **Vercel'in `/tmp` klasörü kalıcı değil.** Dağıtım klasörü salt okunur (yazılamaz), yalnız `/tmp` yazılabilir ve 500 MB'a kadar. Vercel iş yoğunluğuna göre yeni "örnek" (instance = uygulamanın çalışan kopyası) açar; iki ayrı örneğin aynı `/tmp`'yi paylaştığını söyleyen resmî bir cümle yok. Yani bugünkü durum (veri `/tmp`'de) hiçbir şekilde güvenli değil.
2. **Başak'ın verisi 5,7 MB.** Listedeki bedava seçeneklerin hepsi bu boyutu rahat taşıyor. Karar kapasiteye göre değil, **arama yeteneğine** göre verilmeli.
3. **Tam metin arama + vektör aramasını bedava planda BİRLİKTE veren tek net seçenek Turso.** FTS5 (tam metin arama) her veritabanında önceden yüklü, vektör araması ise libSQL'in kendi içinde, eklenti gerektirmiyor. Bedava planda kısıt belirtilmemiş.
4. **Supabase ikinci seçenek:** Postgres'in kendi tam metin araması eklentisiz çalışıyor, vektör için `pgvector` eklentisi açılıyor. Ama bedava projeler **1 hafta hareketsizlikte duraklatılıyor** ve veritabanı 500 MB ile sınırlı.
5. **Cloudflare D1 elendi:** FTS5 var ama vektör araması YOK (Cloudflare'in vektör ürünü ayrı). Neon ve Upstash de tek başına iki aramayı birlikte vermiyor. Fotoğraf gibi büyük dosyalar için en bol bedava alan **Cloudflare R2** (10 GB, dışarı veri çıkışı bedava).

---

## Soru 1 — Vercel fonksiyonlarında `/tmp` klasörü

### Bulgu

| Konu | Gerçek |
|---|---|
| Dağıtım klasörü yazılabilir mi? | **Hayır.** "Vercel functions have a read-only filesystem" (salt okunur dosya sistemi) |
| Yazılabilir yer | Yalnız `/tmp` |
| `/tmp` boyutu | **500 MB**'a kadar ("writable `/tmp` scratch space up to 500 MB") |
| Ömrü | Fonksiyon çağrılmadığında arşivlenir: **üretimde 2 hafta içinde**, ön izlemede **48 saat içinde**. Arşivden dönüş, ilk açılışı en az 1 saniye yavaşlatır. |
| İki ayrı sunucu örneği paylaşır mı? | Resmî belge şunu diyor: Vercel, "çalışan hiçbir örnekte boş kapasite kalmadığında yeni bir örnek başlatır". Paylaşım yalnız **aynı örnek** içinde geçerli: "multiple invocations can share the same physical instance and its global state". İki **ayrı** örneğin `/tmp`'sini paylaştığını söyleyen cümle → **BULUNAMADI** (yani garanti yok, paylaşmadığını varsaymak zorunlu). |

Ek ölçü: fonksiyonun tamamı için 1.024 dosya tanıtıcısı (açık dosya/bağlantı sayacı) sınırı var, eşzamanlı tüm çalışmalar bunu paylaşıyor.

### Kaynak
- https://vercel.com/docs/functions/runtimes — belge tarihi **12 Ağustos 2026** (dosya sistemi, 500 MB, arşivleme)
- https://vercel.com/docs/fluid-compute — belge tarihi **24 Ağustos 2026** (örnek paylaşımı, global durum)
- https://vercel.com/docs/fundamentals/what-is-compute — belge tarihi **11 Ağustos 2026** (yeni örnek ne zaman açılır)
- https://vercel.com/docs/functions/limitations — belge tarihi **24 Ağustos 2026** (dosya tanıtıcısı)

### Başak için anlamı
Bugünkü kurulum "bazen çalışıyor" gibi görünebilir: aynı örnek bir süre ayakta kaldığı için veri kısa vadede duruyor. Ama iki gerçek var: (a) örnek arşivlenince `/tmp` gidiyor, (b) ikinci bir örnek açılırsa o örnek verini hiç görmüyor. Yani veri kaybı rastgele ve tekrar üretilmesi zor. Kalıcı depoya taşıma zorunlu, tercih değil.

---

## Soru 2 — Bedava kalıcı depo seçenekleri (Eylül 2026 gerçek limitleri)

### Karşılaştırma tablosu

| Servis | Bedava depolama | Okuma / yazma limiti | Kullanılmayınca uyur mu? | Bağlantı limiti |
|---|---|---|---|---|
| **Supabase** (Postgres) | 500 MB veritabanı + 1 GB dosya | "Unlimited API requests" (sınırsız istek); 5 GB dışa veri + 5 GB önbellekli dışa veri; 50.000 aylık aktif kullanıcı | **EVET — 1 hafta hareketsizlikte duraklatılıyor.** En fazla 2 aktif proje | Nano boyut: **60** doğrudan bağlantı, **200** havuz (pooler) istemcisi |
| **Turso** (libSQL/SQLite) | **5 GB** | **500 milyon satır okuma/ay**, **10 milyon satır yazma/ay**; 3 GB eşitleme/ay; 100 veritabanı | Fiyat sayfasında uyuma/arşivleme ifadesi → **BULUNAMADI** | HTTP üzerinden çalışıyor; sayısal bağlantı limiti → **BULUNAMADI** |
| **Neon** (Postgres) | 0,5 GB / proje | 100 CU-saat / proje; 5 GB dışa veri / proje; 10 dal / proje; 100 proje | **EVET — 5 dakika sonra sıfıra iniyor, "kapatılamaz"**. Limit aşılırsa yazma durur, veri silinmez | Havuz: `max_client_conn` = **10.000**, `default_pool_size` = `max_connections`'ın %90'ı |
| **Upstash Redis** | 256 MB | **500.000 komut/ay**; 10 GB bant genişliği/ay; tek istek en çok 10 MB | Belgede ifade → **BULUNAMADI** | HTTP üzerinden bağlantısız çalışıyor; eşzamanlı bağlantı sayısı → **BULUNAMADI** |
| **Vercel Blob** (dosya) | 1 GB / ay | 10.000 basit işlem + 2.000 ileri işlem + 10 GB veri transferi; hız sınırı 1.200 basit/dk, 900 ileri/dk | Uyumuyor; ama **limit aşılırsa 30 gün boyunca erişim kapanıyor** | Yok (HTTP) |
| **Cloudflare D1** (SQLite) | **Toplam 5 GB**, ama **veritabanı başına yalnız 500 MB**; en fazla **10 veritabanı** | **5 milyon satır okuma/gün**, **100.000 satır yazma/gün**; çağrı başına 50 sorgu | Uyumuyor; günlük limit dolarsa sorgular hata veriyor | Worker çağrısı başına en çok 6 eşzamanlı D1 bağlantısı |
| **Cloudflare R2** (dosya) | **10 GB-ay** | 1 milyon Class A (yazma tipi) / ay, 10 milyon Class B (okuma tipi) / ay | Uyumuyor | Yok (S3 uyumlu HTTP) |

Not: "Class A / Class B" = Cloudflare'in işlem türü ayrımı; Class A yazma/listeleme gibi pahalı işlemler, Class B okuma gibi ucuz işlemler.

### Kaynak
- Supabase: https://supabase.com/pricing (canlı fiyat sayfası, 23 Eylül 2026'da okundu) + https://supabase.com/docs/guides/platform/compute-and-disk (bağlantı sayıları)
- Turso: https://turso.tech/pricing (23 Eylül 2026'da okundu)
- Neon: https://neon.com/pricing + https://neon.com/docs/connect/connection-pooling
- Upstash: https://upstash.com/pricing/redis
- Vercel Blob: https://vercel.com/docs/vercel-blob/usage-and-pricing — belge tarihi **8 Eylül 2026**
- Cloudflare D1: https://developers.cloudflare.com/d1/platform/pricing/ + https://developers.cloudflare.com/d1/platform/limits/
- Cloudflare R2: https://developers.cloudflare.com/r2/pricing/

### Başak için anlamı
- Kapasite hiçbir seçenekte sorun değil (5,7 MB'a karşı en küçük seçenek 256 MB).
- Gerçek risk **uyuma**: Supabase 1 hafta kullanılmazsa duruyor, Neon 5 dakikada sıfıra iniyor. Neon'un 5 dakikası sorun değil (istek gelince uyanır, sadece ilk istek yavaş), ama Supabase'in 1 haftası gerçek bir risk — Başak kişisel asistan, bir hafta hiç kullanılmayabilir ve o zaman elle uyandırmak gerekir.
- D1'in "5 GB" rakamı yanıltıcı: **tek veritabanı yalnız 500 MB** olabiliyor, üstelik günde 100.000 satır yazma sınırı var.

---

## Soru 3 — Bedava planda tam metin arama + vektör aramasını BİRLİKTE veren seçenekler

### Bulgu

| Servis | Tam metin arama | Vektör araması | Birlikte bedava mı? |
|---|---|---|---|
| **Turso** | **VAR — FTS5 önceden yüklü.** Turso, tüm veritabanlarında önceden yüklü eklentileri şöyle sayıyor: JSON, **FTS5**, R*Tree, SQLean Crypto, Fuzzy, Math, Stats, Text, UUID. FTS5 "her zaman açık ve kullanılabilir" | **VAR — eklenti gerekmiyor.** "Vector Similarity Search is built into Turso and libSQL Server as a native feature" ve "without an extension". Fonksiyonlar: `vector32`, `vector64`, `vector_distance_cos`, `vector_distance_l2`, `vector_extract`; indeks için `libsql_vector_idx`, arama için `vector_top_k()` | **EVET.** İkisi de her veritabanında; plan kısıtı belirtilmemiş |
| **Supabase** | **VAR — eklentisiz.** "Postgres has built-in functions to handle Full Text Search queries. This is like a 'search engine' within Postgres." `to_tsvector()` / `to_tsquery()` doğrudan kullanılıyor, eklenti gerekmiyor, plan kısıtı belirtilmemiş | **VAR — `pgvector` eklentisi açılarak.** Panelden veya `create extension vector with schema extensions;` ile açılıyor | **Muhtemelen evet**, ama "bedava planda pgvector vardır" diyen açık cümle → **BULUNAMADI**. Belgeler plan kısıtından hiç söz etmiyor |
| **Cloudflare D1** | **VAR — FTS5.** "FTS5 module for full-text search (including `fts5vocab`)" | **YOK.** Desteklenen eklentiler yalnız: "FTS5 module... JSON extension... Math functions." `sqlite-vec` veya herhangi bir vektör eklentisi listede yok; D1'in kendisinde vektör benzerlik araması belgelenmemiş | **HAYIR** |
| Neon / Upstash | Neon Postgres olduğu için tam metin araması var (Postgres'in kendisi), pgvector de Postgres eklentisi — ama Neon belgelerinde bedava plan için bunu doğrulayan satır aranmadı | — | Doğrulanmadı |

Turso hakkında iki önemli ayrıntı:
- `sqlite-vec` eklentisi ayrıca sunuluyor ama **yalnız Fly Cloud sağlayıcısında, Pro ve Enterprise planlarda.** Turso'nun kendi tavsiyesi: eklenti yerine "native libSQL vector datatype" (yerleşik libSQL vektör türü) kullanmak. Bedava planda çalışacak olan bu yerleşik olan.
- Turso'nun yeni nesil motorunda (Rust ile SQLite'ı sıfırdan yazma projesi) tam metin arama FTS5 yerine Tantivy ile yapılıyor ve **deneysel** durumda. Bugün Turso Cloud'da kullanılan hâlâ FTS5. Bu bir gelecek riski, bugünkü bir engel değil.

### Kaynak
- https://docs.turso.tech/features/sqlite-extensions (FTS5 önceden yüklü listesi; sqlite-vec'in plan kısıtı)
- https://docs.turso.tech/features/ai-and-embeddings (yerleşik vektör, fonksiyon adları)
- https://supabase.com/docs/guides/database/full-text-search (tsvector, eklentisiz)
- https://supabase.com/docs/guides/database/extensions/pgvector (pgvector nasıl açılır)
- https://developers.cloudflare.com/d1/sql-api/sql-statements/ (D1'in desteklediği eklentilerin tamamı)
- https://turso.tech/blog/beyond-fts5 (yeni motorda Tantivy, deneysel)

Belge tarihleri: Turso ve Cloudflare belgelerinde sayfa üstünde tarih yayımlanmıyor; hepsi **23 Eylül 2026'da** okundu.

### Başak için anlamı
Bugünkü hafıza motoru SQLite üzerinde FTS5 + vektör ile çalışıyor. **Turso bunun aynısı** — SQLite uyumlu, FTS5 hazır, vektör yerleşik. Yani motorun mantığını yeniden yazmak gerekmez, yalnız bağlantı adresi değişir. Supabase'e geçmek Postgres'e taşınmak demek: sorguların yeniden yazılması gerekir.

---

## Soru 4 — Python'dan nasıl erişilir

### Bulgu

| Servis | Resmî Python kütüphanesi | Sunucusuz ortamda nasıl çalışır | Bağlantı havuzu tavsiyesi |
|---|---|---|---|
| **Turso** | **VAR — `pyturso`** (`pip install pyturso`) | HTTP üzerinden: "`turso_serverless` connects to a remote Turso database over HTTP — no persistent connections, no native extensions, just the standard library." Belge bunu "yerel dosya tutamadığın durumlar (örn. durumsuz sunucusuz ortamlar)" için öneriyor | Kalıcı bağlantı olmadığı için havuza gerek yok. Resmî havuz tavsiyesi → **BULUNAMADI** (çünkü konu dışı) |
| **Supabase** | **VAR — `supabase-py`** | Belgede eşzamanlı/eşzamansız ayrımı ve protokol (HTTP mi doğrudan Postgres mi) açıkça yazılmamış → **BULUNAMADI** | Doğrudan Postgres bağlantısı kuracaksan resmî tavsiye: **"Use Shared pooler, transaction mode"** (paylaşımlı havuz, işlem kipi), 6543 portu. Uyarı: "Transaction mode does not support prepared statements" — hazır ifadeleri kapatmak zorunlu |
| **Neon** | Ayrı Neon kütüphanesi YOK. Neon'un kendi "serverless driver"ı **yalnız JavaScript/TypeScript**: "The Neon serverless driver (`@neondatabase/serverless`) is a JavaScript and TypeScript Postgres driver". Python için standart Postgres sürücüleri: **psycopg (v3) — "Recommended for new projects"**, psycopg2, asyncpg | Doğrudan Postgres bağlantısı (HTTP yok) | Resmî tavsiye: **"Use the pooled connection string (hostname with -pooler suffix) for serverless functions and connection-per-request workloads."** |
| **Upstash Redis** | **VAR — `upstash-redis`** | HTTP: "a connectionless, HTTP-based Redis client for Python", Upstash REST API üzerinden. Belge açıkça "AWS Lambda, **Vercel Serverless**, Google Cloud Functions" gibi ortamlar için tasarlandığını söylüyor. Python 3.8+ | Bağlantısız olduğu için havuz gerekmiyor |
| **Cloudflare D1** | Resmî Python SDK → **BULUNAMADI.** HTTP REST ucu var: `POST /accounts/{account_id}/d1/database/{database_id}/query`, `Authorization: Bearer $CLOUDFLARE_API_TOKEN`. Belgedeki örnekler yalnız curl, TypeScript, Go, Terraform — **Python örneği yok** | HTTP üzerinden, her istek ayrı | Gerekmiyor (HTTP) |
| **Vercel Blob** | Resmî Python SDK → **BULUNAMADI.** Belgelerde yalnız JavaScript paketi (`@vercel/blob`) ve Vercel CLI geçiyor | — | — |

### Kaynak
- https://docs.turso.tech/sdk/python/quickstart
- https://supabase.com/docs/reference/python/introduction + https://supabase.com/docs/guides/database/connecting-to-postgres
- https://neon.com/docs/serverless/serverless-driver + https://neon.com/docs/guides/python + https://neon.com/docs/connect/connection-pooling
- https://upstash.com/docs/redis/sdks/py/overview
- https://developers.cloudflare.com/api/resources/d1/subresources/database/methods/query/
- https://vercel.com/docs/vercel-blob — belge tarihi **26 Ağustos 2026**

Diğerlerinde sayfa üstünde tarih yayımlanmıyor; hepsi 23 Eylül 2026'da okundu.

### Başak için anlamı
Başak Python/FastAPI. Bu yüzden:
- **Turso ve Upstash en kolayı**: resmî Python kütüphanesi var, HTTP ile çalışıyor, bağlantı havuzu derdi yok — sunucusuz ortama tam uygun.
- **Neon ve Supabase'de bağlantı havuzu bir iş yükü**: kalıcı TCP bağlantısı kuruluyor, sunucusuz ortamda her çağrı yeni bağlantı açma riski taşıyor; "pooler" adresini ve işlem kipini doğru kurmak gerekiyor. Vercel'in 1.024 dosya tanıtıcısı sınırı da burada devreye girer.
- **Vercel Blob Python'dan resmî yolla kullanılamıyor** — bu, fotoğraf saklama kararı için önemli bir eksik.

---

## Soru 5 — Büyük dosya (fotoğraf) saklama

### Bulgu

| Servis | Bedava limit | Tek dosya en fazla | Tarayıcıdan doğrudan yükleme |
|---|---|---|---|
| **Vercel Blob** | 1 GB/ay depolama, 10 GB veri transferi, 10.000 basit + 2.000 ileri işlem. Limit aşılırsa **30 gün erişim kapanıyor** | **5 TB**; 100 MB üstü için parçalı yükleme öneriliyor; 512 MB üstü önbelleğe alınmıyor | **VAR.** Sayfanın kendi özeti: "Learn how to upload files larger than 4.5 MB directly from the browser to Vercel Blob". Akış: tarayıcı `upload()` çağırıyor → sunucudaki uç `handleUpload()` ile jeton üretiyor → dosya tarayıcıdan doğrudan Blob'a gidiyor, sunucudan geçmiyor. **Ama bu SDK JavaScript** |
| **Supabase Storage** | 1 GB dosya (bedava plan) | Bedava planda **"the limit can't exceed 50 MB"**; Pro'da 500 GB'a kadar | Belgelerde `createSignedUploadUrl` ile tarayıcıdan yükleme → bu sayfalarda **BULUNAMADI**. Standart yükleme 5 GB'a kadar, 6 MB üstü için TUS (parçalı, kaldığı yerden devam eden yükleme) öneriliyor |
| **Cloudflare R2** | **10 GB-ay** depolama, 1 milyon Class A, 10 milyon Class B, **dışa veri çıkışı bedava** | Bu sayfada belirtilmemiş | **VAR — ön imzalı (presigned) adres.** "A presigned URL includes signature parameters in the URL itself, authorizing anyone with the URL to perform a specific operation (like `GetObject` or `PutObject`)... ideal for... allowing users to upload files directly to R2." **Python/boto3 ile üretilebiliyor**: `s3.generate_presigned_url('put_object', ...)`. Uyarı: tarayıcıdan kullanılacaksa **CORS kuralı** şart, ve ön imzalı adres "taşıyıcı jeton gibi" — adresi bilen herkes o işlemi yapabilir |

Önemli bağ: **Vercel fonksiyonuna gelen istek gövdesi en fazla 4,5 MB** (Soru 6). Yani telefon fotoğrafı bile sunucudan geçemez. Doğrudan tarayıcıdan yükleme bir süs değil, zorunluluk.

### Kaynak
- https://vercel.com/docs/vercel-blob/usage-and-pricing — belge tarihi **8 Eylül 2026**
- https://vercel.com/docs/vercel-blob/client-upload — belge tarihi **15 Eylül 2026**
- https://supabase.com/docs/guides/storage/uploads/file-limits + https://supabase.com/docs/guides/storage/uploads/standard-uploads
- https://developers.cloudflare.com/r2/pricing/ + https://developers.cloudflare.com/r2/api/s3/presigned-urls/

### Başak için anlamı
Fotoğraf için **R2 açık ara önde**: 10 kat fazla bedava alan (10 GB'a karşı 1 GB), veri çıkışı bedava, ve en önemlisi **ön imzalı adresi Python'dan üretebiliyorsun** (boto3 ile). Vercel Blob'un tarayıcıdan yükleme akışı çalışıyor ama resmî yolu JavaScript; Python/FastAPI'den kullanmak için belgelenmemiş yollara sapmak gerekir. Supabase Storage bedava planda dosya başına 50 MB ile sınırlı ve tarayıcıdan yükleme yolunu bu sayfalarda doğrulayamadım.

---

## Soru 6 — Vercel istek gövdesi boyut limiti

### Bulgu
**4,5 MB.** Belgenin tam ifadesi:

> "The maximum payload size for the request body or the response body of a Vercel Function is **4.5 MB**. If a Vercel Function receives a payload in excess of the limit it will return an error **413: `FUNCTION_PAYLOAD_TOO_LARGE`**."

Dikkat: bu sınır **hem gelen istek hem giden cevap** için geçerli.

### Kaynak
https://vercel.com/docs/functions/limitations — belge tarihi **24 Ağustos 2026**

### Başak için anlamı
Büyük dosya asla Başak'ın API'sinden geçmeyecek. İki yönlü sonuç: (a) fotoğraf yüklemesi doğrudan tarayıcıdan depoya gidecek, (b) Başak büyük bir dosyayı cevap olarak da geri veremez — dosyayı indirme adresi olarak vermek gerekir.

---

## Tavsiye

**Ana depo: Turso (bedava plan). Fotoğraf/büyük dosya: Cloudflare R2 (bedava plan).**

### Neden Turso
1. **Motoru değiştirmek gerekmiyor.** Başak'ın hafızası SQLite üzerinde FTS5 + vektör ile çalışıyor. Turso SQLite uyumlu, FTS5 önceden yüklü, vektör araması eklentisiz yerleşik. Supabase'e geçmek Postgres'e taşınmak demek — sorguları yeniden yazmak gerekir.
2. **Sunucusuz ortama uygun.** Resmî Python kütüphanesi (`pyturso`) var ve HTTP üzerinden, kalıcı bağlantı olmadan çalışıyor. Bağlantı havuzu kurma, Vercel'in dosya tanıtıcısı sınırına çarpma derdi yok.
3. **Uyuma riski belgelenmemiş.** Supabase'in bedava projesi 1 hafta kullanılmazsa duruyor; Başak kişisel asistan, bu gerçekçi bir risk. Turso'nun fiyat sayfasında böyle bir madde yok.
4. **Limitler bol.** 5 GB depolama (Başak 5,7 MB), ayda 500 milyon satır okuma, 10 milyon satır yazma.

### Neden R2
10 GB bedava (Vercel Blob'da 1 GB), veri çıkışı bedava, ve ön imzalı yükleme adresini **Python'dan boto3 ile** üretebiliyorsun — Vercel Blob'un resmî yolu JavaScript olduğu için Python tarafında pürüzsüz değil.

### Riskler (dürüst kısım)
1. **Turso'nun motor geçişi.** Turso SQLite'ı Rust ile sıfırdan yazıyor ve yeni motorda tam metin arama FTS5 yerine Tantivy ile, **deneysel** durumda. Bugün Turso Cloud'da FTS5 çalışıyor; ama ileride geçiş istenirse arama kodu değişebilir. Bu bir "yarın bozulur" riski değil, "12-24 ay içinde bir kez dokunmak gerekebilir" riski.
2. **Turso daha önce özellik kısmış.** 21 Ocak 2025 tarihli resmî duyuruda yeni kullanıcılar için kenar kopyaları (edge replicas), çok-veritabanı şemaları ve `ATTACH` kaldırıldı. Aynı duyuru mevcut ücretli müşterilere "işleriniz bugün olduğu gibi çalışmaya devam edecek" güvencesi veriyor. Yani bedava plan için benzer bir kısıntı ihtimali sıfır değil. Başak bu kaldırılan özelliklerin hiçbirini kullanmıyor.
3. **İki servis = iki hesap, iki anahtar.** Turso + R2 ikilisi tek servise göre bir tık daha karmaşık. Ama fotoğraf işi ertelenebilir: önce yalnız Turso'ya geçilir, R2 fotoğraf sırası gelince eklenir.
4. **Turso'nun bağlantı sayısı limiti belgelenmemiş.** HTTP olduğu için pratikte sorun çıkarması beklenmez, ama ölçülmüş bir rakam yok.

### Eğer tek servis isteniyorsa
Supabase (veritabanı + Storage + pgvector + tam metin arama hepsi bir yerde). Bedeli: Postgres'e taşınma işi, 1 hafta hareketsizlikte duraklama, bedava planda dosya başına 50 MB, ve bağlantı havuzu ayarı.

---

## Bulunamayanlar

1. İki ayrı Vercel fonksiyon örneğinin `/tmp` klasörünü paylaşıp paylaşmadığını **açıkça** söyleyen resmî cümle. (Dolaylı kanıt var: yeni örnek açılıyor ve paylaşım yalnız aynı örnek içinde belgeleniyor.)
2. Turso'nun bedava planında veritabanlarının hareketsizlikte uyutulup uyutulmadığı.
3. Turso'nun eşzamanlı bağlantı sayısı limiti.
4. Upstash Redis bedava planında veritabanının kullanılmayınca silinip silindiği/duraklatıldığı ve eşzamanlı bağlantı sayısı.
5. "pgvector bedava planda kullanılabilir" diyen açık Supabase cümlesi. (Belgeler plan kısıtından hiç söz etmiyor — yani kısıt belirtilmemiş, ama olumlu bir teyit de yok.)
6. Supabase `supabase-py` kütüphanesinin eşzamanlı mı eşzamansız mı olduğu ve HTTP (PostgREST) mi doğrudan Postgres bağlantısı mı kullandığı.
7. Supabase Storage'da `createSignedUploadUrl` ile tarayıcıdan doğrudan yükleme akışı (baktığım iki sayfada yok; başka bir sayfada olabilir, doğrulamadım).
8. Cloudflare D1 için resmî Python SDK ve belgelerde Python örneği.
9. Vercel Blob için resmî Python SDK.
10. Cloudflare R2'de tek dosya en büyük boyutu (fiyat ve ön imzalı adres sayfalarında yok).
11. Neon'un bedava planında pgvector ve tam metin aramanın durumu (Neon belgelerinde ayrıca doğrulanmadı).
