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
| Kapsam ölçümü | **pytest-cov kuruldu** — genel **%80**, üretim **%68,7**, masaüstü katmanı hariç **%73,5** |
| Tekrarlanabilir kurulum | Dockerfile/Procfile **yok** |
| Production davranışı | **`main`'e merge = otomatik production deploy** (ölçüldü: merge 09:33:19Z → deploy 09:33:49Z) |
| CI sağlayıcı kabulü | `test.yml:96` → **ölü dal** (`preview/fatura-goz-cerrahi-20260927`); **hiç koşmuyor** |
| Canlı kabul paketi | `tests/live/` = 19 test, `--live` kapısı arkasında, CI klasörü tümüyle yok sayıyor |
| Kural belgesi | `CANLI-KAPISI.md` **yazıldı** (2026-10-01) |

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
- [x] **P0.4** `CANLI-KAPISI.md` **yazıldı** (2026-10-01). 4 dosyanın
  atıf yaptığı eksik kural belgesi: `--live` mekanizması, 19 atlanan
  testin dağılımı, kapının dört **ölçülmüş** sebebi, CI'daki **ölü dal
  koşulu** (`test.yml:96`) kaydı ve “ne sayılır / ne koşulmaz” sınırı.
- [x] **P0.5** **Ölçüldü, sınır yazıldı.** Canlıda `POST /api/kimlik` →
  **200** + imzalı çerez (`u9976591660579896`) ⇒ üretimde **en az biri**
  tanımlı. *Hangisi* tanımlı **dışarıdan ayırt edilemiyor**:
  `kullanici.py:181` ikisini de kabul ediyor (`BASAK_OTURUM_ANAHTARI`
  öncelikli, yoksa `BASAK_WEB_TOKEN`) ve imza aynı anahtarla atılıyor.
  Kesin belirleme **Vercel panelindeki env listesine** bakmayı gerektirir;
  bu turda panel erişimi yok. Uydurma değil, ölçülen sınır.
- [ ] **P0.6** Ekran görüntülerine **göz at**: `_z2_kanit/z2_masaustu.png`
  (1100×900), `z2_mobil.png` (390×780). DOM ölçümü var, **gözle
  inceleme yok** — bu ajan görüntü okuyamıyor, dosya boyutu ölçüldü
  ama içerik incelenmedi. **Casper'ın gözüne veya yeni bir turda
  görüntü okuyan bir adıma kalmıştır.**
- [x] **P0.7** `docs/FAZ5-YAYIN-PLANI.md` **düzeltildi** (2026-10-01).
  Belge “ajan `vercel --prod` calistirir, 1 deploy” diyordu; bu adım
  **yok**. Ölçüm: PR #20 merge `8067205` **09:33:19Z** → production
  deployment **09:33:49Z** (**30 saniye**). Kapı “deploy” değil,
  **merge öncesi kontrol**; geri alma da `revert merge` veya Vercel
  promote. Belgenin 1., 2. ve 5. maddeleri buna göre yeniden yazıldı.

**Faz kapısı:** P0.1–P0.6 tamam; P0.7 yazılı. Kanıt: koşu raporu +
10 maddenin sonucu + iki ekran görüntüsü.

---

### P1 — ÖLÇÜLEBİLİRLİK

- [x] **P1.1** `pytest-cov` **önce var mı doğrulanır** (AGENTS.md §5) —
  **yoktu** (`pip show pytest-cov` → bulunamadı). Kuruldu: `pytest-cov==7.1.0`
  + `coverage==7.16.2`, `requirements.txt`'e `==` sabitli eklendi.
  `.coveragerc` yazıldı (neyin ölçülüp neyin ölçülmediği tanımlı).
  **Taban ölçüldü ve CI'a girdi:** `--cov-fail-under=60`
  (`test.yml`). Dürüst sınır: ölçüm **bu Linux sandbox'ında** yapıldı
  (11.454 ifade, **%69** dal ölçümüyle); CI `windows-latest`'te
  `sounddevice`/`pywebview` kurulu olduğu için orada daha **yüksek**
  çıkacak. 60 tabanı kasıtlı olarak aşağıda — ölçülmemiş bir sayıyı
  kapı yapmıyoruz.

  **Ölçülen kapsam (2026-10-01, `pytest tests --ignore=tests/live`):**

  | Kapsam | Sonuç |
  |---|---|
  | Genel (testler dahil) | **%80** |
  | **Üretim kodu** (testler/probeler hariç) | **%68,7** |
  | Masaüstü katmanı hariç (sunucu + çekirdek) | **%73,5** |

  Genel %80 rakamı **şişkindir**: içine test dosyalarının kendi kapsamı
  ve kurulu olmayan `voice/` modülleri giriyor. **CI kapısı üretim
  tabanına yakın 60'dır.**
- [x] **P1.2** **Boşluk raporu çıkarıldı** (aynı ölçümden, aşağıda).
  Hiç ölçülmemiş (%0) **18 modül / 1.398 satır** — bunların çoğu bu
  ortamda kurulu olmayan masaüstü bağımlılıkları; yeni test yazımı
  sırası aşağıdaki tabloya göre yapılır.

  | Modül | Satır | Kapsam | Durum |
  |---|---|---|---|
  | `voice/speaker_id.py` | 130 | **%0** | `sounddevice` kurulu değil |
  | `voice/speaker_db.py` | 92 | **%0** | aynı |
  | `voice/stt.py` | 78 | **%0** | aynı |
  | `voice/tts.py` | 66 | **%9** | aynı |
  | `tray.py` | 45 | **%0** | `pystray` yok |
  | `basak_app.py` | 350 | **%0** | `pywebview` yok — **en büyük boşluk** |
  | `tools/image_analyzer.py` | 206 | %49 | model yolu canlı gerektiriyor |
  | `tools/freetools_kopru.py` | 236 | %49 | Chromium + canlı ağ |
  | `tools/olcum.py` | 207 | %58 | `gh` + git ağacı gerektiren yollar |
  | `tools/reminders.py` | 180 | %49 | zamanlayıcı arka plan işi |

  **Yorum (ölçülmüş):** Boşluğun çoğu **eksik paketten** değil,
  **canlı bağımlılıktan** geliyor. Bu yüzden yeni test yazmadan önce
  satır sayısı değil, **hangi davranışın kanıtlanmadığı** sorulmalı.
- [x] **P1.3** **Sessiz yutma = 0** (2026-10-01 kapandı). AST ölçümü
  (grep değil): **59 → 0**. Kural tek cümle: *bir `except` bloğu yalnız
  `pass` içeremez* — ya `logger` izi bırakır ya da akışı düzeltir.
  Kural teste kilitli: `tests/test_sessiz_yutma.py`.
  **Kapı daha sonra işe yaradı:** P1.4 ölçüm probu yazılırken probun
  kendi sessiz yutmasını yakalayıp koşuyu kırmızıya düşürdü; düzeltildi.
  Yani kural yalnız geçmişe değil, **yeni yazılan koda** da uygulanıyor.
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
- [x] **P1.4** **Gecikme tablosu ÖLÇÜLDÜ** (2026-10-01). Tavan
  **koyulmadı** — bu bir bütçe değil, ölçüm kaydı (AGENTS.md §0: tavan
  geri gelmez). Probu: `scripts/olcum/_gecikme_olcum.py`, her iş **3 kez** koşuldu;
  ilk ölçüm **soğuk** (DNS + TLS + bağlantı kurulumu), kalanı **sıcak**.
  Tek ölçüm "tipik süre" değildir.

  **Ölçülen tablo (Linux sandbox, gerçek ağ):**

  | İş | Soğuk | Sıcak ort. | Sıcak en fazla | Not |
  |---|---|---|---|---|
  | `sayfa_oku` | 0,118 sn | **0,116 sn** | 0,117 sn | 4.000 karakter |
  | `hazirlik_belleg` | 0,000 sn | **0,007 sn** | 0,009 sn | model çağrısı YOK |
  | `dispatcher_konum_coz` | 1,765 sn | **1,962 sn** | 2,124 sn | JSON dönüşü dahil, photon |
  | `konum_coz` | 1,797 sn | **1,857 sn** | 1,930 sn | 5 aday, photon |
  | `sirket_ara` | 11,079 sn | **9,460 sn** | 10,018 sn | en ağır: arama + sayfa okuma |

  **Okuma:** `sayfa_oku` **0,1 sn** — tartışmaya değmez. `sirket_ara`
  **9–11 sn** — bunun tamamı ağ; tek araç olarak bir sohbet turunu
  10 saniye uzatıyor. `konum_coz` ~2 sn. **Bağlam hazırlığı** ise
  **7 milisaniye** — ölçülen hiçbir yerde darboğaz değil.

  **Soğuk/sıcak farkı ölçüldü:** `konum_coz` ilk çağrıda 1,797 sn,
  sıcak 1,857 sn — yani bu işte TLS kurulumu ihmal edilebilir.
  `sirket_ara`'da fark daha büyük (11,08 → 9,46).

  ### Sınır: model çağrısı ÖLÇÜLEMEDİ

  Bu ortamda **sağlayıcı anahtarı yok**. “Tipik sohbet turu”nun en
  büyük kalemi model çağrısıdır (ölçülmüş geçmiş: 5,7–41,3 sn) ve
  **burada ölçülmedi**. Ölçülen şey tam olarak şudur: **ağ katmanı ve
  araç süresi.** Model gecikmesi için ölçüm Casper'ın ortamında
  yapılmalı; uydurma süre yazılmadı.

  ### Ölçüm iki GERÇEK KUSUR buldu

  Tablo ilk çıktığında iki sayı yanlıştı; ikisi de koddu, ölçüm değil:

  1. **URL çift kodlama.** `quote()` varsayılan olarak `%` işaretini de
     kodlar; zaten kodlanmış bir URL ikinci kez kodlanıyordu:
     `/wiki/Ba%C5%9Fak` → `/wiki/Ba%25C5%259Fak` → **HTTP 404**.
  2. **Ham Türkçe karakter.** Yalnız PATH kodlanıyordu; QUERY ve NETLOC
     ham kalıyordu. Türkçe karakter içeren adreslerde
     `UnicodeEncodeError` **tüm sayfa okumayı** düşürüyordu —
     `sirket_ara("Trendyol")` aday sayfalarından birinde bu yüzden
     hata veriyordu.

  Düzeltildi (`%` güvenli; query/netloc de kodlanıyor, alan adı IDNA).
  **Ölçülen etki:** `konum_coz` sıcak **3,878 sn → 1,857 sn**
  (yariya indi). 12 yeni regresyon testi (`tests/test_url_kodlama.py`),
  SSRF savunması ayakta (52 güvenlik testi yeşil).

  **Durüst kayıt — ölçümün kendi hatası da düzeltildi:** probun ilk
  sürümü `sayfa_oku` çıktısında `icerik` alanını okuyordu; araç
  `result` döndürdüğü için tabloya **0 karakter** yazdı ve 404 sanıldı.
  Araç çalışıyordu (ölçüldü: 127.037 karakter). Düzeltilip yeniden
  ölçüldü — tablodaki sayılar ikinci koşunundur.

**Faz kapısı:** Sayısal kapsam tabanı CI'da ✅ (`--cov-fail-under=60`);
**sessiz yutma 0** ✅ (ölçüldü, teste kilitli); boşluk raporu ✅;
gecikme tablosu ✅ (tavan konmadı, model kısmı sınırla belirtildi).

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
- **2026-10-01 (P0.4/P0.5/P0.7 + P1.1/P1.2)**
  - **P0.4:** `CANLI-KAPISI.md` yazıldı — 4 dosyanın atıf yaptığı eksik
    kural belgesi. Ölü dal koşulu (`test.yml:96`) belgeye yazıldı.
  - **P0.5:** canlıda `POST /api/kimlik` → 200 + imzalı çerez ölçüldü
    ⇒ en az bir anahtar tanımlı. Hangisi olduğu **dışarıdan
    ayırt edilemiyor** (`kullanici.py:181` ikisini de kabul ediyor,
    imza aynı). Panel erişimi olmadığı için kesin belirleme yapılamadı
    — **tahmin yazılmadı.**
  - **P0.6:** **AÇIK.** Görüntülerin boyutu ölçüldü (1100×900,
    390×780) ama **içerik gözle incelenmedi** — bu ajan görüntü
    okuyamıyor. Dosyalar bu yüzden repoya da girmedi (repodan hiç
    görsel izlenmiyor, tutarlılık için).
  - **P0.7:** `FAZ5-YAYIN-PLANI.md` düzeltildi. “Ayrı `vercel --prod`
    adımı” **yok** — merge otomatik production deploy tetikler
    (ölçüm: merge 09:33:19Z → deploy 09:33:49Z). Kapı **merge öncesi
    kontrol** oldu.
  - **P1.1:** `pytest-cov` **yoktu** (doğrulandı), kuruldu
    (`==7.1.0`). Taban ölçüldü ve CI'a girdi (`--cov-fail-under=60`).
    Genel %80 / **üretim %68,7** / masaüstü hariç **%73,5**.
  - **P1.2:** boşluk raporu: **18 modül / 1.398 satır %0**. En büyüğü
    `basak_app.py` (350 satır) — `pywebview` kurulu olmadığı için
    ölçülemiyor. Boşluğun çoğu **eksik paketten**, canlı
    bağımlılıktan geliyor.
- **2026-10-01 (P1.4)** Gecikme tablosu ölçüldü, **tavan konmadı**.
  Soğuk/sıcak ayrımı yapıldı (her iş 3 kez). Sonuç: `sayfa_oku` 0,116 sn,
  `konum_coz` 1,857 sn, `sirket_ara` 9,460 sn (en ağır), bağlam hazırlığı
  0,007 sn. **Model çağrısı ölçülemedi** (ortamda sağlayıcı anahtarı yok);
  bu ortamda ölçülen ağ katmanı ve araç süresidir.
  **Ölçüm iki gerçek kusur buldu ve ikisi de düzeltildi:** (a) `quote()`
  `%` işaretini de kodladığı için önceden kodlanmış URL'ler 404 alıyordu;
  (b) yalnız PATH kodlandığı için Türkçe karakterli adreslerde tüm sayfa
  okuma `UnicodeEncodeError` ile düşüyordu. Etkisi ölçüldü: `konum_coz`
  sıcak süre 3,878 sn → **1,857 sn**. 12 regresyon testi eklendi,
  SSRF savunması 52 testle doğrulandı.
  **Dürüst kayıt:** ölçüm probunun ilk sürümü `sayfa_oku` çıktısında
  yanlış alanı (`icerik`) okuduğu için tabloya 0 karakter yazdı ve 404
  sandı; araç çalışıyordu. Prob düzeltilip yeniden ölçüldü.
- **2026-10-01 (sirket_ara hızlandırma)** P1.4 ölçümünde `sirket_ara`'nın
  tek başına **9–11 sn** sürdüğü görüldü. Kırılım ölçüldü
  (`scripts/olcum/_sirket_ara_kirilim.py`): asıl maliyet aday sayfaların **sıralı**
  okunmasıydı (%44) ve `firma_bul`'un iki paralel aramasıydı.

  **İki daraltma DENENDİ ve REDDEDİLDİ:**
  - **Tek aramaya düşürme:** iki sorgu neredeyse **ayrı** host getiriyor
    (kesişim 1/6). Atılırsa kapsam daralırdı. Uygulanmadı.
  - **Erken çıkış:** ölçümde 3 markadan 1'inde kart değişmiş görünüyordu
    — **ama bu ölçüm hatasıydı** (farklı aday listeleri karşılaştırılmış).
    Dondurulmuş liste ile tekrar ölçüldü: kart aynı. **Karar geçersiz;
    bu daraltma yeniden değerlendirilebilir.**

  **Uygulanan:** aday sayfalar **3 iş parçacığıyla paralel** okunuyor.
  Kontrollü ölçüm: sıralı **6,101 sn → 2,749 sn (%55)**. Sıra ve kart
  korunuyor: `kurum_sayfasi_oku` saf bir fonksiyon ve `map` girdi sırasını
  döndürüyor; seçim kuralı zaten sıradan bağımsız (`uyuyor` önce, sonra
  `skor`). **Daraltma yapılmadı** — aday sayısı (3 site × 2 yol) ve arama
  sayısı aynen korundu.
  10 yeni test (`tests/test_sirket_ara_paralel.py`), 99 katalog testi yeşil.
  → **Düzeltme kaydı:** bu işin erken çıkış gerekçesinde geçen
  “kimin.net.tr Trendyol sanıldı” tespiti **sonradan yanlış çıktı**;
  ayrıntılı ölçüm aşağıdaki kayıtta.
- **2026-10-01 (Trendyol / kimin.net.tr araştırması)** Soru: erken çıkış
  denemesinde `kimin.net.tr` Trendyol seçildi — neden? Ölçülen cevap:
  **çünkü o sayfa aslında "ait" sayılmıyor.** Canlı sayfa 3 kez okundu,
  `_host_markaya_uyuyor` ve `_sayfa_markaya_ait` her seferinde `False`
  döndü (sayfanın tek gerçek bloğu `{"ad": "myblog"}`).

  **Önceki kayıt YANLIŞTI ve düzeltildi.** “Erken çıkış kartı bozdu”
  iddiası bir **karşılaştırma hatasından** kaynaklanıyordu: prob her
  koşuda `firma_bul`'u yeniden çağırıyordu, arama sonuçları koşular
  arası değiştiği için iki koşu **farklı aday listeleriyle** çalışmıştı.
  Dondurulmuş liste ile tekrar ölçüldü → kart **AYNI**. Yani “erken
  çıkış güvenli değil” kararı **geçersiz** bir ölçüme dayanıyordu.

  **Gerçek bulgu — `_host_markaya_uyuyor` alt dize karşılaştırması:**
  `anahtar in etiket_anahtar` yüzünden markayı **herhangi bir yerinde**
  geçen host eşleşiyor. Ölçülen yanlış pozitifler:
  `trendyol-korsan.com`, `vestel-isyeri.com`, `milyontrendyol.com`.
  Bu, sahte marka sitelerinin “markaya ait” sayılması demek.

  **Düzeltildi (2026-10-01, aynı gün):** Önceki kayıt “düzeltme
  güvenli değil” diyordu; bu **sonradan aşıldı**. Çözüm: dize kalıbı
  değil, **ek’in anlamı**. Sözlük `scripts/olcum/_marka_ekleri_veri.py` ile
  **23 gerçek markanın sitesi ölçülerek** kuruldu (elle doldurulmadı):

  | Ek | Kaynak | Karar |
  |---|---|---|
  | `elit` | `tutkuelit.com.tr` (kendi kaydımız) | KABUL |
  | `holding` | `yildizholding.com.tr` | KABUL |
  | `efes` | `anadoluefes.com.tr` | KABUL |
  | `korsan`, `isyeri`, `milyon`, `sitez` | sahte site kalıpları | RED |

  Ölçümün bulgusu şuydu: gerçek markalarda ek **ya yok ya da anlamlı**;
  sahte kalıplarda da sonda ama **anlamsız**. Dize kalıbı ikisini
  ayıramıyordu, sözlük ayırıyor.
  Kural **fail-closed**: ek sözlükte yoksa reddedilir — yeni bir sahte
  kalıp sözlüğe girmeden de elenir.

  **Doğrulama:** 23/23 gerçek marka eşleşiyor, **8/8** ölçülmüş yanlış
  pozitif eleniyor (önceden 5 tanesi geçiyordu), 159 katalog testi yeşil.

  Ayrıca ölçülen ikinci davranış: JSON-LD bloğunda `ad`/`url` **boşsa**
  blok “başkasının” denenmiyor ve sayfa **fail-open** olarak “ait”
  sayılıyor. Kayda geçti, değiştirilmedi.

  28 test (`tests/test_marka_ait_olcumu.py`) bulguları kilitliyor;
  yanlış pozitifler **kasıtlı olarak bugünkü haliyle** testte sabitlendi
  ki kural değişirse bilinçli karar verilsin.
  → **Sonuç (aynı gün):** marka ekleri sözlüğü kuruldu ve düzeltme
  **uygulandı**. 50 test, 23/23 gerçek marka korunuyor, 8/8 sahte site
  eleniyor. Bilinen sınır: fail-closed yüzünden gerçek bir marka
  `tutkuelit` gibi görünürse **elenir** — bu yönde hata üretmektense
  alan adı kaybı yeğdir, ama liste ölçümle genişletilmelidir.
- **2026-10-01 — üretim öncesi denetim, 2. ASCII hatası buldu.** Merge
  öncesi `_uretim_import_denetimi.py` (import + uç + sözlük kontrolü)
  **GECTI**, ama canlı `sirket_ara("Trendyol")` koşusu yine
  `Sayfa okuma hatasi: 'ascii' codec can't encode character '\xe7'`
  döndürdü. İzleme gösterdi adres `sayfa_oku`'ya değil
  `kurum_sayfasi_oku` → `_ham_sayfa_getir` hattına giriyor; orada
  **kodlama hiç yoktu**. Yani P1.4'te bulunan hatasının düzeltmesi
  (`_url_kodla`) yalnız `sayfa_oku` yoluna konmuştu.

  Düzeltme: kodlama **tek yere** toplandı (`_url_kodla`), dört çağrı
  yolu da ondan geçiyor — `sayfa_oku`/`derin_oku`, `_ham_sayfa_getir`,
  `adres_kontrol`, `sayfa_gorseller`. Satır içi kopya silindi.
  Sıra korundu: kodlama `_guvenli_adres`'ten **önce** (test kilitli).
  **SSRF savunması değişmedi** — `_engelli_ip_nedeni` /
  `_guvenli_adres` / `_GuvenliYonlendirme` aynı yerde, aynı şekilde.

  **Ölçüm (eski kod ↔ yeni kod, aynı makine, gerçek ağ):**

  | URL | ESKİ | YENİ |
  |---|---|---|
  | `tr.wikipedia.org/wiki/Türkçe` | 0 bayt, UnicodeEncodeError | **200, 877.713 bayt** |
  | `accio.com/supplier/tr/trendyol-tedarikçi-iletişim` | 0 bayt, UnicodeEncodeError | **200, 289.354 bayt** |

  Yani düzeltme yalnız hata mesajını değil, **gerçek veri kaybını**
  kapatıyor: accio sayfası daha önce hiç okunamıyordu.
  10 yeni test (`tests/test_url_kodlama.py`, 12 → 22) kilitliyor:
  kodlama, SSRF sırası, iç adres engeli, idempotans, tek kopya kuralı.
  Geniş koşu: **1190 geçti**, kapsam %66,69 (kapı 60).

  **Dürüst sınır:** `sirket_ara("Trendyol")` uçtan uca bu gün
  **boş kart** döndürdü — ama **eski kod da döndürdü** (aynı anda
  ölçüldü: arama motorları 403/429/captcha veriyor: Google "sorry",
  Brave 429, Mojeek 403, Startpage captcha). Yani bu bir gerileme
  değil, ortamın kısıtı; bu koşu bugün gecikme ölçümüne kanıt
  üretemez.
- **P0 kapısı geçmeden bu belge "profesyonel" sayılmaz.** MVP kanıtı
  eksik: gerçek modelle, gerçek kullanıcı sorusuyla, uçtan uca koşmuş
  sohbet kaydı **yok**.
