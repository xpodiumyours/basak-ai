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
6. `BASAK_DURABLE_CHAT_ENABLED` artık **varsayılan olarak açıktır**: ortam
   değişkeni tanımlı değilse karar kalıcı deponun gerçekten hazır olmasından
   gelir (`chat.veritabani.hazir()`). Açıkça `false` yazılırsa eski sohbet
   yolu kullanılır. Yeni sohbet, işçi yoksa `allow_legacy` ile mevcut Python
   sohbet yoluna döner; iş kaybolmaz. Önceden kaydedilmiş istek aynı kimlikle
   gözlenir; işçi yokken başka bir yürütme yoluna tekrar gönderilmez.
   Bilinmeyen veritabanı hatası da tekrar yürütme gerekçesi değildir.
   Kalıcı yolu **kapatmak** için yalnız hedef ortamda `BASAK_DURABLE_CHAT_ENABLED=false`
   tanımla; üretimde kapatmadan önce işçi ve kimlik ayarlarının hazır olduğunu doğrula.

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

`GET /api/durum` iki işçi kaynağını ayrı raporlar: `isciler` tarayıcı
eylem kuyruğunun (`basak_isci_kalp`) kalp atışı, `platform_isciler` ise
kalıcı görev işçisinin (`basak_platform_worker_presence`) canlı sayısı.
`checkpoint_resume` bu iki kaynaktan **biri** canlıysa ve koşu defteri
açıksa `true` olur; önceki sürüm yalnız eylem kuyruğuna baktığı için
orduyu çalıştıran işçi görünmüyordu.

Çocuk görevleri hâlâ çalışırken biten bir üst görev `verifying` durumunda
bekler. Çocuklar kapandığında `RuntimeStore._recover` üst görevi yeniden
değerlendirir ve `completed`/`partial` durumuna geçirir; böylece koşu
kalıcı olarak yarım görünmez.

GitHub CI testi, farklı PostgreSQL bağlantılarından işçi kaydının
görüldüğünü doğrular. Bu, **uzak sunucuya gerçek işçi kurulduğunun
kanıtı değildir**: Preview görev kabulünde ayrı canlı kanıt aranır.

## Production worker candidate (not yet deployed)

Do **not** reuse the Preview Compose command for Production. The separate
`compose.production.yaml` uses the `basak-agent-production` Compose project,
an independent state volume, `VERCEL_ENV=production`, and a required explicit
`BASAK_PRODUCTION_DATABASE_URL`. No public worker port or Docker socket is
exposed. It does not deploy itself or enable persistent web chat.

Before touching a server:

1. Verify the **actual existing Oracle** instance CPU, memory, architecture
   and OS, plus authorized SSH/console access. The Compose default requests
   2 CPUs and 3 GB RAM; do not assume an Always Free instance can satisfy it.
2. Verify the existing Production Vercel database target and Neon branch
   against the Production worker target (including endpoint, database and
   least-privilege role). Make sure Preview and Production are distinct.
3. Run full CI, OAuth/login, a real Chromium/subagent task, file artifact,
   refresh and restart/resume acceptance **on isolated Preview first**.
4. After those succeed, create the real worker host's `.env.production` from
   `environment.production.example.txt`, using an approved secrets channel.
   Never put credentials in Git, chat, shell history or terminal screenshots.
5. The Production candidate may be inspected without launching it:
   `docker compose --env-file .env.production -f compose.production.yaml config --quiet`.
   For sensitive settings, do not print the expanded config.
6. Run the read-only preflight *inside the configured worker container* only
   when infrastructure approval is complete:
   `docker compose --env-file .env.production -f compose.production.yaml run --rm --entrypoint python agent -m tools.platform_release_preflight --environment production --role worker`.
   This runs SELECT queries and requires a recent worker heartbeat; a newly
   created stopped worker naturally fails that check. **It is a verification,
   not an install or startup command.**
7. Only after explicit rollout authorization, start the worker, repeat the
   read-only preflight and authenticated end-to-end acceptance. Enable
   `BASAK_DURABLE_CHAT_ENABLED=true` in Vercel Production **last**. Rebuild
   Production with the intended environment, run post-release checks and
   retain the previous working deployment for rollback.

The preflight's exit code zero is **not** proof of the three required real
user journeys. The script checks configuration, table existence and a real
worker heartbeat without logging DSNs or secrets. Run it with
`--environment preview --role web` in a securely configured Preview web
environment when the preview worker/login/feature flag are ready. It fails
closed until those conditions are met.

Production must remain unmodified until all gates pass; a Vercel READY
deployment by itself is never a release-acceptance result.

## Oracle 1 GB: systemd ile hafif işçi (varsayılan yol)

Oracle Always Free A1 (1 OCPU / 1 GB) için Docker ve Chromium gerekmez.
`deploy/oracle/setup.sh` iki systemd servisi kurar:

- `basak.service` — web (uvicorn, 700 MB tavan)
- `basak-isci.service` — `python -m worker.platform`, 400 MB tavan

İşçi yuvası RAM'e göre seçilir (1 GB → 1, 2 GB → 2, 4 GB → 3). İşçi
`DATABASE_URL` yoksa başlamaz; bu yüzden `/etc/basak/basak.env` içindeki
DSN **Vercel Production ile aynı Neon dalını** göstermelidir. Preview DSN'i
üretim işçisine yazılmaz.

Kabul kanıtı `systemctl is-active` değil, veritabanı kalp atışıdır:
`/api/durum` → `platform_isciler.canli >= 1` ve `checkpoint_resume: true`.
Ardından web'den gerçek bir alt ajan görevi açılır, tarayıcı kapatılır ve
görevin işçi tarafından tamamlandığı görülür.

Bu kurulumda Playwright/Chromium yoktur; `bulut_tarayici` kapalı kalır.
Tarayıcılı işler `compose.production.yaml` ile ayrı ve daha büyük bir
işçi sunucusunda çalıştırılır.
