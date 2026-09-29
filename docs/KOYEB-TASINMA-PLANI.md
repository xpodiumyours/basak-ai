# KOYEB'E TAŞINMA PLANI — ELENDİ (2026-09-29)

> **Bu plan yürürlükten kalktı.** Casper soğuk başlangıcı reddetti; hosting
> araştırması sonucu **Oracle Always Free** seçildi. Yürürlükteki plan:
> **`ORACLE-TASINMA-PLANI.md`**. Bu dosya yalnız tarihî kayıt olarak durur.

Tarih: 2026-09-29 · Durum: **PLAN — Casper onayı bekliyor** (artık geçersiz)
Dayanak: gelir-kurallari.md §"Yayın ve gelir sırası" (1. adım), resmî Koyeb
docs (koyeb.com/docs, koyeb.com/docs/faqs/pricing — 2026-09-29 doğrulandı).

## 0. Neden

Vercel Hobby ücretsiz planının şartları reklam/ticari kullanım kapalı tutuyor;
AdSense kodu Vercel'de yayınlanamaz. Base44 elendi (gelir-kurallari.md —
ücretsiz plan 5 mesaj/gün, kod düzenleme yok). Kalan tek aday: **Koyeb**.

## 1. Koyeb ücretsiz plan (resmî)

- **1 web servisi**, Frankfurt (fra) veya Washington DC — **512MB RAM,
  0.1 vCPU, 2GB SSD**, kart gerekmez ("You will never be charged when using
  the free Instance").
- **100GB/ay outbound** trafik (sonrası $0.04/GB).
- Ücretsiz Koyeb PostgreSQL: 5 saat aktif zaman/1GB — **kullanılmayacak**;
  Neon Postgres aynen kalır (zaten dış servis, DSN env ile taşınır).
- **Uyku:** boştan sonra instance kapanır, ilk istekte uyanır (1-5 sn
  soğuk başlangıç). Free instance tek instance.
- Dağıtım: **GitHub git-driven** (buildpack) — push'a otomatik deploy.

## 2. Uyumluluk denetimi (2026-09-29, kod üzerinden)

| Kalem | Sonuç |
|---|---|
| requirements.txt Linux uyumu | ✓ win32 paketleri koşullu (`sys_platform`), Linux'a inmez; sqlite-vec manylinux wheel var |
| `uvicorn` | ✗ **YOK → eklenecek** (run command onu kullanacak) |
| Uygulama girişi | `app.py`'de `__main__` yok → Koyeb run command: `uvicorn app:app --host 0.0.0.0 --port 8000` |
| Port | Koyeb `PORT` env verir; expose `8000:http` + route `/:8000` (Vercel'deki gibi değil — Koyeb kalıcı süreç) |
| Sağlık kontrolü | ✓ HTTP `/api/durum` (9 sağlayıcı, 200) — health check olarak kullanılır |
| Neon DSN | ✓ `DATABASE_URL` / `POSTGRES_URL` / `NEON_DATABASE_URL` env'lerinden biri Koyeb'e tanımlanır (`app.py:136`) |
| Üretim modu | `VERCEL` env Koyeb'de yok → **`BASAK_URETIM=1` zorunlu** (`app.py` üretim algısı) |
| Oturum anahtarı | `BASAK_OTURUM_ANAHTARI` + `BASAK_WEB_TOKEN` aynen taşınır (Vercel'deki değerler) |
| Dosya sistemi | Geçici (`temp/basak`) — container yeniden başlayınca silinir. Kalıcı veri Neon'da; audit log/geçici dosyalar kaybolur, **kabul edildi** (Vercel'deki davranışla aynı) |
| sitemap/robots | ✓ **Dinamik** (`request.base_url` — `app.py:988,1042`) → yeni adreste kendiliğinden doğru |
| Kron/arka plan thread | Yok (Vercel'de de yok) — uyku davranışı etkilemez |

Eksik/yapılacak tek kod işi: **`requirements.txt`'e `uvicorn` eklemek.**

## 3. Aşamalar

**Aşama 0 — Yerel hazırlık (ben, kod):**
- `requirements.txt` → `uvicorn` ekle.
- Test paketi yeşil (`python -m pytest tests -q`).
- Lokal `uvicorn app:app` ile duman testi.

**Aşama 1 — Hesaplar (Casper'ın eliyle):**
- app.koyeb.com → ücretsiz kayıt.
- Koyeb kontrol paneli → GitHub yetkilendirmesi (Koyeb GitHub App'i
  `xpodiumyours/basak-ai` deposuna erişsin).

**Aşama 2 — Servis kurulumu (ben, Koyeb CLI):**
```
koyeb app init basak-web \
  --git github.com/xpodiumyours/basak-ai \
  --git-branch feat/freetools-koprosu \
  --git-builder buildpack \
  --git-buildpack-run-command "uvicorn app:app --host 0.0.0.0 --port 8000" \
  --instance-type free --regions fra \
  --ports 8000:http --routes /:8000 \
  --env BASAK_URETIM=1 \
  --env BASAK_WEB_TOKEN=<mevcut değer> \
  --env BASAK_OTURUM_ANAHTARI=<mevcut değer> \
  --env DATABASE_URL=<Neon DSN>
```
Health check: HTTP `/api/durum`. (Vercel'deki secret değerleri `vercel env`
listesinden okunur; sır commit'e girmez, yalnız Koyeb'e yazılır.)

**Aşama 3 — Canlı doğrulama (ben):**
- Aynı 10 madde yayın testi (özet ama ucu açık): kimlik, araç+Kaynaklar,
  sorgu kodlama, freetools bağlantısı, ret, tarih, hava, hafıza izolasyonu,
  kota, derin bağlantı.
- **Soğuk başlangıç ölçümü:** uyuyan servise ilk istek süresi.
- **Yük ölçümü:** birkaç eşzamanlı istek → 512MB/OOM kontrolü.
- `/api/durum` → `hafiza_modu` Neon'a bağlı mı (postgres izolasyonu).

**Aşama 4 — Search Console (Casper + ben):**
- Yeni URL (`*.koyeb.app`) için **URL ön eki mülkü** + HTML dosyası
  doğrulama (aynı akış, dosyayı ben koyarım).
- `sitemap.xml` yeni mülke gönderilir.
- Eski `basak-vercel.vercel.app` mülkü: Vercel kapatılana kadar durur;
  domain alınınca **Domain mülküne** geçilir (zaten kararlı sıra).

**Aşama 5 — Vercel'den ayrılık (Casper kapısı):**
- Koyeb 1-2 hafta canlı kalır, Vercel production da açık kalır → geri alma
  her an `vercel --prod` (DNS yok, alias anında döner).
- Sonra Vercel proje askıya alınır (silinmez).

## 4. Geri alma planı

Koyeb'de sorun → Vercel hâlâ canlı: `npx vercel --prod` yeterli. ToS/ücret
sürprizi yok (free instance kart istemez, 7/14/21 gün ödeme gecikmesi
maddesi yalnız kartlı planda).

## 5. Riskler ve kabul kapıları (Casper onayı)

1. **Soğuk başlangıç 1-5 sn** — ilk mesajda bekleme. Kabul mü?
2. **GitHub push → otomatik deploy (CD):** `feat/freetools-koprosu`'na her
   push Koyeb'i yeniden deploy eder. Kabul mü? (Alternatif: `--git-no-deploy-on-push`
   ile elle deploy.)
3. **Koyeb uyku → Googlebot:** uyanma genelde health check'ten sonra
   sorun çıkarmaz ama indeks hızını düşürebilir. Domain mülkünde tekrar
   değerlendirilir.
4. **512MB tek instance** — Aşama 3 yük ölçümünde OOM çıkarsa plan
   durur (ücretsiz planda büyütme yok; Render free vb. yedeklere dönülür).

## 6. Sıra dışı değil, hatırlatma

Reklam/AdSense kodu bu taşınmadan **sonra** ve gelir-kurallari.md
sırasına göre: (1) Koyeb ✓ → (2) AdSense kodu → (3) domain → (4) başvuru.
Ücretsiz AI sağlayıcı ToS ticari-kontrolü de taşınma öncesi kapı
(gelir-kurallari.md §3).
