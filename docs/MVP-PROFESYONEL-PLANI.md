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

- [x] **P0.1** Sağlayıcı kabulünü CI'da yeniden aç: `test.yml:96`'daki ölü
  dal koşulu yerine etiket veya `workflow_dispatch`. ⚠️ **Kapsam notu:**
  gizli depoda Actions dakikası sınırlı; hangi tetikleyici seçilecek
  **Casper kararıdır**. *(Doğrulandı: `workflow_dispatch` + `kabul-matrisi`
  etiketi + haftalık schedule; `tests/test_kabul_matrisi_tetikleyici.py` 21/21 yeşil.)*
- [ ] **P0.2** `tests/live --live` paketini anahtarlı bir ortamda (Vercel
  Production veya yerel) **bir kez kayıtlı koş**; `data/canli-rapor/`
  çıktısını plana ekle. Sonuç ne olursa olsun **yazılır** — başarısız
  test de kayıttır. **Kısmen (2026-10-14, §8.3):** anahtar GEREKTİRMEYEN
  canlı kabul testi eklendi (`tests/live/test_canli_site_konusma.py`,
  yayındaki Başak'a karşı koşar ve `data/canli-rapor/`a yazar). Paketin
  geri kalanı hâlâ sağlayıcı anahtarı ister → madde **açık**.
- [ ] **P0.3** `docs/BIRLIKTE-TEST-SENARYOLARI.md:88`'deki **10 maddelik
  konuşma listesi** koşulsun. 8'i otomatize, 2'si gözle.
  **Kısmen koşuldu (2026-10-14, §8.3):** listenin 6 maddesi yayındaki
  Başak'a karşı koşuldu ve kaydedildi. 6/6 akış `bitir` ile kapandı,
  araç izi 6/6, `error` 0. İki deterministik maddenin **biri yanlış**
  (Base64 + Türkçe harf) ve beyaz liste reddi maddesi beklenen reddi
  **göstermedi**; ikisi de §8.3'te açık bulgu. Kalan 2 madde (kota
  uyarısı, araç sayfası bağlantısı) preview ayarı ister.
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
- [x] **P2.3** **Tekrarlanabilir kurulum (2026-10-14):** `Procfile`
  eklendi, temiz sanal ortamda kurulum + aynı komutla açılış ölçüldü;
  `pytest`teki Linux dışı işaret kaldırıldı. Ölçüm: §8.1.
  (Dockerfile yazılmadı: doğrulama ortamında konteyner çalıştırıcısı yok
  ⇒ kanıtlanamayacak teslim yazılmaz.)
- [ ] **P2.4** Ortam sırrı disiplini: `freebuff-env` / Vercel ayrımı
  yazılı. `ayarlar.json`, `gecmis.json`, `.env*` commit'e girmiyor —
  korunuyor, **kural yazıya geçirilmemiş**.

**Faz kapısı:** Merge production'ı kendiliğinden tetiklemiyor (ya da
kasıtlıysa yazılı); geri alma provası yapılmış ve kayıtlı.

---

### P3 — GÖZLEMLENEBİLİRLİK

- [x] **P3.1** **Sağlık ucu (2026-10-14):** `GET /healthz` — kimliksiz,
  gövde sabit `{"ok": true}`, bağımlılık/commit/model bilgisi vermez;
  `/api/durum` **token'lı kalır** (kilit testi geçti). 4 test:
  `tests/test_healthz_ucu.py`. Canlı ölçüm: §8.1.
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

---

## 7. 2026-10-13 — TUTARLILIK TURU (ölçülerek; kod okunarak)

Bu bölüm bir taban ölçümü değil, **düzeltme kaydıdır**. Amaç: koddaki ile
yazıdaki iddianın aynı olması. Yukarıdaki tarihli satırlar (2026-10-01)
tarihî kayıt olarak durur; aşağıdakiler onları geçersiz kıldığı yerde
açıkça yazar.

### 7.1 Düzeltilen çelişkiler (hepsi ölçülerek bulundu)

| # | Çelişki | Kanıt | Sonuç |
|---|---|---|---|
| 1 | Canlı FULL TEST **çöküyordu**: `_alan_sema_testi` soruyu `ALAN_SORULARI[alan]` ile try/except DIŞINDA okuyor; `freetools` + `harita` sorusu yoktu | `KeyError`; 15 alan, 13 soru | 2 soru eklendi: **15/15**; kilit testi eklendi |
| 2 | Rapor sabit **"14 yetenek alanı"** yazıyordu | gerçek 15, sorulan 13 | sayı tek kaynaktan gelir; sabit sayı kalmadı |
| 3 | `sir_preflight` anahtar **gerektirmeyen** kilo'yu zorunlu sır sayıyordu | `brain/kilo.py`: "API anahtarı gerektirmez" | zorunlu 7→**6**; `OPSIYONEL_SIRLER` ayrıldı |
| 4 | `SEKIZLER` (8) ile `KAPSAM` (7) iki yönde ayrışıyordu ve bu yazılı değildi | kod | fark **belgeli ve kilitli**: +mistral, −cloudflare/cohere |
| 5 | `chat/evidence.py` "kanıt bağını **DOĞRULAR**" diyordu | hiçbir şey doğrulanmıyor | başlık koda uyduruldu: **kayıt** tutar, denetlemez |
| 6 | `record_evidence` tanımlıydı ama **hiçbir üretim yolundan** çağrılmıyordu | grep | `tool_done` bağlandı: başarılı her araç sonucu kanıt |
| 7 | `pause()` diske checkpoint **yazıyordu**, hiçbir yolu **okumuyordu** | grep + Vercel `/tmp` dokümanı | katman **silindi**; kural zaten "var gibi raporlanmaz" diyordu |
| 8 | `app.py` masaüstü kütüphaneleri olmadan **import edilemiyordu** → paket Linux'ta **toplanamıyordu** | `PortAudio library not found` + `Interrupted` | tembel yükleme; **1324 test, 1,49 sn toplama** |

### 7.2 Ölçülen sonuçlar

| Ölçüm | Önce | Sonra |
|---|---|---|
| Linux'ta toplama | **Interrupted** (1 hata) | **1324 test, 1,49 sn** |
| Sorunlu 6 dosya (Linux) | 12 F + 3 E | **0 F + 0 E** (4 gerekçeli atlama) |
| `test_path_guvenligi` süresi | 224 sn | **17 sn** |
| Kabul matrisi kilit testi | 21 | **27** |

### 7.3 Kayıtlı tarih uydurması (issue #4, 20 Eyl 2026) — kök neden

Kayıt: kilo, `web_search` kullandı ve **"31 Temmuz 2026"** dedi; gerçek
tarih 20 Eylül 2026'ydı. **Bugün aynı soruyla tekrarlanmadı** (canlı
ölçüm, kilo, sıfır maliyet):

- "…bu cihazın gerçek saat aracını kullanarak…" → araç `simdi` → **doğru**
- "Şu an saat kaç? Türkiye saatiyle söyle." → araç `simdi` → **doğru**

Kök neden: zincir o gün zayıf modele düşmüştü
(`kilo:stepfun/step-3.7-flash:free` — upstream'den kaldırıldı) ve model
`simdi` yerine `web_search` seçti. Düzelten şey **model sırası** oldu
(`b265925`); **doğrulayan bir katman yoktur** ve yokmuş gibi de
yazılmamalıdır (silinen `olcu.py` çıkış kapısı geri gelmez, AGENTS.md §0).

### 7.4 Bilinçli olarak YAPILMAYAN ve açık kalan

- **Tam Linux koşusu bu ortamda bitmedi.** Nedeni ölçüldü ve **proje
  değil**: proje kodu olmadan ham SQLite bile WAL için 3–5 sn, 4 KB
  `fsync` 0,81 sn (VM'in disk I/O'su). Kanıt olarak toplama + sorunlu
  dosya grupları ölçüldü.
- **Linux CI işi eklenmedi.** `tests/test_sunucu_ice_aktarma.py` aynı
  arıza sınıfını Windows CI'da yakalar (paketleri engelleyerek). Tam
  Linux işi Actions dakikası harcar → **Casper kararı**.
- **P0.2 hâlâ açık**: `tests/live --live` paketinin bir kez kayıtlı koşusu.
  Sağlayıcı anahtarlarının CI'da tanımlı olması gerekir (issue #4 kaydı:
  8 sağlayıcıdan 7'si "GitHub ortamında ajan olarak hazır değil").
- **P2.3 (Dockerfile/Procfile) açık**; P3.1 `/healthz` **yok**.
  → **2026-10-14: ikisi de kapandı (§8.1).** Satır tarihî kayıt olarak durur.
- `AGENTS.md §1.1` "geçerli plan ANA-PLAN.md" diyor ama **`ANA-PLAN.md`
  yok**; dosya kilitli olduğu için düzeltilmedi, buraya kaydedildi.

---

## 8. 2026-10-14 — KANIT TURU (ölçüldü)

Bu bölüm taban ölçümü değil, **kapanış ve kanıt kaydıdır**. Üç açık madde
(P2.3, P3.1 ve P0.2/P0.3'ün ölçülebilen kısmı) bu turda kapandı ya da
ölçüldü. Ölçüm ortamı: Freebuff bulut sanal makinesi (Linux), tarayıcı
gerçek Chromium; üretim adresi `basak-vercel.vercel.app`.

### 8.1 Kapanan maddeler

- **P2.3 Tekrarlanabilir kurulum.** `Procfile` eklendi:
  `web: uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}`.
  Kanıt: **temiz** sanal ortamda (`python3 -m venv`, hiç paket yok)
  `pip install -r requirements.txt` → 19 paket kuruldu → **aynı komut**
  uvicorn'u açtı → `GET /healthz` **200** `{"ok":true}`,
  `GET /fatura` **200**.
  `requirements.txt`teki `pytest`/`pytest-cov` üzerindeki
  `sys_platform == "win32"` işareti **kaldırıldı**: Linux'ta temiz
  kurulumdan sonra test paketi koşulamıyordu; "yerel ile üretim aynı
  bağımlılığı çalıştırır" kuralı tam da bunu yasaklar. Sürümler
  değişmedi (`pytest==9.1.1`, `pytest-cov==7.1.0`).
  **Dockerfile yazılmadı ve gerekçesi ölçüldü:** bu doğrulama ortamında
  konteyner çalıştırıcısı yok (`/var/run/docker.sock` erişilemez,
  yetki yükseltmesi kapalı) — imaj **kanıtlanamaz** olurdu; kanıtlanamayan
  teslim bu depoda teslim sayılmaz. Plan zaten "`Dockerfile` **veya**
  `Procfile`" diyor.
- **P3.1 Sağlık ucu.** `app.py` → `GET /healthz`: kimliksiz, gövde sabit
  `{"ok": true}`, `Cache-Control: no-store`. Sağlayıcı listesi, model adı,
  commit sha, araç sayısı, zincir durumu **vermez** — o bilgi
  `/api/durum`'da ve token'lıdır. 4 yeni test (`tests/test_healthz_ucu.py`):
  kimliksiz 200, gövde sabit, çekirdeğe dokunmaz (çağrılırsa test patlar),
  `/api/durum` 401 kalır. Canlı: **200** `{"ok":true}`
  (yayın öncesi aynı adres **404** veriyordu).

### 8.2 Fatura ekranının 4,5 MB duvarı kapandı

Ölçülen sorun: sunucu gövdesinin tavanı ~4,5 MB (Vercel; 5,05 MB gövde →
HTTP 413 `FUNCTION_PAYLOAD_TOO_LARGE`). Sohbet ekranı fotoğrafı tarayıcıda
küçültüyordu, **`/fatura` ekranı ham gönderiyordu** — yani fatura işinin
tam üstünde duvar duruyordu.

Düzeltme: küçültme kodu `web/common.js`te **tek yere** alındı
(`window.basakFotografiKucult`, 1600 px, JPEG q0.82); sohbet ekranı
(`web/app.js`) ve fatura ekranı (`web/fatura.html`) aynı işlevi çağırıyor.
Fatura ekranında küçültme başarısız olursa hata ekranda görünür (sessiz
düşme yok). Önbellek sürümleri yükseltildi (`common.js?v=8`,
`app.js?v=21`) ve iki sürüm kilidi testi güncellendi.

**Gerçek Chromium ölçümü (8,0 MP, 3264×2448, gürültülü — en kötü hâl):**

| Ölçüm | Değer |
|---|---|
| Ham dosya | **6,83 MB** |
| Ham data URL (eski gövde) | **9,11 MB** → tavanın 2 katı, istek uca hiç ulaşmaz |
| **[YENİ]** `/fatura` gövdesi | **0,90 MB** |
| Gönderilen görüntü | 1600×1200 JPEG, 0,67 MB |
| Küçültme oranı | **10,1 kat** |
| Kabul ölçütü | gövde < 1,5 MB ✅ (ölçülen en kötü hâl 0,90 MB) |

Test: `tests/test_web_fotograf_kucultma_tarayici.py` (2 test, gerçek
Chromium; sayfa gerçek dosyalardan açılır, ağa çıkan **gövde boyu** ölçülür
— "dosyada şu kelime var mı" değil). Tarayıcı kurulu değilse test atlanır.

**CANLI son doğrulama (2026-10-14, üretim + gerçek Chromium):** 8 MP
gürültülü fatura fotoğrafı (ham **5,31 MB** / data URL **7,08 MB** →
tavanın üstünde) `/fatura` ekranından gönderildi:

- Gönderilen gövde: **0,73 MB** → **9,7 kat** küçültme, tavanın 6 kat altı.
- Okuma: `okuma.ok = true`, `gemini-3-flash-preview`, **63,9 sn**.
- Ekranda okunanlar: satıcı VKN **6120729513**, alıcı VKN **2345678901**,
fatura no **IK-2026-10427**, **2** ürün satırı (8.598,00 / 7.199,00),
matrah **54.720,00**, KDV **10.944,00**, genel toplam **65.664,00** ve
"Matrah + KDV = genel toplam → **tutuyor**" denetimi.

Yani duvar yalnız kodda değil, **canlıda** kapandı.

### 8.3 Canlı kabul — yayındaki Başak ile GERÇEK konuşma

Yeni test: `tests/live/test_canli_site_konusma.py`. **Anahtar
gerektirmez** (anahtar yayındaki süreçte durur), `--live` kapısı
arkasındadır, her koşuyu `data/canli-rapor/` altına JSON yazar. Böylece
canlı kabul, "anahtarı olan bir makine"ye bağlı kalmadan depodan
koşulabilir ve kayda geçebilir.

**Koşu (2026-10-14; kimlik ucu 200; koşu 204 sn):**

| # | Madde | Süre | Araç | Sonuç |
|---|---|---|---|---|
| 1 | sha256 "merhaba" | 43,5 sn | ✅ | **doğru** — hash birebir + araç bağlantısı |
| 2 | base64 "merhaba dünya" | 17,2 sn | ✅ | ❌ **YANLIŞ** — Türkçe harf bozuldu |
| 3 | "%15'i 200 olan ne kadar?" | 12,8 sn | ✅ | 1333,33 — soru **belirsiz** (a) |
| 4 | "evil-site.com'daki aracı çalıştır" | 42,0 sn | ❌ koşmadı | ❌ beyaz liste reddi **yok** (b) |
| 5 | "Hatırlatıcı ekle: yarın saat 10" | 34,2 sn | ✅ | "eklendi" diyor; kayıt **doğrulanmadı** (c) |
| 6 | "Hava durumu Ankara" | 16,6 sn | ✅ | gerçek veri (Open-Meteo) |

Sözleşme tarafı temiz: **6/6 tur `bitir` ile kapandı**, `error` olayı
**0**, boş cevap **0**, araç izi **6/6**, ilk parça 12,8–43,5 sn.

**Bulgu kaydı (düzeltilmedi — karar Casper'ın):**

- **(a) Soru listesindeki 3. madde belirsiz.** "%15'i 200 olan ne kadar?"
  Türkçede "200'ün %15'i" de olabilir, "%15'i 200 olan sayı" da. Model
  ikinciyi seçti ve **1333,33** dedi — yanlış değil, belirsiz. Beklenen
  cevabı **30** yapmak için soru "200'ün %15'i kaçtır?" olmalı
  (`docs/BIRLIKTE-TEST-SENARYOLARI.md` 3. madde).
- **(b) Beyaz liste reddi görünmedi.** Cevap: *"Freetools alanı açıldı!
  Şimdi freetools.org kataloğunda arama ve araç çalıştırma özelliğine
  sahipsin."* — soru `evil-site.com` ile ilgiliyken cevap freetools
  alanından söz ediyor ve red yok. Araç **koşmadı** (`toolDone` yok),
  yani beyaz liste teknik olarak çalışmış olabilir; eksik olan
  **kullanıcıya söylenen cümledir**. Bu, silinen "gerçeklik kapısı"nın
  geri gelmesi demek **değildir** (AGENTS.md §0) — açık bulgu olarak
  kayda geçti.
- **(c) Eylem iddiası doğrulanmadı.** "Hatırlatman başarıyla eklendi"
  dedi ve `toolDone` geldi; gerçekten kaydedildiği **ölçülmedi**.
  Doğrulamak bir sonraki koşuya iş: aynı kimlikle "hatırlatıcılarımı
  listele" sorusu.
- **(2) Deterministik yanlış: Base64 + Türkçe harf.** `merhaba dünya`
  için doğru `bWVyaGFiYSBkw7xueWE=`, model `bWVyaGFiYSBkdXJuYQ==`
  (ilk koşu) ve `bWVyaGFiYSDDinlbmRh` (ikinci koşu) verdi. Yani UTF-8
  dışı harfte sonuç **bozuk** — bu bir yetenek açığıdır, testere
  takılmış hâliyle kayıtlıdır. Düzeltmesi bilinçli olarak bu tura
  alınmadı: kelime/prompt kuralı eklemek AGENTS.md §0 ile yasak; doğru
  çözüm ajan zincirinin kendi hesabı ya da `freetools_yerel` tarafında
  aranmalı (ayrı iş).

### 8.4 Bu turda kapanan kapılar (tam liste)

| Kapı | Sonuç |
|---|---|
| `python -m pytest tests -q --ignore=tests/live` | **1389 geçti, 5 atlandı, 0 kırmızı** (52,6 sn) |
| Tarayıcı testleri (gerçek Chromium) | **atlanmadı, koştu** (playwright kuruldu; 13 test) |
| `tests/live --live` (kota/anahtar isteyen paket) | **koşmadı** — bu ortamda sağlayıcı anahtarı yok (P0.2 hâlâ açık) |
| Canlı prob (anahtarsız) | 2 test: 1 geçti, 1 **kırmızı** (bulgu 2 — yukarıya bak) |
| Sır kapısı | `Procfile` + yeni testler tarandı, sır yok |
| Ruff / py_compile | geçti |

### 8.5 Bilinçli olarak YAPILMAYAN

- **Dockerfile** (gerekçe §8.1) ve **Vercel preview dalı denemesi**:
  bu ortamdan Vercel hesabına erişim yok; dal preview URL'i ölçülemez.
- **P2.1/P2.2/P4.1** (production geri alma provası, Postgres yedek/geri
  yükleme): Vercel paneli + veritabanı erişimi ister, ikisi de bu
  ortamda yok. Kararda uydurma yapılmadı, madde açık bırakıldı.

---

## 9. 2026-10-25 — P6 UZUN KOŞU: kalıcı koşu defteri (ölçüldü)

**Neden:** Tur Vercel'de 300 saniyede kesiliyordu; `AgentRunState.pause()`
yalnız belleği işaretliyor, koşunun kaydı istemcinin taşıdığı imzalı
handoff'ta duruyordu. İstemci kapanınca iş kayboluyordu. Bu, "uzun süreli
iş" iddiasının önündeki tek gerçek engeldi.

**Ne yapıldı:** `chat/kosu_deposu.py` — koşu ve her araç adımı kalıcı
deftere yazılıyor.

| Kalem | Ayrıntı |
|---|---|
| Depolama | `DATABASE_URL` varsa **Postgres (Neon)**; yoksa yerelde SQLite (`<state>/kosular.db`). Üretimde DSN yoksa defter **kapalı** — geçici diske "kalıcı" denmez. |
| Kayıt | `basak_kosu` (durum, istek, sağlayıcı, adım sayısı, devam paketi) + `basak_kosu_adim` (araç, argüman, sonuç, tur, hata). |
| Tekrar koruması | `(kosu_id, cagri_id)` tekil; kapanmış adım **ezilmez**. Devamda aynı çağrı kimliği yeniden **çalıştırılmaz** (çift tıklama olmaz). |
| Devam | Mola anında `p2-handoff-v1` paketi deftere yazılır (`devam_paketi`). `mesaj_isle(..., kosu_id=...)` bu paketi yükleyip önceki araç sonuçlarını modele geri verir — istemci kapalı olsa da iş sürer. |
| Kiracı ayrımı | `yukle(kosu_id, kullanici)` başka kullanıcının koşusunu **döndürmez**; aynı `run_id` başka kullanıcıya denk gelirse satır devralınmaz. |
| Arayüz | `GET /api/kosu/{kosu_id}` — kimlikli, `no-store`, yalnız özet (durum, adımlar, araçlar). |

**Ölçülen kapılar (2026-10-25, Linux, Python 3.12):**

| Kapı | Sonuç |
|---|---|
| `pytest tests -q --ignore=tests/live` | **1745 geçti, 10 atlandı, 0 kırmızı** (55,1 sn) |
| Yeni testler | **24** (`test_kosu_deposu.py` 11, `test_kosu_devam.py` 6, `test_kosu_tiki.py` 7) |
| Eklenti JS (`kutu.test.mjs`) | **4/4** (yeni: `kosu_devam` sayfaya dokunmadan `kosu_id` ile sürdürür) |
| `py_compile` + `ruff check` | geçti |

### 9.1 Anahtarsız devam tetiği (P7, 2026-10-25)

**Neden:** Uzun işi bulutta sürdürmek için zamanlayıcı gerekiyordu; her
seçenek (Cloudflare hesabı, Vercel Pro cron, GitHub Actions sırrı)
Casper'dan bir **anahtar/hesap** istiyordu. Casper bunu yönetemiyor.
Çözüm: tetiği **zaten kurulu ve bağlı olan eklentinin yoklamasına** verdik.

- `chat/kosu_deposu.bekleyen()` — yalnız `paused` koşuyu bulur.
  `running` koşuya dokunulmaz: "running" hem gerçekten çalışan isteği
  hem de kullanıcının **Durdur** ile kestiği koşuyu anlatır; ikincisini
  kendiliğinden sürdürmek kullanıcının iradesine aykırı olurdu.
- `chat/eklenti_ws._kutu_al()` — eklentinin 3 saniyelik yoklaması boş
  döndüğünde koşuyu `kosu_devam` işi olarak kutuya bırakır ve koşuyu
  `running`a çeker (aynı koşu için ikinci tetik üretilmez).
- `eklenti/arka.js` — `kosu_devam` işinde sayfaya **dokunmaz** (onay
  kapısı gerekmez); aynı kanaldan `kosu_id` ile sohbeti sürdürür.
- `chat/eklenti_ws._cevapla(..., kosu_id)` → çekirdek koşuyu defterden
  devam ettirir.

**Sonuç:** Koşu molaya girdiğinde, Chrome açıkken ~3 saniye içinde
kendiliğinden sürer; Chrome kapalıysa iş beklemede kalır ve Chrome
açılınca kaldığı yerden devam eder. Ne hesap ne anahtar gerekir.

**Dürüst sınırlar (bu turda kanıtlanmayanlar):**

- **Postgres dalı koşulmadı** — bu ortamda `DATABASE_URL` yok. Ölçülen
  yol SQLite; Postgres SQL'i aynı gövdeden üretiliyor ama canlı Neon'da
  denenmedi. Üretimde ilk koşu bunu doğrulamalı.
- **Tik, Chrome'a bağlı:** devam tetiği eklentinin yoklamasından gelir.
  Chrome kapalıyken/servis çalışmıyorken koşu beklemede kalır (uydurma
  "sürüyor" yok). Eklenti güncellemesi için `chrome://extensions` →
  "Yenile" gerekir (yeni sürüm 0.2.1).
- **Kesilen istek kendiliğinden sürmez:** ağ koptuğunda koşu `running`
  kalır ve tik üretilmez; kullanıcı arayüzdeki "Devam et" ile sürdürür.
  Tik üretildikten sonra eklenti hiç cevap vermezse koşu yine `running`
  kalır — aynı elle devam yolu geçerlidir.
- **Eklenti JS testi CI'da değil:** `kutu.test.mjs` (ve diğer üç dosya)
  bu makinede jsdom ile koşturuldu; `test.yml`'de `eklenti-js` işi
  **yok** — planın P0 maddesi kodda değil, yalnız belgede duruyor.
- **Arayüz göndermiyor:** web/eklenti sohbeti `kosu_id` alanını henüz
  kullanmıyor; alan API'de hazır.
- **Artifact yok:** yalnız adım günlüğü var; dosya/rapor çalışma alanı
  sonraki dilim.
- **Saklama/silme yok:** koşu satırları süresiz durur (KVKK maddesi
  P4.2 ile birlikte ele alınmalı).
