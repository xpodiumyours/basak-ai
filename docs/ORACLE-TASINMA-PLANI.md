# ORACLE ALWAYS FREE'E TAŞINMA PLANI

Tarih: 2026-09-29 · Durum: **Aşama 0B tamam — Casper'ın Oracle kaydı bekleniyor**
Dayanak: `arastirma/gelir-kurallari.md` (yayın sırası 1. adım) + hosting
araştırması; bu plan `KOYEB-TASINMA-PLANI.md`'nin yerini alır (Koyeb, soğuk
başlangıç reddi üzerine elendi).

## 0. Neden Oracle

Vercel Hobby reklama kapalı → AdSense öncesi taşınma zorunlu. Ücretsiz
platform araştırması (2026-09-29, resmî kaynaklar):

| Platform | Hep açık? | Kart? | Sonuç |
|---|---|---|---|
| **Oracle Always Free** | **Evet — hiç uyumaz** | Kart (ücret çekilmez, 3-5 gün hold) | **SEÇİLDİ (Casper)** |
| Koyeb free | Hayır (1-5 sn soğuk başlangıç) | Yok | Elendi — soğuk başlangıç reddedildi |
| HF Spaces CPU | 48 saatte duraklar; yeni compute Space ücretli plana bağlı | Ücretli plan | Elendi |
| PythonAnywhere | Evet | Yok | Elendi — outbound beyaz liste (API çağrıları ölür) + 100 CPU-sn/gün |
| Render free | Hayır (15 dk uyur) | Yok | Elendi |
| Base44 | İlgisiz (hosting değil) | — | Elendi (gelir-kurallari.md) |

## 1. Oracle Always Free (resmî, 2026-09-29 doğrulandı)

- **VM.Standard.A1.Flex** (Arm/Ampere): free tenancy için toplam **2 OCPU +
  12 GB** (aylık 1.500 OCPU-saat + 9.000 GB-saat) — biz 1 OCPU + 1 GB
  kullanacağız (kota geniş başlıyor).
- Alternatif **E2.1.Micro** (x86, 1/8 OCPU, 1 GB, 2 adet) — seçilmedi,
  aşağıda gerekçesi.
- Kart: kimlik doğrulama için zorunlu; **ücret alınmaz**, tutar hold'u
  3-5 günde kalkar (resmî FAQ). PIN'li debit / prepaid / sanal kart kabul
  edilmez; kredi kartı veya kredi gibi çalışan debit gerekir.
- **Home region seçim sonrası değiştirilemez** → en yakın bölge seçilmeli
  (Türkiye için: **eu-frankfurt-1** önerilir; kapasite yoksa eu-amsterdam-1).
- Free trial $300 / 30 gün → süre bitince Always Free'ye düşülür (ücretsiz
  kalır); **PAYG'e yükseltilmemeli**.
- "Out of host capacity" hatası A1'de yaygındır → farklı AD/değerle tekrar
  denenir; instance silinip yeniden açılabilir.
- Hesap 30 gün hiç kullanılmazsa "terk edilmiş" sayılabilir — instance
  sürekli açık olduğu için etkilenmeyiz.

## 2. Boşa alma (idle reclamation) savunması — şekil seçiminin gerekçesi

Resmî kural: 7 günlük pencerede **hepsi** birlikte sağlanırsa Oracle idle
der: CPU 95. yüzdelik < %20 **VE** ağ < %20 **VE** bellek < %20 (bellek
kriteri yalnız A1'e uygulanır).

- **1 OCPU + 1 GB A1** seçilmiştir: uygulama hafızası (~300-500 MB) 1 GB'ın
  %20'sinin (205 MB) sürekli üstünde → **üç koşul aynı anda asla dolmaz,
  idle kararı verilmez.** Büyük RAM vermek bu savunmayı zayıflatır.
- E2.1.Micro'da bellek kriteri yoktu → yalnız CPU+ağ yeterliydi, yani
  düşük trafikli site gerçekten idle sayılabilirdi. A1+1GB bu yüzden daha
  güvenli.
- 700 MB servis tavanı (MemoryMax) + 2 GB swap → OOM emniyeti.
- Kanıt standardı: Aşama 3'te `free -h` + `journalctl` ile bellek kullanımı
  ölçülür; %20'nin altında kalırsa plan durur ve şekil gözden geçirilir.

## 3. Teknik uyumluluk (kanıtlanmış)

| Kalem | Sonuç |
|---|---|
| ARM (aarch64) bağımlılıklar | ✓ **48 wheel'in tamamı** (transitif dahil, Linux seti) kaynaksız indi — numpy 2.5.3, sqlite-vec, psycopg-binary, lxml, pydantic-core hepsi aarch64 wheel taşıyor |
| requirements.txt Linux uyumu | ✓ win32 paketleri koşullu (`sys_platform`) — Linux'a inmez |
| `uvicorn==0.51.0` | ✓ Aşama 0'da eklendi (build/test/smoke yeşil) |
| Uygulama girişi | `app.py`'de `__main__` yok → `uvicorn app:app --host 127.0.0.1 --port 8000` |
| Statik dosyalar | ✓ `app.mount("/", _Statik, html=True)` — uvicorn tek başına her şeyi servis eder (vercel.json'a bağımlı değil) |
| Sağlık kontrolü | ✓ `/api/durum` |
| Neon DSN | ✓ `DATABASE_URL` (`app.py:136` — önce o okunur) |
| Üretim modu | ✓ `BASAK_URETIM=1` (`kullanici.py:35`: `VERCEL` veya `BASAK_URETIM`) |
| Kimlik | ✓ `BASAK_WEB_TOKEN` + `BASAK_OTURUM_ANAHTARI` (`app.py:67,115,251`) |
| Kota | ✓ `BASAK_ANONIM_KOTA_TAVAN` (`kota.py:30`, yoksa 50) |
| State dizini | ✓ `BASAK_STATE_DIR=/opt/basak/data` (`app.py:33`; yoksa /tmp — reboot'ta silinir) |
| sitemap/robots | ✓ Dinamik `request.base_url` → yeni adreste kendiliğinden doğru |
| Python | ✓ Ubuntu 24.04 = Python 3.12 (pin'ler 3.12.10'da ölçüldü) |
| Depo erişimi | ✓ Repo **PUBLIC** → sunucu `git clone` ile kodu çeker (token gerekmez) |
| Dış ağ (AI API'leri) | ✓ Oracle VM'de serbest (PythonAnywhere'ın aksine beyaz liste yok) |

## 4. Mimari

```
internet → Caddy :80 (ters vekil, domain gelince otomatik TLS)
         → uvicorn 127.0.0.1:8000 (systemd: basak.service, Restart=always)
         → /opt/basak (GitHub clone: feat/freetools-koprosu)
         → /etc/basak/basak.env (mod 600, sır dosyası — git'e girmez)
         → Neon (dış servis, aynen kalır)
```

Dağıtım dosyaları: `deploy/oracle/{setup.sh, basak.service, Caddyfile, basak.env.ornek}`.
Güncelleme = sunucuda `sudo bash /opt/basak/deploy/oracle/setup.sh`
(fetch + reset --hard + pip + restart) — CD yok, elle tetiklenir.

## 5. Aşamalar

**Aşama 0 — Yerel hazırlık ✓ (2026-09-29):**
uvicorn eklendi; 851 test yeşil; lokal `uvicorn` duman testi geçti
(`/api/durum` 200, sitemap 200).

**Aşama 0B — Paket + doğrulama ✓ (2026-09-29):**
ARM wheel doğrulaması (48/48); şekil kararı (A1 1/1); SSH anahtarı üretildi
(`%TEMP%\opencode\basak-oracle_ed25519.pub`); `deploy/oracle/` yazıldı.

**Aşama 1 — Hesap + instance (Casper'ın eliyle, ben adım adım yönlendiririm):**
1. `https://signup.cloud.oracle.com` → free account (e-posta, telefon, kart).
   **Home region: Germany Central (eu-frankfurt-1)** — sonradan değiştirilemez.
2. Compute → Create Instance:
   - Image: **Ubuntu 24.04 (Always Free Eligible)** — Arm/aarch64.
   - Shape: **VM.Standard.A1.Flex — 1 OCPU, 1 GB bellek**.
   - VCN: yeni (sihirbaz) → güvenlik listesinde **80/443** gelen trafiğe
     açık olmalı (22 zaten).
   - SSH: üretilen `basak-oracle-20260929` **public anahtarı** yapıştırılır.
   - Boot volume: varsayılan 50 GB (200 GB free hakkından).
3. Instance public IP bana iletilir.

**Aşama 2 — Kurulum (ben, SSH):**
`deploy/oracle/` + `setup.sh` çalışır; `/etc/basak/basak.env` doldurulur
(`vercel env pull` ile mevcut production değerleri) → `/api/durum` 200 +
Caddy `http://IP/` 200. **Öncesinde commit izni istenecek** (uvicorn +
`deploy/` + docs — bekleyenler).

**Aşama 3 — Canlı doğrulama (ben):**
Aynı 10 madde yayın testi (özet/ucu açık); **soğuk başlangıç ölçümü YOK**
(hep açık); yük + bellek ölçümü (`free -h` → bellek %20 üstünde kalmalı,
yoksa şekil planı durur); `/api/durum` → hafıza modu Neon bağlı.

**Aşama 4 — Search Console (Casper + ben):**
Yeni IP/URL için URL ön eki mülkü + HTML dosyası doğrulama (dosyayı ben
koyarım) + `sitemap.xml`. Eski `basak-vercel.vercel.app` mülkü domain
alınana kadar durur.

**Aşama 5 — Vercel'den ayrılık (Casper kapısı):**
Oracle 1-2 hafta canlı, Vercel production açık → geri alma anlık
(`npx vercel --prod`). Sonra Vercel projesi askıya alınır (silinmez).

**Aşama 6 — Gelir sırası (gelir-kurallari.md):**
AdSense kodu eklenir → domain → başvuru. Ücretsiz AI sağlayıcı ToS
ticari-kontrol kapısı taşınma/AdSense öncesi ayrıca koşulur.

## 6. Geri alma

Oracle'da sorun → Vercel hâlâ canlı: `npx vercel --prod` yeterli. Sırlar
her iki tarafta ayrı yazılır; Oracle silinse bile hesap/kota etkilenmez.

## 7. Risk kapıları (Casper onayı)

1. **A1 kapasite yokluğu** → AD/değer değişimi; ısrar edilmezse E2.1.Micro
   (1 GB, bellek kriteri yok) yedeğe alınır — o zaman idle savunması için
   ayrı önlem gerekir (Aşama 3 ölçümünde belli olur).
2. **1 GB RAM / OOM** → 700 MB tavan + 2 GB swap; Aşama 3'te ölçülür.
3. **Kart hold'u** (3-5 gün, ücret yok) — Casper bilgilendirildi, kabul edildi.
4. **Güncelleme elle** (CD yok) — bilinçli tercih; ilk kurulumdan sonra
   `setup.sh` yeniden çalıştırılır.
5. **Commit izni**: bekleyen işler (`requirements.txt` uvicorn, `deploy/`,
   docs) Aşama 2 öncesi açık izinle commit edilir.
