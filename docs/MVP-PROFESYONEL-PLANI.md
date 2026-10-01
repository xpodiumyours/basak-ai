# MVP → PROFESYONEL GEÇİŞ PLANI

**Tarih:** 2026-10-01 · **Karar:** Casper · **Ölçüm tarihi:** 2026-10-01

**Bu belgenin rolü:** Şemsiye plan. Harita zinciri kendi planında
(`docs/HARITA-ZINCIRI-PLANI.md`), yayın günü kendi belgesinde
(`docs/FAZ5-YAYIN-PLANI.md`) yürür; bu belge **ikisinin de üstünde**
"neden profesyonelleşiyoruz, hangi sırayla, hangi kapıyla" sorusunu
taşır. Diğer belgelerin yerine geçmez; onlara atıf yapar.

Kural (AGENTS.md §0): Bu plandan **hiçbir kelime/regex karar kuralı,
hiçbir model daraltma katmanı, hiçbir tavan veya onay kuyruğu**
çıkmaz. Buradaki işin hepsi ölçüm, kayıt, teslim edilebilirlik ve
teslim edilebilir anlaşma ilgisi.

---

## 0. Ölçülen taban (2026-10-01)

| Ölçüm | Değer |
|---|---|
| Üretim Python satırı | **36.241** |
| Test satırı | **19.080** (oran 0,53) |
| Test dosyası | 98 |
| Geniş koşu | **1103 geçti / 19 atlandı / 1F+3E** |
| Araç / yetenek alanı | 57 / 15 |
| HTTP ucu (`app.py`) | 17 |
| `except …:` → sessiz `pass` | **59 → 0** (AST ölçümü; 2026-10-01'de kapatıldı) |
| Bağımlılık | 19 paket, **tamamı `==` sabitli** |
| Kapsam ölçümü | **pytest-cov YOK** — hiç ölçülmüyor |
| Tekrarlanabilir kurulum | Dockerfile/Procfile **yok** |
| Production davranışı | **`main`'e merge = otomatik production deploy** (ölçüldü: merge 09:33:19Z → deploy 09:33:49Z) |
| CI sağlayıcı kabulü | `test.yml:96` → **ölü dal** (`preview/fatura-goz-cerrahi-20260927`); **hiç koşmuyor** |
| Canlı kabul paketi | `tests/live/` = 19 test, `--live` kapısı arkasında, CI klasörü tümüyle yok sayıyor |
| Kural belgesi | `CANLI-KAPISI.md` **3 dosyada anılıyor, dosya yok** |

**1F+3E açıklaması:** `tests/test_path_guvenligi.py` — Linux'ta normal
taban (`cmd` yok, `normcase` yok). CI `windows-latest` ile koşar;
yeni bir kırık değildir.

---

## 1. "19 neden atlıyoruz" — cevap

**Kusur değil, tasarım.** Kök `conftest.py` `--live` bayrağı tanımlar;
bayrak verilmezse `tests/live/` altındaki **her** test
`canlı hat — --live gerekli` gerekçesiyle atlanır. CI da aynı klasörü
`--ignore=tests/live` ile tamamen dışarıda bırakır.

| Dosya | Atlanan |
|---|---|
| `test_freetools_canli.py` | 5 |
| `test_memory_lifecycle.py` | 4 |
| `test_boot.py` | 3 |
| `test_agent_canli.py` | 2 |
| `test_goz_imtihani.py`, `test_katalog_canli.py`, `test_postgres_hafiza.py`, `test_seviye1_native.py`, `test_seviye2_pilot.py` | 1'er |
| **Toplam** | **19** |

**Amaçları:** gerçek modeller, gerçek ağ, gerçek Postgres. Her koşuda
sağlayıcı kotası harcar; bu yüzden kapının arkasında.

**Profesyonel açıdan asıl sorun sayı değil, şu:** bu 19 test **hiçbir
zaman kayıtlı olarak koşmadı**. Sonuçları `data/canli-rapor/` altına
yazılır ama kimse onu pipeline'ın parçası olmadı. → **P0'ın konusu.**

---

## 2. "MVP" ve "profesyonel" — ölçülebilir ayrım

| | MVP (bugün) | Profesyonel (hedef) |
|---|---|---|
| Çalıştığı kanıt | Kod yazıldı, testler yeşil | **Bir gerçek kullanıcı akışı uçtan uca kayıtlı** |
| Yayın | merge → production otomatik | **kapı merge'in önünde**, geri alınabilir |
| Kapsam | Testler yeşil/yeşil değil | **Sayısal taban + taban kayması alarmı** |
| Sağlayıcı kabulü | Ölü CI koşulu | **Her ana dalda koşar** |
| Canlı kabul | Elle, kayıtsız | **Kayıtlı, raporlu, düzenli** |
| Hata | 59 sessiz `pass` | **Her sessiz yutma ya da gerekçeli ya da kaldırılmış — ÖLÇÜLDÜ: 0** |
| Veri | Postgres var | **Yedekleme + geri yükleme provası yapılmış** |
| Yasal | Taslak | **Avukat onaylı** |

**Bugünkü dürüst konum:** Kod tarafı MVP'yi geçti. **Kanıt tarafı
geçmedi** — hiçbir zaman gerçek bir modelle, gerçek bir kullanıcı
sorusuyla uçtan uca koşmuş bir sohbet kaydımız yok.

---

## 3. Fazlar

### P0 — KANIT (MVP'yi kapatır; profesyonelliğin ön koşulu)

- [ ] **P0.1** Sağlayıcı kabulünü CI'da yeniden aç: `test.yml:96`'daki ölü
  dal koşulu yerine etiket veya `workflow_dispatch`. ⚠️ **Kapsam notu:**
  gizli depoda Actions dakikası sınırlı; hangi tetikleyici seçilecek
  **Casper kararıdır**.
- [ ] **P0.2** `tests/live --live` paketini anahtarlı bir ortamda (Vercel
  Production veya yerel) **bir kez kayıtlı koş**; `data/canli-rapor/`
  çıktısını plana ekle. Sonuç ne olursa olsun **yazılır** — başarısız
  test de kayıttır.
- [ ] **P0.3** `docs/BIRLIKTE-TEST-SENARYOLARI.md:88`'deki **10 maddelik
  konuşma listesi** koşulsun. 8'i otomatize, 2'si gözle.
- [ ] **P0.4** `CANLI-KAPISI.md` **yaz** (3 dosya ona atıf yapıyor, dosya
  yok). İçerik: `--live` kuralı, neyin canlı sayıldığı, neden kapı var.
- [ ] **P0.5** Oturum anahtarı maddesini kapat: `BASAK_OTURUM_ANAHTARI`
  mı `BASAK_WEB_TOKEN` mı üretimde imzalıyor — **yazılı olarak belirle**
  (ölçüm: imzalı çerez üretildi, yani biri tanımlı; hangisi belirsiz).
- [ ] **P0.6** Ekran görüntülerine **göz at**: `_z2_kanit/z2_masaustu.png`,
  `z2_mobil.png`. Bugün DOM ölçümü var, gözle inceleme yok.
- [ ] **P0.7** `docs/FAZ5-YAYIN-PLANI.md`'ye **"merge = production deploy"**
  kuralını yaz. Bu belge "ayrı `vercel --prod` adımı" diyordu; ölçüm
  gösterdi ki adım yok, merge'in **23 saniye** sonrası deploy oluyor.
  Kapı yerine `vercel --prod` değil, **merge öncesi kontrol** konur.

**Faz kapısı:** P0.1–P0.6 tamam; P0.7 yazılı. Kanıt: koşu raporu +
10 maddenin sonucu + iki ekran görüntüsü.

---

### P1 — ÖLÇÜLEBİLİRLİK

- [ ] **P1.1** `pytest-cov` **önce var mı doğrulanır** (AGENTS.md §5:
  var olmayan paket kurulmaz), sonra kurulur. Kapsam tabanı ölçülür
  ve **CI'a taban olarak girer**; yeni kod tabanı düşürürse kırmızı.
- [ ] **P1.2** Kapsam **boşluğu raporu** çıkar: hangi modül en az
  ölçülüyor. Yeni test yazımı sırası bu rapora göre yapılır.
- [x] **P1.3** **Sessiz yutma = 0** (2026-10-01 kapandı). AST ölçümü
  (grep değil): **59 → 0**. Kural tek cümle: *bir `except` bloğu yalnız
  `pass` içeremez* — ya `logger` izi bırakır ya da akışı düzeltir.
  Kural teste kilitli: `tests/test_sessiz_yutma.py`.
  Ölçüm kapsamı: üretim kodu (`tests/`, `_arsiv/`, `__pycache__/` hariç).
  `except → return` olan satırlar kontrol akışıdır, zaten sayılmıyordu.

  **Ölçüm düzeltmesi:** İlk yazımdaki 56/58 sayıları **grep** tabanlıydı
  ve yanlıştı; AST ile gerçek taban **59** çıktı (kök `_olcum_*.py`
  probeleri dahil, bunlar da kapatıldı). Dağılım (AST, üretim):

  | Dosya | Adet |
  |---|---|
  | `basak_app.py` | 10 |
  | `app.py` | 8 |
  | `basak_web.py` | 6 |
  | `brain/brain.py` | 5 |
  | `chat/oturum.py`, `memory/postgres.py`, `tools/freetools_kopru.py`, `tray.py` | 3'er |
  | `brain/kullanim.py`, `chat/kimlik.py`, `conftest.py`, `kullanici.py`, `memory/engine.py`, `voice/tts.py`, `_olcum_*.py` | 2'er (+3'er probeler) |
  | `chat/context.py`, `telegram_bot.py`, `tools/__init__.py`, `tools/saglik.py`, `tools/web_search.py`, `voice/speaker_id.py` | 1'er |

  **Kritik olanlar (körlemesine loglanmadı):**
  - `kullanici.py:207` — anahtar yazılamazsa **her açılışta yeni anahtar**
    üretilir, tüm oturumlar geçersizleşir → `logger.warning`.
  - `chat/kimlik.py:159` — taşıma bayrağı yazılamazsa taşıma her açılışta
    tekrarlanır → `logger.info`.
  - `tools/freetools_kopru.py:128` — **SSRF modülü yüklenemezse** kontrol
    düşüyordu; artık `logger.warning` ile en azından görünür.
  - `conftest.py:73/82` — test izolasyonu kurulamazsa testler **gerçek**
    `kullanicilar.json`'a dokunurdu; artık `RuntimeError` fırlatır.
  - `brain/brain.py:385` — zincir davranışı **bilerek değiştirilmedi**
    (yalnız iz bırakıldı); ölçülmemiş davranış değişikliği yapılmadı.
- [ ] **P1.4** **Gecikme bütçesi** ölç: tipik sohbet turu, `sayfa_oku`,
  `konum_coz`, `sirket_ara` süreleri. Tavan **koyulmaz** — yalnız
  ölçülür ve sapma varsa kovulur (AGENTS.md §0: tavan geri gelmez).

**Faz kapısı:** Sayısal kapsam tabanı CI'da; **sessiz yutma 0**
(ölçüldü, teste kilitli); gecikme tablosu belgeli.

---

### P2 — YAYIN GÜVENLİĞİ

- [ ] **P2.1** **Ön üretim kapısı:** production'a otomatik giden yol
  durdurulur veya en az `production`'a otomatik giden dal kısıtlanır;
  hedef: **merge otomatik deploy etmesin**, deploy bilinçli olsun.
  Vercel "Promote previous deployment" ile bedava geri dönüş **vardır**
  (ölçüldü) — önce bu yol bir kez prova edilir.
- [ ] **P2.2** **Geri alma provası yazılı:** bir production deployment'ı
  geri alınır, sayfa 200 verir, kayda geçer. Provasız "geri alabiliriz"
  denmez.
- [ ] **P2.3** **Tekrarlanabilir kurulum:** `Dockerfile` **veya**
  `Procfile` — yerel ile üretimin aynı bağımlılığı çalıştırdığının
  kanıtı. (Bugün yalnız `requirements.txt` var; hepsi sabitli, bu iyi,
  ama ortam eşitliği ölçülmüyor.)
- [ ] **P2.4** Ortam sırrı disiplini: `freebuff-env` / Vercel ayrımı
  yazılı. `ayarlar.json`, `gecmis.json`, `.env*` commit'e girmiyor —
  korunuyor, **kural yazıya geçirilmemiş**.

**Faz kapısı:** Merge production'ı kendiliğinden tetiklemiyor (ya da
kasıtlıysa yazılı); geri alma provası yapılmış ve kayıtlı.

---

### P3 — GÖZLEMLENEBİLİRLİK

- [ ] **P3.1** **Sağlık ucu:** orkestratör için kimliksiz, ucuz
  `/healthz` (yüklemli ucuz, bağımlılık listesi vermez). `/api/durum`
  **token'lı kalır** — kimliksiz bırakılmaz.
- [ ] **P3.2** **Hata taksonomisi:** `tools/permissions.py` zaten
  etiket→politika tablosuna sahip. Web uçlarındaki hata gövdesi tek bir
  biçime iner: `kod` + ` insan metni`. Bugün metin serbest yazılıyor.
- [ ] **P3.3** **Araç çağrı kaydı** zaten var (`data/audit/`, gizli alan
  maskeli, `tests/test_log_kirmalama.py` yeşil). Eksik olan: **hata
  sınıfı sayacı** — hangi araç kaç kez hata verdi. Karne
  (`brain/karne.json`) bunu model için tutuyor; operasyon için toplam yok.
- [ ] **P3.4** **Canlı rapor → deploy kanıtı (ÖLÇÜLDÜ):** `tests/live`
  çıktısı `data/canli-rapor/`'a yazılıyor ve bu klasör **`.gitignore`
  satır 51'de** → P0.2 kanıtı **depoya girmiyor**. Karar P0.2'de
  verilir: rapor özeti (test sayısı + geçen/kaçan) plana yazılır, ham
  çıktı gitignore'da kalır.

**Faz kapısı:** Sağlık ucu cevap veriyor; her hata tek biçimde
ayrılabiliyor; araç hata sayacı okunabiliyor.

---

### P4 — VERİ

- [ ] **P4.1** **Postgres yedekleme + geri yükleme provası.** Kişi
  hafızası Postgres'te; geri yükleme provası yapılmadan "veriniz
  duruyor" denmez.
- [ ] **P4.2** **Saklama süresi** (KVKK): kişi başı `data/<uid>/`
  silinme süresi yazılı. Şu an kalıcı ve süresiz.
- [ ] **P4.3** **Şema göçü disiplini:** `memory/engine.py` otomatik
  migrasyon yapıyor (`onem` kolonu testle kanıtlı). Yeni şema değişikliği
  için aynı disiplin yazıya geçirilir.
- [ ] **P4.4** Geliştirici kimlik verisi (`data/<uid>/`) gitignore'da —
  `7a98b72` ile sabitlendi. Korunur, sadece teyit edilir.

**Faz kapısı:** Yedek alınıp **geri yüklenmiş** bir kayıt var; saklama
süresi yazılı.

---

### P5 — YASAL VE YAYIN

- [ ] **P5.1** `docs/KVKK-ENVANTER.md` ↔ `web/bilgilendirme.html` eşliği
  testle zorlanıyor (`tests/test_web_gizlilik_beyani.py`, 6 test) —
  **korunur**. Z2 kararı (D4b = B) sayesinde bu faza yeni madde
  eklenmedi: gömülü harita karosu yok, üçüncü taraf isteği yok.
- [ ] **P5.2** Avukat görevleri (`docs/FAZ5-YAYIN-PLANI.md` §4): KVKK
  aydınlatma, çerez politikası, şartlar, sorumluluk reddi. **Casper'ın
  işi**; ajan yalnız hatırlatır.
- [ ] **P5.3** Mali görevler: bağış/sponsor gelir modeli, beyan.
- [ ] **P5.4** Arama motoru görünürlüğü: sitemap gönderimi ve Domain
  doğrulaması.

**Faz kapısı:** Yasal maddeler ya teslim edildi ya da bilinçli olarak
beklemede olarak yazılı.

---

## 4. Kapı kuralı (P0.7 ile yazılı hale gelir)

```
ESKİ:  main'e merge  →  23 sn sonra production   (ölçüldü)
YENİ:  merge  →  kapı  →  production   (kapı: testler + canlı kanıt)
```

Geri alma: Vercel → önceki production deployment → "Promote to
Production" (ölçüldü: mevcut ve bedava). **P2.2 bu yolun provasını
yazmadan "geri alabiliriz" denmeyecek.**

---

## 5. Bilinçli kapsam dışı (bu planda olmayacak)

| Konu | Neden |
|---|---|
| Yeni dilde/framework yazımı | 36k satır Python, 1103 test — taşıma kazançtan büyük risk |
| Yeni model sağlayıcı ekleme | Zincir 8 sağlayıcı, kota/soğuma/karne ölçülmüş; sayı değil güvenilirlik eksik |
| Kapsam/özellik kataloğu | AGENTS.md §0: katalog uydurmak yasak |
| Harita zincirinin Z3–Z5'i | Özellik hattı, MVP değil — ayrı planda |
| Tavan/rozet/deney katmanı | Daha önce söküldü, geri gelmeyecek |

---

## 6. Kayıt

- **2026-10-01** Plan yazıldı. Taban: 1103 geçti / 19 atlandı / 1F+3E
  (bilinen Windows taban hatası), 57 araç, 15 alan, 36.241 üretim satırı.
- **2026-10-01 (düzeltme)** İlk yazımda sessiz yutma sayısı **15** yazılmıştı;
  ölçüm tekrar yapıldı, **gerçek sayı 58** (üretim kodu, probeler hariç) —
  planda düzeltildi. Ayrıca `data/canli-rapor/`'ın gitignore'da olduğu
  **ölçülerek** doğrulandı (satır 51); "olabilir" yerine "kesin" yazıldı.
- **2026-10-01 (P1.3 kapandı)** Sessiz yutma sıfırlandı. Ölçüm **AST**
  ile yeniden yapıldı (grep sayımı yanlıştı): taban **59**, sonuç **0**.
  59 yerin tamamı dosya dosya açılıp karar verildi: 55'i `logger` izi
  (seviye seçildi: `debug` normal akış, `warning` veri/kimlik riski,
  `info` tekrar eden iş), 2'si akış düzeltmesi (`basak_web.py`
  `KeyboardInterrupt` → kapanış cümlesi), 2'si `conftest.py`'de
  `RuntimeError` (test izolasyonu sessizce bozuluyordu).
  Kural teste kilitlendi: `tests/test_sessiz_yutma.py` (5 test;
  sayaç gerçekten çalıştığını kurgusal örneklerle kanıtlıyor).
- **P0 kapısı geçmeden bu belge "profesyonel" sayılmaz.** MVP kanıtı
  eksik: gerçek modelle, gerçek kullanıcı sorusuyla, uçtan uca koşmuş
  sohbet kaydı **yok**.
