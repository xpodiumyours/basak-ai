# Başak kalıcı ajan işçisi — kurulum adayı

**Durum:** Sadece geliştirme dalında kurulum ve CI için hazırlanmıştır. **Canlı kurulum yapılmadı.**
Mevcut `deploy/worker/` eski tarayıcı işçisidir ve **değiştirilmemiştir**.

## Görev

`python -m worker.platform` bağımsız çalışan bir Python süreçtir. Aynı
`DATABASE_URL` üzerinden Başak web uygulamasındaki kayıtlı görevleri talep eder,
model havuzunu kullanır ve sonuçlarını görev defterine kaydeder.
`DATABASE_URL` olmadan **başlamaz**; yanlışlıkla ayrı SQLite kuyruğu oluşturmaz.

## Yalnızca izole test ortamında kurulum

1. Temiz bir geliştirme dalı checkout'unda `cd deploy/platform-worker` yap.
2. `cp environment.example.txt .env` ve `.env` içine **test/Preview** Postgres
   bağlantısını gir. Canlı veritabanıyla karıştırma.
3. Hesap bağlantıları sınanacaksa web ile **aynı** `BASAK_CONNECTION_KEY` değerini
   sunucu ortam sırrı olarak ayarla. Gerçek şifreleri GitHub'a gönderme.
4. `docker compose build`; ardından `docker compose up -d`.
5. `docker compose logs --tail=100 agent` ile bağlantı hatası olmadan görevlere
   eriştiğini doğrula. Aynı test görevini web Preview üzerinden oluştur ve
   tamamlanma kaydını kanıt olarak sakla.

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
