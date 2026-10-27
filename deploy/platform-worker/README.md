# Başak kalıcı ajan işçisi — kurulum adayı

Bu dosya kurulum tarifidir; herhangi bir ortamda çalışan işçi bulunduğunun kanıtı değildir.
Mevcut `deploy/worker/` eski tarayıcı işçisidir ve **değiştirilmemiştir**.

## Görev

`python -m worker.platform` bağımsız çalışan bir Python süreçtir. Aynı
Preview için yalnız `BASAK_PREVIEW_DATABASE_URL` üzerinden Başak web uygulamasındaki kayıtlı görevleri talep eder,
model havuzunu kullanır ve sonuçlarını görev defterine kaydeder.
Preview DSN olmadan **başlamaz**; yanlışlıkla ayrı SQLite kuyruğu oluşturmaz.

## Yalnızca izole test ortamında kurulum

1. Temiz bir geliştirme dalı checkout'unda `cd deploy/platform-worker` yap.
2. `cp environment.example.txt .env` ve `.env` içine **test/Preview** Postgres
   bağlantısını `BASAK_PREVIEW_DATABASE_URL` olarak gir. Compose `VERCEL_ENV=preview`
   kullanır; genel `DATABASE_URL` veya eski worker DSN ayarına düşmez.
   Web Preview da aynı ayrılmış DSN kullanmalı. Veritabanı rolünün production
   kaynaklarına erişemediği gerçek bağlantıyla ayrıca doğrulanmalıdır.
3. Hesap bağlantıları sınanacaksa web ile **aynı** `BASAK_CONNECTION_KEY` değerini
   sunucu ortam sırrı olarak ayarla. Gerçek şifreleri GitHub'a gönderme.
4. `docker compose build`; ardından `docker compose up -d`.
5. `docker compose logs --tail=100 agent` ile bağlantı hatası olmadan görevlere
   eriştiğini doğrula. Aynı test görevini web Preview üzerinden oluştur ve
   tamamlanma kaydını kanıt olarak sakla.
6. Web için `BASAK_DURABLE_CHAT_ENABLED` varsayılan olarak `false` kalır.
   Ayrılmış worker ve kimlik ayarları hazır olduktan sonra yalnız hedef Preview
   ortamında `true` yap; gerçek kabul tamamlanmadan production’da açma.
   Yeni sohbet, işçi hazır değilse mevcut Python sohbet yolunda çalışır.
   Önceden kaydedilmiş istek aynı kimlikle gözlenir; işçi yokken başka
   yürütme yoluna tekrar gönderilmez. Bilinmeyen veritabanı hatası da tekrar
   yürütme gerekçesi değildir.

Bu dosyalar sunucu sağlamaz ve GitHub'a push etmek **sürekli çalışan bir işçi başlatmaz**.
Gerçek sunucu kurulumu, gizli değişkenler, maliyet kontrolü ve canlı görev kabulü ayrı aşamadır.

## Güvenlik ve sınırlamalar

- Başak'ın varsayılan model havuzu/FreeLLMAPI/sohbet kodu aynen kullanılır.
- İmaj yalnız kaynak kodu, gereken paketleri ve Chromium'u taşır; Dockerfile'a özgü
  allowlist, `.env`, kullanıcı kayıtları ve gizli verileri build kapsamından çıkarır.
- Konteyner yetkisiz kullanıcı olarak çalışır; dışarıya HTTP portu açılmaz.
- Host Docker soketi bağlanmaz. gVisor olmadan `kod_calistir` **kapalı kalır**;
  güvenli kod yürütme aşaması ayrı kurulum ve doğrulama gerektirir.
- Tarayıcı oturumları süreç belleğindedir. Yeniden başlatmada kayıp oturumun
  otomatik iyileştirilmesi gerçek çok-adımlı kabul testinde ayrıca ölçülmelidir.
- İşçi kapalıyken kayıtlı görevler Postgres'te korunur fakat ilerlemez.
  CI'nın yeşil olması üretimde çalışan işçi kanıtı sayılmaz.

## Paralel alt ajan ölçeği (yalnız test ortamında)

Aynı test PostgreSQL kuyruğunu kullanan üç kopya başlatılabilir:
`docker compose up -d --scale agent=3`.
`RuntimeStore` aynı ana görevin aynı anda en fazla üç alt ajanını claim eder;
dördüncü çocuk görevi kuyrukta kalır. Bu sınır tek sunucudaki görünüm değil,
veritabanı transaction düzeyinde uygulanır. CI, sahte ve kotasız görev işleyicileriyle
üç ayrı `Worker.tick()` çağrısının eşzamanlılığını test eder.
Bu kontrol uzak sunucu, OAuth veya gerçek sağlayıcı testi yerine geçmez.

## Canlı işçi sağlığı

Yeni `basak_platform_worker_presence` kaydı, işçi **boşta beklese
de** PostgreSQL'e 10 saniyede bir kalp atışı yazar. Görev kirası kalp
atışı ayrı tutulur. `GET /api/kosu/isciler` oturum açmış kullanıcıya,
son 30 saniye içinde kalp atışı olan işçi sayısını ve çevrimiçi durumunu
gösterir. İşçi kapanınca çevrimdışı işaretlenir; beklenmedik çökmede
kalp atışı 30 saniyede eskir. Arayüz işçi yoksa çalışıyormuş gibi
davranmaz.

GitHub CI testi, farklı PostgreSQL bağlantılarından işçi kaydının
görüldüğünü doğrular. Bu, **uzak sunucuya gerçek işçi kurulduğunun
kanıtı değildir**: Preview görev kabulünde ayrı canlı kanıt aranır.
