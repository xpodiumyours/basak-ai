# Bulut tarayıcı işçisi — kurulum

**Durum:** dizin kurulum içindir; canlı Oracle VM kurulumu henüz
yapılmadı. Buradaki komutlar Oracle'da ilk kurulumda koşulacak; kanıt
olarak `/api/durum` → `isciler.canli >= 1` ve `checkpoint_resume: true`
görülmeden "çalışıyor" denmez.

## Ne yapar

Başak'ın beyni (Vercel) onaylı **tek** tarayıcı eylemini Postgres
kuyruğuna bırakır. İşçi bu işi alır, gerçek Chromium'da uygular ve
sonucu (metin/ekran görüntüsü/doğrulama) deftere yazar. İşçi karar
vermez; ikinci bir ajan döngüsü veya model zinciri yoktur.

## Oracle hedefi

- `VM.Standard.A1.Flex`, Ubuntu 24.04 aarch64
- 2 OCPU / 12 GB RAM / 50 GB (Always Free sınırı içinde)
- Genel IPv4; **80/443 açılmaz**, gelen trafik gerekmez
- Docker Engine + Compose eklentisi kurulu

## 1. Ortam dosyası

```bash
cd deploy/worker
cp .env.example .env
# .env içine beyinle AYNI BASAK_ISCI_ANAHTARI ve Postgres DSN'i yaz
chmod 600 .env
```

Anahtar Vercel'deki `BASAK_ISCI_ANAHTARI` ile birebir aynı olmalıdır;
onay belgesi bu anahtarla imzalanır. DSN yoksa işçi yerel SQLite'a
yazar ve Vercel beyni bu kuyruğu **görmez** — üretimde DSN zorunludur.

## 2. İmajı kur ve başlat

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f --tail=100
```

`healthy` görünene kadar bekle. Sağlık ucu yalnız konteyner içinde
`127.0.0.1:8787/saglik` dinler; dışarıya açılmaz.

## 3. Kanıt

```bash
docker compose exec isci python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8787/saglik').read().decode())"
```

Beklenen: `"ok": true`, `"isci": "basak-worker-1"`, `"kuyruk": {...}`.
Ardından canlı sitede `/durum` sayfası:

- `Bulut tarayıcı işçisi` → **canlı işçi** (yeşil)
- `Yarım kalan işi sürdürme` → yalnız bu heartbeat varken yeşil

## 4. Güncelleme / geri alma

```bash
git pull
docker compose up -d --build
```

Sorun çıkarsa:

```bash
docker compose down
# önceki imaj etiketiyle geri dön (image: basak-isci:<etiket>)
```

Kuyruk Postgres'te olduğu için konteyner silinse de işler ve nonce
kayıtları kaybolmaz.

## Sınırlar

- Chromium `--no-sandbox` yalnız konteyner içinde root çalışılırsa
  açılır; imaj `basak` (uid 10001) kullanıcısıyla çalışır.
- İşçi başına en fazla 3 açık tarayıcı oturumu vardır; oturumlar
  `kosu_id` başına izoledir.
- Onay belgesi en fazla 300 saniye yaşar ve tek kullanımlıdır; süresi
  dolan iş `hata` olur, kör tekrar edilmez.
- Çöken işçinin `calisiyor` işleri heartbeat süresi (varsayılan 90 sn)
  dolunca `supheli` işaretlenir; otomatik yeniden denenmez.
